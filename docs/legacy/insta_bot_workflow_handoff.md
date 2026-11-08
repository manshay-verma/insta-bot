# Instagram Automation Project --- Engineering Handoff & Workflow

**Handoff date:** 4 November 2026\
**Project:** `/home/ubuntu/insta-bot`\
**Current phase:** D1.3 --- Browser Runner Supervision (implementation
started; verification incomplete)\
**Local coding model:** `qwen2.5-coder:1.5b`\
**Purpose:** Preserve project context, completed work, safety rules, and
the exact workflow so development can continue without repeating broad
inspections.

------------------------------------------------------------------------

## 1. How to use this document

This is the working handoff for the coding agent and the developer.

Before making changes:

1.  Read this document fully.
2.  Read the permanent project rules:
    `.agents/rules/use-conda-for-run-venv.md`
3.  Inspect the current Git state and the exact code paths relevant to
    the task.
4.  Treat the current repository as the source of truth. This handoff
    summarizes prior reports and may not reflect later unreported edits.
5.  Do not assume a phase is complete merely because code was written or
    a migration was applied.

**Important:** The current D1.3 worktree may contain incomplete or
uncommitted changes. Preserve them. Do not reset, clean, overwrite, or
revert them.

------------------------------------------------------------------------

## 2. Project architecture and environment

### Host and repository

-   Host: AWS EC2 Ubuntu
-   SSH user: `ubuntu`
-   Repository: `/home/ubuntu/insta-bot`
-   Compose project: `insta-bot`
-   Compose file: `/home/ubuntu/insta-bot/docker-compose.yml`

Typical shell prompt:

``` bash
ubuntu@ip-172-31-44-222:~/insta-bot$
```

### Main stack

-   Backend: Django + Django REST Framework
-   Database: PostgreSQL
-   Queue and broker: Celery + Redis
-   Browser automation: Playwright + Chromium
-   Orchestration: Python
-   Frontend: Node.js
-   Runtime: Docker Compose

### Compose services

  Service    Typical container        Image
  ---------- ------------------------ ----------------------
  backend    `insta-bot-backend-1`    `insta-bot-backend`
  worker     `insta-bot-worker-1`     `insta-bot-worker`
  frontend   `insta-bot-frontend-1`   `node:20-alpine`
  db         `insta-bot-db-1`         `postgres:15-alpine`
  redis      `insta-bot-redis-1`      `redis:7-alpine`

Useful commands:

``` bash
docker compose ps
docker ps
docker compose logs --tail=100 backend
docker compose logs --tail=100 worker
docker compose exec backend python manage.py showmigrations api
docker compose exec backend python manage.py makemigrations --check --dry-run
```

Run Django commands in the backend container unless the source mount or
task specifically requires another service. Browser/automation tests may
need the worker container because it has the automation source tree.

Do not use `docker ls`; use `docker ps`.

------------------------------------------------------------------------

## 3. Non-negotiable safety and change-control rules

### Data and infrastructure safety

-   Never run `docker compose down -v`.
-   Never delete Docker volumes or PostgreSQL data.
-   Never reset or drop the database.
-   Never remove persistent Chromium profiles.
-   Do not stop, restart, recreate, or rebuild containers unless the
    task explicitly requires it and approval is obtained.
-   Do not change Compose, Redis persistence, production configuration,
    or EC2 infrastructure as part of a code-only phase.
-   Use `sudo` only when necessary.
-   Do not install packages globally or create a new Python environment
    without approval.
-   Follow the existing Conda/venv instructions in
    `.agents/rules/use-conda-for-run-venv.md`.

### Change preservation

Before editing:

``` bash
git status --short
git diff --stat
git diff --cached --stat
```

-   Preserve all existing uncommitted changes.
-   Do not run `git reset --hard`, `git clean`, broad checkout/revert
    commands, or destructive cleanup.
-   Do not overwrite files to make a patch easier.
-   Make the smallest change that solves the approved task.
-   Report every changed file and every migration.

### Security

-   Never request or print Instagram passwords, cookies, session IDs,
    API tokens, or secret keys.
-   Redact credentials from logs and screenshots.
-   Do not bypass CAPTCHA, checkpoints, or anti-bot controls.
-   Account verification must remain owner-driven and manual.
-   Never log IPC credentials, HMACs, owner tokens, or cookie contents.

### Scope control

-   No Kubernetes, multiple EC2 instances, EFS, or multiple Celery
    workers in this development scope.
