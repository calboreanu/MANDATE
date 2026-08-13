# Codex Handoff 16: Demo re-run from original source binaries

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 12 to 18 minutes (~3.5 minutes per scenario Ollama run, plus the comparison step).
**Blocked on:** Handoff 01 PROCEED, the six `mandate-*` Ollama models loaded, `pypdf` / `python-docx` / `python-pptx` installable in the venv.

---

## Mission

Re-run all three demo scenarios (Volt Typhoon, CrowdStrike outage, SVB collapse) against fresh RAG indexes built from the original source binaries on disk, then diff the new RunRecords against the prior `output_ollama/` runs and write a single comparison report.

The prior demo runs (HANDOFF_25/26/28 task numbers in the cowork tracker) consumed `.txt` extracts that were produced through `mcp web_fetch`'s text-mode rendering. The PI requested a real chain-of-custody pass: starting from the actual PDF, DOCX, PPTX, HTML binaries on disk at `demo/<scenario>/sources/originals/`, run them through the apparatus's production extractors (`apparatus.corpus.sources.fetch.extract_pdf_text`, `extract_docx_text`, `extract_pptx_text`, `extract_html_text`), rebuild the Jaccard indexes, then re-run MANDATE-primary in Ollama mode. The binary→text→index half has already been executed in the cowork sandbox; this handoff covers the eval-host Ollama runs and the comparison.

**Definition of done.** Three new RunRecord artifacts at `demo/<scenario>/output_ollama_from_binaries/mandate_primary__TASK-DEMO-<X>-001__r01.json`, each schema-valid mandate-as-code with `llm_used=True` on every role and `any_llm_fallback=False`. One comparison report at `handoffs/HANDOFF_16_report_<YYYY-MM-DD>.md` covering: anchor delta, COA-count delta, validator-rationale delta, gap-acknowledgment delta versus the prior `output_ollama/` artifacts. The cross-domain single-COA finding is either reaffirmed or invalidated.

**Background reference.** `demo/RERUN_FROM_BINARIES.md`, `demo/SOURCE_BINARIES_INVENTORY.md`, `demo/MANDATE_DEMO_FINDINGS.md`, and `demo/UPSTREAM_MANDATE_NOTE_decomposition_bias.md` describe the work this handoff completes.

## Preconditions

Confirm each:

- Handoff 01 PROCEED (the apparatus suite and the deterministic smoke have passed on this eval host).
- Ollama is running at `http://localhost:11434` and the six `mandate-intake`, `mandate-interpreter`, `mandate-decomp`, `mandate-procedure`, `mandate-binding`, `mandate-validation` role models are loaded.
- The from-binaries indexes are present at the three paths in Task 1; if any is missing or zero-length, halt and report.
- `pypdf`, `python-docx`, `python-pptx` import cleanly in the project venv. The cowork-side extraction already validated these; this is a defense-in-depth check.

## Decision boundary

You may decide:
- One retry on a transient Ollama timeout per scenario.
- Whether to run the three scenarios serially or in parallel (serial is recommended for stable wall-clock comparison; parallel is acceptable if Ollama queue depth allows).
- Comparison formatting beyond what Task 5 prescribes.

You must escalate:
- Any role reporting `llm_used=False` or `any_llm_fallback=True` on the from-binaries runs. Stop, save the partial artifact, and put the role names in the report.
- A from-binaries index whose chunk count differs by more than 20% from what `demo/<scenario>/sources/FROM_BINARIES_REPORT.json` records. The cowork sandbox built the indexes; an eval-host count divergence implies the index was not copied over correctly.
- An `llm_defaults.json` that you cannot restore to its original state (the swap script in Task 2 snapshots and restores it; if the snapshot is lost, do NOT proceed to subsequent scenarios until the original config is recovered).

You may not:
- Change the per-role temperatures in `AEGIS-eval/configs/llm_defaults.json` (they are frozen per PROTOCOL_LOCK §13).
- Edit the from-binaries `.txt` extracts or the JSONL indexes. They were built by the apparatus's production extractors; treat them as inputs.
- Re-fetch any source URL. The binaries on disk are the canonical input for this handoff; if a binary is missing, escalate.

