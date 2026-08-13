# HANDOFF 19 Stage 2 Report — 2026-06-23

## Verdict
HALT

## Stage
Stage 2 pilot smoke runs. Stage 3 was not started.

## Preconditions
All seven preconditions passed on the retry with the corrected MLT pytest working directory:

- Canonical MLT path present.
- MLT mandate suite: `418 passed, 8 skipped, 3 xfailed in 0.60s`.
- Canonical MANDATE smoke: PASS.
- `04_ground_truth/main_tasks.jsonl`: 120 lines.
- Cond-X MANDATE-primary records: 1200 files.
- Anthropic, OpenAI, and Google API keys present in `.env`.
- `07_system_outputs/cond_a/` and `07_system_outputs/cond_b/` created cleanly.

## Stage 1 Plumbing
Stage 1 apparatus plumbing was implemented and committed before the pilot:

- Commit: `37477ae8`
- Added canonical MLT adapter: `apparatus/systems/mandate_canonical.py`
- Added Cond-A extractor: `apparatus/preprocess/extract_mission_input.py`
- Added v2 rubric: `apparatus/grading/rubric_v2.py`
- Added CLI commands: `run-cond-a`, `run-cond-b`, `grade-v2`
- Preserved v1 `grade` behavior; `grade-v2` routes explicitly to the v2 prompt.
- Tests:
  - Focused Stage 1 suites: `53 passed`
  - Full apparatus suite under `.venv/bin/python`: `278 passed, 1 skipped`

## Deviation
The project `.venv/bin/activate` file still points `VIRTUAL_ENV` at the old pre-remap Desktop path (`$HOME/Desktop/MANDATE Evaluation/...`). Under this shell, `source .venv/bin/activate && python3` resolves to Homebrew Python 3.14 instead of the project venv. To avoid contaminating the run with the wrong interpreter, Stage 1 verification and Stage 2 pilots used the project venv directly via `.venv/bin/python`.

## Cond-A Pilot
Command:

```zsh
.venv/bin/python -m apparatus.run run-cond-a \
  TASK-MAIN-INT-034 TASK-MAIN-FIN-001 TASK-MAIN-FIN-018 \
  TASK-MAIN-INT-003 TASK-MAIN-SEC-014 \
  --out 07_system_outputs/cond_a \
  --extraction-model claude-sonnet-4-6
```

Result: 5 of 5 records written, 5 of 5 `ok=True`.

| task_id | ok | minimum keys | target keys | constraints | COAs | trace entries | chain hash |
|---|---:|---:|---:|---:|---:|---:|---:|
| TASK-MAIN-FIN-001 | true | 1 | 1 | 3 | 2 | 6 | true |
| TASK-MAIN-FIN-018 | true | 1 | 1 | 6 | 2 | 6 | true |
| TASK-MAIN-INT-003 | true | 1 | 1 | 9 | 2 | 6 | true |
| TASK-MAIN-INT-034 | true | 1 | 1 | 5 | 2 | 6 | true |
| TASK-MAIN-SEC-014 | true | 1 | 1 | 5 | 2 | 6 | true |

Cond-A passed: all records `ok=True`; constraints non-empty in 5 of 5; COA count in range 1-3; trace chain present.

Cond-A failed: `anchor.minimum` has 1 key in 5 of 5; `anchor.target` has 1 key in 5 of 5. The Stage 2 success criteria require `anchor.minimum` >= 3 keys and `anchor.target` >= 2 keys.

Interpretation: the extractor produced MLT-valid structured `MissionInput` records, but canonical MLT `InterpreterRole.execute()` wraps `minimum_outcome` and `target_outcome` into `{"description": ...}`. This matches `handoffs/v2_redesign_audit_role_schemas.md`: current canonical Interpreter emits single-key description objects even when the input strings contain multiple semantic dimensions.

## Cond-B Pilot
Command:

```zsh
.venv/bin/python -m apparatus.run run-cond-b \
  TASK-MAIN-INT-034 TASK-MAIN-FIN-001 TASK-MAIN-FIN-018 \
  TASK-MAIN-INT-003 TASK-MAIN-SEC-014 \
  --out 07_system_outputs/cond_b \
  --llm-backend anthropic \
  --llm-model claude-sonnet-4-6
```

Result: 5 of 5 records written, 0 of 5 `ok=True`.

| task_id | ok | first failure |
|---|---:|---|
| TASK-MAIN-FIN-001 | false | Intake invalid constraint syntax: natural-language numbered constraints |
| TASK-MAIN-FIN-018 | false | Intake invalid constraint syntax: natural-language numbered constraints |
| TASK-MAIN-INT-003 | false | Intake invalid constraint syntax: natural-language numbered constraints |
| TASK-MAIN-INT-034 | false | Intake invalid constraint syntax: natural-language numbered constraints |
| TASK-MAIN-SEC-014 | false | Intake invalid constraint syntax: natural-language numbered constraints |

All five Cond-B records show `llm_roles_used` = Intake, Interpreter, Decomposition, Procedure, Binding, Validation with `llm_fallback=False`, so the LLM path was reached. The failure mode is that LLM Intake emits natural-language constraints such as "Must align with NIST SP 800-137 guidance" or "Delivery deadline: close of business Friday"; canonical MLT requires its EBNF constraint grammar, so Intake and final Validation reject the artifacts.

## Halt Reason
Stage 2 success criteria failed for both conditions:

1. Cond-A: canonical deterministic MLT produces valid artifacts, but minimum/target are single-key `description` objects, failing the required multi-key anchor richness.
2. Cond-B: canonical LLM-augmented MLT fails 5 of 5 pilot runs because LLM Intake emits natural-language constraints that do not satisfy MLT's constraint grammar.

Per HANDOFF_19: "HALT and report before proceeding to Stage 3 if either pilot fails to meet success criteria." Stage 3 was not started.

## Artifacts Produced
- `07_system_outputs/cond_a/cond_a__TASK-MAIN-*.json` — 5 pilot records
- `07_system_outputs/cond_a/ledger.jsonl`
- `07_system_outputs/cond_b/cond_b__TASK-MAIN-*.json` — 5 pilot records
- `07_system_outputs/cond_b/ledger.jsonl`

## Action Queue for PI
1. Decide whether Cond-A's success criterion should be revised to accept canonical MLT's current single-key `{"description": ...}` anchor shape, since that shape is explicitly documented as canonical in the audits.
2. If multi-key anchors remain required, decide whether to patch canonical MLT Interpreter to preserve structured dimensions. That is an upstream MLT behavior change, not an eval-apparatus-only change.
3. For Cond-B, decide whether to add a grammar-normalization guard around LLM Intake constraints, patch MLT Intake's LLM schema/prompt to emit only valid EBNF constraints, or revise Cond-B to treat invalid natural-language constraints as extraction gaps rather than hard run failures.
4. Repair `.venv/bin/activate` or recreate the venv at the remapped Desktop path before issuing long-running v2 commands that rely on `source .venv/bin/activate && python3`.
