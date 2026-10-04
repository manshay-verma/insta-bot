# Production Backend Dockerfile
FROM python:3.11-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements-backend.txt /app/
RUN pip install --no-cache-dir -r /app/requirements-backend.txt

WORKDIR /app/backend
COPY . /app/
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
