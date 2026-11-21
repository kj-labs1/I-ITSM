"""
Assignment Strategy abstraction — Strategy Pattern implementation.

OOP Design: Demonstrates the Strategy Pattern. AssignmentStrategy is an
abstract base class that defines the contract for different technician
assignment algorithms. Concrete strategies (SkillBased, LeastLoaded)
implement the same interface and can be used interchangeably.

This demonstrates:
- Abstraction: ABC with abstract methods
- Polymorphism: Different strategies interchangeable through same interface
- Open/Closed Principle: New strategies can be added without modifying existing code
- Dependency Inversion: Business services depend on the abstraction, not concrete implementations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.incident.incident_ref import IncidentRef
from app.domain.technician.technician import Technician


@dataclass(frozen=True)
class TechnicianRecommendation:
    """A single technician recommendation with score and explanation.

    Value Object: Immutable recommendation result.
    """

    technician_id: UUID
    technician_user_id: UUID
    score: float
    rank: int
    explanation: str
    strategy_used: str
    skill_match: bool = True
    is_llm_enhanced: bool = False
    username: str | None = None
    full_name: str | None = None

    @property
    def user_id(self) -> UUID:
        """Alias for technician_user_id ensuring consistent identity naming."""
        return self.technician_user_id


@dataclass(frozen=True)
class AssignmentContext:
    """Context information passed to assignment strategies.

    Value Object: Encapsulates all information needed for assignment
    decision-making in one immutable object.
    """

    incident: IncidentRef
    available_technicians: list[Technician]
    strategy_type: str
    use_llm: bool = False
    requested_by: UUID | None = None


@dataclass
class AssignmentResult:
    """Result of an assignment strategy evaluation.

    Contains ranked recommendations and metadata about the evaluation.
    """

    recommendations: list[TechnicianRecommendation]
    strategy_used: str
    total_candidates: int
    eligible_candidates: int
    is_llm_enhanced: bool = False
    evaluation_time_ms: float = 0.0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def has_recommendations(self) -> bool:
        """Check if the result contains any recommendations."""
        return len(self.recommendations) > 0

    @property
    def top_recommendation(self) -> TechnicianRecommendation | None:
        """Return the highest-ranked recommendation, or None if empty."""
        if not self.recommendations:
            return None
        return min(self.recommendations, key=lambda r: r.rank)


class AssignmentStrategy(ABC):
    """
    Abstract base class for technician assignment strategies.

    Strategy Pattern: Each concrete implementation provides a different
    algorithm for selecting and ranking technicians for incident assignment.
    All strategies share the same interface, enabling polymorphic usage
    in the AssignmentService.

    Liskov Substitution Principle: Any concrete strategy can replace
    any other without affecting the correctness of the AssignmentService.
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Unique name identifying this strategy."""
        ...

    @abstractmethod
    def evaluate(self, context: AssignmentContext) -> AssignmentResult:
        """
        Evaluate technicians and produce ranked recommendations.

        Args:
            context: Assignment context with incident and technician info.

        Returns:
            AssignmentResult with ranked recommendations.

        Raises:
            NoEligibleTechnicianError: If no technician meets eligibility criteria.
        """
        ...

    def _filter_eligible(self, technicians: list[Technician], required_skill: str) -> list[Technician]:
        """
        Filter technicians by eligibility criteria.

        Common filtering logic shared by all strategies:
        1. Must be available
        2. Must have the required skill
        3. Must have capacity
        """
        return [t for t in technicians if t.is_eligible_for(required_skill)]
