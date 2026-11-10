# Aegis — AI Assistant Quality, Regression & Security Evaluation Platform

Aegis is an automated evaluation platform designed to benchmark, protect, and quality-gate conversational AI assistants before production release.

Evaluating LLMs requires more than checking whether a response "looks good." Modern AI assistants generate probabilistic responses, maintain multi-turn dialogue context, invoke external tools, and face prompt injections, data leakage, and unintended behavioral regressions across prompt or model updates. Aegis provides an end-to-end framework combining **deterministic zero-cost checks**, **security validators**, **prompt & adversarial assertions**, **assistant version comparisons**, and **automated release quality gates** with a real-time web dashboard.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph UI ["Frontend (React 19 + TypeScript + Vite)"]
        Dash["Overview Dashboard"]
        Datasets["Golden Datasets & Test Cases"]
        Runs["Evaluation Execution & Inspector"]
        Security["Security Intelligence Dashboard"]
        Compare["Version Comparison"]
        Gate["Release Quality Gate"]
        SettingsUI["System Settings"]
    end

    subgraph API ["Backend API (FastAPI)"]
        ProjectsRoute["/api/projects"]
        AssistantsRoute["/api/assistants"]
        DatasetsRoute["/api/datasets"]
        EvalsRoute["/api/evaluations"]
        SecurityRoute["/api/dashboard/security"]
        CompareRoute["/api/evaluations/compare"]
        GateRoute["/api/evaluations/release-gate"]
    end

    subgraph Core ["Evaluation Engine & Adapters"]
        Executor["Evaluation Context & Execution Worker"]
        
        subgraph Adapters ["Assistant Adapter Layer"]
            MockAdapter["Mock Assistant Adapter (Zero-Cost Offline)"]
            HttpAdapter["OpenAI-Compatible Chat Completions"]
            OllamaAdapter["Local Ollama Adapter"]
        end

        subgraph Evaluators ["Evaluation Engines"]
            Deterministic["Deterministic Evaluators (Exact, Contains, Levenshtein)"]
            SecurityEngine["Deterministic Security Validators (PII, Canary, Escapes, Policy)"]
            PromptfooEngine["Promptfoo CLI (Adversarial, Jailbreak & Injection Testing)"]
            DeepEvalEngine["DeepEval (Optional Model Judge: Faithfulness, Hallucination)"]
            RagasEngine["Ragas (Optional Model Judge: Context Precision, Recall)"]
        end
    end

    subgraph Storage ["Persistence Layer (PostgreSQL 16 + SQLAlchemy)"]
        M1[("Projects & AssistantVersions")]
        M2[("Golden Datasets & TestCases")]
        M3[("EvaluationRuns & CaseResults")]
        M4[("MetricResults & Diagnostic Details")]
    end

    UI -->|REST API / JSON| API
    API --> Core
    Core --> Storage
    API --> Storage