---

## Task 1: Verify the from-binaries inputs are present

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

for S in volt_typhoon crowdstrike_outage svb_collapse; do
  IDX="demo/$S/rag/${S}__from_binaries.jsonl"
  ORG="demo/$S/sources/originals"
  TXT="demo/$S/sources/from_binaries"
  TSK="demo/$S/tasks/tasks.jsonl"
  echo "=== $S ==="
  [ -f "$IDX" ] && echo "  index: $(wc -l < "$IDX") chunks  $IDX" || { echo "  MISSING $IDX"; exit 1; }
  [ -d "$ORG" ] && echo "  originals: $(ls "$ORG" | grep -v MANIFEST | wc -l) files" || { echo "  MISSING $ORG"; exit 1; }
  [ -d "$TXT" ] && echo "  from_binaries: $(ls "$TXT"/*.txt 2>/dev/null | wc -l) .txt extracts" || { echo "  MISSING $TXT"; exit 1; }
  [ -f "$TSK" ] && echo "  tasks: $(wc -l < "$TSK") lines  $TSK" || { echo "  MISSING $TSK"; exit 1; }
done

python3 -c "import pypdf, docx, pptx; print('pypdf', pypdf.__version__, '/ python-docx', docx.__version__, '/ python-pptx', pptx.__version__)"
```

**Success criteria.** All three indexes present with chunk counts matching `demo/<scenario>/sources/FROM_BINARIES_REPORT.json` (`volt_typhoon` 2,093 ± 5%, `crowdstrike_outage` 413 ± 5%, `svb_collapse` 619 ± 5%). All three originals/ and from_binaries/ directories carry the right file counts (12, 13, 11 respectively). The three extractor libraries import.

## Task 2: Run MANDATE-primary on each scenario against its from-binaries index

The three blocks below are independent. Each one snapshots `llm_defaults.json`, points `llm_rag_index` at the from-binaries index, runs `apparatus.run run-system --ollama-mode`, and restores the config. Run them serially to keep wall-clock measurements clean.

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

**Success criteria.** Each scenario produces `demo/<scenario>/output_ollama_from_binaries/mandate_primary__TASK-DEMO-<X>-001__r01.json` plus a `ledger.jsonl`. Inspecting any of the RunRecords with `jq` should show `"ok": true`, all six roles with `llm_used=true`, and `decoding_params.rag_retriever_wired: true` on the Procedure role.

**Wall-clock reference** (for sanity, not a halt condition):
- Volt Typhoon: ~238 s on the prior `output_ollama/` run.
- CrowdStrike outage: ~212 s.
- SVB collapse: ~196 s.
The from-binaries indexes are slightly larger for Volt Typhoon (+5%) and smaller for the others (−4% to −2%); wall-clock should land within ±20% of these numbers.

**On a swap-script failure.** If the `python3 -c "..."` swap raises (for example, missing `AEGIS-eval/configs/llm_defaults.json`), the `.bak` is your safety net. Restore with `mv AEGIS-eval/configs/llm_defaults.json.bak AEGIS-eval/configs/llm_defaults.json` and escalate.

## Task 3: Sanity-check each RunRecord

```zsh
for S in volt_typhoon crowdstrike_outage svb_collapse; do
  REC=$(ls demo/$S/output_ollama_from_binaries/mandate_primary__TASK-DEMO-*__r01.json | head -1)
  python3 -c "
