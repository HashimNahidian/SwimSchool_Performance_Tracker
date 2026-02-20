# Operations Runbook

## Health Checks

- Liveness: `GET /health/live`
- Readiness: `GET /health/ready`

## Logging

- API logs are structured JSON to stdout.
- Each request log includes method, path, status, duration, and client IP.

## Audit Logging

- API requests are written to `audit_logs`.
- To reduce write load (non-production), set `ENABLE_AUDIT_LOG=false`.

## Database Backups

1. Set environment variables:
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `POSTGRES_DB`
   - `POSTGRES_HOST`
2. Run backup script:

```sh
sh infra/scripts/backup_postgres.sh
```

3. Verify backup file exists in `./backups` (or `BACKUP_DIR` if configured).

## Restore Test

1. Set the same DB variables as backup.
2. Set `BACKUP_FILE=/path/to/file.sql.gz`.
3. Run:

```sh
sh infra/scripts/restore_postgres.sh
```

## Release Checklist

- `alembic upgrade head` applied successfully.
- CI pipeline green.
- `ALLOW_BOOTSTRAP_MANAGER=false` in production.
- `SECRET_KEY` rotated and stored in secret manager.
- `CORS_ORIGINS` limited to deployed frontend domain.
