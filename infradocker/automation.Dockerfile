FROM python:3.11-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY requirements-backend.txt /app/
RUN pip install --no-cache-dir -r /app/requirements-backend.txt
COPY requirements-automation.txt /app/
RUN pip install --no-cache-dir -r /app/requirements-automation.txt
RUN playwright install chromium firefox --with-deps

COPY . /app/
WORKDIR /app/backend
RUN useradd --create-home appuser && chown -R appuser:appuser /app /ms-playwright
USER appuser

HEALTHCHECK --interval=60s --timeout=30s --start-period=60s --retries=3 \
  CMD ["python", "/app/infradocker/worker_healthcheck.py"]
CMD ["celery", "-A", "config", "worker", "--loglevel=info"]