import json, sys
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
print('  validator_rationale=', (r.get('output',{}).get('recommendation',{}).get('rationale','') or '')[:200])
"
done
```

**Success criteria.** Every scenario shows `ok=True`, `all_llm_used=True`, `any_llm_fallback=False`, `procedure.rag_retriever_wired=True`. The COA count, anchor length, and validator rationale are recorded for the Task 5 comparison.

## Task 4: Restore `llm_defaults.json` and verify

```zsh
git diff -- AEGIS-eval/configs/llm_defaults.json
```

**Success criteria.** No diff. If the file still has a `demo/...` `llm_rag_index` value, restore it with `git checkout AEGIS-eval/configs/llm_defaults.json`.

## Task 5: Comparison report against the prior `output_ollama/` runs

For each scenario, load both the prior `output_ollama/mandate_primary__TASK-DEMO-<X>-001__r01.json` and the new `output_ollama_from_binaries/...` artifact, and tabulate:

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
        "task_dag_nodes": [n.get("description","")[:80] for coa in coas for n in coa.get("task_dag",{}).get("nodes",[])][:6],
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

Take that table as the spine of `handoffs/HANDOFF_16_report_<YYYY-MM-DD>.md` (template below). The substantive question to answer in prose:

1. **Did the cross-domain single-COA finding survive the binary-sourced re-run?** If `n_coas` is still 1 across all three from-binaries runs, the finding is reaffirmed; it is a model behavior, not an extraction-path artifact. If `n_coas` shifts on any scenario, the cause is in the chunks fed to the Procedure retriever and the upstream-MANDATE-team note needs revising.
2. **Did the validator's gap-acknowledgment behavior change?** Compare the `validator_rationale` strings. The prior CrowdStrike run flagged "potential insufficiency in delivering three distinct strategic options"; the prior SVB run did not. If the new runs flip either direction, note it.
3. **Did anchor distillation quality change on the SVB run?** Prior SVB anchor came out in the deterministic-prefix shape ("Minimally satisfy: Team, this is the CFO..."). If the new SVB anchor distills more cleanly, the financial-domain fine-tune behavior may be sensitive to chunk boundary differences.

## Final report

Write `handoffs/HANDOFF_16_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 16 Report: Demo re-run from original source binaries

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes total across the three Ollama runs>

## Verdict

PROCEED | HALT (one word)

## Evidence

- from-binaries indexes verified:           volt=<n_chunks> crwd=<n_chunks> svb=<n_chunks>
- pypdf / python-docx / python-pptx:        <versions>
- Volt Typhoon run ok / wall_clock_ms:      <True|False> / <ms>
  - all_llm_used / any_llm_fallback:        <True|False> / <True|False>
  - n_coas / coa1_name:                     <n> / <name>
- CrowdStrike run ok / wall_clock_ms:       <True|False> / <ms>
  - all_llm_used / any_llm_fallback:        <True|False> / <True|False>
  - n_coas / coa1_name:                     <n> / <name>
- SVB collapse run ok / wall_clock_ms:      <True|False> / <ms>
  - all_llm_used / any_llm_fallback:        <True|False> / <True|False>
  - n_coas / coa1_name:                     <n> / <name>
- llm_defaults.json restored (no git diff): yes | no

## Cross-domain single-COA finding under binary-sourced inputs

<one paragraph: reaffirmed | invalidated | partially affected. Cite the n_coas
values across the three scenarios and any differences in the COA-1 name or
task-DAG node descriptions versus the prior runs.>

## Validator gap-acknowledgment delta

<one paragraph: did the CrowdStrike validator still flag the three-options
gap? Did the SVB validator pick up the gap this time? Quote the exact
rationale strings if they changed.>

## SVB anchor distillation delta

<one paragraph: did the SVB anchor still come out in the deterministic-prefix
shape ("Minimally satisfy: ..."), or did the from-binaries chunks produce a
cleaner distillation?>

## Anything the PI must decide before proceeding

- whether to update demo/MANDATE_DEMO_FINDINGS.md with the binary-sourced rerun results
- whether the upstream-MANDATE-team note (demo/UPSTREAM_MANDATE_NOTE_decomposition_bias.md) needs revision
- whether to proceed to HANDOFF_04 (B4 to B6 calibration) or HANDOFF_08 (hold-out corpus)

## Deviations from this handoff

<short list, empty if none>
```

Commit the three new RunRecords, the comparison output, and the handoff report. Single commit message: `Handoff 16: demo re-run from original source binaries`.
