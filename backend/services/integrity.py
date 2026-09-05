"""
Payment journey integrity validation service.

This module performs deterministic state-machine validation to detect
clearly invalid payment lifecycle transitions.

Phase 4A: State Machine Validation
Phase 4B: Out-of-Order Event Detection
Phase 4C: Duplicate and Missing Event Detection
Phase 4D: Timeline Gap / Timing Anomaly Detection
"""

from typing import List, Dict, Set, Optional
from datetime import datetime
from ..models import PaymentEvent, PaymentAttempt, Evidence


# ============================================================================
# Phase 4D: Timeline Gap Detection Thresholds
# ============================================================================
# These are conservative informational thresholds designed to identify
# suspicious timing patterns without generating false positives.
# All Phase 4D findings are classified as UNKNOWN (not INCONSISTENCY)
# because timing anomalies do not necessarily indicate payment failure.

THRESHOLD_INIT_TO_AUTH_SECONDS = 90  # Scenario B has valid 45s gap
THRESHOLD_AUTH_TO_CAPTURE_SECONDS = 45  # Most captures happen within 10s
THRESHOLD_NEAR_ZERO_MS = 50  # Sub-50ms may indicate timestamp precision issues


def validate_state_transitions(events: List[PaymentEvent],
                               attempts: List[PaymentAttempt]) -> List[Evidence]:
    """
    Validate payment state transitions against expected lifecycle rules.

    Based on the repository's actual event types and statuses:
    - Event types: payment.initiated, payment.authorized, payment.captured,
                   payment.failed, webhook.received
    - Statuses: created, authorized, captured, failed

    Valid lifecycle flows:
    1. initiated (created) → authorized → captured (terminal success)
    2. initiated (created) → failed (terminal failure)
    3. authorized → captured (if initiation was not recorded)

    Invalid transitions detected:
    - captured without prior authorized for same payment_id
    - Terminal state regression (captured/failed → earlier states)

    Args:
        events: List of payment events (already sorted by timestamp)
        attempts: List of payment attempts

    Returns:
        List of Evidence items with category INCONSISTENCY for violations
    """
    violations = []

    if not events:
        return violations

    # Group events by payment_id
    events_by_payment: Dict[str, List[PaymentEvent]] = {}
    for event in events:
        if event.payment_id:
            if event.payment_id not in events_by_payment:
                events_by_payment[event.payment_id] = []
            events_by_payment[event.payment_id].append(event)

    # Validate each payment_id's state transitions
    for payment_id, payment_events in events_by_payment.items():
        payment_violations = _validate_payment_lifecycle(payment_id, payment_events)
        violations.extend(payment_violations)

    return violations


