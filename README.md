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

# Install required language model
python -m spacy download en_core_web_lg

# Create basic .env file
echo "NLP_ENGINE_NAME=spacy
SPACY_MODEL_EN=en_core_web_lg
API_VERSION=v1" > .env

# Run the service
presidio-fastapi
```

The API will be available at `http://localhost:8000/api/v1/`.
Documentation at `http://localhost:8000/api/v1/docs`.

## Installation

### Prerequisites

- Python 3.12
- SpaCy language models

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

## Project Structure

```
presidio_fastapi/
├── app/                  # Main application package 
│   ├── api/              # API routes and endpoints
│   ├── models/           # Pydantic data models
│   ├── services/         # Business logic and services
│   ├── config.py         # Application configuration
│   ├── main.py           # FastAPI application factory
│   ├── middleware.py     # Custom middleware components
│   └── telemetry.py      # OpenTelemetry instrumentation
├── __init__.py           # Package initialization
├── run.py                # Application entry point
└── stubs.py              # Type stubs for improved IDE support
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
- Security headers (CSP, HSTS, XSS Protection)
- Request/response metrics and monitoring

## Monitoring

### Health Check & Metrics

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Service metrics
curl http://localhost:8000/api/v1/metrics
```

### Distributed Tracing

The service supports OpenTelemetry tracing. Configure with:

```env
OTLP_ENDPOINT=http://localhost:4317
OTLP_SECURE=false
```

## License

See the [LICENSE](LICENSE) file for details.
