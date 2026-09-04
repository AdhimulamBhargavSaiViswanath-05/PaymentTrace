"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class PaymentEvent(BaseModel):
    """Payment event record."""
    event_id: str
    order_id: str
    payment_id: Optional[str]
    event_type: str
    status: Optional[str]
    timestamp: str
    error_code: Optional[str]
    metadata: Optional[dict]


class PaymentAttempt(BaseModel):
    """Payment attempt record."""
    attempt_id: str
    order_id: str
    payment_id: str
    method: str
    attempt_number: int
    status: str
    created_at: str


class Order(BaseModel):
    """Order record."""
    order_id: str
    created_at: str
    amount: int
    currency: str
    merchant_status: Optional[str]


class Evidence(BaseModel):
    """Evidence item with classification."""
    category: str  # PROVEN, DERIVED, INCONSISTENCY, UNKNOWN
    statement: str
    source: Optional[str] = None


class PaymentJourney(BaseModel):
    """Complete payment journey reconstruction."""
    order_id: str
    order: Order
    events: List[PaymentEvent]
    attempts: List[PaymentAttempt]
    
    # Derived facts
    attempt_count: int
    event_count: int
    journey_start: str
    journey_end: str
    journey_duration_seconds: float
    retry_count: int
    retry_gaps_seconds: List[float]
    final_status: str
    
    # Evidence classification
    evidence: List[Evidence]


class Diagnosis(BaseModel):
    """LLM-generated diagnostic explanation."""
    summary: str
    what_happened: str
    what_is_known: List[str]
    what_cannot_be_determined: List[str]
    recommended_action: str
    raw_explanation: str  # Full LLM response for transparency


class DiagnosticResponse(BaseModel):
    """Complete diagnostic response with journey and explanation."""
    order_id: str
    journey: PaymentJourney
    diagnosis: Diagnosis
    
    # Metadata
    llm_model: str
    evidence_based: bool  # Always True - diagnosis based only on evidence
