"""Initial technician schema

Revision ID: 001_initial_technician_schema
Revises:
Create Date: 2026-11-12 12:00:00.000000+00:00

Database Ownership:
- Module M3 (Technician Management & Assignment Engine)
- Tables created:
  - `technicians`: Stores technician operational parameters, capacity, and availability.
  - `technician_skills`: Stores acquired skill proficiency ratings (1-5).
- Shared Identity Contract:
  - `technicians.user_id` holds the UUID from M1's `users` table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import Uuid

# revision identifiers, used by Alembic.
revision: str = "001_initial_technician_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Create technicians table ──────────────────────────────────────────────
    op.create_table(
        "technicians",
        sa.Column("id", Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            Uuid(as_uuid=True),
            nullable=False,
            comment="References M1 users.id — shared User UUID",
        ),
        sa.Column(
            "availability",
            sa.String(length=20),
            nullable=False,
            server_default="AVAILABLE",
        ),
        sa.Column(
            "experience_years",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Proposed field: years of professional experience",
        ),
        sa.Column(
            "max_capacity",
            sa.Integer(),
            nullable=False,
            server_default="10",
            comment="Proposed field: maximum concurrent assigned incidents",
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
    )
    op.create_index("ix_technicians_user_id", "technicians", ["user_id"], unique=True)

    # ── Create technician_skills table ────────────────────────────────────────
    op.create_table(
        "technician_skills",
        sa.Column("id", Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "technician_id",
            Uuid(as_uuid=True),
            sa.ForeignKey("technicians.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_name",
            sa.String(length=100),
            nullable=False,
            comment="Skill name or category mapping",
        ),
        sa.Column(
            "proficiency_level",
            sa.Integer(),
            nullable=False,
            server_default="3",
            comment="Proficiency score from 1 (Novice) to 5 (Expert)",
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
        sa.UniqueConstraint("technician_id", "skill_name", name="uq_technician_skill"),
    )
    op.create_index(
        "ix_technician_skills_technician_id",
        "technician_skills",
        ["technician_id"],
    )
    op.create_index(
        "ix_technician_skills_skill_name",
        "technician_skills",
        ["skill_name"],
    )


def downgrade() -> None:
    op.drop_table("technician_skills")
    op.drop_table("technicians")
