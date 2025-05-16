"""Custom middleware for the application."""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
import asyncio

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limit requests by IP address."""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_limit: int = 100
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        now = time.time()
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < 60
        ]
        
        # Check rate limits
        if len(self.requests[client_ip]) >= self.burst_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": "60"
                }
            )
        
        # Record request
        self.requests[client_ip].append(now)
        
        # Process request
        return await call_next(request)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect request metrics."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests_count = 0
        self.requests_by_path = defaultdict(int)
        self.response_times = []
        self._lock = asyncio.Lock()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        async with self._lock:
            self.requests_count += 1
            self.requests_by_path[request.url.path] += 1
            self.response_times.append(duration)
            # Keep only last 1000 response times
            if len(self.response_times) > 1000:
                self.response_times.pop(0)
        
        return response
    
    def get_metrics(self) -> dict:
        """Get current metrics."""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        return {
            "total_requests": self.requests_count,
            "requests_by_path": dict(self.requests_by_path),
            "average_response_time": round(avg_response_time, 3),
            "requests_in_last_minute": len(self.response_times)
        }
