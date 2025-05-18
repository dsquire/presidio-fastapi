"""Application configuration management."""

import logging
from functools import lru_cache
from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings managed via Pydantic BaseSettings.

    Attributes:
        API_VERSION: The version of the API.
        OTEL_ENABLED: Whether OpenTelemetry instrumentation is enabled.
        OTEL_SERVICE_NAME: The service name for OpenTelemetry.
        OTEL_EXPORTER_OTLP_ENDPOINT: The OTLP endpoint for OpenTelemetry.
        OTEL_EXPORTER_OTLP_PROTOCOL: The protocol for OTLP export (grpc/http).
        OTEL_TRACES_SAMPLER: The sampling strategy for traces.
        OTEL_TRACES_SAMPLER_ARG: The sampling rate for traces.
        OTEL_PYTHON_FASTAPI_EXCLUDED_URLS: URLs to exclude from tracing.
        OTLP_ENDPOINT: Legacy - The OTLP endpoint for OpenTelemetry.
        OTLP_SECURE: Legacy - Whether to use a secure connection for OTLP.
        REQUESTS_PER_MINUTE: Allowed requests per minute for rate limiting.
        BURST_LIMIT: Burst limit for rate limiting.
        BLOCK_DURATION: Duration in seconds to block IPs exceeding limits.
        LOG_LEVEL: The logging level for the application.
        SERVER_HOST: The host address for the server.
        SERVER_PORT: The port number for the server.
        NLP_ENGINE_NAME: The name of the NLP engine (e.g., "spacy").
        SPACY_MODEL_EN: The Spacy model for English.
        SPACY_MODEL_ES: The optional Spacy model for Spanish.
        MAX_TEXT_LENGTH: Maximum allowed text length for analysis.
        ALLOWED_ORIGINS: Comma-separated string of allowed CORS origins.
        MIN_CONFIDENCE_SCORE: Minimum confidence score for PII detection.
        ENTITY_MAPPING: Mapping of Presidio entities.
        CONTEXT_SIMILARITY_THRESHOLD: Similarity threshold for context-aware enhancer.
        CONTEXT_MAX_DISTANCE: Maximum word distance for context search.
    """

    # API Version
    API_VERSION: str = "v1"

    # OpenTelemetry Configuration
    OTEL_ENABLED: bool = True
    OTEL_SERVICE_NAME: str = "presidio-fastapi"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_EXPORTER_OTLP_PROTOCOL: str = "grpc"
    OTEL_TRACES_SAMPLER: str = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = 1.0
    OTEL_PYTHON_FASTAPI_EXCLUDED_URLS: str = "health,metrics"

    # Legacy OpenTelemetry settings (kept for backward compatibility)
    OTLP_ENDPOINT: str = "http://localhost:4317"
    OTLP_SECURE: bool = False

    # Rate Limiting Settings
    REQUESTS_PER_MINUTE: int = 60
    BURST_LIMIT: int = 100
    BLOCK_DURATION: int = 300

    # Logging Configuration
    LOG_LEVEL: str = "INFO"

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # NLP Configuration
    NLP_ENGINE_NAME: str = "spacy"
    SPACY_MODEL_EN: str = "en_core_web_lg"
    SPACY_MODEL_ES: str | None = None  # Optional Spanish language model
    MAX_TEXT_LENGTH: int = 102400
    ALLOWED_ORIGINS: str = ""
    MIN_CONFIDENCE_SCORE: float = 0.5
    CONTEXT_SIMILARITY_THRESHOLD: float = 0.65
    CONTEXT_MAX_DISTANCE: int = 10

    # Entity Mapping Configuration
    ENTITY_MAPPING: dict[str, list[str]] = {
        "PERSON": ["PERSON", "PER"],
        "EMAIL_ADDRESS": ["EMAIL"],
        "PHONE_NUMBER": ["PHONE", "PHONE_NUMBER"],
        "CREDIT_CARD": ["CREDIT_CARD", "CC"],
        "DATE_TIME": ["DATE", "TIME", "DATETIME"],
        "ADDRESS": ["LOC", "GPE", "LOCATION"],
        "US_SSN": ["SSN"],
        "IP_ADDRESS": ["IP"],
        "US_DRIVER_LICENSE": ["DRIVER_LICENSE", "DL"],
        "URL": ["URL", "URI"],
    }

    @model_validator(mode="before")
    @classmethod
    def _strip_inline_comments(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cleaned_data = {}
            for key, value in data.items():
                if isinstance(value, str):
                    cleaned_data[key] = value.split("#")[0].strip()
                else:
                    cleaned_data[key] = value
            return cleaned_data
        return data

    @property
    def cors_origins(self) -> list[str]:
        """Get the list of allowed CORS origins.

        Returns:
            A list of allowed CORS origins split from the ALLOWED_ORIGINS setting.
            If no origins are configured, returns an empty list.
        """
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def nlp_configuration(self) -> dict[str, Any]:
        """Construct the NLP configuration for Presidio Analyzer.

        This configuration includes the NLP engine name and a list of models
        with their language codes, model names, and entity mappings.
        The Spanish model is included only if SPACY_MODEL_ES is configured
        with a valid model name.

        Returns:
            A dictionary containing the NLP configuration suitable for
            NlpEngineProvider with the following structure:
            {
                "nlp_engine_name": str,
                "models": [
                    {
                        "lang_code": str,
                        "model_name": str,
                    },
                    # ... more models
                ],
            }
        """
        models = [
            {"lang_code": "en", "model_name": self.SPACY_MODEL_EN.split("#")[0].strip()}
        ]
        if self.SPACY_MODEL_ES:
            # Strip comments from the Spanish model name
            spanish_model_name = self.SPACY_MODEL_ES.split("#")[0].strip()
            if spanish_model_name:  # Ensure it's not an empty string after stripping
                models.append({"lang_code": "es", "model_name": spanish_model_name})

        return {
            "nlp_engine_name": self.NLP_ENGINE_NAME,
            "models": models,
        }

    @property
    def log_level(self) -> int:
        """Convert the string log level from settings to a logging constant.

        Returns:
            The integer value of the logging level (e.g., logging.INFO,
            logging.DEBUG). Defaults to logging.INFO if the configured
            LOG_LEVEL is invalid.
        """
        return getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)

    class Config:
        """Pydantic configuration class for Settings.

        Attributes:
            env_file (str): The name of the environment file to load (e.g., ".env").
            case_sensitive (bool): Whether environment variable names are case-sensitive.
        """

        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Create and cache a Settings instance.

    Uses lru_cache to ensure that the Settings object is created only once,
    improving performance by avoiding repeated file reads and environment
    variable lookups.

    Returns:
        A cached instance of the Settings class.
    """
    return Settings()


settings = get_settings()
