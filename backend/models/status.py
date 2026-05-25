#Модель статуса (OpenAPI: Status). Колонка канбана.
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.issue import Issue
    from backend.models.project import Project

# ENUM из init.sql: CREATE TYPE tracker.status_category AS ENUM (...)
STATUS_CATEGORY_ENUM = ENUM(
    "todo",
    "in_progress",
    "done",
    name="status_category",
    schema="tracker",
    create_type=False,
)


class Status(Base):
    __tablename__ = "statuses"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        STATUS_CATEGORY_ENUM, nullable=False, default="todo"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # relationships
    project: Mapped["Project"] = relationship("Project", back_populates="statuses")
    issues: Mapped[list["Issue"]] = relationship(
        "Issue", back_populates="status", foreign_keys="Issue.status_id"
    )
