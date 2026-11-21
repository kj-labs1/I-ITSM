"""
SLA Policy & Tracking Application Service — Member 4.

OOP Design:
- Single Responsibility Principle: Orchestrates SLA policy configuration,
  per-incident SLA tracking lifecycle, violation queries, and periodic
  breach/warning evaluation.
- Dependency Inversion Principle: Depends only on abstract repositories and
  ``EventPublisher``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.application.interfaces.event_publisher import EventPublisher
from app.application.interfaces.sla_repositories import (
    SLAPolicyRepository,
    SLATrackingRepository,
)
from app.core.exceptions import (
    DuplicateSLAPolicyError,
    SLAPolicyNotFoundError,
    SLATrackingNotFoundError,
)
from app.domain.sla.enums import SLAStatus
from app.domain.sla.events import SLABreachedEvent, SLAMetEvent, SLAWarningEvent
from app.domain.sla.policy import DEFAULT_SLA_POLICY_SPECS, SLAPolicy
from app.domain.sla.tracking import IncidentSLATracking, SLAEvaluationResult
from app.shared.enums import Priority

logger = logging.getLogger(__name__)


class SLAService:
    """Application service coordinating SLA policies, tracking, and breach checks."""

    def __init__(
        self,
        policy_repo: SLAPolicyRepository,
        tracking_repo: SLATrackingRepository,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._policy_repo = policy_repo
        self._tracking_repo = tracking_repo
        self._event_publisher = event_publisher

    # ── Policy Management ─────────────────────────────────────────────────────

    async def ensure_default_policies(self) -> list[SLAPolicy]:
        """Idempotently seed standard P1–P4 SLA policies if they do not exist."""
        created_or_existing: list[SLAPolicy] = []
        for priority, spec in DEFAULT_SLA_POLICY_SPECS.items():
            existing = await self._policy_repo.get_by_priority(priority)
            if existing is not None:
                created_or_existing.append(existing)
                continue
            policy = SLAPolicy(
                priority=priority,
                name=str(spec["name"]),
                response_time_minutes=int(spec["response_time_minutes"]),
                resolution_time_minutes=int(spec["resolution_time_minutes"]),
                warning_threshold_percent=int(spec["warning_threshold_percent"]),
                escalation_enabled=bool(spec["escalation_enabled"]),
            )
            saved = await self._policy_repo.create(policy)
            created_or_existing.append(saved)
            logger.info("Seeded default SLA policy for %s", priority.value)
        return created_or_existing

    async def list_policies(self) -> list[SLAPolicy]:
        """Return all configured SLA policies, seeding defaults if empty."""
        policies = await self._policy_repo.list_all()
        if not policies:
            policies = await self.ensure_default_policies()
        return policies

    async def get_policy_by_priority(self, priority: Priority) -> SLAPolicy:
        """Fetch an SLA policy for ``priority``, seeding default if not yet present."""
        policy = await self._policy_repo.get_by_priority(priority)
        if policy is None:
            await self.ensure_default_policies()
            policy = await self._policy_repo.get_by_priority(priority)
        if policy is None:
            raise SLAPolicyNotFoundError(resource_id=priority.value)
        return policy

    async def create_policy(
        self,
        priority: Priority,
        name: str,
        response_time_minutes: int,
        resolution_time_minutes: int,
        warning_threshold_percent: int = 80,
        escalation_enabled: bool = True,
    ) -> SLAPolicy:
        """Create a new SLA policy for a priority level."""
        existing = await self._policy_repo.get_by_priority(priority)
        if existing is not None:
            raise DuplicateSLAPolicyError(
                f"SLA policy for priority {priority.value} already exists."
            )
        policy = SLAPolicy(
            priority=priority,
            name=name,
            response_time_minutes=response_time_minutes,
            resolution_time_minutes=resolution_time_minutes,
            warning_threshold_percent=warning_threshold_percent,
            escalation_enabled=escalation_enabled,
        )
        return await self._policy_repo.create(policy)

    async def update_policy(
        self,
        priority: Priority,
        name: str | None = None,
        response_time_minutes: int | None = None,
        resolution_time_minutes: int | None = None,
        warning_threshold_percent: int | None = None,
        escalation_enabled: bool | None = None,
    ) -> SLAPolicy:
        """Update targets for an existing SLA policy."""
        policy = await self._policy_repo.get_by_priority(priority)
        if policy is None:
            raise SLAPolicyNotFoundError(resource_id=priority.value)
        policy.update_targets(
            name=name,
            response_time_minutes=response_time_minutes,
            resolution_time_minutes=resolution_time_minutes,
            warning_threshold_percent=warning_threshold_percent,
            escalation_enabled=escalation_enabled,
        )
        return await self._policy_repo.update(policy)

    # ── Incident SLA Tracking ─────────────────────────────────────────────────

    async def start_tracking(
        self,
        incident_id: UUID,
        priority: Priority,
        started_at: datetime | None = None,
    ) -> IncidentSLATracking:
        """
        Start SLA tracking for an incident (idempotent if already tracked).
        """
        existing = await self._tracking_repo.get_by_incident_id(incident_id)
        if existing is not None:
            return existing

        policy = await self.get_policy_by_priority(priority)
        tracking = IncidentSLATracking.start_for_incident(
            incident_id=incident_id,
            policy=policy,
            started_at=started_at,
        )
        saved = await self._tracking_repo.create(tracking)
        logger.info(
            "Started SLA tracking for incident %s (priority=%s, resolution_due=%s)",
            incident_id,
            priority.value,
            saved.resolution_due_at.isoformat(),
        )
        return saved

    async def get_incident_sla(self, incident_id: UUID) -> IncidentSLATracking:
        """Retrieve current SLA tracking for an incident, evaluating up-to-date status."""
        tracking = await self._tracking_repo.get_by_incident_id(incident_id)
        if tracking is None:
            raise SLATrackingNotFoundError(resource_id=incident_id)

        policy = await self._policy_repo.get_by_id(tracking.policy_id)
        threshold = policy.warning_threshold_percent if policy else 80
        result = tracking.evaluate(now=datetime.now(UTC), warning_threshold_percent=threshold)
        if result.previous_status != result.new_status or result.newly_warned or result.newly_breached:
            tracking = await self._tracking_repo.update(tracking)
            await self._publish_evaluation_events(tracking, policy, result)
        return tracking

    async def record_first_response(
        self,
        incident_id: UUID,
        responded_at: datetime | None = None,
    ) -> IncidentSLATracking | None:
        """Record first technician acknowledgment/response for an incident."""
        tracking = await self._tracking_repo.get_by_incident_id(incident_id)
        if tracking is None:
            return None
        tracking.record_first_response(responded_at)
        return await self._tracking_repo.update(tracking)

    async def record_resolution(
        self,
        incident_id: UUID,
        resolved_at: datetime | None = None,
    ) -> IncidentSLATracking | None:
        """Record incident resolution and emit SLAMetEvent if resolved within targets."""
        tracking = await self._tracking_repo.get_by_incident_id(incident_id)
        if tracking is None:
            return None
        tracking.record_resolution(resolved_at)
        updated = await self._tracking_repo.update(tracking)
        if not updated.is_breached and self._event_publisher is not None:
            await self._event_publisher.publish(
                SLAMetEvent(
                    incident_id=updated.incident_id,
                    priority=updated.priority,
                    resolved_at=updated.resolved_at,
                )
            )
        return updated

    async def recalculate_priority(
        self,
        incident_id: UUID,
        new_priority: Priority,
    ) -> IncidentSLATracking | None:
        """Recalculate deadlines when an incident's priority is updated."""
        tracking = await self._tracking_repo.get_by_incident_id(incident_id)
        if tracking is None:
            return None
        policy = await self.get_policy_by_priority(new_priority)
        tracking.recalculate_for_policy(policy)
        return await self._tracking_repo.update(tracking)

    async def list_violations(
        self,
        include_warnings: bool = False,
        priority: Priority | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[IncidentSLATracking]:
        """List SLA breaches (and optionally near-breach warnings)."""
        return await self._tracking_repo.list_violations(
            include_warnings=include_warnings,
            priority=priority,
            skip=skip,
            limit=limit,
        )

    async def get_sla_summary(self) -> dict:
        """Compute aggregate SLA metrics and priority breakdowns."""
        all_records = await self._tracking_repo.list_all()
        total_tracked = len(all_records)
        met_count = sum(
            1
            for r in all_records
            if r.status == SLAStatus.MET or (r.resolved_at is not None and not r.is_breached)
        )
        breached_count = sum(
            1
            for r in all_records
            if r.is_breached or r.status == SLAStatus.BREACHED
        )
        warning_count = sum(
            1
            for r in all_records
            if (r.status == SLAStatus.WARNING or r.warning_sent)
            and not r.is_breached
            and r.resolved_at is None
        )
        active_count = sum(1 for r in all_records if r.resolved_at is None)
        compliance_rate = (
            round((total_tracked - breached_count) / total_tracked * 100.0, 1)
            if total_tracked > 0
            else 100.0
        )

        by_priority = []
        for p in (Priority.P1, Priority.P2, Priority.P3, Priority.P4):
            p_records = [r for r in all_records if r.priority == p]
            p_total = len(p_records)
            p_breached = sum(1 for r in p_records if r.is_breached or r.status == SLAStatus.BREACHED)
            p_met = sum(
                1
                for r in p_records
                if r.status == SLAStatus.MET or (r.resolved_at is not None and not r.is_breached)
            )
            p_compliance = (
                round((p_total - p_breached) / p_total * 100.0, 1)
                if p_total > 0
                else 100.0
            )
            by_priority.append(
                {
                    "priority": p,
                    "total": p_total,
                    "met": p_met,
                    "breached": p_breached,
                    "compliance_rate": p_compliance,
                }
            )

        return {
            "total_tracked": total_tracked,
            "met_count": met_count,
            "breached_count": breached_count,
            "warning_count": warning_count,
            "active_count": active_count,
            "compliance_rate": compliance_rate,
            "by_priority": by_priority,
        }

    # ── Scheduled Evaluation Sweep ────────────────────────────────────────────

    async def evaluate_active_slas(
        self,
        now: datetime | None = None,
    ) -> list[SLAEvaluationResult]:
        """
        Evaluate all active incident SLA tracking records against deadlines.

        Publishes ``SLAWarningEvent`` and ``SLABreachedEvent`` via ``EventPublisher``
        for any newly crossed warning thresholds or breaches.
        """
        check_time = now or datetime.now(UTC)
        active_records = await self._tracking_repo.list_active()
        policies_by_id = {p.id: p for p in await self._policy_repo.list_all()}
        results: list[SLAEvaluationResult] = []

        for tracking in active_records:
            policy = policies_by_id.get(tracking.policy_id)
            threshold = policy.warning_threshold_percent if policy else 80
            result = tracking.evaluate(now=check_time, warning_threshold_percent=threshold)
            results.append(result)

            if (
                result.previous_status != result.new_status
                or result.newly_warned
                or result.newly_breached
            ):
                await self._tracking_repo.update(tracking)
                await self._publish_evaluation_events(tracking, policy, result)

        return results

    async def _publish_evaluation_events(
        self,
        tracking: IncidentSLATracking,
        policy: SLAPolicy | None,
        result: SLAEvaluationResult,
    ) -> None:
        if self._event_publisher is None:
            return

        if result.newly_breached:
            due_at = (
                tracking.response_due_at
                if result.breach_type == "RESPONSE"
                else tracking.resolution_due_at
            )
            await self._event_publisher.publish(
                SLABreachedEvent(
                    incident_id=tracking.incident_id,
                    priority=tracking.priority,
                    breach_type=result.breach_type or "RESOLUTION",
                    due_at=due_at,
                    overdue_minutes=result.overdue_minutes,
                    escalation_enabled=policy.escalation_enabled if policy else True,
                )
            )
        elif result.newly_warned:
            due_at = (
                tracking.response_due_at
                if result.warning_target_type == "RESPONSE"
                else tracking.resolution_due_at
            )
            await self._event_publisher.publish(
                SLAWarningEvent(
                    incident_id=tracking.incident_id,
                    priority=tracking.priority,
                    target_type=result.warning_target_type or "RESOLUTION",
                    due_at=due_at,
                    percent_elapsed=result.percent_elapsed,
                )
            )
