import logging
from typing import Optional

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
    tags=["Analyzer"]
)
@trace_method("analyze_text")
async def analyze_text(request: AnalyzeRequest, req: Request) -> AnalyzeResponse:
    """Analyze text for personally identifiable information (PII).
    
    This endpoint uses Microsoft Presidio to detect PII entities in the provided text.
    
    Args:
        request (AnalyzeRequest): The request body containing text to analyze.
            Contains fields:
            - text: The input text to analyze
            - language: Two-letter language code (default: "en")
        req (Request): FastAPI request object to access application state.
        
    Returns:
        AnalyzeResponse: Contains list of detected PII entities.
            Each entity has:
            - entity_type: Type of PII detected
            - start: Starting character position
            - end: Ending character position
            - score: Confidence score
            - text: The matched text
            
    Raises:
        HTTPException: 
            - 400: Invalid input parameters
            - 503: Analyzer service unavailable
            - 500: Unexpected error during analysis
    """
    try:
        analyzer = req.app.state.analyzer
        if not analyzer:
            logger.error("Analyzer service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analyzer service not available"
            )
            
        logger.info(f"Analyzing text in {request.language}")
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
                "text": request.text[result.start:result.end]
            }
            for result in results
        ]
        
        logger.info(f"Found {len(entities)} entities")
        return AnalyzeResponse(entities=entities)
        
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.exception("Unexpected error during analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        ) from e

@router.post(
    "/analyze/batch",
    response_model=BatchAnalyzeResponse,
    summary="Analyze multiple texts for PII entities",
    response_description="List of analysis results",
    status_code=status.HTTP_200_OK,
    tags=["Analyzer"]
)
@trace_method("analyze_batch")
async def analyze_batch(request: BatchAnalyzeRequest, req: Request) -> BatchAnalyzeResponse:
    """Analyze multiple texts for personally identifiable information (PII).
    
    This endpoint uses Microsoft Presidio to detect PII entities in multiple texts.
    
    Args:
        request (BatchAnalyzeRequest): The request body containing texts to analyze.
            Contains fields:
            - texts: List of input texts to analyze
            - language: Two-letter language code (default: "en")
        req (Request): FastAPI request object to access application state.
        
    Returns:
        BatchAnalyzeResponse: Contains analysis results for each text.
            Each result has:
            - entities: List of detected PII entities
            - cached: Whether the result was from cache
        
    Raises:
        HTTPException: 
            - 400: Invalid input parameters
            - 503: Analyzer service unavailable
            - 500: Unexpected error during analysis
    """
    try:
        analyzer = req.app.state.analyzer
        if not analyzer:
            logger.error("Analyzer service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analyzer service not available"
            )
        
        # Process each text
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
                        "text": text[result.start:result.end]
                    }
                    for result in analyzed
                ]
                
                results.append(AnalyzeResponse(entities=entities))
                
            except Exception as e:
                logger.error(f"Error analyzing text: {str(e)}")
                results.append(AnalyzeResponse(entities=[]))
        
        logger.info(f"Processed {len(results)} texts in batch")
        return BatchAnalyzeResponse(results=results)
        
    except Exception as e:
        logger.exception("Unexpected error during batch analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        ) from e

@router.get(
    "/health",
    summary="Health check endpoint",
    response_description="Service health status",
    status_code=status.HTTP_200_OK,
    tags=["Monitoring"]
)
@trace_method("health_check")
async def health_check():
    """Check the health status of the service.
    
    Returns:
        dict: Health status information
    """
    return {"status": "healthy"}

@router.get(
    "/metrics",
    summary="Service metrics",
    response_description="Application metrics and statistics",
    status_code=status.HTTP_200_OK,
    tags=["Monitoring"]
)
@trace_method("metrics")
async def metrics(request: Request):
    """Get application metrics and statistics.
    
    Args:
        request (Request): FastAPI request object
        
    Returns:
        dict: Metrics including request counts and response times
        
    Raises:
        HTTPException: If metrics middleware is not properly configured
    """
    metrics_middleware: Optional[MetricsMiddleware] = getattr(request.app.state, "metrics", None)
    if not isinstance(metrics_middleware, MetricsMiddleware):
        logger.error("Metrics middleware not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics middleware not configured"
        )
    return metrics_middleware.get_metrics()
