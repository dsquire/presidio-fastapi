"""Main application module for the Presidio FastAPI service."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings
from app.middleware import SecurityHeadersMiddleware, RateLimiterMiddleware, MetricsMiddleware
from app.services.analyzer import get_analyzer
from app.telemetry import setup_telemetry

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Global variable to store the custom OpenAPI schema
openapi_schema_cache: dict[str, Any] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    await startup_event(app)
    yield
    await shutdown_event(app)


async def startup_event(app: FastAPI) -> None:
    """Perform startup activities."""
    logger.info("Application startup")
    
    logger.info("Setting up telemetry...")
    setup_telemetry(app)
    
    logger.info("Initializing middleware...")
    # Initialize metrics middleware first since others might generate metrics
    metrics_middleware = MetricsMiddleware(app)
    app.state.metrics = metrics_middleware
    app.add_middleware(MetricsMiddleware)
    
    # Initialize security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimiterMiddleware)
    
    # Initialize analyzer
    try:
        logger.info("Initializing analyzer...")
        analyzer = get_analyzer()
        app.state.analyzer = analyzer
        logger.info("Analyzer initialization complete")
    except Exception as e:
        logger.error("Failed to initialize analyzer: %s", str(e))
        raise
    
    logger.info("Application startup complete")


async def shutdown_event(app: FastAPI) -> None:
    """Perform shutdown activities."""
    logger.info("Application shutdown")


# Custom OpenAPI schema generation
def get_openapi_schema() -> dict[str, Any]:
    """Generate and cache a custom OpenAPI schema.

    Returns:
        dict[str, Any]: The custom OpenAPI schema.
    """
    global openapi_schema_cache
    if openapi_schema_cache is None:  # Ensure a dict is always returned
        openapi_schema_cache = {}
    return openapi_schema_cache


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    # Initialize FastAPI with versioned title
    app = FastAPI(
        title=f"Presidio Analyzer API {settings.API_VERSION}",
        docs_url=f"/api/{settings.API_VERSION}/docs",
        redoc_url=f"/api/{settings.API_VERSION}/redoc",
        openapi_url=f"/api/{settings.API_VERSION}/openapi.json",
        lifespan=lifespan,
    )

    # Include API routes
    app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    # This block is for development purposes only
    # Use a proper ASGI server like Uvicorn or Hypercorn in production
    import uvicorn

    uvicorn.run(
        app,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=True,
    )
