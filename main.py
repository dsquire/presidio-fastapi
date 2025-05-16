from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get configuration from environment
NLP_ENGINE_NAME = os.getenv("NLP_ENGINE_NAME", "spacy")
SPACY_MODEL_EN = os.getenv("SPACY_MODEL_EN", "en_core_web_lg")
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "102400"))
# Default to a secure setting (empty list) if no origins are specified
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "")
# Parse allowed origins - if '*' is provided, convert to [] which FastAPI interprets as allowing no origins
# This forces explicit configuration of allowed origins in production
ALLOWED_ORIGINS = [] if ALLOWED_ORIGINS_STR == "*" else [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]
MIN_CONFIDENCE_SCORE = float(os.getenv("MIN_CONFIDENCE_SCORE", "0.5"))

# Initialize FastAPI app with metadata
app = FastAPI(
    title="Presidio Analyzer API",
    description="API for analyzing text for PII using Microsoft Presidio",
    version="1.0.0"
)

# Add CORS middleware with secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Only set allow_credentials=True when specific origins are defined
    allow_credentials=len(ALLOWED_ORIGINS) > 0,
    # Restrict to specific HTTP methods needed rather than allowing all
    allow_methods=["GET", "POST", "OPTIONS"],
    # Specify only the headers you need instead of "*"
    allow_headers=["Content-Type", "Authorization"],
    # Add additional security with max_age
    max_age=86400,  # 24 hours
)

# Initialize the analyzer engine with configuration from environment
nlp_config = {
    "nlp_engine_name": NLP_ENGINE_NAME,
    "models": [{"lang_code": "en", "model_name": SPACY_MODEL_EN}]
}
nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
analyzer = AnalyzerEngine(nlp_engine=nlp_engine)

class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        description="The text to analyze for PII",
        min_length=1,
        max_length=MAX_TEXT_LENGTH
    )
    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Two-letter language code (ISO 639-1)"
    )

class Entity(BaseModel):
    entity_type: str
    start: int
    end: int
    score: float
    text: str

class AnalyzeResponse(BaseModel):
    entities: List[Entity]

@app.post(
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
        # Analyze the text using Presidio
        results = analyzer.analyze(
            text=request.text,
            language=request.language,
        )
        
        # Convert results to response format
        entities = [
            Entity(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
                text=request.text[result.start:result.end]
            )
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

# Example route for testing
@app.get("/")
async def read_root():
    return {
        "status": "ok",
        "message": "Welcome to Presidio Analyzer API. Use POST /analyze to analyze text."
    }