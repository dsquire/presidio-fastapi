# Presidio FastAPI Service

A secure and efficient FastAPI service for detecting Personally Identifiable Information (PII) in text using Microsoft's Presidio Analyzer.

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

## API Usage

### Analyze Text

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
        "/health": 134
    },
    "average_response_time": 0.123,
    "requests_in_last_minute": 45
}

## License

See the [LICENSE](LICENSE) file for details.