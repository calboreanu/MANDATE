# Codex Handoff 02: Corpus Pilot (execution plan §13 action 7)

**For:** Codex
**From:** Lead Analyst
**Date:** 2026-06-01
**Estimated wall clock:** 10 to 30 minutes (mostly Claude API latency).
**Blocked on:** Handoff 01 reports PROCEED.

---

## Mission

Produce the six pilot tasks the Phase 0 pilot will use, plus a leakage audit against the MANDATE training corpus, so the pilot can begin as soon as the pre-registration is deposited. This is execution plan §13 action 7, and it is the first content-prep step that the apparatus is now ready for.

**Definition of done.** Three JSONL files of candidate pilot tasks under `03_corpus/pilot/`, one dedup report, one leakage audit report, and a structured handoff report. The Lead Analyst (Cal) selects two tasks per domain manually from the candidate set; Codex does not make that selection.

## Preconditions

Confirm each.

- Handoff 01 reported PROCEED. If A1 did not PASS, do not run this handoff.
- `ANTHROPIC_API_KEY` is set in the environment (`echo "${ANTHROPIC_API_KEY:0:6}..."` should print a prefix).
- `sentence-transformers` is installed in the venv (`python3 -c "import sentence_transformers"` succeeds). If not, install: `pip install sentence-transformers`. The model `sentence-transformers/all-MiniLM-L6-v2` downloads on first use (about 90 MB).
- `AEGIS-eval/training/seed_corpus.json` exists (the leakage audit's reference). Handoff 01 Task 2 produces it.

## Decision boundary

You may decide:
- The output paths under `03_corpus/pilot/` and the dedup / leakage report file names (use the canonical names below).
- A single retry on a transient Anthropic API error.

You must escalate:
- A leakage audit overlap rate above 5% (PROTOCOL_LOCK §13 halt rule). Codex does not substitute or regenerate tasks; the PI decides.
- Any Anthropic API rate-limit or auth error that persists after the single retry.
- Any candidate that is clearly off-domain or off-category (record in the report, do not edit the candidate).

You may not:
- Author tasks yourself, edit candidates after generation, or filter the candidate set. Selection is a manual SME-and-PI step on the candidate JSONL.
- Run the main 120-task corpus generation in this handoff. That is a separate, larger run gated on the hold-out domain decision and the SME calendar.

---

## Task 1: Confirm preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate
test -n "${ANTHROPIC_API_KEY:-}" && echo "key set" || echo "key MISSING"
python3 -c "import sentence_transformers; print('st', sentence_transformers.__version__)"
test -f AEGIS-eval/training/seed_corpus.json && echo "seed corpus present"
```

**Success criteria.** All three checks pass.
**On failure.** Key missing -> escalate to the PI to set `ANTHROPIC_API_KEY`. Sentence-transformers missing -> `pip install sentence-transformers`. Seed corpus missing -> Handoff 01 was not completed; run it first.

## Task 2: Generate pilot candidates (PROMPTS §1)

This is one PROMPTS §1 run per domain, category `full_specification`, model Claude Opus 4. Each run produces up to five candidates per domain, so the candidate set is up to 15 tasks; the Lead Analyst then picks two per domain for the six-task pilot.

```zsh
python3 -m apparatus.corpus.cli pilot --out 03_corpus/pilot
```

**Verification.**
```zsh
ls 03_corpus/pilot/
for f in 03_corpus/pilot/pilot_*.jsonl; do
  echo "=== $f ==="
  wc -l "$f"
  python3 -c "
import json, sys
for line in open(sys.argv[1]):
    d = json.loads(line)
    print('  cand', d['candidate_idx'], d['domain'], d['category'],
          repr(d['text'])[:80])
" "$f"
done
```

**Success criteria.** Three JSONL files exist, one per domain. Each contains roughly five candidates. Each candidate carries `domain`, `category=full_specification`, a non-empty `text`, and `source_model`.

**On failure.** A consistent zero-candidate result usually means the Anthropic API returned a non-numbered format; record the raw response and escalate. Single failed runs can be re-tried by re-running the command; the file is overwritten.

## Task 3: Dedup the candidate pool

```zsh
python3 -m apparatus.corpus.cli dedup \
  --in 03_corpus/pilot \
  --threshold 0.85 \
  --out 03_corpus/pilot/dedup_report.json \
  --kept-out 03_corpus/pilot/candidates_deduped.jsonl
```

**Success criteria.** `dedup_report.json` reports `embedder` is `sentence-transformer:sentence-transformers/all-MiniLM-L6-v2`, the kept count matches the dedup math, and dropped pairs all have similarity at or above 0.85.

**On failure.** If the embedder reports `HashEmbedder`, sentence-transformers did not import; stop and resolve the precondition.

## Task 4: Leakage audit against the training corpus

The reference is the frozen seed corpus the MANDATE fine-tunes were trained on, captured in `AEGIS-eval/training/seed_corpus.json`. The CLI understands the `examples[].payload.preprocessed_text` shape directly.

```zsh
python3 -m apparatus.corpus.cli leakage \
  --in 03_corpus/pilot/candidates_deduped.jsonl \
  --reference AEGIS-eval/training/seed_corpus.json \
  --threshold 0.85 \
  --out 03_corpus/pilot/leakage_audit.json
```

**Success criteria.** `leakage_audit.json` records `n_candidates`, `n_references`, `overlap_rate`, and `halt_triggered`. Overlap below 5% is the operational target.

**On halt-rule fire (overlap > 5%).** Stop. Write the flagged candidate indices and their best reference matches into the report. The PI decides whether to regenerate or substitute; Codex does neither.

## Task 5: Do not select; do not freeze

This handoff stops at producing the candidate set and the audit reports. The Lead Analyst selects two tasks per domain manually, by reading the candidates and recording the decision in the corpus log. Do not edit the candidate JSONL; do not delete unselected candidates; do not create `corpus_freeze_v1` here. Those steps are a separate handoff after PI selection.

---

## Final report

Write `handoffs/HANDOFF_02_report_<YYYY-MM-DD>.md`. Required sections:

```markdown
# Handoff 02 Report: Corpus Pilot

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- pilot candidates generated:        <n>  (target: ~15, lower bound 9)
- dedup embedder:                    sentence-transformer:all-MiniLM-L6-v2 | other
- dedup: kept / in / dropped:        <k>/<i>/<d>
- leakage threshold:                 0.85
- leakage overlap rate:              <pct>%
- leakage halt triggered:            yes | no
- Anthropic model used:              <exact model string>
- Anthropic input tokens (total):    <n>
- Anthropic output tokens (total):   <n>
- estimated API cost (USD):          $<x.xx>

## Flagged leakage matches (if any)

<list of {candidate_idx, best_ref_idx, similarity}, empty if none>

## Anything the PI must decide before proceeding

<short list. Always include: "select 2 candidates per domain from
03_corpus/pilot/candidates_deduped.jsonl">

## Deviations from this handoff

<short list, empty if none>
```

Commit the candidate JSONLs, both reports, and this handoff report. The PI's next action is the manual selection of the six pilot tasks; that selection unblocks Phase 0 once the pre-registration is deposited.
