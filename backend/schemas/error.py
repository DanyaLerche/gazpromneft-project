from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    reason: str


class Error(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: Error
