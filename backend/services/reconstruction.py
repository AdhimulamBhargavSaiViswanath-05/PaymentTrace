"""
Deterministic payment journey reconstruction service.

This service reconstructs a payment journey from database records without
using AI or hardcoded explanations. All facts are either directly from
data (PROVEN) or calculated deterministically (DERIVED).
"""

import json
from datetime import datetime
from typing import List, Optional, Tuple
from ..database import get_db_connection
from ..models import Order, PaymentEvent, PaymentAttempt, PaymentJourney, Evidence


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp string to datetime."""
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))


def calculate_duration_seconds(start: str, end: str) -> float:
    """Calculate duration between two timestamps in seconds."""
    start_dt = parse_timestamp(start)
    end_dt = parse_timestamp(end)
    return (end_dt - start_dt).total_seconds()


async def fetch_order(order_id: str) -> Optional[Order]:
    """
    Fetch order from database.
    
    Returns:
        Order if found, None otherwise
    """
    conn = await get_db_connection()
    
    try:
        cursor = await conn.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            (order_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
            
        return Order(
            order_id=row['order_id'],
            created_at=row['created_at'],
            amount=row['amount'],
            currency=row['currency'],
            merchant_status=row['merchant_status']
        )
        
    finally:
        await conn.close()


async def fetch_events(order_id: str) -> List[PaymentEvent]:
    """
    Fetch all payment events for an order, ordered by timestamp.
    
    IMPORTANT: Events are deterministically sorted by timestamp,
    not by insertion order or event_id.
    
    Returns:
        List of PaymentEvent, sorted chronologically
    """
    conn = await get_db_connection()
    
    try:
        cursor = await conn.execute(
            """
            SELECT * FROM payment_events 
            WHERE order_id = ?
            ORDER BY timestamp ASC
            """,
            (order_id,)
        )
        rows = await cursor.fetchall()
        
        events = []
        for row in rows:
            metadata = json.loads(row['metadata_json']) if row['metadata_json'] else None
            events.append(PaymentEvent(
                event_id=row['event_id'],
                order_id=row['order_id'],
                payment_id=row['payment_id'],
                event_type=row['event_type'],
                status=row['status'],
                timestamp=row['timestamp'],
                error_code=row['error_code'],
                metadata=metadata
            ))
        
        return events
        
    finally:
        await conn.close()


async def fetch_attempts(order_id: str) -> List[PaymentAttempt]:
    """
    Fetch all payment attempts for an order, ordered by attempt number.
    
    Returns:
        List of PaymentAttempt, sorted by attempt_number
    """
    conn = await get_db_connection()
    
    try:
        cursor = await conn.execute(
            """
            SELECT * FROM payment_attempts 
            WHERE order_id = ?
            ORDER BY attempt_number ASC
            """,
            (order_id,)
        )
        rows = await cursor.fetchall()
        
        attempts = []
        for row in rows:
            attempts.append(PaymentAttempt(
                attempt_id=row['attempt_id'],
                order_id=row['order_id'],
                payment_id=row['payment_id'],
                method=row['method'],
                attempt_number=row['attempt_number'],
                status=row['status'],
                created_at=row['created_at']
            ))
        
        return attempts
        
    finally:
        await conn.close()


def calculate_derived_facts(order: Order, events: List[PaymentEvent], 
                           attempts: List[PaymentAttempt]) -> dict:
    """
    Calculate deterministic derived facts from available data.
    
    All calculations are deterministic - same input always produces same output.
    No AI or probabilistic methods are used.
    
    Returns:
        Dictionary of derived facts
    """
    attempt_count = len(attempts)
    event_count = len(events)
    
    # Journey start and end
    if events:
        journey_start = events[0].timestamp
        journey_end = events[-1].timestamp
        journey_duration_seconds = calculate_duration_seconds(journey_start, journey_end)
    else:
        journey_start = order.created_at
        journey_end = order.created_at
        journey_duration_seconds = 0.0
    
    # Retry count (attempts after the first one)
    retry_count = max(0, attempt_count - 1)
    
    # Calculate retry gaps (time between consecutive attempts)
    retry_gaps_seconds = []
    if len(attempts) > 1:
        for i in range(1, len(attempts)):
            gap = calculate_duration_seconds(
                attempts[i-1].created_at,
                attempts[i].created_at
            )
            retry_gaps_seconds.append(gap)
    
    # Final status from most recent attempt or order status
    if attempts:
        final_status = attempts[-1].status
    else:
        final_status = order.merchant_status or "unknown"
    
    return {
        "attempt_count": attempt_count,
        "event_count": event_count,
        "journey_start": journey_start,
        "journey_end": journey_end,
        "journey_duration_seconds": journey_duration_seconds,
        "retry_count": retry_count,
        "retry_gaps_seconds": retry_gaps_seconds,
        "final_status": final_status
    }


async def reconstruct_journey(order_id: str) -> Optional[PaymentJourney]:
    """
    Reconstruct complete payment journey for an order.
    
    This is the main entry point for deterministic journey reconstruction.
    
    Args:
        order_id: The order ID to reconstruct
        
    Returns:
        PaymentJourney if order exists, None otherwise
    """
    # Fetch all data
    order = await fetch_order(order_id)
    if not order:
        return None
    
    events = await fetch_events(order_id)
    attempts = await fetch_attempts(order_id)
    
    # Calculate derived facts
    derived = calculate_derived_facts(order, events, attempts)
    
    # Generate evidence (will be implemented in evidence.py)
    from .evidence import classify_evidence
    evidence = classify_evidence(order, events, attempts, derived)
    
    # Construct journey
    journey = PaymentJourney(
        order_id=order_id,
        order=order,
        events=events,
        attempts=attempts,
        attempt_count=derived["attempt_count"],
        event_count=derived["event_count"],
        journey_start=derived["journey_start"],
        journey_end=derived["journey_end"],
        journey_duration_seconds=derived["journey_duration_seconds"],
        retry_count=derived["retry_count"],
        retry_gaps_seconds=derived["retry_gaps_seconds"],
        final_status=derived["final_status"],
        evidence=evidence
    )
    
    return journey
