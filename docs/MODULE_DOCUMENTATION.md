# Module Documentation Specification

I-ITSM is partitioned into four decoupled modules with clean ownership boundaries, distinct domain entities, dedicated database tables, and explicit cross-module interfaces.

---

## Module 1: Identity, Platform & Administration (M1)

### Responsibility
Manages user accounts, credentials, role-based authorization, enterprise service catalogue entries, incident category configurations, and executive reporting metrics.

### Key Components
- **Entities & Models:**
  - `UserModel` (`users` table): Primary user identity with `username`, `email`, `full_name`, `password_hash`, `role` (`EMPLOYEE`, `TECHNICIAN`, `ADMIN`), and `is_active`.
  - `ServiceModel` (`services` table): IT services with `business_criticality` rating ($1$ to $5$).
  - `CategoryModel` (`incident_categories` table): Incident category names mapped to `required_skill`.
- **API Endpoints:**
  - `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`
  - `/api/v1/users`, `/api/v1/users/summary`, `/api/v1/users/{user_id}`
  - `/api/v1/services`, `/api/v1/services/{service_id}`
  - `/api/v1/categories`, `/api/v1/categories/{category_id}`
  - `/api/v1/reports/summary`
- **Security & Password Hashing:**
  - Salted hash generation using `bcrypt`.
  - Signed JWT token generation containing `sub` (User UUID) and `role` claims with configurable expiration.
- **Cross-Module Integration:**
  - Provides the canonical User UUID (`users.id`) used by M2 (`reporter_id`, `assigned_technician_id`), M3 (`technicians.user_id`), and M4 (`actor_id`, `notifications.user_id`).

---

## Module 2: Incident Management & Lifecycle (M2)

### Responsibility
Owns the core incident entity, state machine lifecycle transitions, priority calculation, collaboration comments, duplicate similarity detection, duplicate ticket merging, and soft-archiving.

### Key Components
- **Entities & Models:**
  - `IncidentModel` (`incidents` table): Stores canonical incident ID, unique code `INC-xxxxxxxx`, classification, description, impact/urgency ($1$–$5$), calculated priority ($P1$–$P4$), status, assigned technician, resolution details, archiving attributes (`is_archived`, `archived_at`, `archived_by`), and merge references (`merged_into_incident_id`, `merged_at`, `merged_by`).
  - `IncidentCommentModel` (`incident_comments` table): Collaboration notes linked to incidents.
- **Priority Calculation Matrix (`PriorityCalculator`):**
  - Evaluates business criticality, urgency, and impact:
    $$\text{Priority Score} = (\text{Impact} \times 0.4) + (\text{Urgency} \times 0.4) + (\text{Business Criticality} \times 0.2)$$
  - Maps score deterministically: $\ge 4.0 \rightarrow P1$, $\ge 3.0 \rightarrow P2$, $\ge 2.0 \rightarrow P3$, $< 2.0 \rightarrow P4$.
- **Lifecycle State Machine:**
  - Strict forward state validation: `NEW` $\rightarrow$ `CLASSIFIED` $\rightarrow$ `ASSIGNED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED` $\rightarrow$ `VERIFIED` $\rightarrow$ `CLOSED`.
  - Enforces required fields upon resolution (`resolutionDetails`).
- **Duplicate Incident Detection (`DuplicateDetector`):**
  - Trigram/TF-IDF tokenization comparing incident description text against existing open incidents in the same category; calculates similarity scores ($0.0$ to $1.0$).
- **Archiving & Merging:**
  - Soft-archives closed tickets to preserve historical records in read-only mode for audit compliance.
  - Merges duplicate secondary incidents into primary incidents, setting secondary status to `CLOSED` and pointing `merged_into_incident_id` to the primary incident.

---

## Module 3: Technician & Assignment Engine (M3)

### Responsibility
Maintains operational technician profiles, acquired skills with proficiency ratings, availability states, active workload tracking, deterministic assignment algorithms, and AI-assisted candidate recommendations.

### Key Components
- **Entities & Models:**
  - `TechnicianModel` (`technicians` table): Linked 1:1 with M1 `users.id` via `user_id`. Tracks `availability` (`AVAILABLE`, `BUSY`, `OFFLINE`, `ON_LEAVE`), `experience_years`, and `max_capacity`. Eagerly loads user account data (`username`, `full_name`, `email`) and skills portfolio.
  - `TechnicianSkillModel` (`technician_skills` table): Stores skill names and numeric proficiency levels ($1$ to $5$).
- **Assignment Strategies (Strategy Pattern):**
  - `SkillBasedAssignmentStrategy`: Evaluates required skill proficiency ($20\times$) and experience bonus ($2\times$) with deterministic tie-breaking.
  - `LeastLoadedAssignmentStrategy`: Evaluates lowest active incident workload with experience tie-breaking.
- **Smart Recommendations (`SmartTechnicianRecommendationService`):**
  - Evaluates candidate pool against incident requirements.
  - Augments rankings with optional LLM reasoning via `LLMProvider` (Adapter Pattern).
  - Guarantees seamless fallback to deterministic rankings if LLM service is offline or times out.
- **Two-Phase Assignment Safety (`TechnicianAssignmentService`):**
  - Validates technician availability, skill match, and guarantees active workload does not exceed `max_capacity`.
  - Dispatches `IncidentAssignedEvent` upon successful assignment.

---

## Module 4: SLA, Notifications & Audit Trail (M4)

### Responsibility
Monitors service level agreement compliance deadlines, sends approaching-breach warnings and breach records, delivers in-app user notifications, and logs immutable audit trails.

### Key Components
- **Entities & Models:**
  - `SLAPolicyModel` (`sla_policies` table): Configured target response and resolution durations in hours per priority level ($P1$ to $P4$).
  - `IncidentSLATrackingModel` (`incident_sla_tracking` table): Live tracking record capturing `response_due_at`, `resolution_due_at`, breach flags (`response_breached`, `resolution_breached`), and status (`RUNNING`, `MET`, `BREACHED`, `WARNING`, `PAUSED`).
  - `NotificationModel` (`notifications` table): Recipient inbox capturing event type, title, message, read flag, and read timestamp.
  - `AuditLogModel` (`audit_logs` table): Append-only immutable event timeline capturing actor, action, previous value, new value, details, and timestamp.
- **Automated SLA Monitor (`SLAMonitorTask`):**
  - Background async service running every 60 seconds.
  - Evaluates active incidents against deadline thresholds.
  - Dispatches `SLAWarningEvent` when an incident crosses 80% of its deadline.
  - Dispatches `SLABreachedEvent` when deadline is exceeded.
- **Event-Driven Observers:**
  - `SLALifecycleEventListener`, `AuditEventListener`, and `NotificationEventListener` subscribe to domain events on the shared `InProcessEventBus`.
