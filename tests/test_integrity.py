"""
Tests for payment journey integrity validation.

Phase 4A: State machine validation tests.
"""

import pytest
from backend.database import (
    initialize_database,
    clear_database,
    insert_order,
    insert_payment_attempt,
    insert_payment_event
)
from backend.services.reconstruction import reconstruct_journey
from backend.services.integrity import validate_state_transitions
from backend.fixtures.data import load_fixtures


@pytest.fixture
async def setup_database():
    """Setup clean database for each test."""
    await initialize_database()
    await clear_database()
    yield
    await clear_database()


@pytest.mark.asyncio
async def test_valid_payment_lifecycle_success(setup_database):
    """
    Test that a valid payment lifecycle (initiated → authorized → captured)
    does NOT produce state machine violations.
    """
    order_id = "test_valid_success"
    payment_id = "pay_valid_1"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Valid sequence: initiated → authorized → captured
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:12Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for state machine violations in evidence
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 0, \
        f"Valid lifecycle should not produce violations: {[v.statement for v in state_violations]}"


@pytest.mark.asyncio
async def test_valid_payment_lifecycle_failure(setup_database):
    """
    Test that a valid payment lifecycle (initiated → failed)
    does NOT produce state machine violations.
    """
    order_id = "test_valid_failure"
    payment_id = "pay_valid_2"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="upi",
        attempt_number=1,
        status="failed",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Valid sequence: initiated → failed
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.failed",
        status="failed",
        timestamp="2026-09-05T10:00:08Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for state machine violations
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 0, \
        f"Valid failure lifecycle should not produce violations: {[v.statement for v in state_violations]}"


@pytest.mark.asyncio
async def test_invalid_captured_without_authorized(setup_database):
    """
    Test detection of invalid transition: captured without prior authorization.
    """
    order_id = "test_invalid_captured"
    payment_id = "pay_invalid_1"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Invalid sequence: initiated → captured (missing authorized)
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for state machine violation
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 1
    assert "without prior payment.authorized" in state_violations[0].statement
    assert payment_id in state_violations[0].statement


