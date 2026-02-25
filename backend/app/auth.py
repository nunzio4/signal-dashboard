"""
Security middleware for the Signal Dashboard.

- Write protection: POST/PUT/DELETE require valid X-API-Key header.
- Admin-read protection: certain GET endpoints require API key too.
- Rate limiting: block IPs after repeated auth failures.
- Security headers: add standard hardening headers to every response.
"""

import logging
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# HTTP methods that are always allowed without authentication
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# GET paths that still require admin API key
ADMIN_GET_PATHS = {"/api/analytics/digest", "/api/analytics/logs"}

# ── Rate limiting for auth failures ──
# Track failed auth attempts per IP: {ip: [(timestamp, ...), ...]}
_auth_failures: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 900        # 15-minute window
RATE_LIMIT_MAX_FAILURES = 10   # max failures before lockout


def _is_rate_limited(ip: str) -> bool:
    """Check if an IP is currently rate-limited due to auth failures."""
    now = time.time()
    # Prune old entries
    _auth_failures[ip] = [t for t in _auth_failures[ip] if now - t < RATE_LIMIT_WINDOW]
    return len(_auth_failures[ip]) >= RATE_LIMIT_MAX_FAILURES


def _record_failure(ip: str) -> None:
    """Record an auth failure for an IP."""
    _auth_failures[ip].append(time.time())


class WriteProtectionMiddleware(BaseHTTPMiddleware):
    """Reject write requests that lack a valid API key, with rate limiting."""

    async def dispatch(self, request, call_next):
        ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Check if this is a safe (public) request
        is_safe = request.method in SAFE_METHODS and path not in ADMIN_GET_PATHS

        if is_safe:
            return await call_next(request)

        # All non-safe requests below require authentication

        # No admin key configured = dev mode, allow everything
        if not settings.admin_api_key:
            return await call_next(request)

        # Rate limiting check
        if _is_rate_limited(ip):
            logger.warning("Rate-limited IP attempted request: %s %s from %s", request.method, path, ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many failed authentication attempts. Try again later."},
            )

        provided = request.headers.get("X-API-Key", "")
        if provided != settings.admin_api_key:
            _record_failure(ip)
            remaining = RATE_LIMIT_MAX_FAILURES - len(_auth_failures.get(ip, []))
            logger.warning(
                "Unauthorized attempt: %s %s from %s (%d attempts remaining)",
                request.method, path, ip, max(remaining, 0),
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: valid API key required"},
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every response."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Only allow HTTPS (tell browsers to always use HTTPS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Restrict permissions
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        return response
