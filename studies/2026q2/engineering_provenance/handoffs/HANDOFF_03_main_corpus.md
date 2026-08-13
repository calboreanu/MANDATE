# Codex Handoff 03: Main Corpus Authoring (120 tasks, source-first)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** 90 to 150 minutes (mostly source fetches and 270 source-conditioned Anthropic calls).
**Blocked on:** Handoff 06 PROCEED, the refined source list confirmed by the PI (see "Open precondition" below), `pypdf` and `sentence-transformers` already installed from prior handoffs.

---

## Mission

Author the source-first 120-task main corpus across the three pre-registered domains (`security_operations_reporting`, `financial_reporting`, `intelligence_collection_tasking`). Every candidate is derived from a real public source document (PROMPTS Section 1 post-reconciliation; see `_package/RECONCILIATION_LOG.md` Change 9). Codex produces the deduped candidate pool; the Lead Analyst's manual 40-per-domain selection, the SME realism audit, and the `corpus_freeze_v1` tag are out of scope for this session.

**Definition of done.** A deduped pool of approximately 200 candidates after dedup at `03_corpus/main/candidates_main.jsonl`, with each candidate carrying a canonical `derived_from` reference. Per-domain breakdown is sufficient for the PI to select 40 per domain (a pool of 60+ per domain after dedup is the target). One handoff report.

## Open precondition: intel source coverage

The pilot ran with three working intel sources (ODNI Annual Threat Assessment 2024, ATA 2025, intelligence.gov "How the IC Works" HTML). Seven of the curated intel URLs (JCS.mil Joint Publications, CIA static-CDN tradecraft documents, GAO HTML, the other intelligence.gov page) failed from the eval host's network in two attempts. Three sources are acceptable for the six-task pilot's dry-run; 40 intel candidates derived from those three is thin for the main corpus.

**Before running Handoff 03,** the PI confirms one of:

A. **Proceed with the current three intel sources.** The main corpus carries the limitation in the corpus log and the deposit. Reviewer-visible note recommended.

B. **Expand the intel source list via manual ingestion.** Handoff 07d established that the eval-host venv cannot fetch the JCS Joint Publications, CIA static-CDN tradecraft documents, GAO HTML, and most dni.gov PDFs (403 / 404). Browser fetch on the PI's workstation works for these files; the corpus authoring pipeline supports importing them through `apparatus.corpus.cli ingest-manual`. Workflow on the PI's Mac (which is the eval host):

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. write the manifest template once
python3 -m apparatus.corpus.cli ingest-manual \
  --domain intelligence_collection_tasking --init-manifest
# Edit rag/sources/intelligence_collection_tasking/manual/manual_sources_manifest.json
# Add one entry per PDF the PI plans to download (title, url, tier).

# 2. download the PDFs in Safari and place them in
#    rag/sources/intelligence_collection_tasking/manual/
#    Filenames must match the "filename" field in the manifest entries.

# 3. ingest + rebuild the intel index
python3 -m apparatus.corpus.cli ingest-manual \
  --domain intelligence_collection_tasking --rebuild-index
```

A reasonable PI shortlist to download in Safari (each verified to render in a browser; the manual ingest path then captures their SHA-256 for the replication package):

- JCS Joint Publication 2-0 (Joint Intelligence), `https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_0.pdf`
- JCS Joint Publication 2-01 (Joint and National Intelligence Support to Military Operations), `https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01.pdf`
- JCS Joint Publication 2-01.3 (Joint Intelligence Preparation of the Operational Environment), `https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01_3.pdf`
- ODNI ICD 203 (Analytic Standards), search dni.gov for the current canonical URL
- ODNI ICD 204 (National Intelligence Priorities Framework), as above
- ODNI ICD 208 (Maximizing the Utility of Analytic Products), as above
- GAO Intelligence Community Information Sharing report, `https://www.gao.gov/products/gao-21-104450`

Six to eight ingested PDFs plus the three fetched intel sources puts intel coverage at parity with security and finance. The manual ingest pathway commits the PDFs themselves into the replication package alongside their SHA-256 digests; reviewers verify each PDF's hash against an authoritative copy at the recorded URL, which is stronger provenance than refetching a moving target.

Codex does not add URLs to the curated list or download PDFs on its own; PI sign-off is required. The handoff resumes after the PI's manual ingest finishes and the refreshed `rag/embeddings/intelligence_collection_tasking.jsonl` is committed.

## Preconditions (after the open precondition is resolved)

