"""
Standardized API response helpers to reduce boilerplate in endpoints.
"""
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


def success(data: Any = None, message: str = None, **extra) -> Dict:
    """Create a success response."""
    response = {"status": "success"}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    response.update(extra)
    return response


def error(message: str, status_code: int = 400, **extra) -> JSONResponse:
    """Create an error response with proper HTTP status code."""
    content = {"status": "error", "message": message}
    content.update(extra)
    return JSONResponse(content=content, status_code=status_code)


def not_found(message: str = "Resource not found", **extra) -> JSONResponse:
    """Create a 404 not found response."""
    return error(message, status_code=404, **extra)


def waiting(message: str = "Waiting for session", **extra) -> Dict:
    """Create a waiting status response."""
    response = {"status": "waiting", "message": message}
    response.update(extra)
    return response


def not_in_session(message: str = "Trader not in active session", **extra) -> Dict:
    """Create a not-in-session response."""
    response = {"status": "not_in_session", "message": message}
    response.update(extra)
    return response
