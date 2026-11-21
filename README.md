# I-ITSM — Intelligent IT Service Management System

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.x-61dafb.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646cff.svg)](https://vitejs.dev/)
[![SQLAlchemy 2.x](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B-336791.svg)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/tests-267%20passed-brightgreen.svg)]()
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

An enterprise-grade, object-oriented Intelligent IT Service Management (I-ITSM) system developed for **CS F213 / MAC F212 (Object-Oriented Programming)**. The system features a production-ready **FastAPI** backend with strict layered clean architecture, a **React 18 + Vite** frontend with role-based dashboards, a PostgreSQL relational database with Alembic migrations, an asynchronous event-driven bus (Observer Pattern), an AI-assisted technician recommendation engine (Strategy & Adapter Patterns), automated SLA compliance monitoring, audit trail logging, and in-app notifications.

---

## 1. Project Overview & Problem Statement

Modern enterprise IT organizations handle hundreds of operational incidents daily spanning cloud services, local hardware, databases, enterprise software, and networking clusters. Manual ticket assignment is error-prone, slow, and often violates Service Level Agreements (SLAs).

**I-ITSM** solves these challenges by providing:
1. **Automated Incident Triage & Priority Scoring:** Calculates deterministic incident priority ($P1$ to $P4$) using business criticality, technical urgency, and user impact matrices.
2. **AI-Assisted Smart Technician Allocation:** Employs the **Strategy Pattern** (`SkillBasedAssignmentStrategy` and `LeastLoadedAssignmentStrategy`) augmented by LLM reasoning with guaranteed offline fallback to assign tickets based on skills, availability, and active workload limits.
3. **Strict Incident Lifecycle State Machine:** Enforces valid transitions from `NEW` $\rightarrow$ `CLASSIFIED` $\rightarrow$ `ASSIGNED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED` $\rightarrow$ `VERIFIED` $\rightarrow$ `CLOSED`.
4. **Automated SLA Compliance & Warning Engine:** Continuously tracks response and resolution deadlines per priority level ($P1$–$P4$), generating approaching-breach warnings and breach records automatically.
5. **Incident Archiving & Duplicate Merging:** Preserves historical closed incidents in read-only audit-compliant storage and detects/merges duplicate issues to prevent split investigations.
6. **Multi-Role User Portals:** Provides tailored, responsive interfaces for **Employees**, **Technicians**, and **Administrators** with real-time popup toasts, unread notification counts, and centralized error messaging.

---

## 2. Technology Stack