```

### End-to-End Evaluation Flow
1. **Dataset Ingestion**: Curate or import golden test cases containing prompts, ground truth, retrieval context, and validation tags.
2. **Execution Worker**: Asynchronously dispatches test cases against target assistant versions (mock, local, or HTTP providers) with configurable worker concurrency and fail-fast options.
3. **Multi-Engine Evaluation**: Runs deterministic string/regex checks, security validators, and optional model judges against model outputs.
4. **Relational Persistence**: Captures latency, prompt snapshots, output texts, metric scores, and pass/fail states in PostgreSQL.
5. **Comparison & Quality Gating**: Analyzes deltas between candidate and baseline runs, surfaces regressions, and enforces automated release decisions.

---

## Key Capabilities

### 1. Golden Dataset Management
- Centralized test suites with multi-category test cases.
- Comprehensive test case schemas: user messages, expected outputs, retrieval context, ground-truth context, tags, and metadata.
- Full JSON import/export and batch enable/disable toggle.
- Bundled **BharatHome Customer Support** golden dataset (40 real-world appliance support test cases across 8 categories).

### 2. Deterministic Zero-Cost Evaluation
- Zero latency, zero external API costs, and 100% reproducible test execution.
- Evaluators include Exact Match, Case-Insensitive Token Containment, Forbidden Lexicons, and Levenshtein Normalized Similarity.

### 3. Lightweight Security Validators
Fast, deterministic Python security checks that operate without downloading LLM weights or calling external services:
- **PII Detection**: Detects email addresses, Indian mobile numbers (`+91`, `0`, or 10-digit formats), and Aadhaar patterns.
- **Canary Token Leakage**: Verifies that confidential system prompt canary tokens are never leaked in assistant responses.
- **Forbidden Content & Injection**: Catches system file accesses, shell execution attempts, and sensitive prompt keywords.
- **Technical Safety**: Detects API keys, bearer tokens, connection strings, shell syntax, and internal stack traces.
- **Policy Compliance**: Validates adherence to out-of-domain boundaries and competitor product disclaimers.

### 4. Adversarial & Prompt Testing (Promptfoo Integration)
- Integrated CLI execution of `promptfoo` via asynchronous Python subprocessing.
- Evaluates 13 assertions covering normal inquiries, expected outputs, jailbreak defense, prompt injection resistance, and abusive input defusing.
- Automatic redaction of API keys, bearer tokens, and connection strings from logs and outputs.

### 5. Multi-Turn & Tool-Call Testing
- Evaluates multi-turn context retention, conversation history ordering, and prompt instruction following.
- Verifies tool-call schema conformance, parameter extraction, and execution validation.

### 6. Assistant Version Comparison Engine
- Compares two completed evaluation runs against the same dataset.
- Computes aggregate score deltas, metric-by-metric changes, regression counts, and latency percentiles.

### 7. Automated Release Quality Gate
- Automated policy engine for release approval or rejection.
- Configurable release rules:
  - Minimum candidate pass rate (e.g. 90%).
  - Maximum allowable metric regression drop (e.g. 5%).
  - Zero-tolerance security check enforcement (security regressions force immediate failure).
  - Mandatory metric requirements.

### 8. Model-Based Evaluation (DeepEval & Ragas — Optional)
- **DeepEval Integration**: Faithfulness, Answer Relevancy, and Hallucination metrics.
- **Ragas Integration**: RAG-specific Context Precision, Context Recall, and Faithfulness.
- *Note*: Model-based evaluations are optional and disabled by default. When enabled, they can connect to a local Ollama daemon or OpenAI-compatible endpoint.

### 9. Management Dashboard & Telemetry
- **Overview**: Real-time evaluation KPIs, pass-rate trends, and security posture donuts.
- **Projects & Assistants**: Register models, inspect system prompts, and organize evaluation runs.
- **Test Runs & Inspector**: Filter runs, view case-by-case outputs, latency, and evaluator metric chips.
- **Security Dashboard**: 5-category breakdown cards and detailed findings log.
- **Settings**: Local execution defaults and telemetry monitoring.

### 10. Continuous Integration (GitHub Actions)
- Automated pipeline running backend unit tests, frontend build/typecheck, and Promptfoo evaluations in parallel on push and pull requests.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Lucide React, Modern CSS Grid/Flexbox |
| **Backend API** | FastAPI, Pydantic v2, Python 3.12, Uvicorn, Python-Dotenv |
| **Database & ORM** | PostgreSQL 16, SQLAlchemy 2.0, Alembic, Psycopg 3 |
| **Evaluation Engines** | Promptfoo CLI (v0.120+), DeepEval (v4.3+), Ragas (v0.2+) |
| **CI / CD** | GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`) |

---

## Project Structure

```text
Aegis/
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions CI pipeline
├── backend/
│   ├── app/
│   │   ├── adapters/              # Mock, Ollama, and HTTP assistant adapters
│   │   ├── api/routes/            # FastAPI endpoints (projects, assistants, datasets, evaluations)
│   │   ├── core/                  # Settings and application configuration
│   │   ├── db/                    # SQLAlchemy database session and base
│   │   ├── demo/                  # BharatHome assistant orchestrator (v1 good / v2 broken)
│   │   ├── evaluation/            # Core executor, comparison, quality gate, and evaluators
│   │   │   ├── deepeval/          # DeepEval adapter integration
│   │   │   ├── ragas/             # Ragas RAG evaluation engine
│   │   │   ├── promptfoo/         # Promptfoo CLI runner & secret redaction
│   │   │   └── security/          # Deterministic security validators (PII, Canary, Safety)
│   │   ├── models/                # SQLAlchemy models (Project, AssistantVersion, Dataset, etc.)
│   │   └── schemas/               # Pydantic v2 request/response schemas
│   ├── migrations/                # Alembic schema migrations
│   ├── promptfoo/                 # Promptfoo YAML config and custom Python provider
│   ├── scripts/                   # Seeding, verification, and benchmark scripts
│   ├── tests/                     # 221 automated unit and integration tests
│   └── requirements.txt           # Pinned backend dependencies
├── docs/
│   └── screenshots/               # Application showcase documentation and screenshots
├── frontend/
│   ├── src/
│   │   ├── api/                   # Typed API client services
│   │   ├── components/            # React UI components (Dashboard, Datasets, Runs, Security, etc.)
│   │   ├── types/                 # TypeScript interfaces and response schemas
│   │   ├── App.tsx                # Main application shell and sidebar navigation
│   │   └── styles.css             # Unified SaaS design styles
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml             # Full-stack container orchestration
├── .gitignore                     # Repository hygiene exclusions
└── README.md
```

---

## Getting Started

### Prerequisites
- **Python**: 3.12+
- **Node.js**: 20+ (with npm)
- **PostgreSQL**: 16 (Local or via Docker)

---

### Step 1: Clone and Configure Environment

```bash
git clone https://github.com/your-username/aegis.git
cd aegis
```

Create the environment file for the backend:
```bash
cp backend/.env.example backend/.env
```

