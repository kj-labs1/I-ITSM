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

## 4. Incident Search, Filtering and Duplicate Detection (Module 2)

### 4.1 Search and Filter Incidents

- **Method & Path:** `GET /api/v1/incidents`

Supported query parameters:

| Parameter | Type | Description |
|---|---|---|
| `skip` | Integer | Number of records to skip; default 0 |
| `limit` | Integer | Maximum results; default 50, maximum 100 |
| `incidentId` | UUID | Exact incident ID |
| `incidentCode` | String | Partial, case-insensitive incident-code search |
| `dateFrom` | ISO-8601 datetime | Include incidents created at or after this time |
| `dateTo` | ISO-8601 datetime | Include incidents created at or before this time |
| `status` | IncidentStatus | Filter by lifecycle status |
| `priority` | Priority | Filter by P1, P2, P3 or P4 |
| `category` | IncidentCategory | Filter by incident category |
| `serviceId` | UUID | Filter by affected service |
| `assignedTechnicianId` | UUID | Filter by assigned technician |

Multiple filters are combined using AND logic.

The current employee-facing endpoint restricts results to the authenticated reporter's incidents.

- **Response 200 OK:** List of matching `IncidentResponse` objects.
- **Response 400 Bad Request:** Invalid date range or query parameters.

### 4.2 Find Potential Duplicate Incidents

- **Method & Path:** `GET /api/v1/incidents/{incident_id}/duplicates`

The backend compares the incident with other incidents satisfying all of these conditions:

1. Same affected service.
2. Same incident category.
3. Created within the previous 24 hours.
4. Description Jaccard similarity greater than or equal to 0.50.

Description preprocessing includes lowercase normalization, punctuation removal,
tokenization and common stop-word removal.

- **Response 200 OK:**

```json
[
  {
    "incidentId": "550e8400-e29b-41d4-a716-446655440000",
    "incidentCode": "INC-1001",
    "category": "NETWORK",
    "priority": "P2",
    "status": "NEW",
    "createdAt": "2026-11-14T10:00:00Z",
    "similarityScore": 0.75,
    "explanation": "Same affected service and category. Description similarity is 0.750, which meets the threshold of 0.50."
  }
]

### 4.3 Retrieve Incident

- Method: GET
- Path: `/api/v1/incidents/{incident_id}`

Returns IncidentDetailsResponse, including associated comments.

### 4.4 Update Incident

- Method: PATCH
- Path: `/api/v1/incidents/{incident_id}`

Permitted fields:
- description
- impact
- urgency

Priority is recalculated when scoring factors change.

### 4.5 Update Incident Status

- Method: PATCH
- Path: `/api/v1/incidents/{incident_id}/status`

Request:

{
  "status": "CLASSIFIED"
}

For RESOLVED:

{
  "status": "RESOLVED",
  "resolutionDetails": "Network configuration corrected."
}

Every successful transition must pass through IncidentLifecycle.

### 4.6 Add Incident Comment

- Method: POST
- Path: `/api/v1/incidents/{incident_id}/comments`

Request:

{
  "content": "Please investigate the network issue."
}

Success: 201 Created.

### 4.7 Common Error Responses

- 400: Invalid request or validation error.
- 403: Insufficient incident access permissions.
- 404: Incident not found.
- 409: Invalid lifecycle transition or business-rule conflict.

All errors use the shared I-ITSM error response envelope.

### 4.3 Search Validation Rules

The incident search endpoint applies the following validation rules:

1. `skip` must be greater than or equal to zero.
2. `limit` must be between 1 and 100.
3. Incident codes are trimmed before searching.
4. Incident codes containing only whitespace are rejected.
5. Date filters must use timezone-aware ISO-8601 timestamps.
6. Date filters are normalized to UTC before database queries.
7. `dateFrom` must be earlier than or equal to `dateTo`.

Relevant application error codes:

| Error Code | HTTP Status | Description |
|---|---:|---|
| `INVALID_PAGINATION` | 400 | Invalid skip or limit supplied to the application service |
| `INVALID_INCIDENT_CODE` | 400 | Incident code is blank or too long |
| `TIMEZONE_REQUIRED` | 400 | Date filter does not contain timezone information |
| `INVALID_DATE_RANGE` | 400 | dateFrom occurs after dateTo |

### 4.4 Duplicate Detection Policy

The duplicate detection policy is centralized in
`app/domain/incident/duplicate_policy.py`.

Default configuration:

- Lookback window: 24 hours.
- Jaccard similarity threshold: 0.50.
- Candidate service and category must match.
- Similarity results are ordered from highest to lowest.
- The explanation includes the similarity score and shared-token count.

Duplicate detection only identifies potential matches. It never automatically
deletes or merges incident records.
