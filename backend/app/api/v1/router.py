"""
API v1 router — aggregates all module sub-routers under the /api/v1 prefix.

Route paths adhere to shared team contracts:
- M3 Technicians: /api/v1/technicians, /api/v1/technicians/recommendations
- M3 Assignment:  /api/v1/incidents/{incident_id}/assign
- M1 Auth/User:   /api/v1/auth/*, /api/v1/users (Extension points documented)
- M2 Incidents:   /api/v1/incidents (Extension points documented)
- M4 SLA/Audit:   /api/v1/incidents/{id}/sla, /api/v1/sla/violations,
                  /api/v1/notifications, /api/v1/incidents/{id}/audit
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import assignment, audit, notifications, sla, technicians

router = APIRouter()

# ── Module 3: Technicians & Assignment ────────────────────────────────────────
router.include_router(technicians.router)
router.include_router(assignment.router)

# ── Module 4: SLA, Notifications & Audit ──────────────────────────────────────
router.include_router(sla.router)
router.include_router(notifications.router)
router.include_router(audit.router)

# ── Extension Points for Parallel Team Development ───────────────────────────
#
# Module 1 (Identity, Auth, Services, Categories) will attach:
#   from app.api.v1 import auth, users, services, categories
#   router.include_router(auth.router, prefix="/auth", tags=["Auth"])
#   router.include_router(users.router, prefix="/users", tags=["Users"])
#   router.include_router(services.router, prefix="/services", tags=["Services"])
#   router.include_router(categories.router, prefix="/categories", tags=["Categories"])
#
# Module 2 (Incidents, Lifecycle, Comments, Duplicate Detection) will attach:
#   from app.api.v1 import incidents
#   router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
