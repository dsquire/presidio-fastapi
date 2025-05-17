"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from presidio_fastapi.app.main import create_app

# Test constants
REQUESTS_PER_MINUTE = 60
BURST_LIMIT = 100
BLOCK_DURATION = 1


@pytest.fixture
async def app_with_lifespan() -> AsyncGenerator[FastAPI, None]:
    """Provide a FastAPI app instance with lifespan events executed.

    Yields:
        FastAPI: The application instance.
    """
    app = create_app()
    
    async with app.router.lifespan_context(app):
        # Wait for any background tasks
        await asyncio.sleep(0.1)
        yield app


@pytest.fixture
def client(app_with_lifespan: FastAPI) -> TestClient:
    """Create a test client for the FastAPI app with lifespan setup.

    Args:
        app_with_lifespan: The FastAPI app instance with lifespan events.

    Returns:
        TestClient: A configured test client for making requests.
    """
    # Initialize test client with the app that has completed lifespan setup
    return TestClient(app_with_lifespan)
