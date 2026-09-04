"""
PaymentTrace Backend - Phase 0
Minimal FastAPI application with health check endpoint only.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PaymentTrace",
    description="Developer diagnostic tool for investigating payment journeys",
    version="0.1.0"
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
        "version": "0.1.0",
        "phase": "0 - Setup"
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
        "health": "/health"
    }
