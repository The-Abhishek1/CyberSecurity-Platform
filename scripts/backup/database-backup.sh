#!/bin/bash
# scripts/backup/database-backup.sh

set -e

# Configuration
BACKUP_DIR="/backups/postgres"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/orchestrator_${DATE}.sql.gz"
S3_BUCKET="s3://security-orchestrator-backups"

# Create backup directory
mkdir -p $BACKUP_DIR

echo "Starting database backup at $(date)"

# Perform backup
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
    -h $POSTGRES_HOST \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    --format=custom \
    --verbose \
    --no-owner \
    --no-privileges | gzip > $BACKUP_FILE

# Check backup size
BACKUP_SIZE=$(du -h $BACKUP_FILE | cut -f1)
echo "Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"

# Upload to S3
aws s3 cp $BACKUP_FILE $S3_BUCKET/production/database/

# Upload to DR region
aws s3 cp $BACKUP_FILE $S3_BUCKET/dr/database/ --region eu-west-1

# Verify backup
aws s3 ls $S3_BUCKET/production/database/$(basename $BACKUP_FILE)

# Cleanup old backups locally
find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully at $(date)"

# Send notification
curl -X POST -H "Content-Type: application/json" \
    -d "{\"text\": \"Database backup completed: $BACKUP_FILE ($BACKUP_SIZE)\"}" \
    $SLACK_WEBHOOK_URL