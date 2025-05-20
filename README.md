# Presidio FastAPI Service

A secure, high-performance FastAPI service for detecting Personally Identifiable Information (PII) in text using Microsoft's Presidio Analyzer.

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)

## Features

- PII detection using Microsoft Presidio
- FastAPI-based RESTful API with automatic documentation
- Input validation and sanitization via Pydantic
- Robust rate limiting and security headers
- OpenTelemetry instrumentation for monitoring
- Type-safe with comprehensive type hints

## Quick Start

```bash
# Install package
pip install -e .

# Install required dependencies
python -m spacy download en_core_web_lg
pip install prometheus-client>=0.17.1

# Create basic .env file
echo "NLP_ENGINE_NAME=spacy
SPACY_MODEL_EN=en_core_web_lg
API_VERSION=v1
OTEL_ENABLED=false
PROMETHEUS_MONITORED_PATHS=analyze,analyze/batch" > .env

# Run the service
presidio-fastapi
```

The API will be available at `http://localhost:8000/api/v1/`.
Documentation at `http://localhost:8000/api/v1/docs`.

## Installation

### Prerequisites

- Python 3.12
- SpaCy language models
- Prometheus client library

### Setup Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/presidio_fastapi.git
   cd presidio_fastapi
   ```

2. **Create a Virtual Environment**:
   ```bash
   # Using venv
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # Windows PowerShell
   # OR source .venv/bin/activate  # macOS/Linux
   
   # OR using uv (faster)
   uv venv
   .venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

3. **Install Dependencies**:
   ```bash
   pip install -e .
   
   # For development
   pip install -e ".[dev]"
   ```

4. **Install Language Models**:
   ```bash
   python -m spacy download en_core_web_lg  # Required: English model
   python -m spacy download es_core_news_lg  # Optional: Spanish model
   ```

5. **Set Up Environment Variables**:
   Create a `.env` file with the settings from the "Configuration" section below.

6. **Run the Application**:
   ```bash
   # As installed package (recommended)
   presidio-fastapi
   
   # OR with uvicorn directly
   uvicorn presidio_fastapi.app.main:app --reload
   
   # OR using the run module
   python -m presidio_fastapi.run
   ```

## Configuration

### Essential Environment Variables

```env
# NLP Engine Configuration
NLP_ENGINE_NAME=spacy
SPACY_MODEL_EN=en_core_web_lg
SPACY_MODEL_ES=es_core_news_lg  # Optional: For Spanish language support

# API Configuration
API_VERSION=v1
MAX_TEXT_LENGTH=102400
MIN_CONFIDENCE_SCORE=0.5

# Security Settings
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
REQUESTS_PER_MINUTE=60
BURST_LIMIT=100

# Prometheus Configuration
PROMETHEUS_MONITORED_PATHS=analyze,analyze/batch  # Comma-separated path suffixes to monitor

# Logging Configuration
LOG_LEVEL=INFO
```

### PII Detection Tuning

Fine-tune context-aware PII detection with:

* `CONTEXT_SIMILARITY_THRESHOLD` (default: 0.65)
  * Higher (0.8-0.9): More precision, fewer false positives
  * Lower (0.4-0.6): Better recall, catches more variations
  
* `CONTEXT_MAX_DISTANCE` (default: 10)
  * Higher (15-20): Looks further for context, better for complex text
  * Lower (5-8): Faster processing, best for simple text

## Custom Recognizers

You can configure custom recognizers using YAML configuration without writing any code. The configuration file is located at `config/recognizers.yaml`.

### Example Configuration

```yaml
# Recognizer Registry configuration
recognizer_registry:
  supported_languages:
    - en
    - es
  recognizers:
    # Custom regex-based recognizer
    - name: "employee_id"
      supported_entity: "EMPLOYEE_ID"
      type: regex
      patterns:
        - name: "standard_employee_id"
          regex: "EMP\\d{6}"  # Matches EMP followed by 6 digits
          score: 0.85
      context:
        - "employee"
        - "id"
        - "number"
      supported_language: "en"

    # Deny list based recognizer
    - name: "project_code"
      supported_entity: "PROJECT_CODE"
      type: regex
      patterns:
        - name: "internal_project"
          regex: "PRJ-[A-Z]{2}-\\d{4}"  # Matches PRJ-XX-1234 format
          score: 0.9
      context:
        - "project"
        - "code"
        - "reference"
      supported_language: "en"
```

### Configuration Options

Each recognizer can have the following options:

- `name`: Unique identifier for the recognizer
- `supported_entity`: The type of entity this recognizer detects
- `type`: Type of recognizer (`regex`, `pattern`, `deny_list`, or `predefined`)
- `patterns`: List of regex patterns with names and confidence scores
- `context`: List of context words that improve detection accuracy
- `supported_language`: Language code this recognizer supports

### Context Settings

Global context awareness settings can be configured:

```yaml
defaults:
  allow_overlap: false
  context:
    similarity_threshold: 0.65  # How similar context words need to be
    max_distance: 10           # Maximum word distance for context
```

### Adding New Recognizers

1. Edit `config/recognizers.yaml`
2. Add your recognizer configuration under the `recognizers` section
3. Restart the service to apply changes

### Testing Recognizers

You can test your custom recognizers using the API:

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
     -H "Content-Type: application/json" \
     -d '{"text": "Employee EMP123456 is working on project PRJ-AB-1234"}'
