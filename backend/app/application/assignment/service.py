"""
Technician Recommendation and Incident Assignment Application Services.

OOP Design Decisions:
- Strategy Pattern: Employs `AssignmentStrategy` implementations polymorphically to rank candidates.
- Adapter Pattern: Interacts with external LLM engines through the `LLMProvider` interface.
- Observer Pattern: Publishes `IncidentAssignedEvent` upon successful assignment.
- Dependency Inversion: Depends on abstract interfaces (`TechnicianRepository`, `IncidentServiceBoundary`,
  `LLMProvider`, `EventPublisher`) injected through constructors.
- Two-Phase Safety & Concurrency Validation:
  1. Smart recommendation suggests ranked candidates with transparent explanations.
  2. Assignment confirmation rigorously re-validates availability, skills, capacity, and incident
     state right before delegating state transition to Member 2.
"""

from __future__ import annotations

import asyncio
import logging
import time
from uuid import UUID

from app.application.assignment.factory import AssignmentStrategyFactory
from app.application.interfaces.event_publisher import EventPublisher
from app.application.interfaces.incident_service import IncidentServiceBoundary
from app.application.interfaces.repositories import TechnicianRepository
from app.core.exceptions import (
    CapacityExceededError,
    DuplicateAssignmentError,
    IncidentNotFoundError,
    InvalidAssignmentError,
    SkillMismatchError,
    TechnicianNotFoundError,
    TechnicianUnavailableError,
)
from app.domain.assignment.events import (
    IncidentAssignedEvent,
    TechnicianWorkloadWarningEvent,
)
from app.domain.assignment.strategy import (
    AssignmentContext,
    AssignmentResult,
    TechnicianRecommendation,
)
from app.domain.incident.incident_ref import IncidentRef
from app.domain.technician.technician import Technician
from app.integrations.llm.provider import (
    LLMCandidateData,
    LLMProvider,
    LLMRecommendationRequest,
)
from app.shared.enums import AssignmentStrategyType

logger = logging.getLogger(__name__)


