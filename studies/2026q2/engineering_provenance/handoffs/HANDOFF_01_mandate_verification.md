# Codex Handoff 01: MANDATE Verification on the Eval Host

**For:** Codex
**From:** Lead Analyst
**Date:** 2026-06-01
**Estimated wall clock:** 30 to 90 minutes (most of it Ollama inference for A1).

---

## Mission

Take MANDATE-primary from "code-complete in source" to "verified-running on the eval host," so the headline H1 through H5 analysis can run when Phase 6 begins. This is the apparatus audit's required A1 re-verification, the 2026-05-23 PASS having been superseded by the RAG-retriever fix; the supporting AEGIS-eval recreation; and the provenance capture against the frozen tree.

**Definition of done.** A1 reports PASS, `provenance_evidence.md` reflects the frozen `AEGIS-eval/` state, and the full apparatus unit suite is green on the eval host. The handoff ends with a structured report that lets the PI (Cal) say "proceed to corpus generation" or "halt and investigate."

## Preconditions

Confirm each. Stop and report if any is false.

- Eval host: `lattice-ws01` (or the designated Mac mini M4 Pro). `hostname` should match the host the model manifest was captured on.
- Working directory: `~/Desktop/MANDATE Evaluation/mandate_eval_2026Q2`.
- Upstream AEGIS at `~/Desktop/AEGIS` is a git repository and carries the tag `mandate-eval-primary-2026q2-v1`.
- Ollama is installed and `ollama serve` is running on `http://localhost:11434`.
- The six fine-tuned models are registered: `ollama list` shows `mandate-intake`, `mandate-interpreter`, `mandate-decomp`, `mandate-procedure`, `mandate-binding`, `mandate-validation` (the `:latest` tag is acceptable).
- The Python venv at `.venv/` exists and was created by `setup/install.sh`.
- At least 1 GB free disk for the frozen extraction.

## Decision boundary

You may decide:
- Output paths and intermediate file names (use the canonical phase directories already in the project tree).
- A single network retry on a transient Ollama or pip error.
- The default model strings the apparatus uses (do not override them; the freeze fixes them).

You must escalate (write into the final report and stop the relevant section):
- Any failure of A1 (PASS is the only acceptable verdict).
- Any reported `llm_fallback=True` on a fine-tuned role.
- Any deviation from the pinned tag `mandate-eval-primary-2026q2-v1`.
- Any change to a TO_FILL_TRACKER row that would move it from RESOLVED back to OPEN.
- A unit test failure on the apparatus suite that did not exist in the lead-analyst environment (current baseline 195 / 195 pass).

You may not:
- Edit any file under `_package/`, `AEGIS-eval/`, or files the user has previously curated in `setup/` (`install.sh`, `ollama_models.sh`, `capture_provenance.sh`, `verify.sh`, `README.md`).
- Run any system on real study data.
- Touch the upstream live AEGIS working tree.

---

## Task 1: Confirm preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate
which python3                                    # must be inside .venv
hostname                                         # record in report
git -C "$HOME/Desktop/AEGIS" rev-parse --verify mandate-eval-primary-2026q2-v1^{commit}
ollama list | grep -E 'mandate-(intake|interpreter|decomp|procedure|binding|validation)'
```

**Success criteria.** `which python3` points into `.venv/bin/`; the tag resolves to commit `4f8af83`; `ollama list` shows all six `mandate-*` models. **On failure**, stop and write the missing piece into the report.

## Task 2: Recreate `AEGIS-eval/`

```zsh
bash setup/recreate_aegis_eval.sh --aegis "$HOME/Desktop/AEGIS"
```

If `AEGIS-eval/` already exists from a prior session and you have confirmed it is at commit `4f8af83`, skip with no error. Otherwise pass `--force` to wipe and recreate.

**Verification.**
```zsh
ls AEGIS-eval/_AEGIS_EVAL_README.txt
head -c 400 AEGIS-eval/configs/llm_defaults.json | python3 -m json.tool | head
test -f AEGIS-eval/rag/embeddings/enterprise-attack.jsonl && \
  echo "RAG index present: $(wc -c < AEGIS-eval/rag/embeddings/enterprise-attack.jsonl) bytes"
