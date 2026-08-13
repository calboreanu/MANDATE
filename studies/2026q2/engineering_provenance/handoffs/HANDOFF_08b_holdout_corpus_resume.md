# Codex Handoff 08b: Hold-out corpus, resume after 08 halt

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 30 to 60 minutes (same as HANDOFF_08 — registry fix is already in place).
**Blocked on:** None. HANDOFF_08's registry gap is closed.

---

## Why this exists

HANDOFF_08 halted because `apparatus.corpus.prompts.DOMAIN_GUIDANCE` did not list `software_engineering_specification`, even though `CURATED_SOURCES` did. The `source-build` and `source-generate` CLI subcommands both gate on `DOMAIN_GUIDANCE`, so the configured hold-out domain was rejected as unknown.

The registry gap is fixed on project main (sandbox-side patch, committed before this handoff). The patch:

- Adds the `software_engineering_specification` entry to `DOMAIN_GUIDANCE` matching the existing three-domain pattern (one sentence on document types, one on stakeholders).
- Updates `test_three_canonical_domains_only` to `test_corpus_domains_match_curated_sources` — a stronger invariant that asserts `set(DOMAIN_GUIDANCE) == set(CURATED_SOURCES)`, so future drift between the two registries fails fast.
- The 18 existing `tests/test_corpus.py` cases still pass under the new invariant.

This handoff re-executes the original HANDOFF_08 body verbatim.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

python3 -c "
from apparatus.corpus.prompts import DOMAIN_GUIDANCE
from apparatus.corpus.sources.curated_sources import CURATED_SOURCES
assert set(DOMAIN_GUIDANCE) == set(CURATED_SOURCES) == {
    'security_operations_reporting', 'financial_reporting',
    'intelligence_collection_tasking', 'software_engineering_specification'
}, 'registry mismatch — abort'
print('registries aligned:', sorted(DOMAIN_GUIDANCE))
"

python3 -m pytest apparatus/corpus/tests/test_corpus.py -q 2>&1 | tail -3
grep -E "^ANTHROPIC_API_KEY=" .env >/dev/null && echo "ANTHROPIC key set"
```

**Success criteria.** The registry-alignment assertion passes; corpus tests print `18 passed`; Anthropic key is set. If any check fails, do not proceed; report and stop.

## Tasks

Identical to HANDOFF_08 Tasks. Reproduced for self-contained use.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. Build the hold-out domain source index
python3 -m apparatus.corpus.cli source-build \
  --domain software_engineering_specification \
  --project-root "$PWD" \
  --out rag/embeddings/build_report_holdout.json

# 2. Generate candidates: 3 categories x 15 chunks each = 45 candidates
mkdir -p 03_corpus/holdout 03_corpus/candidates_source_first_holdout
SEED=20260603
for CAT in full_specification gap_triggering stretch_case; do
  python3 -m apparatus.corpus.cli source-generate \
    --domain software_engineering_specification \
    --category $CAT --n-chunks 15 --seed $SEED \
    --project-root "$PWD" \
    --out 03_corpus/candidates_source_first_holdout
  SEED=$((SEED+1))
done

# 3. Dedup + leakage audit
python3 -m apparatus.corpus.cli dedup \
  --in 03_corpus/candidates_source_first_holdout \
  --threshold 0.85 \
  --out 03_corpus/holdout/dedup_report.json \
  --kept-out 03_corpus/holdout/candidates_holdout.jsonl

python3 -m apparatus.corpus.cli leakage \
  --in 03_corpus/holdout/candidates_holdout.jsonl \
  --reference AEGIS-eval/training/seed_corpus.json \
  --threshold 0.85 \
  --out 03_corpus/holdout/leakage_audit.json
```

**Success criteria.** `03_corpus/holdout/candidates_holdout.jsonl` exists with at least 35 candidates, every candidate carrying `derived_from.reference_id`, leakage overlap rate at or below 0.05.

**Decision boundary.** Same as HANDOFF_08:
- Retry once on transient HTTP / 5xx during `source-build` URL fetches; multiple retries not authorized.
- A leakage overlap rate above 5% is a halt. Stop and write the flagged indices into the report; do not select the pool.
- Anthropic API rate-limit errors that persist after one retry are an escalation.

## Final report

Write `handoffs/HANDOFF_08b_report_<YYYY-MM-DD>.md` with the same template HANDOFF_08 specified:

```markdown
# Handoff 08b Report: Hold-out corpus (software_engineering_specification)

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- registry gap closed (precondition):       yes
- SE-domain URLs fetched / failed:          <n>/<f>
- candidates generated per (category):      <full_specification>/<gap_triggering>/<stretch_case>
- dedup kept / in / dropped:                <k>/<i>/<d>
- leakage threshold:                        0.85
- leakage overlap rate:                     <pct>%
- leakage halt triggered:                   yes | no
- every candidate has derived_from:         yes | no
- Anthropic model used:                     claude-opus-4-6
- Anthropic input tokens (total):           <n>
- Anthropic output tokens (total):          <n>
- estimated API cost (USD):                 $<x.xx>

## Failed URLs

<list of {url, reason} for every failed fetch, empty if none>

## Anything the PI must decide before proceeding

- Review the deduped pool at 03_corpus/holdout/candidates_holdout.jsonl and select 30 candidates for the hold-out task set.

## Deviations from this handoff

<short list, empty if none>
```

Commit message: `Handoff 08b: hold-out corpus (software_engineering_specification, resume after 08 halt)`.
