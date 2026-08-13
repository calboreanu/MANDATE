# Codex Handoff 21: Cut gt_freeze_v1 and perturbation_freeze_v1

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 2 to 5 minutes (no API calls; verification + two annotated git tags).
**Blocked on:** HANDOFF_06c, HANDOFF_09, HANDOFF_20, HANDOFF_10 all PROCEED.

---

## Why this exists

Per `00_preregistration/DEVIATIONS.md` 2026-06-04 (SME-skip pivot), the scaffold output of PROMPTS Section 2 on the three pools IS the ground truth for the formal Phase 6 study. The three scaffold pools are now present, every record `parse_ok: true`:

```
04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl       6 records  (HANDOFF_06c)
04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl      120 records  (HANDOFF_09)
04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl    30 records  (HANDOFF_20)
06_perturbations/perturbation_suite.jsonl                  350 records  (HANDOFF_10)
```

This handoff verifies the four files are intact and cuts two annotated tags: `gt_freeze_v1` (covers the three scaffold pools as ground truth) and `perturbation_freeze_v1` (covers the perturbation suite). After these tags, the four-tag freeze trifecta is complete and Phase 6 (HANDOFF_11) becomes the only remaining gate.

**Definition of done.** Two annotated git tags exist at the project repository: `gt_freeze_v1` and `perturbation_freeze_v1`. One handoff report. No file changes.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# All four artifact files present with the expected line counts
python3 - <<'PY'
import json, sys
need = [("04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl",   6, True),
        ("04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl",   120, True),
        ("04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl", 30, True),
        ("06_perturbations/perturbation_suite.jsonl",              350, False)]
for path, n_expected, check_parse_ok in need:
    rows = [json.loads(l) for l in open(path)]
    assert len(rows) == n_expected, f"{path}: expected {n_expected} got {len(rows)}"
    if check_parse_ok:
        ok = sum(1 for r in rows if r.get("parse_ok"))
        assert ok == n_expected, f"{path}: {ok}/{n_expected} parse_ok (must be 100%)"
print("all four artifact files verified")
PY

# corpus_freeze_v1 and baseline_freeze_v1 already present
git tag --list | grep -E "^(corpus_freeze_v1|baseline_freeze_v1)$" | sort \
  | diff - <(echo -e "baseline_freeze_v1\ncorpus_freeze_v1") \
  || { echo "earlier freezes missing"; exit 1; }
echo "earlier freezes present"

# Neither new tag exists yet
git tag --list | grep -E "^(gt_freeze_v1|perturbation_freeze_v1)$" \
  && { echo "one of the new tags already exists"; exit 1; }
echo "new tags do not already exist"
```

**Success criteria.** All four artifact files print as verified; the two earlier freezes are present; neither new tag pre-exists.

## Decision boundary

You may decide:
- Tag commit message text within the templates below.

You must escalate:
- A `parse_ok=false` record in any scaffold pool.
- A line-count mismatch in any artifact.
- An existing `gt_freeze_v1` or `perturbation_freeze_v1` tag.

You may not:
- Modify any of the four artifact files. They are the deposit artifacts as-is.
- Cut tags in upstream AEGIS.

---

## Task 1: Cut gt_freeze_v1

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

git tag -a gt_freeze_v1 -m "Ground truth freeze v1 (SME-skip per DEVIATIONS.md 2026-06-04)

Pilot scaffolds:     6 records  (TASK-PILOT-{SEC,FIN,INT}-00{1,2})
Main scaffolds:    120 records  (TASK-MAIN-{SEC,FIN,INT}-001..040)
Holdout scaffolds:  30 records  (TASK-HOLDOUT-SES-001..030)

Under the SME-skip deviation, the PROMPTS Section 2 anchor scaffolds produced
by Claude Opus 4.6 are the ground truth verbatim. Phase 6 grading reads from
04_ground_truth/{pilot,main,holdout}_scaffolds/anchor_scaffolds.jsonl. The
realism question is an acknowledged caveat, not adjudicated.

Anchor scaffolds: HANDOFF_06c PROCEED + HANDOFF_09 PROCEED + HANDOFF_20 PROCEED.
Scaffolder default max_tokens=4096 (patched 2026-06-04 after HANDOFF_06b halt).
All 156 records parse_ok=true with raw_json captured."

git tag --list gt_freeze_v1
git show gt_freeze_v1 --stat | head -10
```

**Success criteria.** Annotated tag `gt_freeze_v1` exists.

## Task 2: Cut perturbation_freeze_v1

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

git tag -a perturbation_freeze_v1 -m "Perturbation suite freeze v1

06_perturbations/perturbation_suite.jsonl: 350 records, seven canonical types
(50 each). Generated from the frozen main corpus by HANDOFF_10 PROCEED. The
perturbation generator was extended on 2026-06-04 with canonical output labels
and small CLI fixes (commits db46035, bc8af1b, 021c5f5, b334c5a).

Phase 6 reads this file at 5 runs per record per system."

git tag --list perturbation_freeze_v1
git show perturbation_freeze_v1 --stat | head -10
```

**Success criteria.** Annotated tag `perturbation_freeze_v1` exists.

## Task 3: Confirm the four-tag freeze trifecta

```zsh
echo "Final freeze tag state:"
git tag --list | grep -E "freeze" | sort
# Expect:
#   baseline_freeze_v1
#   corpus_freeze_v1
#   gt_freeze_v1
#   perturbation_freeze_v1
```

**Success criteria.** All four tags present.

## Report

`handoffs/HANDOFF_21_report_<YYYY-MM-DD>.md` with:
- Per-file verification: line counts and parse_ok rates
- Four freeze tag hashes
- PROCEED verdict

Commit message: `Handoff 21: gt_freeze_v1 + perturbation_freeze_v1 (four-tag freeze trifecta complete)`.