def _validate_payment_lifecycle(payment_id: str,
                                events: List[PaymentEvent]) -> List[Evidence]:
    """
    Validate lifecycle for a single payment_id.

    Args:
        payment_id: Payment identifier
        events: List of events for this payment (already sorted by timestamp)

    Returns:
        List of Evidence items for violations
    """
    violations = []

    # Track state progression
    has_initiated = False
    has_authorized = False
    has_captured = False
    has_failed = False

    for i, event in enumerate(events):
        event_type = event.event_type
        status = event.status

        # Track state flags
        if event_type == "payment.initiated" and status == "created":
            has_initiated = True

            # Check for terminal state regression
            if has_captured:
                violations.append(Evidence(
                    category="INCONSISTENCY",
                    statement=f"Payment {payment_id}: State regression detected - "
                             f"payment.initiated (created) occurred at {event.timestamp} "
                             f"after payment.captured (terminal success state)",
                    source=f"state_machine_validation: event {event.event_id}"
                ))
            if has_failed:
                violations.append(Evidence(
                    category="INCONSISTENCY",
                    statement=f"Payment {payment_id}: State regression detected - "
                             f"payment.initiated (created) occurred at {event.timestamp} "
                             f"after payment.failed (terminal failure state)",
                    source=f"state_machine_validation: event {event.event_id}"
                ))

        elif event_type == "payment.authorized" and status == "authorized":
            has_authorized = True

            # Check for terminal state regression
            if has_captured:
                violations.append(Evidence(
                    category="INCONSISTENCY",
                    statement=f"Payment {payment_id}: State regression detected - "
                             f"payment.authorized occurred at {event.timestamp} "
                             f"after payment.captured (terminal success state)",
                    source=f"state_machine_validation: event {event.event_id}"
                ))
            if has_failed:
                violations.append(Evidence(
                    category="INCONSISTENCY",
                    statement=f"Payment {payment_id}: State regression detected - "
                             f"payment.authorized occurred at {event.timestamp} "
                             f"after payment.failed (terminal failure state)",
                    source=f"state_machine_validation: event {event.event_id}"
                ))

        elif event_type == "payment.captured" and status == "captured":
            # Check for missing authorization
            if not has_authorized:
                violations.append(Evidence(
                    category="INCONSISTENCY",
                    statement=f"Payment {payment_id}: Invalid state transition - "
                             f"payment.captured occurred at {event.timestamp} "
                             f"without prior payment.authorized event",
                    source=f"state_machine_validation: event {event.event_id}"
                ))

            # Check for terminal state regression (captured again after failed)
            if has_failed:
                violations.append(Evidence(
                    category="INCONSISTENCY",
                    statement=f"Payment {payment_id}: State regression detected - "
                             f"payment.captured occurred at {event.timestamp} "
                             f"after payment.failed (terminal failure state)",
                    source=f"state_machine_validation: event {event.event_id}"
                ))

            has_captured = True

        elif event_type == "payment.failed" and status == "failed":
            # Check for terminal state regression (failed after captured)
            if has_captured:
                violations.append(Evidence(
                    category="INCONSISTENCY",
                    statement=f"Payment {payment_id}: State regression detected - "
                             f"payment.failed occurred at {event.timestamp} "
                             f"after payment.captured (terminal success state)",
                    source=f"state_machine_validation: event {event.event_id}"
                ))

            has_failed = True

        # webhook.received is informational and does not affect state validation

    return violations


def detect_out_of_order_events(events: List[PaymentEvent]) -> List[Evidence]:
    """
    Detect logically out-of-order payment events based on timestamps.

    Phase 4B: Out-of-Order Event Detection

    While events are sorted chronologically for display, this function detects
    when the logical lifecycle order is violated by timestamp inconsistencies.

    Expected logical order for a payment lifecycle:
    1. payment.initiated (first)
    2. payment.authorized (after initiated)
    3. payment.captured (after authorized)

    Or failure path:
    1. payment.initiated (first)
    2. payment.failed (terminal)

    Violations detected:
    - authorized timestamp < initiated timestamp
    - captured timestamp < initiated timestamp
    - captured timestamp < authorized timestamp
    - Any lifecycle event after terminal state (captured/failed)

    Webhook events (webhook.received) are ignored for ordering validation.

    Args:
        events: List of payment events (already sorted by timestamp)

    Returns:
        List of Evidence items with category INCONSISTENCY for violations
    """
    violations = []

    if not events:
        return violations

    # Group events by payment_id
    events_by_payment: Dict[str, List[PaymentEvent]] = {}
    for event in events:
        if event.payment_id:
            if event.payment_id not in events_by_payment:
                events_by_payment[event.payment_id] = []
            events_by_payment[event.payment_id].append(event)

    # Validate each payment_id's event ordering
    for payment_id, payment_events in events_by_payment.items():
        payment_violations = _validate_event_ordering(payment_id, payment_events)
        violations.extend(payment_violations)

    return violations