Confirm each:

- Handoff 06 reported PROCEED (the pilot scaffolding ran end-to-end with source-first candidates).
- `apparatus/corpus/sources/curated_sources.py` reflects the PI-confirmed source list. The reconciliation note at the bottom of the file lists what changed since 07c.
- `ANTHROPIC_API_KEY` is in `.env` (the CLI auto-loads it).
- `pypdf` and `sentence-transformers` import in the venv.
- The pilot's source-first index files at `rag/embeddings/<domain>.jsonl` are present from 07c. They are rebuilt fresh below as part of Task 2.

## Decision boundary

You may decide:
- Output paths inside the documented tree.
- One retry per URL on a transient HTTP error.
- The exact `--n-chunks` value within the documented range (default 30, up to 40).

You must escalate (write into the report and stop the relevant section):
- A leakage audit overlap rate above 5% (PROTOCOL_LOCK Section 13).
- A per-domain URL failure rate above 30% (the threshold matches Handoff 07b's lesson; if intel had only three of ten working before and the PI did not expand the list, intel will trip this and the report will say so explicitly).
- A persistent Anthropic auth or rate-limit error.
- Anything that would change a TO_FILL row from RESOLVED back to OPEN.

You may not:
- Add URLs to `apparatus/corpus/sources/curated_sources.py` (PI sign-off required).
- Make the 40-per-domain selection. The deduped pool is the deliverable; the PI selects.
- Tag `corpus_freeze_v1`. That tag is a separate PI action gated on selection and the SME realism audit.
- Run any baseline calibration, perturbation generation, or system runs on study data.

---

## Task 1: Confirm preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate
python3 -c "
import os
from apparatus.corpus.cli import _load_dotenv
_load_dotenv()
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'key missing'
import sentence_transformers, pypdf
print('preconditions OK: key set, sentence-transformers', sentence_transformers.__version__,
      ', pypdf', pypdf.__version__)
"
test -f handoffs/HANDOFF_06_report_*.md && echo "handoff 06 report present"
git -C "$PWD" log --oneline -5 apparatus/corpus/sources/curated_sources.py
```

**Success criteria.** Preconditions print OK; the most recent commit on `curated_sources.py` shows the PI-confirmed source list update (or 07c's commit if the PI chose to proceed with the three intel sources).

## Task 2: Rebuild all three per-domain source indexes

The pilot used the same per-domain indexes the main corpus draws from. Rebuilding here ensures the main run uses the current curated_sources.py and that any URL the PI added is fetched. The fetcher's polite 0.5 s sleep between requests is built in.

```zsh
mkdir -p rag/sources rag/embeddings 03_corpus/main 03_corpus/candidates_source_first_main
rm -rf rag/sources/security_operations_reporting \
       rag/sources/financial_reporting \
       rag/sources/intelligence_collection_tasking
rm -f rag/embeddings/security_operations_reporting.jsonl \
      rag/embeddings/financial_reporting.jsonl \
      rag/embeddings/intelligence_collection_tasking.jsonl \
      rag/embeddings/build_report.json

python3 -m apparatus.corpus.cli source-build \
  --domain security_operations_reporting \
  --domain financial_reporting \
  --domain intelligence_collection_tasking \
  --project-root "$PWD" \
  --out rag/embeddings/build_report.json
```

**Success criteria.**
- Per-domain `rag/sources/<domain>/` directories carry one `.txt` per successfully fetched URL.
- Per-domain `rag/embeddings/<domain>.jsonl` exists with chunks.
- `build_report.json` records each URL with `ok: true` or `ok: false` plus the error.
- For every domain, the URL failure rate is at or below 30%. **If any domain exceeds 30%, stop and write the failed URLs into the report.** (Intel will trip this if the PI did not expand the list; that is the documented limitation.)

## Task 3: Source-conditioned candidate generation, main-corpus scale

Nine runs: three domains times three categories. The main corpus targets 30 chunks per (domain × category), yielding ~270 candidates pre-dedup so the PI has ~200+ post-dedup to select 40 per domain from.

```zsh
for DOM in security_operations_reporting financial_reporting \
          intelligence_collection_tasking; do
  for CAT in full_specification gap_triggering stretch_case; do
    python3 -m apparatus.corpus.cli source-generate \
      --domain $DOM --category $CAT --n-chunks 30 \
      --seed 20260603 \
      --project-root "$PWD" \
      --out 03_corpus/candidates_source_first_main
  done
done
```

**Success criteria.** Nine JSONL files under `03_corpus/candidates_source_first_main/`, each with up to 30 candidates. Every candidate carries `derived_from.reference_id`, `derived_from.source`, `derived_from.name`, and `derived_from.content_preview`.

## Task 4: Dedup and leakage audit across the main-corpus pool

```zsh
python3 -m apparatus.corpus.cli dedup \
  --in 03_corpus/candidates_source_first_main \
  --threshold 0.85 \
  --out 03_corpus/main/dedup_report.json \
  --kept-out 03_corpus/main/candidates_main.jsonl

python3 -m apparatus.corpus.cli leakage \
  --in 03_corpus/main/candidates_main.jsonl \
  --reference AEGIS-eval/training/seed_corpus.json \
  --threshold 0.85 \
  --out 03_corpus/main/leakage_audit.json
```

**Success criteria.** Dedup writes a kept count above 200 (out of ~270 in). Leakage `overlap_rate` is at or below 0.05; on halt, the flagged candidate indices are listed in the report.

## Task 5: Sanity (per-domain coverage and derivation)

```zsh
python3 -c "
import json, collections
rows = [json.loads(l) for l in open('03_corpus/main/candidates_main.jsonl')]
n = len(rows)
with_d = sum(1 for r in rows
             if r.get('derived_from', {}).get('reference_id'))
by_dom = collections.Counter(r['domain'] for r in rows)
by_dc  = collections.Counter((r['domain'], r['category']) for r in rows)
print('candidates:', n, ' with derived_from:', with_d)
print('per domain:', dict(by_dom))
print('per (domain, category):')
for k in sorted(by_dc): print('  %-32s %-22s n=%d' % (k[0], k[1], by_dc[k]))
assert with_d == n
for d, c in by_dom.items():
    assert c >= 50, f'{d} has only {c} candidates; pool too thin for 40-per-domain selection'
"
```

**Success criteria.** Every candidate has `derived_from`. Every domain has at least 50 candidates so the PI has selection room.

---

## Final report

Write `handoffs/HANDOFF_03_report_<YYYY-MM-DD>.md` using the same template shape as 07 and 07c. Required sections:

```markdown
# Handoff 03 Report: Main Corpus Authoring

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- per-domain URLs fetched / failed:      sec=<n>/<f>, fin=<n>/<f>, int=<n>/<f>
- per-domain failure rate:               sec=<pct>%, fin=<pct>%, int=<pct>%
- per-domain chunks indexed:             sec=<n>, fin=<n>, int=<n>
- candidates generated per (dom x cat):  9 files, totals <list>
- dedup kept / in / dropped:             <k>/<i>/<d>
- per-domain kept:                       sec=<n>, fin=<n>, int=<n>
- leakage threshold:                     0.85
- leakage overlap rate:                  <pct>%
- leakage halt triggered:                yes | no
- every candidate has derived_from:      yes | no
- Anthropic model used:                  claude-opus-4-6
- Anthropic input tokens (total):        <n>
- Anthropic output tokens (total):       <n>
- estimated API cost (USD):              $<x.xx>

## Failed URLs

<list of {url, reason}, empty if none>

## Anything the PI must decide before proceeding

- review the main candidate pool at 03_corpus/main/candidates_main.jsonl
- select 40 per domain (approximately 14 per category) and write
  03_corpus/main/main_selection.json
- run the SME realism audit on the selected 120 tasks
- after the realism audit passes, tag corpus_freeze_v1

## Deviations from this handoff

<short list, empty if none>
```

Commit the rebuilt source texts and indexes, the build report, the new candidate files, the dedup and leakage reports, and the handoff report in a single commit with message `Handoff 03: source-first main corpus authoring (~200 candidate pool)`.

---

## What this handoff explicitly does not do

For clarity, since the main corpus has more downstream PI steps than the pilot:

- It does not select the 40-per-domain main set. The PI does that on the candidate pool, the same way the pilot's six-task selection works.
- It does not run the SME realism audit. The realism rating (FORMS Section 4) is human work, separate handoff template.
- It does not tag `corpus_freeze_v1`. That tag is a PI action gated on the realism audit passing and Cal signing off in writing (PROTOCOL_LOCK Section 13).
- It does not generate the 30-task hold-out 4th-domain corpus. That is a separate handoff once the hold-out domain decision (Decisions memo Section 1) lands.
- It does not generate the 350-perturbation suite. That is a Phase 5 handoff that draws from `corpus_freeze_v1`.
