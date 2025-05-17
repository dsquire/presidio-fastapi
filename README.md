# Presidio FastAPI Service

A secure, high-performance FastAPI service for detecting Personally Identifiable Information (PII) in text using Microsoft's Presidio Analyzer.

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)

## Features

- PII detection using Microsoft Presidio
- FastAPI-based RESTful API
- Input validation and sanitization
- Configurable CORS settings
- Environment-based configuration
- Type-safe with Pydantic models

## Requirements

- Python 3.12
- FastAPI
- Presidio Analyzer
- Spacy language models

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/presidio_fastapi.git
   cd presidio_fastapi
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   # Activate the virtual environment
   # On Windows:
   .venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -e .
   ```

4. **Install Language Models**:
   ```bash
   python -m spacy download en_core_web_lg
   python -m spacy download es_core_news_lg  # Optional for Spanish support
   ```

5. **Set Up Environment Variables**:
   Create a `.env` file in the project root with the following content:
   ```env
   NLP_ENGINE_NAME=spacy
   SPACY_MODEL_EN=en_core_web_lg
   SPACY_MODEL_ES=es_core_news_lg
   API_VERSION=v1
   MAX_TEXT_LENGTH=102400
   MIN_CONFIDENCE_SCORE=0.5
   ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
   REQUESTS_PER_MINUTE=60
   BURST_LIMIT=100
   BLOCK_DURATION=300
   OTLP_ENDPOINT=http://localhost:4317
   OTLP_SECURE=false
   LOG_LEVEL=INFO
   ```

6. **Run the Application**:
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

## Installation

1. Clone the repository
2. Install dependencies and language models:

   Using `pip`:
   ```bash
   # Install package
   pip install -e .

   # Install required language models
   python -m spacy download en_core_web_lg  # Required: English model
   python -m spacy download es_core_news_lg  # Optional: Spanish model
   ```

   Alternatively, using `uv`:
   ```bash
   # Install uv (if you haven't already)
   # pip install uv 
   # or consult https://github.com/astral-sh/uv for other installation methods

   # Create a virtual environment and install dependencies
   uv venv
   uv pip install -e .

   # Install required language models
   python -m spacy download en_core_web_lg  # Required: English model
   python -m spacy download es_core_news_lg  # Optional: Spanish model
   ```

## Environment Variables

Create a `.env` file with the following variables:

```env
# NLP Engine Configuration
NLP_ENGINE_NAME=spacy
SPACY_MODEL_EN=en_core_web_lg
SPACY_MODEL_ES=es_core_news_lg  # Optional: For Spanish language support

# API Configuration
API_VERSION=v1  # API version prefix, e.g., /api/v1/
MAX_TEXT_LENGTH=102400  # Maximum text length for analysis
MIN_CONFIDENCE_SCORE=0.5  # Minimum confidence score for PII detection

# Security Settings
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# Rate Limiting Settings
REQUESTS_PER_MINUTE=60  # Number of requests allowed per IP per minute
BURST_LIMIT=100  # Maximum burst of requests allowed
BLOCK_DURATION=300  # Duration in seconds to block IPs that exceed limits

# OpenTelemetry Configuration
OTLP_ENDPOINT=http://localhost:4317  # OpenTelemetry collector endpoint
OTLP_SECURE=false  # Whether to use TLS for OTLP exporter

# Logging Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, or CRITICAL
```

## Running the Application

1. Ensure you have created a `.env` file as described in the "Environment Variables" section.
2. Start the FastAPI application using Uvicorn:

```bash
# Make sure your virtual environment is activated
# For PowerShell:
# .\.venv\Scripts\Activate.ps1

uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

API documentation will be available at:
- Swagger UI: `http://localhost:8000/api/v1/docs` (or your configured API_VERSION)
- ReDoc: `http://localhost:8000/api/v1/redoc` (or your configured API_VERSION)

## Running Tests

This project uses pytest for testing.

1. Ensure all development dependencies are installed:

   Using `pip`:
   ```bash
   pip install -e ".[dev]"
   ```

   Alternatively, using `uv`:
   ```bash
   # Ensure your virtual environment created with uv is active
   # .venv\Scripts\Activate.ps1 (PowerShell)
   # source .venv/bin/activate (bash/zsh)
   uv pip install -e ".[dev]"
   ```

2. Run the tests using the following command from the project root directory:

```bash
pytest
```

## API Reference

### Text Analysis Endpoints

#### Single Text Analysis