def _validate_event_ordering(payment_id: str,
                             events: List[PaymentEvent]) -> List[Evidence]:
    """
    Validate timestamp ordering for a single payment_id.

    Args:
        payment_id: Payment identifier
        events: List of events for this payment (already sorted by timestamp)

    Returns:
        List of Evidence items for ordering violations
    """
    violations = []

    # Track timestamps for lifecycle events (ignore webhooks)
    initiated_timestamp: Optional[str] = None
    authorized_timestamp: Optional[str] = None
    captured_timestamp: Optional[str] = None
    failed_timestamp: Optional[str] = None

    initiated_event_id: Optional[str] = None
    authorized_event_id: Optional[str] = None
    captured_event_id: Optional[str] = None
    failed_event_id: Optional[str] = None

    # First pass: collect all event timestamps
    for event in events:
        event_type = event.event_type
        status = event.status

        if event_type == "payment.initiated" and status == "created":
            initiated_timestamp = event.timestamp
            initiated_event_id = event.event_id

        elif event_type == "payment.authorized" and status == "authorized":
            authorized_timestamp = event.timestamp
            authorized_event_id = event.event_id

        elif event_type == "payment.captured" and status == "captured":
            captured_timestamp = event.timestamp
            captured_event_id = event.event_id

        elif event_type == "payment.failed" and status == "failed":
            failed_timestamp = event.timestamp
            failed_event_id = event.event_id

    # Second pass: validate ordering
    # Check: authorized should not occur before initiated
    if initiated_timestamp and authorized_timestamp:
        if _timestamp_before(authorized_timestamp, initiated_timestamp):
            violations.append(Evidence(
                category="INCONSISTENCY",
                statement=f"Payment {payment_id}: Out-of-order events detected - "
                         f"payment.authorized (at {authorized_timestamp}) occurred before "
                         f"payment.initiated (at {initiated_timestamp})",
                source=f"out_of_order_detection: events {authorized_event_id} vs {initiated_event_id}"
            ))

    # Check: captured should not occur before initiated
    if initiated_timestamp and captured_timestamp:
        if _timestamp_before(captured_timestamp, initiated_timestamp):
            violations.append(Evidence(
                category="INCONSISTENCY",
                statement=f"Payment {payment_id}: Out-of-order events detected - "
                         f"payment.captured (at {captured_timestamp}) occurred before "
                         f"payment.initiated (at {initiated_timestamp})",
                source=f"out_of_order_detection: events {captured_event_id} vs {initiated_event_id}"
            ))

    # Check: captured should not occur before authorized
    if authorized_timestamp and captured_timestamp:
        if _timestamp_before(captured_timestamp, authorized_timestamp):
            violations.append(Evidence(
                category="INCONSISTENCY",
                statement=f"Payment {payment_id}: Out-of-order events detected - "
                         f"payment.captured (at {captured_timestamp}) occurred before "
                         f"payment.authorized (at {authorized_timestamp})",
                source=f"out_of_order_detection: events {captured_event_id} vs {authorized_event_id}"
            ))

    # Check: failed should not occur before initiated
    if initiated_timestamp and failed_timestamp:
        if _timestamp_before(failed_timestamp, initiated_timestamp):
            violations.append(Evidence(
                category="INCONSISTENCY",
                statement=f"Payment {payment_id}: Out-of-order events detected - "
                         f"payment.failed (at {failed_timestamp}) occurred before "
                         f"payment.initiated (at {initiated_timestamp})",
                source=f"out_of_order_detection: events {failed_event_id} vs {initiated_event_id}"
            ))

    return violations


def _timestamp_before(ts1: str, ts2: str) -> bool:
    """
    Check if timestamp ts1 is before timestamp ts2.

    Args:
        ts1: First timestamp (ISO format)
        ts2: Second timestamp (ISO format)

    Returns:
        True if ts1 < ts2, False otherwise
    """
    try:
        dt1 = datetime.fromisoformat(ts1.replace('Z', '+00:00'))
        dt2 = datetime.fromisoformat(ts2.replace('Z', '+00:00'))
        return dt1 < dt2
    except Exception:
        # If parsing fails, assume no ordering violation
        return False


