#!/bin/bash
# pg_backup.sh - PostgreSQL backup to local and S3

export PGPASSWORD=${DB_PASSWORD}
BACKUP_NAME="pg_backup_$(date +%Y%m%d_%H%M%S).sql"

echo "Creating local backup..."
pg_dump -h ${DB_HOST:-localhost} -U ${DB_USER:-postgres} ${DB_NAME:-instabot_db} > /tmp/$BACKUP_NAME

if [ -n "$AWS_STORAGE_BUCKET_NAME" ]; then
    echo "Pushing backup to S3..."
    aws s3 cp /tmp/$BACKUP_NAME s3://$AWS_STORAGE_BUCKET_NAME/backups/postgres/$BACKUP_NAME
fi

echo "PostgreSQL backup complete: $BACKUP_NAME"
rm -f /tmp/$BACKUP_NAME
