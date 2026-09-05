"""
Advanced fixture scenarios for testing payment integrity validation.

Phase 4A: State machine validation fixtures.
Phase 4B: Out-of-order event detection fixtures.
Phase 4C: Duplicate and missing event detection fixtures.
Phase 4D: Timeline gap and timing anomaly detection fixtures.
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


async def load_scenario_f():
    """
    SCENARIO F: Duplicate lifecycle events

    Timeline:
    1. Payment initiated at 14:20:05Z
    2. Payment authorized at 14:20:10Z
    3. Payment captured at 14:20:15Z (FIRST)
    4. Payment captured at 14:20:20Z (DUPLICATE - INVALID)

    This demonstrates:
    - Duplicate payment.captured event
    - Same lifecycle event occurring multiple times for same payment_id

    Expected detection:
    - INCONSISTENCY evidence: "Duplicate lifecycle event detected - payment.captured occurred 2 times"
    """
    order_id = "order_scenario_f"
    payment_id = "pay_f_duplicate"

    # Create order
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T14:20:00Z",
        amount=85000,  # 850.00 in smallest currency unit
        currency="INR",
        merchant_status="paid"
    )

    # Single payment attempt
    await insert_payment_attempt(
        attempt_id="attempt_f_1",
        order_id=order_id,
        payment_id=payment_id,
        method="netbanking",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T14:20:05Z"
    )

    # Event 1: Payment initiated
    await insert_payment_event(
        event_id="event_f_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T14:20:05Z"
    )

    # Event 2: Payment authorized
    await insert_payment_event(
        event_id="event_f_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T14:20:10Z"
    )

    # Event 3: Payment captured (FIRST)
    await insert_payment_event(
        event_id="event_f_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T14:20:15Z"
    )

    # Event 4: Payment captured (DUPLICATE - INVALID)
    await insert_payment_event(
        event_id="event_f_4",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T14:20:20Z"
    )


async def load_scenario_g():
    """
    SCENARIO G: Missing expected lifecycle events

    Timeline:
    1. Payment authorized at 14:30:10Z (NO initiated event)
    2. Payment captured at 14:30:15Z

    This demonstrates:
    - Missing payment.initiated event in available data
    - Payment lifecycle with gaps in recorded events

    Expected detection:
    - UNKNOWN evidence: "No payment.initiated event found in available data, though payment.authorized is present"

    Note: This is flagged as UNKNOWN (not INCONSISTENCY) because we cannot prove
    the initiated event never occurred - it may simply not be in our data.
    """
    order_id = "order_scenario_g"
    payment_id = "pay_g_missing"

    # Create order
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T14:30:00Z",
        amount=95000,  # 950.00 in smallest currency unit
        currency="INR",
        merchant_status="paid"
    )

    # Single payment attempt
    await insert_payment_attempt(
        attempt_id="attempt_g_1",
        order_id=order_id,
        payment_id=payment_id,
        method="wallet",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T14:30:10Z"
    )

    # Event 1: Payment authorized (NO initiated event before this)
    await insert_payment_event(
        event_id="event_g_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T14:30:10Z"
    )

    # Event 2: Payment captured
    await insert_payment_event(
        event_id="event_g_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T14:30:15Z"
    )


async def load_scenario_h():
    """
    SCENARIO H: Extremely long authorization delay

    Timeline:
    1. Payment initiated at 15:00:00Z
    2. Payment authorized at 15:02:00Z (120 seconds later - exceeds 90s threshold)
    3. Payment captured at 15:02:05Z

    This demonstrates:
    - Unusually long initiated → authorized gap (120s > 90s threshold)
    - Valid payment state machine (no INCONSISTENCY)
    - Normal authorized → captured gap (5s)
    - Timing anomaly detection (Phase 4D)

    Expected detection:
    - UNKNOWN evidence: Unusually long gap between initiated and authorized
    - No state machine violations (Phase 4A)
    - No out-of-order violations (Phase 4B)
    - No duplicate/missing violations (Phase 4C)

    Note: This is still a VALID payment flow, just with suspicious timing.
    """
    order_id = "order_scenario_h"
    payment_id = "pay_h_longdelay"

    # Create order
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T15:00:00Z",
        amount=150000,  # 1500.00 in smallest currency unit
        currency="INR",
        merchant_status="paid"
    )

    # Single payment attempt
    await insert_payment_attempt(
        attempt_id="attempt_h_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T15:00:00Z"
    )

    # Event 1: Payment initiated
    await insert_payment_event(
        event_id="event_h_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T15:00:00Z"
    )

    # Event 2: Payment authorized (120 seconds after initiated)
    await insert_payment_event(
        event_id="event_h_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T15:02:00Z"
    )

    # Event 3: Payment captured (5 seconds after authorized)
    await insert_payment_event(
        event_id="event_h_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T15:02:05Z"
    )


async def load_scenario_i():
    """
    SCENARIO I: Suspiciously fast event sequence (near-zero gaps)

    Timeline:
    1. Payment initiated at 15:10:00.000Z
    2. Payment authorized at 15:10:00.020Z (20 milliseconds later)
    3. Payment captured at 15:10:00.040Z (20 milliseconds later)

    This demonstrates:
    - Near-zero gaps (< 50ms threshold)
    - Millisecond timestamp precision
    - Valid payment state machine (no INCONSISTENCY)
    - Timing anomaly detection (Phase 4D)

    Expected detection:
    - UNKNOWN evidence: Near-zero gap between initiated and authorized
    - UNKNOWN evidence: Near-zero gap between authorized and captured
    - No state machine violations (Phase 4A)
    - No out-of-order violations (Phase 4B)
    - No duplicate/missing violations (Phase 4C)

    Note: This may indicate timestamp precision issues or synchronization behavior,
    not necessarily a payment problem.
    """
    order_id = "order_scenario_i"
    payment_id = "pay_i_nearzero"

    # Create order
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T15:10:00Z",
        amount=200000,  # 2000.00 in smallest currency unit
        currency="INR",
        merchant_status="paid"
    )

    # Single payment attempt
    await insert_payment_attempt(
        attempt_id="attempt_i_1",
        order_id=order_id,
        payment_id=payment_id,
        method="upi",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T15:10:00Z"
    )

    # Event 1: Payment initiated (with millisecond precision)
    await insert_payment_event(
        event_id="event_i_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T15:10:00.000Z"
    )

    # Event 2: Payment authorized (20ms after initiated)
    await insert_payment_event(
        event_id="event_i_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T15:10:00.020Z"
    )

    # Event 3: Payment captured (20ms after authorized)
    await insert_payment_event(
        event_id="event_i_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T15:10:00.040Z"
    )


async def load_advanced_scenarios():
    """
    Load all advanced scenario fixtures.
    """
    await load_scenario_c()
    await load_scenario_e()
    await load_scenario_f()
    await load_scenario_g()
    await load_scenario_h()
    await load_scenario_i()
