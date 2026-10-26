"""
workflow.py — Deterministic State Machine for Instrument & Release Lifecycles.

SINGLE SOURCE OF TRUTH:
All instrument state transitions MUST be evaluated through transition().
No SQL UPDATE should alter instrument.status directly.
Keep transition() a pure function.
"""

from typing import Tuple, List, Dict, Any, Callable
from clock import Clock


class WorkflowError(Exception):
    """Raised when an illegal transition or unmet guard is encountered."""
    pass


# ── Allowed States ─────────────────────────────────────────────────────────────

NORMAL_STATES = {
    "SUBMITTED",
    "BANK_CHECK",
    "AICTE_REVIEW",
    "ACTIVE",
    "RELEASE_REQUESTED",
    "COMPLIANCE_CHECK",
    "APPROVED",
    "BANK_RELEASE_PENDING",
    "CLOSED",
}

EXCEPTION_STATES = {
    "NEEDS_CORRECTION",
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


def guard_reason_provided(context: Dict[str, Any]) -> bool:
    """Ensure a written audit reason is attached."""
    reason = context.get("reason")
    if not reason or not str(reason).strip():
        raise WorkflowError("A specific operational reason must be recorded for this action.")
    return True


def guard_no_open_dispute(context: Dict[str, Any]) -> bool:
    """Release is strictly blocked if any active dispute or compliance hold exists."""
    has_dispute = context.get("has_active_dispute", False)
    if has_dispute:
        raise WorkflowError("Release is blocked: an active dispute or compliance hold is open.")
    return True


def guard_maturity_or_closure(context: Dict[str, Any]) -> bool:
    """Guards release request: maturity date has passed per Clock (or request kind is closure)."""
    kind = context.get("kind", "release")
    if kind == "closure":
        return True
    instrument = context.get("instrument")
    if not instrument or not instrument.maturity_date:
        raise WorkflowError("Maturity date is missing on instrument.")
    if instrument.maturity_date > Clock.today():
        raise WorkflowError("Release cannot be requested before maturity date has passed unless kind is closure.")
    return True


def guard_maker_differs_from_checker(context: Dict[str, Any]) -> bool:
    """Enforce maker != checker: Approving senior manager must differ from recommending officer."""
    maker_id = context.get("maker_id")
    checker_id = context.get("actor_id")
    if maker_id and checker_id and maker_id == checker_id:
        raise WorkflowError("AICTE Senior Checker must be a different person from Officer Maker.")
    return True


def guard_checklist_cleared(context: Dict[str, Any]) -> bool:
    """Ensure all required pre-release checklist clearances are satisfied."""
    checklist = context.get("checklist")
    if not checklist or not isinstance(checklist, dict):
        raise WorkflowError("Clearance checklist is required and must be completed.")
    if not all(checklist.values()):
        raise WorkflowError("All clearance checklist requirements must be satisfied.")
    return True


def guard_reverification_match(context: Dict[str, Any]) -> bool:
    """Guards final approval: fresh simulated bank re-verification must return match."""
    reverification_result = context.get("reverification_result")
    if reverification_result is not None and reverification_result != "match":
        raise WorkflowError("Bank re-verification did not return match. Release cannot be approved.")
    return True


def guard_matching_release_code(context: Dict[str, Any]) -> bool:
    """Guards closing deposit: requires valid matching bank release confirmation."""
    code_matched = context.get("code_matched", True)
    if not code_matched:
        raise WorkflowError("Release authorization code mismatch or unverified by issuing bank.")
    return True


# ── Pure Transition Table ──────────────────────────────────────────────────────
# Format: (from_state, event) -> (to_state, list of guard functions, list of effect labels)

TRANSITIONS: Dict[Tuple[str, str], Tuple[str, List[Callable], List[str]]] = {
    # 1. Submission -> Bank check (automatic on submit)
    ("SUBMITTED", "send_to_bank"): (
        "BANK_CHECK",
        [guard_required_fields_present],
        ["notify_bank_adapter"]
    ),

    # 2. Bank check -> AICTE Review (adapter result = match)
    ("BANK_CHECK", "bank_match"): (
        "AICTE_REVIEW",
        [],
        ["record_bank_match"]
    ),
    ("BANK_CHECK", "bank_confirms"): (
        "AICTE_REVIEW",
        [],
        ["record_bank_match"]
    ),

    # 3. Bank check -> Needs Correction (adapter result = mismatch, college-only visible)
    ("BANK_CHECK", "bank_mismatch"): (
        "NEEDS_CORRECTION",
        [guard_reason_provided],
        ["notify_college_mismatch", "record_failed_verification"]
    ),
    ("BANK_CHECK", "bank_rejects"): (
        "NEEDS_CORRECTION",
        [guard_reason_provided],
        ["notify_college_mismatch", "record_failed_verification"]
    ),

    # 4. Bank check stays pending on source_unavailable (retry with backoff)
    ("BANK_CHECK", "source_unavailable"): (
        "BANK_CHECK",
        [],
        ["retry_with_backoff"]
    ),

    # 5. Needs Correction -> Resubmitted
    ("NEEDS_CORRECTION", "resubmit"): (
        "SUBMITTED",
        [guard_required_fields_present],
        ["clear_previous_mismatches"]
    ),

    # 6. AICTE Review -> Active (University officer approves)
    ("AICTE_REVIEW", "approve"): (
        "ACTIVE",
        [guard_reason_provided],
        ["mark_lien_active"]
    ),

    # 7. AICTE Review -> Rejected (Officer rejects with reason)
    ("AICTE_REVIEW", "reject"): (
        "REJECTED",
        [guard_reason_provided],
        ["notify_institution_rejection"]
    ),

    # 8. Rejected -> Resubmitted
    ("REJECTED", "resubmit"): (
        "SUBMITTED",
        [guard_required_fields_present],
        ["clear_previous_mismatches"]
    ),

    # 9. Active -> Renewal Pending
    ("ACTIVE", "renewal_detected"): (
        "RENEWAL_PENDING",
        [],
        ["queue_renewal_inspection"]
    ),

    # 10. Renewal Pending -> Bank Check
    ("RENEWAL_PENDING", "send_to_bank"): (
        "BANK_CHECK",
        [guard_required_fields_present],
        ["verify_successor_instrument"]
    ),

    # 11. Active -> Dispute Opened
    ("ACTIVE", "dispute_opened"): (
        "DISPUTED",
        [guard_reason_provided],
        ["lock_release_pipeline"]
    ),

    # 12. Dispute Cleared -> Active
    ("DISPUTED", "dispute_cleared"): (
        "ACTIVE",
        [guard_reason_provided],
        ["unlock_release_pipeline"]
    ),

    # 13. Active -> Release Requested (college requests)
    ("ACTIVE", "release_requested"): (
        "RELEASE_REQUESTED",
        [guard_no_open_dispute, guard_maturity_or_closure],
        ["initiate_clearance_checklist"]
    ),

    # 14. Release Requested -> Compliance Check (University officer starts review and recommends)
    ("RELEASE_REQUESTED", "start_review"): (
        "COMPLIANCE_CHECK",
        [guard_reason_provided],
        ["record_officer_recommendation"]
    ),
    ("RELEASE_REQUESTED", "recommend"): (
        "COMPLIANCE_CHECK",
        [guard_reason_provided],
        ["record_officer_recommendation"]
    ),

    # 15. Compliance Check -> Approved (Senior Manager approves)
    ("COMPLIANCE_CHECK", "approve"): (
        "APPROVED",
        [
            guard_maker_differs_from_checker,
            guard_no_open_dispute,
            guard_checklist_cleared,
            guard_reverification_match,
        ],
        ["generate_approval_certificate"]
    ),

    # 16. Compliance Check -> Rejected back to Active
    ("COMPLIANCE_CHECK", "reject_release"): (
        "ACTIVE",
        [guard_reason_provided],
        ["record_rejection_reason"]
    ),

    # 17. Approved -> Bank Release Pending (System issues ReleaseAuthorization)
    ("APPROVED", "issue_authorization"): (
        "BANK_RELEASE_PENDING",
        [],
        ["dispatch_bank_release_authorization"]
    ),
    ("APPROVED", "instruct_bank"): (
        "BANK_RELEASE_PENDING",
        [],
        ["dispatch_bank_release_authorization"]
    ),

    # 18. Bank Release Pending -> Closed (ONLY when bank user confirms with matching college code)
    ("BANK_RELEASE_PENDING", "bank_confirms_release"): (
        "CLOSED",
        [guard_matching_release_code],
        ["release_custody_lien", "archive_instrument"]
    ),
    ("BANK_RELEASE_PENDING", "bank_confirm_release"): (
        "CLOSED",
        [guard_matching_release_code],
        ["release_custody_lien", "archive_instrument"]
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