-   Intended Celery worker mode is one worker with
    `--pool=solo --concurrency=1`.
-   SSH is for manual browser verification only.
-   No unrelated architecture rewrites.
-   Do not implement a later phase while working on an earlier phase.

------------------------------------------------------------------------

## 4. Required development workflow

Always follow:

**Inspect → Plan → Approval → Implement → Test → Report**

### Step 1 --- Inspect

-   Inspect only the files and call paths required for the task.
-   Check Git status first.
-   Read the permanent rules.
-   Inspect existing tests and migration dependencies.
-   Identify whether the worktree already contains partial
    implementation.
-   Do not edit during inspection.

### Step 2 --- Plan

Return a concise plan containing:

-   Exact behavior to change.
-   Exact files expected to change.
-   Database migration impact.
-   Security and failure-mode considerations.
-   Tests to add/run.
-   Explicitly excluded phases and infrastructure.

### Step 3 --- Approval

Wait for explicit approval before editing, migrating, or changing
runtime behavior.

Approval for one phase does not authorize another phase.

### Step 4 --- Implement

-   Implement only the approved scope.
-   Keep patches narrow.
-   Preserve previous phases.
-   Do not silently change infrastructure or dependencies.
-   If an unsafe or out-of-scope dependency is discovered, stop and
    report it.

### Step 5 --- Test

-   Run syntax/compile checks.
-   Run focused tests for changed behavior.
-   Run relevant regression tests for previous phases.
-   Use PostgreSQL-backed tests for transaction, row-locking, and
    concurrency behavior. SQLite or mocks alone are insufficient
    evidence for PostgreSQL guarantees.
-   Do not claim tests passed if a command failed, was skipped, or its
    result is unknown.
-   Record exact test command, pass/fail count, and environment.
-   If a test cannot run because a dependency is unavailable, do not
    install it without approval. Report the limitation.

### Step 6 --- Report

Report:

1.  What changed.
2.  Exact changed files.
3.  Migration created/applied (or not).
4.  Tests run and exact results.
5.  Tests not run and why.
6.  Runtime/container/Redis/DB changes, if any.
7.  Remaining risks.
8.  Whether the phase is complete, conditional, or blocked.
9.  Confirm no later phase was started.

------------------------------------------------------------------------

## 5. Completed phases --- based on previous agent reports

These are historical reported results, not a claim that every behavior
has been independently revalidated in the current worktree.

### Initial audit

Original issue:

-   A trusted local browser session worked.
-   The Playwright worker used a fresh profile.
-   Account 1 had no stored cookies.
-   Password fallback reached an account checkpoint.

The audit found issues including plaintext cookie handling, broad worker
API access, ephemeral browser contexts, ignored headless configuration,
and retry/cancellation/recovery gaps.

Live inspection found:

-   Account 1 `cookies_json` was SQL NULL.
-   Worker API returned no cookies.
-   No account-1 cookie file existed.
-   Account was active, encrypted password existed, no proxy was
    configured, and no active jobs existed.
-   Root cause chain:
    `cookies_json NULL → worker API None → CookieSync no cookies → Playwright unauthenticated → job fails`.
-   Why cookies were never stored remained unknown.

### Phase A --- Cookie/session management

Reported work:

-   Encrypted cookie/session storage and metadata.
-   PostgreSQL as authoritative cookie source.
-   Session status and cookie version.
-   Missing/malformed/expired cookie validation.
-   Version/conflict protection.
-   Dedicated `INSTABOT_COOKIE_ENCRYPTION_KEY`, separate from Django
    secret.
-   Migration `account.0003_cookie_session_metadata` applied after a
    pre-migration database dump.
-   Account 1 remained `session_status=missing`, `cookie_version=0`,
    with no cookies.
-   Focused Phase A tests: 15/15.
-   Standalone baseline cookie tests: 8/8.
-   Broader suite had three pre-existing failures at that point.

No real Instagram login was performed.

### Phase B --- Persistent browser profiles

Reported work:

-   No separate `/srv/insta-bot` EBS mount was available, so a named
    Docker volume was used.
-   Persistent Chromium profile support.
-   Headless setting honored.
-   Account-specific profile paths.
-   Process-level profile lock.
-   Explicit context close.
-   Docker volume: `insta-bot_instabot_profiles` mounted at
    `/app/profiles`, owned by appuser UID/GID 1000.
-   Worker rebuilt/recreated during that earlier approved phase; volume
    retained.
-   Focused profile/cookie suite: 12/12.
-   Synthetic cookie persistence, same-profile concurrency, and
    different-account isolation tested.

