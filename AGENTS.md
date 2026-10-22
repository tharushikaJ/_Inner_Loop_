# AGENTS.md

## Project overview

InnerLoop is an internal Digital Lab platform for project, task, meeting, reporting, room, and user management. The repository is organized as a small full-stack system:

- `Frontend/`: React 18 + Vite 7 single-page application.
- `Backend/`: FastAPI + SQLAlchemy backend scaffold.
- `Databases/`: PostgreSQL schema and development seed assets.
- `docker-compose.yml`: local orchestration for frontend, backend, and PostgreSQL.

Read the closest `AGENTS.md` before editing if more scoped guidance files are added later. Instructions in a nearer file override this root file.

## Current implementation status

Do not infer functionality from filenames alone. Much of the repository is planned scaffolding:

- The main workspace frontend remains in `Frontend/src/App.jsx` and `Frontend/src/index.css`.
- `Frontend/src/main.jsx` mounts `App` inside `BrowserRouter` and `AuthProvider`.
- Authentication and RBAC are implemented in `Frontend/src/api/`, `context/AuthContext.jsx`, `components/ProtectedRoute.jsx`, `components/RoleProtectedRoute.jsx`, and the login/register/profile/workspace routes.
- The backend implements `GET /health`, the `/api/auth` flow, role-aware dashboard/project/task APIs, employee/management operational APIs, and management-only administration APIs.
- Authentication uses the existing PostgreSQL `users` table, bcrypt password hashes, JWTs in HttpOnly cookies, and environment-configured CORS. RBAC resolves the current user from that cookie and filters intern projects/tasks in SQL through direct task assignments.
- `Databases/schema.sql` is the only complete database definition. `Databases/seed/seed.sql` is a placeholder.
- Backend authentication and RBAC behavior is covered by the pytest suite in `Backend/tests/`. There is no configured frontend linter at present.

When implementing a feature, wire every layer that the request actually requires. Do not report a placeholder module as implemented.

## Repository map

```text
InnerLoop/
|-- Frontend/
|   |-- src/
|   |   |-- App.jsx          # Current routes, layout, and UI implementation
|   |   |-- index.css        # Tailwind import and custom component/theme styles
|   |   |-- main.jsx         # React entry point, BrowserRouter, and AuthProvider
|   |   |-- api/             # API clients; authentication client is implemented
|   |   |-- components/      # Shared brand and protected-route components
|   |   |-- context/         # Authentication state and application context
|   |   |-- pages/           # Login, registration, profile, and planned feature pages
|   |   `-- utils/           # Planned formatting and role/status helpers
|   |-- package.json
|   |-- vite.config.js
|   `-- Dockerfile           # Builds Vite assets and serves them with nginx
|-- Backend/
|   |-- app/
|   |   |-- main.py          # FastAPI application entry point
|   |   |-- config.py        # Pydantic settings loaded from .env
|   |   |-- database.py      # SQLAlchemy engine, session factory, and Base
|   |   |-- routes/          # Planned HTTP routers
|   |   |-- services/        # Planned business logic
|   |   |-- models/          # Planned SQLAlchemy models
|   |   |-- schemas/         # Planned Pydantic request/response schemas
|   |   `-- utils/           # Planned security/export/permission helpers
|   |-- requirements.txt
|   `-- Dockerfile
|-- Databases/
|   |-- schema.sql           # PostgreSQL source schema
|   `-- seed/seed.sql        # Development seed placeholder
|-- docker-compose.yml
`-- README.md
```

## Frontend conventions

- Use JavaScript and JSX; the project is not configured for TypeScript.
- Keep `BrowserRouter` in `src/main.jsx`. Components that use `Routes`, `Link`, or `useLocation` require it.
- Tailwind CSS v4 is enabled through `@tailwindcss/vite` and `@import "tailwindcss"` in `src/index.css`.
- The current design language is a white-first interface with navy text, blue (`#075fae`/`#0871c6`) and green (`#20b51d`) accents, rounded surfaces, and responsive layouts.
- Use `lucide-react` for interface icons instead of adding another icon library.
- Preserve responsive behavior at mobile, tablet, and desktop widths. The sidebar becomes an overlay below the `lg` breakpoint.
- Use semantic interactive elements: buttons for actions, links for navigation, labels for form controls, and useful `aria-label` text for icon-only controls.
- Prefer extracting reusable UI into `src/components/` as new features grow. The current monolithic `App.jsx` is the working baseline, not a requirement for future code.
- Put backend calls behind modules in `src/api/`; do not scatter fetch logic through presentation components.
- Do not add hard-coded production secrets, tokens, or user credentials to frontend code.

