"""
Central policy for rule-based incident duplicate detection.

The defaults follow the I-ITSM team handbook.
"""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class DuplicateDetectionPolicy:
    """Immutable configuration for duplicate detection."""

    lookback_window: timedelta = timedelta(hours=24)
    similarity_threshold: float = 0.50

    def __post_init__(self) -> None:
        if self.lookback_window <= timedelta(0):
            raise ValueError(
                "Duplicate lookback window must be positive."
            )

        if not 0 < self.similarity_threshold <= 1:
            raise ValueError(
                "Similarity threshold must be greater than 0 and at most 1."
            )


DEFAULT_DUPLICATE_POLICY = DuplicateDetectionPolicy()