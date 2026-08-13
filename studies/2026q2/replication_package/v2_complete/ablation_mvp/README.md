# MANDATE Ablation Evaluation — MVP run (main + holdout, gradeable)

A real, on-disk demonstration that the canonical MLT MANDATE engine
(`mlt-stack-1.0.0rc1`) and all seven pre-registered ablations run end-to-end,
produce analyzable RunRecords, and emit a judge-ready (gradeable) layout.

- **Records:** 1,200 = 8 systems × 150 tasks (120 main + 30 SES holdout).
- **Mode:** deterministic, minimal-input — a `MissionInput` is built directly
  from each task's request text (no extraction LLM), so outputs are single-COA
  (the documented unstructured-input behavior). This is the fully reproducible,
  no-API subset. A1 uses a deterministic stub adapter.
- **Reproduce:**
  `PYTHONPATH="<eval_root>:<MLT>/src" python3 scripts/run_ablation_mvp.py --tasks 04_ground_truth/main_tasks.jsonl 04_ground_truth/holdout_tasks.jsonl --out <dir> --include-a1 --gradeable`

## Layout

```
MANDATE_ablation_mvp/
  canonical/            150 RunRecords (full, with system identity)
  ablation_a1..a7/      150 each
  anonymized_outputs/   1,200 OUT-*.json  (judge-facing: no system identity)
  anonymization_mapping.json   OUT-id -> {system_id, system_label, run_id, ...}
  grading_manifest.jsonl       1,200 x {anon_id, task_id}
  summary.json / SUMMARY.md    aggregate comparison
```

The `anonymized_outputs/` + `anonymization_mapping.json` pair matches the exact
format the v2 grading stage consumes (`{anon_id, task_id, output_type, output,
ok}`, system identity stripped, including the `ablation_id` field removed so a
blind judge cannot infer the system). This set is ready to feed to the grader.

## What each system produced (150/150 tasks each)

| System | ok | trace entries | target band | nist_rmf | registry | COA bands collapsed | schema-valid* |
|---|---|---|---|---|---|---|---|
| canonical | 150 | 6 | 150 | 150 | 150 | 0 | yes |
| A2 no tolerance bands | 150 | 6 | **0** | 150 | 150 | **150** | yes |
| A3 no gap-report | 150 | 6 | 150 | 150 | 150 | 0 | yes |
| A4 no Validation role | 150 | **5** | 150 | 150 | 150 | 0 | yes |
| A5 no registry | 150 | 6 | 150 | 150 | **150** | 0 | yes |
| A6 no search-trace | 150 | **0** | 150 | 150 | 150 | 0 | **no (by design)** |
| A7 no NIST RMF | 150 | 6 | 150 | **0** | 150 | 0 | yes |
| A1 no role separation | 150 | **1** | 150 | **0** | 150 | 150† | **no (by design)** |

\* Schema = `mandate-as-code.schema.json`. A6 (empty trace) and A1 (single-pass
light artifact) deviate by design; an active ablation relaxes the final gate so
the record still emits. † A1 stub COAs carry no `risk_assessment`, so the
band-collapse check is vacuously true.

## How to read it

Each ablation demonstrably removes exactly its component, at scale: A2 → no
target band + collapsed COA bands; A4 → trace ends at Binding (5 entries); A6 →
no trace (0); A7 → no NIST RMF; A1 → single combined entry, light artifact. A3
and A5 match canonical here — A3 only suppresses the gap-report artifact (no gaps
on minimal input), and **A5 does not actually ablate** (registry present on all
150; pre-existing, see Finding 7).

## Honest scope

This is *demonstrated, gradeable, and reproducible* — not the full empirical
result. These are deterministic minimal-input records (single-COA), no LLM judge
has scored them yet, and A1 used a stub. The grader has not been run against this
set; it is merely in the correct input format. The next step is to (a) run the
same harness with Cond-A Sonnet pre-extraction for richer multi-COA artifacts
and a live A1 adapter, then (b) point the v2 three-judge grader at
`anonymized_outputs/`.

Harness: `scripts/run_ablation_mvp.py` in the eval tree.
