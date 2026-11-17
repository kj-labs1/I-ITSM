
"""
IncidentComment domain entity — Member 2.

Represents a comment or additional information attached
to an incident.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class IncidentComment:
    """
    Represents one comment associated with an incident.

    incident_id:
        Parent incident UUID.

    author_id:
        UUID of the user who submitted the comment.

    content:
        Text of the comment.
    """

    incident_id: UUID
    author_id: UUID
    content: str

    id: UUID = field(default_factory=uuid4)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        """Validate comment content."""

        if not self.content or not self.content.strip():
            raise ValueError("Comment content cannot be empty.")

        self.content = self.content.strip()

    def __repr__(self) -> str:
        return (
            f"IncidentComment("
            f"id={self.id}, "
            f"incident_id={self.incident_id}"
            f")"
        )
