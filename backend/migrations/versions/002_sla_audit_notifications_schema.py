"""Create SLA policies, incident SLA tracking, audit logs, and notifications tables.

Revision ID: 002_sla_audit_notifications_schema
Revises: 001_initial_technician_schema
Create Date: 2026-11-18 12:00:00.000000+00:00

Database Ownership:
- Module M4 (SLA, Notifications & Audit Automation)
- Tables created:
  - ``sla_policies``: P1–P4 response and resolution duration targets.
  - ``incident_sla_tracking``: Per-incident SLA deadlines, warning, and breach flags.
  - ``audit_logs``: Chronological incident event timeline.
  - ``notifications``: Recipient delivery queue and read state.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import Uuid

# revision identifiers, used by Alembic.
revision: str = "002_sla_audit_notifications_schema"
down_revision: str | None = "001_initial_technician_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. sla_policies ───────────────────────────────────────────────────────
    op.create_table(
        "sla_policies",
        sa.Column("id", Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("response_time_minutes", sa.Integer(), nullable=False),
        sa.Column("resolution_time_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "warning_threshold_percent",
            sa.Integer(),
            nullable=False,
            server_default="80",
        ),
        sa.Column(
            "escalation_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
    op.create_index("ix_sla_policies_priority", "sla_policies", ["priority"], unique=True)

    # ── 2. incident_sla_tracking ──────────────────────────────────────────────
    op.create_table(
        "incident_sla_tracking",
        sa.Column("id", Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            Uuid(as_uuid=True),
            nullable=False,
            comment="Logical FK to M2 incidents.id",
        ),
        sa.Column(
            "policy_id",
            Uuid(as_uuid=True),
            sa.ForeignKey("sla_policies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "response_breached",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "resolution_breached",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "warning_sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "breach_notified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ON_TRACK",
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
    op.create_index(
        "ix_incident_sla_tracking_incident_id",
        "incident_sla_tracking",
        ["incident_id"],
        unique=True,
    )
    op.create_index(
        "ix_incident_sla_tracking_policy_id",
        "incident_sla_tracking",
        ["policy_id"],
    )
    op.create_index(
        "ix_incident_sla_tracking_status",
        "incident_sla_tracking",
        ["status"],
    )
    op.create_index(
        "ix_incident_sla_tracking_priority",
        "incident_sla_tracking",
        ["priority"],
    )

    # ── 3. audit_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            Uuid(as_uuid=True),
            nullable=False,
            comment="Logical FK to M2 incidents.id",
        ),
        sa.Column(
            "actor_id",
            Uuid(as_uuid=True),
            nullable=True,
            comment="Logical FK to M1 users.id",
        ),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
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
    op.create_index("ix_audit_logs_incident_id", "audit_logs", ["incident_id"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"])
    op.create_index(
        "ix_audit_logs_incident_occurred",
        "audit_logs",
        ["incident_id", "occurred_at"],
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # ── 4. notifications ──────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            Uuid(as_uuid=True),
            nullable=False,
            comment="Logical FK to M1 users.id",
        ),
        sa.Column(
            "incident_id",
            Uuid(as_uuid=True),
            nullable=True,
            comment="Logical FK to M2 incidents.id",
        ),
        sa.Column(
            "channel",
            sa.String(length=20),
            nullable=False,
            server_default="IN_APP",
        ),
        sa.Column(
            "notification_type",
            sa.String(length=30),
            nullable=False,
            server_default="GENERAL",
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "delivery_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
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
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_incident_id", "notifications", ["incident_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index(
        "ix_notifications_user_read",
        "notifications",
        ["user_id", "is_read"],
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("audit_logs")
    op.drop_table("incident_sla_tracking")
    op.drop_table("sla_policies")
