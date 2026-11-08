# Dependency and configuration review

Docker images install these files:

| Image | Requirements file |
| --- | --- |
| `infradocker/backend.Dockerfile` | `requirements-backend.txt` |
| `infradocker/automation.Dockerfile` | `requirements-backend.txt` then `requirements-automation.txt` |
| `infradocker/spark.Dockerfile` | `requirements-spark.txt` |

`requirements.txt` and `orchestrator/requirements.txt` are not used by those Dockerfiles. `requirements.txt` overlaps the other files and is the only file that listed `beautifulsoup4`. That package has no import in the repository, so it was removed from `requirements.txt`. No other pin was changed.

## Packages that stay

| Package | Where it is required | Why it stays |
| --- | --- | --- |
| Django, DRF, SimpleJWT, spectacular, cors, psycopg, celery, redis, cryptography | `requirements-backend.txt` | API and worker |
| channels, daphne | `requirements-backend.txt` | Installed apps and ASGI route |
| playwright, requests, lxml, pyotp | `requirements-automation.txt` | Live browser and downloader path |
| scrapy, selenium, webdriver-manager, pymongo | `requirements-automation.txt` | Deprecated adapters and the Scrapy Mongo pipeline import them when constructed |
| boto3 | `requirements-automation.txt` and `requirements.txt` | `upload_media_to_s3` imports it when the task runs. It is not in `requirements-backend.txt`. The task now imports `boto3` inside the function so API-process autodiscovery does not crash. |
| Spark Python deps | `requirements-spark.txt` | Only the optional Spark image |

No major versions were bumped.

## Environment variables

Production variables in `backend/config/settings.py` were not removed. That includes `DJANGO_SECRET_KEY`, `DB_*`, `CELERY_*`, `INSTABOT_WORKER_TOKEN`, `INSTABOT_API_URL`, and the `AWS_*` settings. The AWS values are unused by the live job path and are still read by the S3 task.

Runner IPC requires `INSTABOT_RUNNER_IPC_SECRET` at process start (`orchestrator/runner_ipc.py`). Compose does not set it in `docker-compose.yml`. That is an existing operational gap, not an unused variable.

## Compose services

Default services `db`, `redis`, `backend`, `worker`, and `frontend` are required for the documented stack.

| Service | Classification |
| --- | --- |
| `spark-master` | DEPRECATED. Profile `analytics`. No job submitter in this repo. |
| `mongodb`, `node-ws` | DEPRECATED. Profile `optional-data`. Django does not connect to MongoDB. |
| Published ports 5678 and 5679 | KEEP for the current debugpy commands. The worker command still uses `--wait-for-client`. |
| `version: '3.8'` | Removed. Compose ignored it. |

`docker compose config` was run after the version key was removed. It completed without the obsolete-version warning.