def detect_duplicate_lifecycle_events(events: List[PaymentEvent]) -> List[Evidence]:
    """
    Detect duplicate lifecycle events for the same payment_id.

    Phase 4C: Duplicate Event Detection

    A duplicate is defined as multiple occurrences of the same lifecycle event type
    for the same payment_id. For example:
    - Two payment.initiated events
    - Two payment.authorized events
    - Two payment.captured events
    - Two payment.failed events

    Webhook events (webhook.received) are excluded from duplicate detection as they
    are informational and multiple webhooks may be legitimately sent.

    Args:
        events: List of payment events (already sorted by timestamp)

    Returns:
        List of Evidence items with category INCONSISTENCY for duplicates
    """
    violations = []

    if not events:
        return violations

    # Group events by payment_id
    events_by_payment: Dict[str, List[PaymentEvent]] = {}
    for event in events:
        if event.payment_id:
            if event.payment_id not in events_by_payment:
                events_by_payment[event.payment_id] = []
            events_by_payment[event.payment_id].append(event)

    # Check each payment_id for duplicates
    for payment_id, payment_events in events_by_payment.items():
        payment_violations = _detect_duplicate_events_for_payment(payment_id, payment_events)
        violations.extend(payment_violations)

    return violations


def _detect_duplicate_events_for_payment(payment_id: str,
                                         events: List[PaymentEvent]) -> List[Evidence]:
    """
    Detect duplicate lifecycle events for a single payment_id.

    Args:
        payment_id: Payment identifier
        events: List of events for this payment

    Returns:
        List of Evidence items for duplicates
    """
    violations = []

    # Track lifecycle event occurrences (excluding webhooks)
    lifecycle_events = {
        'payment.initiated': [],
        'payment.authorized': [],
        'payment.captured': [],
        'payment.failed': []
    }

    for event in events:
        event_type = event.event_type

        # Only track lifecycle events (exclude webhooks)
        if event_type in lifecycle_events:
            lifecycle_events[event_type].append(event)

    # Check for duplicates
    for event_type, event_list in lifecycle_events.items():
        if len(event_list) > 1:
            # Multiple occurrences detected
            timestamps = [e.timestamp for e in event_list]
            event_ids = [e.event_id for e in event_list]

            violations.append(Evidence(
                category="INCONSISTENCY",
                statement=f"Payment {payment_id}: Duplicate lifecycle event detected - "
                         f"{event_type} occurred {len(event_list)} times "
                         f"(at {', '.join(timestamps)})",
                source=f"duplicate_detection: events {', '.join(event_ids)}"
            ))

    return violations


def detect_missing_expected_events(events: List[PaymentEvent]) -> List[Evidence]:
    """
    Detect missing expected lifecycle events in available data.

    Phase 4C: Missing Event Detection (Conservative)

    This function identifies when expected lifecycle events are absent from the
    available data. It is conservative and does NOT claim that events "never occurred",
    only that they are not present in the available records.

    Expected patterns:
    - If payment.captured exists, payment.authorized is expected
    - If payment.authorized exists, payment.initiated is expected

    Missing events are flagged as UNKNOWN (not INCONSISTENCY) because we cannot
    definitively prove the event never occurred - it may simply not be in our data.

    Note: Phase 4A already detects "captured without authorized" as an INCONSISTENCY
    because that violates the payment state machine. This function provides additional
    context about missing events without duplicating that violation.

    Webhook events (webhook.received) are excluded as they are not part of the
    payment lifecycle state machine.

    Args:
        events: List of payment events (already sorted by timestamp)

    Returns:
        List of Evidence items with category UNKNOWN for missing events
    """
    findings = []

    if not events:
        return findings

    # Group events by payment_id
    events_by_payment: Dict[str, List[PaymentEvent]] = {}
    for event in events:
        if event.payment_id:
            if event.payment_id not in events_by_payment:
                events_by_payment[event.payment_id] = []
            events_by_payment[event.payment_id].append(event)

    # Check each payment_id for missing events
    for payment_id, payment_events in events_by_payment.items():
        payment_findings = _detect_missing_events_for_payment(payment_id, payment_events)
        findings.extend(payment_findings)

    return findings


