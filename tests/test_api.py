"""API endpoint tests."""

from http import HTTPStatus

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Verify the root endpoint returns a status message.

    Args:
        client: FastAPI test client for making requests.
    """
    response = client.get("/api/v1/")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == "ok"


def test_health_check(client: TestClient) -> None:
    """Ensure the health check endpoint reports the service as healthy.

    Args:
        client: FastAPI test client for making requests.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["status"] == "healthy"


def test_analyze_endpoint_success(client: TestClient) -> None:
    """Test successful analysis of text for PII entities.

    Args:
        client: FastAPI test client for making requests.
    """
    test_text = "My name is John Doe and my email is john@example.com"
    response = client.post(
        "/api/v1/analyze",
        json={
            "text": test_text,
            "language": "en",
        },
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "entities" in data
    assert len(data["entities"]) > 0
    # Verify we found at least one PERSON and one EMAIL_ADDRESS
    entity_types = {entity["entity_type"] for entity in data["entities"]}
    assert "PERSON" in entity_types
    assert "EMAIL_ADDRESS" in entity_types


def test_analyze_endpoint_validation(client: TestClient) -> None:
    """Test input validation for analyze endpoint.

    Args:
        client: FastAPI test client
    """  # Test empty text
    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "",
            "language": "en",
        },
    )
    assert (
        response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    )  # Test invalid language code
    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "Some text",
            "language": "invalid",
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
