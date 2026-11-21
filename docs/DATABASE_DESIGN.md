# Database Design & Schema Specification

## 1. Relational Entity-Relationship Diagram

```mermaid
erDiagram
    users ||--o| technicians : "1:1 user_id"
    users ||--o{ incidents : "reporter_id"
    users ||--o{ incident_comments : "author_id"
    users ||--o{ notifications : "user_id"
    services ||--o{ incidents : "service_id"
    technicians ||--o{ technician_skills : "1:N owns (CASCADE)"
    technicians ||--o{ incidents : "assigned_technician_id (logical)"
    incidents ||--o{ incident_comments : "1:N (CASCADE)"
    incidents ||--o| incident_sla_tracking : "1:1 (logical)"
    incidents ||--o{ audit_logs : "1:N (logical)"
    incidents ||--o{ notifications : "1:N incident_id"
    sla_policies ||--o{ incident_sla_tracking : "policy_id"

    users {
        uuid id PK
        varchar username UK
        varchar email UK
        varchar full_name
        varchar password_hash
        varchar role "EMPLOYEE, TECHNICIAN, ADMIN"
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    services {
        uuid id PK
        varchar name UK
        text description
        integer business_criticality "1 to 5"
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    incident_categories {
        uuid id PK
        varchar category UK
        text description
        varchar required_skill
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    technicians {
        uuid id PK
        uuid user_id UK "References users.id"
        varchar availability "AVAILABLE, BUSY, OFFLINE, ON_LEAVE"
        integer experience_years ">= 0"
        integer max_capacity ">= 1"
        timestamp created_at
        timestamp updated_at
    }

    technician_skills {
        uuid id PK
        uuid technician_id FK "References technicians.id ON DELETE CASCADE"
        varchar skill_name "NETWORK, DATABASE, CLOUD..."
        integer proficiency_level "1 to 5"
        timestamp created_at
        timestamp updated_at
    }

    incidents {
        uuid id PK
        varchar incident_code UK "INC-xxxxxxxx"
        uuid reporter_id "References users.id"
        uuid service_id "References services.id"
        varchar category "HARDWARE, SOFTWARE, NETWORK..."
        varchar required_skill
        text description
        integer impact "1 to 5"
        integer urgency "1 to 5"
        integer business_criticality "1 to 5"
        varchar priority "P1, P2, P3, P4"
        varchar status "NEW, CLASSIFIED, ASSIGNED... CLOSED"
        uuid assigned_technician_id "References users.id"
        text resolution_details
        boolean is_archived "default false"
        timestamp archived_at
        uuid archived_by "References users.id"
        uuid merged_into_incident_id "References incidents.id"
        timestamp merged_at
        uuid merged_by "References users.id"
        timestamp created_at
        timestamp updated_at
    }

    incident_comments {
        uuid id PK
        uuid incident_id FK "References incidents.id ON DELETE CASCADE"
        uuid author_id "References users.id"
        text content
        timestamp created_at
        timestamp updated_at
    }

    sla_policies {
        uuid id PK
        varchar priority UK "P1, P2, P3, P4"
        integer response_time_hours
        integer resolution_time_hours
        timestamp created_at
        timestamp updated_at
    }

    incident_sla_tracking {
        uuid id PK
        uuid incident_id UK "Logical FK to incidents.id"
        uuid policy_id "References sla_policies.id"
        varchar priority "P1, P2, P3, P4"
        timestamp started_at
        timestamp response_due_at
        timestamp resolution_due_at
        timestamp first_responded_at
        timestamp resolved_at
        boolean response_breached "default false"
        boolean resolution_breached "default false"
        boolean warning_sent "default false"
        boolean breach_notified "default false"
        varchar status "RUNNING, MET, BREACHED, WARNING, PAUSED"
        timestamp created_at
        timestamp updated_at
    }

    audit_logs {
        uuid id PK
        uuid incident_id "Logical FK to incidents.id"
        uuid actor_id "References users.id"
        varchar action
        varchar event_type
        text previous_value
        text new_value
        text details
        timestamp occurred_at
        timestamp created_at
    }

    notifications {
        uuid id PK
        uuid user_id "References users.id"
        uuid incident_id "Logical FK to incidents.id"
        varchar notification_type
        varchar title
        text message
        boolean is_read "default false"
        timestamp read_at
        timestamp created_at
        timestamp updated_at
    }
```

---

