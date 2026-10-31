# AWS Production Deployment Plan

## 1. Recommended Architecture

Use AWS-managed services where possible, with Docker images in ECR. Keep automation workers separate from the public API because Playwright needs Chromium/Firefox, more CPU/RAM, and potentially browser lifecycle isolation.

```text
Users
  |
  | HTTPS
  v
Route 53 -> ACM certificate -> CloudFront or Application Load Balancer
                                     |
                     +---------------+---------------+
                     |                               |
                     v                               v
             React frontend                    Backend ALB path
             ECS Fargate/Nginx               /api/* and /ws/*
                                                     |
                                                     v
                                            Django Daphne on ECS
                                                    |
                     +------------------------------+------------------------------+
                     |                              |                              |
                     v                              v                              v
               RDS PostgreSQL                ElastiCache Redis              Secrets Manager
            private subnet, Multi-AZ       broker + pub/sub + cache          environment secrets
                     |                              |
                     +--------------+---------------+
                                    v
                             Celery worker
                              ECS EC2 nodes
                    Playwright browser automation
                                    |
                     +--------------+---------------+
                     |                              |
                     v                              v
               S3 media buckets              CloudWatch Logs/Metrics

Optional WebSocket service: ECS service on Node + Redis/MongoDB as needed
Optional analytics: AWS Glue, Athena, or EMR/Spark on scheduled jobs
```

## 2. AWS Services

| Area | AWS service | Purpose |
|---|---|---|
| DNS/TLS | Route 53, ACM | Domain routing and HTTPS certificates |
| CDN/security | CloudFront, AWS WAF | Static frontend delivery, caching, and optional protection |
| Load balancing | Application Load Balancer | HTTP/WebSocket routing and health checks |
| Containers | ECR + ECS | Store and run application containers |
| Backend capacity | ECS Fargate | Stateless Django/Daphne API tasks |
| Worker capacity | ECS on EC2 or dedicated EC2 ASG | Playwright workers that need Chromium, browser binaries, CPU and memory |
| Database | RDS PostgreSQL 15 | Primary durable application data |
| Cache/broker | ElastiCache Redis | Celery broker/result backend and future cache/channel layer |
| Storage | S3 | Raw/processed downloads, exports, backups and static assets |
| Secrets | Secrets Manager | Database credentials, Django secret, worker token and API secrets |
| IAM | IAM roles/policies | Grant ECS tasks least-privilege access without access keys |
| Networking | VPC, 2 public + 2 private subnets, NAT, security groups | Network isolation and controlled outbound access |
| Monitoring | CloudWatch Logs, Metrics, Alarms, SNS | Logs, dashboards and incident alerts |
| CI/CD | GitHub Actions | Build/test/push ECS images and trigger deployment |
| State | Terraform remote state in S3 + DynamoDB lock | Safe collaborative infrastructure changes |
| Email/alerts | SNS; SES optional | Operations alerts; application email later if required |
| Data processing | Glue/Athena; optional EMR | Optional Spark and analytics workloads |

## 3. Production ECS Layout

### ECS cluster

Create one ECS cluster with two capacity strategies/services:

1. **Fargate backend and frontend services**
   - Django/Daphne task: 1 vCPU, 2 GB minimum to start; scale 2–6 tasks.
   - Frontend/Nginx task: 0.25–0.5 vCPU, 0.5 GB.

2. **Worker capacity on ECS EC2 (preferred over Fargate initially)**
   - EC2 worker: `t3.large` or larger depending on browser concurrency.
   - Worker task: 2 vCPU and 4 GB per task, matching the existing Compose resource limit as a starting point.
   - Start with one worker task on one instance, then scale by queue depth and CPU.

A worker instance should not receive public inbound traffic. Use an instance role for ECS and S3 access, with outbound internet access through NAT or an approved controlled proxy architecture.

### ECS services

- `instabot-backend`: same task definition/image across API and ASGI deployment.
- `instabot-worker`: Celery worker task only; no public load balancer target.
- `instabot-frontend`: Nginx static frontend container, or deploy static output directly to S3+CloudFront.
- `instabot-node-ws` optional only after the Node/Redis/Mongo flow is required.
- Spark jobs optional as ECS scheduled tasks, Glue jobs, or EMR only; they are not part of normal API traffic.

## 4. Network Design

Use a VPC such as `10.0.0.0/16`:

- 2 public subnets for ALB and NAT gateways.
- 2 private application subnets for ECS tasks.
- 2 private database subnets for RDS and ElastiCache.
- No public IP for ECS tasks, RDS or ElastiCache.

Security groups:

| Source | Destination | Port |
|---|---|---|
| Internet | ALB | 80 and 443 |
| ALB | Backend ECS tasks | 8000 |
| ALB | Frontend ECS tasks | 80 |
| Backend/worker | RDS | 5432 |
| Backend/worker | ElastiCache Redis | 6379 |
| ECS tasks | S3 through gateway endpoint/Internet/NAT | HTTPS 443 |
| Operations/CI | No direct SSH access; use Systems Manager Session Manager if needed | — |

