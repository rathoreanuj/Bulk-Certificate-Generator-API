# Bulk Certificate Generator API & Platform

An enterprise-grade, asynchronous backend API built with **FastAPI**, **SQLAlchemy**, **Alembic**, and **ReportLab** for bulk-generating high-resolution PDF certificates. Includes a modern React management dashboard.

The system accepts cohorts of recipients, offloads generation to asynchronous workers, tracks granular per-certificate statuses, enables paginated querying, and securely streams generated PDF files.

---

## Table of Contents

- [Project Setup](#project-setup)
- [Running the Application](#running-the-application)
- [Docker & Containerization](#docker--containerization)
- [Running Tests](#running-tests)
- [How to Submit a Certificate Generation Request](#how-to-submit-a-certificate-generation-request)
- [How to Retrieve Generated Certificates](#how-to-retrieve-generated-certificates)
  - [1. Poll Overall Job Status & Progress Counters](#1-poll-overall-job-status--progress-counters)
  - [2. List Certificates in a Job (With Pagination & Filtering)](#2-list-certificates-in-a-job-with-pagination--filtering)
  - [3. Retrieve a Single Certificate Record](#3-retrieve-a-single-certificate-record)
  - [4. Download a Certificate PDF](#4-download-a-certificate-pdf)
  - [5. Download All Certificates as ZIP Archive](#5-download-all-certificates-as-zip-archive)
  - [6. Public Certificate Verification Registry](#6-public-certificate-verification-registry)
  - [7. Retry Failed Certificates in a Job](#7-retry-failed-certificates-in-a-job)
- [Important Implementation & Design Decisions](#important-implementation--design-decisions)
  - [1. Asynchronous Architecture: FastAPI BackgroundTasks](#1-asynchronous-architecture-fastapi-backgroundtasks)
  - [2. Database Scalability: SQLite WAL Mode & Indexing](#2-database-scalability-sqlite-wal-mode--indexing)
  - [3. Failure Isolation & Incremental State Commits](#3-failure-isolation--incremental-state-commits)
  - [4. Programmatic Vector PDF Generation: ReportLab Canvas](#4-programmatic-vector-pdf-generation-reportlab-canvas)
  - [5. Security & Path Traversal Mitigation](#5-security--path-traversal-mitigation)
  - [6. Input Validation & DoS Defenses](#6-input-validation--dos-defenses)
  - [7. Observability & Distributed Tracing](#7-observability--distributed-tracing)
  - [8. In-Memory Streaming & Resilient Error Recovery](#8-in-memory-streaming--resilient-error-recovery)
- [Project Structure](#project-structure)

---

## Project Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** *(optional, only needed if developing the React frontend)*

### 1. Clone & Navigate to Repository

```bash
git clone <repo-url>
cd AEREO-SDE-INTERN-BULK-GENERATORE-ASSIGNMENT
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate on macOS / Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create or review `.env` in the project root:

```ini
# Environment Mode
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database Connection (SQLite or PostgreSQL)
DATABASE_URL=sqlite:///./certificates.db

# Storage Directory for Generated PDFs
CERTIFICATES_DIR=./generated_certificates

# Scalability & DoS Controls
MAX_RECIPIENTS_PER_JOB=10000
DEFAULT_PAGE_SIZE=100
MAX_PAGE_SIZE=1000
```

*Note: Default values work out of the box with zero external configuration required.*

### 5. Apply Database Migrations (Alembic)

```bash
python -m alembic upgrade head
```

This runs all migrations up to head, creating `certificates.db` with all tables, foreign keys, and indexes.

---

## Running the Application

### Option A: Standard Startup (FastAPI + Embedded React UI)

Run the backend server with auto-reload:

```bash
uvicorn app.main:app --reload
```

Or run migrations and start the server in a single PowerShell command:

```powershell
python -m alembic upgrade head; uvicorn app.main:app --reload
```

The application is now live at **http://127.0.0.1:8000**:
- **Web UI Dashboard:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/) *(serves the pre-compiled production React SPA)*
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Service Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Option B: Frontend Hot-Reload Development (Vite)

If actively modifying frontend components:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on **http://localhost:3000** and automatically proxies API requests to `http://127.0.0.1:8000`.

---

## Docker & Containerization

The repository includes a multi-stage `Dockerfile` and a `docker-compose.yml` configuration allowing full deployment of the FastAPI backend, background workers, and embedded React SPA with zero local Python or Node dependencies.

### One-Command Startup (Docker Compose):

```bash
docker compose up --build
```

- Multi-stage build compiles the React dashboard via Node 18 Alpine and packages it directly with Python 3.11-slim.
- Automatically executes `alembic upgrade head` before booting Uvicorn on port `8000`.
- Persistent Docker volumes preserve SQLite databases (`certificates_data`) and generated certificate PDFs (`generated_certs_data`).
- Includes a built-in container healthcheck polling `/health`.

Access the application at **http://localhost:8000**.

---

## Running Tests

The test suite covers unit tests for PDF generation, service-layer business logic, and integration tests for all REST endpoints using an in-memory SQLite database (`StaticPool`).

Run the full test suite:

```bash
python -m pytest tests/ -v
```

Output:
```
======================== 73 passed, 1 warning in 3.53s ========================
```

Run specific test modules:

```bash
# REST API endpoints & integration tests
python -m pytest tests/test_jobs_api.py -v

# Service layer unit tests
python -m pytest tests/test_services.py -v

# ReportLab PDF canvas generator tests
python -m pytest tests/test_certificate_generator.py -v
```

---

## How to Submit a Certificate Generation Request

Submit a batch of recipients along with shared event metadata. The request is validated by Pydantic and returns immediately with **HTTP 202 Accepted** and a tracking `job_id`. Background workers generate the certificates asynchronously.

### Endpoint: `POST /api/v1/jobs`

#### Request Payload:

```json
{
  "event_name": "Autonomous UAV Engineering Fellowship 2024",
  "issuer_name": "Aereo Aerospace Academy",
  "issue_date": "2024-11-15",
  "recipients": [
    {
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice.johnson@example.com",
      "course_name": "Computer Vision & LiDAR Point Clouds"
    },
    {
      "recipient_name": "Bob Smith",
      "recipient_email": "bob.smith@example.com",
      "course_name": "Geospatial Photogrammetry & Orthomosaics"
    }
  ]
}
```

#### cURL Command:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Autonomous UAV Engineering Fellowship 2024",
    "issuer_name": "Aereo Aerospace Academy",
    "issue_date": "2024-11-15",
    "recipients": [
      {
        "recipient_name": "Alice Johnson",
        "recipient_email": "alice.johnson@example.com",
        "course_name": "Computer Vision & LiDAR Point Clouds"
      },
      {
        "recipient_name": "Bob Smith",
        "recipient_email": "bob.smith@example.com",
        "course_name": "Geospatial Photogrammetry & Orthomosaics"
      }
    ]
  }'
```

#### PowerShell Command:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs" -Method Post -ContentType "application/json" -Body '{
  "event_name": "Autonomous UAV Engineering Fellowship 2024",
  "issuer_name": "Aereo Aerospace Academy",
  "issue_date": "2024-11-15",
  "recipients": [
    {
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice.johnson@example.com",
      "course_name": "Computer Vision & LiDAR Point Clouds"
    },
    {
      "recipient_name": "Bob Smith",
      "recipient_email": "bob.smith@example.com",
      "course_name": "Geospatial Photogrammetry & Orthomosaics"
    }
  ]
}'
```

#### Response (`HTTP 202 Accepted`):

```json
{
  "job_id": "eb3d964e-597a-437b-b5c8-033328c5f13f",
  "status": "pending",
  "total_count": 2,
  "message": "Job accepted. 2 certificate(s) will be generated. Poll GET /jobs/eb3d964e-597a-437b-b5c8-033328c5f13f for progress."
}
```

---

## How to Retrieve Generated Certificates

### 1. Poll Overall Job Status & Progress Counters

Retrieve real-time counts of completed, pending, and failed certificates.

**Endpoint:** `GET /api/v1/jobs/{job_id}`

```bash
curl http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f
```

**Response (`HTTP 200 OK`):**

```json
{
  "id": "eb3d964e-597a-437b-b5c8-033328c5f13f",
  "event_name": "Autonomous UAV Engineering Fellowship 2024",
  "issuer_name": "Aereo Aerospace Academy",
  "issue_date": "2024-11-15",
  "status": "completed",
  "total_count": 2,
  "success_count": 2,
  "failed_count": 0,
  "pending_count": 0,
  "created_at": "2024-11-15T10:00:00Z",
  "updated_at": "2024-11-15T10:00:03Z"
}
```

*Lifecycle States:* `pending` → `processing` → `completed` (or `failed` if catastrophic system crash).

---

### 2. List Certificates in a Job (With Pagination & Filtering)

Retrieve individual certificate records. Supports optional status filtering and pagination for large cohorts.

**Endpoint:** `GET /api/v1/jobs/{job_id}/certificates`

**Query Parameters (Optional):**
- `status`: `success` | `pending` | `failed`
- `limit`: Number of records to return (1 - 1000)
- `offset`: Number of records to skip

#### Examples:

```bash
# Retrieve all records
curl http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f/certificates

# Filter only successful certificates with pagination
curl "http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f/certificates?status=success&limit=10&offset=0"
```

**Response (`HTTP 200 OK`):**

```json
[
  {
    "id": "7ea2ce94-c019-4037-b86a-ec81ff38dba3",
    "job_id": "eb3d964e-597a-437b-b5c8-033328c5f13f",
    "recipient_name": "Alice Johnson",
    "recipient_email": "alice.johnson@example.com",
    "course_name": "Computer Vision & LiDAR Point Clouds",
    "status": "success",
    "error_message": null,
    "created_at": "2024-11-15T10:00:00Z",
    "updated_at": "2024-11-15T10:00:02Z"
  },
  {
    "id": "5ee1f52b-cef7-4d3c-ae21-7d6ddb38400e",
    "job_id": "eb3d964e-597a-437b-b5c8-033328c5f13f",
    "recipient_name": "Bob Smith",
    "recipient_email": "bob.smith@example.com",
    "course_name": "Geospatial Photogrammetry & Orthomosaics",
    "status": "success",
    "error_message": null,
    "created_at": "2024-11-15T10:00:00Z",
    "updated_at": "2024-11-15T10:00:03Z"
  }
]
```

---

### 3. Retrieve a Single Certificate Record

**Endpoint:** `GET /api/v1/jobs/{job_id}/certificates/{certificate_id}`

```bash
curl http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f/certificates/7ea2ce94-c019-4037-b86a-ec81ff38dba3
```

---

### 4. Download a Certificate PDF

Streams the binary PDF file generated for the recipient.

**Endpoint:** `GET /api/v1/jobs/{job_id}/certificates/{certificate_id}/download`

#### cURL Command:

```bash
curl -O -J http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f/certificates/7ea2ce94-c019-4037-b86a-ec81ff38dba3/download
```
*Saves as `certificate_Alice_Johnson.pdf`.*

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f/certificates/7ea2ce94-c019-4037-b86a-ec81ff38dba3/download" -OutFile "certificate_Alice_Johnson.pdf"
```

#### Status Codes:
- `HTTP 200 OK`: PDF stream with `Content-Type: application/pdf` and `Content-Disposition` header.
- `HTTP 409 Conflict`: If the certificate is still `pending` in queue or `failed`.
- `HTTP 404 Not Found`: If the job or certificate ID does not exist.
- `HTTP 403 Forbidden`: If an unauthorized file target or path traversal attempt is detected.

---

### 5. Download All Certificates as ZIP Archive

Bundles all successfully generated PDF certificates for a job into an in-memory ZIP archive stream.

**Endpoint:** `GET /api/v1/jobs/{job_id}/download-zip` *(Alias: `GET /api/v1/jobs/{job_id}/download-all`)*

#### cURL Command:

```bash
curl -O -J http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f/download-zip
```
*Saves as `certificates_eb3d964e-597a-437b-b5c8-033328c5f13f.zip`.*

#### PowerShell Command:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f/download-zip" -OutFile "certificates.zip"
```

#### Status Codes:
- `HTTP 200 OK`: Binary ZIP stream with `Content-Type: application/zip` containing all generated PDFs.
- `HTTP 409 Conflict`: If no successful certificates are ready for download.
- `HTTP 404 Not Found`: If the job ID does not exist.

---

### 6. Public Certificate Verification Registry

Allows employers, academic institutions, and credential checkers to verify certificate authenticity and tamper-evidence by certificate ID.

**Endpoint:** `GET /api/v1/verify/{certificate_id}`

#### cURL Command:

```bash
curl http://127.0.0.1:8000/api/v1/verify/7ea2ce94-c019-4037-b86a-ec81ff38dba3
```

#### Response (`HTTP 200 OK`):

```json
{
  "valid": true,
  "certificate_id": "7ea2ce94-c019-4037-b86a-ec81ff38dba3",
  "status": "success",
  "recipient_name": "Alice Johnson",
  "course_name": "Computer Vision & LiDAR Point Clouds",
  "event_name": "Autonomous UAV Engineering Fellowship 2024",
  "issuer_name": "Aereo Aerospace Academy",
  "issue_date": "2024-11-15",
  "issued_at": "2024-11-15T10:00:02Z"
}
```

#### Status Codes:
- `HTTP 200 OK`: Valid certificate metadata response.
- `HTTP 404 Not Found`: If certificate does not exist in the official registry.

---

### 7. Retry Failed Certificates in a Job

Re-queues any failed certificate generations within a job without regenerating existing successful ones.

**Endpoint:** `POST /api/v1/jobs/{job_id}/retry`

#### cURL Command:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs/eb3d964e-597a-437b-b5c8-033328c5f13f/retry
```

#### Response (`HTTP 200 OK`):

```json
{
  "job_id": "eb3d964e-597a-437b-b5c8-033328c5f13f",
  "status": "processing",
  "retried_count": 1,
  "message": "Enqueued 1 failed certificate(s) for retry."
}
```

---

## Important Implementation & Design Decisions

### 1. Asynchronous Architecture: FastAPI BackgroundTasks
- **Zero Heavy Infrastructure Dependencies:** Instead of requiring Celery, Redis, and separate worker daemons, the application leverages FastAPI's built-in `BackgroundTasks` executing in a thread pool. This provides true asynchronous non-blocking request handling with zero setup complexity.
- **Immediate Response (`HTTP 202 Accepted`):** The API accepts the cohort, creates the job record in the database, and returns immediately so clients do not face connection timeouts on large batches.
- **Decoupled Database Sessions:** Background tasks open and close their own independent `SessionLocal()` session to avoid leaking or colliding with the HTTP request's session lifecycle.

### 2. Database Scalability: SQLite WAL Mode & Indexing
- **Write-Ahead Logging (`PRAGMA journal_mode=WAL`):** By default, SQLite locks the entire database file during writes. In `app/database.py`, SQLite connection pragmas configure WAL mode and `synchronous=NORMAL`. Readers can query job statuses concurrently while background workers write completed certificates.
- **Busy Timeout Protection (`busy_timeout=15000`):** Concurrency lock contention is automatically handled with a 15-second retry timeout.
- **Relational Indexing Strategy:**
  - Foreign key index on `certificate_records.job_id`.
  - Filter indexes on `certificate_jobs.status` and `certificate_records.status`.
  - Composite index `Index('ix_cert_records_job_status', 'job_id', 'status')` ensuring $O(\log N)$ filtered lookups.
- **Database Portability:** Code is written with pure SQLAlchemy ORM and Alembic migrations. Simply setting `DATABASE_URL=postgresql://user:pass@host/db` in `.env` activates production connection pooling (`pool_size`, `max_overflow`, `pool_pre_ping`) with zero code refactoring.

### 3. Failure Isolation & Incremental State Commits
- **Fault-Isolated Batch Processing:** In `app/services.py`, each recipient's certificate generation is wrapped in an isolated `try/except` block and committed individually.
- **Partial Success Preservation:** If recipient #4 fails (e.g. font rendering or OS file write issue), recipients #1–#3 and #5–#100 are still successfully generated.
- **Granular Diagnostics:** The `error_message` column on `CertificateRecord` persists the exact failure reason, enabling clients to diagnose individual failures while the parent job safely reaches `completed`.

### 4. Programmatic Vector PDF Generation: ReportLab Canvas
- **Self-Contained & Deterministic:** ReportLab's low-level canvas API renders high-resolution, vector-crisp certificates programmatically without headless browser dependencies (like Puppeteer or wkhtmltopdf) that consume high CPU and memory.
- **Collision-Free UUID Storage:** Each PDF is saved as `{record.id}.pdf` within `generated_certificates/`, preventing collisions during concurrent generation.
- **Dynamic Auto-Shrink Typography:** If a recipient or course name is exceptionally long, font sizes automatically scale down incrementally to prevent text truncation or canvas overflow.
- **Proper Visual Hierarchy & Contrast:** Navy header/footer bands, high-contrast white text on dark accents, clean cream paper background, and background watermark seal rendered strictly behind text.

### 5. Security & Path Traversal Mitigation
- **File Access Verification:** In `download_certificate`, the endpoint strictly validates that the requested file resolves to `{record.id}.pdf` with a `.pdf` extension.
- **Sanitized Download Filenames:** Recipient names in `Content-Disposition` headers are sanitized to alphanumeric characters, hyphens, and underscores to prevent header injection attacks.

### 6. Input Validation & DoS Defenses
- **Cohort Bound Limits:** `JobCreateRequest` caps the maximum recipients per request to `MAX_RECIPIENTS_PER_JOB` (10,000) to protect the server from memory exhaustion.
- **Pydantic v2 String Sanitization:** Removes control characters, carriage returns, and leading/trailing whitespace across recipient names and course titles.
- **RFC-Compliant Email Validation:** Powered by `EmailStr` to validate recipient email format prior to job acceptance.

### 7. Observability & Distributed Tracing
- **Request ID Middleware:** Generates and returns an `X-Request-ID` header on every request/response, allowing log correlation across production monitoring tools.
- **Global Error Boundary:** Catches unhandled exceptions, logs the full traceback, and returns a clean, structured `HTTP 500` JSON response without exposing internal code structures.

### 8. In-Memory Streaming & Resilient Error Recovery
- **Zero-Disk-Leak In-Memory ZIP Streaming:** Bulk ZIP archives are constructed directly in an `io.BytesIO` memory stream via Python's `zipfile.ZipFile`, avoiding the need to write temporary archives to disk or schedule file cleanup crons.
- **Idempotent Retry Subsystem:** Retry requests only target records in `FAILED` status, resetting state to `PENDING` and decrementing `failed_count` while leaving successful records untouched.
- **Multi-Stage Containerization:** The production `Dockerfile` creates a lean container combining an optimized Vite client build with a lightweight Python 3.11-slim server, auto-migrating database schemas at runtime.

---

## Project Structure

```
.
├── Dockerfile                   # Multi-stage production container build (Vite + Python)
├── docker-compose.yml           # One-command full-stack container deployment
├── .dockerignore                # Container build exclusions (.venv, node_modules)
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application factory, middleware, lifespan
│   ├── config.py                # Pydantic BaseSettings (.env configuration)
│   ├── database.py              # SQLAlchemy engine, WAL pragmas, session dependency
│   ├── models.py                # ORM models: CertificateJob, CertificateRecord + indexes
│   ├── schemas.py               # Pydantic v2 validation models & sanitizers
│   ├── services.py              # Business logic: batch creation, background workers, ZIP streaming
│   ├── certificate_generator.py # ReportLab PDF canvas engine with vector graphics
│   └── routers/
│       ├── __init__.py
│       ├── jobs.py              # REST API endpoints (jobs, polling, download, ZIP, retry)
│       └── verify.py            # Public credential verification registry endpoint
├── frontend/                    # Modern React management dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx       # Segmented navigation & API health indicator
│   │   │   ├── Generator.jsx    # Bulk submission form & CSV importer
│   │   │   ├── JobTracker.jsx   # Real-time polling, counters, ZIP download & retry actions
│   │   │   ├── CertificatePreviewModal.jsx # Certificate layout inspector
│   │   │   ├── ApiDocs.jsx      # Developer API specs, verification docs & cURL references
│   │   │   └── Toast.jsx        # Notification alert system
│   │   ├── App.jsx              # Main dashboard view coordinator
│   │   ├── App.css              # Light-mode SaaS layout styles
│   │   └── index.css            # Minimal design tokens & WCAG accessibility
│   └── dist/                    # Compiled production SPA assets
├── tests/
│   ├── conftest.py              # Pytest fixtures (in-memory SQLite StaticPool)
│   ├── test_certificate_generator.py # Unit tests for PDF creation
│   ├── test_jobs_api.py         # Integration tests for all REST endpoints (including ZIP & retry)
│   └── test_services.py         # Unit tests for service layer & workers
├── alembic/                     # Database migrations
│   ├── env.py
│   └── versions/
│       ├── ec9759d911f7_initial_schema.py
│       └── 42f222e51160_add_indexes_for_scalability.py
├── generated_certificates/      # Output directory for generated PDF files
├── alembic.ini                  # Alembic CLI migration configuration
├── requirements.txt             # Python project dependencies
├── pytest.ini                   # Pytest test configuration
├── .env                         # Local environment settings
└── README.md                    # Project documentation
```
