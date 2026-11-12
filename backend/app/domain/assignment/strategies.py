"""
Concrete assignment strategy implementations.

OOP Design:
- Inheritance: Both strategies inherit from AssignmentStrategy ABC
- Polymorphism: Both can be used interchangeably via the AssignmentStrategy interface
- Single Responsibility: Each strategy encapsulates one specific algorithm

Strategy A - SkillBasedAssignmentStrategy:
  Ranking formula: score = (proficiency_level * 20) + (experience_years * 2)
  Justification: Proficiency is weighted 10x more than experience because
  skill match quality directly impacts resolution quality. Experience provides
  a secondary ranking factor. These weights are documented and configurable.

Strategy B - LeastLoadedAssignmentStrategy:
  Ranking: Primary = fewest active incidents. Tie-break = highest experience_years.
  If still tied, use technician UUID string sort for deterministic ordering.
"""

import time

from app.core.exceptions import NoEligibleTechnicianError
from app.domain.assignment.strategy import (
    AssignmentContext,
    AssignmentResult,
    AssignmentStrategy,
    TechnicianRecommendation,
)
from app.domain.technician.technician import Technician

PROFICIENCY_WEIGHT = 20  # Weight for skill proficiency (1-5) → max 100
EXPERIENCE_WEIGHT = 2  # Weight for experience years → proportional bonus


class SkillBasedAssignmentStrategy(AssignmentStrategy):
    """
    Assigns technicians based on skill match quality and experience.

    Algorithm:
    1. Filter technicians by availability, required skill, and capacity
    2. For each eligible technician, calculate score:
       score = (proficiency_level * PROFICIENCY_WEIGHT) + (experience_years * EXPERIENCE_WEIGHT)
    3. Rank by score descending
    4. Generate explanation for each recommendation

    OOP: Inherits from AssignmentStrategy, implementing the Strategy Pattern.
    """

    @property
    def strategy_name(self) -> str:
        """Return the unique strategy identifier."""
        return "SKILL_BASED"

    def evaluate(self, context: AssignmentContext) -> AssignmentResult:
        """Evaluate technicians using skill-based scoring algorithm."""
        start_time = time.monotonic()
        required_skill = context.incident.required_skill
        eligible = self._filter_eligible(context.available_technicians, required_skill)

        if not eligible:
            raise NoEligibleTechnicianError(
                message=f"No eligible technician found with skill '{required_skill}' "
                f"for incident {context.incident.incident_code}"
            )

        # Score and rank
        scored: list[tuple[Technician, float, int]] = []
        for tech in eligible:
            proficiency = tech.get_skill_proficiency(required_skill)
            score = (proficiency * PROFICIENCY_WEIGHT) + (tech.experience_years * EXPERIENCE_WEIGHT)
            scored.append((tech, score, proficiency))

        # Sort by score descending, then by UUID for determinism
        scored.sort(key=lambda x: (-x[1], str(x[0].user_id)))

        recommendations: list[TechnicianRecommendation] = []
        for rank, (tech, score, proficiency) in enumerate(scored, start=1):
            explanation = (
                f"Skill '{required_skill}' proficiency: {proficiency}/5, "
                f"experience: {tech.experience_years} years, "
                f"active incidents: {tech.active_incident_count}/{tech.max_capacity}, "
                f"composite score: {score:.1f}"
            )
            recommendations.append(
                TechnicianRecommendation(
                    technician_id=tech.id,
                    technician_user_id=tech.user_id,
                    score=score,
                    rank=rank,
                    explanation=explanation,
                    strategy_used=self.strategy_name,
                )
            )

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return AssignmentResult(
            recommendations=recommendations,
            strategy_used=self.strategy_name,
            total_candidates=len(context.available_technicians),
            eligible_candidates=len(eligible),
            evaluation_time_ms=elapsed_ms,
        )


class LeastLoadedAssignmentStrategy(AssignmentStrategy):
    """
    Assigns the technician with the fewest active incidents.

    Algorithm:
    1. Filter technicians by availability, required skill, and capacity
    2. Sort by active_incident_count ascending
    3. Break ties using experience_years descending
    4. Break remaining ties using UUID string sort (deterministic)
    5. Return ranked list

    OOP: Inherits from AssignmentStrategy, demonstrating polymorphism —
    this strategy is interchangeable with SkillBasedAssignmentStrategy.
    """

    @property
    def strategy_name(self) -> str:
        """Return the unique strategy identifier."""
        return "LEAST_LOADED"

    def evaluate(self, context: AssignmentContext) -> AssignmentResult:
        """Evaluate technicians using least-loaded sorting algorithm."""
        start_time = time.monotonic()
        required_skill = context.incident.required_skill
        eligible = self._filter_eligible(context.available_technicians, required_skill)

        if not eligible:
            raise NoEligibleTechnicianError(
                message=f"No eligible technician found with skill '{required_skill}' "
                f"for incident {context.incident.incident_code}"
            )

        # Sort: fewest incidents first, then most experience, then UUID for determinism
        eligible.sort(
            key=lambda t: (
                t.active_incident_count,
                -t.experience_years,
                str(t.user_id),
            )
        )

        recommendations: list[TechnicianRecommendation] = []
        for rank, tech in enumerate(eligible, start=1):
            proficiency = tech.get_skill_proficiency(required_skill)
            explanation = (
                f"Active incidents: {tech.active_incident_count}/{tech.max_capacity} "
                f"(lowest workload), "
                f"skill '{required_skill}' proficiency: {proficiency}/5, "
                f"experience: {tech.experience_years} years"
            )
            score = float(tech.max_capacity - tech.active_incident_count)
            recommendations.append(
                TechnicianRecommendation(
                    technician_id=tech.id,
                    technician_user_id=tech.user_id,
                    score=score,
                    rank=rank,
                    explanation=explanation,
                    strategy_used=self.strategy_name,
                )
            )

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return AssignmentResult(
            recommendations=recommendations,
            strategy_used=self.strategy_name,
            total_candidates=len(context.available_technicians),
            eligible_candidates=len(eligible),
            evaluation_time_ms=elapsed_ms,
        )
