#!/bin/bash
# deploy_all.sh - Orchestrate full stack deployment with zero-downtime attempt

set -e

echo "Pulling latest code..."
git pull origin main

echo "Building containers..."
docker-compose build

echo "Performing database migrations..."
docker-compose run --rm backend python manage.py migrate --no-input

echo "Bringing system live..."
docker-compose up -d

echo "Running health checks..."
./infrascripts/monitor/health_check.sh

echo "Full stack deployment successful!"
