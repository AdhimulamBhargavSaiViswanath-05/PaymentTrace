"""
Advanced fixture scenarios for testing payment integrity validation.

Phase 4A: State machine validation fixtures.
Phase 4B: Out-of-order event detection fixtures.
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


async def load_scenario_e():
    """
    SCENARIO E: Out-of-order events - authorized before initiated
    
    Timeline (database timestamps, not logical order):
    1. Payment authorized at 14:10:05Z
    2. Payment initiated at 14:10:10Z (AFTER authorization - INVALID)
    3. Payment captured at 14:10:15Z
    
    This demonstrates:
    - Timestamp ordering violation
    - Authorized event has earlier timestamp than initiated event
    - Events are stored out of logical order
    
    Expected detection:
    - INCONSISTENCY evidence: "Out-of-order events detected: payment.authorized occurred before payment.initiated"
    
    Note: The reconstruction service will sort these by timestamp for display,
    but the integrity validation should detect the logical order violation.
    """
    order_id = "order_scenario_e"
    payment_id = "pay_e_outoforder"
    
    # Create order
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T14:10:00Z",
        amount=100000,  # 1000.00 in smallest currency unit
        currency="INR",
        merchant_status="paid"
    )
    
    # Single payment attempt
    await insert_payment_attempt(
        attempt_id="attempt_e_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T14:10:05Z"
    )
    
    # Event 1: Payment authorized (EARLIEST timestamp)
    await insert_payment_event(
        event_id="event_e_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T14:10:05Z"
    )
    
    # Event 2: Payment initiated (MIDDLE timestamp - but logically should be FIRST)
    await insert_payment_event(
        event_id="event_e_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T14:10:10Z"
    )
    
    # Event 3: Payment captured (LATEST timestamp)
    await insert_payment_event(
        event_id="event_e_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T14:10:15Z"
    )


async def load_advanced_scenarios():
    """
    Load all advanced scenario fixtures.
    """
    await load_scenario_c()
    await load_scenario_e()
