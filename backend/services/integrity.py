"""
Payment journey integrity validation service.

This module performs deterministic state-machine validation to detect
clearly invalid payment lifecycle transitions.

Phase 4A: State Machine Validation Only
"""

from typing import List, Dict, Set
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
