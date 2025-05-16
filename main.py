"""Main application module."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config import settings
from app.middleware import SecurityHeadersMiddleware, RateLimiterMiddleware, MetricsMiddleware

# Initialize FastAPI app with metadata
app = FastAPI(
    title="Presidio Analyzer API",
    description="API for analyzing text for PII using Microsoft Presidio",
    version="1.0.0"
)

# Add middleware in order (last added = first executed)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimiterMiddleware,
    requests_per_minute=60,
    burst_limit=100
)

# Add metrics middleware and store reference
metrics_middleware = MetricsMiddleware(app)
app.add_middleware(lambda app: metrics_middleware)
app.metrics = metrics_middleware

# Add CORS middleware with secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=bool(settings.cors_origins),  # Only True when origins are specified
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=86400,  # 24 hours
)

# Include API routes
app.include_router(router)

@app.get("/")
async def read_root():
    """Root endpoint for API status."""
    return {
        "status": "ok",
        "message": "Welcome to Presidio Analyzer API. Use POST /analyze to analyze text."
    }