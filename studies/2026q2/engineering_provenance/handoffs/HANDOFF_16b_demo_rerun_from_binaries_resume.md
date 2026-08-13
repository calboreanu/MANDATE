# Codex Handoff 16b: Demo re-run from original source binaries (resume after 16 halt)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 10 to 15 minutes (three Ollama runs plus comparison).
**Blocked on:** Handoff 16's `HALT` was recorded for the right reason under the handoff as written; this 16b removes the unnecessary precondition and continues. No new code or data is required.

---

## Why this exists

HANDOFF_16 Task 1 made `import docx` and `import pptx` (the python-docx and python-pptx libraries) a hard gate on the eval host. That was an over-broad precondition on my part. The runtime path for this handoff (`apparatus.run run-system --ollama-mode`) consumes the pre-built `.jsonl` indexes at `demo/<scenario>/rag/<scenario>__from_binaries.jsonl` and never invokes the text extractors. The extractors were used in the cowork sandbox to produce those indexes from the binaries; the eval host only needs them as a future option, not for this run.

Codex correctly halted under the handoff as written and committed the report cleanly (`520a4e7`). No config was swapped, no Ollama run was attempted, `AEGIS-eval/configs/llm_defaults.json` has no diff.

This handoff resumes from Task 2 with the precondition lifted. If `python-docx` and `python-pptx` are needed for a future from-binaries re-extraction on the eval host, install them then; not for this run.

## Mission (unchanged from 16)

Re-run all three demo scenarios (Volt Typhoon, CrowdStrike outage, SVB collapse) against the from-binaries Jaccard indexes already on disk, then diff the new RunRecords against the prior `output_ollama/` runs and write a single comparison report.

**Definition of done** is the same as HANDOFF_16's: three new RunRecord artifacts at `demo/<scenario>/output_ollama_from_binaries/mandate_primary__TASK-DEMO-<X>-001__r01.json`, each schema-valid with `llm_used=True` on every role and `any_llm_fallback=False`. One comparison report at `handoffs/HANDOFF_16b_report_<YYYY-MM-DD>.md`.

## Preconditions (revised)

Confirm each:

- Handoff 01 PROCEED.
- Ollama is running and the six `mandate-*` role models are loaded. (HANDOFF_16 Task 1 already verified this.)
- The three from-binaries indexes are present with the chunk counts HANDOFF_16 Task 1 confirmed: `volt_typhoon` 2,093, `crowdstrike_outage` 413, `svb_collapse` 619. (Already verified.)
- The three tasks files and the originals/ and from_binaries/ directories are populated. (Already verified.)
- `pypdf` imports. (Defensive only; not used at runtime in this handoff, but its absence would indicate a deeper venv problem.)

**`python-docx` and `python-pptx` are NOT preconditions for this handoff.** Do not halt on them. If you want to install them for completeness, `pip install python-docx python-pptx` works (they are pure-Python wheels), but it is not required.

## Decision boundary

Unchanged from HANDOFF_16.

---

## Task 1: Quick re-verify (the previously-confirmed inputs)

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

for S in volt_typhoon crowdstrike_outage svb_collapse; do
  IDX="demo/$S/rag/${S}__from_binaries.jsonl"
  echo "$S: $(wc -l < "$IDX") chunks  $IDX"
done

