# Пользователь (OpenAPI: User). Используется в auth, project и поиске пользователей.
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppRole(str, Enum):
    USER = "user"
    ADMIN_APP = "admin_app"


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    email: str
    full_name: str
    avatar_url: str | None = None
    is_active: bool
    app_role: AppRole
    created_at: datetime


class PagedUsers(BaseModel):
    items: List[User]
    total: int


class UpdateUserAppRoleRequest(BaseModel):
    app_role: AppRole