## 2. Table Catalog & Ownership Matrix

| Table Name | Owning Module | Foreign Key References | Purpose |
|---|---|---|---|
| `users` | M1 (Identity) | None | System user accounts, credentials, and roles (`EMPLOYEE`, `TECHNICIAN`, `ADMIN`). |
| `services` | M1 (Platform) | None | IT service catalogue entries with business criticality ratings (1–5). |
| `incident_categories` | M1 (Platform) | None | Allowed incident classification categories and skill mappings. |
| `technicians` | M3 (Technicians) | `user_id` $\rightarrow$ `users.id` (Unique) | Operational technician profiles, availability, capacity, and experience. |
| `technician_skills` | M3 (Technicians) | `technician_id` $\rightarrow$ `technicians.id` (Cascade) | Technical competencies and skill proficiency levels (1–5). |
| `incidents` | M2 (Incidents) | `reporter_id`, `service_id`, `assigned_technician_id` | Core incident tickets, priority, state machine status, archiving, and merging. |
| `incident_comments` | M2 (Incidents) | `incident_id` $\rightarrow$ `incidents.id` (Cascade) | Collaboration notes and resolution discussion thread. |
| `sla_policies` | M4 (SLA) | None | Standard response and resolution time targets for priority levels $P1$–$P4$. |
| `incident_sla_tracking` | M4 (SLA) | `incident_id`, `policy_id` | Live tracking records of active response/resolution timers and breach flags. |
| `audit_logs` | M4 (Audit) | `incident_id`, `actor_id` | Immutable append-only audit trail capturing all lifecycle and administrative events. |
| `notifications` | M4 (Notifications)| `user_id`, `incident_id` | Recipient alert delivery inbox with read/unread flags. |

---

## 3. Indexing & Integrity Constraints

1. **Unique Constraints:**
   - `users.username` & `users.email`: Enforces login and email uniqueness.
   - `services.name`: Prevents duplicate service catalogue entries.
   - `incident_categories.category`: Prevents duplicate category definitions.
   - `technicians.user_id`: Enforces a strict 1-to-1 relationship between an M1 User and an M3 Technician profile.
   - `technician_skills (technician_id, skill_name)`: Prevents duplicate skill records on the same technician profile.
   - `incidents.incident_code`: Enforces canonical ticket code uniqueness (`INC-xxxxxxxx`).
   - `sla_policies.priority`: Guarantees exactly one policy per priority level ($P1$, $P2$, $P3$, $P4$).
   - `incident_sla_tracking.incident_id`: Enforces single active SLA tracking record per incident.
2. **Performance Indexes:**
   - `ix_incidents_status_priority`: Composite index optimizing queue filtering by status and urgency.
   - `ix_incidents_reporter_created`: Optimizes Employee "My Incidents" timeline queries.
   - `ix_incidents_assigned_status`: Optimizes Technician assigned workload queries.
   - `ix_incidents_is_archived`: Accelerates active vs. archived incident separation.
   - `ix_incidents_merged_into`: Optimizes child incident lookup during duplicate tree resolution.
   - `ix_technician_skills_skill_name`: Accelerates candidate filtering during recommendation runs.
   - `ix_notifications_user_read`: Optimizes unread notification polling (`/notifications/unread/count`).
   - `ix_audit_logs_incident_occurred`: Optimizes chronological audit trail retrieval.

---

## 4. Alembic Migration History

All schema revisions are version-controlled in `backend/migrations/versions/`:

| Revision | File Name | Description |
|---|---|---|
| `001` | `001_initial_technician_schema.py` | Creates initial `technicians` and `technician_skills` tables. |
| `002` | `002_create_users.py` | Creates `users` table with username, email, password hash, and role enum. |
| `003` | `003_services_and_categories.py` | Creates `services` and `incident_categories` tables. |
| `004` | `004_incidents_and_comments.py` | Creates `incidents` and `incident_comments` tables with foreign keys and status enums. |
| `005` | `005_sla_audit_notifications.py` | Creates `sla_policies`, `incident_sla_tracking`, `audit_logs`, and `notifications` tables. |
| `006` | `006_incident_archive_merge.py` | Adds archiving (`is_archived`, `archived_at`, `archived_by`) and merging (`merged_into_incident_id`, `merged_at`, `merged_by`) columns to `incidents`. |

### Applying Migrations
```bash
cd backend
alembic upgrade head
```
