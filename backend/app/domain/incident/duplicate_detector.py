"""
Rule-based incident duplicate detection.

Uses normalized word tokens and Jaccard similarity.
This module has no dependencies on FastAPI or SQLAlchemy.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.incident.incident import Incident


@dataclass(frozen=True)
class DuplicateMatch:
    """A possible duplicate incident with a matching explanation."""

    incident: Incident
    similarity_score: float
    explanation: str


class DuplicateDetector:
    """
    Detects possible duplicates using Jaccard similarity.

    The repository is responsible for retrieving candidates from the
    same service, category and relevant time window.
    """

    DEFAULT_THRESHOLD = 0.50

    STOP_WORDS = {
        "a", "an", "the",
        "is", "are", "was", "were",
        "am", "be", "been", "being",
        "to", "of", "in", "on", "at",
        "for", "by", "and", "or", "but",
        "with", "from", "after", "before",
        "when", "while", "this", "that",
        "these", "those", "it", "my", "our",
        "we", "i", "you", "your",
        "has", "have", "had", "do", "does",
        "did", "there", "here", "about",
        "into", "out",
    }

    TOKEN_PATTERN = re.compile(r"[^\W_]+", flags=re.UNICODE)

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:

        if not 0 < threshold <= 1:
            raise ValueError(
                "Similarity threshold must be greater than 0 and at most 1."
            )

        self.threshold = threshold

    @classmethod
    def normalize_description(
        cls,
        description: str,
    ) -> set[str]:
        """
        Normalize a description into a set of meaningful tokens.

        Operations:
        1. Unicode normalization.
        2. Lowercase conversion using casefold.
        3. Punctuation removal.
        4. Tokenization.
        5. Stop-word removal.

        Important:
        Negation words such as 'not' are deliberately retained because
        they can change the meaning of an incident description.
        """

        if not isinstance(description, str):
            raise ValueError("Incident description must be a string.")

        normalized = unicodedata.normalize(
            "NFKC",
            description,
        )

        normalized = normalized.casefold()

        # Treat ampersands as the word "and".
        normalized = normalized.replace("&", " and ")

        tokens = cls.TOKEN_PATTERN.findall(normalized)

        return {
            token
            for token in tokens
            if token not in cls.STOP_WORDS
        }

    @classmethod
    def calculate_similarity(
        cls,
        first_description: str,
        second_description: str,
    ) -> float:
        """
        Calculate Jaccard similarity.

        J(A, B) = |A intersection B| / |A union B|
        """

        first_tokens = cls.normalize_description(
            first_description
        )

        second_tokens = cls.normalize_description(
            second_description
        )

        union = first_tokens | second_tokens

        if not union:
            return 0.0

        intersection = first_tokens & second_tokens

        return len(intersection) / len(union)

    def find_duplicates(
        self,
        incident: Incident,
        candidates: Iterable[Incident],
    ) -> list[DuplicateMatch]:
        """
        Return potential duplicates meeting the similarity threshold.

        An incident is never compared with itself.
        Incidents belonging to another service or category are ignored.
        """

        matches: list[DuplicateMatch] = []

        original_tokens = self.normalize_description(
            incident.description
        )

        if not original_tokens:
            return matches

        for candidate in candidates:

            if candidate.id == incident.id:
                continue

            if candidate.service_id != incident.service_id:
                continue

            if candidate.category != incident.category:
                continue

            candidate_tokens = self.normalize_description(
                candidate.description
            )

            union = original_tokens | candidate_tokens

            if not union:
                continue

            intersection = original_tokens & candidate_tokens

            similarity = len(intersection) / len(union)

            # Small tolerance prevents floating-point boundary surprises.
            if similarity + 1e-12 < self.threshold:
                continue

            explanation = (
                "Same affected service and category. "
                f"Description similarity is {similarity:.3f} "
                f"({len(intersection)} shared terms out of "
                f"{len(union)} unique terms). "
                f"The required threshold is {self.threshold:.2f}."
            )

            matches.append(
                DuplicateMatch(
                    incident=candidate,
                    similarity_score=similarity,
                    explanation=explanation,
                )
            )

        # Deterministic ranking: highest similarity first.
        matches.sort(
            key=lambda match: (
                -match.similarity_score,
                match.incident.incident_code,
            )
        )

        return matches