python3 -c "import pypdf; print('pypdf', pypdf.__version__)"
curl -sS http://localhost:11434/api/tags | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = sorted(m['name'] for m in d.get('models', []))
need = ['mandate-intake','mandate-interpreter','mandate-decomp','mandate-procedure','mandate-binding','mandate-validation']
missing = [n for n in need if not any(x.startswith(n) for x in names)]
print('models present:', len(names))
print('mandate-* missing:', missing if missing else 'none')
"
```

**Success criteria.** Chunk counts match (2,093 / 413 / 619), `pypdf` imports, Ollama lists all six `mandate-*` models. No halt on `docx` or `pptx`.

## Task 2: Run MANDATE-primary on each scenario

The three swap-and-run blocks from HANDOFF_16 Section 2 (Volt Typhoon, CrowdStrike, SVB) are unchanged. Reproduced verbatim for self-contained use.

### 2a — Volt Typhoon

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

cp AEGIS-eval/configs/llm_defaults.json AEGIS-eval/configs/llm_defaults.json.bak
python3 -c "
import json, pathlib
p = pathlib.Path('AEGIS-eval/configs/llm_defaults.json')
cfg = json.loads(p.read_text())
cfg['llm_rag_index'] = 'demo/volt_typhoon/rag/volt_typhoon__from_binaries.jsonl'
p.write_text(json.dumps(cfg, indent=2))
"

python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --tasks demo/volt_typhoon/tasks/tasks.jsonl \
  --runs 1 \
  --output demo/volt_typhoon/output_ollama_from_binaries \
  --code-ref demo-volt-typhoon-ollama-from-binaries \
  --ollama-mode

mv AEGIS-eval/configs/llm_defaults.json.bak AEGIS-eval/configs/llm_defaults.json
```

### 2b — CrowdStrike outage

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

cp AEGIS-eval/configs/llm_defaults.json AEGIS-eval/configs/llm_defaults.json.bak
python3 -c "
import json, pathlib
p = pathlib.Path('AEGIS-eval/configs/llm_defaults.json')
cfg = json.loads(p.read_text())
cfg['llm_rag_index'] = 'demo/crowdstrike_outage/rag/crowdstrike_outage__from_binaries.jsonl'
p.write_text(json.dumps(cfg, indent=2))
"

python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --tasks demo/crowdstrike_outage/tasks/tasks.jsonl \
  --runs 1 \
  --output demo/crowdstrike_outage/output_ollama_from_binaries \
  --code-ref demo-crowdstrike-outage-ollama-from-binaries \
  --ollama-mode

mv AEGIS-eval/configs/llm_defaults.json.bak AEGIS-eval/configs/llm_defaults.json
```

### 2c — SVB collapse

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

cp AEGIS-eval/configs/llm_defaults.json AEGIS-eval/configs/llm_defaults.json.bak
python3 -c "
import json, pathlib
p = pathlib.Path('AEGIS-eval/configs/llm_defaults.json')
cfg = json.loads(p.read_text())
cfg['llm_rag_index'] = 'demo/svb_collapse/rag/svb_collapse__from_binaries.jsonl'
p.write_text(json.dumps(cfg, indent=2))
"

python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --tasks demo/svb_collapse/tasks/tasks.jsonl \
  --runs 1 \
  --output demo/svb_collapse/output_ollama_from_binaries \
  --code-ref demo-svb-collapse-ollama-from-binaries \
  --ollama-mode

mv AEGIS-eval/configs/llm_defaults.json.bak AEGIS-eval/configs/llm_defaults.json
```

**Success criteria.** Each scenario emits `demo/<scenario>/output_ollama_from_binaries/mandate_primary__TASK-DEMO-<X>-001__r01.json` plus a `ledger.jsonl`. `"ok": true`, six roles with `llm_used=true`, Procedure-role `decoding_params.rag_retriever_wired=true`.

## Task 3: Sanity-check each RunRecord

Same as HANDOFF_16 Task 3 (loop the three records, print `ok`, `all_llm_used`, `any_llm_fallback`, `procedure.rag_retriever_wired`, `n_coas`, anchor lengths, validator rationale snippet). Reproduced for convenience:

```zsh
for S in volt_typhoon crowdstrike_outage svb_collapse; do
  REC=$(ls demo/$S/output_ollama_from_binaries/mandate_primary__TASK-DEMO-*__r01.json | head -1)
  python3 -c "
import json
r = json.load(open('$REC'))
roles = r.get('roles', [])
all_llm = all(role.get('llm_used') for role in roles)
any_fb = any(role.get('llm_fallback') for role in roles)
proc = next((role for role in roles if role.get('name')=='procedure'), {})
rag_wired = proc.get('decoding_params', {}).get('rag_retriever_wired')
out = r.get('output', {})
coas = out.get('courses_of_action', [])
anchor = out.get('anchor', {})
print('$S:')
print('  ok=', r.get('ok'))
print('  all_llm_used=', all_llm)
print('  any_llm_fallback=', any_fb)
print('  procedure.rag_retriever_wired=', rag_wired)
print('  n_coas=', len(coas))
print('  anchor.minimum_chars=', len(str(anchor.get('minimum',''))))
print('  validator_rationale=', (r.get('output',{}).get('recommendation',{}).get('rationale','') or '')[:240])
"
done
```

## Task 4: Restore `llm_defaults.json`

```zsh
git diff -- AEGIS-eval/configs/llm_defaults.json
```

If a diff is present, `git checkout AEGIS-eval/configs/llm_defaults.json`.

## Task 5: Comparison report

Same as HANDOFF_16 Task 5: tabulate prior `output_ollama/` vs new `output_ollama_from_binaries/` on `ok`, `wall_clock_ms`, `n_coas`, `coa1_name`, anchor lengths, constraints count, validator rationale. Reproduced verbatim:

```zsh
python3 - <<'PY'
import json, os
SCN = [
    ("volt_typhoon",       "TASK-DEMO-VOLT-001"),
    ("crowdstrike_outage", "TASK-DEMO-CRWD-001"),
    ("svb_collapse",       "TASK-DEMO-SVB-001"),
]

def load_rec(path):
    if not os.path.exists(path): return None
    return json.load(open(path))

def summarize(r):
    if r is None: return None
    out = r.get("output", {})
    coas = out.get("courses_of_action", [])
    anchor = out.get("anchor", {})
    rec = out.get("recommendation", {})
    return {
        "ok": r.get("ok"),
        "wall_clock_ms": r.get("wall_clock_ms"),
        "n_coas": len(coas),
        "coa1_name": (coas[0].get("name") if coas else None),
        "anchor_min_chars": len(str(anchor.get("minimum",""))),
        "anchor_tgt_chars": len(str(anchor.get("target",""))),
        "n_constraints": len(anchor.get("constraints", []) or []),
        "validator_rationale": (rec.get("rationale","") or "")[:240],
    }

print("| scenario | metric | prior output_ollama | new from_binaries |")
print("|---|---|---|---|")
for s, tid in SCN:
    prior = load_rec(f"demo/{s}/output_ollama/mandate_primary__{tid}__r01.json")
    newr = load_rec(f"demo/{s}/output_ollama_from_binaries/mandate_primary__{tid}__r01.json")
    p, n = summarize(prior), summarize(newr)
    if p is None or n is None:
        print(f"| {s} | (missing artifact) | {p} | {n} |")
        continue
    for k in ["ok","wall_clock_ms","n_coas","coa1_name","anchor_min_chars",
              "anchor_tgt_chars","n_constraints","validator_rationale"]:
        pv = str(p.get(k,""))[:80]
        nv = str(n.get(k,""))[:80]
        marker = "" if pv==nv else " *"
        print(f"| {s} | {k} | {pv}{marker} | {nv}{marker} |")
PY
```

Three substantive questions to answer in prose (same as HANDOFF_16 Task 5):

1. Cross-domain single-COA finding under binary-sourced inputs — reaffirmed, invalidated, or partial?
2. Validator gap-acknowledgment delta on CrowdStrike and SVB?
3. SVB anchor distillation — still deterministic-prefix shape, or cleaner now?

## Final report

Write `handoffs/HANDOFF_16b_report_<YYYY-MM-DD>.md` using the HANDOFF_16 report template, with one extra line under Evidence:

```
- HANDOFF_16 halt resolved (python-docx/pptx not required for runtime): yes
```

Commit message: `Handoff 16b: demo re-run from original source binaries (resume after 16 halt)`.
