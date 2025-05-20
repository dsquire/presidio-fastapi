"""Prometheus metrics integration for FastAPI."""

import logging
from typing import Callable

from fastapi import FastAPI
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

from presidio_fastapi.app.config import settings

logger = logging.getLogger(__name__)

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total count of HTTP requests", 
    ["method", "endpoint", "status_code"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)
ERROR_COUNT = Counter(
    "http_errors_total", 
    "Total count of HTTP errors", 
    ["method", "endpoint", "status_code"]
)
ACTIVE_REQUESTS = Gauge(
    "http_active_requests", 
    "Number of currently active HTTP requests",
    ["method", "endpoint"]
)
PII_ENTITIES_DETECTED = Counter(
    "presidio_pii_entities_detected_total",
    "Total count of PII entities detected",
    ["entity_type", "language"]
)

class PrometheusMiddleware:
    """Middleware for collecting Prometheus metrics on HTTP requests."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        logger.info("Prometheus middleware initialized")
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        path = scope["path"]
        method = scope["method"]
        
        # Only collect metrics for configured paths
        api_version = settings.API_VERSION
        monitored_path_suffixes = [
            suffix.strip() for suffix in settings.PROMETHEUS_MONITORED_PATHS.split(",")
            if suffix.strip()
        ]
        monitored_paths = [f"/api/{api_version}/{suffix}" for suffix in monitored_path_suffixes]
        
        # Skip metrics collection for non-monitored paths
        if path not in monitored_paths:
            # Skip metrics endpoint to avoid recursion
            if path == f"/api/{api_version}/metrics":
                logger.debug(f"Skipping metrics collection for metrics endpoint: {path}")
            else:
                logger.debug(f"Skipping metrics collection for non-monitored path: {path}")
            return await self.app(scope, receive, send)
            
        # From here, we only process monitored paths
        logger.debug(f"Collecting metrics for monitored path: {path}")
            
        # Increment active requests
        ACTIVE_REQUESTS.labels(method=method, endpoint=path).inc()
        
        # Define response interceptor
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status_code).inc()
                
                # Record errors (4xx and 5xx)
                if status_code >= 400:
                    ERROR_COUNT.labels(method=method, endpoint=path, status_code=status_code).inc()
                    
            await send(message)
            
            # Decrement active requests when response ends
            if message["type"] == "http.response.end":
                ACTIVE_REQUESTS.labels(method=method, endpoint=path).dec()
        
        # Start timer
        REQUEST_LATENCY.labels(method=method, endpoint=path).time()
        
        # Process request
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Ensure metrics are updated even if an exception occurs
            ACTIVE_REQUESTS.labels(method=method, endpoint=path).dec()
            ERROR_COUNT.labels(method=method, endpoint=path, status_code=500).inc()
            logger.exception("Error in request: %s", str(e))
            raise

def track_pii_entity(entity_type: str, language: str) -> None:
    """Increment counter for detected PII entity.
    
    Args:
        entity_type: The type of PII entity detected
        language: The language of the text analyzed
    """
    PII_ENTITIES_DETECTED.labels(entity_type=entity_type, language=language).inc()

def metrics_endpoint() -> Callable:
    """Create metrics endpoint handler.
    
    Returns:
        Callable: FastAPI endpoint handler function
    """
    async def metrics(request):
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST
        )
    return metrics

def setup_prometheus(app: FastAPI) -> None:
    """Set up Prometheus metrics for FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware)
    
    # Add metrics endpoint
    app.add_route(
        f"/api/{settings.API_VERSION}/metrics", 
        metrics_endpoint()
    )
    
    # Log monitored paths
    api_version = settings.API_VERSION
    monitored_path_suffixes = [
        suffix.strip() for suffix in settings.PROMETHEUS_MONITORED_PATHS.split(",")
        if suffix.strip()    ]
    monitored_paths = [f"/api/{api_version}/{suffix}" for suffix in monitored_path_suffixes]
    paths_str = ", ".join(monitored_paths)
    logger.info(f"Prometheus metrics setup complete. Monitoring paths: {paths_str}")
