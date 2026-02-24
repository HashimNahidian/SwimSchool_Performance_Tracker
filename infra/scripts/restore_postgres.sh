#!/usr/bin/env sh
set -eu

: "${POSTGRES_USER:?POSTGRES_USER required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}"
: "${POSTGRES_DB:?POSTGRES_DB required}"
: "${POSTGRES_HOST:?POSTGRES_HOST required}"
: "${BACKUP_FILE:?BACKUP_FILE required}"

export PGPASSWORD="$POSTGRES_PASSWORD"
gunzip -c "$BACKUP_FILE" | psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "Restore completed from $BACKUP_FILE"
