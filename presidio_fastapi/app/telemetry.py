"""OpenTelemetry configuration and utilities."""

import logging
import socket
import uuid
from functools import wraps
from typing import Any, Optional

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace.status import Status, StatusCode

from presidio_fastapi.app.config import settings

# Configure logging with a NullHandler to avoid "No handlers" warnings
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Global tracking for telemetry resources
_tracer_provider: Optional[TracerProvider] = None
_span_processors = []
_is_setup_complete = False


def _enrich_span_with_request_details(span: trace.Span, scope: dict[str, Any]) -> None:
    """Add custom attributes to request spans."""
    if not span or not span.is_recording():
        return

    # Add request ID for correlation
    span.set_attribute("app.request_id", str(uuid.uuid4()))

    # Add PII detection context if available
    analyzer_entities = scope.get("analyzer_entities")
    if analyzer_entities is not None:
        span.set_attribute("app.presidio.entities", str(analyzer_entities))

    language = scope.get("language")
    if language is not None:
        span.set_attribute("app.presidio.language", str(language))


def _is_collector_available(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if the OpenTelemetry collector is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except (socket.timeout, socket.error, OSError):
        return False


def test_function():
    """Simple test function to verify module is working."""
    return "Module is working"


def shutdown_telemetry():
    """Properly shutdown OpenTelemetry components to prevent resource leaks."""
    global _tracer_provider, _span_processors, _is_setup_complete
    
    if not _is_setup_complete:
        return
        
    logger.info("Shutting down OpenTelemetry components...")
    
    # Shutdown all span processors
    for processor in _span_processors:
        try:
            processor.shutdown()
            logger.debug("Span processor shutdown completed")
        except Exception as e:
            logger.warning(f"Error shutting down span processor: {e}")
    
    # Clear global state
    _span_processors.clear()
    _tracer_provider = None
    _is_setup_complete = False
    
    logger.info("OpenTelemetry shutdown completed")


def setup_telemetry(app: FastAPI):
    """Set up OpenTelemetry tracing for the FastAPI application."""
    global _tracer_provider, _span_processors, _is_setup_complete
    
    # Early return if telemetry is disabled
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry instrumentation is disabled")
        return

    # Prevent multiple setups
    if _is_setup_complete:
        logger.debug("OpenTelemetry already configured, skipping setup")
        return
        
    # Check if a tracer provider is already set (avoid override warnings)
    existing_provider = trace.get_tracer_provider()
    if hasattr(existing_provider, 'add_span_processor'):
        logger.warning(
            "TracerProvider already exists, skipping telemetry setup to avoid conflicts"
        )
        return

    try:
        # Create resource with service information
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: settings.OTEL_SERVICE_NAME,
                ResourceAttributes.SERVICE_VERSION: settings.API_VERSION,
            }
        )

        # Configure sampling strategy
        sampler = ParentBased(
            root=TraceIdRatioBased(settings.OTEL_TRACES_SAMPLER_ARG)
        )

        # Create and configure tracer provider
        _tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )
        trace.set_tracer_provider(_tracer_provider)

        # Configure OTLP exporter with proper error handling
        has_endpoint = (
            settings.OTEL_EXPORTER_OTLP_ENDPOINT
            and settings.OTEL_EXPORTER_OTLP_ENDPOINT.strip()
        )
        
        if has_endpoint:
            try:
                endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
                endpoint_parts = (
                    endpoint.replace("http://", "").replace("https://", "").split(":")
                )
                collector_host = endpoint_parts[0]
                collector_port = (
                    int(endpoint_parts[1]) if len(endpoint_parts) > 1 else 4317
                )
                
                # Check if collector is available before attempting to connect
                collector_available = _is_collector_available(collector_host, collector_port)
                
                if collector_available:
                    logger.info(
                        f"OTLP collector is available at {collector_host}:{collector_port}"
                    )
                    
                    # Create OTLP exporter with fast timeout
                    otlp_exporter = OTLPSpanExporter(
                        endpoint=endpoint,
                        insecure=not settings.OTLP_SECURE,
                        timeout=3,
                    )
                    
                    span_processor = BatchSpanProcessor(
                        otlp_exporter,
                        max_export_batch_size=512,
                        schedule_delay_millis=5000,
                        max_queue_size=2048,
                    )
                    
                    _tracer_provider.add_span_processor(span_processor)
                    _span_processors.append(span_processor)
                else:
                    logger.warning(
                        f"OTLP collector not available at {collector_host}:{collector_port}. "
                        "Using console exporter."
                    )
                    console_exporter = ConsoleSpanExporter()
                    console_processor = BatchSpanProcessor(console_exporter)
                    _tracer_provider.add_span_processor(console_processor)
                    _span_processors.append(console_processor)
            except Exception as e:
                logger.warning(
                    f"Failed to configure OTLP exporter: {e!s}. Using console exporter."
                )
                console_exporter = ConsoleSpanExporter()
                console_processor = BatchSpanProcessor(console_exporter)
                _tracer_provider.add_span_processor(console_processor)
                _span_processors.append(console_processor)
        else:
            # If no endpoint is specified, use console exporter
            logger.info("OTLP endpoint not configured. Using console exporter.")
            console_exporter = ConsoleSpanExporter()
            console_processor = BatchSpanProcessor(console_exporter)
            _tracer_provider.add_span_processor(console_processor)
            _span_processors.append(console_processor)
            
        # Instrument FastAPI with request hooks
        logger.info("Instrumenting FastAPI application with OpenTelemetry")
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls=settings.OTEL_PYTHON_FASTAPI_EXCLUDED_URLS,
            server_request_hook=_enrich_span_with_request_details,
        )
        
        # Mark setup as complete
        _is_setup_complete = True
        logger.info("OpenTelemetry instrumentation configured successfully")

    except Exception as e:
        logger.error("Failed to configure OpenTelemetry: %s", str(e))
        logger.exception(e)


def trace_method(name=None):
    """Decorator to add OpenTelemetry tracing to an async method."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not settings.OTEL_ENABLED:
                return await func(*args, **kwargs)

            tracer = trace.get_tracer(__name__)
            span_name = name or func.__name__

            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add function context to span
                    span.set_attributes(
                        {
                            "function.name": func.__name__,
                            "function.args_count": len(args),
                            "function.kwargs_keys": str(list(kwargs.keys())),
                        }
                    )

                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator
