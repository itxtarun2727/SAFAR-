"""
workflow.py — Deterministic State Machine for Instrument & Release Lifecycles.

SINGLE SOURCE OF TRUTH:
All instrument state transitions MUST be evaluated through transition().
No SQL UPDATE should alter instrument.status directly.
"""

from typing import Tuple, List, Dict, Any, Callable


class WorkflowError(Exception):
    """Raised when an illegal transition or unmet guard is encountered."""
    pass


# ── Allowed States ─────────────────────────────────────────────────────────────

NORMAL_STATES = {
    "SUBMITTED",
    "BANK_CHECK",
    "ACTIVE",
    "RELEASE_REQUESTED",
    "COMPLIANCE_CHECK",
    "APPROVED",
    "BANK_RELEASE_PENDING",
    "CLOSED",
}

EXCEPTION_STATES = {
    "REJECTED",
    "RENEWAL_PENDING",
    "DISPUTED",
}

ALL_STATES = NORMAL_STATES | EXCEPTION_STATES


# ── Guard Functions ────────────────────────────────────────────────────────────

def guard_required_fields_present(context: Dict[str, Any]) -> bool:
    """Ensure essential instrument fields exist."""
    instrument = context.get("instrument")
    if not instrument:
        return False
    return bool(instrument.reference_no and instrument.amount_paise > 0 and instrument.maturity_date)


def guard_bank_checker_differs(context: Dict[str, Any]) -> bool:
    """Enforce separation between bank maker and bank checker."""
    actor_id = context.get("actor_id")
    maker_id = context.get("bank_maker_id")
    if maker_id and actor_id and maker_id == actor_id:
        raise WorkflowError("Bank Checker must be a different individual from Bank Maker.")
    return True


def guard_no_open_dispute(context: Dict[str, Any]) -> bool:
    """Release is strictly blocked if any active dispute or legal hold exists."""
    has_dispute = context.get("has_active_dispute", False)
    if has_dispute:
        raise WorkflowError("Release is blocked: an active dispute or compliance hold is open.")
    return True


def guard_maker_differs_from_checker(context: Dict[str, Any]) -> bool:
    """Enforce maker != checker on AICTE release approvals."""
    maker_id = context.get("maker_id")
    checker_id = context.get("actor_id")
    if maker_id and checker_id and maker_id == checker_id:
        raise WorkflowError("AICTE Senior Checker must be a different person from Officer Maker.")
    return True


def guard_checklist_cleared(context: Dict[str, Any]) -> bool:
    """Ensure all required pre-release checklist clearances are satisfied."""
    checklist = context.get("checklist", {})
    if not checklist:
        return False
    # All items in clearance checklist must be true
    return all(checklist.values())


def guard_reason_provided(context: Dict[str, Any]) -> bool:
    """Ensure a written audit reason is attached."""
    reason = context.get("reason")
    if not reason or not reason.strip():
        raise WorkflowError("A specific operational reason must be recorded for this action.")
    return True


# ── Transition Table ───────────────────────────────────────────────────────────
# Format: (from_state, event) -> (to_state, list of guard functions, list of effect labels)

TRANSITIONS: Dict[Tuple[str, str], Tuple[str, List[Callable], List[str]]] = {
    # 1. Submission -> Bank check
    ("SUBMITTED", "send_to_bank"): (
        "BANK_CHECK",
        [guard_required_fields_present],
        ["notify_bank_adapter"]
    ),

    # 2. Bank check -> Active (confirmation match)
    ("BANK_CHECK", "bank_confirms"): (
        "ACTIVE",
        [guard_bank_checker_differs],
        ["mark_lien_active", "record_bank_match"]
    ),

    # 3. Bank check -> Rejected
    ("BANK_CHECK", "bank_rejects"): (
        "REJECTED",
        [guard_reason_provided],
        ["notify_institution_deficiency"]
    ),

    # 4. Rejected -> Resubmit
    ("REJECTED", "resubmit"): (
        "SUBMITTED",
        [guard_required_fields_present],
        ["clear_previous_mismatches"]
    ),

    # 5. Active -> Renewal Pending
    ("ACTIVE", "renewal_detected"): (
        "RENEWAL_PENDING",
        [],
        ["queue_renewal_inspection"]
    ),

    # 6. Renewal Pending -> Bank Check
    ("RENEWAL_PENDING", "send_to_bank"): (
        "BANK_CHECK",
        [guard_required_fields_present],
        ["verify_successor_instrument"]
    ),

    # 7. Active -> Dispute Opened
    ("ACTIVE", "dispute_opened"): (
        "DISPUTED",
        [guard_reason_provided],
        ["lock_release_pipeline"]
    ),

    # 8. Dispute Cleared -> Active
    ("DISPUTED", "dispute_cleared"): (
        "ACTIVE",
        [guard_reason_provided],
        ["unlock_release_pipeline"]
    ),

    # 9. Active -> Release Requested
    ("ACTIVE", "release_requested"): (
        "RELEASE_REQUESTED",
        [guard_no_open_dispute],
        ["initiate_clearance_checklist"]
    ),

    # 10. Release Requested -> Compliance Check
    ("RELEASE_REQUESTED", "start_review"): (
        "COMPLIANCE_CHECK",
        [],
        ["assign_scrutiny_officer"]
    ),

    # 11. Compliance Check -> Approved
    ("COMPLIANCE_CHECK", "approve"): (
        "APPROVED",
        [guard_no_open_dispute, guard_maker_differs_from_checker, guard_checklist_cleared],
        ["generate_approval_certificate"]
    ),

    # 12. Compliance Check -> Rejected back to Active
    ("COMPLIANCE_CHECK", "reject_release"): (
        "ACTIVE",
        [guard_reason_provided],
        ["record_rejection_reason"]
    ),

    # 13. Approved -> Bank Release Pending
    ("APPROVED", "instruct_bank"): (
        "BANK_RELEASE_PENDING",
        [],
        ["dispatch_bank_discharge_instruction"]
    ),

    # 14. Bank Release Pending -> Closed
    ("BANK_RELEASE_PENDING", "bank_confirms_release"): (
        "CLOSED",
        [],
        ["archive_instrument", "release_custody_lien"]
    ),
}


def transition(current_state: str, event: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
    """
    Pure transition function:
    Evaluates (current_state, event) against the transition matrix, runs all guards,
    and returns (new_state, effects).

    Raises WorkflowError if invalid or guard fails.
    """
    if context is None:
        context = {}

    key = (current_state, event)
    if key not in TRANSITIONS:
        raise WorkflowError(
            f"Illegal state transition: Cannot perform event '{event}' from state '{current_state}'."
        )

    to_state, guards, effects = TRANSITIONS[key]

    # Evaluate guards
    for guard in guards:
        if not guard(context):
            raise WorkflowError(
                f"Transition guard '{guard.__name__}' failed for event '{event}'."
            )

    return to_state, effects
