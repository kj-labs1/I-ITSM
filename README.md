# I-ITSM — Intelligent IT Service Management System

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.x-61dafb.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646cff.svg)](https://vitejs.dev/)
[![SQLAlchemy 2.x](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B-336791.svg)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/tests-273%20passed-brightgreen.svg)]()
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

An enterprise-grade, object-oriented Intelligent IT Service Management (I-ITSM) system built for **CS F213 / MAC F212 (Object-Oriented Programming)**. The system aligns with **ITIL v4 Service Operation** standards and implements a production-ready **FastAPI** backend with strict layered clean architecture, a **React 18 + Vite** frontend with role-based operational dashboards, an asynchronous **PostgreSQL 16+** persistence layer managed with **Alembic**, an in-process event bus (**Observer Pattern**), an algorithmic technician allocation and recommendation engine (**Strategy & Adapter Patterns**), automated SLA compliance monitoring, immutable audit logging, and real-time in-app notifications.

---

## Table of Contents

1. [Project Title & Badges](#i-itsm--intelligent-it-service-management-system)
2. [Project Overview](#1-project-overview)
3. [Problem Statement](#2-problem-statement)
4. [Project Objectives](#3-project-objectops)
5. [Key Features](#4-key-features)
6. [Technology Stack](#5-technology-stack)
7. [System Architecture](#6-system-architecture)
8. [Repository Structure](#7-repository-structure)
9. [Architecture and Design Patterns](#8-architecture-and-design-patterns)
10. [Database Design](#9-database-design)
11. [API Documentation](#10-api-documentation)
12. [Prerequisites](#11-prerequisites)
13. [Installation and Setup](#12-installation-and-setup)
14. [Environment Variables](#13-environment-variables)
15. [Database Setup and Migrations](#14-database-setup-and-migrations)
16. [Running the Application](#15-running-the-application)
17. [Running Tests & Quality Assurance](#16-running-tests--quality-assurance)
18. [API Usage Examples](#17-api-usage-examples)
19. [Error Handling and Validation](#18-error-handling-and-validation)
20. [Current Implementation Status](#19-current-implementation-status)
21. [Future Enhancements](#20-future-enhancements)
22. [Contributing Guidelines & Project Team](#21-contributing-guidelines--project-team)

---

## 1. Project Overview

Modern enterprise IT organizations handle hundreds of operational incidents daily spanning cloud infrastructure, local workstation hardware, relational databases, distributed microservices, and internal identity providers. In conventional help desk systems, ticket triage, urgency classification, and technician dispatch are handled manually. This introduces cognitive bottlenecks, operational latency, severe SLA violations, and frequent skill-mismatched assignments.

**I-ITSM** addresses these systemic challenges by implementing an automated, intelligent, and mathematically deterministic IT Service Management platform. Designed around Domain-Driven Design (DDD) and SOLID object-oriented principles, I-ITSM replaces manual dispatching with deterministic matrix scoring, rule-based and AI-augmented technician matching, a strict lifecycle state machine, real-time SLA deadline monitoring, and a transparent audit trail.

---

## 2. Problem Statement

Manual IT incident triage and ticket resolution workflows in growing organizations suffer from five critical failure modes:

1. **Subjective Priority Classification:** End users routinely classify minor software requests as "Urgent" or "Critical," leading to alert fatigue and delayed triage of genuine production outages.
2. **Suboptimal Ticket Dispatch:** IT dispatchers struggle to evaluate technician domain competency, current active ticket load, and operational availability in real time, leading to overloaded senior technicians and idle junior staff.
3. **SLA Deadlines Overlooked:** Support tickets languish in unacknowledged queues until SLA thresholds are breached, resulting in contractual penalties and business disruption.
4. **Duplicate Investigation Overhead:** Multiple users reporting the same network failure or database degradation generate dozens of isolated tickets, fragmenting technician communication and wasting engineering hours.
5. **Lack of Auditability & Compliance:** Ad-hoc ticket status changes, missing lifecycle transition histories, and untracked administrative overrides violate SOC 2, ISO/IEC 20000, and ITIL compliance standards.

---

## 3. Project Objectives

The primary engineering objectives of the I-ITSM platform are:

- **Deterministic Urgency & Priority Scoring:** Implement an objective mathematical scoring matrix combining business criticality, technical urgency, and user impact to determine incident priority ($P1$ Critical to $P4$ Low).
- **Algorithmic & AI-Assisted Dispatch:** Deliver pluggable assignment strategies (`SkillBasedAssignmentStrategy` and `LeastLoadedAssignmentStrategy`) combined with an offline-resilient LLM recommendation adapter to rank candidate technicians by domain skill match, active ticket load, and availability.
- **Strict Incident Lifecycle State Machine:** Guarantee that incident records can only traverse valid, auditable state transitions (`NEW` $\rightarrow$ `CLASSIFIED` $\rightarrow$ `ASSIGNED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED` $\rightarrow$ `VERIFIED` $\rightarrow$ `CLOSED`).
- **Proactive SLA Compliance Engine:** Provide automated tracking of response and resolution deadlines per priority tier ($P1$–$P4$), generating approaching-breach warning events and breach flags without manual oversight.
- **Event-Driven Decoupling:** Utilize an asynchronous In-Process Event Bus (**Observer Pattern**) to notify users, update SLA clocks, and append immutable audit log entries without coupling domain services.
- **Auditable & Archivable Incident Storage:** Provide soft-archiving capabilities for closed incidents and duplicate detection/merging mechanisms to maintain a clean, performant active incident queue.

---

## 4. Key Features

### Module 1: Identity, Access Management & Platform Administration (M1)
- **Role-Based Access Control (RBAC):** Three distinct roles: `EMPLOYEE`, `TECHNICIAN`, and `ADMIN`.
- **JWT Authentication:** Stateless authentication using `python-jose` (HS256) with password security enforced via `passlib` (bcrypt).
- **Service Catalogue & Categories:** Complete CRUD management for business IT services and taxonomy categories (`HARDWARE`, `SOFTWARE`, `NETWORK`, `DATABASE`, `CLOUD`, `SECURITY`, `AUTHENTICATION`, `APPLICATION`, `STORAGE`).
- **User Management & Role Promotion:** Comprehensive administrator tools to view, search, edit, and deactivate users, featuring a seamless two-phase technician promotion workflow.
- **Platform Analytics:** Real-time KPI summaries reporting total users, active incidents, resolution rates, and system health.

### Module 2: Incident Management & Lifecycle Engine (M2)
- **Deterministic Priority Scoring:** Automated evaluation of business impact, urgency, and affected service criticality to assign priority levels ($P1$, $P2$, $P3$, $P4$).
- **Formal State Machine:** Strict enforcement of lifecycle transitions, blocking illegal jumps (e.g., preventing `CLOSED` from jumping directly to `NEW` or unassigned incidents from moving to `IN_PROGRESS`).
- **Incident Discussion Threads:** Threaded comments supporting collaboration between reporting employees, assigned technicians, and administrators.
- **Duplicate Detection & Merging:** Real-time text similarity scoring against open incidents to suggest existing tickets upon creation, plus an administrative merge workflow that transfers comments and closes duplicates.
- **Compliance Archiving:** Soft-archiving workflow for closed incidents to keep operational queues fast while preserving full audit trails.

### Module 3: Technician Management & Intelligent Assignment (M3)
- **Technician Profiles & Skill Matrices:** Domain profiles tracking active ticket loads, maximum workload limits (default: 5 concurrent tickets), and domain skill competencies with proficiency ratings (1–5).
- **Operational Availability:** Dynamic status flags (`AVAILABLE`, `BUSY`, `OFFLINE`, `ON_LEAVE`) that immediately disqualify technicians from assignment when unavailable.
- **Strategy Pattern Dispatch:**
  - `SkillBasedAssignmentStrategy`: Prioritizes domain skill overlap and competency score, breaking ties by lowest workload.
  - `LeastLoadedAssignmentStrategy`: Distributes incoming volume evenly across available personnel to prevent technician burnout.
- **AI Recommendation Engine (Adapter Pattern):** Asynchronous LLM reasoning provider with a deterministic mock fallback that inspects incident context and returns top candidate technicians with human-readable rationale.

### Module 4: SLA Compliance, Notification System & Audit Trail (M4)
- **SLA Policy Matrix:** Configurable response and resolution thresholds per priority ($P1$: 15m response / 2h resolution; $P2$: 30m response / 4h resolution; $P3$: 2h response / 8h resolution; $P4$: 4h response / 24h resolution).
- **Automated SLA Monitor Daemon:** A 60-second periodic background task that scans active incidents, updates elapsed times, flags approaching breaches ($\ge 80\%$ threshold), and records breaches.
- **In-Process Event Bus (Observer Pattern):** Decoupled publish-subscribe mechanism emitting domain events (`INCIDENT_CREATED`, `INCIDENT_ASSIGNED`, `STATUS_CHANGED`, `SLA_WARNING`, `SLA_BREACHED`).
- **Real-Time Notification Center:** In-app notification inbox with unread counters, mark-as-read actions, and auto-dismissing visual toast popups in the frontend.
- **Immutable Audit Ledger:** Comprehensive, append-only audit trail logging every administrative and lifecycle action with user attribution, timestamps, and state snapshots.

---

## 5. Technology Stack

### Backend Technologies
| Layer / Component | Technology | Version / Specification |
|---|---|---|
| **Language & Runtime** | Python | 3.12+ (tested on 3.12 and 3.14) |
| **Web Framework** | FastAPI | 0.115+ (Asynchronous ASGI framework) |
| **ASGI Server** | Uvicorn | 0.32+ with uvloop |
| **Validation & Serialization** | Pydantic v2 | 2.10+ (using `BaseDTO` camelCase aliasing) |
| **ORM & Persistence** | SQLAlchemy | 2.0+ (Async engine & sessions) |
| **Database Driver** | Psycopg 3 | 3.2+ (PostgreSQL async binary driver) |
| **Test Database Engine** | aiosqlite | 0.20+ (In-memory asynchronous SQLite harness) |
| **Schema Migrations** | Alembic | 1.14+ (6 versioned revisions) |
| **Security & Auth** | python-jose & passlib | JWT (HS256) & bcrypt password hashing |
| **HTTP Client** | HTTPX | 0.28+ (Async external LLM adapter) |
| **Test Framework** | pytest & pytest-asyncio | 8.3+ (273 automated tests) |
| **Linter & Formatter** | Ruff | 0.8+ (Zero warnings/errors) |

### Frontend Technologies
| Layer / Component | Technology | Version / Specification |
|---|---|---|
| **Core Framework** | React | 18.3+ (Functional components & hooks) |
| **Build Tooling** | Vite | 5.4+ (ESM-based lightning-fast bundler) |
| **Styling & Design System** | Custom CSS3 | Modular CSS design system (zero UI bloat) |
| **State Management** | React Hooks | `useState`, `useEffect`, `useMemo`, `useRef` |
| **API Client** | Native Fetch API | Centralized error handler (`errorHandler.js`) |
| **Routing** | Hash / State Router | Deep-linking support (`#incident-{id}`) |

### Infrastructure & Deployment
| Component | Technology | Specification |
|---|---|---|
| **Database** | PostgreSQL | 16.x Alpine |
| **Containerization** | Docker & Docker Compose | Multi-stage Dockerfile (Node 20 build $\rightarrow$ Nginx Alpine) |
| **Web Server / Reverse Proxy** | Nginx | Alpine-based SPA routing with API reverse proxy |

---

## 6. System Architecture

I-ITSM is structured as a **Layered Clean Architecture** (Domain-Driven Design), ensuring total separation of domain rules from web frameworks, persistence mechanisms, and third-party APIs.

```mermaid
flowchart TD
    subgraph Client ["Frontend Layer (React 18 + Vite)"]
        UI_EMP["Employee Incident Portal"]
        UI_TECH["Technician Queue & Availability"]
        UI_ADMIN["Admin KPI Dashboard & Workflows"]
        ERR_HDL["Centralized Error Extractor"]
    end

    subgraph API ["Presentation Layer (FastAPI /api/v1)"]
        AUTH_ROUTER["Auth & Profile (/auth)"]
        USER_ROUTER["User Management (/users)"]
        INC_ROUTER["Incidents & Archiving (/incidents)"]
        TECH_ROUTER["Technicians & Skills (/technicians)"]
        SLA_ROUTER["SLA Policies & Sweeps (/sla)"]
        NOTIF_ROUTER["Notifications (/notifications)"]
        AUDIT_ROUTER["Audit Ledger (/audit)"]
    end

    subgraph AppService ["Application Layer (Orchestration)"]
        INC_SVC["IncidentService"]
        REC_SVC["SmartRecommendationService"]
        ASSIGN_SVC["TechnicianAssignmentService"]
        SLA_SVC["SLAService & 60s Background Task"]
        NOTIF_SVC["NotificationService"]
        AUDIT_SVC["AuditService"]
    end

    subgraph Domain ["Pure Domain Layer (Business Rules & OOP)"]
        INC_ENT["Incident Aggregate & State Machine"]
        TECH_ENT["Technician Aggregate Root & Skills"]
        STRAT_ENT["Assignment Strategies (Strategy Pattern)"]
        SLA_ENT["SLA Policy & Tracking Aggregates"]
    end

    subgraph Infra ["Infrastructure & Persistence Layer"]
        EVENT_BUS["InProcessEventBus (Observer Pattern)"]
        REPO_IMPL["SQLAlchemy 2.0 Repositories"]
        LLM_ADAPT["LLM Provider (Adapter Pattern)"]
        DB_ENGINE[(PostgreSQL 16 Engine / Alembic)]
    end

    Client -->|HTTP / JSON (REST)| API
    API --> AppService
    AppService --> Domain
    AppService --> Infra
    Infra --> DB_ENGINE
    Infra -.->|Domain Events| EVENT_BUS
    EVENT_BUS -.->|Notify| AppService
```

### Layer Responsibilities

1. **Presentation Layer (`backend/app/api/`):**
   - Implements 41 RESTful API endpoints organized under `/api/v1`.
   - Handles HTTP request validation, parameter deserialization, and response serialization via Pydantic v2 `BaseDTO`.
   - Enforces JWT authentication, role verification (`require_roles`), and HTTP error translation.
2. **Application Layer (`backend/app/application/`):**
   - Coordinates use cases and transaction boundaries across repositories and domain entities.
   - Emits asynchronous domain events via the event bus upon state mutations.
   - Manages background scheduled jobs (e.g., 60-second SLA monitor task).
3. **Domain Layer (`backend/app/domain/`):**
   - Pure Python classes containing business logic, validation rules, state machines, and mathematical formulas.
   - Completely decoupled from FastAPI, SQLAlchemy, databases, or external protocols.
4. **Infrastructure Layer (`backend/app/infrastructure/`):**
   - Concrete implementations of repository interfaces using SQLAlchemy 2.0 async sessions.
   - Database ORM models, session lifecycle, and transaction commits.
   - External service adapters (OpenAI-compatible LLM provider and mock fallback).

---

## 7. Repository Structure

```text
I-ITSM/
├── backend/
│   ├── app/
│   │   ├── api/                      # Presentation layer
│   │   │   ├── deps.py               # Dependency injection & authentication guards
│   │   │   └── v1/                   # 41 REST endpoints across 11 modules
│   │   │       ├── assignment.py     # Incident assignment routes
│   │   │       ├── audit.py          # Immutable audit log query routes
│   │   │       ├── auth.py           # Registration, login & profile routes
│   │   │       ├── categories.py     # Incident category management routes
│   │   │       ├── incidents.py      # Lifecycle, comments, search, merge & archive
│   │   │       ├── notifications.py  # User notifications & unread counts
│   │   │       ├── reports.py        # System KPI dashboard routes
│   │   │       ├── router.py         # Consolidated API v1 router
│   │   │       ├── schemas.py        # Pydantic v2 DTOs with camelCase aliases
│   │   │       ├── services.py       # IT service catalogue routes
│   │   │       ├── sla.py            # SLA policies, compliance & manual sweeps
│   │   │       ├── sla_schemas.py    # SLA & Audit DTO definitions
│   │   │       ├── technicians.py    # Technician profiles, skills & availability
│   │   │       └── users.py          # Admin user administration routes
│   │   ├── application/              # Application orchestration services
│   │   │   ├── assignment/           # Recommendation & assignment coordination
│   │   │   ├── incident/             # Incident use cases & lifecycle management
│   │   │   ├── interfaces/           # Abstract repository & service contracts
│   │   │   ├── sla/                  # SLA, notification & audit orchestration
│   │   │   └── technician/           # Technician profile & skill management
│   │   ├── core/                     # Configuration, JWT security & base exceptions
│   │   │   ├── config.py             # Pydantic BaseSettings environment loader
│   │   │   ├── database.py           # SQLAlchemy async engine & session factory
│   │   │   ├── exceptions.py         # Custom application domain exceptions
│   │   │   └── security.py           # Password hashing & JWT generation/verification
│   │   ├── domain/                   # Pure OOP domain entities & aggregates
│   │   │   ├── assignment/           # SkillBased & LeastLoaded strategy implementations
│   │   │   ├── identity/             # User identity entity & value objects
│   │   │   ├── incident/             # Incident aggregate, state machine & priority logic
│   │   │   ├── sla/                  # SLA policy & tracking aggregates
│   │   │   └── technician/           # Technician aggregate root & skills
│   │   ├── infrastructure/           # Concrete infrastructure & database implementations
│   │   │   ├── database/             # SQLAlchemy ORM models & table definitions
│   │   │   ├── events/               # InProcessEventBus (Observer pattern)
│   │   │   └── repositories/         # Concrete async SQLAlchemy repositories
│   │   ├── integrations/             # External adapters (LLM provider & factory)
│   │   │   └── llm/                  # Async HTTPX OpenAI adapter & mock provider
│   │   ├── shared/                   # System-wide enums and types
│   │   │   ├── enums.py              # Status, Priority, Category, Role enums
│   │   │   └── types.py              # Common type aliases & value objects
│   │   └── main.py                   # FastAPI application initialization & lifespan
│   ├── migrations/                   # Alembic database migration scripts
│   │   ├── versions/                 # 6 sequential migration revisions (001–006)
│   │   └── env.py                    # Alembic async migration environment
│   ├── tests/                        # 273 automated tests
│   │   ├── api/                      # REST API endpoint tests
│   │   ├── integration/              # Service & repository integration tests
│   │   ├── unit/                     # Domain entities, algorithms & state machine tests
│   │   └── conftest.py               # Asynchronous fixtures & in-memory test database
│   ├── alembic.ini                   # Alembic configuration file
│   ├── pyproject.toml                # Project metadata, dependencies & tool configs
│   ├── requirements.txt              # Pinned production requirements
│   └── seed_demo_data.py             # Complete database demo seeder script
├── frontend/                         # React 18 + Vite frontend SPA
│   ├── src/
│   │   ├── features/employee/        # Employee incident views & submission forms
│   │   │   ├── components/           # Incident cards, tables, badges
│   │   │   ├── hooks/                # useIncidents custom data fetching hook
│   │   │   ├── pages/                # ReportIncident, MyIncidents, IncidentDetails
│   │   │   └── utils/                # incidentHelpers formatters & transformers
│   │   ├── utils/                    # errorHandler.js centralized error extractor
│   │   ├── App.jsx                   # Role-based dashboard tabs & authentication state
│   │   ├── main.jsx                  # React DOM mount point
│   │   └── index.css                 # Clean, responsive CSS design system
│   ├── package.json                  # Frontend dependencies and npm scripts
│   └── vite.config.js                # Vite build and proxy configuration
├── docs/                             # Authoritative technical documentation suite
│   ├── INSTALLATION_GUIDE.md         # Multi-OS installation, troubleshooting & seeding
│   ├── USER_GUIDE.md                 # Role-based user manual (Employee, Technician, Admin)
│   ├── ARCHITECTURE.md               # Clean architecture, layering & event bus
│   ├── API_DOCUMENTATION.md          # Complete REST API reference & schemas
│   ├── DATABASE_DESIGN.md            # Relational schema, ER diagram & Alembic history
│   ├── OOP_DESIGN.md                 # 6 OOP pillars, 7 design patterns, SOLID compliance
│   ├── ASSIGNMENT_ALGORITHMS.md      # Skill-Based, Least-Loaded formulas & AI adapter
│   ├── MODULE_DOCUMENTATION.md       # Modules M1, M2, M3, and M4 responsibilities
│   ├── TESTING.md                    # Test suite overview, harness & CI matrix
│   └── final-report/                 # Academic final project report
│       ├── I-ITSM_Final_Project_Report.pdf  # 73-page PDF academic report
│       └── I-ITSM_Final_Project_Report.tex  # Complete editable LaTeX report source
├── docker-compose.yml                # Multi-container full-stack orchestration
└── README.md                         # Project documentation entry point
```

---

## 8. Architecture and Design Patterns

The I-ITSM backend strictly adheres to classic Object-Oriented Design and the GoF Design Patterns:

### 1. Strategy Pattern (`backend/app/domain/assignment/`)
Encapsulates ticket assignment algorithms behind an abstract base class `AssignmentStrategy`:
- `SkillBasedAssignmentStrategy`: Evaluates required incident category against technician domain skills, calculates proficiency scores (1–5), and selects the highest-scoring candidate. Ties are broken using lowest current workload.
- `LeastLoadedAssignmentStrategy`: Normalizes workload capacity ratios across active personnel, dispatching the ticket to the technician with the most remaining capacity.

### 2. State Machine Pattern (`backend/app/domain/incident/`)
Governs incident lifecycle transitions via explicit transition matrices. State changes are guarded by validation methods:
- Valid transition: `NEW` $\rightarrow$ `CLASSIFIED` $\rightarrow$ `ASSIGNED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED` $\rightarrow$ `VERIFIED` $\rightarrow$ `CLOSED`.
- Illegal operations (e.g., closing an unassigned ticket or moving an in-progress ticket back to new) raise `InvalidStateTransitionException` and are rejected before touching persistence.

### 3. Observer Pattern (`backend/app/infrastructure/events/`)
Decouples domain state changes from secondary side-effects via `InProcessEventBus`:
- When an incident is assigned, an `INCIDENT_ASSIGNED` event is published.
- The `NotificationService` observer captures the event to create in-app notifications for the technician.
- The `AuditService` observer writes an immutable audit record to the `audit_logs` table.
- The `SLAService` observer initializes response/resolution tracking clocks.

### 4. Repository Pattern (`backend/app/infrastructure/repositories/`)
Abstracts database access behind clean repository interfaces (`IUserRepository`, `IIncidentRepository`, `ITechnicianRepository`, `ISLARepository`). The application layer interacts solely with domain entities, allowing database engines to be swapped (PostgreSQL in production, SQLite in tests) without modifying business logic.

### 5. Adapter Pattern (`backend/app/integrations/llm/`)
Provides a unified interface (`ILLMProvider`) for technician candidate recommendations:
- `OpenAILLMProvider`: Issues asynchronous HTTP requests to OpenAI-compatible endpoints with incident context and technician metadata.
- `MockLLMProvider`: Deterministic local provider executing without network access, ensuring zero external dependencies during unit testing and offline development.

### 6. Dependency Injection (`backend/app/api/deps.py`)
Utilizes FastAPI's dependency injection system to inject database sessions, repository instances, domain services, and current authenticated user principals into API route handlers.

---

## 9. Database Design

I-ITSM uses **PostgreSQL 16+** with strict relational integrity, foreign key constraints, and performance indexes.

```mermaid
erDiagram
    users ||--o{ incidents : "reports"
    users ||--o| technicians : "promoted_to"
    services ||--o{ incidents : "categorizes"
    incident_categories ||--o{ incidents : "classifies"
    technicians ||--o{ incidents : "assigned_to"
    technicians ||--o{ technician_skills : "has"
    incidents ||--o{ incident_comments : "contains"
    incidents ||--o| incident_sla_tracking : "tracked_by"
    sla_policies ||--o{ incident_sla_tracking : "governs"
    users ||--o{ notifications : "receives"
    incidents ||--o{ notifications : "triggers"
    users ||--o{ audit_logs : "performs"
    incidents ||--o{ audit_logs : "records"

    users {
        uuid id PK
        string username UK
        string email UK
        string hashed_password
        enum role "EMPLOYEE, TECHNICIAN, ADMIN"
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    services {
        uuid id PK
        string name UK
        string description
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    incident_categories {
        uuid id PK
        string name UK
        string description
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    technicians {
        uuid id PK
        uuid user_id FK, UK
        enum status "AVAILABLE, BUSY, OFFLINE, ON_LEAVE"
        int max_workload
        int current_workload
        datetime created_at
        datetime updated_at
    }

    technician_skills {
        uuid id PK
        uuid technician_id FK
        string category
        int proficiency_level "1 to 5"
        datetime created_at
    }

    incidents {
        uuid id PK
        string title
        string description
        enum priority "P1, P2, P3, P4"
        enum status "NEW, CLASSIFIED, ASSIGNED, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, VERIFIED, CLOSED"
        enum category "HARDWARE, SOFTWARE, NETWORK, etc."
        uuid service_id FK
        uuid reporter_id FK
        uuid technician_id FK
        boolean is_archived
        datetime created_at
        datetime updated_at
    }

    incident_comments {
        uuid id PK
        uuid incident_id FK
        uuid author_id FK
        text content
        datetime created_at
    }

    sla_policies {
        uuid id PK
        enum priority UK "P1, P2, P3, P4"
        int response_time_minutes
        int resolution_time_minutes
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    incident_sla_tracking {
        uuid id PK
        uuid incident_id FK, UK
        uuid policy_id FK
        datetime response_deadline
        datetime resolution_deadline
        datetime responded_at
        datetime resolved_at
        boolean is_response_breached
        boolean is_resolution_breached
        boolean is_warning_sent
        datetime created_at
        datetime updated_at
    }

    notifications {
        uuid id PK
        uuid user_id FK
        uuid incident_id FK
        string title
        text message
        string notification_type
        boolean is_read
        datetime created_at
    }

    audit_logs {
        uuid id PK
        uuid incident_id FK
        uuid user_id FK
        string action
        text details
        datetime created_at
    }
```

### Alembic Migration History
Schema versioning is maintained under `backend/migrations/versions/`:
- `001_initial_core_schema.py`: Core `users`, `services`, and `incident_categories` tables.
- `002_technicians_and_skills.py`: `technicians` profiles, workload counters, and `technician_skills`.
- `003_incidents_and_comments.py`: `incidents` table, lifecycle state enum, priority matrix, and `incident_comments`.
- `004_sla_and_audit.py`: `sla_policies`, `incident_sla_tracking`, and `audit_logs` ledger.
- `005_notifications.py`: `notifications` table for event-driven user alerts.
- `006_incident_archiving.py`: `is_archived` column and performance indexes for incident archiving and duplicate detection.

---

## 10. API Documentation

All API routes are prefixed with `/api/v1` and return uniform JSON envelopes. Protected endpoints require a Bearer token in the `Authorization` header: `Authorization: Bearer <access_token>`.

### Route Summary (41 Endpoints)

| Method | Endpoint | Access Roles | Description |
|---|---|---|---|
| **Authentication & Profile** | | | |
| `POST` | `/api/v1/auth/register` | Public | Register a new user account (defaults to `EMPLOYEE`). |
| `POST` | `/api/v1/auth/login` | Public | Authenticate credentials and receive a JWT access token. |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieve current user profile and role details. |
| **User Administration** | | | |
| `GET` | `/api/v1/users` | `ADMIN` | List all registered users with optional role filtering. |
| `GET` | `/api/v1/users/summary` | `ADMIN` | Get high-level user statistics across roles. |
| `GET` | `/api/v1/users/{id}` | `ADMIN` | Retrieve detailed profile for a specific user. |
| `PATCH` | `/api/v1/users/{id}` | `ADMIN` | Update user details, role promotion, or active status. |
| `DELETE` | `/api/v1/users/{id}` | `ADMIN` | Deactivate/remove a user account. |
| **Service Catalogue** | | | |
| `GET` | `/api/v1/services` | Authenticated | List all active IT services. |
| `POST` | `/api/v1/services` | `ADMIN` | Create a new IT service entry. |
| `PATCH` | `/api/v1/services/{id}` | `ADMIN` | Update an existing IT service entry. |
| `DELETE` | `/api/v1/services/{id}` | `ADMIN` | Deactivate an IT service entry. |
| **Incident Categories** | | | |
| `GET` | `/api/v1/categories` | Authenticated | List all active incident categories. |
| `POST` | `/api/v1/categories` | `ADMIN` | Create a new incident category. |
| `PATCH` | `/api/v1/categories/{id}` | `ADMIN` | Update an incident category. |
| `DELETE` | `/api/v1/categories/{id}` | `ADMIN` | Deactivate an incident category. |
| **Incident Management** | | | |
| `GET` | `/api/v1/incidents` | Authenticated | List active incidents (filtered by role permissions). |
| `POST` | `/api/v1/incidents` | Authenticated | Submit a new incident ticket. |
| `GET` | `/api/v1/incidents/search` | Authenticated | Search incidents by keyword, category, or status. |
| `GET` | `/api/v1/incidents/archived` | `ADMIN` | Retrieve soft-archived historical incidents. |
| `GET` | `/api/v1/incidents/{id}` | Authenticated | Get full details, SLA clock, and comments for an incident. |
| `PATCH` | `/api/v1/incidents/{id}` | `ADMIN` | Update incident metadata (priority, service, category). |
| `PATCH` | `/api/v1/incidents/{id}/status` | Authenticated | Progress incident lifecycle state. |
| `POST` | `/api/v1/incidents/{id}/comments` | Authenticated | Add a comment to an incident thread. |
| `GET` | `/api/v1/incidents/{id}/duplicates`| Authenticated | Scan for potential duplicate tickets using text similarity. |
| `POST` | `/api/v1/incidents/{id}/merge` | `ADMIN` | Merge duplicate incident into a primary target ticket. |
| `PATCH` | `/api/v1/incidents/{id}/archive` | `ADMIN` | Soft-archive a closed incident ticket. |
| **Technician & Assignment** | | | |
| `GET` | `/api/v1/technicians` | `ADMIN`, `TECHNICIAN` | List all technician profiles, skills, and capacities. |
| `POST` | `/api/v1/technicians` | `ADMIN` | Create technician profile for a promoted user. |
| `GET` | `/api/v1/technicians/{id}` | `ADMIN`, `TECHNICIAN` | Get specific technician profile and skills. |
| `PATCH` | `/api/v1/technicians/{id}` | `ADMIN` | Update technician workload limit or configuration. |
| `PATCH` | `/api/v1/technicians/{id}/availability` | `ADMIN`, `TECHNICIAN` | Toggle availability status (`AVAILABLE`, `BUSY`, etc.). |
| `GET` | `/api/v1/technicians/{id}/skills` | Authenticated | List domain skills and proficiencies for a technician. |
| `POST` | `/api/v1/technicians/{id}/skills` | `ADMIN` | Assign a new domain skill to a technician. |
| `DELETE` | `/api/v1/technicians/{id}/skills/{name}` | `ADMIN` | Remove a domain skill from a technician. |
| `GET` | `/api/v1/technicians/recommendations` | `ADMIN` | Retrieve AI/algorithm candidate recommendations for an incident. |
| `POST` | `/api/v1/incidents/{id}/assign` | `ADMIN` | Assign technician to incident via chosen strategy. |
| **SLA Compliance & Monitoring** | | | |
| `GET` | `/api/v1/sla/policies` | Authenticated | List SLA threshold policies for all priority tiers. |
| `POST` | `/api/v1/sla/policies` | `ADMIN` | Create or update SLA policy parameters. |
| `GET` | `/api/v1/sla/summary` | `ADMIN` | Retrieve aggregated SLA compliance statistics. |
| `GET` | `/api/v1/sla/violations` | `ADMIN` | List all incidents with active SLA breaches or warnings. |
| `POST` | `/api/v1/sla/check` | `ADMIN` | Manually trigger an SLA evaluation sweep. |
| **Notifications** | | | |
| `GET` | `/api/v1/notifications` | Authenticated | List in-app notifications for the calling user. |
| `GET` | `/api/v1/notifications/unread/count` | Authenticated | Retrieve unread notification count badge. |
| `PATCH` | `/api/v1/notifications/{id}/read` | Authenticated | Mark a specific notification as read. |
| `POST` | `/api/v1/notifications/read-all` | Authenticated | Mark all notifications as read for current user. |
| **Audit Ledger & Reporting** | | | |
| `GET` | `/api/v1/audit` | `ADMIN` | Query immutable audit log records with filtering. |
| `GET` | `/api/v1/reports/summary` | `ADMIN` | Retrieve executive system metrics and KPI dashboard data. |

---

## 11. Prerequisites

Before installing I-ITSM, ensure your host environment meets the following specifications:

- **Python:** 3.12 or newer (`python3 --version`)
- **Node.js:** 20.x LTS or newer (`node --version`)
- **Package Manager:** `npm` 10+ (`npm --version`)
- **Database:** PostgreSQL 16+ (or use Docker for PostgreSQL)
- **Container Engine (Optional):** Docker 24+ and Docker Compose v2+
- **Operating Systems:** macOS (ARM64 / x86_64), Linux (Ubuntu 22.04+, Debian, Fedora), Windows 11 (PowerShell / WSL2)

---

## 12. Installation and Setup

### Option A: 1-Minute Docker Compose (Recommended)

Run the entire application stack (PostgreSQL database, FastAPI backend, React frontend) with a single command:

```bash
docker compose up --build -d
```

- **Frontend Application:** [http://localhost:5173](http://localhost:5173)
- **Backend Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

To seed demo accounts and sample IT services inside Docker:
```bash
docker compose exec backend python seed_demo_data.py
```

To stop all services:
```bash
docker compose down
```

---

### Option B: Native Host Setup (Development)

#### 1. Start PostgreSQL
Ensure PostgreSQL 16+ is running locally on port `5432` with a database named `iitsm`, or start only the database container:
```bash
docker compose up -d db
```

#### 2. Backend Installation
```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Upgrade pip and install package in editable mode with development dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# Copy environment configuration
cp .env.example .env

# Apply database migrations
alembic upgrade head

# Seed initial services, categories, and demo user accounts
python seed_demo_data.py
```

#### 3. Frontend Installation
In a separate terminal window:
```bash
cd frontend

# Install dependencies
npm install
```

---

## 13. Environment Variables

The backend configuration is managed by Pydantic's `BaseSettings` (`backend/app/core/config.py`). Create a `.env` file in `backend/`:

| Variable | Type | Default Value | Description |
|---|---|---|---|
| `PROJECT_NAME` | String | `I-ITSM` | Human-readable application name. |
| `API_V1_STR` | String | `/api/v1` | Base prefix for all API routes. |
| `ENVIRONMENT` | String | `development` | Deployment environment (`development`, `staging`, `production`). |
| `DEBUG` | Boolean | `true` | Enables verbose debug logging and traceback outputs. |
| `DATABASE_URL` | String | `postgresql+psycopg://iitsm:iitsm@localhost:5432/iitsm` | Async SQLAlchemy PostgreSQL connection string. |
| `SECRET_KEY` | String | `insecure-dev-secret-key-change-in-production-min-32-chars` | Cryptographic secret for signing JWT tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | `1440` | JWT expiration duration in minutes (default: 24 hours). |
| `ALGORITHM` | String | `HS256` | JWT HMAC hashing algorithm. |
| `BACKEND_CORS_ORIGINS` | JSON List | `["http://localhost:5173","http://localhost:3000"]` | Allowed CORS origins for browser API requests. |
| `LLM_PROVIDER` | String | `mock` | Recommendation provider: `mock` (offline) or `openai`. |
| `OPENAI_API_KEY` | String | `""` | API key required when `LLM_PROVIDER=openai`. |
| `OPENAI_BASE_URL` | String | `https://api.openai.com/v1` | API base URL for OpenAI-compatible providers. |
| `OPENAI_MODEL` | String | `gpt-4o-mini` | Model identifier used for AI recommendations. |
| `SLA_MONITOR_INTERVAL_SECONDS` | Integer | `60` | Frequency of background SLA compliance sweeps. |

---

## 14. Database Setup and Migrations

I-ITSM uses **Alembic** for asynchronous database migrations. The migration environment is configured in `backend/migrations/env.py`.

```bash
cd backend
source .venv/bin/activate

# Apply all migrations to latest revision
alembic upgrade head

# Verify current revision status
alembic current

# Revert a single revision (if needed)
alembic downgrade -1

# Generate a new migration revision after modifying models
alembic revision --autogenerate -m "describe_schema_change"
```

### Seeding Demo Data

The seed script creates initial IT services, categories, and 5 pre-configured demo user accounts:

```bash
python seed_demo_data.py
```

#### Pre-Configured Demo Accounts
| Username | Password | Role | Description |
|---|---|---|---|
| `sysadmin` | `SysAdmin@123` | `ADMIN` | System Administrator (Full platform access) |
| `admin_user` | `AdminUser@123` | `ADMIN` | Secondary Operations Administrator |
| `emp_bob` | `EmpBob@123` | `EMPLOYEE` | Standard Employee (Reports & tracks incidents) |
| `tech_alice` | `TechAlice@123` | `TECHNICIAN` | Senior Specialist (Skills: `NETWORK`, `SECURITY`, `CLOUD`) |
| `tech_charlie` | `TechCharlie@123` | `TECHNICIAN` | Specialist (Skills: `HARDWARE`, `SOFTWARE`, `APPLICATION`) |

---

## 15. Running the Application

### Starting the Backend Server
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Base URL: `http://localhost:8000/api/v1`
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative ReDoc UI: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### Starting the Frontend Development Server
```bash
cd frontend
npm run dev
```
- Frontend UI: [http://localhost:5173](http://localhost:5173)

---

## 16. Running Tests & Quality Assurance

The test suite consists of **273 automated tests** covering unit, integration, and API layers. Tests run completely offline with zero external database dependencies using an in-memory SQLite async engine (`aiosqlite`) and mock LLM adapters.

```bash
cd backend
source .venv/bin/activate

# Run the complete test suite
pytest

# Run tests with verbose output and duration profiling
pytest -v --durations=10

# Run specific test modules
pytest tests/unit/test_assignment_strategies.py
pytest tests/api/test_incidents_api.py

# Run static code analysis and linting checks
ruff check app tests

# Run formatting checks
ruff format --check app tests
```

To build and verify the frontend production bundle:
```bash
cd frontend
npm run build
```

---

## 17. API Usage Examples

### 1. User Authentication (Login)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "sysadmin",
    "password": "SysAdmin@123"
  }'
```
**Response:**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsIn...",
  "tokenType": "bearer",
  "user": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "username": "sysadmin",
    "email": "sysadmin@iitsm.local",
    "role": "ADMIN",
    "isActive": true
  }
}
```

### 2. Submit a New Incident (Employee)
```bash
curl -X POST "http://localhost:8000/api/v1/incidents" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "VPN Gateway Unresponsive",
    "description": "Remote engineering staff unable to connect to the US-East VPN concentrator.",
    "category": "NETWORK",
    "urgency": "HIGH",
    "impact": "HIGH"
  }'
```
**Response:**
```json
{
  "id": "7b8e5c2d-94a1-4328-b8d4-5394e1e8609a",
  "title": "VPN Gateway Unresponsive",
  "description": "Remote engineering staff unable to connect to the US-East VPN concentrator.",
  "category": "NETWORK",
  "priority": "P1",
  "status": "NEW",
  "reporterId": "e12b7a9f-31d0-42f1-bc8e-17d91e605d3b",
  "createdAt": "2026-11-22T12:00:00Z"
}
```

### 3. Get AI-Assisted Technician Recommendations (Admin)
```bash
curl -X GET "http://localhost:8000/api/v1/technicians/recommendations?incidentId=7b8e5c2d-94a1-4328-b8d4-5394e1e8609a" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```
**Response:**
```json
{
  "incidentId": "7b8e5c2d-94a1-4328-b8d4-5394e1e8609a",
  "recommendedTechnicians": [
    {
      "technicianId": "c3d4e5f6-a7b8-4901-c2d3-e4f5a6b7c8d9",
      "username": "tech_alice",
      "score": 0.95,
      "currentWorkload": 1,
      "maxWorkload": 5,
      "matchedSkills": ["NETWORK", "SECURITY"],
      "reasoning": "High proficiency in NETWORK and available workload capacity."
    }
  ]
}
```

### 4. Progress Incident Lifecycle State (Technician)
```bash
curl -X PATCH "http://localhost:8000/api/v1/incidents/7b8e5c2d-94a1-4328-b8d4-5394e1e8609a/status" \
  -H "Authorization: Bearer <TECH_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_PROGRESS",
    "resolutionDetails": "Restarted redundant gateway daemon and flushed stale routing table entries."
  }'
```

---

## 18. Error Handling and Validation

I-ITSM enforces strict, predictable error contracts across all endpoints:

1. **Pydantic Validation Errors (`422 Unprocessable Entity`):** Occur when request payloads fail type constraints or missing required fields.
2. **Domain Rule Exceptions (`400 Bad Request`):** Raised by domain aggregates (e.g., `InvalidStateTransitionException`, `TechnicianOverloadedException`).
3. **Authentication Failures (`401 Unauthorized`):** Invalid, expired, or missing JWT Bearer tokens.
4. **Access Control Denials (`403 Forbidden`):** Authenticated user role does not meet the endpoint's permission criteria.
5. **Entity Not Found (`404 Not Found`):** Requested resource UUID does not exist.

### Uniform JSON Error Envelope
```json
{
  "detail": "Cannot transition incident from 'NEW' to 'IN_PROGRESS'. Incident must first be 'ASSIGNED' and 'ACKNOWLEDGED'."
}
```

The React frontend handles these errors centrally via `frontend/src/utils/errorHandler.js`, extracting error messages from any server response structure and displaying non-intrusive banner or toast alerts to the user.

---

## 19. Current Implementation Status

| Capability / Module | Status | Verification & Test Coverage |
|---|---|---|
| **M1: User & Authentication** | Implemented | JWT auth, bcrypt, RBAC, service catalogue, categories. Tested in `tests/api/test_auth.py`, `tests/api/test_users.py`. |
| **M1: User Promotion Modal** | Implemented | Two-phase user role promotion to technician with skill assignment modal in frontend. |
| **M2: Incident Lifecycle** | Implemented | 8-state state machine, comments, priority matrix. Tested in `tests/unit/test_incident_lifecycle.py`. |
| **M2: Duplicate Detection & Merging** | Implemented | Similarity scoring, duplicate recommendation, merge tickets. Tested in `tests/api/test_incidents_api.py`. |
| **M2: Soft-Archiving** | Implemented | Archive closed tickets, view archived records, restore filters. Tested in `tests/api/test_incidents_api.py`. |
| **M3: Technician Management** | Implemented | Workload capacities, skills, availability toggles. Tested in `tests/api/test_technicians_api.py`. |
| **M3: Assignment Strategies** | Implemented | Skill-Based & Least-Loaded algorithms. Tested in `tests/unit/test_assignment_strategies.py`. |
| **M3: AI Recommendation Engine** | Implemented | Async HTTPX adapter + mock provider. Tested in `tests/unit/test_recommendations.py`. |
| **M4: SLA Monitoring Daemon** | Implemented | 60s periodic background sweep, warnings at $\ge 80\%$, breaches. Tested in `tests/integration/test_sla_monitoring.py`. |
| **M4: Event-Driven Bus** | Implemented | `InProcessEventBus` decoupling domain mutations from audit logs and notifications. |
| **M4: In-App Notifications** | Implemented | Unread counters, read state updates, frontend toast popups. Tested in `tests/api/test_notifications.py`. |
| **M4: Audit Ledger** | Implemented | Immutable append-only logging of lifecycle and admin events. Tested in `tests/api/test_audit.py`. |
| **Frontend UI Portals** | Implemented | Employee, Technician, and Admin dashboards with Vite production build verification. |
| **Test Suite** | Implemented | 273 automated tests passing in $< 4$ seconds with Ruff linter clean. |

---

## 20. Future Enhancements

The following features represent architectural opportunities for future development:

1. **WebSocket / Server-Sent Events (SSE):** Replace the 15-second client polling interval for notifications with real-time bidirectional WebSocket connections.
2. **Multi-Tenant Organization Support:** Partition incident queues, technicians, and SLA policies across multiple tenant organizations with data isolation.
3. **Enterprise Single Sign-On (SSO):** Integrate SAML 2.0 and OIDC (Okta, Azure AD, Google Workspace) identity providers.
4. **Predictive SLA Machine Learning:** Train statistical models on historical resolution durations to predict SLA breaches before ticket assignment.
5. **Mobile Applications:** Develop cross-platform React Native companion apps for field technicians to receive push notifications and update ticket statuses on-site.

---

## 21. Contributing Guidelines & Project Team

### Development Workflow
1. Fork or branch from `integration/system-integration`.
2. Ensure Python 3.12+ and Node.js 20+ are installed.
3. Make atomic, well-documented changes adhering to SOLID design principles.
4. Run the complete backend test suite: `pytest`.
5. Run the static code linter: `ruff check app tests`.
6. Verify the frontend production build: `npm run build` in `frontend/`.
7. Submit a clean Pull Request with detailed descriptions of changes.

### Academic Project Team (CS F213 / MAC F212)

| Module | Engineer | Primary Responsibilities |
|---|---|---|
| **Module 1 (M1)** | **Anay Goenka** | Identity & Access Management, JWT Security, User Administration, Service Catalogue, Category Taxonomies, System Metrics |
| **Module 2 (M2)** | **Anshul Naik** | Incident Management, Lifecycle State Machine, Deterministic Priority Scoring, Comments, Duplicate Merging, Soft-Archiving |
| **Module 3 (M3)** | **Krish Jain** | Technician Management, Skill Matrices, Capacity Constraints, Assignment Strategies (Skill-Based & Least-Loaded), AI Recommendation Engine |
| **Module 4 (M4)** | **Anirudh Yendalur** | SLA Policies & Compliance Engine, 60s Background Sweeper, Event-Driven Bus (Observer Pattern), In-App Notifications, Immutable Audit Trail |

---

## 22. Detailed Documentation Index

For comprehensive technical specifications, please consult the dedicated documentation files:
- [Installation & Operations Guide](file:///Users/wonderer/Desktop/I-ITSM/docs/INSTALLATION_GUIDE.md) — Multi-OS installation, Docker Compose, seeding, and troubleshooting.
- [User & Operations Guide](file:///Users/wonderer/Desktop/I-ITSM/docs/USER_GUIDE.md) — Role-based operations manual (Employee, Technician, Admin), role promotion & profile setup modal.
- [Architecture Specification](file:///Users/wonderer/Desktop/I-ITSM/docs/ARCHITECTURE.md) — System layering, modular monolith boundaries, and event-driven bus.
- [REST API Documentation](file:///Users/wonderer/Desktop/I-ITSM/docs/API_DOCUMENTATION.md) — Complete endpoint reference, schemas, JWT auth, and uniform error envelope.
- [Database Design & Migrations](file:///Users/wonderer/Desktop/I-ITSM/docs/DATABASE_DESIGN.md) — Relational schema, ER diagram, table constraints, and Alembic migrations 001–006.
- [OOP Design & Patterns](file:///Users/wonderer/Desktop/I-ITSM/docs/OOP_DESIGN.md) — 6 OOP pillars, 7 design patterns, and SOLID principles.
- [Assignment Algorithms & AI](file:///Users/wonderer/Desktop/I-ITSM/docs/ASSIGNMENT_ALGORITHMS.md) — Skill-Based, Least-Loaded formulas, AI adapter, privacy guarantee & fallback.
- [Module Documentation](file:///Users/wonderer/Desktop/I-ITSM/docs/MODULE_DOCUMENTATION.md) — Deep-dive into Modules M1, M2, M3, and M4 responsibilities.
- [Testing & Quality Verification](file:///Users/wonderer/Desktop/I-ITSM/docs/TESTING.md) — Automated test suite (273 tests), offline harness, and CI matrix.
- [Frontend Application Specification](file:///Users/wonderer/Desktop/I-ITSM/frontend/README.md) — React 18 architecture, state management, and error handling.
- [Final Academic Project Report (PDF)](file:///Users/wonderer/Desktop/I-ITSM/docs/final-report/I-ITSM_Final_Project_Report.pdf) — Comprehensive 73-page academic final report in PDF format.
- [Final Academic Project Report (LaTeX Source)](file:///Users/wonderer/Desktop/I-ITSM/docs/final-report/I-ITSM_Final_Project_Report.tex) — Complete editable LaTeX source.
