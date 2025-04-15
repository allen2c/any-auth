import secrets
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    """

    def __init__(self, app: ASGIApp, csp_directives: dict[str, str] | None = None):
        super().__init__(app)
        self.csp = self._build_csp_header(csp_directives or {})

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers to all responses
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = (
            "0"  # Not needed with modern CSP, but some legacy browsers use it
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = self.csp
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        return response

    def _build_csp_header(self, directives: dict[str, str]) -> str:
        """Build Content Security Policy header with sensible defaults"""
        default_directives = {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src": "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "img-src": "'self' https://fastapi.tiangolo.com",
            "font-src": "'self'",
            "connect-src": "'self'",
            "frame-src": "'none'",
            "object-src": "'none'",
            "base-uri": "'self'",
        }

        # Override defaults with any provided directives
        for key, value in directives.items():
            default_directives[key] = value

        # Build the header string
        return "; ".join(f"{key} {value}" for key, value in default_directives.items())


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that implements proper CSRF protection for OAuth2 endpoints.

    For authorization endpoint:
    - Requires state parameter
    - Validates CSRF token from session/cookie

    For token endpoint:
    - Not needed due to client authentication and secret channel
    """

    EXCLUDED_PATHS = {"/token", "/introspect", "/revoke"}

    def __init__(
        self,
        app: ASGIApp,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        cookie_max_age: int = 3600,
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.cookie_max_age = cookie_max_age

    async def dispatch(self, request: Request, call_next):
        path = request.url.path.lower()

        # Skip CSRF check for non-GET OAuth endpoints (they use client authentication)
        if request.method != "GET" and any(
            path.endswith(excluded) for excluded in self.EXCLUDED_PATHS
        ):
            return await call_next(request)

        # For GET to authorization endpoint, set CSRF token
        if request.method == "GET" and path.endswith("/authorize"):
            response = await call_next(request)

            # Generate or retrieve CSRF token
            csrf_token = request.cookies.get(self.cookie_name) or secrets.token_urlsafe(
                32
            )

            # Set the token in response cookie if not already present
            if self.cookie_name not in request.cookies:
                response.set_cookie(
                    key=self.cookie_name,
                    value=csrf_token,
                    max_age=self.cookie_max_age,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                )

            return response

        # For POST to authorization endpoint, validate CSRF token
        elif request.method == "POST" and path.endswith("/authorize"):
            csrf_cookie = request.cookies.get(self.cookie_name)
            csrf_header = request.headers.get(self.header_name)

            # Check for token in header or form data
            if not csrf_header:
                form_data = await request.form()
                csrf_header = form_data.get("csrf_token")

            if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                return Response(content="CSRF validation failed", status_code=403)

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware to prevent abuse.

    Uses a sliding window algorithm to count requests.
    Ideally, you would use Redis for distributed environments.
    """

    def __init__(
        self,
        app: ASGIApp,
        rate_limit: int = 60,  # requests per minute
        window_size: int = 60,  # seconds
    ):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_size = window_size
        self.request_records: dict[str, list[float]] = (
            {}
        )  # ip -> [timestamp, timestamp, ...]

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        # Skip rate limiting for whitelisted IPs (optional)
        # if client_ip in WHITELISTED_IPS:
        #     return await call_next(request)

        # Get current timestamp
        now = time.time()

        # Initialize record for new clients
        if client_ip not in self.request_records:
            self.request_records[client_ip] = []

        # Remove timestamps outside the current window
        self.request_records[client_ip] = [
            timestamp
            for timestamp in self.request_records[client_ip]
            if now - timestamp <= self.window_size
        ]

        # Check if rate limit exceeded
        if len(self.request_records[client_ip]) >= self.rate_limit:
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={"Retry-After": str(self.window_size)},
            )

        # Record this request
        self.request_records[client_ip].append(now)

        # Process the request
        return await call_next(request)
