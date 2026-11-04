---
trigger: always_on
---

use for run venv i am use conda 
terminal cmd :  conda activate inst-bot-venv

## AWS EC2 and Terminal Rules
Our project runs on AWS EC2.

- EC2 SSH user: `ubuntu`
- Project directory: `/home/ubuntu/insta-bot`
- Expected terminal working directory:

```
ubuntu@ip-172-31-44-222:~/insta-bot$
```

- Run project commands from `/home/ubuntu/insta-bot` unless a command specifically requires another directory.
- Do not assume the project is running directly on the EC2 host.
- Use the existing Conda/virtual environment rules in this file. Do not create another environment or install dependencies globally without approval.
- Use `sudo` only when genuinely required. Do not run the project as root unnecessarily.
- Never expose credentials, cookies, tokens, passwords, or session data in command output or logs.

## Docker Compose Architecture
Our application runs using Docker Compose with five containers.

Compose project:

- Name: `insta-bot`
- Compose file: `/home/ubuntu/insta-bot/docker-compose.yml`

| Service | Container name | Image |
|---|---|---|
| Backend | `insta-bot-backend-1` | `insta-bot-backend` |
| Worker | `insta-bot-worker-1` | `insta-bot-worker` |
| Frontend | `insta-bot-frontend-1` | `node:20-alpine` |
| Database | `insta-bot-db-1` | `postgres:15-alpine` |
| Redis | `insta-bot-redis-1` | `redis:7-alpine` |

### Important Docker command rules
Use Docker Compose commands from the project directory.

```
docker compose ls
docker compose ps
docker ps
docker compose logs --tail=100 worker
docker compose logs --tail=100 backend
docker compose exec worker sh
docker compose exec backend sh
```

Remember:

- `docker ls` is not a valid Docker command. Use `docker ps` to list running containers.
- Use `docker compose exec <service> <command>` to execute commands inside a running service.
- Use `docker compose logs` to inspect container logs.
- Use `docker compose config` to validate Compose configuration.
- Use `docker compose build <service>` when a service image needs rebuilding.
- Do not assume host Python and container Python environments are identical.

### Execution and safety rules

1. First determine whether a command belongs on the EC2 host or inside a container.
2. Database commands must target the correct PostgreSQL container and database.
3. Django management commands should run inside the backend container unless the task explicitly requires otherwise.
4. Celery commands and worker diagnostics should target the worker container.
5. Redis diagnostics should target the Redis service.
6. Do not restart, recreate, stop, or delete containers unless the approved implementation step requires it.
7. Do not run `docker compose down -v`, remove volumes, reset databases, or delete persistent profiles.
8. Before rebuilding or recreating a container, explain the expected impact and obtain approval if it could interrupt running services or risk data.
9. Preserve all existing Docker volumes, PostgreSQL data, Redis data, and Chromium browser profiles.
10. Never modify production Compose configuration while working on a development-only phase unless explicitly approved.

## Phase Execution Rule
For every implementation phase:

1. Inspect the current EC2 project state.
2. Check Git status and existing uncommitted changes.
3. Identify the relevant Docker Compose service.
4. Implement only the approved scope.
5. Run focused tests in the correct environment.
6. Report changed files, commands executed, containers affected, and test results.
7. Stop and wait for approval before starting the next phase.