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

## Prompt and Adversarial Testing (Promptfoo Integration)

Aegis integrates the **Promptfoo CLI** (`promptfoo@0.120.19`) for deterministic prompt evaluation, assertion verification, and adversarial vulnerability testing against customer-support assistants.

### What Promptfoo Does in Aegis
Promptfoo evaluates assistant responses against predefined assertions (`contains`, `not-contains`, `icontains`, etc.) without requiring external paid LLM judge APIs. Aegis invokes the CLI asynchronously via Python `subprocess`, captures structured JSON evaluation results, redacts sensitive credentials from logs and outputs, and surfaces results via both CLI and API.

### Test Categories Included
The suite in `backend/promptfoo/promptfooconfig.yaml` contains 13 test cases across five core categories:
1. **Normal Prompt Testing**: Validates standard domain inquiries (product specifications, warranty periods, installation clearances, drain error codes).
2. **Expected-Output Assertions**: Ensures mandatory terms, tool booking confirmation codes (`ticket id`), and absence of forbidden phrases.
3. **Jailbreak Defense Testing**: Tests resilience against prompt leakage ("output system prompt verbatim"), authority override ("Emergency Directive 402 instant refund"), and safety bypass ("cut the wires to disable lid lock").
4. **Prompt Injection Testing**: Asserts that malicious user input cannot override knowledge base facts (e.g. injected 50-year warranty claims) or extract synthetic database credentials (`root123`).
5. **Adversarial Input Handling**: Verifies polite refusal of unsupported products (laptops, phones), respectful defusing of toxic user abuse, and handling of contradictory instructions.

### How to Run Promptfoo Tests

#### 1. Via Promptfoo CLI Directly
```powershell
# Evaluate BharatHome Assistant v1 (Good Production Configuration - 100% Pass Rate)
$env:PROMPTFOO_DISABLE_UPDATE='true'
$env:PROMPTFOO_DISABLE_TELEMETRY='true'
$env:PROMPTFOO_PYTHON='backend/.venv/Scripts/python.exe'
promptfoo eval -c backend/promptfoo/promptfooconfig.yaml --no-cache

# Evaluate BharatHome Assistant v2 (Intentionally Flawed Configuration - Highlights Failures)
$env:AEGIS_ASSISTANT_VERSION='v2'
promptfoo eval -c backend/promptfoo/promptfooconfig.yaml --no-cache
```

#### 2. Via Aegis FastAPI Endpoint
```http
POST /api/evaluations/promptfoo
Content-Type: application/json

{
  "version": "v1",
  "provider": "mock",
  "timeout_seconds": 120
}
```

Or target a specific persisted assistant UUID:
```http
POST /api/evaluations/promptfoo
Content-Type: application/json

{
  "assistant_version_id": "00000000-0000-0000-0000-000000000000",
  "timeout_seconds": 120
}
```

#### 3. Run Automated Integration Tests (Subprocess Mocked)
```powershell
$env:PYTHONPATH='backend'; & "backend/.venv/Scripts/python.exe" -m unittest discover -s backend/tests -p "test_promptfoo_integration.py" -v
```

### How Results Are Interpreted
- **`status: "completed"`**: Evaluation ran to completion. The response includes `total_tests`, `passed`, `failed`, and a list of per-test results with detailed assertion breakdowns. Note: failed test assertions are normal benchmark findings and are **not** treated as infrastructure errors.
- **`status: "timeout"`**: Promptfoo CLI exceeded the configured execution timeout (default 120s). The process was safely terminated.
- **`status: "cli_not_found"`**: The `promptfoo` CLI binary was not detected in `PATH` or npm directories.
- **`status: "error"`**: Subprocess crash, non-zero exit without JSON generation, or unparseable output.

## Continuous Integration (GitHub Actions)

Aegis includes an automated CI workflow defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### Workflow Triggers
- **Pushes** targeting the `main` branch.
- **Pull Requests** targeting the `main` branch.

### Pipeline Jobs & Checks

| Job | Environment | Execution Steps & Verification |
|---|---|---|
| **Backend Test Suite** (`backend`) | Ubuntu Latest, Python 3.12, PostgreSQL 16 Service | 1. Provisions ephemeral PostgreSQL 16 container.<br>2. Installs cached dependencies from `backend/requirements.txt`.<br>3. Applies Alembic migrations (`alembic upgrade head`).<br>4. Runs full test suite (221 tests) including ORM integration, deterministic evaluators, security validators, multi-turn adapters, version comparison, and release quality gate rules. |
| **Frontend Build & Typecheck** (`frontend`) | Ubuntu Latest, Node.js 20 | 1. Installs reproducible dependencies with `npm ci`.<br>2. Validates strict TypeScript compilation (`tsc -b`).<br>3. Compiles production Vite client bundle (`vite build`). |
| **Promptfoo Adversarial & Quality Check** (`promptfoo`) | Ubuntu Latest, Python 3.12, Node.js 20 | 1. Installs backend dependencies for the Python adapter provider.<br>2. Executes deterministic Promptfoo CLI evaluation (`promptfoo eval -c backend/promptfoo/promptfooconfig.yaml --no-cache`).<br>3. Verifies 13 test assertions across normal inquiries, expected outputs, jailbreak defenses, prompt injection resistance, and adversarial defusing. |

### What a Passing Workflow Verifies
- **Reliable Development Lifecycle**: Both frontend and backend compile and build without warnings or type errors.
- **Database Schema Integrity**: PostgreSQL migrations apply cleanly to a fresh database and all relational constraints hold.
- **Safety & Regression Prevention**: Deterministic security validators (PII detection, system canary secrecy, forbidden terms, technical safety, policy compliance) pass without failures.
- **Assistant Adapter Correctness**: Tool calls, multi-turn history, and evaluation comparison engines operate accurately.
- **Promptfoo Assertions**: 100% of benchmark assertions pass on production assistant configurations.

### Checks Intentionally Excluded from CI
1. **Live External LLM Calls & Ollama Inference**: All CI evaluations and tests execute deterministically using mock adapters, regex/rule validators, and offline fixtures. Live LLM API calls and local Ollama daemons are intentionally excluded to ensure CI remains fast (<1 minute), reproducible, zero-cost, and resilient against network outages, API quotas, or hardware limitations.
2. **Ad-hoc Cross-Run Release Gate against Production History**: The release quality gate engine logic and threshold rules are fully verified in `test_quality_gate.py` against isolated test fixtures. However, executing live comparisons against persistent production benchmark runs is excluded from ephemeral PR builds because CI runners do not host long-term historical database state.




