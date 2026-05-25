#Модель задачи/эпика (OpenAPI: Issue).
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.attachment import IssueAttachment
    from backend.models.criticality import Criticality
    from backend.models.project import Project
    from backend.models.status import Status
    from backend.models.user import User
    from backend.models.worklog import Worklog

# ENUM из init.sql: CREATE TYPE tracker.issue_type AS ENUM (...)
ISSUE_TYPE_ENUM = ENUM(
    "epic",
    "task",
    name="issue_type",
    schema="tracker",
    create_type=False,
)


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (UniqueConstraint("project_id", "key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(ISSUE_TYPE_ENUM, nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    criticality_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("criticalities.id", ondelete="SET NULL"), nullable=True
    )
    status_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("statuses.id", ondelete="RESTRICT"), nullable=True
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("issues.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    taken_in_work_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    project: Mapped["Project"] = relationship("Project", back_populates="issues")
    status: Mapped["Status | None"] = relationship(
        "Status", back_populates="issues", foreign_keys=[status_id]
    )
    criticality: Mapped["Criticality | None"] = relationship(
        "Criticality", back_populates="issues"
    )
    author: Mapped["User"] = relationship(
        "User", foreign_keys=[author_id]
    )
    assignee: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assignee_id]
    )
    parent: Mapped["Issue | None"] = relationship(
        "Issue", remote_side="Issue.id", back_populates="children", foreign_keys=[parent_id]
    )
    children: Mapped[list["Issue"]] = relationship(
        "Issue", back_populates="parent", foreign_keys=[parent_id]
    )
    attachments: Mapped[list["IssueAttachment"]] = relationship(
        "IssueAttachment", back_populates="issue"
    )
    worklogs: Mapped[list["Worklog"]] = relationship(
        "Worklog", back_populates="issue"
    )
