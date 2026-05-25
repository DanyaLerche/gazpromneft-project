# Auth схемы из OpenAPI (register, login, refresh, me).
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from backend.schemas.user import User


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str = Field(..., min_length=8)


class RegisterResponse(BaseModel):
    email: str
    verification_required: bool = True


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: User


class MeResponse(BaseModel):
    user: User


class UpdateMyProfileRequest(BaseModel):
    avatar_url: Optional[str] = Field(default=None, max_length=4_000_000)


class VerifyEmailRequest(BaseModel):
    email: str
    code: str = Field(..., min_length=4, max_length=12)


class VerifyEmailResponse(BaseModel):
    verified: bool = True


class ResendVerificationRequest(BaseModel):
    email: str


class ResendVerificationResponse(BaseModel):
    sent: bool = True
