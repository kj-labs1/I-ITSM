# Cross-Module Integration Guide

This guide explains how Members 1, 2, and 4 connect their modules into the shared backend application without restructuring existing code.

---

## 1. Member 1: Platform, Authentication & Administration

### Backend Responsibilities:
1. **User Identity & Roles:**
   - Define `UserModel` in `app/infrastructure/database/models.py` (or `app/domain/identity/`).
   - Tables owned: `users`, `employees`, `administrators`, `services`, `incident_categories`.
   - Shared UUID: Ensure `users.id` generates UUID v4. The `technicians.user_id` column references this identifier.
2. **Authentication Middleware:**
   - Implement login endpoint `POST /api/v1/auth/login`.
   - Issue JWTs signed with `Settings.JWT_SECRET_KEY`. Include claims:
     ```json
     { "sub": "<user_uuid>", "role": "EMPLOYEE|TECHNICIAN|ADMIN", "exp": 1234567890 }
     ```
   - Complete `app/core/security.py` dependencies (`get_current_user_id`, `require_role`).
3. **Register Routers in `app/api/v1/router.py`:**
   ```python
   from app.api.v1 import auth, users, services, categories
   router.include_router(auth.router, prefix="/auth", tags=["Auth"])
   router.include_router(users.router, prefix="/users", tags=["Users"])
   router.include_router(services.router, prefix="/services", tags=["Services"])
   router.include_router(categories.router, prefix="/categories", tags=["Categories"])
   ```

---

## 2. Member 2: Incident Management & Lifecycle

### Backend Responsibilities:
1. **Incident Entity & Persistence:**
   - Create `IncidentModel` and `IncidentCommentModel` in `app/infrastructure/database/`.
   - Tables owned: `incidents`, `incident_comments`.
   - Columns must match shared contracts: `id`, `incident_code`, `category`, `required_skill`, `priority`, `status`, `assigned_technician_id`, `reporter_id`, `service_id`.
2. **Implement Incident Service Boundary:**
   - Implement `app/application/interfaces/incident_service.py:IncidentServiceBoundary`:
     ```python
     class PersistentIncidentService(IncidentServiceBoundary):
         async def get_incident(self, incident_id: UUID) -> IncidentRef | None: ...
         async def assign_technician(self, incident_id: UUID, technician_id: UUID, actor_id: UUID) -> bool: ...
         async def get_active_incident_count(self, technician_user_id: UUID) -> int: ...
     ```
   - Wire your service in `app/api/deps.py`:
     ```python
     def get_incident_service_boundary(...) -> IncidentServiceBoundary:
         return PersistentIncidentService(...)
     ```
3. **Publish Lifecycle Events:**
   - When incident is created, publish `IncidentCreatedEvent` to `EventPublisher`.
   - When status changes, publish `IncidentStatusChangedEvent`.
4. **Register Routers in `app/api/v1/router.py`:**
   ```python
   from app.api.v1 import incidents
   router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
   ```

---

## 3. Member 4: SLA, Notifications & Audit Automation

### Backend Responsibilities:
1. **Subscribe to Domain Events (Observer Pattern):**
   - Implement `EventListener` in `app/application/interfaces/event_publisher.py`:
     ```python
     from app.application.interfaces.event_publisher import EventListener
     from app.domain.assignment.events import IncidentAssignedEvent

     class AuditEventListener(EventListener):
         async def handle(self, event: DomainEvent) -> None:
             if isinstance(event, IncidentAssignedEvent):
                 # Create audit entry
                 ...
     ```
   - Register listeners in `app/main.py` lifespan startup:
     ```python
     event_bus = get_event_bus()
     event_bus.subscribe(IncidentAssignedEvent, AuditEventListener())
     ```
2. **SLA Policies & Scheduled Monitor:**
   - Implement background task checking active incidents against SLA deadlines once per minute.
   - Tables owned: `sla_policies`, `incident_sla_tracking`, `audit_logs`, `notifications`.
3. **Register Routers in `app/api/v1/router.py`:**
   ```python
   from app.api.v1 import sla, notifications, audit
   router.include_router(sla.router, prefix="/sla", tags=["SLA"])
   router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
   ```
