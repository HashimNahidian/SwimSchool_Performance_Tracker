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
