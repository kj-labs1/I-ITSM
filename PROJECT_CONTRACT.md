# I-ITSM Shared Project Contract

**Project Title:** Intelligent IT Service Management & Incident Resolution System  
**Course:** CS F213 / MAC F212 — Object-Oriented Programming (Semester I, 2026–2027)  
**Status:** Binding Agreement & Proposed Architecture Evolution (Draft for Team Approval)  
**Effective Date:** 5 November 2026 (Contract Freeze)

---

## 1. Architecture & Technology Stack Proposal

### 1.1 Context and Rationale
The team handbook initially outlined a Java + Spring Boot backend. The course project brief explicitly allows technology freedom (including FastAPI, Django, Spring Boot, ASP.NET Core). 

This proposal establishes a **Python 3.12+ / FastAPI / SQLAlchemy 2.x / PostgreSQL** architecture.

| Dimension | Team Handbook Agreement | Proposed Python Architecture | Rationale / Benefits |
|---|---|---|---|
| **Backend Language** | Java 17+ | Python 3.12+ | Native ecosystem for AI/LLM integration; concise OOP models. |
| **Framework** | Spring Boot | FastAPI | Async I/O, auto-generated OpenAPI 3.1 docs, Pydantic v2 validation. |
| **ORM / Persistence** | Spring Data JPA / Hibernate | SQLAlchemy 2.x (Async) | Explicit query control, async execution, clean Repository pattern. |
| **Migrations** | Flyway | Alembic | Direct Python migration scripts sharing SQLAlchemy ORM metadata. |
| **Testing** | JUnit 5 | pytest + pytest-asyncio | Parametrized tests, fast execution, fixture dependency injection. |
| **AI Integration** | Not specified | Native async adapter | Direct integration with OpenAI, Anthropic, Gemini, or mock adapters. |

> [!IMPORTANT]
> **Status of Change:** This transition is **PROPOSED** to the four-member team. The backend foundation implemented here demonstrates complete compatibility with all functional agreements, data contracts, and REST paths defined in the Team Handbook.

---

## 2. Common Conventions & Data Standards

1. **REST Base Path:** `/api/v1`
2. **JSON Serialization:** `camelCase` for all request/response fields (e.g. `technicianId`, `incidentCode`, `maxCapacity`).
3. **Internal Python Naming:** `snake_case` for variables, attributes, and methods (e.g. `technician_id`, `max_capacity`).
4. **Primary Keys:** UUID v4 format serialized as lowercase 36-character hyphenated strings.
5. **Timestamps:** ISO-8601 UTC with `Z` suffix (e.g. `2026-11-04T09:30:00Z`).
6. **Authentication:** Bearer JWT in the `Authorization` header (`Authorization: Bearer <token>`).
7. **Error Response Schema:** Uniform JSON error envelope across all modules:
   ```json
   {
     "timestamp": "2026-11-12T12:00:00Z",
     "status": 409,
     "errorCode": "DUPLICATE_ASSIGNMENT",
     "message": "Incident INC-1001 is already assigned to technician 550e8400-...",
     "path": "/api/v1/incidents/550e8400-.../assign"
   }
   ```

---

## 3. Shared Enums (Exact Shared Values)

All team members must use these exact enumeration tokens without renaming:

### 3.1 UserRole
`EMPLOYEE`, `TECHNICIAN`, `ADMIN`

### 3.2 Priority
`P1`, `P2`, `P3`, `P4`

### 3.3 IncidentStatus
`NEW`, `CLASSIFIED`, `ASSIGNED`, `ACKNOWLEDGED`, `IN_PROGRESS`, `RESOLVED`, `VERIFIED`, `CLOSED`

### 3.4 IncidentCategory
`HARDWARE`, `SOFTWARE`, `NETWORK`, `DATABASE`, `CLOUD`, `SECURITY`, `AUTHENTICATION`, `APPLICATION`, `STORAGE`

### 3.5 AssignmentStrategyType
`SKILL_BASED`, `LEAST_LOADED`

### 3.6 AvailabilityStatus
`AVAILABLE`, `BUSY`, `OFFLINE`, `ON_LEAVE`

---

## 4. Module Ownership Matrix

