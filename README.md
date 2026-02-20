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
- `POST /users` (manager-only)
- `GET /instructors` (manager + supervisor)
- `POST /levels`, `PATCH /levels/{id}`, `GET /levels`
- `POST /skills`, `PATCH /skills/{id}`, `GET /skills`
- `POST /attributes`, `PATCH /attributes/{id}`, `GET /attributes`
- `POST /templates`, `GET /templates`
- `POST /evaluations/draft`
- `PATCH /evaluations/{id}/draft`
- `POST /evaluations/{id}/submit`
- `GET /evaluations/{id}`
- `GET /me/evaluations`
- `GET /manager/evaluations`
- `GET /supervisor/evaluations`
- `GET /exports/evaluations.csv`

## Notes
- Frontend now includes a functional MVP for manager/supervisor/instructor flows.
- `POST /auth/login` uses email-only identity for MVP bootstrap. Add password hashing + secure auth provider before production.
- Seeded login emails: `manager@propel.local`, `supervisor@propel.local`, `instructor1@propel.local`, `instructor2@propel.local`
