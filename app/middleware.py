"""Custom middleware for the application."""

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self';"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limit requests by IP address with burst protection."""

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 60,
        burst_limit: int = 100,
        block_duration: int = 300,  # 5 minutes
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.block_duration = block_duration
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.blocked_ips: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown_client"
        now = datetime.now(timezone.utc)
        now_ts = now.timestamp()

        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            if now < self.blocked_ips[client_ip]:
                retry_after = int((self.blocked_ips[client_ip] - now).total_seconds())
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "IP address blocked due to rate limit violation",
                        "retry_after": retry_after,
                    },
                )
            else:
                del self.blocked_ips[client_ip]

        async with self._lock:
            # Clean old requests
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip] if now_ts - req_time < 60
            ]

            # Check burst limit
            if len(self.requests[client_ip]) >= self.burst_limit:
                block_until = now + timedelta(seconds=self.block_duration)
                self.blocked_ips[client_ip] = block_until
                logger.warning("IP %s blocked for burst limit violation", client_ip)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many requests - IP blocked",
                        "retry_after": self.block_duration,
                    },
                )

            # Check rate limit
            if len(self.requests[client_ip]) >= self.requests_per_minute:
                retry_after = int(60 - (now_ts - self.requests[client_ip][0]))
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many requests",
                        "retry_after": retry_after,
                    },
                )

            # Record request
            self.requests[client_ip].append(now_ts)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_ip])
        )
        response.headers["X-RateLimit-Reset"] = str(int(now_ts - self.requests[client_ip][0]))

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect request metrics with enhanced security monitoring."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.requests_count: int = 0
        self.requests_by_path: dict[str, int] = defaultdict(int)
        self.response_times: list[float] = []
        self.error_counts: dict[int, int] = defaultdict(int)
        self.suspicious_requests: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
    
    def _is_suspicious(self, request: Request) -> bool:
        """Check for potentially suspicious patterns in requests."""
        suspicious_patterns = [
            "../../",  # Path traversal
            "select",  # SQL injection
            "<script",  # XSS
            "../etc/passwd",  # Path traversal
        ]
        path = request.url.path.lower()
        query = str(request.query_params).lower()
        
        return any(pattern in path or pattern in query for pattern in suspicious_patterns)

    async def _update_metrics(
        self, 
        request: Request, 
        duration: float, 
        status_code: int | None = None,
    ) -> None:
        """Update metrics under lock."""
        async with self._lock:
            self.requests_count += 1
            self.requests_by_path[request.url.path] += 1
            self.response_times.append(duration)
            
            # Keep only last minute of response times
            now = time.monotonic()
            cutoff = now - 60  # 1 minute ago
            self.response_times = [t for t in self.response_times if t > cutoff]
            
            # Track errors
            if status_code and status_code >= 400:
                self.error_counts[status_code] += 1

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.monotonic()

        # Check for suspicious activity
        client_host: str = getattr(request.client, "host", "unknown_client")
        if self._is_suspicious(request):
            async with self._lock:
                self.suspicious_requests[client_host] += 1

        try:
            response = await call_next(request)
            duration = time.monotonic() - start_time
            
            await self._update_metrics(
                request=request,
                duration=duration,
                status_code=response.status_code,
            )
            
            return response

        except Exception as e:
            duration = time.monotonic() - start_time
            await self._update_metrics(
                request=request,
                duration=duration,
                status_code=500,
            )
            logger.exception("Error processing request")
            raise

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics with security insights."""
        # Calculate average response time from the last minute
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        
        # Calculate error rate
        error_rate = (
            sum(self.error_counts.values()) / self.requests_count
            if self.requests_count else 0
        )

        return {
            "total_requests": self.requests_count,
            "requests_by_path": dict(self.requests_by_path),
            "average_response_time": round(avg_response_time, 3),
            "requests_in_last_minute": len(self.response_times),
            "error_rate": round(error_rate, 3),
            "error_counts": dict(self.error_counts),
            "suspicious_requests": dict(self.suspicious_requests),
        }
