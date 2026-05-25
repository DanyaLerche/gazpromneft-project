#Модель пользователя (OpenAPI: User). Нужна для Project.created_by и ProjectUser.
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.attachment import IssueAttachment
    from backend.models.worklog import Worklog


APP_ROLE_ENUM = ENUM(
    "user",
    "admin_app",
    name="app_role",
    schema="tracker",
    create_type=False,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    app_role: Mapped[str] = mapped_column(
        APP_ROLE_ENUM,
        nullable=False,
        default="user",
        server_default=text("'user'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    created_projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="creator", foreign_keys="Project.created_by"
    )
    project_roles: Mapped[list["ProjectUser"]] = relationship(
        "ProjectUser", back_populates="user"
    )
    auth_credential: Mapped["AuthCredential | None"] = relationship(
        "AuthCredential", back_populates="user", uselist=False
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user"
    )
    auth_events: Mapped[list["AuthEvent"]] = relationship(
        "AuthEvent", back_populates="user"
    )
    email_verification: Mapped["EmailVerification | None"] = relationship(
        "EmailVerification", back_populates="user", uselist=False
    )
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule", back_populates="user"
    )
    worklogs: Mapped[list["Worklog"]] = relationship(
        "Worklog", back_populates="user"
    )
    attachments: Mapped[list["IssueAttachment"]] = relationship(
        "IssueAttachment", back_populates="uploader"
    )