Ensure `backend/.env` has your PostgreSQL connection string:
```env
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/aegis
CORS_ORIGINS=http://localhost:5173
```

---

### Step 2: Database Setup & Migrations

If running PostgreSQL locally, create the database:
```sql
CREATE DATABASE aegis;
```

Run Alembic schema migrations:
```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
```

*(Optional)* Seed the BharatHome Golden Dataset:
```bash
python scripts/seed_golden_dataset.py
```

---

### Step 3: Start the Backend Service

```bash
# From within backend/ with .venv active:
uvicorn app.main:app --reload --port 8000
```
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

### Step 4: Start the Frontend Application

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** in your browser.

---

## Example Evaluation Workflow

Here is how to run an end-to-end evaluation cycle using the UI or API:

```mermaid
sequenceDiagram
    autonumber
    actor User as AI Engineer / QA
    participant Web as Aegis Dashboard
    participant API as FastAPI Backend
    participant Worker as Evaluation Worker
    participant Mock as BharatHome Assistant
    participant Engine as Security & Evaluators
    participant DB as PostgreSQL

    User->>Web: 1. Select Assistant Version & Golden Dataset
    Web->>API: 2. POST /api/evaluations (config: concurrency=2, enable_security=true)
    API->>DB: 3. Create EvaluationRun (status: pending)
    API-->>Web: 4. 202 Accepted (Run UUID)
    
    par Async Evaluation
        Worker->>DB: Fetch test cases
        Worker->>Mock: Dispatch prompt messages
        Mock-->>Worker: Assistant response
        Worker->>Engine: Run deterministic & security validators
        Engine-->>Worker: Metric scores & violation diagnostic
        Worker->>DB: Persist CaseResult & MetricResults
    end

    User->>Web: 5. Inspect Run Results
    Web->>API: GET /api/evaluations/{id}/results
    API-->>Web: Case scores, latency, input/output snapshots

    User->>Web: 6. Compare Candidate vs Baseline
    Web->>API: POST /api/evaluations/compare
    API-->>Web: Score deltas & detected regressions

    User->>Web: 7. Run Quality Gate Check
    Web->>API: POST /api/evaluations/release-gate (min_pass_rate=90%)
    API-->>Web: Gate Decision: PASS or FAIL with diagnostic reasons
```

---

## Testing & CI Pipeline

### Running Backend Tests
The backend test suite contains **221 unit and integration tests** executing in ~7.5 seconds:

```bash
# Run the complete test suite from repository root:
$env:PYTHONPATH='backend'; python -m unittest discover -s backend/tests -p "test_*.py" -v
```

### Running Promptfoo Evaluation
Run the deterministic Promptfoo test suite (13 assertions across normal, jailbreak, injection, and defusing cases):

```bash
# Windows PowerShell:
$env:PROMPTFOO_DISABLE_UPDATE='true'; $env:PROMPTFOO_DISABLE_TELEMETRY='true'; $env:AEGIS_ASSISTANT_VERSION='v1'; $env:AEGIS_ASSISTANT_PROVIDER='mock'; npx --yes promptfoo@0.120.19 eval -c backend/promptfoo/promptfooconfig.yaml --no-cache

# macOS / Linux:
PROMPTFOO_DISABLE_UPDATE=true PROMPTFOO_DISABLE_TELEMETRY=true AEGIS_ASSISTANT_VERSION=v1 AEGIS_ASSISTANT_PROVIDER=mock npx --yes promptfoo@0.120.19 eval -c backend/promptfoo/promptfooconfig.yaml --no-cache
```

### Building Frontend
```bash
cd frontend
npm run build
# Runs: tsc -b && vite build
```

### GitHub Actions CI
The workflow in `.github/workflows/ci.yml` runs on every push and PR to `main`:
- **`backend`**: Spins up a PostgreSQL 16 service container, applies migrations, and executes all 221 tests.
- **`frontend`**: Validates strict TypeScript compilation and Vite production bundling.
- **`promptfoo`**: Executes the deterministic prompt and adversarial assertions against the assistant adapter.

---

## Known Limitations

Aegis is engineered as a robust, transparent evaluation harness, not an opaque autonomous AI security barrier:
1. **Deterministic Rule Constraints**: Regex and keyword-based security detection cannot catch novel, heavily obfuscated, or semantically subtle prompt injections that do not match defined patterns.
2. **Mock Assistant Scope**: The offline mock assistant uses rule-based responses for predictable, reproducible benchmarks without requiring GPU infrastructure. Evaluating live LLMs requires configuring OpenAI API keys or a local Ollama instance.
3. **Model-Based Judging Overhead**: DeepEval and Ragas evaluation metrics require an LLM judge (such as `qwen2.5` via Ollama or `gpt-4o-mini`). They are intentionally optional to keep default CI and test cycles fast, free, and deterministic.
4. **Historical Database in CI**: Ephemeral CI runners test release quality gate logic with isolated test fixtures, but cannot evaluate against long-term production benchmark history without external persistent storage.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