def _detect_missing_events_for_payment(payment_id: str,
                                       events: List[PaymentEvent]) -> List[Evidence]:
    """
    Detect missing expected events for a single payment_id.

    Args:
        payment_id: Payment identifier
        events: List of events for this payment

    Returns:
        List of Evidence items for missing events (UNKNOWN category)
    """
    findings = []

    # Track which lifecycle events are present
    has_initiated = False
    has_authorized = False
    has_captured = False
    has_failed = False

    for event in events:
        event_type = event.event_type
        status = event.status

        if event_type == "payment.initiated" and status == "created":
            has_initiated = True
        elif event_type == "payment.authorized" and status == "authorized":
            has_authorized = True
        elif event_type == "payment.captured" and status == "captured":
            has_captured = True
        elif event_type == "payment.failed" and status == "failed":
            has_failed = True

    # Check for missing events (conservative approach)
    # Note: We only flag as UNKNOWN, not INCONSISTENCY

    # If authorized exists but initiated is missing
    if has_authorized and not has_initiated:
        findings.append(Evidence(
            category="UNKNOWN",
            statement=f"Payment {payment_id}: payment.initiated event not found in available data, "
                     f"though payment.authorized is present",
            source="missing_event_detection: payment.initiated"
        ))

    # If captured exists but initiated is missing (and we haven't already flagged it above)
    if has_captured and not has_initiated and not has_authorized:
        findings.append(Evidence(
            category="UNKNOWN",
            statement=f"Payment {payment_id}: payment.initiated event not found in available data, "
                     f"though payment.captured is present",
            source="missing_event_detection: payment.initiated"
        ))

    # If failed exists but initiated is missing
    if has_failed and not has_initiated:
        findings.append(Evidence(
            category="UNKNOWN",
            statement=f"Payment {payment_id}: payment.initiated event not found in available data, "
                     f"though payment.failed is present",
            source="missing_event_detection: payment.initiated"
        ))

    return findings


# ============================================================================
# Phase 4D: Timeline Gap / Timing Anomaly Detection
# ============================================================================

def detect_timeline_gaps(events: List[PaymentEvent],
                        attempts: List[PaymentAttempt]) -> List[Evidence]:
    """
    Detect suspicious timeline gaps and timing anomalies in payment lifecycle.

    Phase 4D: Timeline Gap Detection

    This function identifies unusually long or suspiciously short gaps between
    payment lifecycle events. All findings are classified as UNKNOWN because
    timing anomalies do not necessarily indicate payment failure.

    Detection rules:
    1. Initiated → Authorized > 90 seconds: May indicate authorization delays
    2. Authorized → Captured > 45 seconds: May indicate processing delays
    3. Consecutive lifecycle events < 50ms: May indicate timestamp precision issues

    Webhooks (webhook.received) are excluded from timing analysis.

    Args:
        events: List of payment events (already sorted by timestamp)
        attempts: List of payment attempts (included for consistency with Phase 4 API)

    Returns:
        List of Evidence items with category UNKNOWN for timing anomalies
    """
    findings = []

    if not events:
        return findings

    # Group events by payment_id
    events_by_payment: Dict[str, List[PaymentEvent]] = {}
    for event in events:
        if event.payment_id:
            if event.payment_id not in events_by_payment:
                events_by_payment[event.payment_id] = []
            events_by_payment[event.payment_id].append(event)

    # Detect gaps for each payment_id
    for payment_id, payment_events in events_by_payment.items():
        payment_findings = _detect_gaps_for_payment(payment_id, payment_events)
        findings.extend(payment_findings)

    return findings


