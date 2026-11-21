# REST API Contracts Specification

**Base URL Prefix:** `/api/v1`  
**Standard Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer <jwt-token>` (for authenticated endpoints)

---

## 1. Authentication & Platform (Module 1)

### 1.1 User Registration
- **Method & Route:** `POST /api/v1/auth/register`
- **Auth:** Public
- **Request Body:**
  ```json
  {
    "username": "alice_smith",
    "email": "alice@example.com",
    "fullName": "Alice Smith",
    "password": "SecurePassword123!"
  }
  ```
- **Response 201 Created:** Returns `UserResponse` with default `EMPLOYEE` role.
- **Response 409 Conflict:** If username or email is already registered.

### 1.2 User Login
- **Method & Route:** `POST /api/v1/auth/login`
- **Auth:** Public (Form Data: `OAuth2PasswordRequestForm` with `username` and `password`)
- **Response 200 OK:**
  ```json
  {
    "accessToken": "eyJhbGciOi...",
    "tokenType": "bearer"
  }
  ```
- **Response 401 Unauthorized:** If credentials are invalid or user account is deactivated.

### 1.3 Current User Profile
- **Method & Route:** `GET /api/v1/auth/me`
- **Auth:** Any authenticated user
- **Response 200 OK:** Returns logged-in `UserResponse` (`id`, `username`, `email`, `fullName`, `role`, `isActive`).

### 1.4 User Management (Admin Only)
- `GET /api/v1/users`: List all registered system users.
- `GET /api/v1/users/summary`: Returns total, active, inactive, and role-segmented user metrics.
- `GET /api/v1/users/{user_id}`: Retrieve detailed user account information.
- `PATCH /api/v1/users/{user_id}`: Update user full name, role, or active status.
- `DELETE /api/v1/users/{user_id}`: Soft-deactivate a user account (prevents self-deactivation).

### 1.5 Service Catalogue & Categories
- `GET /api/v1/services`: List active IT service catalogue entries.
- `POST /api/v1/services` (Admin): Create service catalogue item with `businessCriticality` (1–5).
- `PATCH /api/v1/services/{service_id}` (Admin): Update service details or criticality.
- `DELETE /api/v1/services/{service_id}` (Admin): Deactivate service.
- `GET /api/v1/categories`: List active incident categories and required skill mappings.
- `POST /api/v1/categories` (Admin): Create category mapping.
- `PATCH /api/v1/categories/{category_id}` (Admin): Update category definition.
- `DELETE /api/v1/categories/{category_id}` (Admin): Deactivate category.
- `GET /api/v1/reports/summary` (Admin): Returns aggregated executive KPI summary.

---

## 2. Incident Management & Lifecycle (Module 2)

### 2.1 Create Incident
- **Method & Route:** `POST /api/v1/incidents`
- **Auth:** Authenticated user (`EMPLOYEE` or `ADMIN`)
- **Request Body:**
  ```json
  {
    "serviceId": "550e8400-e29b-41d4-a716-446655440000",
    "category": "DATABASE",
    "description": "Production PostgreSQL cluster experiencing query timeouts.",
    "impact": 4,
    "urgency": 5,
    "businessCriticality": 4,
    "requiredSkill": "DATABASE"
  }
  ```
- **Response 201 Created:** Returns `IncidentResponse` with deterministic calculated priority (`P1`–`P4`), initial status `NEW`, and canonical incident code `INC-xxxxxxxx`.

### 2.2 List Incidents
- **Method & Route:** `GET /api/v1/incidents`
- **Query Parameters:** `status`, `category`, `priority`, `serviceId`, `reporterId`, `assignedTechnicianId`, `search`, `skip`, `limit`
- **Role-Based Visibility:**
  - `EMPLOYEE`: Returns only incidents created by the calling user.
  - `TECHNICIAN`: Returns incidents assigned to the calling technician.
  - `ADMIN`: Returns all enterprise incidents.

### 2.3 Incident Details & Update
- `GET /api/v1/incidents/{incident_id}`: Returns `IncidentDetailsResponse` with associated comments.
- `PATCH /api/v1/incidents/{incident_id}`: Update incident description, impact, or urgency (recalculates priority).
- `POST /api/v1/incidents/{incident_id}/comments`: Add comment note (`authorId` inferred from JWT).

### 2.4 Status Lifecycle Transitions
- **Method & Route:** `PATCH /api/v1/incidents/{incident_id}/status`
- **Request Body:**
  ```json
  {
    "status": "IN_PROGRESS",
    "resolutionDetails": null
  }
  ```
- **State Machine Rules:** Validates allowed transitions (`NEW` $\rightarrow$ `CLASSIFIED` $\rightarrow$ `ASSIGNED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED` $\rightarrow$ `VERIFIED` $\rightarrow$ `CLOSED`). Transitions to `RESOLVED` require non-empty `resolutionDetails`.

### 2.5 Duplicate Detection & Merging
- `GET /api/v1/incidents/{incident_id}/duplicates`: Trigram/keyword similarity scoring returning potential duplicates.
- `POST /api/v1/incidents/{incident_id}/merge` (Admin): Merges duplicate ticket into primary incident; automatically closes secondary ticket, links `merged_into_incident_id`, and creates audit log entries.

### 2.6 Incident Archiving
- `PATCH /api/v1/incidents/{incident_id}/archive` (Admin): Soft-archives a closed incident into read-only audit-compliant storage.
- `GET /api/v1/incidents/archived` (Admin): Lists historical soft-archived incidents.

---

## 3. Technician Management & Recommendations (Module 3)

### 3.1 List Technicians
- **Method & Route:** `GET /api/v1/technicians`
- **Auth:** Any authenticated user
- **Response 200 OK:**
  ```json
  [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "userId": "123e4567-e89b-12d3-a456-426614174000",
      "username": "tech_charlie",
      "fullName": "Charlie Technician",
      "email": "charlie@example.com",
      "availability": "AVAILABLE",
      "experienceYears": 6,
      "maxCapacity": 10,
      "activeIncidentCount": 2,
      "remainingCapacity": 8,
      "skills": [
        {
          "id": "770e8400-e29b-41d4-a716-446655440001",
          "technicianId": "550e8400-e29b-41d4-a716-446655440000",
          "skillName": "DATABASE",
          "proficiencyLevel": 5
        }
      ]
    }
  ]
  ```

### 3.2 Smart Recommendations
- **Method & Route:** `GET /api/v1/technicians/recommendations`
- **Auth:** Admin only
- **Query Parameters:**
  - `incidentId` (UUID, required): Target incident to evaluate.
  - `strategy` (enum, default `SKILL_BASED`): `SKILL_BASED` or `LEAST_LOADED`.
  - `useLlm` (boolean, default `false`): Enables optional AI ranking augmentation.
- **Response 200 OK:** Returns `RecommendationResponse` with candidate rankings, composite match scores, explainable reasoning strings, and LLM enhancement indicators.

### 3.3 Incident Assignment
- **Method & Route:** `POST /api/v1/incidents/{incident_id}/assign`
- **Auth:** Admin only
- **Request Body:**
  ```json
  {
    "technicianId": "123e4567-e89b-12d3-a456-426614174000"
  }
  ```
- **Validation:** Concurrently checks technician availability, skill match, and guarantees active workload does not exceed `maxCapacity`. Transitions incident to `ASSIGNED` and fires `IncidentAssignedEvent`.

### 3.4 Operational Profile & Skills Management
- `PATCH /api/v1/technicians/{technician_id}` (Admin): Updates `experienceYears` and `maxCapacity`.
- `PATCH /api/v1/technicians/{technician_id}/availability`: Updates operational availability (`AVAILABLE` $\leftrightarrow$ `BUSY`).
- `GET /api/v1/technicians/{technician_id}/skills`: Retrieves skill portfolio.
- `POST /api/v1/technicians/{technician_id}/skills`: Adds or updates skill proficiency (1–5).
- `DELETE /api/v1/technicians/{technician_id}/skills/{skill_name}`: Removes a skill.

---

## 4. SLA, Notifications & Audit Trail (Module 4)

### 4.1 SLA Policies & Sweeps
- `GET /api/v1/sla/policies`: List target response and resolution durations for $P1$, $P2$, $P3$, and $P4$.
- `POST /api/v1/sla/policies` (Admin): Create SLA policy.
- `PATCH /api/v1/sla/policies/{priority}` (Admin): Update target hours for a priority level.
- `GET /api/v1/sla/summary` (Admin): Returns overall compliance percentage, total tracked, breached, and approaching-warning counts.
- `GET /api/v1/sla/violations` (Admin): Lists breached incidents and tickets approaching deadline.
- `POST /api/v1/sla/check` (Admin): Manually triggers an on-demand breach evaluation sweep.
- `GET /api/v1/incidents/{incident_id}/sla`: Returns live tracking status, response/resolution deadlines, and breach flags for a ticket.

### 4.2 Notifications
- `GET /api/v1/notifications`: List recent notifications for the logged-in user.
- `GET /api/v1/notifications/unread`: List unread notifications.
- `GET /api/v1/notifications/unread/count`: Lightweight counter endpoint for real-time badge polling.
- `PATCH /api/v1/notifications/{notification_id}/read`: Mark specific notification as read.
- `PATCH /api/v1/notifications/read-all`: Mark all notifications as read for current user.

### 4.3 Audit Trail
- `GET /api/v1/audit` (Admin): Query enterprise-wide audit logs with filters (`incident_id`, `actor_id`, `action`, `event_type`, `date_from`, `date_to`).
- `GET /api/v1/incidents/{incident_id}/audit`: Returns chronological immutable audit event history for a specific incident.