Send all inbound HTTP from the internet to HTTPS. Redirect port 80 to 443 and only permit public traffic through the ALB or CloudFront.

## 5. Routing Flow

### Web request flow

```text
Browser
  -> Route 53
  -> HTTPS on ALB
  -> frontend for / or React static files
  -> /api/* and /ws/* to Django Daphne
  -> PostgreSQL for durable state
  -> Redis for cache, channels and Celery broker
```

The backend currently has an ASGI command in production Compose. It should be the ECS task command. The Node WebSocket service is optional and should not be added to the main path until its Redis/MongoDB behavior is implemented and tested.

### Automation execution flow

```text
Frontend/API caller
  -> POST /api/v1/bot/execute/
  -> Django validates account and ownership
  -> Django saves AutomationJob to PostgreSQL
  -> Django publishes Celery task to ElastiCache Redis
  -> Celery worker in private ECS EC2 capacity claims the task
  -> Worker loads account/cookies and invokes Playwright
  -> Worker records job/callback status through the Django API
  -> API/client polls /api/v1/bot/jobs/{job_id}/ or subscribes to updates
```

Browser binaries must remain worker-only. Do not install Playwright/browser dependencies in the backend image.

## 6. Database and Storage

### RDS

- Engine: PostgreSQL 15 or the repository-supported version.
- Deployment: Multi-AZ for production; a single-AZ dev instance for cost testing.
- Backup retention: 7–35 days.
- Storage encryption: enabled.
- Secrets: credentials supplied by ECS through Secrets Manager.
- Run migrations as a one-shot ECS task before traffic switches:

```bash
python manage.py migrate --no-input
python manage.py collectstatic --no-input  # if Django static files are served or stored
```

### Redis

- Use Redis 7-compatible ElastiCache.
- Separate logical Redis databases can exist initially for broker/results, but production credentials and TLS must be configured consistently.
- Restrict Redis access to backend and worker security groups.

### S3

Create environment-specific buckets:

- `instabot-<account>-<env>-raw`
- `instabot-<account>-<env>-processed`
- `instabot-<account>-<env>-exports`
- `instabot-<account>-<env>-backups`

Enable block-public-access, versioning for exports/backups, encryption, lifecycle policies, access logging and bucket policies for ECS task roles. Use private buckets and CloudFront signed URLs when media access is required; never make media public.

## 7. Secrets and IAM

Store the following in Secrets Manager or as ECS parameter-store references:

- `DJANGO_SECRET_KEY`
- database username/password and host
- `INSTABOT_WORKER_TOKEN`
- Redis endpoint/TLS connection string
- optional third-party API credentials
- optional proxy credentials

Use separate ECS task roles:

- Backend role: read required secrets and access S3 buckets needed by Django.
- Worker role: read required secrets, access media S3 buckets, and write CloudWatch logs.
- No shared AWS access keys in the repository or environment files.
- External GitHub Actions should use an OIDC role rather than long-lived AWS keys.

## 8. CI/CD Pipeline

Build and deploy images for immutable releases instead of pulling source onto EC2.

1. Pull request:
   - Checkout code.
   - Install dependencies and run focused tests.
   - Run Django checks and migrations against a disposable database if feasible.
   - Build backend, worker, and frontend images.
   - Scan images with ECR Scanning/Trivy and fail on critical vulnerabilities.

2. Main branch:
   - Assume an AWS IAM role using GitHub OIDC.
   - Login to ECR.
   - Build and push backend, automation worker and frontend images using commit SHA tags and immutable digests.
   - Update ECS task definitions.
   - Run migration task.
   - Deploy backend service with rolling deployment/health checks.
   - Deploy frontend/container or upload frontend assets and invalidate CloudFront.
   - Deploy worker service last.
   - Wait for ECS service stability and run smoke tests.

Recommended image tags: SHA, release version, and optionally `stable`; never deploy only by `latest`.

## 9. Deployment Sequence

### Phase 0 — fix production blockers

Before infrastructure deployment:

- Correct the GitHub Actions workflow paths. The current workflow references `backend/Dockerfile`, `automation/Dockerfile`, and `frontend/Dockerfile.prod`; repository Dockerfiles are in `infradocker/` and one frontend Dockerfile builds from the repository root context.
- Replace static `latest` deployment values with SHA-based ECS task definitions.
- Replace the Compose-deploy shell script with ECS migrations/deploy operations.
- Add the missing Terraform variables/outputs/backend configuration and make public/private subnet design explicit.
- Ensure the Django backend starts with Daphne and that `downloads` and WebSocket dependencies are valid in production settings.
- Add explicit Redis TLS/password settings, RDS SSL settings and ECS health-check URL behavior if supported by the deployment environment.

