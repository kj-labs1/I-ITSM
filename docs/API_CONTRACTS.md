# API Contracts Specification

**Prefix:** `/api/v1`  
**Standard Headers:**

- `Content-Type: application/json`
- `Authorization: Bearer <jwt-token>` (for protected routes)

---

## 1. Technician Management Endpoints (Module 3)

### 1.1 List Technicians

- **Method & Path:** `GET /api/v1/technicians`
- **Query Parameters:**
  - `skip` (int, default `0`)
  - `limit` (int, default `50`, max `100`)
- **Response 200 OK:**
  ```json
  [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "userId": "123e4567-e89b-12d3-a456-426614174000",
      "availability": "AVAILABLE",
      "experienceYears": 5,
      "maxCapacity": 10,
      "activeIncidentCount": 2,
      "remainingCapacity": 8,
      "skills": [
        {
          "id": "770e8400-e29b-41d4-a716-446655440001",
          "technicianId": "550e8400-e29b-41d4-a716-446655440000",
          "skillName": "NETWORK",
          "proficiencyLevel": 4,
          "createdAt": "2026-11-12T10:00:00Z",
          "updatedAt": "2026-11-12T10:00:00Z"
        }
      ],
      "createdAt": "2026-11-12T10:00:00Z",
      "updatedAt": "2026-11-12T10:00:00Z"
    }
  ]
  ```

### 1.2 Create Technician Profile

- **Method & Path:** `POST /api/v1/technicians`
- **Request Body:**
  ```json
  {
    "userId": "123e4567-e89b-12d3-a456-426614174000",
    "experienceYears": 4,
    "maxCapacity": 8,
    "skills": [
      {
        "skillName": "DATABASE",
        "proficiencyLevel": 4
      }
    ]
  }
  ```
- **Response 201 Created:** Returns created `TechnicianResponse`.
- **Response 409 Conflict:** If technician profile already exists for `userId`.

### 1.3 Get Technician Details

- **Method & Path:** `GET /api/v1/technicians/{technician_id}`
- **Response 200 OK:** Returns `TechnicianResponse`.
- **Response 404 Not Found:** If technician does not exist.

### 1.4 Update Technician Parameters

- **Method & Path:** `PATCH /api/v1/technicians/{technician_id}`
- **Request Body:**
  ```json
  {
    "experienceYears": 6,
    "maxCapacity": 12
  }
  ```
- **Response 200 OK:** Returns updated `TechnicianResponse`.

### 1.5 Update Availability Status

- **Method & Path:** `PATCH /api/v1/technicians/{technician_id}/availability`
- **Request Body:**
  ```json
  {
    "availability": "BUSY"
  }
  ```
- **Response 200 OK:** Returns updated `TechnicianResponse`.

### 1.6 Skills Management

- `GET /api/v1/technicians/{technician_id}/skills`: Returns `list[SkillResponse]`.
- `POST /api/v1/technicians/{technician_id}/skills`: Creates/updates skill proficiency.
- `DELETE /api/v1/technicians/{technician_id}/skills/{skill_name}`: Removes a skill.

---

## 2. Recommendation Endpoint (Module 3)

- **Method & Path:** `GET /api/v1/technicians/recommendations`
- **Query Parameters:**
  - `incidentId` (UUID, required): The target incident.
  - `strategy` (enum, optional): `SKILL_BASED` (default) or `LEAST_LOADED`.
  - `useLlm` (bool, optional, default `false`): When `true`, augments recommendations with LLM evaluation.
- **Response 200 OK:**
  ```json
  {
    "incidentId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "strategyUsed": "SKILL_BASED",
    "totalCandidates": 5,
    "eligibleCandidates": 2,
    "isLlmEnhanced": false,
    "evaluationTimeMs": 2.4,
    "recommendations": [
      {
        "technicianId": "550e8400-e29b-41d4-a716-446655440000",
        "technicianUserId": "123e4567-e89b-12d3-a456-426614174000",
        "score": 116.0,
        "rank": 1,
        "explanation": "Skill 'NETWORK' proficiency: 5/5, experience: 8 years, active incidents: 1/10, composite score: 116.0",
        "strategyUsed": "SKILL_BASED",
        "skillMatch": true,
        "isLlmEnhanced": false
      }
    ]
  }
  ```

---

## 3. Incident Assignment Endpoint (Module 3)

- **Method & Path:** `POST /api/v1/incidents/{incident_id}/assign`
- **Request Body:**
  ```json
  {
    "technicianId": "550e8400-e29b-41d4-a716-446655440000",
    "strategyUsed": "SKILL_BASED",
    "reason": "Top scoring candidate with 5/5 skill proficiency."
  }
  ```
