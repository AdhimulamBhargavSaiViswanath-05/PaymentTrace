"""
Tests for payment journey reconstruction logic.
"""

import pytest
from backend.database import (
    initialize_database,
    clear_database,
    insert_order,
    insert_payment_attempt,
    insert_payment_event
)
from backend.services.reconstruction import (
    fetch_order,
    fetch_events,
    fetch_attempts,
    calculate_derived_facts,
    reconstruct_journey,
    calculate_duration_seconds
)
from backend.fixtures.data import load_fixtures


@pytest.fixture
async def setup_database():
    """Setup clean database for each test."""
    await initialize_database()
    await clear_database()
    yield
    # Cleanup after test
    await clear_database()


@pytest.mark.asyncio
async def test_event_ordering(setup_database):
    """
    Test that events are deterministically ordered by timestamp,
    not by insertion order.
    """
    order_id = "test_order_ordering"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-04T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    # Insert events in WRONG chronological order
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id="pay_1",
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-04T10:00:30Z"  # Latest
    )
    
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id="pay_1",
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-04T10:00:10Z"  # Earliest
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id="pay_1",
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-04T10:00:20Z"  # Middle
    )
    
    # Fetch events - should be ordered by timestamp
    events = await fetch_events(order_id)
    
    assert len(events) == 3
    assert events[0].event_id == "event_1"  # Earliest timestamp
    assert events[1].event_id == "event_2"  # Middle timestamp
    assert events[2].event_id == "event_3"  # Latest timestamp
    assert events[0].event_type == "payment.initiated"
    assert events[2].event_type == "payment.captured"


@pytest.mark.asyncio
async def test_attempt_count(setup_database):
    """Test that attempt count is correctly calculated."""
    order_id = "test_order_attempts"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-04T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    # Add 3 attempts
    for i in range(1, 4):
        await insert_payment_attempt(
            attempt_id=f"attempt_{i}",
            order_id=order_id,
            payment_id=f"pay_{i}",
            method="upi",
            attempt_number=i,
            status="failed" if i < 3 else "captured",
            created_at=f"2026-09-04T10:00:{i:02d}Z"
        )
    
    attempts = await fetch_attempts(order_id)
    order = await fetch_order(order_id)
    events = await fetch_events(order_id)
    
    derived = calculate_derived_facts(order, events, attempts)
    
    assert derived["attempt_count"] == 3
    assert derived["retry_count"] == 2  # Retries = attempts - 1


@pytest.mark.asyncio
async def test_retry_count_and_gaps(setup_database):
    """Test retry count and gap calculations."""
    order_id = "test_order_retries"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-04T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    # First attempt at T+5s
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id="pay_1",
        method="upi",
        attempt_number=1,
        status="failed",
        created_at="2026-09-04T10:00:05Z"
    )
    
    # Second attempt at T+50s (45 second gap)
    await insert_payment_attempt(
        attempt_id="attempt_2",
        order_id=order_id,
        payment_id="pay_2",
        method="upi",
        attempt_number=2,
        status="captured",
        created_at="2026-09-04T10:00:50Z"
    )
    
    attempts = await fetch_attempts(order_id)
    order = await fetch_order(order_id)
    events = await fetch_events(order_id)
    
    derived = calculate_derived_facts(order, events, attempts)
    
    assert derived["retry_count"] == 1
    assert len(derived["retry_gaps_seconds"]) == 1
    assert derived["retry_gaps_seconds"][0] == 45.0


@pytest.mark.asyncio
async def test_duration_calculation(setup_database):
    """Test journey duration calculation."""
    order_id = "test_order_duration"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-04T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    # Event at start
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id="pay_1",
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-04T10:00:10Z"
    )
    
    # Event at end (70 seconds later)
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id="pay_1",
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-04T10:01:20Z"
    )
    
    events = await fetch_events(order_id)
    order = await fetch_order(order_id)
    attempts = await fetch_attempts(order_id)
    
    derived = calculate_derived_facts(order, events, attempts)
    
    assert derived["journey_duration_seconds"] == 70.0


@pytest.mark.asyncio
async def test_duration_calculation_helper():
    """Test the duration calculation helper function."""
    duration = calculate_duration_seconds(
        "2026-09-04T10:00:00Z",
        "2026-09-04T10:01:00Z"
    )
    assert duration == 60.0
    
    duration = calculate_duration_seconds(
        "2026-09-04T10:00:00Z",
        "2026-09-04T10:00:45Z"
    )
    assert duration == 45.0


@pytest.mark.asyncio
async def test_unknown_order(setup_database):
    """Test behavior when order doesn't exist."""
    journey = await reconstruct_journey("nonexistent_order")
    assert journey is None


@pytest.mark.asyncio
async def test_scenario_a_reconstruction():
    """Test full reconstruction of Scenario A (UPI retry after PIN error)."""
    await initialize_database()
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_a")
    
    assert journey is not None
    assert journey.order_id == "order_scenario_a"
    assert journey.attempt_count == 2
    assert journey.retry_count == 1
    assert journey.final_status == "captured"
    assert journey.event_count == 5
    
    # Verify events are ordered
    assert journey.events[0].event_type == "payment.initiated"
    assert journey.events[-1].event_type == "payment.captured"
    
    # Verify retry gap exists and is reasonable
    assert len(journey.retry_gaps_seconds) == 1
    assert journey.retry_gaps_seconds[0] > 0


@pytest.mark.asyncio
async def test_scenario_b_reconstruction():
    """Test full reconstruction of Scenario B (late authorization)."""
    await initialize_database()
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_b")
    
    assert journey is not None
    assert journey.order_id == "order_scenario_b"
    assert journey.attempt_count == 1
    assert journey.retry_count == 0
    assert journey.final_status == "captured"
    assert journey.event_count == 4
    
    # Verify no retry gaps for single attempt
    assert len(journey.retry_gaps_seconds) == 0


@pytest.mark.asyncio
async def test_evidence_classification():
    """Test that evidence is properly classified into categories."""
    await initialize_database()
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_a")
    
    # Should have evidence in all categories
    proven = [e for e in journey.evidence if e.category == "PROVEN"]
    derived = [e for e in journey.evidence if e.category == "DERIVED"]
    
    assert len(proven) > 0, "Should have PROVEN evidence"
    assert len(derived) > 0, "Should have DERIVED evidence"
    
    # Verify PROVEN evidence has sources
    for evidence in proven:
        assert evidence.source is not None


@pytest.mark.asyncio
async def test_inconsistency_detection():
    """Test detection of state inconsistencies."""
    await initialize_database()
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_b")
    
    # Scenario B has an inconsistency (order status = created, payment status = captured)
    inconsistencies = [e for e in journey.evidence if e.category == "INCONSISTENCY"]
    
    assert len(inconsistencies) > 0, "Scenario B should detect inconsistency"
    
    # Verify inconsistency mentions the conflict
    inconsistency_text = " ".join([e.statement for e in inconsistencies])
    assert "created" in inconsistency_text.lower()
    assert "captured" in inconsistency_text.lower()