class SmartTechnicianRecommendationService:
    """
    Evaluates incident requirements against the technician pool using deterministic
    strategies augmented optionally by LLM reasoning.
    """

    def __init__(
        self,
        technician_repo: TechnicianRepository,
        incident_service: IncidentServiceBoundary,
        llm_provider: LLMProvider,
    ) -> None:
        self.technician_repo = technician_repo
        self.incident_service = incident_service
        self.llm_provider = llm_provider

    async def get_recommendations(
        self,
        incident_id: UUID,
        strategy_type: AssignmentStrategyType | str = AssignmentStrategyType.SKILL_BASED,
        use_llm: bool = False,
    ) -> AssignmentResult:
        """
        Produce ranked technician recommendations for a given incident.

        Workflow:
        1. Fetch incident projection from Member 2 boundary.
        2. Retrieve all active available technicians from repository.
        3. Attach current active incident workloads from Member 2.
        4. Execute selected deterministic assignment strategy.
        5. If `use_llm` is enabled, augment rankings with LLM evaluation and reasoning.
        6. Return AssignmentResult with ranked recommendations and explanations.
        """
        start_time = time.monotonic()

        # Step 1: Retrieve incident
        incident = await self.incident_service.get_incident(incident_id)
        if incident is None:
            raise IncidentNotFoundError(resource_id=str(incident_id))

        if not incident.is_assignable and not incident.is_reassignable:
            raise InvalidAssignmentError(
                f"Incident {incident.incident_code} in status '{incident.status.value}' "
                f"is not eligible for assignment."
            )

        # Step 2: Retrieve available technicians
        all_techs = await self.technician_repo.list_available()

        # Step 3: Populate authoritative active workloads
        for tech in all_techs:
            workload = await self.incident_service.get_active_incident_count(tech.user_id)
            tech.update_active_incident_count(workload)

        # Step 4: Resolve strategy polymorphically via Factory Pattern
        strategy = AssignmentStrategyFactory.get_strategy(strategy_type)

        context = AssignmentContext(
            incident=incident,
            available_technicians=all_techs,
            strategy_type=strategy.strategy_name,
            use_llm=use_llm,
        )

        # Evaluate deterministic baseline
        result = strategy.evaluate(context)

        # Step 5: Optional LLM Enhancement with Deterministic Fallback
        if use_llm and result.has_recommendations:
            try:
                result = await self._enhance_with_llm(incident, result, all_techs)
            except Exception as llm_err:
                logger.warning(
                    "LLM recommendation enhancement failed (%s). "
                    "Falling back seamlessly to deterministic %s results.",
                    llm_err,
                    strategy.strategy_name,
                )
                # Deterministic fallback: preserve original results, record note in explanations
                updated_recs = [
                    TechnicianRecommendation(
                        technician_id=r.technician_id,
                        technician_user_id=r.technician_user_id,
                        score=r.score,
                        rank=r.rank,
                        explanation=f"{r.explanation} (LLM fallback applied: {type(llm_err).__name__})",
                        strategy_used=r.strategy_used,
                        skill_match=r.skill_match,
                        is_llm_enhanced=False,
                        username=r.username,
                        full_name=r.full_name,
                    )
                    for r in result.recommendations
                ]
                result.recommendations = updated_recs

        result.evaluation_time_ms = (time.monotonic() - start_time) * 1000
        return result

    async def _enhance_with_llm(
        self,
        incident: IncidentRef,
        deterministic_result: AssignmentResult,
        candidate_pool: list[Technician],
    ) -> AssignmentResult:
        """Call LLM provider to re-rank and enrich recommendation justifications."""
        tech_map = {str(t.id): t for t in candidate_pool}
        user_id_map = {str(t.user_id): t for t in candidate_pool}

        candidates_payload: list[LLMCandidateData] = []
        for rec in deterministic_result.recommendations:
            tech = tech_map.get(str(rec.technician_id)) or user_id_map.get(str(rec.technician_user_id))
            if tech:
                candidates_payload.append(
                    LLMCandidateData(
                        id=str(tech.id),
                        skills=[
                            {"name": s.skill_name, "proficiency": s.proficiency_level} for s in tech.skills
                        ],
                        experienceYears=tech.experience_years,
                        activeIncidents=tech.active_incident_count,
                        maxCapacity=tech.max_capacity,
                    )
                )

        if not candidates_payload:
            return deterministic_result

        llm_request = LLMRecommendationRequest(
            incidentCategory=incident.category.value,
            incidentPriority=incident.priority.value,
            incidentDescription=incident.description,
            requiredSkill=incident.required_skill,
            candidates=candidates_payload,
        )

        llm_response = await self.llm_provider.get_recommendation(llm_request)

        # Merge LLM rankings with deterministic recommendations
        enhanced_recs: list[TechnicianRecommendation] = []
        for ranking in llm_response.rankings:
            # Locate original technician
            matching_rec = next(
                (
                    r
                    for r in deterministic_result.recommendations
                    if str(r.technician_id) == ranking.technician_id
                ),
                None,
            )
            if matching_rec:
                enhanced_recs.append(
                    TechnicianRecommendation(
                        technician_id=matching_rec.technician_id,
                        technician_user_id=matching_rec.technician_user_id,
                        score=ranking.relevance_score,
                        rank=ranking.rank,
                        explanation=ranking.explanation,
                        strategy_used=f"{deterministic_result.strategy_used}+LLM",
                        skill_match=True,
                        is_llm_enhanced=True,
                        username=matching_rec.username,
                        full_name=matching_rec.full_name,
                    )
                )

        # Re-sort by rank
        enhanced_recs.sort(key=lambda r: r.rank)

        return AssignmentResult(
            recommendations=enhanced_recs if enhanced_recs else deterministic_result.recommendations,
            strategy_used=f"{deterministic_result.strategy_used}+LLM",
            total_candidates=deterministic_result.total_candidates,
            eligible_candidates=deterministic_result.eligible_candidates,
            is_llm_enhanced=True,
            evaluation_time_ms=deterministic_result.evaluation_time_ms,
        )


