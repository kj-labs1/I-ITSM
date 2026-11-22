# I-ITSM — REST API Documentation

**Base API Path:** `/api/v1`  
**Authentication Scheme:** Bearer JWT in `Authorization` header (`Authorization: Bearer <token>`)  
**Data Format:** JSON (`Content-Type: application/json`), all payloads use `camelCase` keys.

---

## 1. Authentication & Platform Endpoints (Module 1)

### 1.1 User Registration
- **Route:** `POST /api/v1/auth/register` (Public)
- **Request Body:**
  ```json
  {
    "username": "jane_doe",
    "email": "jane@example.com",
    "fullName": "Jane Doe",
    "password": "Password123!"
  }
  ```
- **Response (201 Created):** Returns user object with role `EMPLOYEE`.

### 1.2 User Login
- **Route:** `POST /api/v1/auth/login` (Public, OAuth2 Form Data)
- **Form Parameters:** `username` (or email) and `password`.
- **Response (200 OK):**
  ```json
  {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "tokenType": "bearer"
  }
  ```

### 1.3 Current User Profile
- **Route:** `GET /api/v1/auth/me` (Authenticated)
- **Response (200 OK):**
  ```json
  {
    "id": "c3a1b2d4-1234-5678-90ab-cdef12345678",
    "username": "jane_doe",
    "email": "jane@example.com",
    "fullName": "Jane Doe",
    "role": "EMPLOYEE",
    "isActive": true
  }
  ```

### 1.4 User Management (Admin Only)
- `GET /api/v1/users`: List all users with query parameters (`skip`, `limit`, `role`, `isActive`, `search`).
- `GET /api/v1/users/summary`: Aggregated counts of total, active, and role-segmented accounts.
- `GET /api/v1/users/{user_id}`: Retrieve detailed user account information.
- `PATCH /api/v1/users/{user_id}`: Update user full name, role (e.g. promote to `TECHNICIAN` or `ADMIN`), or active status.
- `DELETE /api/v1/users/{user_id}`: Soft-deactivate user account (prevents self-deactivation).

### 1.5 Service Catalogue & Incident Categories
- `GET /api/v1/services`: List active IT enterprise services.
- `POST /api/v1/services` (Admin): Create service item with `businessCriticality` ($1$ to $5$).
- `PATCH /api/v1/services/{service_id}` (Admin): Update service details.
- `DELETE /api/v1/services/{service_id}` (Admin): Soft-deactivate service.
- `GET /api/v1/categories`: List incident categories and required skill mappings.
- `POST /api/v1/categories` (Admin): Create incident category mapping.
- `PATCH /api/v1/categories/{category_id}` (Admin): Update category mapping.
- `DELETE /api/v1/categories/{category_id}` (Admin): Deactivate category.
- `GET /api/v1/reports/summary` (Admin): Aggregated executive dashboard KPI metrics.

---

## 2. Incident Management & Lifecycle (Module 2)

### 2.1 Create Incident
- **Route:** `POST /api/v1/incidents` (`EMPLOYEE`, `ADMIN`)
- **Request Body:**
  ```json
  {
    "serviceId": "a1b2c3d4-0000-0000-0000-000000000001",
    "category": "NETWORK",
    "description": "Core switch in Rack 4 is dropping packets intermittently.",
    "impact": 4,
    "urgency": 5,
    "businessCriticality": 4,
    "requiredSkill": "NETWORK"
  }
  ```
- **Response (201 Created):** Returns incident with canonical code `INC-xxxxxxxx`, calculated priority ($P1$–$P4$), and initial status `NEW`.

### 2.2 List & Query Incidents
- **Route:** `GET /api/v1/incidents` (Authenticated)
  - *Employees:* see only their submitted tickets.
  - *Technicians:* see tickets assigned to them.
  - *Admins:* see all organization incidents.
- **Query Parameters:** `status`, `category`, `priority`, `serviceId`, `search`, `skip`, `limit`.

### 2.3 Incident Details & Comments
- `GET /api/v1/incidents/{id}`: Detailed view including SLA deadlines and comments thread.
- `PATCH /api/v1/incidents/{id}`: Edit incident description, impact, or urgency (triggers priority re-calculation).
- `POST /api/v1/incidents/{id}/comments`: Post a collaborative update note.

