# Production Automation (Playwright, Selenium, etc.)
FROM python:3.11-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements-backend.txt /app/
RUN pip install --no-cache-dir -r /app/requirements-backend.txt
COPY requirements-automation.txt /app/
RUN pip install --no-cache-dir -r requirements-automation.txt
RUN playwright install chromium firefox --with-deps

COPY . /app/
CMD ["python", "orchestrator/bot_worker.py"]
