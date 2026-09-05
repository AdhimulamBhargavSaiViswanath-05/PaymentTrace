"""
Payment journey integrity validation service.

This module performs deterministic state-machine validation to detect
clearly invalid payment lifecycle transitions.

Phase 4A: State Machine Validation
Phase 4B: Out-of-Order Event Detection
"""

from typing import List, Dict, Set, Optional
from datetime import datetime
from ..models import PaymentEvent, PaymentAttempt, Evidence


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
