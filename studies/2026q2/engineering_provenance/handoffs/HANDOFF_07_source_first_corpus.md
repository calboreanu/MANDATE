# Codex Handoff 07: Source-First Corpus Authoring (PROMPTS Section 1 post-reconciliation)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** 60 to 120 minutes (mostly the source downloads and the source-conditioned Anthropic calls).
**Blocked on:** Handoff 01 PROCEED, `pypdf` installable in the venv, network access to the curated source URLs.

---

## Mission

Implement the source-first corpus authoring directive: every candidate task is derived from a real public source document. Build the per-domain authoritative source corpora from the curated URL list in `apparatus.corpus.sources.curated_sources`, build AEGIS-format Jaccard indexes per domain, then run the source-conditioned PROMPTS Section 1 prompt to generate candidate pools for the pilot. The 15 synthetic pilot candidates produced by Handoff 02 are explicitly superseded; this handoff replaces them.

**Definition of done.** Per-domain raw source texts under `rag/sources/<domain>/`, AEGIS-format chunk indexes at `rag/embeddings/<domain>.jsonl`, a cross-domain build report at `rag/embeddings/build_report.json` listing every URL with `ok` or the failure reason, and a fresh source-derived pilot candidate pool at `03_corpus/pilot/candidates_source_first_<domain>_<category>.jsonl` for every (domain × category). Each candidate carries a canonical `derived_from` reference. One handoff report.

**Reconciliation reference.** PROMPTS Section 1 was reconciled on 2026-06-03 from synthetic generation to source-conditioned generation; see `_package/RECONCILIATION_LOG.md` Change 9 and `_package/PROMPTS.md` Section 1 and 1.1.

## Preconditions

Confirm each:

- Handoff 01 PROCEED (the apparatus suite and the deterministic smoke have passed on this eval host).
- `pip install pypdf` succeeds in the project venv. `pypdf` is pure Python; no system packages are needed.
- `ANTHROPIC_API_KEY` is present (the CLI auto-loads `.env`).
- Outbound HTTPS to `nvlpubs.nist.gov`, `www.govinfo.gov`, `pcaobus.org`, `www.sec.gov`, `www.dni.gov`, `www.cisa.gov`, `irp.fas.org`, `crsreports.congress.gov`, `www.whitehouse.gov`, `www.coso.org`, `fasb.org`, and `d3fend.mitre.org` is allowed. If your network blocks any of these, record the block as a failed fetch; do not substitute.

## Decision boundary

You may decide:
- One retry on a transient HTTP error per URL (timeout or HTTP 5xx). Multiple retries are not authorized.
- Output paths inside the documented tree.
- The number of generated candidates per (domain × category): default 25, which produces a ~225-candidate pool across the three domains. The PI selects the pilot from this pool.

You must escalate:
- A leakage audit overlap rate above 5% after the source-first generation. Stop and write the failed candidates into the report.
- Any source URL that returns a redirect-to-login, a paywall, or a non-document (HTML error page). Record the URL with the failure reason; do not invent content from a different source.
- A persistent Anthropic API auth or rate-limit error.

You may not:
- Add URLs to `apparatus/corpus/sources/curated_sources.py` (PI sign-off required for the source set).
- Edit the generated candidate text after generation. Selection is the PI's manual step.
- Run the main 120-task corpus authoring or the hold-out 30-task authoring in this handoff. Those are separate handoffs once the pilot validates the source-first flow.

---

## Task 1: Preconditions and pypdf install

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate
python3 -c "
import os
from apparatus.corpus.cli import _load_dotenv
_load_dotenv()
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'key missing'
print('key set')
"
pip install pypdf
python3 -c "import pypdf; print('pypdf', pypdf.__version__)"
```

**Success criteria.** `key set` prints; `pypdf` imports.

## Task 2: Build the per-domain source indexes

This fetches every URL in the curated list, extracts text (HTML or PDF), and builds the per-domain AEGIS-format Jaccard chunk index. Polite half-second sleep between requests is built into the fetcher.

```zsh
python3 -m apparatus.corpus.cli source-build \
  --domain security_operations_reporting \
  --domain financial_reporting \
  --domain intelligence_collection_tasking \
  --project-root "$PWD" \
  --out rag/embeddings/build_report.json
```

**Success criteria.**
- `rag/sources/<domain>/` carries one `.txt` per successfully fetched URL.
- `rag/embeddings/<domain>.jsonl` exists per domain and is non-empty.
- `rag/embeddings/build_report.json` lists every URL with `ok: true` or `ok: false`; failed URLs carry an `error` field naming the cause.

**On a failure.** A single failed URL does not stop the build. The other URLs proceed and their content lands in the index. If an entire domain's fetches fail (network is blocked), stop and report.

## Task 3: Source-conditioned candidate generation per (domain × category)

Nine runs total: three domains times three categories. Each run draws a deterministic chunk sample from the domain index and calls Claude Opus 4-6 with the source-conditioned PROMPTS Section 1 prompt.

```zsh
for DOM in security_operations_reporting financial_reporting \
          intelligence_collection_tasking; do
  for CAT in full_specification gap_triggering stretch_case; do
    python3 -m apparatus.corpus.cli source-generate \
      --domain $DOM --category $CAT --n-chunks 25 \
      --project-root "$PWD" \
      --out 03_corpus/candidates_source_first
  done
