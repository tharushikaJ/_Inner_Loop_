# InnerLoop

Internal Project, Meeting, and Resource Management Platform for Digital Lab.

## Docker Setup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git installed if cloning the repository

### 1. Configure the backend environment

From the repository root, create `Backend/.env` with the following values:

```env
DATABASE_URL=
JWT_SECRET=
JWT_ALGORITHM=
MICROSOFT_TENANT_ID=
MICROSOFT_CLIENT_ID=
```

For shared or production environments, replace `JWT_SECRET` with a long, random secret and do not commit the `.env` file.

The database host depends on where the backend runs:

- Docker Compose backend: use `postgres:5432` as shown above. Docker resolves `postgres` to the PostgreSQL service.
- FastAPI running directly on Windows: use `localhost:5432`, because PostgreSQL is published from the container to the host.

For a direct local run, change only the database host in `Backend/.env` to:

```env
DATABASE_URL=
```

Restore `postgres:5432` before starting the backend with Docker Compose.

### Microsoft sign-in

The login page includes Microsoft Entra ID sign-in for the configured SLT tenant.
The Microsoft account must belong to the configured SLT tenant and already exist
as an active InnerLoop user; roles are still managed by InnerLoop and are not
taken from Microsoft claims.

In the Entra app registration, configure the application as a **Single-page
application** and add these redirect URIs:

- `https://innerloop.raccoon-ai.io`
- `http://localhost:5173` for local Vite development
- `http://localhost:3000` for the local Docker frontend

Set the matching frontend values in `Frontend/.env`:

```env
VITE_MICROSOFT_TENANT_ID=
VITE_MICROSOFT_CLIENT_ID=
```

The app defaults its Microsoft redirect URI to the page's current origin. This
works for both Vite (`http://localhost:5173`) and the Docker frontend
(`http://localhost:3000`) without changing the file. Set
`VITE_MICROSOFT_REDIRECT_URI` only when an explicit redirect URI is required,
and ensure that exact URI is registered in Entra ID.

The frontend also defaults API requests to `/api`, which works through the Vite
and nginx proxies. Set `VITE_API_BASE_URL` only when the API is deliberately
hosted on a separate origin. For that setup, include the deployed frontend
origin in `CORS_ORIGINS` in `Backend/.env`. No Microsoft client secret is
required for this SPA flow.

### 2. Build and start the services

Run this command from the directory containing `docker-compose.yml`:

```bash
docker compose up --build
```

To start the services in the background:

```bash
docker compose up --build -d
```

The first build downloads the required dependencies and may take a few minutes.

### 3. Access the application

Once the containers are running, use:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API health check: http://localhost:8000/health
- PostgreSQL: `localhost:5432`

### Docker commands

```bash
# View running containers
docker compose ps

# Follow service logs
docker compose logs -f

# Stop the services
docker compose down

# Stop the services and remove the PostgreSQL data volume
docker compose down -v
```

The PostgreSQL data is stored in the named Docker volume `innerloop_postgres_data` and is preserved when using `docker compose down`. Use `docker compose down -v` only when you want to delete the local database data.

## Data persistence

InnerLoop stores application records in PostgreSQL through the FastAPI API. The
React frontend does not use browser persistence APIs such as Web Storage or
IndexedDB. React component state is transient display/form state and is rebuilt
from the API after a page reload.

Authentication uses a signed JWT in a secure HttpOnly cookie. The cookie is an
authentication credential only; application records are not stored in it.

To enforce the browser-storage rule, run this from `Frontend/`:

```bash
npm run check:no-browser-storage
```

## Structure

- `Frontend/` — React + Vite application scaffold
- `Backend/` — FastAPI application scaffold
- `Databases/` — PostgreSQL schema/migration assets
- `docker-compose.yml` — Frontend, backend, and PostgreSQL deployment scaffold

The structure follows the InnerLoop Project Proposal dated 14 September 2026.
