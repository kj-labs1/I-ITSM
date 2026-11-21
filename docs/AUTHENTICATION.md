# Authentication & Role-Based Access Control (RBAC)

## 1. Authentication Overview

I-ITSM uses a stateless, token-based authentication mechanism powered by **JSON Web Tokens (JWT)** and **bcrypt** password hashing.

---

## 2. Password Security & Hashing

- **Algorithm:** `bcrypt` with dynamic salt generation.
- **Salt Rounds:** Default 12 rounds.
- **Storage:** Plaintext passwords are never stored, logged, or returned in any API response. Only the bcrypt hash string is persisted in `users.password_hash`.
- **Validation:** Passwords must be at least 8 characters long (maximum 128 characters).

---

## 3. JWT Token Structure & Lifecycle

### Token Issuance
Upon successful authentication at `POST /api/v1/auth/login`, the server returns a signed JWT bearer token.

### Standard Claims
```json
{
  "sub": "123e4567-e89b-12d3-a456-426614174000",
  "role": "EMPLOYEE",
  "exp": 1731672000
}
```
- `sub`: Canonical user UUID matching `users.id`.
- `role`: Permitted user role (`EMPLOYEE`, `TECHNICIAN`, or `ADMIN`).
- `exp`: Expiration timestamp in UTC (configured via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, default 60 minutes).

### Cryptographic Signing
Signed using `HS256` symmetric encryption with `JWT_SECRET_KEY`.

---

## 4. Role-Based Access Control (RBAC) Matrix

FastAPI dependencies (`get_current_user_id`, `require_role`) enforce strict role checks on every protected route:

| API Route Group | Permitted Roles | Description |
|---|---|---|
| `POST /auth/register` | Public | Registers a new account with default `EMPLOYEE` role. |
| `POST /auth/login` | Public | Authenticates credentials and returns signed JWT. |
| `GET /auth/me` | Any Authenticated | Retrieves current logged-in user identity. |
| `GET /incidents` | Any Authenticated | Filtered by role: Employee sees own; Tech sees assigned; Admin sees all. |
| `POST /incidents` | `EMPLOYEE`, `ADMIN` | Submit new incident ticket. |
| `PATCH /incidents/{id}` | `EMPLOYEE`, `ADMIN` | Update ticket details (Employee restricted to own tickets). |
| `PATCH /incidents/{id}/status` | `TECHNICIAN`, `ADMIN` | Advance incident lifecycle state machine. |
| `POST /incidents/{id}/comments` | Any Authenticated | Add collaborative note to ticket. |
| `POST /incidents/{id}/assign` | `ADMIN` | Assign or reassign technician to ticket. |
| `GET /technicians/recommendations` | `ADMIN` | Generate ranked smart candidate recommendations. |
| `PATCH /incidents/{id}/archive` | `ADMIN` | Soft-archive closed ticket to read-only compliance storage. |
| `POST /incidents/{id}/merge` | `ADMIN` | Merge duplicate tickets into primary ticket. |
| `GET /users`, `PATCH /users/{id}` | `ADMIN` | Manage user accounts and active statuses. |
| `GET /sla/summary`, `GET /sla/violations` | `ADMIN` | View SLA compliance reports and breach queues. |
| `POST /sla/check` | `ADMIN` | Trigger manual SLA breach evaluation sweep. |
| `GET /audit` | `ADMIN` | Query enterprise audit trails. |
| `GET /notifications` | Any Authenticated | Retrieve personal notification inbox. |
| `PATCH /technicians/{id}/availability` | `TECHNICIAN`, `ADMIN` | Toggle technician availability mode. |
