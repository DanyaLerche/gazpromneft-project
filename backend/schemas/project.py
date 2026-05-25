# Схемы проектов и ролей доступа.
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.user import User


class ProjectCategory(str, Enum):
    SOFTWARE = "Software"
    MARKETING = "Marketing"
    BUSINESS = "Business"


class ProjectRole(str, Enum):
    USER = "user"
    ADMIN_PROJECT = "admin_project"


class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    key: str = Field(..., max_length=20, description="Ключ проекта (для ключей задач)")
    name: str
    description: str = ""
    category: ProjectCategory = ProjectCategory.SOFTWARE
    created_by: UUID = Field(..., description="Создатель")
    created_at: datetime = Field(..., description="ISO 8601 datetime")
    updated_at: datetime = Field(..., description="ISO 8601 datetime")
    current_user_role: ProjectRole = Field(
        ...,
        description="Эффективная роль текущего пользователя в проекте",
    )


class ProjectResponse(Project):
    model_config = ConfigDict(extra="ignore")


class CreateProjectRequest(BaseModel):
    key: str = Field(..., min_length=2, max_length=20, description="Уникальный ключ проекта")
    name: str = Field(..., min_length=1, max_length=200, description="Название проекта")


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    category: ProjectCategory | None = None


class ProjectUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: UUID
    user_id: UUID
    role: ProjectRole


class ProjectUserExpanded(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user: User
    role: ProjectRole


class AddProjectUserRequest(BaseModel):
    user_id: UUID
    role: ProjectRole


class UpdateProjectUserRequest(BaseModel):
    role: ProjectRole


class PagedProjects(BaseModel):
    items: List[ProjectResponse]
    total: int


class ProjectResponseWrapper(BaseModel):
    project: ProjectResponse


class PagedProjectUsers(BaseModel):
    items: List[ProjectUserExpanded]
    total: int