@pytest.mark.asyncio
async def test_terminal_state_regression_captured_to_failed(setup_database):
    """
    Test detection of terminal state regression: captured → failed.
    """
    order_id = "test_regression_1"
    payment_id = "pay_regression_1"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Invalid sequence: initiated → authorized → captured → failed (regression)
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:12Z"
    )
    
    await insert_payment_event(
        event_id="event_4",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.failed",
        status="failed",
        timestamp="2026-09-05T10:00:20Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for state regression violation
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 1
    assert "State regression" in state_violations[0].statement
    assert "after payment.captured" in state_violations[0].statement


@pytest.mark.asyncio
async def test_terminal_state_regression_failed_to_captured(setup_database):
    """
    Test detection of terminal state regression: failed → captured.
    """
    order_id = "test_regression_2"
    payment_id = "pay_regression_2"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="upi",
        attempt_number=1,
        status="failed",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Invalid sequence: initiated → failed → authorized → captured (regression)
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.failed",
        status="failed",
        timestamp="2026-09-05T10:00:08Z"
    )
    
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:15Z"
    )
    
    await insert_payment_event(
        event_id="event_4",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:20Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for state regression violations
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    # Should detect 2 violations: authorized after failed, captured after failed
    assert len(state_violations) >= 2
    violations_text = " ".join([v.statement for v in state_violations])
    assert "after payment.failed" in violations_text


@pytest.mark.asyncio
async def test_empty_events_no_violations(setup_database):
    """
    Test that empty event list does not produce violations.
    """
    order_id = "test_empty"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    # No events, no attempts
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for state machine violations
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 0


@pytest.mark.asyncio
async def test_existing_scenario_a_no_violations(setup_database):
    """
    Test that existing Scenario A (valid retry flow) produces no state violations.
    """
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    # Scenario A has: fail → retry → success (all valid transitions)
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 0, \
        f"Scenario A should not produce state violations: {[v.statement for v in state_violations]}"


@pytest.mark.asyncio
async def test_existing_scenario_b_no_violations(setup_database):
    """
    Test that existing Scenario B (late authorization) produces no state violations.
    """
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_b")
    assert journey is not None
    
    # Scenario B has: initiated → authorized (delayed) → captured (all valid)
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 0, \
        f"Scenario B should not produce state violations: {[v.statement for v in state_violations]}"


@pytest.mark.asyncio
async def test_scenario_c_invalid_transition_detected(setup_database):
    """
    Test that Scenario C (captured without authorized) is correctly detected.
    """
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_c")
    assert journey is not None
    
    # Scenario C should produce exactly 1 state violation
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 1
    assert "without prior payment.authorized" in state_violations[0].statement
    assert "pay_c_invalid" in state_violations[0].statement


@pytest.mark.asyncio
async def test_integration_with_existing_evidence_pipeline(setup_database):
    """
    Test that state machine validation integrates cleanly with existing evidence.
    """
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    # Verify existing evidence categories still present
    proven = [e for e in journey.evidence if e.category == "PROVEN"]
    derived = [e for e in journey.evidence if e.category == "DERIVED"]
    
    assert len(proven) > 0, "PROVEN evidence should still exist"
    assert len(derived) > 0, "DERIVED evidence should still exist"
    
    # Verify evidence count is reasonable (not duplicated)
    total_evidence = len(journey.evidence)
    assert total_evidence > 0
    assert total_evidence < 100  # Sanity check - shouldn't explode


@pytest.mark.asyncio
async def test_webhook_events_do_not_affect_validation(setup_database):
    """
    Test that webhook.received events do not trigger state violations.
    """
    order_id = "test_webhook"
    payment_id = "pay_webhook"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Valid sequence with webhook
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:12Z"
    )
    
    await insert_payment_event(
        event_id="event_4",
        order_id=order_id,
        payment_id=payment_id,
        event_type="webhook.received",
        status="captured",
        timestamp="2026-09-05T10:00:15Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Webhooks should not cause violations
    state_violations = [e for e in journey.evidence if 
                       e.category == "INCONSISTENCY" and 
                       "state_machine_validation" in (e.source or "")]
    
    assert len(state_violations) == 0


# ============================================================================
# Phase 4B: Out-of-Order Event Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_valid_event_ordering(setup_database):
    """
    Test that properly ordered events (initiated → authorized → captured)
    do NOT produce out-of-order violations.
    """
    order_id = "test_valid_ordering"
    payment_id = "pay_ordered_1"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Properly ordered: initiated (10:00:05) → authorized (10:00:10) → captured (10:00:15)
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:15Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for out-of-order violations
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) == 0, \
        f"Valid ordering should not produce violations: {[v.statement for v in ordering_violations]}"


@pytest.mark.asyncio
async def test_authorized_before_initiated(setup_database):
    """
    Test detection of authorized event occurring before initiated event.
    """
    order_id = "test_auth_before_init"
    payment_id = "pay_outoforder_1"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="authorized",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Out of order: authorized (10:00:05) BEFORE initiated (10:00:10)
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for out-of-order violation
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) == 1
    assert "authorized" in ordering_violations[0].statement.lower()
    assert "before" in ordering_violations[0].statement.lower()
    assert "initiated" in ordering_violations[0].statement.lower()


@pytest.mark.asyncio
async def test_captured_before_authorized(setup_database):
    """
    Test detection of captured event occurring before authorized event.
    """
    order_id = "test_cap_before_auth"
    payment_id = "pay_outoforder_2"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Out of order: captured (10:00:08) BEFORE authorized (10:00:10)
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:08Z"
    )
    
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for out-of-order violation
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) >= 1
    violations_text = " ".join([v.statement for v in ordering_violations])
    assert "captured" in violations_text.lower()
    assert "before" in violations_text.lower()


@pytest.mark.asyncio
async def test_captured_before_initiated(setup_database):
    """
    Test detection of captured event occurring before initiated event.
    """
    order_id = "test_cap_before_init"
    payment_id = "pay_outoforder_3"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Out of order: captured (10:00:05) BEFORE initiated (10:00:10)
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:12Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Check for out-of-order violation
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) >= 1
    violations_text = " ".join([v.statement for v in ordering_violations])
    assert "captured" in violations_text.lower()
    assert "before" in violations_text.lower()


