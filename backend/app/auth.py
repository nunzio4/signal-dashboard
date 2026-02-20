"""
Simple API-key guard for write operations.

All GET / HEAD / OPTIONS requests pass through freely (public read access).
POST / PUT / DELETE / PATCH require a valid X-API-Key header.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# HTTP methods that are always allowed without authentication
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class WriteProtectionMiddleware(BaseHTTPMiddleware):
    """Reject write requests that lack a valid API key."""

    async def dispatch(self, request, call_next):
        if request.method in SAFE_METHODS:
            return await call_next(request)

        # No admin key configured = dev mode, allow everything
        if not settings.admin_api_key:
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if provided != settings.admin_api_key:
            logger.warning(
                "Unauthorized write attempt: %s %s from %s",
                request.method,
                request.url.path,
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: valid API key required for write operations"},
            )

        return await call_next(request)
