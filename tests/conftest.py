"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture  # type: ignore[misc]
def client() -> TestClient:
    """Create a test client for the FastAPI application.

    Returns:
        TestClient: A configured test client for making requests.
    """
    return TestClient(app)
