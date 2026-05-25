from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    500: "INTERNAL_ERROR",
}

_MESSAGE_MAP = {
    400: "Bad request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not found",
    500: "Internal server error",
}


def _build_error_response(
    request: Request,
    status_code: int,
    message: str | None = None,
    code: str | None = None,
    details: list[dict[str, str | None]] | None = None,
) -> dict:
    return {
        "error": {
            "code": code or _CODE_MAP.get(status_code, "ERROR"),
            "message": message or _MESSAGE_MAP.get(status_code, "Error"),
            "details": details,
            "request_id": request.headers.get("X-Request-ID") or str(uuid4()),
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        message = str(exc.detail) if exc.detail is not None else None
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_response(
                request=request,
                status_code=exc.status_code,
                message=message,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        details: list[dict[str, str | None]] = []
        for error in exc.errors():
            loc = [str(part) for part in error.get("loc", []) if part != "body"]
            details.append(
                {
                    "field": ".".join(loc) if loc else None,
                    "reason": error.get("msg", "Invalid value"),
                }
            )
        return JSONResponse(
            status_code=400,
            content=_build_error_response(
                request=request,
                status_code=400,
                code="VALIDATION_ERROR",
                message="Validation failed",
                details=details or None,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server error: %s", exc.__class__.__name__)
        return JSONResponse(
            status_code=500,
            content=_build_error_response(request=request, status_code=500),
        )
