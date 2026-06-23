"""
Standardized error types and FastAPI exception handlers.
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class MerchMindError(Exception):
    """Base application error."""
    def __init__(self, message: str, code: str = "internal_error"):
        super().__init__(message)
        self.code = code


class NotFoundError(MerchMindError):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(f"{resource} '{resource_id}' not found", "not_found")


class ValidationError(MerchMindError):
    def __init__(self, message: str):
        super().__init__(message, "validation_error")


class ExternalAPIError(MerchMindError):
    def __init__(self, service: str, detail: str):
        super().__init__(f"{service} API error: {detail}", "external_api_error")


def _envelope(success: bool, data=None, error: str = None) -> dict:
    return {"success": success, "data": data, "error": error}


def _cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin")
    if not origin:
        return {}
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-credentials": "true",
    }


async def merchmind_exception_handler(request: Request, exc: MerchMindError) -> JSONResponse:
    status = 404 if exc.code == "not_found" else 400 if exc.code == "validation_error" else 500
    logger.error(f"MerchMindError [{exc.code}]: {exc}")
    return JSONResponse(status_code=status, content=_envelope(False, error=str(exc)), headers=_cors_headers(request))


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_envelope(False, error=exc.detail), headers=_cors_headers(request))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception on {request.method} {request.url}")
    return JSONResponse(status_code=500, content=_envelope(False, error=f"Internal server error: {exc}"), headers=_cors_headers(request))
