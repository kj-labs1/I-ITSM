"""
SQLAlchemy declarative base and common model mixins.

OOP Design:
- Encapsulates common persistence behaviors (UUID primary keys, audit timestamps)
  in reusable mixin classes.
- DeclarativeBase provides the root abstraction for all relational entity mappings.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class Base(DeclarativeBase):
    """Root base class for all SQLAlchemy ORM models in I-ITSM."""

    pass


class TimestampMixin:
    """Mixin providing created_at and updated_at timestamp columns in UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Mixin providing a UUID primary key with automatic generation."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
