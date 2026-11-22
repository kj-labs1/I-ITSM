# I-ITSM — Installation & Operations Guide

This guide provides comprehensive, tested, step-by-step instructions for running the **I-ITSM** platform from a fresh GitHub clone across macOS, Linux, and Windows (PowerShell), using either containerized Docker Compose or native environments.

---

## 1. System Requirements & Prerequisites

| Component | Minimum Version | Recommended | Notes |
|---|---|---|---|
| **Python** | `3.12+` | `3.12.x` / `3.14.x` | Required for backend development |
| **Node.js** | `v20.x+` (or `v18.x`) | `v20.x LTS` | Required for frontend build |
| **npm** | `9.x+` | Latest bundled | Package manager for frontend dependencies |
| **PostgreSQL** | `16+` | `16 Alpine` | Required for persistent data storage |
| **Docker** | `24+` | Docker Desktop | Optional, recommended for 1-command startup |
| **Docker Compose** | `v2.20+` | `compose v2` | Multi-container orchestration |

---

## 2. Quick Start: 1-Minute Docker Compose (Recommended)

The easiest and most reliable way to run the entire stack (PostgreSQL 16, FastAPI backend, and React 18 frontend) is using Docker Compose.

```bash
# 1. Clone the repository
git clone https://github.com/kj-labs1/I-ITSM.git
cd I-ITSM

# 2. Build and launch all services in detached mode
docker compose up --build -d

# 3. Seed demo accounts, IT services, and incident categories
docker compose exec backend python seed_demo_data.py
```

### Accessing Running Services
- **Frontend SPA Portal:** [http://localhost:5173](http://localhost:5173)
- **Backend Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **PostgreSQL Database:** Port `5432` (`localhost:5432/iitsm`)

*(To view logs: `docker compose logs -f`; to stop containers: `docker compose down`)*

---

## 3. Native Host Setup: Step-by-Step

If you prefer running services directly on your host machine without Docker:

### 3.1 Start PostgreSQL
Ensure a local PostgreSQL server is active, or run just the database container:
```bash
docker compose up -d db
```
Default connection URL: `postgresql+psycopg://iitsm:iitsm@localhost:5432/iitsm`

---

### 3.2 Backend Setup (Terminal 1)

#### On macOS / Linux (bash/zsh):
```bash
cd backend

# Create & activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip & install package in editable mode with development dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# Configure environment variables
cp .env.example .env

# Run database migrations to revision 006
alembic upgrade head

# Seed complete demo data (Services, Categories, and Demo Accounts)
python seed_demo_data.py

# Start Uvicorn development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### On Windows (PowerShell):
```powershell
cd backend

# Create & activate Python virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Upgrade pip & install dependencies
python -m pip install --upgrade pip
pip install -e ".[dev]"

# Configure environment variables
Copy-Item .env.example .env

# Run database migrations
alembic upgrade head

# Seed demo data
python seed_demo_data.py

# Start Uvicorn development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Endpoint: [http://localhost:8000/health](http://localhost:8000/health)

---

### 3.3 Frontend Setup (Terminal 2)

In a new terminal window:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

- Open your browser at: **[http://localhost:5173](http://localhost:5173)**

---

## 4. Pre-Seeded Demo Login Credentials

Running `python seed_demo_data.py` (or `docker compose exec backend python seed_demo_data.py`) automatically populates the database with verified demo accounts across all supported roles:

| Username | Password | Role | Description | Assigned Skills |
|---|---|---|---|---|
| `sysadmin` | `SysAdmin@123` | `ADMIN` | System Administrator (Full access) | N/A |
| `admin_user` | `AdminUser@123` | `ADMIN` | Secondary Operations Administrator | N/A |
| `emp_bob` | `EmpBob@123` | `EMPLOYEE` | Standard Employee (Reports & tracks incidents) | N/A |
| `tech_alice` | `TechAlice@123` | `TECHNICIAN` | Senior Specialist | `NETWORK`, `SECURITY`, `CLOUD` |
| `tech_charlie` | `TechCharlie@123` | `TECHNICIAN` | Endpoint & Software Specialist | `HARDWARE`, `SOFTWARE`, `APPLICATION` |

---

## 5. Environment Variables Specification

The backend reads configuration from environment variables or `backend/.env`.

| Variable | Default Value | Description |
|---|---|---|
| `APP_NAME` | `I-ITSM` | Application identifier |
| `APP_ENV` | `development` | Environment mode (`development`, `production`, `testing`) |
| `DEBUG` | `true` | Enables verbose FastAPI logging and exceptions |
| `DATABASE_URL` | `postgresql+psycopg://iitsm:iitsm@localhost:5432/iitsm` | Async SQLAlchemy PostgreSQL connection string |
| `DATABASE_ECHO` | `false` | Echo raw SQL queries to stdout |
| `JWT_SECRET_KEY` | `dev-insecure-secret-key-change-in-production-0123456789` | Secret key for signing HS256 JWT tokens |
| `JWT_ALGORITHM` | `HS256` | JWT cryptographic algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token expiration lifespan |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173","http://127.0.0.1:5173"]` | Allowed browser origins |
| `LLM_PROVIDER` | `mock` | Recommendation AI provider: `mock` (offline) or `openai_compatible` |
| `LLM_API_KEY` | `mock-key` | API key for OpenAI-compatible provider |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL for LLM provider |
| `LLM_MODEL_NAME` | `gpt-4o-mini` | LLM model identifier |

Frontend environment variables (`frontend/.env`):
| Variable | Default Value | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Backend API base URL consumed by React |

---

## 6. Database Migrations Workflow (Alembic)

Database schema versions are managed via Alembic in `backend/migrations/`:
- `001_initial_technician_schema`: Creates `technicians` and `technician_skills` tables.
- `002_identity_and_platform_schema`: Creates `users`, `services`, and `incident_categories` tables.
- `003_incident_management_schema`: Creates `incidents` and `incident_comments` tables.
- `004_sla_audit_notification_schema`: Creates `sla_policies`, `incident_sla_tracking`, `audit_logs`, and `notifications` tables.
- `005_incident_code_archive_merge`: Adds unique incident codes (`INC-xxxxxxxx`), archiving fields, and duplicate merge pointers.
- `006_incident_category_enum_align`: Aligns category enumeration constraints.

### Useful Alembic Commands:
```bash
cd backend
source .venv/bin/activate

# Upgrade to latest migration revision
alembic upgrade head

# Check current revision
alembic current

# View migration history
alembic history --verbose

# Roll back one revision (if needed)
alembic downgrade -1
```

---

## 7. Verification & Troubleshooting

### Port Conflicts
- **Port 5432 in use:** If local PostgreSQL is already occupying port 5432, stop it via `brew services stop postgresql@17` (macOS) or `sudo systemctl stop postgresql` (Linux) before running `docker compose up -d db`.
- **Port 8000 in use:** Terminate any stale uvicorn process via `kill -9 $(lsof -ti :8000)`.
- **Port 5173 in use:** Vite will automatically increment to 5174; update `VITE_API_URL` and CORS settings accordingly.

### Database Connection Failure
- Verify PostgreSQL is accepting connections:
  ```bash
  pg_isready -h localhost -p 5432
  ```
- If running in Docker:
  ```bash
  docker compose ps
  docker compose logs db
  ```
