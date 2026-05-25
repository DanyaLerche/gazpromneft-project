"""Модели проектов (OpenAPI: Project, ProjectUser)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

# ENUM из init.sql: CREATE TYPE tracker.project_role AS ENUM (...)
PROJECT_ROLE_ENUM = ENUM(
    "user",
    "admin_project",
    name="project_role",
    schema="tracker",
    create_type=False,
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Software",
        server_default=text("'Software'"),
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # relationships
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_projects", foreign_keys=[created_by]
    )
    project_users: Mapped[list["ProjectUser"]] = relationship(
        "ProjectUser", back_populates="project"
    )
    statuses: Mapped[list["Status"]] = relationship(
        "Status", back_populates="project"
    )
    issues: Mapped[list["Issue"]] = relationship(
        "Issue", back_populates="project"
    )


class ProjectUser(Base):
    #Участник проекта с ролью (OpenAPI: ProjectUser).
    __tablename__ = "project_users"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        PROJECT_ROLE_ENUM,
        nullable=False,
        default="user",
        server_default=text("'user'"),
    )

    # relationships
    project: Mapped["Project"] = relationship("Project", back_populates="project_users")
    user: Mapped["User"] = relationship("User", back_populates="project_roles")
