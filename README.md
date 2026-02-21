<<<<<<< HEAD
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

=======
# Propel Swim Eval App

Backend MVP for Propel Swim Academy's role-based instructor evaluation system.

## Stack
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL (Docker compose in `infra/docker-compose.yml`)

## Local Setup
1. Start database:
```powershell
docker compose -f infra/docker-compose.yml up -d
```
2. Create venv and install backend dependencies:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
3. Configure env vars in `backend/.env`:
```env
DATABASE_URL=postgresql+psycopg2://propel:propelpass@localhost:5432/propel_eval
SECRET_KEY=replace-with-a-random-secret
SQL_ECHO=false
ACCESS_TOKEN_EXPIRE_HOURS=8
PASSWORD_HASH_ITERATIONS=390000
ALLOWED_ORIGINS=http://localhost:5173
LOGIN_RATE_LIMIT_MAX_ATTEMPTS=10
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
```
4. Run migrations:
```powershell
cd backend
alembic upgrade head
```
5. Start API:
```powershell
cd backend
uvicorn main:app --reload
```
6. Start frontend:
```powershell
cd frontend
npm install
npm run dev
```
7. Seed demo data (optional but recommended):
```powershell
cd backend
python seed.py
```
8. Run backend tests:
```powershell
cd backend
pytest -q
```

## Containerized Run
Run full stack (db + backend + frontend):
```powershell
docker compose -f infra/docker-compose.app.yml up --build
```

Endpoints:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

For DB-only local mode, keep using:
>>>>>>> origin/main
```powershell
docker compose -f infra/docker-compose.yml up -d
```

<<<<<<< HEAD
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
=======
## Implemented Backend Scope
- Role model: `MANAGER`, `SUPERVISOR`, `INSTRUCTOR`
- Core tables: users, levels, skills, attributes, templates, template_attributes, evaluations, evaluation_ratings, audit_logs
- Role-enforced endpoints for:
  - Manager configuration CRUD (users/levels/skills/attributes/templates)
  - Supervisor draft + submit evaluation flow
  - Instructor evaluation list/detail
  - Manager evaluation listing + CSV export
- Token-based auth (`/auth/login`) with signed bearer token

## Important API Endpoints
- `POST /auth/login`
- `POST /users` (manager-only, includes `password`)
- `GET /instructors` (manager + supervisor)
- `POST /levels`, `PATCH /levels/{id}`, `GET /levels`
- `POST /skills`, `PATCH /skills/{id}`, `GET /skills`
- `POST /attributes`, `PATCH /attributes/{id}`, `GET /attributes`
- `POST /templates`, `PATCH /templates/{id}`, `GET /templates`
- `POST /evaluations/draft`
- `PATCH /evaluations/{id}/draft`
- `POST /evaluations/{id}/submit`
- `GET /evaluations/{id}`
- `GET /me/evaluations`
- `GET /manager/evaluations`
- `GET /supervisor/evaluations`
- `GET /supervisors`
- `GET /me/evaluations/trends`
- `GET /exports/evaluations.csv`

Evaluation listing/export query options:
- Filters: `date_from`, `date_to`, `level_id`, `skill_id`, `supervisor_id`, `instructor_id`, `status`
- Pagination: `limit`, `offset` (list endpoints)
- Sorting: `sort_by` in (`id`, `created_at`, `session_date`, `submitted_at`, `status`) and `sort_dir` in (`asc`, `desc`)

## Notes
- Frontend now includes a functional MVP for manager/supervisor/instructor flows.
- Manager UI supports activate/deactivate controls for levels, skills, attributes, and templates.
- `POST /auth/login` requires `email` + `password`.
- Seeded login emails: `manager@propel.local`, `supervisor@propel.local`, `instructor1@propel.local`, `instructor2@propel.local`
- Seeded password for all users: `Propel123!`
- CI workflow is configured at `.github/workflows/ci.yml` and runs backend tests + frontend build on push/PR.
>>>>>>> origin/main
