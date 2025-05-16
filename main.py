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
    app.state.analyzer = None

# Include API routes
app.include_router(router)

@app.get("/")
async def read_root():
    """Redirect to the latest API version documentation."""
    return {
        "status": "ok",
        "message": f"Please use the API at /api/{settings.API_VERSION}",
        "docs_url": f"/api/{settings.API_VERSION}/docs"
    }