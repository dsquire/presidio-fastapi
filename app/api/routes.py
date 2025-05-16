"""Routes module for the Presidio FastAPI API.

This module contains all the route handlers for the API endpoints.
"""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.middleware import MetricsMiddleware
from app.models import AnalyzeRequest, AnalyzeResponse, BatchAnalyzeRequest, BatchAnalyzeResponse
from app.telemetry import trace_method

logger = logging.getLogger(__name__)
router = APIRouter(prefix=f"/api/{settings.API_VERSION}")

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
    """Analyze text for personally identifiable information (PII).

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
        An AnalyzeResponse object containing a list of detected PII entities.
        Each entity includes:
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
            {
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score,
                "text": request.text[result.start:result.end],
            }
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
async def analyze_batch(request: BatchAnalyzeRequest, req: Request) -> BatchAnalyzeResponse:
    """Analyze multiple texts for personally identifiable information (PII).

    This endpoint uses Microsoft Presidio to detect PII entities in a batch
    of texts provided in the request.

    Args:
        request: The request body containing texts to analyze.
            It includes the following fields:
            - texts (List[str]): A list of input texts to analyze.
            - language (str): Two-letter language code (default: "en").
        req: FastAPI request object to access application state,
            specifically the Presidio analyzer instance.

    Returns:
        A BatchAnalyzeResponse object containing analysis results for each text.
        Each result includes:
        - entities (List[dict]): List of detected PII entities for that text.
        - cached (bool): Whether the result was from cache (Note: caching not
          explicitly implemented in this snippet for batch items).

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

        results = []
        for text in request.texts:
            try:
                analyzed = analyzer.analyze(
                    text=text,
                    language=request.language,
                )

                entities = [
                    {
                        "entity_type": result.entity_type,
                        "start": result.start,
                        "end": result.end,
                        "score": result.score,
                        "text": text[result.start:result.end],
                    }
                    for result in analyzed
                ]

                results.append(AnalyzeResponse(entities=entities))

            except Exception as e:
                logger.exception("Error analyzing text: %s", str(e))
                results.append(AnalyzeResponse(entities=[]))

        logger.info("Processed %d texts in batch", len(results))
        return BatchAnalyzeResponse(results=results)

    except Exception as e:
        logger.exception("Unexpected error during batch analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        ) from e

@router.get(
    "/health",
    summary="Health check endpoint",
    response_description="Service health status",
    status_code=status.HTTP_200_OK,
    tags=["Monitoring"],
)
@trace_method("health_check")
async def health_check() -> Dict[str, str]:
    """Check the health status of the service.

    Returns:
        A dictionary indicating the service health status.
        Example: {"status": "healthy"}
    """
    return {"status": "healthy"}

@router.get(
    "/metrics",
    summary="Service metrics",
    response_description="Application metrics and statistics",
    status_code=status.HTTP_200_OK,
    tags=["Monitoring"],
)
@trace_method("metrics")
async def metrics(request: Request) -> Dict[str, Any]:
    """Get application metrics and statistics.

    Args:
        request: FastAPI request object, used to access the
            metrics middleware from the application state.

    Returns:
        A dictionary containing various metrics, such as request counts
        and response times, as provided by the MetricsMiddleware.

    Raises:
        HTTPException: If the metrics middleware is not properly configured
            or found in the application state.
    """
    metrics_middleware: MetricsMiddleware | None = getattr(request.app.state, "metrics", None)
    if not isinstance(metrics_middleware, MetricsMiddleware):
        logger.exception("Metrics middleware not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics middleware not configured",
        )
    return metrics_middleware.get_metrics()
