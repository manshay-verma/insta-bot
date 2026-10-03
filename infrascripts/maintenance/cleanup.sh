#!/bin/bash
# cleanup.sh - Generic server maintenance

set -e

echo "Cleaning up dangling Docker images..."
docker image prune -f

echo "Clearing temporary files..."
rm -rf /tmp/*.sql
rm -rf /tmp/*.json

echo "Purging old application logs (> 7 days)..."
find ./logs -name "*.log" -type f -mtime +7 -delete

echo "Cleanup complete!"
