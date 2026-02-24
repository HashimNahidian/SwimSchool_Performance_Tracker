#!/usr/bin/env sh
set -eu

: "${POSTGRES_USER:?POSTGRES_USER required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}"
: "${POSTGRES_DB:?POSTGRES_DB required}"
: "${POSTGRES_HOST:?POSTGRES_HOST required}"
: "${BACKUP_DIR:=./backups}"

mkdir -p "$BACKUP_DIR"
timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
file="$BACKUP_DIR/propel_eval_$timestamp.sql.gz"

export PGPASSWORD="$POSTGRES_PASSWORD"
pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$file"
echo "Backup written to $file"
