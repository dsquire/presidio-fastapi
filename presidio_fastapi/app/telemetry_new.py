"""OpenTelemetry configuration and utilities."""

import logging
import socket
import uuid
from collections.abc import Awaitable, Callable
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
    """Check if an OpenTelemetry collector is available at the specified host and port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.error, socket.timeout):
        return False


def shutdown_telemetry() -> None:
    """Shutdown telemetry components and clean up resources.
    
    This function ensures proper cleanup of all OpenTelemetry resources
    to prevent I/O errors and resource leaks during application shutdown.
    """
    global _tracer_provider, _span_processors, _is_setup_complete
    
    logger.info("Shutting down telemetry...")
    
    try:
        # Shutdown all span processors first
        for processor in _span_processors:
            try:
                if hasattr(processor, 'shutdown'):
                    processor.shutdown()
                    logger.debug(f"Shutdown span processor: {type(processor).__name__}")
            except Exception as e:
                logger.warning(f"Error shutting down span processor: {e}")
        
        # Shutdown the tracer provider
        if _tracer_provider is not None:
            try:
                if hasattr(_tracer_provider, 'shutdown'):
                    _tracer_provider.shutdown()
                    logger.debug("Shutdown tracer provider")
            except Exception as e:
                logger.warning(f"Error shutting down tracer provider: {e}")
        
        # Clear global state
        _tracer_provider = None
        _span_processors.clear()
        _is_setup_complete = False
        
        logger.info("Telemetry shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during telemetry shutdown: {e}")


def setup_telemetry(app: FastAPI) -> None:
    """Set up OpenTelemetry tracing for the FastAPI application.
    
    Args:
        app: The FastAPI application instance to instrument.
    """
    global _tracer_provider, _span_processors, _is_setup_complete
    
    # Check if telemetry is disabled
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry is disabled via configuration")
        return
    
    # Prevent multiple setup attempts
    if _is_setup_complete:
        logger.warning("Telemetry setup already completed, skipping")
        return
    
    # Check if a TracerProvider is already set globally
    current_provider = trace.get_tracer_provider()
    if hasattr(current_provider, '_resource') and current_provider != trace.NoOpTracerProvider():
        logger.warning("TracerProvider already exists, skipping setup to avoid override warnings")
        return
    
    try:
        logger.info("Setting up OpenTelemetry tracing...")
        
        # Create resource with service information
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: settings.SERVICE_NAME,
            ResourceAttributes.SERVICE_VERSION: settings.SERVICE_VERSION,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.ENVIRONMENT,
        })
        
        # Create tracer provider with sampling
        _tracer_provider = TracerProvider(
            resource=resource,
            sampler=ParentBased(root=TraceIdRatioBased(settings.OTEL_TRACES_SAMPLE_RATE))
        )
        
        # Configure span processor and exporter
        span_processor = None
        
        # Try OTLP exporter first if endpoint is configured
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            try:
                # Parse host and port from endpoint for availability check
                endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')
                if '://' in endpoint:
                    endpoint = endpoint.split('://', 1)[1]
                if ':' in endpoint:
                    host, port_str = endpoint.rsplit(':', 1)
                    port = int(port_str)
                else:
                    host, port = endpoint, 4317  # Default OTLP gRPC port
                
                # Check if collector is available
                if _is_collector_available(host, port):
                    otlp_exporter = OTLPSpanExporter(
                        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                        headers=settings.OTEL_EXPORTER_OTLP_HEADERS,
                    )
                    span_processor = BatchSpanProcessor(otlp_exporter)
                    logger.info(f"Using OTLP exporter: {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
                else:
                    logger.warning(f"OTLP collector not available at {host}:{port}, falling back to console exporter")
            except Exception as e:
                logger.warning(f"Failed to setup OTLP exporter: {e}, falling back to console exporter")
        
        # Fall back to console exporter if OTLP is not available
        if span_processor is None:
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            logger.info("Using console exporter for tracing")
        
        # Add span processor and set as global provider
        _tracer_provider.add_span_processor(span_processor)
        _span_processors.append(span_processor)
        
        trace.set_tracer_provider(_tracer_provider)
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        
        _is_setup_complete = True
        logger.info("OpenTelemetry setup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {e}")
        # Clean up on failure
        shutdown_telemetry()


def trace_method(name: Optional[str] = None):
    """Decorator to add OpenTelemetry tracing to an async method.
    
    Args:
        name: Optional custom name for the span. If not provided, uses the function name.
        
    Returns:
        Decorated function with tracing capabilities.
    """
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Skip tracing if telemetry is disabled
            if not settings.OTEL_ENABLED or not _is_setup_complete:
                return await func(*args, **kwargs)
            
            tracer = trace.get_tracer(__name__)
            span_name = name or f"{func.__module__}.{func.__qualname__}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add function metadata
                    span.set_attribute("code.function", func.__name__)
                    span.set_attribute("code.namespace", func.__module__)
                    
                    # Execute the function
                    result = await func(*args, **kwargs)
                    
                    # Mark span as successful
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    # Record error in span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                    
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Skip tracing if telemetry is disabled
            if not settings.OTEL_ENABLED or not _is_setup_complete:
                return func(*args, **kwargs)
            
            tracer = trace.get_tracer(__name__)
            span_name = name or f"{func.__module__}.{func.__qualname__}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add function metadata
                    span.set_attribute("code.function", func.__name__)
                    span.set_attribute("code.namespace", func.__module__)
                    
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Mark span as successful
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    # Record error in span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__call__'):
            import inspect
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return func
    
    return decorator
