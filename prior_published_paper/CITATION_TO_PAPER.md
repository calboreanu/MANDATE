# The Paper This Deposit Supports

**Title:** MANDATE: A Tolerance-Based Framework for Autonomous Agent Task
Specification
**Author:** Elias Calboreanu (Capitol Technology University)
**Status:** Revised manuscript (Frontiers in Artificial Intelligence,
manuscript ID 1802568 lineage). The paper text is not redistributed in this
deposit; cite the journal/preprint version.

## Relationship between paper and this deposit

- Paper **§12 Tier 1** (pilot case study: AEGIS audit convergence, 500-test
  static suite, 8-scenario deterministic + LLM runs) is backed by
  `replication_package/v0_pilot/` and `v0_5_pilot/`.
- Paper **§12 Tier 2** (pre-registered 2026Q2 comparative evaluation) is
  backed by `replication_package/v1_main/` and `v2_complete/` — the
  comparative table's source of record is
  `v1_main/grading/v2_full_coverage/ensemble_scores.jsonl` (12,000 records).
- The three supplement PDFs in `supplement_pdfs/` are the long-form empirical
  record: results, protocol amendment, and engineering/operational provenance.

## Reviewer-feedback provenance (why this evaluation exists)

The original submission was rejected on empirical grounds; the reviewers
requested, in substance: (1) empirical validation beyond a single-system
pilot, (2) comparative evaluation against baseline approaches, (3)
demonstrated robustness, (4) multi-vendor LLM evidence, and (5)
out-of-domain generalization. The 2026Q2 evaluation is the pre-registered
corrective response: six baselines including single-prompt and ReAct
(objection 2), a 350-perturbation adversarial suite with 100% structural
pass on prompt injection for canonical MANDATE (objection 3), four LLM
vendor families with per-vendor fallback disclosure (objection 4), and a
30-task software-engineering hold-out (objection 5). The mapping from each
objection to data files is in `docs/CLAIM_TO_DATA_MAP.md`.
