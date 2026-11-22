# I-ITSM Complete Installation, Deployment, and User Creation Guide

This document is the authoritative, step-by-step setup guide for **I-ITSM (Intelligent IT Service Management)**. It covers clean cloning, containerized Docker execution, local native development (Windows, macOS, Linux), user creation for every supported role, and common troubleshooting solutions.

---

## Table of Contents
1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Prerequisites](#2-prerequisites)
3. [Cloning the Repository](#3-cloning-the-repository)
4. [Environment Configuration](#4-environment-configuration)
5. [Option A: Docker-First Setup (Recommended)](#5-option-a-docker-first-setup-recommended)
6. [Option B: Native Development Setup (Windows / macOS / Linux)](#6-option-b-native-development-setup-windows--macos--linux)
7. [Comprehensive User Creation & Role Management Guide](#7-comprehensive-user-creation--role-management-guide)
   - [7.1 Pre-configured Demo Accounts](#71-pre-configured-demo-accounts)
   - [7.2 Creating an Employee Account](#72-creating-an-employee-account)
   - [7.3 Creating an Administrator / System Administrator](#73-creating-an-administrator--system-administrator)
   - [7.4 Creating & Configuring a Technician Profile](#74-creating--configuring-a-technician-profile)
   - [7.5 Role Transitions & In-Flight Profile Creation](#75-role-transitions--in-flight-profile-creation)
8. [Verifying System Functionality](#8-verifying-system-functionality)
9. [Common Development Commands](#9-common-development-commands)
10. [Troubleshooting Guide](#10-troubleshooting-guide)

---

## 1. Project Overview & Architecture

I-ITSM is an enterprise-grade, modular monolith for IT Service Management built with:
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy 2.0 (async), Alembic, Pydantic v2.
- **Database**: PostgreSQL 16 (persisted via Docker volume or native service).
- **Frontend**: React 19, Vite, responsive vanilla CSS design with clean SVG iconography.
- **Core Modules**:
  - **M1 (Identity & Service Catalogue)**: User accounts, JWT auth, RBAC, services, incident categories.
  - **M2 (Incident Management)**: Incident submission, lifecycle state transitions, priority calculation, duplicate detection, archiving.
  - **M3 (Technician Management & Assignment)**: Technician profiles, skills taxonomy, capacity tracking, heuristic & LLM recommendation engine.
  - **M4 (SLA, Audit & Notifications)**: SLA tracking policies, warning & breach alerts, escalation routing, chronological audit trail.

---

## 2. Prerequisites

Verify that the following tools are installed on your machine:

| Tool | Minimum Version | Check Command |
|---|---|---|
| **Git** | 2.30+ | `git --version` |
| **Docker & Docker Compose** *(for Docker setup)* | Compose v2 | `docker compose version` |
| **Python** *(for Native setup)* | 3.12+ | `python --version` (or `python3 --version`) |
| **Node.js & npm** *(for Native setup)* | Node 20+, npm 10+ | `node --version` and `npm --version` |
| **PostgreSQL** *(for Native setup without Docker)* | 15+ | `psql --version` |

---

## 3. Cloning the Repository

Open a terminal (PowerShell on Windows, Bash/Zsh on macOS/Linux) and clone the repository:

```bash
git clone https://github.com/kj-labs1/I-ITSM.git
cd I-ITSM
git checkout integration/system-integration
```

---

## 4. Environment Configuration

The application requires environment configuration for backend database connectivity and frontend API targeting.

### Backend `.env`
Create the backend configuration file from the provided template:

**macOS / Linux:**
```bash
cp backend/.env.example backend/.env
```

**Windows (PowerShell):**
```powershell
Copy-Item backend\.env.example backend\.env
```

*Key backend configuration variables:*
- `DATABASE_URL`: `postgresql+psycopg://iitsm:iitsm@localhost:5432/iitsm` (or `@db:5432/iitsm` in Docker Compose).
- `JWT_SECRET_KEY`: Random string (min 32 characters).
- `CORS_ORIGINS`: Allowed web browser origins (`["http://localhost:3000","http://localhost:5173"]`).

### Frontend `.env` (Optional)
The frontend automatically defaults to `http://127.0.0.1:8000/api/v1`. To explicitly override:
```bash
cp frontend/.env.example frontend/.env
```

---

## 5. Option A: Docker-First Setup (Recommended)

Docker Compose starts PostgreSQL, the FastAPI backend, and the Vite/Nginx frontend with a single command.

### 1. Launch Services
From the repository root:
```bash
docker compose up -d
```

### 2. Run Database Migrations
Apply Alembic migrations inside the running backend container:
```bash
docker compose exec backend alembic upgrade head
```

### 3. Seed Demo Data & Demo Accounts
Populate the initial demo users, services, incident categories, and technician profiles:
```bash
docker compose exec backend python seed_demo_data.py
```

### 4. Access the Application
- **Frontend Web Portal**: [http://localhost:5173](http://localhost:5173)
- **Interactive OpenAPI Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 6. Option B: Native Development Setup (Windows / macOS / Linux)

If you prefer to run Python and Node.js directly on your host operating system:

### 1. Database Setup (PostgreSQL)
Ensure PostgreSQL is running locally with user and database `iitsm`:
```sql
CREATE USER iitsm WITH PASSWORD 'iitsm';
CREATE DATABASE iitsm OWNER iitsm;
GRANT ALL PRIVILEGES ON DATABASE iitsm TO iitsm;
```
*(Alternatively, run just the database in Docker: `docker run -d --name iitsm-db -e POSTGRES_USER=iitsm -e POSTGRES_PASSWORD=iitsm -e POSTGRES_DB=iitsm -p 5432:5432 postgres:16`)*

### 2. Backend Setup
Navigate to the `backend` directory:
```bash
cd backend
```

**Create and activate virtual environment:**
- macOS / Linux:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- Windows (PowerShell):
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```

**Install dependencies:**
```bash
pip install -e ".[dev]"
```

**Execute migrations:**
```bash
alembic upgrade head
```

**Seed demo accounts & catalogue:**
```bash
python seed_demo_data.py
```

*(Optional: To create a custom administrator with your own password, run `python create_admin.py`)*

**Start the FastAPI backend:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
Open a new terminal window and navigate to `frontend`:
```bash
cd frontend
npm ci
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 7. Comprehensive User Creation & Role Management Guide

I-ITSM implements three first-class user roles:
- **`ADMIN`**: Full administrative authority over users, technician profiles, SLA policies, services, and audit logs. (Includes `sysadmin` and `admin_user`).
- **`TECHNICIAN`**: Resolves assigned incidents, sets availability, acquires skills, and monitors capacity.
- **`EMPLOYEE`**: Standard end-user who reports incidents and verifies resolutions.

### 7.1 Pre-configured Demo Accounts
When `seed_demo_data.py` has run, the following accounts are immediately available:

| Role | Username | Password | Full Name | Notes |
|---|---|---|---|---|
| **Admin** | `sysadmin` | `AdminPassword123!` | System Administrator | System administrator account |
| **Admin** | `admin_user` | `AdminPassword123!` | IT Operations Admin | Standard operations admin |
| **Employee** | `emp_bob` | `EmpPassword123!` | Bob Smith | Employee with reported tickets |
| **Technician** | `tech_alice` | `TechPassword123!` | Alice Johnson | Network & Security specialist |
| **Technician** | `tech_charlie` | `TechPassword123!` | Charlie Davis | Hardware & Software technician |

---

### 7.2 Creating an Employee Account

#### Method A: Via Web UI (Self-Registration)
1. Navigate to [http://localhost:5173](http://localhost:5173).
2. If already logged in, click **Sign out** at the bottom of the sidebar.
3. On the login screen, click **"Don't have an account? Register"**.
4. Fill in:
   - **Full Name**: e.g., `Jane Doe`
   - **Username**: e.g., `emp_jane`
   - **Email**: e.g., `jane@example.com`
   - **Password**: Minimum 8 characters.
5. Click **Create account**. The account is created with role `EMPLOYEE` and immediately logged in.

#### Method B: Via API (cURL)
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "emp_jane",
    "email": "jane@example.com",
    "fullName": "Jane Doe",
    "password": "Password123!"
  }'
```

---

### 7.3 Creating an Administrator / System Administrator

To prevent privilege escalation, public self-registration **never** permits selecting `ADMIN`. New administrators must be provisioned either through the authorized Admin UI or the server-side CLI tool.

#### Method A: Promoting an Existing User via Admin UI
1. Log in with an existing Admin account (e.g. `sysadmin` / `AdminPassword123!`).
2. Click the **Users** tab in the sidebar.
3. Find the user in the system users table.
4. In the **Role** dropdown, change `EMPLOYEE` to `ADMIN`.
5. The role updates immediately in the database without requiring logout.

#### Method B: Server-Side Terminal Utility (`create_admin.py`)
Run the interactive terminal script in the `backend` directory:
```bash
cd backend
python create_admin.py
```
It prompts securely for a password (min 8 chars) and creates an active `ADMIN` account.

---

### 7.4 Creating & Configuring a Technician Profile

In I-ITSM, a technician consists of two distinct components:
1. **User Identity** (`users` table): Stores credentials and role (`TECHNICIAN`).
2. **Operational Profile** (`technicians` & `technician_skills` tables): Stores experience, maximum incident capacity, availability (`AVAILABLE`/`BUSY`), and proficiency ratings (1–5).

#### Complete Workflow:
1. **Promote User**:
   - As an Admin, open **Users** page.
   - Change user's role to `TECHNICIAN`.
2. **Open Technician Roster**:
   - Go to **Technicians** page.
   - The user immediately appears in the roster with the badge: **`Profile Not Configured`**.
3. **Configure Operational Profile**:
   - Click the **Add Technician Profile** button in that user's row.
   - Enter **Experience (Years)** (e.g., `4`).
   - Enter **Max Workload Capacity** (e.g., `10`).
   - Select an **Initial Technical Skill** (e.g., `NETWORK`, `DATABASE`, `SECURITY`) and proficiency level (1 to 5).
   - Click **Save Technician Profile**.
4. **Result**:
   - The badge clears, operational parameters activate, and the technician becomes eligible for smart incident recommendations and assignments.

---

## 8. Verifying System Functionality

Run these checks to confirm all modules function as expected:

1. **Employee Ticket Submission**:
   - Log in as `emp_bob` (`EmpPassword123!`).
   - Go to **Report Incident**. Select category `NETWORK`, describe the problem, and submit.
   - Confirm incident appears in **My Incidents**.
2. **Admin Incident Triage & Smart Assignment**:
   - Log in as `sysadmin` (`AdminPassword123!`).
   - Navigate to **Incident Management**, select the newly reported ticket.
   - Request technician recommendations or select `tech_alice`. Assign the incident.
3. **Technician Workflow**:
   - Log in as `tech_alice` (`TechPassword123!`).
   - View assigned ticket under **Incident Management**.
   - Transition status: `ACKNOWLEDGE` → `IN_PROGRESS` → `RESOLVED`.
4. **Notifications & SLA Verification**:
   - Observe real-time notification alerts (topbar bell) for technician assignment and status changes.
   - Check **SLA Tracking** page for breach monitoring and active policies.

---

## 9. Common Development Commands

### Backend Tests & Code Quality
```bash
cd backend
pytest tests/ -v          # Run 273+ unit and integration tests
ruff check app/ tests/    # Validate linting and formatting
```

### Frontend Build Verification
```bash
cd frontend
npm run build             # Build optimized production bundle to dist/
```

### Safe Docker Operations
```bash
docker compose logs -f backend    # Follow backend API logs
docker compose down               # Stop containers (preserves database data)
docker compose down -v            # Stop containers AND delete database volume
```

---

## 10. Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| **`Connection refused to localhost:5432`** | PostgreSQL is not running or port 5432 is occupied. | Ensure PostgreSQL service is active or run `docker compose up -d db`. Verify `DATABASE_URL` in `backend/.env`. |
| **`Alembic: Target database is not up to date`** | Pending database migrations. | Run `alembic upgrade head` in `backend/` or `docker compose exec backend alembic upgrade head`. |
| **`Login fails: Incorrect username or password`** | Seed script has not been run on fresh database. | Execute `python seed_demo_data.py` (or `docker compose exec backend python seed_demo_data.py`). |
| **`User is Technician but not available for assignment`** | User's operational profile has not been configured. | Navigate to **Technicians** tab as Admin and click **Add Technician Profile** to assign capacity and skills. |
| **`Network Error: Unable to connect to server`** | Backend is stopped or frontend is pointing to wrong URL. | Check backend status on port 8000. Ensure `CORS_ORIGINS` in `backend/.env` includes `http://localhost:5173`. |
| **`psycopg.OperationalError: password authentication failed`** | Mismatch between `.env` database password and PostgreSQL user. | Ensure `backend/.env` password matches PostgreSQL user credentials (`iitsm:iitsm`). |
