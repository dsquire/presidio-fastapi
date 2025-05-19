"""Routes module for the Presidio FastAPI API."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, status
from presidio_analyzer import AnalyzerEngine

from presidio_fastapi.app.middleware import MetricsMiddleware
from presidio_fastapi.app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    Entity,
)
from presidio_fastapi.app.telemetry import trace_method

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/",
    summary="Root endpoint",
    response_description="API status",
    status_code=status.HTTP_200_OK,
    tags=["Monitoring"],
)
@trace_method("root")
async def root() -> Dict[str, str]:
    """Root API endpoint.

    Returns:
        A simple status message confirming the API is running.
    """
    return {"status": "ok"}


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze text for PII entities",
    response_description="List of detected PII entities",
    status_code=status.HTTP_200_OK,
    tags=["Analyzer"],
)
@trace_method("analyze_text")
async def analyze_text(request: AnalyzeRequest, req: Request) -> AnalyzeResponse:
    """Analyzes text for personally identifiable information (PII).

    This endpoint uses Microsoft Presidio to detect PII entities in the
    provided text.

    Args:
        request: The request body containing text to analyze.
            It includes the following fields:
            - text (str): The input text to analyze.
            - language (str): Two-letter language code (default: "en").
        req: FastAPI request object to access application state,
            specifically the Presidio analyzer instance.

    Returns:
        AnalyzeResponse: An AnalyzeResponse object containing a list of
                         detected PII entities. Each entity includes:
                         - entity_type (str): Type of PII detected.
                         - start (int): Starting character position.
                         - end (int): Ending character position.
                         - score (float): Confidence score.
                         - text (str): The matched text.

    Raises:
        HTTPException:
            - 400 (Bad Request): If input parameters are invalid.
            - 503 (Service Unavailable): If the analyzer service is not available.
            - 500 (Internal Server Error): For unexpected errors during analysis.
    """
    try:
        analyzer = req.app.state.analyzer
        if not analyzer:
            logger.exception("Analyzer service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analyzer service not available",
            )

        logger.info("Analyzing text in %s", request.language)
        results = analyzer.analyze(
            text=request.text,
            language=request.language,
        )

        entities = [
            Entity(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
                text=request.text[result.start : result.end],
            )
            for result in results
        ]

        logger.info("Found %d entities", len(entities))
        return AnalyzeResponse(entities=entities)

    except ValueError as e:
        logger.error("Invalid request: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        ) from e


@router.post(
    "/analyze/batch",
    response_model=BatchAnalyzeResponse,
    summary="Analyze multiple texts for PII entities",
    response_description="List of analysis results",
    status_code=status.HTTP_200_OK,
    tags=["Analyzer"],
)
@trace_method("analyze_batch")
async def analyze_batch(
    request: BatchAnalyzeRequest, req: Request
) -> BatchAnalyzeResponse:
    """Analyze multiple texts for personally identifiable information (PII).

    This endpoint uses Microsoft Presidio to detect PII entities in a batch
    of texts provided in the request.
    """
    try:
        analyzer = _get_analyzer_from_request(req)
        # Create AnalyzeResponse for each text
        results = [
            AnalyzeResponse(
                entities=_analyze_single_text(analyzer, text, request.language)
            )
            for text in request.texts
        ]
        logger.info("Processed %d texts in batch", len(results))
        return BatchAnalyzeResponse(results=results)
    except Exception as e:
        logger.exception("Unexpected error during batch analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        ) from e


def _get_analyzer_from_request(req: Request) -> AnalyzerEngine:
    analyzer = getattr(req.app.state, "analyzer", None)
    if not analyzer:
        logger.exception("Analyzer service not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analyzer service not available",
        )
    return analyzer


def _analyze_single_text(
    analyzer: AnalyzerEngine, text: str, language: str
) -> list[Entity]:
    try:
        analyzed = analyzer.analyze(
            text=text,
            language=language,
        )

        entities = [
            Entity(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
                text=text[result.start : result.end],
            )
            for result in analyzed
        ]

        return entities
    except Exception as e:
        logger.exception("Error analyzing text: %s", str(e))
        return []


@router.get(
    "/health",
    summary="Health check endpoint",
    response_description="Service health status",
    status_code=status.HTTP_200_OK,
    tags=["Monitoring"],
)
@trace_method("health_check")
async def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        A simple status message confirming the service is healthy.
    """
    return {"status": "healthy"}


@router.get(
    "/metrics",
    summary="Metrics endpoint",
    response_description="Service metrics data",
    status_code=status.HTTP_200_OK,
    tags=["Monitoring"],
)
@trace_method("metrics")
async def metrics(request: Request) -> Dict[str, Any]:
    """Get service metrics.

    Args:
        request: FastAPI request object to access state.

    Returns:
        Dictionary containing service metrics data.
    """
    metrics_middleware: MetricsMiddleware = request.app.state.metrics

    # Debug logging
    metrics_data = metrics_middleware.get_metrics()
    logger.info(
        f"GET /metrics - Current metrics: total_requests={metrics_data['total_requests']}, "
        f"requests_by_path={metrics_data['requests_by_path']}"
    )

    return metrics_data
