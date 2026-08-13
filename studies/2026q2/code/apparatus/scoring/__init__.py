"""
Outcome scorers and task-level aggregation (Workstream B7).

This package is the coded path from grading (B5) to the pre-registered
hypotheses. `outcomes` derives the five primary outcomes O1-O5 (and the
secondary O2b) per run from the three-judge EnsembleScore and the Section 4a
schema check; `aggregate` collapses runs to the task-level unit of analysis
(PROTOCOL_LOCK Section 6.3) and emits the long-format table that Notebook 04
feeds to the mixed-effects models.
"""
from .outcomes import (OUTCOME_IDS, GAP_TRIGGERING, OutcomeRow, score_run,
                       score_o1, score_o2a, score_o2b, score_o3, score_o4,
                       score_o5)
from .aggregate import TaskOutcome, task_level, analysis_table

__all__ = [
    "OUTCOME_IDS", "GAP_TRIGGERING", "OutcomeRow", "score_run",
    "score_o1", "score_o2a", "score_o2b", "score_o3", "score_o4", "score_o5",
    "TaskOutcome", "task_level", "analysis_table",
]
