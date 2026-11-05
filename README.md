# Aegis

Aegis is a lightweight foundation for an LLM Quality & Security Testing Platform. This starter includes a React dashboard shell, a FastAPI health endpoint, PostgreSQL, SQLAlchemy, and Alembic. It does not yet implement evaluation or security testing functionality.

## Requirements

- Docker Desktop with Docker Compose (full stack)
- Node.js 20+ and npm (frontend standalone)
- Python 3.12+ and pip (backend standalone; Python 3.12 is used in Docker)
- PostgreSQL 16 (backend standalone, unless using the Compose database)

## Start the full stack

From the repository root:

```sh
cp .env.example .env
docker compose up --build
```

On PowerShell, use `Copy-Item .env.example .env` in place of `cp`. The dashboard is at http://localhost:5173, the API at http://localhost:8000, and the health check at http://localhost:8000/health. Stop with `Ctrl+C`, or run `docker compose down`. PostgreSQL data persists in the `postgres_data` volume.

## Run the frontend independently

```sh
cd frontend
npm install
Copy-Item .env.example .env.local  # PowerShell; use cp .env.example .env.local on macOS/Linux
npm run dev
```

The Vite development server uses `VITE_API_BASE_URL` from `frontend/.env.local` (defaults to `http://localhost:8000`). Build with `npm run build`.

## Run the backend independently

Start PostgreSQL first, either with `docker compose up -d db` from the root or a local PostgreSQL 16 installation. Then:

```sh
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1       # PowerShell; use source .venv/bin/activate on macOS/Linux
python -m pip install -r requirements.txt
Copy-Item .env.example .env       # PowerShell; use cp .env.example .env on macOS/Linux
uvicorn app.main:app --reload
```

Set the environment before launching the backend. In PowerShell, after copying the backend example file, run `$env:DATABASE_URL = (Get-Content .env | Where-Object { $_ -match '^DATABASE_URL=' }) -replace '^DATABASE_URL=', ''` and `$env:CORS_ORIGINS = 'http://localhost:5173'`. On macOS/Linux, use `set -a; . ./.env; set +a`. Update the example URL to match your local PostgreSQL credentials. The backend reads `DATABASE_URL` and comma-separated `CORS_ORIGINS` from its environment. The health endpoint does not require a database connection. API docs are available at http://localhost:8000/docs.

## Database migrations

Alembic is configured in `backend/alembic.ini`; migration scripts belong in `backend/migrations/versions/`. With the backend virtual environment active and `DATABASE_URL` set:

```sh
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

No database tables are defined yet. The SQLAlchemy engine and declarative base are ready for models.
