#!/bin/bash
# health_check.sh - Simple service diagnostics

set -e

echo "--- System Status Report ---"

echo "Checking Django API..."
curl -f http://localhost:8000/api/v1/health/ || echo "Backend is UNSTABLE!"

echo "Checking React Frontend..."
curl -f http://localhost:5173/ || echo "Frontend is UNSTABLE!"

echo "Checking Docker containers..."
docker ps --format "{{.Names}}: {{.Status}}"

echo "Checking disk usage..."
df -h / | tail -1

echo "Monitoring complete!"