```

For more examples and configuration options, see the [Presidio documentation](https://microsoft.github.io/presidio/).

## Project Structure

```
presidio_fastapi/
├── app/                  # Main application package 
│   ├── api/              # API routes and endpoints
│   ├── models/           # Pydantic data models
│   ├── services/         # Business logic and services
│   ├── config.py         # Application configuration
│   ├── main.py           # FastAPI application factory
│   ├── middleware.py     # Security, rate limiting, and metrics middleware  
│   ├── prometheus.py     # Prometheus metrics integration
│   └── telemetry.py      # Fault-tolerant OpenTelemetry instrumentation
├── __init__.py           # Package initialization
└── run.py                # Application entry point
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=presidio_fastapi

# Run linting
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Run type checking
mypy .
```

### Usage Examples

#### Single Text Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{"text": "My name is John Doe and my email is john@example.com", "language": "en"}'
```

#### Batch Text Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analyze/batch" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["My name is Jane Smith.", "Contact: jane@example.com"], "language": "en"}'
```

## Security Features

- CORS with configurable origins
- Input validation and sanitization
- Rate limiting (default: 60 requests/minute per IP)
- IP blocking for abusive clients (burst protection)
- Security headers (CSP, HSTS, XSS Protection, Content-Type Options)
- Comprehensive Prometheus metrics for monitoring
- Selective endpoint monitoring for optimized performance
- Suspicious request detection and tracking

## Monitoring

### Health Check & Metrics

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get metrics in Prometheus format (standard endpoint for Prometheus scraping)
curl http://localhost:8000/api/v1/metrics

# Get metrics in JSON format (legacy, deprecated)
curl http://localhost:8000/api/v1/metrics-json
```

#### Metrics Format

The service exposes metrics in two formats:

1. **Prometheus Text Format** (default endpoint: `/api/v1/metrics`):
   - Standard endpoint for Prometheus scraping
   - Returns metrics in Prometheus' text-based exposition format
   - Use this endpoint when configuring Prometheus scraping

2. **JSON Format** (legacy endpoint: `/api/v1/metrics-json`):
   - Maintained for backward compatibility
   - Provides a more human-readable format
   - Will be deprecated in future versions

The following metrics are available through both endpoints:

- `http_requests_total`: Total number of HTTP requests (labeled by method, endpoint, status_code)
- `http_request_duration_seconds`: Duration of HTTP requests in seconds (labeled by method, endpoint)
- `http_errors_total`: Total count of HTTP errors (labeled by method, endpoint, status_code)
- `http_active_requests`: Number of currently active HTTP requests (labeled by method, endpoint)
- `presidio_pii_entities_detected_total`: Total number of PII entities detected (labeled by entity_type, language)

By default, metrics are only collected for specific endpoints (`/analyze` and `/analyze/batch`). This can be configured using the `PROMETHEUS_MONITORED_PATHS` environment variable:

```env
# Monitor only the analyze endpoint
PROMETHEUS_MONITORED_PATHS=analyze

# Monitor multiple endpoints (comma-separated)
PROMETHEUS_MONITORED_PATHS=analyze,analyze/batch,health,status
```

#### Legacy JSON Metrics (Deprecated)

The legacy JSON metrics endpoint is maintained for backward compatibility but is deprecated. It provides the following information:

- `total_requests`: Total number of requests processed
- `requests_by_path`: Count of requests per API endpoint path
- `average_response_time`: Average response time in seconds
- `requests_in_last_minute`: Number of requests in the last minute
- `error_rate`: Proportion of requests that resulted in errors
- `error_counts`: Count of errors by HTTP status code
- `suspicious_requests`: Count of potentially suspicious requests

Example legacy metrics response:
```json
{
  "total_requests": 42,
  "requests_by_path": {
    "/api/v1/analyze": 24,
    "/api/v1/health": 10,
    "/api/v1/metrics": 8
  },
  "average_response_time": 0.125,
  "requests_in_last_minute": 5,
  "error_rate": 0.02,
  "error_counts": {
    "404": 1
  },
  "suspicious_requests": {}
}
```

### Distributed Tracing

The service supports OpenTelemetry tracing which can be enabled/disabled and configured via environment variables:

```env
# OpenTelemetry Toggle
OTEL_ENABLED=true  # Set to false to completely disable OpenTelemetry

# Service Information
OTEL_SERVICE_NAME=presidio-fastapi  # Name of the service
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # OTLP endpoint URL
OTEL_EXPORTER_OTLP_PROTOCOL=grpc  # Protocol (grpc/http)

# Sampling Configuration
OTEL_TRACES_SAMPLER=parentbased_traceidratio  # Sampling strategy
OTEL_TRACES_SAMPLER_ARG=1.0  # Sampling rate (0.0 to 1.0)

# Optional: URLs to exclude from tracing
OTEL_PYTHON_FASTAPI_EXCLUDED_URLS=health,metrics

# Legacy Configuration (for backward compatibility)
OTLP_SECURE=false  # Whether to use secure connection for OTLP

# Optional: Authentication for secure endpoints
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <token>"
```

The telemetry implementation includes the following features:
- Automatically checks if the OTLP collector is available before attempting to connect
- Falls back to console exporter when the collector is unavailable
- Thread-safe operation with proper error handling
- Graceful degradation when telemetry services are unavailable
- Custom attributes for detailed PII detection tracing

When enabled, the service will automatically:
- Track all incoming HTTP requests
- Add trace context to PII detection operations
- Track function execution times and errors
- Add relevant PII detection attributes to spans

To disable OpenTelemetry in development or testing environments, set `OTEL_ENABLED=false`.

## License

See the [LICENSE](LICENSE) file for details.
