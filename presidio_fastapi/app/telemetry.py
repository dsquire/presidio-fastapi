"""OpenTelemetry configuration and utilities."""

import logging
import socket
import uuid
from collections.abc import Awaitable, Callable
from functools import lru_cache, wraps
from typing import Any, ParamSpec, TypeVar

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

P = ParamSpec("P")
R = TypeVar("R")


def _enrich_span_with_request_details(span: trace.Span, scope: dict[str, Any]) -> None:
    """Add custom attributes to request spans.

    Args:
        span: The span to enrich with attributes.
        scope: The ASGI scope dictionary containing request details.
    """
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
    """Check if the OpenTelemetry collector is available.

    Args:
        host: The hostname or IP address of the collector.
        port: The port number of the collector.
        timeout: Socket connection timeout in seconds.

    Returns:
        True if the collector is available, False otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except (socket.timeout, socket.error, OSError):
        return False


@lru_cache()
def setup_telemetry(app: FastAPI) -> None:
    """Set up OpenTelemetry tracing for the FastAPI application.

    Configures OpenTelemetry tracer provider, sampling, and instrumentation.
    Uses standard OTEL_* environment variables for configuration.

    Args:
        app: The FastAPI application instance to instrument.
    """
    # Early return if telemetry is disabled
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry instrumentation is disabled")
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
        sampler = ParentBased(root=TraceIdRatioBased(settings.OTEL_TRACES_SAMPLER_ARG))

        # Create and configure tracer provider
        tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )
        trace.set_tracer_provider(tracer_provider)

        # Configure OTLP exporter using standard environment variables with proper error handling
        # Only attempt to set up the exporter if explicitly enabled with a valid endpoint
        has_endpoint = (
            settings.OTEL_EXPORTER_OTLP_ENDPOINT
            and settings.OTEL_EXPORTER_OTLP_ENDPOINT.strip()
        )
        
        if has_endpoint:
            try:
                endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
                endpoint_parts = endpoint.replace("http://", "").replace("https://", "").split(":")
                collector_host = endpoint_parts[0]
                collector_port = int(endpoint_parts[1]) if len(endpoint_parts) > 1 else 4317
                
                # Check if collector is available before attempting to connect
                collector_available = _is_collector_available(collector_host, collector_port)
                
                if collector_available:
                    logger.info(f"OTLP collector is available at {collector_host}:{collector_port}")
                    logger.info(f"Configuring OTLP exporter with endpoint: {endpoint}")
                    
                    # Create OTLP exporter with fast timeout to fail quickly if collector is down
                    otlp_exporter = OTLPSpanExporter(
                        endpoint=endpoint,
                        insecure=not settings.OTLP_SECURE,  # Use the legacy setting
                        timeout=3,  # 3 seconds timeout
                    )
                    
                    # Use a more conservative batch processor configuration
                    span_processor = BatchSpanProcessor(
                        otlp_exporter,
                        # Smaller batch size and queue for better reliability
                        max_export_batch_size=512,
                        schedule_delay_millis=5000,
                        max_queue_size=2048,
                    )
                    
                    tracer_provider.add_span_processor(span_processor)
                else:
                    logger.warning(
                        f"OTLP collector not available at {collector_host}:{collector_port}. "
                        "Using console exporter instead."
                    )
                    # Fallback to console exporter for development/debugging
                    console_exporter = ConsoleSpanExporter()
                    console_processor = BatchSpanProcessor(console_exporter)
                    tracer_provider.add_span_processor(console_processor)
            except Exception as e:
                logger.warning(f"Failed to configure OTLP exporter: {e!s}. Using console exporter.")
                # Always provide a fallback
                console_exporter = ConsoleSpanExporter()
                console_processor = BatchSpanProcessor(console_exporter)
                tracer_provider.add_span_processor(console_processor)
        else:
            # If no endpoint is specified, use console exporter
            logger.info("OTLP endpoint not configured. Using console exporter.")
            console_exporter = ConsoleSpanExporter()
            console_processor = BatchSpanProcessor(console_exporter)
            tracer_provider.add_span_processor(console_processor)
            
        # Instrument FastAPI with request hooks
        logger.info("Instrumenting FastAPI application with OpenTelemetry")
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls=settings.OTEL_PYTHON_FASTAPI_EXCLUDED_URLS,
            server_request_hook=_enrich_span_with_request_details,
        )
        logger.info("OpenTelemetry instrumentation configured successfully")

    except Exception as e:
        logger.error("Failed to configure OpenTelemetry: %s", str(e))
        logger.exception(e)


def trace_method(
    name: str | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator to add OpenTelemetry tracing to an async method.

    Only creates spans if OpenTelemetry is enabled.

    Args:
        name: Optional name for the span. If not provided, the function name is used.

    Returns:
        A decorator function that adds tracing to the decorated async method.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
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
                            # Only include minimal info to avoid logging sensitive data
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
