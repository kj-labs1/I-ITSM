"""Add incident archiving and duplicate merging columns.

Revision ID: 006_incident_archive_merge
Revises: 005_sla_audit_notifications
Create Date: 2026-11-21 21:55:00.000000+00:00

Database Ownership:
- Module M2 (Incident Management)
- Adds archiving and duplicate incident merging reference columns to ``incidents`` table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import Uuid

# revision identifiers, used by Alembic.
revision: str = "006_incident_archive_merge"
down_revision: str | None = "005_sla_audit_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Archiving columns
    op.add_column(
        "incidents",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether incident has been soft-archived by admin",
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when incident was archived",
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "archived_by",
            Uuid(as_uuid=True),
            nullable=True,
            comment="Logical reference to users.id who archived the incident",
        ),
    )

    # Merging columns
    op.add_column(
        "incidents",
        sa.Column(
            "merged_into_incident_id",
            Uuid(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
            comment="Reference to canonical primary incident if merged",
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "merged_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when incident was merged",
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "merged_by",
            Uuid(as_uuid=True),
            nullable=True,
            comment="Logical reference to users.id who merged the incident",
        ),
    )

    # Indices
    op.create_index(
        "ix_incidents_is_archived",
        "incidents",
        ["is_archived"],
        unique=False,
    )
    op.create_index(
        "ix_incidents_merged_into_incident_id",
        "incidents",
        ["merged_into_incident_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_incidents_merged_into_incident_id", table_name="incidents")
    op.drop_index("ix_incidents_is_archived", table_name="incidents")

    op.drop_column("incidents", "merged_by")
    op.drop_column("incidents", "merged_at")
    op.drop_column("incidents", "merged_into_incident_id")

    op.drop_column("incidents", "archived_by")
    op.drop_column("incidents", "archived_at")
    op.drop_column("incidents", "is_archived")