### Phase 1 — foundation

- Create AWS organization/account/region strategy.
- Configure Terraform S3 backend and DynamoDB lock table.
- Create VPC, subnets, route tables, Internet/NAT gateways, security groups and ECS cluster.
- Create ECR repositories, log groups, SNS alarm topic and Secrets Manager entries.

### Phase 2 — data services

- Deploy RDS PostgreSQL, ElastiCache Redis and S3 buckets.
- Configure backup and encryption.
- Create ECS task/execution roles and application roles.

### Phase 3 — application services

- Push backend and frontend images.
- Run one-shot migrations and smoke/check commands.
- Deploy backend, frontend and ALB target groups.
- Configure Route 53 and ACM.
- Verify health, API authentication and static/frontend loading.

### Phase 4 — automation workers

- Push the automation image containing Playwright browsers.
- Deploy an ECS EC2 capacity provider and Celery worker service.
- Add queue-depth scaling based on Redis/Celery metrics.
- Run one controlled automation job against a dummy account.

### Phase 5 — production hardening

- Enable CloudFront and WAF if appropriate.
- Add CloudWatch dashboards, alarms, central logs and retention.
- Test RDS backup restore, Redis failure handling and ECS task recovery.
- Add autoscaling, cost budgets, image cleanup, secret rotation and deployment rollback.

## 10. Autoscaling

- Backend: scale by ALB request count and CPU; begin with 2 tasks across 2 availability zones.
- Frontend: scale by CPU and request volume.
- Workers: scale by Celery queue depth, CPU and memory. Avoid scaling based on browser actions alone because a worker can become healthy before it is ready for more browsers.
- RDS: scale instance class/storage after load measurement; consider read replicas only when read-heavy workloads prove them necessary.
- Redis: use replication/node sizing based on broker and Celery result retention.

## 11. Monitoring

Create CloudWatch dashboards for:

- ALB 5xx/4xx rate and target health
- ECS service CPU/memory, task restarts and deployment failures
- RDS CPU, connections, free storage and replication status
- ElastiCache CPU, memory and evictions
- Celery queue depth and task success/failure rate
- Playwright worker job duration, failures and browser crashes
- S3 request/error metrics and costs

Alarms should notify SNS and pagers/chat systems for:

- no backend healthy targets
- sustained 5xx rate
- RDS storage/connection limits
- Redis memory pressure
- Celery queue backlog
- worker task crashes or prolonged no-task heartbeats
- migration/deployment failures

## 12. Cost-Starting Estimate

These are order-of-magnitude planning numbers for low-production traffic; obtain an AWS calculator estimate for the exact region and commitment plan.

| Service | Starting choice | Expected monthly range |
|---|---:|---:|
| ECS backend Fargate | 2 small tasks | $30–$100 |
| ECS worker EC2 | 1 `t3.large`–`t3.xlarge` | $60–$180 |
| RDS PostgreSQL | Single-AZ then Multi-AZ | $30–$250 |
| ElastiCache Redis | Small single node then replication | $15–$200 |
| ALB + CloudFront + Route 53 | Low traffic | $20–$100 |
| NAT, logs, S3, secrets, backups | Small usage | $20–$150 |

Budget roughly $175–$980/month initially depending on Multi-AZ, worker size and data transfer. Use Spot capacity only for disposable worker tasks after Celery retry behavior is validated, never for the database.

## 13. Go-Live Checklist

- [ ] Domain and ACM certificate configured in region/CloudFront requirements.
- [ ] WAF and HTTPS redirects enabled.
- [ ] RDS password, Django secret, Redis password and worker token stored in Secrets Manager.
- [ ] No application secrets or `.env` secrets committed to Git.
- [ ] ECS task roles have least-privilege permissions.
- [ ] Database migration ran successfully as a separate task.
- [ ] Backend, frontend and worker health checks pass.
- [ ] Celery executes and returns a result for one dummy job.
- [ ] Job status/cancellation endpoints work in AWS.
- [ ] Playwright can start Chromium with the worker IAM/network configuration.
- [ ] S3 upload/download permissions work through task roles.
- [ ] CloudWatch logs, dashboards and SNS alarms are active.
- [ ] Smoke test is automated.
- [ ] Rollback procedure is tested.
- [ ] RDS backup restore is tested.
- [ ] Optional Node/Spark/Mongo services are excluded unless explicitly needed.

## 14. Recommended Final AWS Stack

Use this minimum production stack:

- Route 53
- ACM
- ALB
- ECS Fargate backend
- ECS EC2 Celery/Playwright workers
- ECR
- RDS PostgreSQL Multi-AZ
- ElastiCache Redis
- S3
- Secrets Manager
- IAM
- CloudWatch/SNS
- GitHub Actions + Terraform remote state

CloudFront, WAF, MongoDB/Node WebSocket, Spark/Glue and EMR should be staged additions rather than blockers for the core automation product going live.
