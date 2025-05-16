"""Main application module for the Presidio FastAPI service."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
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
    yield


async def startup_event() -> None:
    """Perform startup activities."""
    logger.info("Application startup")
    setup_telemetry(app)


async def shutdown_event() -> None:
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

    @app.on_event("startup")
    async def startup() -> None:
        """Initializes application resources on startup.

        This function sets up logging, initializes OpenTelemetry for tracing,
        and creates the Presidio analyzer engine. It stores the analyzer
        instance in the application state. If any step fails, it logs the error
        and re-raises the exception to prevent the application from starting
        in a broken state.
        """
        try:
            logger.info("Starting up application...")

            # Initialize OpenTelemetry
            logger.info("Configuring OpenTelemetry...")
            setup_telemetry(app)

            # Initialize analyzer
            logger.info("Initializing analyzer...")
            analyzer = get_analyzer()
            app.state.analyzer = analyzer

            logger.info("Application startup complete")

        except Exception as e:
            logger.error(f"Error during startup: {str(e)}")
            logger.exception(e)
            raise

    @app.on_event("shutdown")
    async def shutdown() -> None:
        """Cleans up resources on application shutdown.

        Currently, this function sets the analyzer instance in the application
        state to None, allowing it to be garbage collected.
        """
        app.state.analyzer = None

    # Include API routes
    app.include_router(router)

    @app.get("/")
    async def read_root() -> dict[str, str]:
        """Redirects to the latest API version documentation.

        Returns:
            dict: A dictionary containing a status message and the URL
                  to the API documentation.
        """
        return {
            "status": "ok",
            "message": f"Please use the API at /api/{settings.API_VERSION}",
            "docs_url": f"/api/{settings.API_VERSION}/docs",
        }

    return app


app = create_app()


if __name__ == "__main__":
    # This block is for development purposes only
    # Use a proper ASGI server like Uvicorn or Hypercorn in production
    import uvicorn

    uvicorn.run(
        app,
        host=settings.SERVER_HOST,  # Corrected attribute name
        port=settings.SERVER_PORT,  # Corrected attribute name
        log_level=settings.LOG_LEVEL.lower(),  # Ensure log_level is lowercase
        reload=True,
    )
