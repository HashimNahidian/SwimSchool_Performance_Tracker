# Propel Swim Academy Evaluation System

Production-oriented full-stack implementation of the Propel Swim Academy role-based evaluation platform.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy + Alembic
- Database: PostgreSQL
- Auth: Access + rotating refresh JWT tokens

## Features Implemented

- Role-based security for `MANAGER`, `SUPERVISOR`, `INSTRUCTOR`
- Manager configuration APIs (users, levels, skills, attributes, templates)
- Supervisor evaluation workflow (draft, update, submit)
- Instructor evaluation access and filtering
- Manager CSV export
- Login rate limiting
- Token refresh + logout revocation
- Structured JSON API logs
- Audit log table (`audit_logs`)
- Health endpoints:
  - `GET /health/live`
  - `GET /health/ready`

## Local Development

1. Start Postgres:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

2. Backend:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

3. Bootstrap first manager (development only):

```http
POST http://127.0.0.1:8000/auth/bootstrap-manager
Content-Type: application/json

{
  "name": "Admin",
  "email": "admin@propel.local",
  "password": "ChangeThis123!",
  "role": "MANAGER",
  "active": true
}
```

4. Frontend:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

## Verified Runbook (Windows)

From repository root:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

Backend terminal:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
copy .env.example .env
alembic upgrade head
uvicorn main:app --reload --port 8000
```

Frontend terminal:

```powershell
cd frontend
npm run dev
```

Checks:
- API live: `http://127.0.0.1:8000/health/live`
- UI: `http://localhost:5173`

If port 8000 is already used:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess
Stop-Process -Id <PID> -Force
```

## Production Deploy (Docker Compose)

1. Create environment file from template:

```powershell
copy infra\.env.prod.example infra\.env.prod
```

2. Set secure values in `infra/.env.prod`:
- strong `SECRET_KEY`
- production `CORS_ORIGINS`
- production `VITE_API_BASE_URL`

3. Deploy:

```powershell
docker compose --env-file infra/.env.prod -f infra/docker-compose.prod.yml up -d --build
```

4. Verify:
- `GET /health/live`
- `GET /health/ready`

## Deployment Runbook (Single School)

This is the minimal production-like runbook for one swim school.

### Environment Variables

| Variable | Required | Example | Notes |
|---|---|---|---|
| `APP_ENV` | yes | `production` | Use `production` outside local dev. |
| `DATABASE_URL` | yes | `postgresql+psycopg2://propel:***@db:5432/propel_eval` | Backend DB connection string. |
| `SECRET_KEY` | yes | long random string | Never use default in production. |
| `CORS_ORIGINS` | yes | `https://app.example.com` | Comma-separated list of allowed frontend origins. |
| `ALLOW_BOOTSTRAP_MANAGER` | yes | `false` | Set `true` only for first-manager bootstrap window. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` | Defaults are acceptable. |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | no | `10080` | Defaults are acceptable. |
| `LOGIN_RATE_LIMIT_COUNT` | no | `8` | Tighten as needed. |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | no | `60` | Tighten as needed. |
| `ENABLE_AUDIT_LOG` | no | `true` | Keep enabled in production. |
| `SMTP_HOST` | no | `smtp.example.com` | If unset, email export returns `501 Email not configured`. |
| `SMTP_PORT` | no | `587` | Used only when SMTP is configured. |
| `SMTP_USERNAME` | no | `mailer-user` | Optional for relays requiring auth. |
| `SMTP_PASSWORD` | no | `mailer-pass` | Optional for relays requiring auth. |
| `SMTP_FROM_EMAIL` | no | `noreply@example.com` | Required for real email sending. |
| `SMTP_USE_TLS` | no | `true` | TLS toggle for SMTP. |
| `VITE_API_BASE_URL` | yes (frontend build) | `https://api.example.com` | Frontend API origin at build time. |

### Bootstrap (First School + First Manager)

1. Run migrations (`alembic upgrade head`).
2. Temporarily set `ALLOW_BOOTSTRAP_MANAGER=true`.
3. Call:

```http
POST /auth/bootstrap-manager
Content-Type: application/json

{
  "name": "School Manager",
  "email": "manager@school.local",
  "password": "ChangeMe123!",
  "role": "MANAGER",
  "active": true
}
```

Behavior:
- If no school exists, backend creates `Default School`.
- It creates the first manager in that school.
- Endpoint rejects additional manager bootstraps.

4. Set `ALLOW_BOOTSTRAP_MANAGER=false` immediately after bootstrap.

### Start Commands (Manual Production-like)

Backend:

```powershell
cd backend
copy .env.example .env
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
copy .env.example .env
npm run build
npm run preview -- --host 0.0.0.0 --port 4173
```

### Smoke Checklist

1. `GET /health/live` and `GET /health/ready` return 200.
2. Manager can log in.
3. Manager can create level and skill.
4. Manager can create template with criteria and ordered `sort_order`.
5. Manager evaluation list works and CSV export works.
6. Email export endpoint:
   - returns `501` if SMTP is unset.
   - returns `200` when SMTP is configured and reachable.

## CI

GitHub Actions workflow at `.github/workflows/ci.yml` runs:
- backend dependency install
- alembic migration check
- backend tests
- frontend build

## Security Notes

- In production set:
  - `APP_ENV=production`
  - `ALLOW_BOOTSTRAP_MANAGER=false`
  - restricted `CORS_ORIGINS`
  - non-default `SECRET_KEY`
- Login endpoint includes basic rate limiting via IP+email key.

## Operations

See `docs/OPERATIONS.md` for:
- backup and restore scripts
- audit logging behavior
- release checklist

## Migrations

- Base schema: `backend/alembic/versions/1b1c9d4f7a21_create_initial_schema.py`
- Security/audit schema: `backend/alembic/versions/5e4c8a2d9f10_add_refresh_tokens_and_audit_logs.py`
