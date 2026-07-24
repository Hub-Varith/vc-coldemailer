from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Errors always leave the API in the envelope shape (API_ENDPOINTS §Conventions)."""

    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}

    def as_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content={"error": {"code": self.code, "message": self.message, "details": self.details}},
        )


def not_found(resource: str, identifier: str) -> ApiError:
    return ApiError(404, f"{resource}_not_found", f"No {resource.replace('_', ' ')} with id {identifier}.")


async def api_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return exc.as_response()


async def http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    status = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", "Unexpected error")
    code = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict"}.get(
        status, "internal_error"
    )
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": str(detail), "details": {}}})


async def validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    errors = getattr(exc, "errors", lambda: [])()
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request body failed validation.",
                "details": {"errors": [{k: str(v) for k, v in e.items() if k != "ctx"} for e in errors]},
            }
        },
    )