No actual Instagram login was performed. The named volume is not a
separate EBS mount; root EBS persistence/recovery still needs
validation.

### Phase C --- PostgreSQL account/browser locking

Reported work:

-   `AccountBrowserLock`.
-   Migration `api.0005_accountbrowserlock_and_constraint.py`.
-   Atomic acquire/renew/validate/reconcile/release helpers in
    `account_locks.py`.
-   Partial unique index `one_active_automation_job_per_account` for
    active statuses.
-   Lock lifecycle integrated into task execution and retries.
-   Worker cookie/session APIs validate lock ownership.
-   Focused lock/cookie/job tests reported 41/41, plus task-result and
    profile tests.

No live Instagram worker SIGKILL/orphan Chromium test was performed.

### Phase D inspection

Inspection found:

-   Default Celery early-ack risk could leave a RUNNING job after worker
    loss.
-   No startup stale-job reconciliation.
-   No task time limits.
-   Docker stop grace might be too short for Playwright cleanup.
-   No orphan Chromium tracking.
-   Health check covered Redis/Chromium but not full DB/Celery/queue
    health.
-   OTP and cancellation recovery gaps.
-   Logs lacked consistent structured context.
-   Failure-injection coverage was missing.

D1 was split into subphases. Do not assume D1.4 or D1.5 is complete.

------------------------------------------------------------------------

## 6. D1.1 --- Execution-generation fencing

Reported implementation:

-   Migration `0006_execution_generation_fencing`.
-   Added fields including:
    -   `AutomationJob.execution_generation`
    -   `application_retry_count`
    -   `worker_redelivery_count`
    -   `recovery_state`
    -   `AccountBrowserLock.execution_generation`
-   Generation and owner fencing propagated through tasks, worker, API
    client, cookies/session endpoints, and OTP paths.
-   Corrective patch made generation validation fail closed.
-   Focused tests reported 43 passed.
-   Browser profile tests reported 4 passed.
-   `makemigrations --check --dry-run` found no pending changes.

D1.1 was accepted based on the reported evidence.

------------------------------------------------------------------------

## 7. D1.2 --- Atomic recovery authority and idempotency

Reported implementation:

-   Migration `0007_atomic_execution_recovery`.
-   PostgreSQL transaction/row-lock recovery authority.
-   Separate application retry and worker-loss counters.
-   Prepared generation can be resumed after a crash rather than
    allocating another generation.
-   Migration `0008_execution_recovery_record`.
-   Added `ExecutionRecoveryRecord`.
-   Unique recovery identity `(job, failed_generation, recovery_kind)`.
-   Unique delivery key and persisted allocated generation.
-   Deterministic worker-loss key:
    `worker_redelivery:<job_id>:<failed_generation>`
-   Stable worker-loss key propagated through Celery.
-   Recovery history remains queryable after current key changes.
-   OTP reconnect requires confirmed runner identity, valid owner token,
    and account lock.
-   Missing/wrong/stale runner identity must fail closed.
-   Focused Django tests reported 43 passed, 0 failures after the
    corrective patch.
-   Migrations 0007 and 0008 reported applied.

D1.2 was accepted for **database recovery authority and idempotency
scope** based on the reports.

Important limitation:

-   Actual runner IPC/reconnection was not implemented in D1.2.
-   A database decision to reconnect does not prove that a live runner
    can actually be reconnected.
-   Real process-crash recovery was not proven.

------------------------------------------------------------------------

## 8. D1.3 --- Browser runner supervision: current status

**Current status: implementation started; verification incomplete. Do
not mark complete.**

The purpose of D1.3 is to separate Playwright/Chromium from the Celery
supervisor so a supervisor can die and a new supervisor can safely
reconnect to the same existing browser runner.

### D1.3 intended architecture

-   Dedicated browser runner subprocess owns Playwright and Chromium.
-   Celery worker acts as supervisor.
-   Runner holds the actual account profile `flock()` for its full
    lifetime.
-   Runner identity includes UUID, job ID, execution generation, PID,
    process start ticks, container boot identity, process group ID, and
    profile lock identity.
-   Runner exposes authenticated Unix-domain socket IPC.
-   Supervisor reconnects to the existing runner using a scoped HMAC
    challenge.
-   Runner immediately rejects new browser actions if ownership or
    supervisor connectivity cannot be confirmed.
-   PostgreSQL remains authoritative for job status, account lock,
    cookies, OTP, and results.
