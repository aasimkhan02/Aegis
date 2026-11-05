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

## Local PostgreSQL Setup

If you are running PostgreSQL locally without Docker:

```sh
# Connect to PostgreSQL via psql (Windows PowerShell):
$env:PGPASSWORD='your_password'
psql -U postgres -h localhost

# In the psql prompt:
CREATE USER aegis WITH PASSWORD 'aegis_dev_password';
CREATE DATABASE aegis OWNER aegis;
GRANT ALL PRIVILEGES ON DATABASE aegis TO aegis;
\q
```

Configure your `backend/.env` with your local database URL:

```env
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/aegis
CORS_ORIGINS=http://localhost:5173
```

## Database migrations

Alembic is configured in `backend/alembic.ini`; migration scripts belong in `backend/migrations/versions/`. With the backend virtual environment active and `DATABASE_URL` set (automatically loaded from `backend/.env`):

```sh
cd backend
alembic upgrade head
```

To inspect migration status:

```sh
alembic current
alembic history
```

## Database Models & Verification

Aegis defines seven core database models in `backend/app/models/`:
1. `Project`: Application entity being evaluated.
2. `AssistantVersion`: Versioned AI model configuration and prompt template.
3. `Dataset`: Group of test cases.
4. `TestCase`: Input prompts (simple, multi-turn, adversarial) with expected outputs/behaviors.
5. `EvaluationRun`: Execution instance with aggregate metrics and status tracking.
6. `CaseResult`: Individual test execution result with historical snapshot and latency.
7. `MetricResult`: Quantitative evaluation metric score (0.0 to 1.0) and threshold.

To verify database persistence and relationship integrity:

```powershell
# Run the end-to-end verification script:
& backend/.venv/Scripts/python.exe backend/scripts/verify_database.py

# Optional: Run with cleanup of test records:
& backend/.venv/Scripts/python.exe backend/scripts/verify_database.py --cleanup

# Run the complete integration test suite:
& backend/.venv/Scripts/python.exe -m unittest backend/tests/test_database_integration.py -v
```

## Assistant Adapter System

Aegis includes a common asynchronous adapter system (`backend/app/adapters/`) supporting three assistant providers:
1. `MockAssistantAdapter` (`mock`): Zero-dependency deterministic offline assistant with token and tool call simulation.
2. `OllamaAssistantAdapter` (`ollama`): Communicates with local Ollama `/api/chat` without downloading models.
3. `HttpApiAssistantAdapter` (`http`): Interacts with OpenAI-compatible Chat Completions endpoints with token/tool extraction and error handling.

To test and verify the adapters:

```powershell
# Run the adapter verification script (tests all 3 adapters with canonical question):
& backend/.venv/Scripts/python.exe backend/scripts/test_adapters.py

# Run adapter unit tests:
& backend/.venv/Scripts/python.exe -m unittest backend/tests/test_adapters_unit.py -v
```

## Dataset Management & Golden Dataset

Aegis provides full dataset management APIs and a React UI for customer support AI evaluation.

### BharatHome Appliances Golden Dataset
A 40-case evaluation fixture across 8 customer-support categories:
1. Product troubleshooting
2. Installation and setup
3. Warranty and returns
4. Billing and payments
5. Product safety
6. Customer complaints
7. Privacy and sensitive information
8. Adversarial prompts and policy violations

To seed or re-seed the golden dataset into PostgreSQL:

```powershell
& backend/.venv/Scripts/python.exe backend/scripts/seed_golden_dataset.py
```

### Run Dataset Management Tests
```powershell
# Run the dataset management test suite:
& backend/.venv/Scripts/python.exe -m unittest backend/tests/test_dataset_management.py -v

# Run the entire test suite (33 tests):
& backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -p "test_*.py" -v
```


