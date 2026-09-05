"""
PaymentTrace Backend - Phase 2
FastAPI application with deterministic payment journey reconstruction
and LLM-based diagnostic explanation generation.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from .database import initialize_database
from .fixtures.data import load_fixtures
from .services.reconstruction import reconstruct_journey
from .services.llm import generate_diagnosis
from .models import PaymentJourney, DiagnosticResponse, Diagnosis

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Initializes database and loads fixtures on startup.
    """
    # Startup
    await initialize_database()
    await load_fixtures()
    yield
    # Shutdown (nothing to clean up)


app = FastAPI(
    title="PaymentTrace",
    description="Developer diagnostic tool for investigating payment journeys with evidence-grounded AI explanations",
    version="0.3.0",
    lifespan=lifespan
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify API is running.
    
    Returns:
        dict: Status and version information
    """
    llm_configured = bool(os.getenv("GEMINI_API_KEY"))
    
    return {
        "status": "healthy",
        "service": "PaymentTrace",
        "version": "0.3.0",
        "phase": "2 - LLM Diagnostic Integration",
        "llm_configured": llm_configured
    }


@app.get("/")
async def root():
    """
    Root endpoint with basic API information.
    
    Returns:
        dict: Welcome message and documentation link
    """
    return {
        "message": "PaymentTrace API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "journeys": "/journeys/{order_id}",
            "diagnosis": "/journeys/{order_id}/diagnosis"
        }
    }


@app.get("/journeys/{order_id}", response_model=PaymentJourney)
async def get_payment_journey(order_id: str):
    """
    Reconstruct payment journey for a given order ID.
    
    This endpoint performs deterministic reconstruction from database records.
    NO AI-generated content is returned - only structured evidence.
    
    Returns structured data including:
    - Order details
    - All events (chronologically ordered)
    - All payment attempts
    - Derived facts (attempt count, duration, retries, etc.)
    - Evidence classification (PROVEN/DERIVED/INCONSISTENCY/UNKNOWN)
    
    Args:
        order_id: The order ID to investigate
        
    Returns:
        PaymentJourney: Complete reconstructed journey with evidence
        
    Raises:
        HTTPException: 404 if order not found
    """
    journey = await reconstruct_journey(order_id)
    
    if not journey:
        raise HTTPException(
            status_code=404,
            detail=f"Order '{order_id}' not found in database"
        )
    
    return journey


@app.get("/journeys/{order_id}/diagnosis", response_model=DiagnosticResponse)
async def get_payment_diagnosis(order_id: str):
    """
    Get payment journey with AI-generated diagnostic explanation.
    
    This endpoint:
    1. Uses the existing deterministic reconstruction engine (Phase 1)
    2. Extracts pre-classified evidence
    3. Sends structured evidence to LLM with strict constraints
    4. Generates natural-language diagnostic explanation
    
    IMPORTANT: The LLM does NOT determine facts or perform reasoning.
    All facts are established by the deterministic engine.
    The LLM only converts structured evidence into readable explanations.
    
    Args:
        order_id: The order ID to investigate
        
    Returns:
        DiagnosticResponse: Journey + AI-generated diagnostic explanation
        
    Raises:
        HTTPException: 404 if order not found
        HTTPException: 503 if LLM service unavailable
    """
    # Step 1: Get deterministic journey reconstruction
    journey = await reconstruct_journey(order_id)
    
    if not journey:
        raise HTTPException(
            status_code=404,
            detail=f"Order '{order_id}' not found in database"
        )
    
    # Step 2: Check LLM configuration
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="LLM service not configured. Set GEMINI_API_KEY environment variable."
        )
    
    # Step 3: Generate diagnosis from structured evidence
    try:
        diagnosis_data = await generate_diagnosis(journey)
        
        diagnosis = Diagnosis(**diagnosis_data)
        
        # Step 4: Construct response
        response = DiagnosticResponse(
            order_id=order_id,
            journey=journey,
            diagnosis=diagnosis,
            llm_model="gemini-3.7-flash",
            evidence_based=True  # Always true - diagnosis based only on evidence
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate diagnosis: {str(e)}"
        )
