"""
Advanced fixture scenarios for testing payment integrity validation.

Phase 4A: State machine validation fixtures.
"""

from ..database import (
    insert_order,
    insert_payment_attempt,
    insert_payment_event
)


async def load_scenario_c():
    """
    SCENARIO C: Invalid state transition - captured without authorization
    
    Timeline:
    1. Payment initiated
    2. Payment captured WITHOUT authorization (INVALID)
    
    This demonstrates:
    - Invalid state machine transition
    - Missing required authorization step before capture
    
    Expected detection:
    - INCONSISTENCY evidence: "payment.captured occurred without prior payment.authorized event"
    """
    order_id = "order_scenario_c"
    payment_id = "pay_c_invalid"
    
    # Create order
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T14:00:00Z",
        amount=75000,  # 750.00 in smallest currency unit
        currency="INR",
        merchant_status="paid"
    )
    
    # Single payment attempt - shows captured status
    await insert_payment_attempt(
        attempt_id="attempt_c_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T14:00:10Z"
    )
    
    # Event 1: Payment initiated
    await insert_payment_event(
        event_id="event_c_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T14:00:10Z"
    )
    
    # Event 2: Payment captured WITHOUT authorization (INVALID TRANSITION)
    await insert_payment_event(
        event_id="event_c_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T14:00:15Z"
    )


async def load_advanced_scenarios():
    """
    Load all advanced scenario fixtures.
    """
    await load_scenario_c()
