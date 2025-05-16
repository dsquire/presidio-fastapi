from fastapi import APIRouter, HTTPException, Request
from app.models import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer import get_analyzer
from app.middleware import MetricsMiddleware

router = APIRouter()

@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze text for PII entities",
    response_description="List of detected PII entities",
    tags=["Analyzer"]
)
async def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze text for personally identifiable information (PII) using Microsoft Presidio.
    
    Args:
        request: AnalyzeRequest containing the text to analyze and optional language code
        
    Returns:
        AnalyzeResponse containing the list of detected entities
        
    Raises:
        HTTPException: If the analysis fails or invalid language is provided
    """
    try:
        analyzer = get_analyzer()
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
        
        return AnalyzeResponse(entities=entities)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@router.get("/metrics")
async def metrics(request: Request):
    """Get application metrics."""
    if not isinstance(request.app.metrics, MetricsMiddleware):
        raise HTTPException(status_code=500, detail="Metrics middleware not configured")
    return request.app.metrics.get_metrics()