class TechnicianAssignmentService:
    """
    Coordinates technician assignment validation and execution.
    """

    _tech_locks: dict[UUID, asyncio.Lock] = {}

    def __init__(
        self,
        technician_repo: TechnicianRepository,
        incident_service: IncidentServiceBoundary,
        event_publisher: EventPublisher,
    ) -> None:
        self.technician_repo = technician_repo
        self.incident_service = incident_service
        self.event_publisher = event_publisher

    @classmethod
    def _get_technician_lock(cls, technician_id: UUID) -> asyncio.Lock:
        if technician_id not in cls._tech_locks:
            cls._tech_locks[technician_id] = asyncio.Lock()
        return cls._tech_locks[technician_id]

    async def assign_technician(
        self,
        incident_id: UUID,
        technician_id: UUID,
        actor_id: UUID,
        strategy_used: str = "MANUAL",
        reason: str = "",
    ) -> dict:
        """
        Execute an incident assignment with comprehensive safety validation.

        Validation Rules:
        1. Incident must exist and be in assignable status.
        2. Incident must not already be assigned to this technician.
        3. Technician must exist.
        4. Technician must be currently AVAILABLE.
        5. Technician must possess the incident's required skill.
        6. Technician active workload must not exceed max_capacity.
        7. Calls Member 2 boundary to perform status change and persistence.
        8. Publishes IncidentAssignedEvent to notify Member 4 (SLA & Audit).
        """
        # Step 1: Validate Incident
        incident = await self.incident_service.get_incident(incident_id)
        if incident is None:
            raise IncidentNotFoundError(resource_id=str(incident_id))

        # Step 2: Validate Technician by user_id (canonical identity from M1) first, then profile id
        tech = await self.technician_repo.get_by_user_id(technician_id, for_update=True)
        if tech is None:
            tech = await self.technician_repo.get_by_id(technician_id, for_update=True)
            if tech is None:
                raise TechnicianNotFoundError(resource_id=str(technician_id))

        if incident.assigned_technician_id is not None:
            if incident.assigned_technician_id in (tech.user_id, tech.id):
                raise DuplicateAssignmentError(
                    f"Incident {incident.incident_code} is already assigned to technician {tech.user_id}."
                )
            raise DuplicateAssignmentError(
                f"Incident {incident.incident_code} is already assigned to another technician."
            )

        if not incident.is_assignable and not incident.is_reassignable:
            raise InvalidAssignmentError(
                f"Incident {incident.incident_code} in status '{incident.status.value}' cannot be assigned."
            )

        if not tech.is_available:
            raise TechnicianUnavailableError(
                f"Technician {tech.id} is currently unavailable (status: {tech.availability.value})."
            )

        if not tech.has_skill(incident.required_skill):
            raise SkillMismatchError(
                f"Technician {tech.id} lacks required skill '{incident.required_skill}'."
            )

        # Check workload & capacity inside synchronized block
        lock = self._get_technician_lock(tech.user_id)
        async with lock:
            active_count = await self.incident_service.get_active_incident_count(tech.user_id)
            tech.update_active_incident_count(active_count)
            if not tech.has_capacity:
                raise CapacityExceededError(
                    f"Technician {tech.id} has reached maximum capacity ({tech.active_incident_count}/{tech.max_capacity})."
                )

            # Step 3: Delegate state change to Member 2 boundary
            success = await self.incident_service.assign_technician(
                incident_id=incident.id,
                technician_id=tech.user_id,
                actor_id=actor_id,
            )
            if not success:
                raise InvalidAssignmentError("Incident service rejected assignment operation.")

            # Publish workload warning if technician is now at capacity
            if active_count + 1 >= tech.max_capacity:
                await self.event_publisher.publish(
                    TechnicianWorkloadWarningEvent(
                        technician_id=tech.user_id,
                        active_incidents=active_count + 1,
                        max_capacity=tech.max_capacity,
                    )
                )

        # Step 4: Observer Pattern — Publish IncidentAssignedEvent for Member 4
        assigned_event = IncidentAssignedEvent(
            incident_id=incident.id,
            technician_id=tech.user_id,
            actor_id=actor_id,
            strategy_used=strategy_used,
            explanation=reason or f"Assigned via {strategy_used} strategy.",
            incident_code=incident.incident_code,
            reporter_id=incident.reporter_id,
        )
        await self.event_publisher.publish(assigned_event)
        logger.info(
            "Successfully assigned technician %s to incident %s (strategy=%s)",
            tech.id,
            incident.id,
            strategy_used,
        )

        return {
            "incidentId": incident.id,
            "incidentCode": incident.incident_code,
            "technicianId": tech.id,
            "technicianUserId": tech.user_id,
            "status": "ASSIGNED",
            "strategyUsed": strategy_used,
            "assignedBy": actor_id,
        }
