
"""
Priority calculation engine — Member 2.

Calculates incident priority using:
    Priority Score = Impact x Urgency x Business Criticality

All three inputs must be integers between 1 and 5.

Priority thresholds:
    75-125 : P1 (Critical)
    40-74  : P2 (High)
    15-39  : P3 (Medium)
    1-14   : P4 (Low)

This is a pure domain component and has no database or API dependencies.
"""

from __future__ import annotations

from app.shared.enums import Priority


class PriorityCalculator:
    """
    Calculates the priority of an incident.

    OOP principles:
    - Encapsulation: Scoring rules are maintained inside one class.
    - Abstraction: Other components call calculate() without needing
      to know the internal threshold implementation.
    - Single Responsibility: This class only handles priority calculation.
    """

    MIN_FACTOR = 1
    MAX_FACTOR = 5

    MIN_SCORE = 1
    MAX_SCORE = 125

    # Minimum score required for each priority level.
    PRIORITY_THRESHOLDS = (
        (75, Priority.P1),
        (40, Priority.P2),
        (15, Priority.P3),
        (1, Priority.P4),
    )

    @classmethod
    def _validate_factor(
        cls,
        factor_name: str,
        value: int,
    ) -> None:
        """
        Validate an individual scoring factor.

        Rejects:
        - Values below 1.
        - Values above 5.
        - Negative numbers.
        - Floating-point numbers.
        - Boolean values.
        """

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not cls.MIN_FACTOR <= value <= cls.MAX_FACTOR
        ):
            raise ValueError(
                f"{factor_name} must be an integer "
                f"between {cls.MIN_FACTOR} and {cls.MAX_FACTOR}. "
                f"Received: {value!r}"
            )

    @classmethod
    def calculate_score(
        cls,
        impact: int,
        urgency: int,
        business_criticality: int,
    ) -> int:
        """
        Calculate the numerical priority score.

        Formula:
            Score = Impact x Urgency x Business Criticality

        Returns:
            Integer between 1 and 125.
        """

        cls._validate_factor("Impact", impact)
        cls._validate_factor("Urgency", urgency)
        cls._validate_factor(
            "Business Criticality",
            business_criticality,
        )

        return impact * urgency * business_criticality

    @classmethod
    def calculate_priority_from_score(
        cls,
        score: int,
    ) -> Priority:
        """
        Convert a validated priority score into a Priority enum.

        Returns:
            Priority.P1, Priority.P2, Priority.P3 or Priority.P4.
        """

        if (
            isinstance(score, bool)
            or not isinstance(score, int)
            or not cls.MIN_SCORE <= score <= cls.MAX_SCORE
        ):
            raise ValueError(
                f"Priority score must be an integer "
                f"between {cls.MIN_SCORE} and {cls.MAX_SCORE}. "
                f"Received: {score!r}"
            )

        for minimum_score, priority in cls.PRIORITY_THRESHOLDS:
            if score >= minimum_score:
                return priority

        # Defensive fallback; valid scores are covered by the thresholds.
        raise ValueError(f"Unable to determine priority for score: {score}")

    @classmethod
    def calculate(
        cls,
        impact: int,
        urgency: int,
        business_criticality: int,
    ) -> Priority:
        """
        Calculate the final incident priority directly from its inputs.

        This is the main method that application services should call.
        """

        score = cls.calculate_score(
            impact=impact,
            urgency=urgency,
            business_criticality=business_criticality,
        )

        return cls.calculate_priority_from_score(score)