done
```

**Success criteria.** Nine JSONL files under `03_corpus/candidates_source_first/`, one per (domain × category), each with ~25 candidates. Each candidate carries a `derived_from` object with `reference_id`, `source`, `name`, and `content_preview`.

## Task 4: Dedup and leakage audit on the source-first pool

Dedup runs across all nine files. Leakage audits against the MANDATE training corpus, the same as Handoff 02.

```zsh
python3 -m apparatus.corpus.cli dedup \
  --in 03_corpus/candidates_source_first \
  --threshold 0.85 \
  --out 03_corpus/candidates_source_first/dedup_report.json \
  --kept-out 03_corpus/candidates_source_first/candidates_deduped.jsonl

python3 -m apparatus.corpus.cli leakage \
  --in 03_corpus/candidates_source_first/candidates_deduped.jsonl \
  --reference AEGIS-eval/training/seed_corpus.json \
  --threshold 0.85 \
  --out 03_corpus/candidates_source_first/leakage_audit.json
```

**Success criteria.** Dedup report records the kept pool size; leakage `overlap_rate` is at or below 0.05. The leakage halt rule (overlap above 5%) is the same as Handoff 02; on halt, write the flagged indices into the report.

## Task 5: Replace the pilot pool

Move the source-first deduplicated pool into the canonical pilot path. The synthetic pilot files at `03_corpus/pilot/` are retained as the historical record (the `SUPERSEDED.md` already in that directory documents the supersession); the new files replace `candidates_with_sources.jsonl` so Handoff 06 picks them up by its existing precondition.

```zsh
cp 03_corpus/candidates_source_first/candidates_deduped.jsonl \
   03_corpus/pilot/candidates_with_sources.jsonl
cp 03_corpus/candidates_source_first/dedup_report.json \
   03_corpus/pilot/dedup_report_source_first.json
cp 03_corpus/candidates_source_first/leakage_audit.json \
   03_corpus/pilot/leakage_audit_source_first.json
```

**Success criteria.** `03_corpus/pilot/candidates_with_sources.jsonl` now points at the source-first deduped pool. `SUPERSEDED.md` remains in `03_corpus/pilot/`.

## Task 6: Sanity (each candidate has a derived_from reference)

```zsh
python3 -c "
import json, collections
rows = [json.loads(l) for l in open(
    '03_corpus/pilot/candidates_with_sources.jsonl')]
n = len(rows)
with_d = sum(1 for r in rows if r.get('derived_from', {}).get('reference_id'))
print('candidates:', n, 'with derived_from:', with_d)
by_dom = collections.Counter(r['domain'] for r in rows)
print('per domain:', dict(by_dom))
assert with_d == n, 'every candidate must carry a derived_from'
"
```

**Success criteria.** Every candidate carries a non-empty `derived_from.reference_id`. The per-domain count is reported.

---

## Final report

Write `handoffs/HANDOFF_07_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 07 Report: Source-First Corpus Authoring

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- pypdf installed:                       <version>
- per-domain URLs fetched / failed:      sec=<n>/<f>, fin=<n>/<f>, int=<n>/<f>
- per-domain chunks indexed:             sec=<n>, fin=<n>, int=<n>
- candidates generated per (dom x cat):  9 files, totals <list>
- dedup kept / in / dropped:             <k>/<i>/<d>
- leakage threshold:                     0.85
- leakage overlap rate:                  <pct>%
- leakage halt triggered:                yes | no
- every candidate has derived_from:      yes | no
- Anthropic model used:                  claude-opus-4-6
- Anthropic input tokens (total):        <n>
- Anthropic output tokens (total):       <n>
- estimated API cost (USD):              $<x.xx>

## Failed URLs

<list of {url, reason} for every failed fetch, empty if none>

## Anything the PI must decide before proceeding

- review the source-first deduped pool at
  03_corpus/pilot/candidates_with_sources.jsonl
- select 6 candidates (2 per domain) and write
  03_corpus/pilot/pilot_selection.json (Handoff 06 then runs)

## Deviations from this handoff

<short list, empty if none>
```

Commit the source texts, the indexes, the build report, the candidate files, dedup/leakage reports, and the handoff report. Single commit message: `Handoff 07: source-first corpus authoring (PROMPTS §1 post-reconciliation)`.
