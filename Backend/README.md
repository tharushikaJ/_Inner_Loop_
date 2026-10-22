# InnerLoop Backend

FastAPI backend for the InnerLoop platform. Authentication uses the existing
PostgreSQL `users` table, bcrypt password hashes, and JWT access tokens stored
in HttpOnly cookies.

## Local development

Create `Backend/.env` from `.env.example`. When PostgreSQL is exposed to the
host, keep `localhost:5432` in `DATABASE_URL`.

From `Backend/` on Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell activation is restricted, activation is optional:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- Health check: `http://localhost:8000/health`
- OpenAPI documentation: `http://localhost:8000/docs`

## Database migrations

Docker Compose runs the checked-in SQL migrations before starting the backend.
For a backend running directly on the host, set `DATABASE_URL` to the host
PostgreSQL connection and run:

```powershell
.\.venv\Scripts\python.exe -m app.migrate
```

## Authentication endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

## Role-based endpoints

All endpoints below resolve the authenticated user from the signed HttpOnly
cookie. Project and task queries are restricted to direct/pod assignments for
interns.

- All roles: `GET /api/dashboard`, `GET /api/projects`, `GET /api/tasks`
- Employee and management: `GET /api/meetings`, `GET /api/meeting-rooms`,
  `GET /api/reports/summary`
- Management only: `GET /api/users`, `GET /api/settings`,
  `GET /api/audit-logs`

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
