"""Add services and incident categories tables.

Revision ID: 003_add_services_and_incident_categories
Revises: 002_create_users
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import Uuid

# Revision identifiers
revision: str = "003_add_services_and_incident_categories"
down_revision: str | None = "002_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("business_criticality", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "business_criticality >= 1 AND business_criticality <= 5",
            name="ck_services_business_criticality",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "incident_categories",
        sa.Column("id", Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "HARDWARE",
                "SOFTWARE",
                "NETWORK",
                "DATABASE",
                "CLOUD",
                "SECURITY",
                "AUTHENTICATION",
                "APPLICATION",
                "STORAGE",
                name="incident_category_enum",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_skill", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category"),
    )


def downgrade() -> None:
    op.drop_table("incident_categories")
    op.drop_table("services")
