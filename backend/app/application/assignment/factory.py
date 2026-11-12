"""
Assignment Strategy Factory — Factory Pattern.

OOP Design:
- Factory Pattern: Encapsulates creation and resolution of concrete assignment strategies.
- Open/Closed Principle: Allows new assignment strategies (e.g. Round-Robin, Experience-Based)
  to be registered without altering strategy consumer services.
"""

from __future__ import annotations

import logging

from app.domain.assignment.strategies import (
    LeastLoadedAssignmentStrategy,
    SkillBasedAssignmentStrategy,
)
from app.domain.assignment.strategy import AssignmentStrategy
from app.shared.enums import AssignmentStrategyType

logger = logging.getLogger(__name__)


class AssignmentStrategyFactory:
    """
    Factory creating interchangeable AssignmentStrategy implementations.
    """

    _registry: dict[str, type[AssignmentStrategy]] = {
        AssignmentStrategyType.SKILL_BASED.value: SkillBasedAssignmentStrategy,
        AssignmentStrategyType.LEAST_LOADED.value: LeastLoadedAssignmentStrategy,
    }

    @classmethod
    def register(cls, strategy_name: str, strategy_cls: type[AssignmentStrategy]) -> None:
        """Register a new strategy class in the factory."""
        cls._registry[strategy_name.upper()] = strategy_cls
        logger.info("Registered assignment strategy: '%s'", strategy_name)

    @classmethod
    def get_strategy(cls, strategy_type: str | AssignmentStrategyType) -> AssignmentStrategy:
        """
        Instantiate and return the requested AssignmentStrategy.

        Raises:
            ValueError: If the requested strategy is not registered.
        """
        name = (
            strategy_type.value
            if isinstance(strategy_type, AssignmentStrategyType)
            else str(strategy_type).upper()
        )

        if name not in cls._registry:
            raise ValueError(
                f"Unknown assignment strategy '{name}'. Available strategies: {list(cls._registry.keys())}"
            )

        strategy_cls = cls._registry[name]
        return strategy_cls()
