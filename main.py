"""Main application module."""
import logging

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.services.analyzer import get_analyzer
from app.telemetry import setup_telemetry

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Initialize FastAPI with versioned title
app = FastAPI(
    title=f"Presidio Analyzer API {settings.API_VERSION}",
    docs_url=f"/api/{settings.API_VERSION}/docs",
    redoc_url=f"/api/{settings.API_VERSION}/redoc",
    openapi_url=f"/api/{settings.API_VERSION}/openapi.json"
)

@app.on_event("startup")
async def startup():
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
async def shutdown():
    """Cleans up resources on application shutdown.

    Currently, this function sets the analyzer instance in the application
    state to None, allowing it to be garbage collected.
    """
    app.state.analyzer = None

# Include API routes
app.include_router(router)

@app.get("/")
async def read_root():
    """Redirects to the latest API version documentation.

    Returns:
        dict: A dictionary containing a status message and the URL
              to the API documentation.
    """
    return {
        "status": "ok",
        "message": f"Please use the API at /api/{settings.API_VERSION}",
        "docs_url": f"/api/{settings.API_VERSION}/docs"
    }