### Backend
- **Language & Runtime:** Python 3.12+ (tested on Python 3.12 and Python 3.14)
- **Web Framework:** [FastAPI 0.115+](https://fastapi.tiangolo.com) (Asynchronous REST API)
- **Server:** [Uvicorn](https://www.uvicorn.org/) (ASGI server)
- **Data Validation & Serialisation:** [Pydantic v2](https://docs.pydantic.dev/) (`BaseDTO` with camelCase alias generation)
- **ORM & Database Abstraction:** [SQLAlchemy 2.x Asyncio](https://docs.sqlalchemy.org/en/20/)
- **Database Driver:** [Psycopg 3](https://www.psycopg.org/psycopg3/) (PostgreSQL async driver) / [aiosqlite](https://aiosqlite.omnilib.dev/) (in-memory test harness)
- **Relational Database:** PostgreSQL 16+
- **Database Migrations:** [Alembic](https://alembic.sqlalchemy.org/) (6 versioned migrations)
- **Authentication & Security:** JWT (JSON Web Tokens via `python-jose`) & Password Hashing via `bcrypt`
- **Testing & Quality:** [pytest](https://docs.pytest.org/), `pytest-asyncio`, and [Ruff](https://astral.sh/ruff)
- **AI Integration:** Async HTTPX adapter with OpenAI-compatible completion APIs + deterministic Mock provider

### Frontend
- **Framework & Build:** [React 18](https://react.dev/) + [Vite 5](https://vitejs.dev/)
- **UI Components:** Custom modular CSS design system (zero heavy external UI framework overhead)
- **State & Communication:** React Hooks (`useState`, `useEffect`, `useMemo`, `useRef`), native Fetch API with centralized error extraction utility
- **Routing:** URL hash / session-backed routing supporting direct incident deep-linking (`#incident-{id}`)

---

## 3. Architecture & Module Ownership

I-ITSM is built as a **Layered Modular Monolith** adhering to clean architecture and Domain-Driven Design (DDD) principles:

```mermaid
flowchart TD
    subgraph Frontend ["Frontend Layer (React + Vite)"]
        UI_EMP["Employee Portal"]
        UI_TECH["Technician Portal"]
        UI_ADMIN["Admin Dashboard"]
        ERR["Centralized Error Handler"]
    end

    subgraph API ["API Layer (/api/v1)"]
        AUTH_API["Auth & Users"]
        INC_API["Incidents & Archiving"]
        TECH_API["Technicians & Recommendations"]
        SLA_API["SLA, Audit & Notifications"]
    end

    subgraph AppService ["Application Layer"]
        INC_SRV["IncidentService"]
        REC_SRV["SmartRecommendationService"]
        ASSIGN_SRV["TechnicianAssignmentService"]
        SLA_SRV["SLAService & MonitorTask"]
        AUDIT_SRV["AuditService"]
        NOTIF_SRV["NotificationService"]
    end

    subgraph Domain ["Pure Domain Layer (OOP)"]
        INC_DOM["Incident & State Machine"]
        TECH_DOM["Technician Aggregate & Skills"]
        STRAT_DOM["Assignment Strategies (Strategy Pattern)"]
        SLA_DOM["SLA Tracking & Policies"]
    end

    subgraph Infra ["Infrastructure Layer"]
        DB_REPO["SQLAlchemy Repositories"]
        EVENT_BUS["InProcessEventBus (Observer Pattern)"]
        LLM_ADAPT["LLM Provider (Adapter Pattern)"]
    end

    subgraph Storage ["Persistence"]
        PG[(PostgreSQL 16 Engine)]
    end

    Frontend --> API
    API --> AppService
    AppService --> Domain
    AppService --> Infra
    Infra --> Storage
    Infra -.-> EVENT_BUS
```

### Module Breakdown
- **Module 1 (M1 — Identity, Platform & Administration):** User accounts, roles (`EMPLOYEE`, `TECHNICIAN`, `ADMIN`), JWT authentication, service catalogue management, incident categories, and system metrics reporting.
- **Module 2 (M2 — Incident Management & Lifecycle):** Incident creation, canonical UUID persistence, lifecycle state transitions, comment threads, duplicate incident similarity detection, duplicate merging, and soft-archiving.
- **Module 3 (M3 — Technician & Assignment Engine):** Technician profiles, skill levels with proficiency (1–5), workload capacity limits, availability states, deterministic assignment algorithms (`SkillBasedAssignmentStrategy`, `LeastLoadedAssignmentStrategy`), and LLM recommendation augmentation.
- **Module 4 (M4 — SLA, Notifications & Audit Trail):** SLA policy configurations ($P1$–$P4$), automated deadline monitoring, approaching-breach warnings, event-driven notifications with unread counts and toast popups, and immutable incident audit logging.

---

## 4. Repository Structure

```text
I-ITSM/
├── backend/
│   ├── app/
│   │   ├── api/                      # Presentation layer
│   │   │   ├── deps.py               # Dependency injection providers
│   │   │   └── v1/                   # REST endpoints (41 routes)
│   │   │       ├── assignment.py     # Incident assignment
│   │   │       ├── audit.py          # Audit log query APIs
│   │   │       ├── auth.py           # Registration & login
│   │   │       ├── categories.py     # Incident categories
│   │   │       ├── incidents.py      # Incident lifecycle, archive & merge
│   │   │       ├── notifications.py  # User notifications & unread count
│   │   │       ├── reports.py        # Executive dashboard metrics
│   │   │       ├── router.py         # Root API v1 router
│   │   │       ├── schemas.py        # Pydantic v2 DTOs
│   │   │       ├── services.py       # IT service catalogue
│   │   │       ├── sla.py            # SLA policies, tracking & sweeps
│   │   │       ├── sla_schemas.py    # SLA & Audit DTOs
│   │   │       ├── technicians.py    # Technician profiles & skills
│   │   │       └── users.py          # Admin user management
│   │   ├── application/              # Application orchestration services
│   │   │   ├── assignment/           # Recommendation & assignment services
│   │   │   ├── incident/             # Incident lifecycle services
│   │   │   ├── interfaces/           # Abstract repository & service boundaries
│   │   │   ├── sla/                  # SLA, notification, and audit services
│   │   │   └── technician/           # Technician management services
│   │   ├── core/                     # App settings, security, exceptions
│   │   ├── domain/                   # Pure OOP domain entities & rules
│   │   │   ├── assignment/           # Strategy implementations
│   │   │   ├── identity/             # User identity value objects
│   │   │   ├── incident/             # Incident aggregate & lifecycle
│   │   │   ├── sla/                  # SLA policy & tracking entities
│   │   │   └── technician/           # Technician aggregate root & skills
│   │   ├── infrastructure/           # Database models & repositories
│   │   │   ├── database/             # SQLAlchemy ORM models & session factory
│   │   │   ├── events/               # InProcessEventBus
│   │   │   └── repositories/         # Concrete SQLAlchemy repositories
│   │   ├── integrations/             # LLM adapters and provider factory
│   │   └── shared/                   # System-wide enums and types
│   ├── migrations/                   # Alembic database migration revisions
│   │   └── versions/                 # 001 through 006 revisions
│   ├── tests/                        # Automated test suite (267 test cases)
│   │   ├── api/                      # API endpoint tests
│   │   ├── integration/              # Service and repository integration tests
│   │   └── unit/                     # Domain, strategy, and utility tests
│   ├── alembic.ini                   # Alembic configuration
│   └── pyproject.toml                # Dependencies and project metadata
├── frontend/                         # React 18 + Vite frontend SPA
│   ├── src/
│   │   ├── features/employee/        # Employee incident views and components
│   │   │   ├── components/           # Incident cards, tables, badges
│   │   │   ├── hooks/                # useIncidents custom hook
│   │   │   ├── pages/                # ReportIncident, MyIncidents, IncidentDetails
│   │   │   └── utils/                # incidentHelpers formatters
│   │   ├── utils/                    # errorHandler.js centralized error handling
│   │   ├── App.jsx                   # Role-based dashboard and router
│   │   ├── main.jsx                  # React application entry point
│   │   └── index.css                 # Clean CSS design system
│   ├── package.json                  # Node dependencies
│   └── vite.config.js                # Vite build configuration
├── docs/                             # Detailed architectural specifications
│   ├── ARCHITECTURE.md               # Complete system architecture specification
│   ├── API_CONTRACTS.md              # Full REST API contracts & Pydantic schemas
│   ├── DATABASE_DESIGN.md            # Database schema, ER diagrams & migrations
│   ├── MODULE_DOCUMENTATION.md       # Modules M1, M2, M3, and M4 documentation
│   ├── OOP_DESIGN.md                 # Design patterns and OOP principles
│   ├── LLM_INTEGRATION.md            # AI recommendation adapter and fallback
│   ├── ASSIGNMENT_ALGORITHM.md       # Deterministic assignment algorithm formulas
│   ├── AUTHENTICATION.md             # Authentication, JWT, and RBAC specification
│   ├── USER_WORKFLOWS.md             # Employee, Technician, and Admin workflows
│   ├── ADMIN_GUIDE.md                # Administrator operations manual
│   ├── EMPLOYEE_GUIDE.md             # Employee incident guide
│   ├── TECHNICIAN_GUIDE.md           # Technician incident handling guide
│   ├── INSTALLATION_AND_SETUP.md     # Installation and environment guide
│   └── TESTING.md                    # Comprehensive test documentation
├── docker-compose.yml                # Docker compose orchestration
└── README.md                         # Project documentation entry point
```

---

## 5. Quick Start & Installation

### Prerequisites
- **Python 3.12+** (tested on Python 3.12 and Python 3.14)
- **Node.js 18+** & `npm`
- **PostgreSQL 16+** (local instance or Docker container)
- **Git**

### 5.1 Database Setup (PostgreSQL)
Ensure PostgreSQL is running locally or start it via Docker:
```bash
docker compose up -d db
```
Default connection URL: `postgresql+psycopg://postgres:postgres@localhost:5432/iitsm`

### 5.2 Backend Setup
```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies in editable mode
pip install --upgrade pip
pip install -e ".[dev]"

# Configure environment
cp .env.example .env

# Apply database migrations (revisions 001 through 006)
alembic upgrade head

# Start Uvicorn backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 5.3 Frontend Setup
In a new terminal window:
```bash
cd frontend

# Install npm packages
npm install

# Start Vite development server
npm run dev -- --port 3000
```
- Open application: [http://localhost:3000](http://localhost:3000)

---

## 6. Running Tests & Code Quality

The backend includes a comprehensive automated test suite of **267 test cases** executing completely offline with zero external network or database dependencies (via SQLite in-memory engine and mock LLM providers):

```bash
cd backend
source .venv/bin/activate

# Execute all 267 automated tests
pytest -v

# Run linter and formatting checks
ruff check app tests
ruff format --check app tests
```

To build and verify the frontend production bundle:
```bash
cd frontend
npm run build
```

---

## 7. User Roles & Security

| Role | Permissions & Portals |
|---|---|
| **EMPLOYEE** | Report new incidents with real-time duplicate suggestions; track personal incidents; view lifecycle history, SLA deadlines, and comments; add user comments; view unread notifications and popup alerts. |
| **TECHNICIAN** | View assigned incident queue; acknowledge assigned incidents; progress status to `IN_PROGRESS` and `RESOLVED`; provide resolution details; toggle personal operational availability (`AVAILABLE` $\leftrightarrow$ `BUSY`). |
| **ADMIN** | Executive KPI summary dashboard; complete incident management (assignment, smart AI candidate recommendations, status updates); soft-archiving of closed incidents; duplicate incident merging; technician operational capacity management; user management; service catalogue and category management; SLA policy management and manual breach evaluation sweeps; system-wide audit logging. |

---

## 8. Detailed Documentation Index

For comprehensive technical specifications, please consult the dedicated documentation files:
- [Architecture Specification](file:///Users/wonderer/Desktop/I-ITSM/docs/ARCHITECTURE.md) — System layering, event bus, and component relationships.
- [REST API Contracts](file:///Users/wonderer/Desktop/I-ITSM/docs/API_CONTRACTS.md) — Complete endpoint documentation with request/response schemas.
- [Database Schema & Migrations](file:///Users/wonderer/Desktop/I-ITSM/docs/DATABASE_DESIGN.md) — Relational schema, ER diagrams, indexes, and migrations 001–006.
- [Module Documentation](file:///Users/wonderer/Desktop/I-ITSM/docs/MODULE_DOCUMENTATION.md) — Deep-dive into Modules M1, M2, M3, and M4.
- [OOP Design & Patterns](file:///Users/wonderer/Desktop/I-ITSM/docs/OOP_DESIGN.md) — Strategy, Observer, Factory, Adapter, and Repository patterns.
- [LLM Integration Architecture](file:///Users/wonderer/Desktop/I-ITSM/docs/LLM_INTEGRATION.md) — AI recommendation adapter, privacy, and deterministic fallback.
- [Assignment Algorithms](file:///Users/wonderer/Desktop/I-ITSM/docs/ASSIGNMENT_ALGORITHM.md) — Mathematical formulas and ranking logic.
- [Authentication & Security](file:///Users/wonderer/Desktop/I-ITSM/docs/AUTHENTICATION.md) — JWT issuance, password hashing, and RBAC rules.
- [User Workflows](file:///Users/wonderer/Desktop/I-ITSM/docs/USER_WORKFLOWS.md) — End-to-end user journeys and state transitions.
- [Administrator Operations Guide](file:///Users/wonderer/Desktop/I-ITSM/docs/ADMIN_GUIDE.md) — Admin manual for operational workflows.
- [Employee Guide](file:///Users/wonderer/Desktop/I-ITSM/docs/EMPLOYEE_GUIDE.md) — Employee incident reporting manual.
- [Technician Guide](file:///Users/wonderer/Desktop/I-ITSM/docs/TECHNICIAN_GUIDE.md) — Incident acknowledgment and resolution manual.
- [Installation & Setup Guide](file:///Users/wonderer/Desktop/I-ITSM/docs/INSTALLATION_AND_SETUP.md) — Detailed environment and deployment guide.
- [Testing & Quality Verification](file:///Users/wonderer/Desktop/I-ITSM/docs/TESTING.md) — Test suite organization and execution results.
- [Frontend Application Specification](file:///Users/wonderer/Desktop/I-ITSM/frontend/README.md) — React architecture, state management, and error handling.
