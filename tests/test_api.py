"""API endpoint tests."""
from fastapi.testclient import TestClient

def test_root_endpoint(client: TestClient):
    """Test the root endpoint returns correct status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_analyze_endpoint_success(client: TestClient):
    """Test successful PII analysis."""
    test_text = "My name is John Doe and my email is john@example.com"
    response = client.post(
        "/analyze",
        json={
            "text": test_text,
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "entities" in data
    assert len(data["entities"]) > 0
    # Verify we found at least one PERSON and one EMAIL_ADDRESS
    entity_types = {entity["entity_type"] for entity in data["entities"]}
    assert "PERSON" in entity_types
    assert "EMAIL_ADDRESS" in entity_types

def test_analyze_endpoint_validation(client: TestClient):
    """Test input validation for analyze endpoint."""
    # Test empty text
    response = client.post(
        "/analyze",
        json={
            "text": "",
            "language": "en"
        }
    )
    assert response.status_code == 422

    # Test invalid language code
    response = client.post(
        "/analyze",
        json={
            "text": "Some text",
            "language": "invalid"
        }
    )
    assert response.status_code == 422
