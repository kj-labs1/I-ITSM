
"""Create incident and incident_comments tables.

Revision ID: 002_incident_schema
Revises: 001_initial_technician_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import Uuid


# Revision identifiers.
revision: str = "004_incidents_and_comments"

down_revision: str | None = "003_services_and_categories"

branch_labels: str | Sequence[str] | None = None

depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    # ============================================================
    # INCIDENTS TABLE
    # ============================================================

    op.create_table(
        "incidents",

        sa.Column(
            "id",
            Uuid(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "incident_code",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "reporter_id",
            Uuid(as_uuid=True),
            nullable=False,
            comment="Logical reference to users.id owned by M1",
        ),

        sa.Column(
            "service_id",
            Uuid(as_uuid=True),
            nullable=False,
            comment="Logical reference to services.id owned by M1",
        ),

        sa.Column(
            "category",
            sa.String(length=32),
            nullable=False,
        ),

        sa.Column(
            "required_skill",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "impact",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "urgency",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "business_criticality",
            sa.Integer(),
            nullable=False,
            comment="Snapshot of affected service criticality",
        ),

        sa.Column(
            "priority",
            sa.String(length=2),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="NEW",
        ),

        sa.Column(
            "assigned_technician_id",
            Uuid(as_uuid=True),
            nullable=True,
            comment="Logical reference to technicians.user_id",
        ),

        sa.Column(
            "resolution_details",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        # Unique incident code.
        sa.UniqueConstraint(
            "incident_code",
            name="uq_incidents_incident_code",
        ),

        # Data validation constraints.
        sa.CheckConstraint(
            "impact BETWEEN 1 AND 5",
            name="ck_incidents_impact_range",
        ),

        sa.CheckConstraint(
            "urgency BETWEEN 1 AND 5",
            name="ck_incidents_urgency_range",
        ),

        sa.CheckConstraint(
            "business_criticality BETWEEN 1 AND 5",
            name="ck_incidents_business_criticality_range",
        ),
    )

    # Incident search indexes.
    op.create_index(
        "ix_incidents_reporter_id",
        "incidents",
        ["reporter_id"],
    )

    op.create_index(
        "ix_incidents_service_id",
        "incidents",
        ["service_id"],
    )

    op.create_index(
        "ix_incidents_category",
        "incidents",
        ["category"],
    )

    op.create_index(
        "ix_incidents_priority",
        "incidents",
        ["priority"],
    )

    op.create_index(
        "ix_incidents_status",
        "incidents",
        ["status"],
    )

    op.create_index(
        "ix_incidents_created_at",
        "incidents",
        ["created_at"],
    )

    op.create_index(
        "ix_incidents_assigned_technician_id",
        "incidents",
        ["assigned_technician_id"],
    )

    # ============================================================
    # INCIDENT COMMENTS TABLE
    # ============================================================

    op.create_table(
        "incident_comments",

        sa.Column(
            "id",
            Uuid(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "incident_id",
            Uuid(as_uuid=True),
            sa.ForeignKey(
                "incidents.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "author_id",
            Uuid(as_uuid=True),
            nullable=False,
            comment="Logical reference to users.id",
        ),

        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_incident_comments_content_not_empty",
        ),
    )

    op.create_index(
        "ix_incident_comments_incident_id",
        "incident_comments",
        ["incident_id"],
    )


def downgrade() -> None:

    # Remove child table first.
    op.drop_index(
        "ix_incident_comments_incident_id",
        table_name="incident_comments",
    )

    op.drop_table("incident_comments")

    # Remove incident indexes.
    op.drop_index(
        "ix_incidents_assigned_technician_id",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_created_at",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_status",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_priority",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_category",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_service_id",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_reporter_id",
        table_name="incidents",
    )

    op.drop_table("incidents")
