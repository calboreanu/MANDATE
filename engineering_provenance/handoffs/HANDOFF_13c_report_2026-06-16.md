# HANDOFF_13c Report: Phase 8 three-judge grading with patched apparatus

## Verdict

HALT

## Halt Point

Pre-spend one-record judge smoke, after Task 1 (`04_ground_truth/ground_truth.json`) and Task 2 (`08_grading/judges_config.json`) completed, before the full 9000-record grading command.

## Preconditions Checked

- `--double-grade-pct` flag: present.
- Grading tests: `16 passed`.
- `outputs_freeze_v1_1`: present.
- Anonymized outputs: 9000 JSON records under `08_grading/anonymized_outputs/`.
- API keys: `.env` contains all three key names, but the `.env` OpenAI key failed real authentication with `401 invalid_api_key`. The Desktop API-keys file was used for real preflight calls, consistent with the user's prior instruction.
- Judge healthchecks:
  - Claude Opus 4.6: OK.
  - GPT-4o (`gpt-4o-2024-11-20`): OK using the Desktop API-keys file.
  - Gemini 2.5 Pro through the actual `GeminiClient`: OK on a small 256-token healthcheck, after installing the already-declared `google-genai>=0.3` dependency into the project venv.

Operational note: the live project path is `/Users/ws01admin/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2`. The checked-in `.venv/bin/activate` still points to the old missing Desktop path, so commands were run with `.venv/bin/python` directly.

## Tasks Completed

- Apparatus patch committed before this handoff run:
  - Commit `fb0dd185`: `Patch cmd_grade double-grade sample support`
  - Adds `--double-grade-pct` and `--double-grade-seed`.
  - Adds regression coverage for `pipeline.double_grade` and CLI flag parsing.
- Task 1 completed:
  - `04_ground_truth/ground_truth.json` written.
  - 150 task-keyed entries.
  - All entries have non-empty `anchor.mission_intent`.
- Task 2 completed:
  - `08_grading/judges_config.json` written with GPT-4o, Claude Opus 4.6, and Gemini 2.5 Pro.

## Total Anonymized Records Graded

0 formal Phase 8 records.

A one-record paid smoke was run outside the canonical grading output tree at `/tmp/mandate_13c_smoke/` to avoid launching the full spend into a known judge failure.

Smoke record:

- `anon_id`: `OUT-0007F2EC`
- `task_id`: `TASK-MAIN-FIN-024`

Smoke results:

- `judge_1_gpt4o`: 1 row, `parse_ok=1`, captured cost `$0.022120`.
- `judge_2_claude_opus`: 1 row, `parse_ok=1`, captured cost `$0.036117`.
- `judge_3_gemini_pro`: 1 row, `parse_ok=0`, captured cost `$0.009615`, error `empty model output`.

No canonical `08_grading/judge_*`, `08_grading/ensemble_aggregated/`, `08_grading/double_grade/`, or `08_grading/irr.json` outputs were written.

## Per-Judge Cost

Formal grading cost: `$0.00`.

Preflight diagnostic cost was limited to healthchecks plus the one-record smoke. Captured smoke costs total `$0.067852`; healthcheck and direct Gemini diagnostic costs were not written by the apparatus but were low-token preflight calls.

## Per-Pair Cohen's Kappa

Not computed for the formal run.

The one-record smoke has no meaningful kappa.

## Double-Grade Sample

Not run.

The handoff halted before `--double-grade-pct 0.20` was launched.

## Blocking Finding

Gemini 2.5 Pro cannot produce judge text under the current `Judge.grade(... max_tokens=2048)` budget for the actual grading prompt.

Evidence from the direct Gemini diagnostic on the same smoke prompt:

- `max_output_tokens=2048`: `text_len=0`, `finish_reason=MAX_TOKENS`, `prompt_tokens=7692`, `thought_tokens=2045`, `total_tokens=9737`.
- `max_output_tokens=4096`: `text_len=1751`, `finish_reason=STOP`, `output_tokens=426`, `thought_tokens=3362`, `total_tokens=11480`, valid JSON text begins with the expected grader payload.

This means the current full grading run would likely produce near-100% Gemini judge parse failures, violating HANDOFF_13c's escalation rule for judge structured-output/schema failures above 5%. The failure is not an API-key or authentication problem; it is a Gemini judge token-budget/thinking-budget configuration problem.

## Halt Decision

HALT.

Launching the 9000-record run would spend into a known, reproducible judge failure mode.

## Anomalies

- The handoff's healthcheck example uses deprecated `google.generativeai`, while the apparatus uses the current `google-genai` SDK through `GeminiClient`. The actual grader path was tested.
- `google-genai` was declared in `setup/requirements.txt` and `environment.yml` but was missing from the venv; it was installed before the actual GeminiClient healthcheck.
- `.env` has an invalid OpenAI key. The Desktop API-keys file has a working OpenAI key and was used for real calls. The full grading command must export the Desktop key values or `.env` must be corrected before retry.
- `.venv/bin/activate` still references the old missing project path. Use `.venv/bin/python` directly or recreate/fix the venv activation script before retry.

## Per-Domain Breakouts

Not available; no formal ensemble scores were produced.

## Escalation Queue

1. Patch the Gemini judge path before retry:
   - Minimum viable patch: raise the grader generation budget from 2048 to at least 4096 for Gemini 2.5 Pro.
   - Better patch: expose per-judge `max_tokens` in `judges_config.json` or disable/reduce Gemini thinking budget via `thinking_config` if supported and protocol-acceptable.
2. Add a regression or preflight test that the actual GeminiClient path returns non-empty parseable judge JSON on a representative grading prompt.
3. Update the HANDOFF_13 healthcheck language to use `google-genai` / `GeminiClient`, not deprecated `google.generativeai`.
4. Correct `.env` or explicitly export keys from `/Users/ws01admin/Desktop/api keys` for the retry, so the stale OpenAI key is not used.
5. Fix or recreate `.venv/bin/activate` for the live `Desktop - lattice-ws01` project path, or standardize future handoffs on `.venv/bin/python`.
6. Re-fire a corrected HANDOFF_13d only after a one-record smoke shows all three judges `parse_ok=1` under the same model IDs intended for the full run.