| Module | Owner | Core Responsibilities | Database Tables Owned | Master API Routes Owned |
|---|---|---|---|---|
| **Platform & Identity** | **Member 1** | User accounts, roles, auth tokens, IT services, incident categories, admin reporting | `users`, `employees`, `administrators`, `services`, `incident_categories` | `POST /api/v1/auth/login`<br>`POST /api/v1/auth/register`<br>`GET /api/v1/auth/me`<br>`/api/v1/users`<br>`/api/v1/services`<br>`/api/v1/categories`<br>`GET /api/v1/reports/summary` |
| **Incident Lifecycle** | **Member 2** | Incident creation, priority scoring, state transitions, comments, duplicate detection | `incidents`, `incident_comments` | `POST /api/v1/incidents`<br>`GET /api/v1/incidents`<br>`GET /api/v1/incidents/{id}`<br>`PATCH /api/v1/incidents/{id}`<br>`PATCH /api/v1/incidents/{id}/status`<br>`POST /api/v1/incidents/{id}/comments` |
| **Technician & Assignment** | **Member 3 (Us)** | Technician profiles, skills, availability, workload derivation, assignment strategies, LLM recommendations | `technicians`, `technician_skills` | `GET /api/v1/technicians`<br>`POST /api/v1/technicians`<br>`GET /api/v1/technicians/{id}`<br>`PATCH /api/v1/technicians/{id}`<br>`PATCH /api/v1/technicians/{id}/availability`<br>`/api/v1/technicians/{id}/skills`<br>`GET /api/v1/technicians/recommendations`<br>`POST /api/v1/incidents/{id}/assign` |
| **SLA & Automation** | **Member 4** | SLA tracking deadlines, breach warnings, audit trail logging, notification dispatching | `sla_policies`, `incident_sla_tracking`, `audit_logs`, `notifications` | `GET /api/v1/incidents/{id}/sla`<br>`GET /api/v1/sla/violations`<br>`GET /api/v1/notifications`<br>`PATCH /api/v1/notifications/{id}/read`<br>`GET /api/v1/incidents/{id}/audit` |

---

## 5. Cross-Module Integration Contracts

### 5.1 Member 3 $\rightarrow$ Member 1 (Identity Contract)
- **Shared Primary Key:** Technician uses the shared `users.id` UUID as its identity reference (`technicians.user_id`).
- **No Duplicate Identity:** Technician profiles contain only operational attributes (availability, skills, capacity). User account details (name, email, password) are managed solely by Member 1.
- **Authentication:** M3 endpoints extract `user_id` from the verified JWT payload.

### 5.2 Member 3 $\rightarrow$ Member 2 (Incident Contract)
- **Read Contract:** M3 consumes read-only `IncidentRef` containing `id`, `category`, `required_skill`, `priority`, `status`, `assigned_technician_id`.
- **Assignment Hand-Off:** M3 does **not** update the `incidents` table directly. M3 calls M2's agreed application boundary:
  ```python
  await incident_service.assign_technician(incident_id, technician_user_id, actor_id)
  ```
- **Workload Derivation:** Active workload is derived on-demand from M2's incident service via:
  ```python
  count = await incident_service.get_active_incident_count(technician_user_id)
  ```
  This eliminates competing workload counters.

### 5.3 Member 3 $\rightarrow$ Member 4 (Observer Pattern / Event Contract)
- On successful assignment, M3 publishes `IncidentAssignedEvent` via the shared `EventPublisher`:
  ```python
  event = IncidentAssignedEvent(
      incident_id=incident_uuid,
      technician_id=technician_user_uuid,
      actor_id=actor_user_uuid,
      strategy_used="SKILL_BASED",
      explanation="...",
  )
  await event_bus.publish(event)
  ```
- Member 4's listeners subscribe to `IncidentAssignedEvent` to generate audit records and dispatch notifications.

---

## 6. Documented Proposed Fields (Pending Team Approval)

The following fields are introduced in Module 3 to satisfy algorithm and capacity requirements:
1. `technicians.experience_years` (Integer, default 0): Required by the course brief to implement experience-based ranking and tie-breaking.
2. `technicians.max_capacity` (Integer, default 10): Required to enforce the "technician capacity limit" requirement from the evaluation rubric.