Send a POST request to `/api/v1/analyze` with the following payload:
```json
{
    "text": "My name is John Doe and my email is john@example.com",
    "language": "en"
}
```

Response:
```json
{
    "entities": [
        {
            "entity_type": "PERSON",
            "start": 11,
            "end": 19,
            "score": 0.85,
            "text": "John Doe"
        },
        {
            "entity_type": "EMAIL_ADDRESS",
            "start": 33,
            "end": 48,
            "score": 1.0,
            "text": "john@example.com"
        }
    ]
}
```

#### Batch Text Analysis

Send a POST request to `/api/v1/analyze/batch` with the following payload:
```json
{
    "texts": [
        {"text": "My name is Jane Doe and my email is jane@example.com"},
        {"text": "His phone number is 555-1234."}
    ],
    "language": "en"
}
```

Response:
```json
{
    "results": [
        {
            "entities": [
                {
                    "entity_type": "PERSON",
                    "start": 11,
                    "end": 19,
                    "score": 0.85,
                    "text": "Jane Doe"
                },
                {
                    "entity_type": "EMAIL_ADDRESS",
                    "start": 33,
                    "end": 48,
                    "score": 1.0,
                    "text": "jane@example.com"
                }
            ]
        },
        {
            "entities": [
                {
                    "entity_type": "PHONE_NUMBER",
                    "start": 19,
                    "end": 27,
                    "score": 0.9,
                    "text": "555-1234"
                }
            ]
        }
    ]
}
```

### API Versioning

All API endpoints are versioned and available under `/api/v1/`. The version can be configured using the `API_VERSION` environment variable.

Example versioned endpoints:
- `/api/v1/analyze`
- `/api/v1/analyze/batch`
- `/api/v1/docs`
- `/api/v1/redoc`

## Development

To run the development server:

```bash
uvicorn main:app --reload
```

API documentation will be available at:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI Schema: http://localhost:8000/api/v1/openapi.json

## Security Considerations

- CORS is configured to accept only specified origins
- Input validation is enforced through Pydantic models
- Text length is limited to prevent DoS attacks
- Detailed error messages are sanitized in production
- Rate limiting prevents abuse (60 requests/minute per IP)
- Security headers are automatically added to all responses:
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Strict-Transport-Security
  - Content-Security-Policy

### Rate Limiting

The API implements rate limiting with the following default settings:
- 60 requests per minute per IP
- Burst limit of 100 requests
- 5-minute blocking period for burst limit violations

Rate limit headers in responses:
- `X-RateLimit-Limit`: Requests allowed per minute
- `X-RateLimit-Remaining`: Remaining requests in the current window
- `X-RateLimit-Reset`: Seconds until the current window resets

### Security Features

1. Request Rate Limiting
   - Per-IP rate limiting
   - Burst protection
   - Automatic blocking for abuse

2. Security Headers
   - Content Security Policy (CSP)
   - HSTS (HTTP Strict Transport Security)
   - XSS Protection
   - Frame Options
   - Content Type Options
   - Referrer Policy
   - Permissions Policy

3. Input Validation
   - Maximum text length limits
   - Language code validation
   - JSON payload validation

## Monitoring

The service includes built-in monitoring endpoints:

### Health Check
```bash
GET /api/v1/health
```

### Metrics
```bash
GET /api/v1/metrics

Response:
{
    "total_requests": 1234,
    "requests_by_path": {
        "/": 100,
        "/analyze": 1000,
        "/analyze/batch": 100,
        "/health": 34
    },
    "average_response_time": 0.123,
    "requests_in_last_minute": 45,
    "error_rate": 0.001,
    "error_counts": {
        "400": 10,
        "429": 5,
        "500": 1
    },
    "suspicious_requests": {
        "192.168.1.1": 2
    }
}
```

### Distributed Tracing

The service is instrumented with OpenTelemetry for distributed tracing. Traces are exported to an OTLP collector.

Configuration via environment variables:
```env
OTLP_ENDPOINT=http://localhost:4317
OTLP_SECURE=false
```

Each API endpoint and analyzer operation is traced, providing:
- Request/response timing
- Error tracking
- Function parameters
- Cross-service dependencies

To view traces:
1. Start an OpenTelemetry collector
2. Configure the OTLP endpoint
3. Use a tracing UI like Jaeger or Zipkin

Trace data includes:
- HTTP request details
- PII analysis operations
- Error details
- Custom attributes

## License

See the [LICENSE](LICENSE) file for details.
