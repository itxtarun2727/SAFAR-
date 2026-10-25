"""
test_workflow.py — Unit tests for the pure workflow transition state machine.
"""

import pytest
import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import workflow


class DummyInstrument:
    def __init__(self, reference_no="REF123", amount_paise=150000000, maturity_date="2034-01-01"):
        self.reference_no = reference_no
        self.amount_paise = amount_paise
        self.maturity_date = maturity_date


def test_allowed_transition():
    """SUBMITTED -> BANK_CHECK via send_to_bank should succeed when fields are present."""
    context = {"instrument": DummyInstrument()}
    new_state, effects = workflow.transition("SUBMITTED", "send_to_bank", context)
    assert new_state == "BANK_CHECK"
    assert "notify_bank_adapter" in effects


def test_forbidden_transition():
    """SUBMITTED -> CLOSED directly must be rejected."""
    context = {"instrument": DummyInstrument()}
    with pytest.raises(workflow.WorkflowError):
        workflow.transition("SUBMITTED", "bank_confirms_release", context)


def test_guard_maker_checker_enforced():
    """AICTE release approval must block if maker == checker."""
    context = {
        "maker_id": "u-officer-01",
        "actor_id": "u-officer-01",  # Same person trying to approve!
        "checklist": {"c1": True, "c2": True},
        "has_active_dispute": False,
    }
    with pytest.raises(workflow.WorkflowError) as excinfo:
        workflow.transition("COMPLIANCE_CHECK", "approve", context)
    assert "different person" in str(excinfo.value)


def test_guard_dispute_blocks_release():
    """Active dispute must block release approval."""
    context = {
        "maker_id": "u-officer-01",
        "actor_id": "u-senior-02",
        "checklist": {"c1": True},
        "has_active_dispute": True,  # Dispute open!
    }
    with pytest.raises(workflow.WorkflowError) as excinfo:
        workflow.transition("COMPLIANCE_CHECK", "approve", context)
    assert "dispute" in str(excinfo.value).lower()
