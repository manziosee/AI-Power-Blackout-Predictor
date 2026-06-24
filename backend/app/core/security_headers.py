"""Security headers middleware — applied globally to every response."""
from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects defensive HTTP security headers on every response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Prevent browsers from MIME-sniffing away from declared Content-Type
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Deny framing everywhere (clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"
        # Disable legacy XSS filter (modern browsers use CSP instead)
        response.headers["X-XSS-Protection"] = "0"
        # Referrer — send origin only, not full URL
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions policy — disable browser features not needed by the API
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        # Content Security Policy — API responses, not HTML pages; restrict everything
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        # HSTS — 1 year, include subdomains (only meaningful over HTTPS)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        # Remove server fingerprint headers that may have been set upstream
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]
        return response
