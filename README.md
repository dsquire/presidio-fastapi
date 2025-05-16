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

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -e .
python -m spacy download en_core_web_lg
```

## Environment Variables

Create a `.env` file with the following variables:

```env
NLP_ENGINE_NAME=spacy
SPACY_MODEL_EN=en_core_web_lg
MAX_TEXT_LENGTH=102400
ALLOWED_ORIGINS=http://localhost:3000
MIN_CONFIDENCE_SCORE=0.5
```

## API Reference

### Text Analysis Endpoints

#### Single Text Analysis

```bash
POST /analyze

Request:
{
    "text": "My name is John Doe and my email is john@example.com",
    "language": "en"
}

Response:
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

```bash
POST /analyze/batch

Request:
{
    "texts": [
        "My name is John Doe",
        "Contact me at john@example.com"
    ],
    "language": "en"
}

Response:
{
    "results": [
        {
            "entities": [
                {
                    "entity_type": "PERSON",
                    "start": 11,
                    "end": 19,
                    "score": 0.85,
                    "text": "John Doe"
                }
            ]
        },
        {
            "entities": [
                {
                    "entity_type": "EMAIL_ADDRESS",
                    "start": 13,
                    "end": 28,
                    "score": 1.0,
                    "text": "john@example.com"
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
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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
GET /health
```

### Metrics
```bash
GET /metrics

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