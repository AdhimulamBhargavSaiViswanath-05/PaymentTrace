"""
Fixture data for testing payment journey reconstruction.

These are controlled, realistic scenarios - NOT production data.
Error codes and behaviors are generic/simulated, not official Razorpay specifications.
"""

from ..database import (
    clear_database,
    insert_order,
    insert_payment_attempt,
    insert_payment_event
)


async def load_fixtures():
    """
    Load all fixture scenarios into the database.
    Clears existing data first.
    """
    await clear_database()
    await load_scenario_a()
    await load_scenario_b()


async def load_scenario_a():
    """
    SCENARIO A: UPI retry after PIN error
    
    Timeline:
    1. Customer initiates UPI payment
    2. First attempt fails (generic authentication error)
    3. Customer retries with correct PIN
    4. Second attempt succeeds
    
    This demonstrates:
    - Multiple payment attempts
    - Retry behavior
    - Success after failure
    - Retry gap timing
    """
    order_id = "order_scenario_a"
    payment_id_1 = "pay_a_attempt1"
    payment_id_2 = "pay_a_attempt2"
    
    # Create order
    await insert_order(
        order_id=order_id,
        created_at="2026-09-04T10:00:00Z",
        amount=50000,  # 500.00 in smallest currency unit
        currency="INR",
        merchant_status="paid"
    )
    
    # First payment attempt - failed
    await insert_payment_attempt(
        attempt_id="attempt_a_1",
        order_id=order_id,
        payment_id=payment_id_1,
        method="upi",
        attempt_number=1,
        status="failed",
        created_at="2026-09-04T10:00:05Z"
    )
    
    # Events for first attempt
    await insert_payment_event(
        event_id="event_a_1",
        order_id=order_id,
        payment_id=payment_id_1,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-04T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_a_2",
        order_id=order_id,
        payment_id=payment_id_1,
        event_type="payment.failed",
        status="failed",
        timestamp="2026-09-04T10:00:12Z",
        error_code="BAD_REQUEST_ERROR",
        metadata={"description": "Authentication failed"}
    )
    
    # Second payment attempt - success (45 seconds after first attempt)
    await insert_payment_attempt(
        attempt_id="attempt_a_2",
        order_id=order_id,
        payment_id=payment_id_2,
        method="upi",
        attempt_number=2,
        status="captured",
        created_at="2026-09-04T10:00:50Z"
    )
    
    # Events for second attempt
    await insert_payment_event(
        event_id="event_a_3",
        order_id=order_id,
        payment_id=payment_id_2,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-04T10:00:50Z"
    )
    
    await insert_payment_event(
        event_id="event_a_4",
        order_id=order_id,
        payment_id=payment_id_2,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-04T10:00:58Z"
    )
    
    await insert_payment_event(
        event_id="event_a_5",
        order_id=order_id,
        payment_id=payment_id_2,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-04T10:00:59Z"
    )


async def load_scenario_b():
    """
    SCENARIO B: Late authorization / non-clean payment journey
    
    Timeline:
    1. Payment initiated
    2. Authorization delayed (longer than typical)
    3. Authorization received
    4. Capture occurs after authorization
    5. Order status shows inconsistency (demonstrates INCONSISTENCY category)
    
    This demonstrates:
    - Authorization timing
    - Capture timing
    - State inconsistencies between systems
    - Duration calculations for longer journeys
    """
    order_id = "order_scenario_b"
    payment_id = "pay_b_single"
    
    # Create order with inconsistent status
    await insert_order(
        order_id=order_id,
        created_at="2026-09-04T11:30:00Z",
        amount=125000,  # 1250.00 in smallest currency unit
        currency="INR",
        merchant_status="created"  # Inconsistent with payment status
    )
    
    # Single payment attempt
    await insert_payment_attempt(
        attempt_id="attempt_b_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-04T11:30:10Z"
    )
    
    # Event sequence with timing gaps
    await insert_payment_event(
        event_id="event_b_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-04T11:30:10Z"
    )
    
    # Long delay before authorization (45 seconds - unusual)
    await insert_payment_event(
        event_id="event_b_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-04T11:30:55Z",
        metadata={"authorization_delay": "unusual"}
    )
    
    # Capture shortly after authorization
    await insert_payment_event(
        event_id="event_b_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-04T11:31:02Z"
    )
    
    # Additional event showing webhook received
    await insert_payment_event(
        event_id="event_b_4",
        order_id=order_id,
        payment_id=payment_id,
        event_type="webhook.received",
        status="captured",
        timestamp="2026-09-04T11:31:05Z",
        metadata={"webhook_type": "payment.captured"}
    )