```

**Success criteria.** The marker file exists; `llm_defaults.json` is the frozen config (per-role temperatures Intake 0.0, Interpreter 0.1, Decomposition 0.2, Procedure 0.1, Binding 0.1, Validation 0.0); the RAG index is roughly 87 MB.

## Task 3: Deterministic-mode smoke

This proves MANDATE imports and runs end-to-end from the frozen tree, before invoking Ollama. It is fast (seconds) and isolates infrastructure problems from fine-tune problems.

```zsh
python3 apparatus/run_demo.py --aegis ./AEGIS-eval
```

**Success criteria.** "ReferenceSystem: 6 runs, 6 ok" and "MANDATE (det.): 6 runs, 6 ok, 6 roles captured per run, 0 runs with llm fallback."

**On failure.** Capture stderr in the report. Most likely cause is missing Python packages; rerun `bash setup/install.sh --aegis ./AEGIS-eval` (note: against `./AEGIS-eval`, not the live path).

## Task 4: A1 verification (Ollama mode, the audit-required re-run)

This is the main mission. It runs MANDATE-primary in Ollama mode against the six calibration tasks and verifies every fine-tuned role fired with no silent fallback.

```zsh
bash setup/run_a1_verification.sh
```

The verifier writes its report to `00_preregistration/a1_verification/`. The script forwards extra arguments, so if you need a different output directory pass `--out-dir`.

**Success criteria.**
- The console report ends with "A1 PASS."
- `00_preregistration/a1_verification/a1_report.json` exists and shows `pass: true`.
- Every per-run record has `any_llm_fallback: false` and `llm_used: true` on all six roles.
- The MANDATE-primary anchor differs from the deterministic anchor on each of the six calibration tasks (the verifier checks this).

**On failure.**
- If a role reports `llm_fallback=True`, the cause is almost always (a) the matching `mandate-*` model is not registered in Ollama, (b) `OLLAMA_BASE_URL` is wrong, or (c) `llm_fallback_enabled=true` masking a timeout. Record which role and which reason field in the report, halt, do not retry blindly.
- If A1 anchors match the deterministic anchors on every task, the fine-tuned models are not actually being used; record and halt.

## Task 5: Provenance refresh

With A1 PASS, refresh the freeze evidence against `AEGIS-eval`.

```zsh
bash setup/capture_provenance.sh --aegis ./AEGIS-eval
```

**Verification.**
```zsh
grep -E "tag|commit|ollama|sha256" 00_preregistration/provenance_evidence.md | head -30
```

**Success criteria.** `provenance_evidence.md` now records: tag `mandate-eval-primary-2026q2-v1`, commit `4f8af83`, Ollama version, six `mandate-*` model SHA-256 digests, and the resolved `decoding_params` (per-role temperatures from the frozen `llm_defaults.json`).

## Task 6: Apparatus suite on the eval host

```zsh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest apparatus -q --basetemp=/tmp/pt_handoff_$(date +%s) -p no:cacheprovider
```

**Success criteria.** 195 of 195 pass. Note any test that fails on the eval host but passed in the lead-analyst environment; that is a real signal, not noise.

**Known platform note.** If `statsmodels` raises `EOFError: marshal data too short` on import, clear its bytecode cache once: `find $(python3 -c "import statsmodels, os; print(os.path.dirname(statsmodels.__file__))") -name __pycache__ -type d -exec rm -rf {} +`. This is a known statsmodels artifact and is not a study issue.

## Task 7: Update the tracker

Edit `00_preregistration/TO_FILL_TRACKER.md`:

- Row **D3** (AEGIS tag): replace the housekeeping note with "Re-verified against `AEGIS-eval/` on the eval host on 2026-MM-DD. A1 PASS. Provenance refreshed."
- Row **D4** (model hashes) and **D5** (Ollama version): write the captured values from `provenance_evidence.md`, not a placeholder.
- Row **D10** (decoding parameters): leave RECOMMENDED until the PI signs; do not flip it to RESOLVED.

Do not edit other rows.

---

## Final report

Write `handoffs/HANDOFF_01_report_<YYYY-MM-DD>.md`. Required sections:

```markdown
# Handoff 01 Report: MANDATE Verification

**Codex session:** <id or short description>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- A1 verification:                   PASS | FAIL
- Apparatus unit suite:              <pass>/<total>
- Deterministic smoke:               PASS | FAIL
- AEGIS-eval commit captured:        <40-char sha>
- AEGIS-eval tag captured:           mandate-eval-primary-2026q2-v1
- Ollama version:                    <x.y.z>
- Six mandate-* SHA-256 digests:     listed in provenance_evidence.md
- Any role with llm_fallback=True:   <list, or "none">

## Anything the PI must decide before proceeding

<short bulleted list, empty if nothing>

## Deviations from this handoff

<short list, empty if none>
```

Commit the report to the project repository as part of the deposit record. Hand the verdict to the PI; if PROCEED, the next action is Handoff 02 (corpus pilot). If HALT, the report's escalation list is the action queue.