-   OTP reconnection must reuse the same existing runner and browser
    challenge.
-   No replacement browser/login for an unexpired OTP challenge.
-   Database lease expiry alone is never proof that the old runner or
    Chromium terminated.

### Mandatory D1.3 safety constraints

1.  Database lease expiry must never be treated as proof that the old
    runner or Chromium terminated.
2.  If supervisor connectivity or ownership validation is lost, the
    runner must immediately reject new browser actions.
3.  A replacement runner must not start until the previous runner is
    positively terminated or safely fenced.
4.  Before signaling a process group, validate:
    -   PID
    -   `/proc` process start ticks
    -   Container boot identity
    -   PGID
    -   Runner UUID
    -   Execution generation
5.  Protect against PID reuse.
6.  Use a dedicated `INSTABOT_RUNNER_IPC_SECRET`, separate from Django
    `SECRET_KEY` and cookie encryption key.
7.  Use nonce-based HMAC authentication, expiry, and replay protection.
8.  Unix socket directory mode `0700`; socket mode `0600`.
9.  Never log credentials or expose them in Redis or ordinary job
    fields.
10. Runner owns the actual profile flock for its entire lifetime.
11. Database lock expiry alone must not authorize profile reuse.
12. Add real Linux process integration tests, not only mocked runner
    tests.

### D1.3 implementation activity recorded in the latest agent log

The coding agent reported that it:

-   Added or edited dedicated runner, supervisor, and IPC modules.
-   Modified backend models, account-lock handling, tasks, and browser
    manager.
-   Added migration `0009_browser_runner_identity`.
-   Applied migration `0009` in the existing backend container.
-   Ran compile checks.
-   Encountered several initial test failures and made follow-up edits.
-   Reported a later combined command for
    runner/account-lock/task-result tests.
-   Could not run the browser profile pytest suite because `pytest` was
    not installed in the worker environment.
-   Did not install pytest.
-   Reported migration `0009` applied and no pending migration changes.
-   Confirmed permanent project rules were already appended to
    `.agents/rules/use-conda-for-run-venv.md`.

### D1.3 evidence gaps

The latest report does **not** provide a clear final test pass count or
sufficient evidence for:

-   Real supervisor termination while runner/Chromium remains alive.
-   New supervisor reconnecting to the same runner.
-   Safe SIGTERM/SIGKILL process-group cleanup.
-   PostgreSQL connectivity loss while runner remains alive.
-   Lease expiry while Chromium remains alive.
-   Competing supervisors racing to reconnect.
-   PID reuse/mismatched process identity.
-   Actual OTP challenge reconnect.
-   Confirmed availability/configuration of
    `INSTABOT_RUNNER_IPC_SECRET`.

Therefore:

**D1.3 is not verified complete. Freeze further feature work until a
focused review establishes what is actually implemented and safe.**

Do not rollback migration `0009` or revert partial code without a
reviewed recovery plan.

------------------------------------------------------------------------

## 9. Exact next task: D1.3 read-only verification

The next coding-agent task must be **read-only**. Do not implement new
features yet.

### Required checks

1.  Inspect `git status`, `git diff --stat`, and exact D1.3 changed
    files.
2.  Confirm migration `0009` is applied and migration consistency is
    clean.
3.  Inspect the actual runner, supervisor, IPC, and browser lifecycle
    code.
4.  Confirm whether `INSTABOT_RUNNER_IPC_SECRET` is configured. Do not
    print its value.
5.  Confirm socket permissions and HMAC nonce/replay/expiry behavior.
6.  Confirm process identity validation before signals.
7.  Confirm runner holds the profile flock for its lifetime.
8.  Confirm runner stops accepting actions when ownership/DB
    connectivity is lost.
9.  Confirm a replacement runner cannot start based on lease expiry
    alone.
10. Identify exact tests that cover each behavior and whether they use
    real Linux processes or mocks.
11. Run no migration, no database mutation, no container restart, and no
    Redis mutation during this review.
12. Do not install missing dependencies.
13. Do not edit files.

### Suggested prompt for the local coding agent

