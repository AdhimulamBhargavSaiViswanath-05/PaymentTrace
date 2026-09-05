"""
Evidence classification service.

Classifies facts into four categories:
- PROVEN: Directly from database records
- DERIVED: Calculated deterministically from available data
- INCONSISTENCY: Conflicting information detected
- UNKNOWN: Gaps in available data
"""

from typing import List
from ..models import Order, PaymentEvent, PaymentAttempt, Evidence
from .integrity import (
    validate_state_transitions,
    detect_out_of_order_events,
    detect_duplicate_lifecycle_events,
    detect_missing_expected_events
)


def classify_evidence(order: Order, events: List[PaymentEvent],
                     attempts: List[PaymentAttempt], derived: dict) -> List[Evidence]:
    """
    Classify all available evidence into structured categories.

    This function does NOT generate natural language explanations.
    It only categorizes facts that can be proven, derived, or identified
    as inconsistent/unknown from the available data.

    Args:
        order: Order record
        events: List of payment events
        attempts: List of payment attempts
        derived: Dictionary of derived facts

    Returns:
        List of Evidence items
    """
    evidence_list = []

    # PROVEN facts - directly from database records
    evidence_list.append(Evidence(
        category="PROVEN",
        statement=f"Order {order.order_id} was created at {order.created_at}",
        source="orders.created_at"
    ))

    evidence_list.append(Evidence(
        category="PROVEN",
        statement=f"Order amount: {order.amount} {order.currency}",
        source="orders.amount"
    ))

    if order.merchant_status:
        evidence_list.append(Evidence(
            category="PROVEN",
            statement=f"Merchant order status: {order.merchant_status}",
            source="orders.merchant_status"
        ))

    # Events as proven facts
    for event in events:
        statement = f"Event '{event.event_type}' occurred at {event.timestamp}"
        if event.status:
            statement += f" with status '{event.status}'"
        if event.error_code:
            statement += f" (error: {event.error_code})"

        evidence_list.append(Evidence(
            category="PROVEN",
            statement=statement,
            source=f"payment_events.{event.event_id}"
        ))

    # Attempts as proven facts
    for attempt in attempts:
        evidence_list.append(Evidence(
            category="PROVEN",
            statement=f"Payment attempt {attempt.attempt_number} using {attempt.method} "
                     f"resulted in status '{attempt.status}' at {attempt.created_at}",
            source=f"payment_attempts.{attempt.attempt_id}"
        ))

    # DERIVED facts - calculated from available data
    evidence_list.append(Evidence(
        category="DERIVED",
        statement=f"Total payment attempts: {derived['attempt_count']}",
        source="calculated from payment_attempts count"
    ))

    evidence_list.append(Evidence(
        category="DERIVED",
        statement=f"Total events recorded: {derived['event_count']}",
        source="calculated from payment_events count"
    ))

    if derived['retry_count'] > 0:
        evidence_list.append(Evidence(
            category="DERIVED",
            statement=f"Number of retries: {derived['retry_count']}",
            source="calculated from attempt_count - 1"
        ))

        for i, gap in enumerate(derived['retry_gaps_seconds']):
            evidence_list.append(Evidence(
                category="DERIVED",
                statement=f"Time between attempt {i+1} and {i+2}: {gap:.2f} seconds",
                source="calculated from attempt timestamps"
            ))

    evidence_list.append(Evidence(
        category="DERIVED",
        statement=f"Journey duration: {derived['journey_duration_seconds']:.2f} seconds",
        source="calculated from first and last event timestamps"
    ))

    evidence_list.append(Evidence(
        category="DERIVED",
        statement=f"Final payment status: {derived['final_status']}",
        source="last attempt status or order status"
    ))

    # INCONSISTENCY detection - check for conflicting data
    if order.merchant_status and attempts:
        last_attempt_status = attempts[-1].status
        if order.merchant_status != last_attempt_status:
            evidence_list.append(Evidence(
                category="INCONSISTENCY",
                statement=f"Merchant order status '{order.merchant_status}' does not match "
                         f"last payment attempt status '{last_attempt_status}'",
                source="comparison: orders.merchant_status vs payment_attempts.status"
            ))

    # Check if any event status conflicts with attempt status
    for attempt in attempts:
        related_events = [e for e in events if e.payment_id == attempt.payment_id]
        for event in related_events:
            if event.status and event.status != attempt.status:
                evidence_list.append(Evidence(
                    category="INCONSISTENCY",
                    statement=f"Event status '{event.status}' for payment {event.payment_id} "
                             f"does not match attempt status '{attempt.status}'",
                    source=f"comparison: event {event.event_id} vs attempt {attempt.attempt_id}"
                ))

    # UNKNOWN - gaps in data
    if not events:
        evidence_list.append(Evidence(
            category="UNKNOWN",
            statement="No payment events are available in the data",
            source="payment_events table empty for this order"
        ))

    if not attempts:
        evidence_list.append(Evidence(
            category="UNKNOWN",
            statement="No payment attempt records are available",
            source="payment_attempts table empty for this order"
        ))

    # Check for error codes without details
    for event in events:
        if event.error_code and not event.metadata:
            evidence_list.append(Evidence(
                category="UNKNOWN",
                statement=f"Error code '{event.error_code}' recorded but no additional error details available",
                source=f"event {event.event_id}"
            ))

    # Phase 4A: State machine validation
    # Validate payment state transitions and detect lifecycle violations
    state_violations = validate_state_transitions(events, attempts)
    evidence_list.extend(state_violations)

    # Phase 4B: Out-of-order event detection
    # Detect logically invalid timestamp ordering
    ordering_violations = detect_out_of_order_events(events)
    evidence_list.extend(ordering_violations)

    # Phase 4C: Duplicate and missing event detection
    # Detect duplicate lifecycle events
    duplicate_violations = detect_duplicate_lifecycle_events(events)
    evidence_list.extend(duplicate_violations)

    # Detect missing expected lifecycle events (conservative)
    missing_event_findings = detect_missing_expected_events(events)
    evidence_list.extend(missing_event_findings)

    return evidence_list