- **Response 200 OK:**
  ```json
  {
    "incidentId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "incidentCode": "INC-1001",
    "technicianId": "550e8400-e29b-41d4-a716-446655440000",
    "technicianUserId": "123e4567-e89b-12d3-a456-426614174000",
    "status": "ASSIGNED",
    "strategyUsed": "SKILL_BASED",
    "assignedBy": "00000000-0000-0000-0000-000000000001"
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Invalid payload shape.
  - `404 Not Found`: Incident or technician does not exist.
  - `409 Conflict`:
    - `DUPLICATE_ASSIGNMENT`: Incident already assigned.
    - `TECHNICIAN_UNAVAILABLE`: Selected technician is not `AVAILABLE`.
    - `SKILL_MISMATCH`: Technician lacks incident's required skill.
    - `CAPACITY_EXCEEDED`: Technician active incidents $\ge$ max capacity.
    - `INVALID_ASSIGNMENT`: Incident is in an unassignable lifecycle state.

---

## 4. Platform & Identity Endpoints (Module 1)

All protected endpoints require `Authorization: Bearer <jwt-token>`.

### 4.1 Authentication

| Method | Endpoint                | Access        | Purpose                           |
| ------ | ----------------------- | ------------- | --------------------------------- |
| POST   | `/api/v1/auth/register` | Public        | Register an Employee account      |
| POST   | `/api/v1/auth/login`    | Public        | Authenticate and obtain a JWT     |
| GET    | `/api/v1/auth/me`       | Authenticated | Return the current user's profile |

Registration request:

```json
{
  "username": "jdoe",
  "email": "jdoe@example.com",
  "fullName": "Jane Doe",
  "password": "password123"
}
```

Registration creates an `EMPLOYEE` account. Passwords are stored as bcrypt hashes.

Login accepts form-encoded `username` and `password` fields. The username field also accepts an email address.

Login response:

```json
{
  "accessToken": "<jwt>",
  "tokenType": "bearer"
}
```

### 4.2 User Management

Administrator access is required for these endpoints.

| Method | Endpoint                  | Purpose                                 |
| ------ | ------------------------- | --------------------------------------- |
| GET    | `/api/v1/users`           | List users                              |
| GET    | `/api/v1/users/{user_id}` | Retrieve a user                         |
| PATCH  | `/api/v1/users/{user_id}` | Update user name, role or active status |
| DELETE | `/api/v1/users/{user_id}` | Deactivate a user                       |
| GET    | `/api/v1/users/summary`   | Return user counts by role and status   |

Example user update:

```json
{
  "role": "TECHNICIAN",
  "isActive": true
}
```

DELETE performs a soft deactivation. It does not permanently delete the user record. An administrator cannot deactivate or demote their own account.

### 4.3 IT Service Catalogue

| Method | Endpoint                        | Access        | Purpose              |
| ------ | ------------------------------- | ------------- | -------------------- |
| POST   | `/api/v1/services`              | ADMIN         | Create a service     |
| GET    | `/api/v1/services`              | Authenticated | List active services |
| GET    | `/api/v1/services/{service_id}` | Authenticated | Retrieve a service   |
| PATCH  | `/api/v1/services/{service_id}` | ADMIN         | Update a service     |
| DELETE | `/api/v1/services/{service_id}` | ADMIN         | Deactivate a service |

Example service creation:

```json
{
  "name": "Email Service",
  "description": "Corporate email and calendar services",
  "businessCriticality": 4
}
```

Business criticality must be an integer from 1 to 5. Administrators may use `?include_inactive=true` when listing services.

### 4.4 Incident Categories

| Method | Endpoint                           | Access        | Purpose                |
| ------ | ---------------------------------- | ------------- | ---------------------- |
| POST   | `/api/v1/categories`               | ADMIN         | Create a category      |
| GET    | `/api/v1/categories`               | Authenticated | List active categories |
| GET    | `/api/v1/categories/{category_id}` | Authenticated | Retrieve a category    |
| PATCH  | `/api/v1/categories/{category_id}` | ADMIN         | Update a category      |
| DELETE | `/api/v1/categories/{category_id}` | ADMIN         | Deactivate a category  |

Example category creation:

```json
{
  "category": "NETWORK",
  "description": "Network connectivity issues",
  "requiredSkill": "NETWORK"
}
```

Categories use the shared `IncidentCategory` enum. The `requiredSkill` value maps the incident category to the skill name used by the technician module. Administrators may use `?include_inactive=true` when listing categories.

### 4.5 Administrative Reports

| Method | Endpoint                  | Access | Purpose                                  |
| ------ | ------------------------- | ------ | ---------------------------------------- |
| GET    | `/api/v1/reports/summary` | ADMIN  | Summarise users, services and categories |

The response includes total, active and inactive counts for each platform-owned entity, together with user counts grouped by role.

### 4.6 Access Control

- Public registration always creates an Employee account.
- Login issues a signed JWT containing the user's UUID and role.
- Protected endpoints validate the Bearer token.
- Administrator operations enforce the `ADMIN` role.
- Inactive accounts cannot log in or access the current-user endpoint.
- Deactivation is implemented as a status change rather than permanent deletion.