### Frontend commands

Run from `Frontend/`:

```bash
npm install
npm run dev
npm run build
npm run preview
```

On Windows PowerShell systems that block `npm.ps1`, use `npm.cmd` in place of `npm`, for example `npm.cmd run build`.

Before completing a frontend change, run `npm run build` (or `npm.cmd run build`) and fix all compile errors.

## Backend conventions

- Target Python 3.11, as specified by `Backend/Dockerfile`.
- Use FastAPI routers for HTTP concerns, service modules for business rules, SQLAlchemy models for persistence, and Pydantic schemas for validation and serialization.
- Register new routers in `Backend/app/main.py`; creating a file in `routes/` alone does not expose an endpoint.
- Obtain database sessions through `SessionLocal` and close them reliably, preferably through a FastAPI dependency.
- Keep environment-driven configuration in `Backend/app/config.py` using `pydantic-settings`.
- Follow Python naming conventions: `snake_case` functions/modules/fields and `PascalCase` classes.
- Return explicit response models and appropriate HTTP status codes. Validate authorization in the backend, not only in the UI.
- Hash passwords and sign JWTs through dedicated security helpers. Never store or log plaintext passwords or tokens.
- Avoid creating tables implicitly at application startup when a migration or schema change is more appropriate.

### Backend local commands

From `Backend/`, create and activate a virtual environment, then run:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend health check is `GET http://localhost:8000/health`.

## Database conventions

- PostgreSQL 15 is used by Docker Compose.
- Treat `Databases/schema.sql` as the current schema source of truth until Alembic migrations are implemented.
- Preserve existing foreign keys, uniqueness constraints, time-range checks, cascading behavior, and indexes when changing related tables.
- Use `BIGINT`-compatible identifiers across SQL, SQLAlchemy, Pydantic schemas, and frontend API payloads.
- Use PostgreSQL-friendly `snake_case` names.
- Schema changes should be reflected consistently in SQL, backend models, schemas, services, API contracts, and relevant frontend forms.
- Keep development-only data in `Databases/seed/seed.sql`. Do not place secrets or real personal data in seed files.

## Environment and Docker

The backend expects `Backend/.env` with values equivalent to:

```env
DATABASE_URL=postgresql://innerloop_user:innerloop_password@postgres:5432/innerloop_db
JWT_SECRET=change-me
JWT_ALGORITHM=HS256
```

- Use host `postgres` when the backend runs in Docker Compose.
- Use host `localhost` when FastAPI runs directly on the host against the Dockerized database.
- Never commit `Backend/.env`; it is ignored by Git.
- Replace the example JWT secret outside local development.

From the repository root:

```bash
docker compose up --build
docker compose ps
docker compose logs -f
docker compose down
```

Services are exposed at:

- Frontend via Docker: `http://localhost:3000`
- Frontend via Vite: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

`docker compose down -v` deletes the named PostgreSQL data volume. Do not run it unless the user explicitly wants local database data removed.

## Change and verification guidelines

- Inspect existing files before editing; several files are intentionally empty scaffolds.
- Keep changes scoped to the requested feature and preserve unrelated user modifications.
- Update documentation when setup steps, environment variables, ports, or architecture change.
- For frontend work, run the production build and exercise the affected route when browser access is available.
- For backend work, at minimum import/start the FastAPI app and check `/health`; add focused tests when implementing non-trivial behavior.
- For database work, review the complete dependency chain of affected foreign keys and constraints before applying destructive changes.
- Do not claim end-to-end integration unless the frontend, API route registration, service/model/schema layers, and database contract are all connected and verified.

## Safety boundaries

- Do not commit secrets, `.env` files, access tokens, generated exports, `node_modules/`, Python virtual environments, or build output.
- Do not reset, drop, truncate, or remove database volumes without explicit user authorization.
- Do not overwrite unrelated work in this repository. A dirty worktree may contain deliberate user changes.
- Prefer additive, reversible migrations and narrowly scoped edits.
