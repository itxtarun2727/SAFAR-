"""
test_workflow.py — Unit tests for the pure workflow transition state machine.
Validates all allowed transitions, guard conditions, and illegal transitions.
"""

from datetime import date, timedelta
import pytest
import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import workflow
from clock import Clock


class DummyInstrument:
    def __init__(self, reference_no="DEMOA00112233", amount_paise=200000000, maturity_date=None):
        self.reference_no = reference_no
        self.amount_paise = amount_paise
        self.maturity_date = maturity_date or (Clock.today() - timedelta(days=10))


def test_submission_and_bank_check():
    """SUBMITTED -> BANK_CHECK -> AICTE_REVIEW or NEEDS_CORRECTION."""
    inst = DummyInstrument()
    context = {"instrument": inst}

    # SUBMITTED -> BANK_CHECK
    new_state, effects = workflow.transition("SUBMITTED", "send_to_bank", context)
    assert new_state == "BANK_CHECK"
    assert "notify_bank_adapter" in effects

    # BANK_CHECK -> AICTE_REVIEW on bank match
    new_state, effects = workflow.transition("BANK_CHECK", "bank_match", context)
    assert new_state == "AICTE_REVIEW"

    # BANK_CHECK -> NEEDS_CORRECTION on mismatch
    mismatch_context = {"instrument": inst, "reason": "Amount does not match bank record"}
    new_state, effects = workflow.transition("BANK_CHECK", "bank_mismatch", mismatch_context)
    assert new_state == "NEEDS_CORRECTION"
    assert "notify_college_mismatch" in effects

    # BANK_CHECK stays pending on source_unavailable
    new_state, effects = workflow.transition("BANK_CHECK", "source_unavailable", context)
    assert new_state == "BANK_CHECK"
    assert "retry_with_backoff" in effects

    # NEEDS_CORRECTION -> SUBMITTED on resubmit
    new_state, effects = workflow.transition("NEEDS_CORRECTION", "resubmit", context)
    assert new_state == "SUBMITTED"


def test_aicte_review_transitions():
    """AICTE_REVIEW -> ACTIVE (approve) or REJECTED (reject)."""
    context = {"reason": "Verified against state university accreditation norms."}
    new_state, effects = workflow.transition("AICTE_REVIEW", "approve", context)
    assert new_state == "ACTIVE"
    assert "mark_lien_active" in effects

    # Rejection requires reason
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("AICTE_REVIEW", "reject", {"reason": ""})

    new_state, effects = workflow.transition("AICTE_REVIEW", "reject", {"reason": "Document blur."})
    assert new_state == "REJECTED"

    # REJECTED -> SUBMITTED on resubmit
    inst = DummyInstrument()
    new_state, _ = workflow.transition("REJECTED", "resubmit", {"instrument": inst})
    assert new_state == "SUBMITTED"


def test_renewal_and_dispute_transitions():
    """ACTIVE -> RENEWAL_PENDING, ACTIVE -> DISPUTED, DISPUTED -> ACTIVE."""
    # Active -> Renewal
    new_state, _ = workflow.transition("ACTIVE", "renewal_detected", {})
    assert new_state == "RENEWAL_PENDING"

    # Active -> Disputed
    new_state, _ = workflow.transition("ACTIVE", "dispute_opened", {"reason": "Court stay order."})
    assert new_state == "DISPUTED"

    # Dispute Cleared -> Active
    new_state, _ = workflow.transition("DISPUTED", "dispute_cleared", {"reason": "Grievance disposed."})
    assert new_state == "ACTIVE"


def test_release_guards_and_approval_pipeline():
    """Test full release flow: ACTIVE -> RELEASE_REQUESTED -> COMPLIANCE_CHECK -> APPROVED -> BANK_RELEASE_PENDING -> CLOSED."""
    today = Clock.today()
    future_inst = DummyInstrument(maturity_date=today + timedelta(days=100))
    past_inst = DummyInstrument(maturity_date=today - timedelta(days=10))

    # Guard: Premature release blocked unless closure
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("ACTIVE", "release_requested", {"instrument": future_inst, "kind": "release"})

    # Premature closure allowed
    new_state, _ = workflow.transition("ACTIVE", "release_requested", {"instrument": future_inst, "kind": "closure"})
    assert new_state == "RELEASE_REQUESTED"

    # Matured FDR release requested
    new_state, _ = workflow.transition("ACTIVE", "release_requested", {"instrument": past_inst, "kind": "release"})
    assert new_state == "RELEASE_REQUESTED"

    # RELEASE_REQUESTED -> COMPLIANCE_CHECK
    new_state, _ = workflow.transition("RELEASE_REQUESTED", "recommend", {"reason": "All checks clear"})
    assert new_state == "COMPLIANCE_CHECK"

    # COMPLIANCE_CHECK -> APPROVED requires:
    # 1. maker != checker
    # 2. no active dispute
    # 3. all checklist items true
    # 4. bank reverification match
    base_context = {
        "maker_id": "u-officer-01",
        "actor_id": "u-senior-01",
        "has_active_dispute": False,
        "checklist": {"fee_cleared": True, "salary_cleared": True, "inspection_noc": True},
        "reverification_result": "match",
    }
    new_state, effects = workflow.transition("COMPLIANCE_CHECK", "approve", base_context)
    assert new_state == "APPROVED"
    assert "generate_approval_certificate" in effects

    # Guard: same officer cannot approve their own recommendation
    bad_maker = dict(base_context, actor_id="u-officer-01")
    with pytest.raises(workflow.WorkflowError) as excinfo:
        workflow.transition("COMPLIANCE_CHECK", "approve", bad_maker)
    assert "different person" in str(excinfo.value)

    # Guard: dispute blocks approval
    bad_dispute = dict(base_context, has_active_dispute=True)
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("COMPLIANCE_CHECK", "approve", bad_dispute)

    # Guard: checklist incomplete blocks approval
    bad_checklist = dict(base_context, checklist={"c1": True, "c2": False})
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("COMPLIANCE_CHECK", "approve", bad_checklist)

    # Guard: reverification mismatch blocks approval
    bad_reverify = dict(base_context, reverification_result="mismatch")
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("COMPLIANCE_CHECK", "approve", bad_reverify)

    # APPROVED -> BANK_RELEASE_PENDING
    new_state, effects = workflow.transition("APPROVED", "issue_authorization", {})
    assert new_state == "BANK_RELEASE_PENDING"
    assert "dispatch_bank_release_authorization" in effects

    # BANK_RELEASE_PENDING -> CLOSED only when bank confirms with matching code
    new_state, effects = workflow.transition("BANK_RELEASE_PENDING", "bank_confirms_release", {"code_matched": True})
    assert new_state == "CLOSED"
    assert "release_custody_lien" in effects


def test_forbidden_transitions():
    """Ensure invalid bypass jumps are strictly rejected."""
    inst = DummyInstrument()
    context = {"instrument": inst}

    # SUBMITTED cannot jump to CLOSED directly
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("SUBMITTED", "bank_confirms_release", context)

    # AICTE approval alone must NEVER close a deposit
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("APPROVED", "bank_confirms_release", context)

    # AICTE review cannot jump directly to CLOSED
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("AICTE_REVIEW", "bank_confirms_release", context)