def _detect_gaps_for_payment(payment_id: str,
                             events: List[PaymentEvent]) -> List[Evidence]:
    """
    Detect timing anomalies for a single payment_id.

    Args:
        payment_id: Payment identifier
        events: List of events for this payment (already sorted by timestamp)

    Returns:
        List of Evidence items for timing anomalies
    """
    findings = []

    # Extract lifecycle events (exclude webhooks)
    lifecycle_events = []
    for event in events:
        if event.event_type in ['payment.initiated', 'payment.authorized',
                               'payment.captured', 'payment.failed']:
            lifecycle_events.append(event)

    if not lifecycle_events:
        return findings

    # Track first occurrence of each lifecycle event type
    initiated_event: Optional[PaymentEvent] = None
    authorized_event: Optional[PaymentEvent] = None
    captured_event: Optional[PaymentEvent] = None
    failed_event: Optional[PaymentEvent] = None

    for event in lifecycle_events:
        event_type = event.event_type
        status = event.status

        if event_type == "payment.initiated" and status == "created" and not initiated_event:
            initiated_event = event
        elif event_type == "payment.authorized" and status == "authorized" and not authorized_event:
            authorized_event = event
        elif event_type == "payment.captured" and status == "captured" and not captured_event:
            captured_event = event
        elif event_type == "payment.failed" and status == "failed" and not failed_event:
            failed_event = event

    # Rule 1: Initiated → Authorized gap > 90 seconds
    if initiated_event and authorized_event:
        gap_seconds = _calculate_gap_seconds(initiated_event.timestamp, authorized_event.timestamp)
        if gap_seconds > THRESHOLD_INIT_TO_AUTH_SECONDS:
            findings.append(Evidence(
                category="UNKNOWN",
                statement=f"Payment {payment_id}: Unusually long gap ({gap_seconds:.1f}s) detected "
                         f"between payment.initiated (at {initiated_event.timestamp}) and "
                         f"payment.authorized (at {authorized_event.timestamp}). This may indicate "
                         f"an authorization delay, but does not necessarily indicate a payment failure.",
                source="timeline_gap_detection: initiated_to_authorized"
            ))

    # Rule 2: Authorized → Captured gap > 45 seconds
    if authorized_event and captured_event:
        gap_seconds = _calculate_gap_seconds(authorized_event.timestamp, captured_event.timestamp)
        if gap_seconds > THRESHOLD_AUTH_TO_CAPTURE_SECONDS:
            findings.append(Evidence(
                category="UNKNOWN",
                statement=f"Payment {payment_id}: Unusually long gap ({gap_seconds:.1f}s) detected "
                         f"between payment.authorized (at {authorized_event.timestamp}) and "
                         f"payment.captured (at {captured_event.timestamp}). This may indicate "
                         f"a processing or capture delay, but does not necessarily indicate a payment failure.",
                source="timeline_gap_detection: authorized_to_captured"
            ))

    # Rule 3: Near-zero gaps (< 50ms) between consecutive lifecycle events
    for i in range(1, len(lifecycle_events)):
        prev_event = lifecycle_events[i - 1]
        curr_event = lifecycle_events[i]

        gap_ms = _calculate_gap_milliseconds(prev_event.timestamp, curr_event.timestamp)

        # Only flag positive gaps less than 50ms (avoid negative gaps from out-of-order events)
        if 0 < gap_ms < THRESHOLD_NEAR_ZERO_MS:
            findings.append(Evidence(
                category="UNKNOWN",
                statement=f"Payment {payment_id}: Near-zero gap ({gap_ms:.1f}ms) detected "
                         f"between {prev_event.event_type} and {curr_event.event_type}. "
                         f"This may indicate timestamp precision or synchronization behavior "
                         f"and does not necessarily indicate a payment issue.",
                source="timeline_gap_detection: near_zero_gap"
            ))

    return findings


def _calculate_gap_seconds(ts1: str, ts2: str) -> float:
    """
    Calculate gap in seconds between two timestamps.

    Args:
        ts1: First timestamp (ISO format)
        ts2: Second timestamp (ISO format)

    Returns:
        Gap in seconds (positive if ts2 > ts1)
    """
    try:
        dt1 = datetime.fromisoformat(ts1.replace('Z', '+00:00'))
        dt2 = datetime.fromisoformat(ts2.replace('Z', '+00:00'))
        return (dt2 - dt1).total_seconds()
    except Exception:
        return 0.0


def _calculate_gap_milliseconds(ts1: str, ts2: str) -> float:
    """
    Calculate gap in milliseconds between two timestamps.

    Args:
        ts1: First timestamp (ISO format)
        ts2: Second timestamp (ISO format)

    Returns:
        Gap in milliseconds (positive if ts2 > ts1)
    """
    try:
        dt1 = datetime.fromisoformat(ts1.replace('Z', '+00:00'))
        dt2 = datetime.fromisoformat(ts2.replace('Z', '+00:00'))
        return (dt2 - dt1).total_seconds() * 1000
    except Exception:
        return 0.0
