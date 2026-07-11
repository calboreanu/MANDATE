"""
Tests for the failure-mode taxonomy and distribution (Workstream B6,
Notebook 09).

Run:  python3 -m pytest apparatus/analysis/tests/test_failure_modes.py -q
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.analysis.failure_modes import (
    FAILURE_CATEGORIES, UNCODED, validate_category, FailureCoding,
    suggest_category, failure_distribution)


# --- taxonomy ----------------------------------------------------------------

def test_taxonomy_has_nine_categories():
    assert len(FAILURE_CATEGORIES) == 9


def test_validate_category_accepts_known_and_uncoded():
    assert validate_category("fabrication")[0] is True
    assert validate_category(UNCODED)[0] is True


def test_validate_category_rejects_unknown():
    ok, msg = validate_category("not_a_category")
    assert ok is False and "unknown" in msg


def test_validate_category_mandate_only_rejected_for_baseline():
    ok, msg = validate_category("trace_failure", system_id="baseline_b1")
    assert ok is False and "MANDATE-only" in msg
    # but allowed for MANDATE-primary
    assert validate_category("trace_failure",
                             system_id="mandate_primary")[0] is True


# --- heuristic suggestion ----------------------------------------------------

def test_suggest_infrastructure_when_run_failed():
    assert suggest_category(run_ok=False) == "infrastructure_failure"
    assert suggest_category(run_ok=True,
                            errors=["boom"]) == "infrastructure_failure"


def test_suggest_adversarial_compliance():
    assert suggest_category(run_ok=True, o5=0) == "adversarial_compliance"


def test_suggest_silent_and_false_gap():
    assert suggest_category(run_ok=True, o2a=0) == "silent_gap"
    assert suggest_category(run_ok=True, o2b=0) == "false_gap"


def test_suggest_fabrication_and_extraction():
    assert suggest_category(run_ok=True, o3=5.0) == "fabrication"
    assert suggest_category(run_ok=True, o1=0.1) == "extraction_failure"


def test_suggest_uncoded_when_nothing_applies():
    assert suggest_category(run_ok=True, o1=0.9, o3=0.0) == UNCODED


def test_suggest_priority_infrastructure_over_behaviour():
    # a failed run with a bad outcome score is still infrastructure first
    assert suggest_category(run_ok=False, o5=0) == "infrastructure_failure"


# --- distribution ------------------------------------------------------------

def test_failure_distribution_per_system():
    codings = [
        FailureCoding("r1", "mandate_primary", "T1", "silent_gap"),
        FailureCoding("r2", "mandate_primary", "T2", "silent_gap"),
        FailureCoding("r3", "mandate_primary", "T3", "trace_failure"),
        FailureCoding("r4", "baseline_b1", "T1", "fabrication"),
        FailureCoding("r5", "baseline_b1", "T2", UNCODED),
    ]
    d = failure_distribution(codings)
    assert d["n_failures"] == 5
    assert d["by_system"]["mandate_primary"]["silent_gap"] == 2
    assert d["category_totals"]["silent_gap"] == 2
    assert d["n_uncoded"] == 1
    # the table carries one row per (system, category) with a nonzero count
    assert {"system_id": "baseline_b1", "category": "fabrication",
            "label": "Fabrication", "count": 1} in d["table"]
