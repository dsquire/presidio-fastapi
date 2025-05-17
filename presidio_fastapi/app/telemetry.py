"""OpenTelemetry configuration and utilities."""

import logging
from collections.abc import Awaitable, Callable
from functools import lru_cache, wraps
from typing import ParamSpec, TypeVar

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.status import Status, StatusCode

from presidio_fastapi.app.config import settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


@lru_cache()
def setup_telemetry(app: FastAPI) -> None:
    """Set up OpenTelemetry tracing for the FastAPI application.

    Configures the tracer provider, OTLP exporter, and FastAPI instrumentation.

    Args:
        app: The FastAPI application instance to instrument.
    """
    try:
        # Create and set tracer provider
        tracer_provider = TracerProvider()
        trace.set_tracer_provider(tracer_provider)

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTLP_ENDPOINT,
            insecure=not settings.OTLP_SECURE,
        )

        # Add BatchSpanProcessor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=tracer_provider,
            excluded_urls="health,metrics",
        )

        logger.info("OpenTelemetry instrumentation configured successfully")

    except Exception as e:
        logger.error("Failed to configure OpenTelemetry: %s", str(e))
        logger.exception(e)


def trace_method(
    name: str | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator to add OpenTelemetry tracing to an async method.

    Args:
        name: Optional name for the span. If not provided, the function name is used.

    Returns:
        A decorator function that adds tracing to the decorated async method.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        """Wrap the async function with tracing.

        Args:
            func: The async function to be wrapped with tracing.

        Returns:
            The wrapped async function with tracing added.
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """Execute the wrapped async function with tracing.

            Args:
                *args: Positional arguments to pass to the wrapped async function.
                **kwargs: Keyword arguments to pass to the wrapped async function.

            Returns:
                The result of the wrapped async function.

            Raises:
                Any exception that the wrapped async function may raise.
            """
            # Get current tracer
            tracer = trace.get_tracer(__name__)
            span_name = name or func.__name__

            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add function parameters to span attributes
                    span.set_attributes(
                        {
                            "function.name": func.__name__,
                            "function.args": str(args),
                            "function.kwargs": str(kwargs),
                        }
                    )

                    result: R = await func(*args, **kwargs)

                    # Add success status
                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    # Record error in span
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator
