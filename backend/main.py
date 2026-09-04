"""
PaymentTrace Backend - Phase 1
FastAPI application with deterministic payment journey reconstruction.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import initialize_database
from .fixtures.data import load_fixtures
from .services.reconstruction import reconstruct_journey
from .models import PaymentJourney


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
    description="Developer diagnostic tool for investigating payment journeys",
    version="0.2.0",
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
    return {
        "status": "healthy",
        "service": "PaymentTrace",
        "version": "0.2.0",
        "phase": "1 - Data Model & Reconstruction"
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
            "journeys": "/journeys/{order_id}"
        }
    }


@app.get("/journeys/{order_id}", response_model=PaymentJourney)
async def get_payment_journey(order_id: str):
    """
    Reconstruct payment journey for a given order ID.
    
    This endpoint performs deterministic reconstruction from database records.
    NO hardcoded explanations or AI-generated content is returned.
    
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