``` text
Perform a READ-ONLY D1.3 verification. Do not edit files, apply migrations,
modify database/Redis, restart containers, install packages, or change infrastructure.

Read:
- Project handoff Markdown.
- .agents/rules/use-conda-for-run-venv.md.
- Current git status and diffs.
- Runner/supervisor/IPC implementation.
- Browser manager/profile lock code.
- D1.2 recovery authority and D1.3 migration.

Verify:
1. Dedicated IPC secret exists in runtime configuration without printing its value.
2. Unix socket directory/socket permissions.
3. HMAC nonce, expiry, and replay protection.
4. PID/start ticks/boot ID/PGID/runner UUID/generation validation before signals.
5. Runner owns profile flock for its entire lifetime.
6. Runner rejects actions immediately after ownership or DB connectivity loss.
7. Lease expiry alone cannot authorize replacement runner/profile reuse.
8. Supervisor can reconnect to the same runner.
9. OTP reconnect uses the same runner and browser challenge.
10. Real Linux process integration test coverage versus mocks.

For each requirement report exact file/function/test and evidence.
Give exact test pass counts only if already available; do not guess.
List missing guarantees and the smallest safe next step.
Preserve every existing change. Stop after the report.
```

------------------------------------------------------------------------

## 10. Working with the local Qwen2.5-Coder 1.5B model

The local model is small. Use it for narrow, well-bounded tasks, not
broad autonomous architecture work.

### Recommended task size

Give it one task at a time:

-   Explain one function.
-   Trace one call path.
-   Review one small diff.
-   Add one focused test.
-   Identify one bug from a concrete traceback.
-   Produce a read-only report for a small set of files.

Avoid asking it to redesign the entire project or independently
implement a multi-file process-supervision architecture.

### Rules for prompting the local model

-   Include the exact project path.
-   Include relevant filenames and function names.
-   State whether the task is read-only or implementation.
-   Explicitly list forbidden operations.
-   Ask it to inspect before proposing changes.
-   Require exact test names and outputs.
-   Ask it to stop if context is missing.
-   Ask it not to invent files, functions, test results, or environment
    configuration.
-   Keep changes small and review diffs manually.

### Suggested local model prompt prefix

``` text
You are working in /home/ubuntu/insta-bot.

Follow .agents/rules/use-conda-for-run-venv.md and the project handoff.

Preserve all existing uncommitted changes.
Do not reset, clean, overwrite, or revert unrelated files.
Do not run destructive database, Docker, Redis, or volume commands.
Do not install dependencies or change infrastructure without approval.
Do not expose credentials or session data.

Workflow: Inspect -> Plan -> Approval -> Implement -> Test -> Report.

Only perform the exact task below. If the task is ambiguous or unsafe,
stop and explain what information is missing.
Never claim a test passed unless you have its actual output.
```

### Review strategy

For every implementation:

1.  Ask Qwen to inspect and propose a small plan.
2.  Review the plan yourself.
3.  Approve only the exact scope.
4.  Ask it to implement one small patch.
5.  Inspect `git diff`.
6.  Run the narrow test.
7.  Review the actual output.
8.  Record the result in the handoff.

For complex process ownership, concurrency, cryptography, and database
locking, do not trust a 1.5B model's unsupported claims. Require code
evidence and real tests.

------------------------------------------------------------------------

## 11. Useful commands for safe inspection

``` bash
cd /home/ubuntu/insta-bot

git status --short
git diff --stat
git diff --cached --stat

docker compose ps

docker compose exec backend python manage.py showmigrations api

docker compose exec backend python manage.py makemigrations --check --dry-run
```

Inspect only relevant changed files:

``` bash
git diff -- backend/api/models.py backend/api/account_locks.py backend/api/tasks.py
git diff -- orchestrator automation/playwright_engine
```

Do not run test commands that create/modify a test database during a
task explicitly marked read-only.

------------------------------------------------------------------------

## 12. Phase completion criteria

A phase is complete only when:

-   Its approved scope is implemented.
-   Relevant tests actually pass.
-   PostgreSQL-specific guarantees are tested against PostgreSQL.
-   Failure scenarios are covered at the appropriate integration level.
-   Migration state is known.
-   Worktree changes are understood and preserved.
-   Remaining limitations are documented.
-   No out-of-scope work was performed.

Use these status labels:

-   **Not started**
-   **Plan ready**
-   **Awaiting approval**
-   **Implementation in progress**
-   **Implemented --- verification pending**
-   **Conditionally accepted**
-   **Complete**
-   **Blocked**

Current label:

**D1.3 --- Implemented in part; verification pending.**

------------------------------------------------------------------------

## 13. Immediate next action

Do not ask the local model to continue building features yet.

First perform the read-only D1.3 verification described in Section 9.
Then decide whether the current implementation is safe, needs a small
corrective patch, or must be paused for a design issue.

Preserve the current repository state and all uncommitted changes.
