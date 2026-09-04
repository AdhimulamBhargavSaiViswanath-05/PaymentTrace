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
