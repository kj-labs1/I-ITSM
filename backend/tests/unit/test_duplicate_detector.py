from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.incident.duplicate_detector import DuplicateDetector
from app.domain.incident.incident import Incident
from app.shared.enums import IncidentCategory, Priority


def make_incident(
    description: str,
    service_id=None,
    category=IncidentCategory.NETWORK,
) -> Incident:
    now = datetime.now(UTC)

    return Incident(
        incident_code=f"INC-{uuid4().hex[:8].upper()}",
        reporter_id=uuid4(),
        service_id=service_id or uuid4(),
        category=category,
        required_skill="NETWORK",
        description=description,
        impact=3,
        urgency=3,
        business_criticality=3,
        priority=Priority.P2,
        created_at=now,
        updated_at=now,
    )


def test_description_normalization_removes_punctuation_and_stop_words():
    detector = DuplicateDetector()

    tokens = detector.normalize_description(
        "The Wi-Fi router is NOT connecting after restart!"
    )

    assert "the" not in tokens
    assert "is" not in tokens
    assert "router" in tokens
    assert "connecting" in tokens
    assert "not" in tokens


def test_jaccard_similarity_identical_descriptions():
    first = "Database connection failure after server restart"
    second = "Database connection failure after server restart"

    score = DuplicateDetector.calculate_similarity(first, second)

    assert score == 1.0


def test_jaccard_similarity_partial_match():
    first = "database connection failure"
    second = "database connection timeout"

    score = DuplicateDetector.calculate_similarity(first, second)

    # Tokens:
    # First  = {database, connection, failure}
    # Second = {database, connection, timeout}
    # Intersection = 2
    # Union = 4
    assert score == 0.5


def test_jaccard_similarity_empty_descriptions():
    score = DuplicateDetector.calculate_similarity(
        "the is and",
        "a the is",
    )

    assert score == 0.0


def test_duplicate_detector_finds_matching_incident():
    service_id = uuid4()

    original = make_incident(
        "Database connection failure after server restart",
        service_id=service_id,
    )

    candidate = make_incident(
        "Database connection timeout after server restart",
        service_id=service_id,
    )

    detector = DuplicateDetector(threshold=0.50)

    matches = detector.find_duplicates(
        incident=original,
        candidates=[candidate],
    )

    assert len(matches) == 1
    assert matches[0].incident.id == candidate.id
    assert matches[0].similarity_score >= 0.50
    assert "similarity" in matches[0].explanation.lower()


def test_duplicate_detector_ignores_different_service():
    original = make_incident(
        "Database connection failure",
        service_id=uuid4(),
    )

    candidate = make_incident(
        "Database connection failure",
        service_id=uuid4(),
    )

    matches = DuplicateDetector().find_duplicates(
        incident=original,
        candidates=[candidate],
    )

    assert matches == []


def test_duplicate_detector_ignores_different_category():
    service_id = uuid4()

    original = make_incident(
        "Database connection failure",
        service_id=service_id,
        category=IncidentCategory.DATABASE,
    )

    candidate = make_incident(
        "Database connection failure",
        service_id=service_id,
        category=IncidentCategory.NETWORK,
    )

    matches = DuplicateDetector().find_duplicates(
        incident=original,
        candidates=[candidate],
    )

    assert matches == []


def test_duplicate_detector_ignores_itself():
    original = make_incident(
        "Database connection failure",
    )

    matches = DuplicateDetector().find_duplicates(
        incident=original,
        candidates=[original],
    )

    assert matches == []


def test_duplicate_detector_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        DuplicateDetector(threshold=0)

    with pytest.raises(ValueError):
        DuplicateDetector(threshold=1.5)


def test_duplicate_detector_sorts_by_similarity():
    service_id = uuid4()

    original = make_incident(
        "network router connection failure after restart",
        service_id=service_id,
    )

    less_similar = make_incident(
        "network router connection problem",
        service_id=service_id,
    )

    more_similar = make_incident(
        "network router connection failure after restart",
        service_id=service_id,
    )

    matches = DuplicateDetector().find_duplicates(
        original,
        [less_similar, more_similar],
    )

    assert len(matches) == 2
    assert (
        matches[0].similarity_score
        >= matches[1].similarity_score
    )

def test_negation_is_preserved_during_normalization():
    tokens = DuplicateDetector.normalize_description(
        "The server is not responding"
    )

    assert "not" in tokens
    assert "server" in tokens
    assert "responding" in tokens


def test_single_character_technical_tokens_are_preserved():
    tokens = DuplicateDetector.normalize_description(
        "C server failed"
    )

    assert "c" in tokens
    assert "server" in tokens
    assert "failed" in tokens


def test_similarity_above_threshold_is_detected():
    first = "database connection failure timeout"
    second = "database connection failure restart"

    score = DuplicateDetector.calculate_similarity(
        first,
        second,
    )

    assert score == 0.6


def test_similarity_below_threshold_is_not_detected():
    service_id = uuid4()

    original = make_incident(
        "database connection failure timeout",
        service_id=service_id,
    )

    candidate = make_incident(
        "database restart issue",
        service_id=service_id,
    )

    detector = DuplicateDetector(threshold=0.50)

    matches = detector.find_duplicates(
        original,
        [candidate],
    )

    assert matches == []


def test_empty_description_tokens_do_not_create_duplicates():
    service_id = uuid4()

    original = make_incident(
        "the is and",
        service_id=service_id,
    )

    candidate = make_incident(
        "a the is",
        service_id=service_id,
    )

    matches = DuplicateDetector().find_duplicates(
        original,
        [candidate],
    )

    assert matches == []


def test_duplicate_explanation_contains_similarity_details():
    service_id = uuid4()

    original = make_incident(
        "database connection failure",
        service_id=service_id,
    )

    candidate = make_incident(
        "database connection timeout",
        service_id=service_id,
    )

    matches = DuplicateDetector().find_duplicates(
        original,
        [candidate],
    )

    assert len(matches) == 1

    explanation = matches[0].explanation

    assert "similarity" in explanation.lower()
    assert "shared terms" in explanation.lower()
    assert "0.50" in explanation
