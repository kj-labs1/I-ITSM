
"""
Unit tests for Member 2 PriorityCalculator.
"""

import pytest

from app.domain.incident.priority_calculator import PriorityCalculator
from app.shared.enums import Priority


# ============================================================
# SCORE CALCULATION TESTS
# ============================================================


@pytest.mark.parametrize(
    "impact, urgency, business_criticality, expected_score",
    [
        (1, 1, 1, 1),
        (2, 2, 2, 8),
        (3, 3, 2, 18),
        (4, 5, 5, 100),
        (5, 5, 5, 125),
        (1, 5, 3, 15),
        (2, 4, 5, 40),
    ],
)
def test_calculate_score(
    impact,
    urgency,
    business_criticality,
    expected_score,
):
    """Verify multiplication of the three scoring factors."""

    score = PriorityCalculator.calculate_score(
        impact,
        urgency,
        business_criticality,
    )

    assert score == expected_score


# ============================================================
# PRIORITY THRESHOLD TESTS
# ============================================================


@pytest.mark.parametrize(
    "score, expected_priority",
    [
        (1, Priority.P4),
        (14, Priority.P4),

        (15, Priority.P3),
        (39, Priority.P3),

        (40, Priority.P2),
        (74, Priority.P2),

        (75, Priority.P1),
        (125, Priority.P1),
    ],
)
def test_priority_threshold_boundaries(
    score,
    expected_priority,
):
    """
    Test the lower and upper boundaries of all four priorities.
    """

    result = PriorityCalculator.calculate_priority_from_score(
        score
    )

    assert result == expected_priority


# ============================================================
# INPUT VALIDATION TESTS
# ============================================================


@pytest.mark.parametrize(
    "invalid_value",
    [
        0,
        6,
        -1,
        10,
        1.5,
        True,
        False,
        "3",
        None,
    ],
)
def test_invalid_impact_is_rejected(invalid_value):

    with pytest.raises(ValueError):

        PriorityCalculator.calculate_score(
            impact=invalid_value,
            urgency=3,
            business_criticality=3,
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        0,
        6,
        -1,
        2.5,
        True,
        "4",
        None,
    ],
)
def test_invalid_urgency_is_rejected(invalid_value):

    with pytest.raises(ValueError):

        PriorityCalculator.calculate_score(
            impact=3,
            urgency=invalid_value,
            business_criticality=3,
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        0,
        6,
        -1,
        4.5,
        True,
        "5",
        None,
    ],
)
def test_invalid_business_criticality_is_rejected(invalid_value):

    with pytest.raises(ValueError):

        PriorityCalculator.calculate_score(
            impact=3,
            urgency=3,
            business_criticality=invalid_value,
        )


@pytest.mark.parametrize(
    "invalid_score",
    [
        0,
        126,
        -10,
        1.5,
        True,
        "75",
        None,
    ],
)
def test_invalid_priority_score_is_rejected(invalid_score):

    with pytest.raises(ValueError):

        PriorityCalculator.calculate_priority_from_score(
            invalid_score
        )


# ============================================================
# END-TO-END CALCULATION TESTS
# ============================================================


@pytest.mark.parametrize(
    "impact, urgency, business_criticality, expected_priority",
    [
        (1, 1, 1, Priority.P4),
        (1, 5, 3, Priority.P3),
        (2, 4, 5, Priority.P2),
        (4, 5, 5, Priority.P1),
        (5, 5, 5, Priority.P1),
    ],
)
def test_calculate_final_priority(
    impact,
    urgency,
    business_criticality,
    expected_priority,
):

    result = PriorityCalculator.calculate(
        impact=impact,
        urgency=urgency,
        business_criticality=business_criticality,
    )

    assert result == expected_priority


# ============================================================
# INTEGRATION WITH INCIDENT DOMAIN ENTITY
# ============================================================


def test_incident_priority_recalculation():

    from uuid import uuid4

    from app.domain.incident.incident import Incident
    from app.shared.enums import IncidentCategory

    incident = Incident(
        incident_code="INC-3001",
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="Network connectivity is unstable",
        impact=3,
        urgency=3,
        business_criticality=2,
        priority=Priority.P4,
    )

    assert incident.recalculate_priority() == Priority.P3

    # Change incident scoring factors.
    incident.impact = 5
    incident.urgency = 5
    incident.business_criticality = 5

    # Recalculate after modification.
    result = incident.recalculate_priority()

    assert result == Priority.P1
    assert incident.priority == Priority.P1
