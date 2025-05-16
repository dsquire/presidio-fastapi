"""Main application module."""
import logging
from fastapi import FastAPI
from app.api.routes import router
from app.services.analyzer import get_analyzer

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presidio Analyzer API")

@app.on_event("startup")
async def startup():
    try:
        logger.info("Starting up application...")
        logger.info("Initializing analyzer...")
        analyzer = get_analyzer()
        logger.info("Analyzer initialized successfully")
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
    return {"status": "ok"}