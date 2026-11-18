"""
In-memory stub implementation of IncidentServiceBoundary for Member 3 development.

OOP Design:
- Adapter / Test Double: Allows Member 3's recommendation and assignment features to run,
  test, and validate before Member 2 completes the persistent Incident entity.
- Conforms strictly to `IncidentServiceBoundary`.
- Clearly labelled as an integration stub: in production, Member 2's concrete
  service is injected in place of this stub.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.interfaces.incident_service import IncidentServiceBoundary
from app.core.exceptions import IncidentNotFoundError, InvalidAssignmentError
from app.domain.incident.incident_ref import IncidentRef
from app.shared.enums import IncidentCategory, IncidentStatus, Priority

logger = logging.getLogger(__name__)


class StubIncidentService(IncidentServiceBoundary):
    """
    In-memory incident repository and lifecycle coordinator for development and testing.
    Can fall back to a persistent IncidentServiceBoundary if an incident is not in memory.
    """

    def __init__(self, fallback: IncidentServiceBoundary | None = None) -> None:
        self._incidents: dict[UUID, dict] = {}
        self._fallback = fallback

    def seed_incident(
        self,
        incident_id: UUID | None = None,
        incident_code: str | None = None,
        category: IncidentCategory = IncidentCategory.NETWORK,
        required_skill: str = "NETWORK",
        priority: Priority = Priority.P2,
        status: IncidentStatus = IncidentStatus.CLASSIFIED,
        description: str = "Corporate Wi-Fi authentication failing across Engineering floor.",
        service_id: UUID | None = None,
        reporter_id: UUID | None = None,
        assigned_technician_id: UUID | None = None,
    ) -> IncidentRef:
        """Helper to seed test incidents for automated tests and local runs."""
        iid = incident_id or uuid4()
        code = incident_code or f"INC-{1000 + len(self._incidents) + 1}"
        record = {
            "id": iid,
            "incident_code": code,
            "category": category,
            "required_skill": required_skill,
            "priority": priority,
            "status": status,
            "description": description,
            "service_id": service_id or uuid4(),
            "reporter_id": reporter_id or uuid4(),
            "assigned_technician_id": assigned_technician_id,
            "created_at": datetime.now(UTC),
        }
        self._incidents[iid] = record
        return IncidentRef(**record)

    async def get_incident(self, incident_id: UUID) -> IncidentRef | None:
        """Retrieve an incident projection by ID."""
        record = self._incidents.get(incident_id)
        if record is None:
            if self._fallback is not None:
                return await self._fallback.get_incident(incident_id)
            return None
        return IncidentRef(**record)

    async def assign_technician(
        self,
        incident_id: UUID,
        technician_id: UUID,
        actor_id: UUID,
    ) -> bool:
        """
        Coordinate assignment with lifecycle validation.

        Enforces:
        - Incident must exist.
        - Status must be NEW or CLASSIFIED (or ASSIGNED for reassignment).
        - Prevents duplicate assignment if already assigned to the same technician.
        """
        record = self._incidents.get(incident_id)
        if record is None:
            if self._fallback is not None:
                return await self._fallback.assign_technician(
                    incident_id=incident_id,
                    technician_id=technician_id,
                    actor_id=actor_id,
                )
            raise IncidentNotFoundError(resource_id=str(incident_id))

        current_status = record["status"]
        if current_status not in (IncidentStatus.NEW, IncidentStatus.CLASSIFIED):
            raise InvalidAssignmentError(
                f"Incident {record['incident_code']} is in status '{current_status.value}' "
                f"and cannot be assigned. Only NEW or CLASSIFIED incidents may be assigned."
            )

        if record["assigned_technician_id"] is not None:
            raise InvalidAssignmentError(
                f"Incident {record['incident_code']} already has assigned technician "
                f"{record['assigned_technician_id']}."
            )

        record["assigned_technician_id"] = technician_id
        record["status"] = IncidentStatus.ASSIGNED
        logger.info(
            "StubIncidentService: Assigned technician %s to incident %s by actor %s",
            technician_id,
            incident_id,
            actor_id,
        )
        return True

    async def get_active_incident_count(self, technician_user_id: UUID) -> int:
        """Count active open incidents assigned to this technician."""
        active_statuses = {
            IncidentStatus.ASSIGNED,
            IncidentStatus.ACKNOWLEDGED,
            IncidentStatus.IN_PROGRESS,
        }
        count = sum(
            1
            for rec in self._incidents.values()
            if rec.get("assigned_technician_id") == technician_user_id
            and rec.get("status") in active_statuses
        )
        if self._fallback is not None:
            fallback_count = await self._fallback.get_active_incident_count(technician_user_id)
            count += fallback_count
        return count


# Singleton instance for in-memory stub operations
_stub_incident_service: StubIncidentService | None = None


def get_stub_incident_service() -> StubIncidentService:
    """Return the global StubIncidentService instance."""
    global _stub_incident_service
    if _stub_incident_service is None:
        _stub_incident_service = StubIncidentService()
    return _stub_incident_service
