"""API endpoint tests."""

from http import HTTPStatus
from unittest.mock import patch

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
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY  # Test invalid language code
    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "Some text",
            "language": "invalid",
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_analyze_endpoint_analyzer_unavailable(client: TestClient) -> None:
    """Test analyze endpoint when analyzer service is unavailable.

    Args:
        client: FastAPI test client for making requests.
    """
    with patch.object(client.app.state, "analyzer", None):
        response = client.post(
            "/api/v1/analyze",
            json={
                "text": "Test text",
                "language": "en",
            },
        )
        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        data = response.json()
        assert "Analyzer service not available" in data["detail"]


def test_analyze_endpoint_internal_server_error(client: TestClient) -> None:
    """Test analyze endpoint with internal server error simulation.

    Args:
        client: FastAPI test client for making requests.
    """
    with patch("presidio_fastapi.app.api.routes.analyze_with_metrics") as mock_analyze:
        mock_analyze.side_effect = Exception("Database connection failed")

        response = client.post(
            "/api/v1/analyze",
            json={
                "text": "Test text",
                "language": "en",
            },
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Internal server error occurred" in data["detail"]


def test_batch_analyze_endpoint_success(client: TestClient) -> None:
    """Test successful batch analysis of multiple texts.

    Args:
        client: FastAPI test client for making requests.
    """
    test_texts = [
        "My name is John Doe",
        "Contact me at jane@example.com",
        "Call me at 555-123-4567",
    ]

    response = client.post(
        "/api/v1/analyze/batch",
        json={
            "texts": test_texts,
            "language": "en",
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 3

    # Verify each result has the expected structure
    for result in data["results"]:
        assert "entities" in result
        assert isinstance(result["entities"], list)


def test_batch_analyze_endpoint_empty_texts(client: TestClient) -> None:
    """Test batch analysis with empty text list.

    Args:
        client: FastAPI test client for making requests.
    """
    response = client.post(
        "/api/v1/analyze/batch",
        json={
            "texts": [],
            "language": "en",
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 0


def test_batch_analyze_endpoint_analyzer_unavailable(client: TestClient) -> None:
    """Test batch analyze endpoint when analyzer service is unavailable.

    Args:
        client: FastAPI test client for making requests.
    """
    with patch.object(client.app.state, "analyzer", None):
        response = client.post(
            "/api/v1/analyze/batch",
            json={
                "texts": ["Test text"],
                "language": "en",
            },
        )
        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        data = response.json()
        assert "Analyzer service not available" in data["detail"]


def test_batch_analyze_endpoint_internal_error(client: TestClient) -> None:
    """Test batch analyze endpoint with internal server error simulation.

    Args:
        client: FastAPI test client for making requests.
    """
    with patch("presidio_fastapi.app.api.routes._analyze_single_text") as mock_analyze:
        mock_analyze.side_effect = Exception("Processing failed")

        response = client.post(
            "/api/v1/analyze/batch",
            json={
                "texts": ["Test text"],
                "language": "en",
            },
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Internal server error occurred" in data["detail"]


def test_batch_analyze_validation_errors(client: TestClient) -> None:
    """Test batch analyze endpoint input validation.

    Args:
        client: FastAPI test client for making requests.
    """
    # Test invalid language code
    response = client.post(
        "/api/v1/analyze/batch",
        json={
            "texts": ["Test text"],
            "language": "invalid",
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # Test missing texts field
    response = client.post(
        "/api/v1/analyze/batch",
        json={
            "language": "en",
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_analyze_single_text_empty_results(client: TestClient) -> None:
    """Test analysis when no PII entities are found.

    Args:
        client: FastAPI test client for making requests.
    """
    # Text with no recognizable PII
    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "This is a simple text with no personal information.",
            "language": "en",
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "entities" in data
    # Should return empty list when no entities found
    assert isinstance(data["entities"], list)


def test_analyze_with_different_languages(client: TestClient) -> None:
    """Test analysis with different supported languages.

    Args:
        client: FastAPI test client for making requests.
    """
    test_cases = [
        ("en", "My name is John Doe"),
        ("es", "Mi nombre es Juan Pérez"),
        ("de", "Mein Name ist Hans Müller"),
    ]

    for language, text in test_cases:
        response = client.post(
            "/api/v1/analyze",
            json={
                "text": text,
                "language": language,
            },
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "entities" in data


def test_analyze_with_special_characters(client: TestClient) -> None:
    """Test analysis with special characters and unicode.

    Args:
        client: FastAPI test client for making requests.
    """
    special_text = "Name: José María, Email: josé@example.com, Phone: +1-555-123-4567"

    response = client.post(
        "/api/v1/analyze",
        json={
            "text": special_text,
            "language": "en",
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "entities" in data


def test_analyze_large_text(client: TestClient) -> None:
    """Test analysis with large text input.

    Args:
        client: FastAPI test client for making requests.
    """
    # Create a large text with repeated patterns
    large_text = "My name is John Doe. " * 100 + "Contact: john@example.com"

    response = client.post(
        "/api/v1/analyze",
        json={
            "text": large_text,
            "language": "en",
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "entities" in data