### 2.4 Lifecycle State Machine Transitions
- **Route:** `PATCH /api/v1/incidents/{id}/status` (`TECHNICIAN`, `ADMIN`)
- **Request Body:**
  ```json
  {
    "status": "RESOLVED",
    "resolutionDetails": "Replaced damaged Cat6 cable and verified zero CRC errors."
  }
  ```
- **State Validation Rules:**
  - `ASSIGNED` $\rightarrow$ `ACKNOWLEDGED` (Technician marks ticket seen).
  - `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` (Diagnostic work begins).
  - `IN_PROGRESS` $\rightarrow$ `RESOLVED` (Requires non-empty `resolutionDetails`).
  - `RESOLVED` $\rightarrow$ `VERIFIED` (Reporter/Admin confirms service restored).
  - `VERIFIED` $\rightarrow$ `CLOSED` (Ticket finalized).

### 2.5 Duplicate Detection, Merging & Archiving
- `GET /api/v1/incidents/{id}/duplicates` (Admin): Query token similarity matches against open tickets.
- `POST /api/v1/incidents/{primary_id}/merge` (Admin): Merge secondary incident into primary incident.
- `PATCH /api/v1/incidents/{id}/archive` (Admin): Soft-archive closed ticket to read-only compliance storage.
- `GET /api/v1/incidents/archived` (Admin): List archived tickets.

---

## 3. Technician Management & Allocation (Module 3)

### 3.1 Technician Profiles & Skills
- `GET /api/v1/technicians` (Admin): List all technicians including users with role `TECHNICIAN` whose profiles are not yet configured (`hasProfile = false`).
- `POST /api/v1/technicians` (Admin): Create an operational profile for an existing technician user:
  ```json
  {
    "userId": "c3a1b2d4-1234-5678-90ab-cdef12345678",
    "experienceYears": 4,
    "maxCapacity": 5,
    "availability": "AVAILABLE"
  }
  ```
- `GET /api/v1/technicians/{id}`: Retrieve detailed technician profile.
- `PATCH /api/v1/technicians/{id}`: Update experience or max capacity.
- `PATCH /api/v1/technicians/{id}/availability`: Toggle status between `AVAILABLE` and `BUSY`.
- `POST /api/v1/technicians/{id}/skills`: Add skill with proficiency ($1$ to $5$).
- `DELETE /api/v1/technicians/{id}/skills/{skill_name}`: Remove skill.

### 3.2 Smart Recommendations & Incident Assignment
- `GET /api/v1/technicians/recommendations` (Admin): Query ranked candidates for an incident using `SKILL_BASED` or `LEAST_LOADED` strategies with optional LLM reasoning.
- `POST /api/v1/incidents/{id}/assign` (Admin): Assign technician to ticket. Re-validates availability, skill matching, and capacity headroom before publishing `IncidentAssignedEvent`.

---

## 4. SLA, Notifications & Audit Logs (Module 4)

### 4.1 SLA Governance
- `GET /api/v1/sla/policies`: List target response and resolution durations in hours per priority ($P1$–$P4$).
- `GET /api/v1/sla/summary`: Overview of total tracked, compliant, warning, and breached tickets.
- `GET /api/v1/sla/violations`: List all breached incidents.
- `POST /api/v1/sla/check`: Trigger an immediate manual evaluation sweep of all active SLA timers.

### 4.2 User Notifications
- `GET /api/v1/notifications`: List personal notifications with read/unread flags.
- `GET /api/v1/notifications/unread/count`: Return integer count of unread notifications.
- `PATCH /api/v1/notifications/{id}/read`: Mark notification as read.
- `POST /api/v1/notifications/read-all`: Mark all personal notifications as read.

### 4.3 Audit Logging
- `GET /api/v1/audit` (Admin): Query immutable chronological audit trail with filters (`actorId`, `action`, `startDate`, `endDate`, `skip`, `limit`).

---

## 5. Standard Error Envelope

All error responses across all modules return a consistent JSON schema:

```json
{
  "timestamp": "2026-11-22T14:00:00Z",
  "status": 409,
  "errorCode": "CAPACITY_EXCEEDED",
  "message": "Technician has reached maximum active capacity (5/5)",
  "path": "/api/v1/incidents/11111111-2222-3333-4444-555555555555/assign"
}
```