@pytest.mark.asyncio
async def test_webhook_does_not_create_out_of_order_violation(setup_database):
    """
    Test that webhook events do not trigger out-of-order violations.
    """
    order_id = "test_webhook_ordering"
    payment_id = "pay_webhook_1"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id,
        method="card",
        attempt_number=1,
        status="captured",
        created_at="2026-09-05T10:00:05Z"
    )
    
    # Valid ordering with webhook in between
    await insert_payment_event(
        event_id="event_1",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2",
        order_id=order_id,
        payment_id=payment_id,
        event_type="webhook.received",
        status="created",
        timestamp="2026-09-05T10:00:08Z"
    )
    
    await insert_payment_event(
        event_id="event_3",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:00:10Z"
    )
    
    await insert_payment_event(
        event_id="event_4",
        order_id=order_id,
        payment_id=payment_id,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:00:15Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Webhook should not cause out-of-order violations
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) == 0


@pytest.mark.asyncio
async def test_multiple_payment_ids_validated_independently(setup_database):
    """
    Test that out-of-order detection validates each payment_id independently.
    """
    order_id = "test_multi_payment"
    payment_id_1 = "pay_multi_1"
    payment_id_2 = "pay_multi_2"
    
    await insert_order(
        order_id=order_id,
        created_at="2026-09-05T10:00:00Z",
        amount=1000,
        currency="INR"
    )
    
    # Attempt 1 - valid ordering
    await insert_payment_attempt(
        attempt_id="attempt_1",
        order_id=order_id,
        payment_id=payment_id_1,
        method="upi",
        attempt_number=1,
        status="failed",
        created_at="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_1_1",
        order_id=order_id,
        payment_id=payment_id_1,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:00:05Z"
    )
    
    await insert_payment_event(
        event_id="event_1_2",
        order_id=order_id,
        payment_id=payment_id_1,
        event_type="payment.failed",
        status="failed",
        timestamp="2026-09-05T10:00:08Z"
    )
    
    # Attempt 2 - out of order (authorized before initiated)
    await insert_payment_attempt(
        attempt_id="attempt_2",
        order_id=order_id,
        payment_id=payment_id_2,
        method="upi",
        attempt_number=2,
        status="captured",
        created_at="2026-09-05T10:01:00Z"
    )
    
    await insert_payment_event(
        event_id="event_2_1",
        order_id=order_id,
        payment_id=payment_id_2,
        event_type="payment.authorized",
        status="authorized",
        timestamp="2026-09-05T10:01:00Z"
    )
    
    await insert_payment_event(
        event_id="event_2_2",
        order_id=order_id,
        payment_id=payment_id_2,
        event_type="payment.initiated",
        status="created",
        timestamp="2026-09-05T10:01:05Z"
    )
    
    await insert_payment_event(
        event_id="event_2_3",
        order_id=order_id,
        payment_id=payment_id_2,
        event_type="payment.captured",
        status="captured",
        timestamp="2026-09-05T10:01:10Z"
    )
    
    # Reconstruct journey
    journey = await reconstruct_journey(order_id)
    assert journey is not None
    
    # Should detect out-of-order only for payment_id_2
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) == 1
    assert payment_id_2 in ordering_violations[0].statement


@pytest.mark.asyncio
async def test_existing_scenario_a_no_out_of_order_violations(setup_database):
    """
    Test that existing Scenario A has no out-of-order violations.
    """
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_a")
    assert journey is not None
    
    # Scenario A has valid ordering in both attempts
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) == 0, \
        f"Scenario A should not have ordering violations: {[v.statement for v in ordering_violations]}"


@pytest.mark.asyncio
async def test_existing_scenario_b_no_out_of_order_violations(setup_database):
    """
    Test that existing Scenario B has no out-of-order violations.
    """
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_b")
    assert journey is not None
    
    # Scenario B has valid ordering (though delayed)
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) == 0, \
        f"Scenario B should not have ordering violations: {[v.statement for v in ordering_violations]}"


@pytest.mark.asyncio
async def test_scenario_e_detects_out_of_order_event(setup_database):
    """
    Test that Scenario E (authorized before initiated) is correctly detected.
    """
    await load_fixtures()
    
    journey = await reconstruct_journey("order_scenario_e")
    assert journey is not None
    
    # Scenario E should produce out-of-order violation
    ordering_violations = [e for e in journey.evidence if 
                          e.category == "INCONSISTENCY" and 
                          "out_of_order_detection" in (e.source or "")]
    
    assert len(ordering_violations) >= 1
    violations_text = " ".join([v.statement for v in ordering_violations])
    assert "authorized" in violations_text.lower()
    assert "before" in violations_text.lower()
    assert "initiated" in violations_text.lower()
