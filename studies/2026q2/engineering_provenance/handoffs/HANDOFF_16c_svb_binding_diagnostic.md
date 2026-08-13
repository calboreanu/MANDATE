# Codex Handoff 16c: SVB Binding role raw-response diagnostic

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 6 to 10 minutes (no full MANDATE re-run; one direct Ollama call against the failing role).
**Blocked on:** Handoff 01 PROCEED, `mandate-binding` Ollama model loaded.

---

## Mission

HANDOFF_16b succeeded on Volt Typhoon and CrowdStrike but the SVB from-binaries run tripped the no-fallback gate: the `mandate-binding` role emitted text that failed schema validation 3 times in a row with `'decision_summary' is a required property`, and the apparatus fell back to the deterministic Binding path. The RunRecord at `demo/svb_collapse/output_ollama_from_binaries/mandate_primary__TASK-DEMO-SVB-001__r01.json` records the fallback reason but not the raw text the role emitted on each attempt. This handoff captures those raw responses so we can name the failure mode (invalid JSON, missing field, extra prose around valid JSON, hallucinated structure) and tell the upstream MANDATE team something concrete about the financial-domain Binding fine-tune.

**Definition of done.** A new file at `demo/svb_collapse/diagnostics/svb_binding_raw_responses_<YYYY-MM-DD>.json` containing the prompt sent to `mandate-binding`, three independent Ollama completions at the frozen `Binding` temperature (0.1) and max-tokens (2048), and an analyst-readable summary of each (parses-as-JSON, contains `decision_summary`, contains extra prose). One handoff report at `handoffs/HANDOFF_16c_report_<YYYY-MM-DD>.md`. The MANDATE-primary pipeline is NOT re-run; only the Binding role is exercised in isolation.

## Preconditions

- Handoff 01 PROCEED.
- Ollama running at `http://localhost:11434` with `mandate-binding` loaded.
- `demo/svb_collapse/output_ollama_from_binaries/mandate_primary__TASK-DEMO-SVB-001__r01.json` exists and shows `any_llm_fallback=True` with `fallback_roles=['Binding']`.
- The Procedure-role output from the same run is reachable (it's in the same RunRecord's `roles[3].output` or equivalent; the diagnostic script below extracts it).
- `AEGIS-eval/config/system-prompts/Binding.md` (or whatever filename the Binding role's system prompt lives at) is readable. The script below resolves the path via the apparatus's config.

## Decision boundary

You may decide:
- Whether to retry the diagnostic if Ollama times out (one retry is fine).
- Output filename suffix if the date overlaps an existing diagnostic.

You must escalate:
- The `mandate-binding` model not being loaded.
- The Procedure-role output not being recoverable from the RunRecord (in which case the diagnostic cannot reproduce the failing call).
- Any direct-Ollama call returning an HTTP 5xx that does not clear on one retry.

You may not:
- Re-run the MANDATE-primary pipeline. This handoff is a targeted role-level diagnostic.
- Modify the `mandate-binding` model file, the role's system prompt, or any apparatus code.
- Edit any RunRecord. The earlier artifacts are read-only here.

---

## Task 1: Locate the Binding role's input

The diagnostic needs the exact prompt the apparatus sent to `mandate-binding` on the failing SVB run. The apparatus assembles the Binding prompt from:

1. The Binding role's system prompt (resolves via `decoding_params.llm_prompt_dir`).
2. The output of the upstream roles (Intake, Interpreter, Decomposition, Procedure) on the same run.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

python3 - <<'PY'
import json, os
r = json.load(open('demo/svb_collapse/output_ollama_from_binaries/mandate_primary__TASK-DEMO-SVB-001__r01.json'))
print("any_llm_fallback:", r["any_llm_fallback"])
print("fallback_roles:", r["fallback_roles"])
print("decoding_params.llm_prompt_dir:", r["decoding_params"]["llm_prompt_dir"])
print("decoding_params.llm_role_models.Binding:", r["decoding_params"]["llm_role_models"]["Binding"])
print("decoding_params.llm_role_temperatures.Binding:", r["decoding_params"]["llm_role_temperatures"]["Binding"])
print("decoding_params.llm_role_max_tokens.Binding:", r["decoding_params"]["llm_role_max_tokens"]["Binding"])
print("decoding_params.llm_role_retries.Binding:", r["decoding_params"]["llm_role_retries"]["Binding"])
# What roles are emitted on this artifact?
print()
print("artifact has keys:", list(r["output"]["artifact"].keys()))
# The Binding role consumes the upstream artifact fields. Show them.
art = r["output"]["artifact"]
for k in ("anchor","courses_of_action","recommendation","trace","registry_reference","metadata"):
    v = art.get(k)
    if isinstance(v, (dict, list)):
        print(f"  {k}: {type(v).__name__} of size {len(v)}")
    else:
        print(f"  {k}: {str(v)[:80]}")
PY
```

**Success criteria.** Decoding params print, Binding model name is `mandate-binding`, prompt directory exists, the artifact's anchor / courses_of_action / recommendation are populated.

## Task 2: Reproduce the Binding prompt and call Ollama directly

The apparatus's Binding-role prompt assembly is documented in `AEGIS-eval/src/aegis/llm/role_runners/binding.py` (or the equivalent role file). The simplest reproduction is to import that role runner, hand it the RunRecord's upstream-role outputs, and ask it for the prompt string only (do not call run; just call `_build_prompt` or whatever the role's prompt assembly function is named).

```zsh
PYTHONPATH="AEGIS-eval/src:$PWD" python3 - <<'PY'
"""Reproduce the SVB from-binaries Binding prompt and call Ollama directly
three times at the frozen Binding temperature. Save raw responses, parse
attempts, and a per-attempt analyst summary."""
import json, os, datetime, urllib.request

# 1. Load the failing RunRecord
rec = json.load(open('demo/svb_collapse/output_ollama_from_binaries/mandate_primary__TASK-DEMO-SVB-001__r01.json'))
art = rec["output"]["artifact"]
dp = rec["decoding_params"]

# 2. Import the Binding role runner from AEGIS-eval
# NOTE: the exact import path may differ; the apparatus team's frozen layout
# under AEGIS-eval/src/aegis/llm/ should expose the role runners. If the
# import below fails, list AEGIS-eval/src/aegis/llm/role_runners/ and adjust.
from aegis.llm.role_runners import binding as binding_role

# 3. Reconstruct the Binding-role input from the upstream artifact.
# The Binding role consumes the anchor + courses_of_action and produces the
# recommendation block (which contains decision_summary).
binding_input = {
    "anchor": art["anchor"],
    "courses_of_action": art["courses_of_action"],
    "metadata": art.get("metadata", {}),
}

# 4. Build the prompt string. The role runner exposes a prompt-build helper;
# if its public API differs in the frozen MANDATE-primary tag, adjust here.
prompt = binding_role.build_prompt(binding_input, system_prompt_dir=dp["llm_prompt_dir"])

# 5. Call Ollama three times at the frozen Binding temperature
def call_ollama(prompt, model, temperature, max_tokens):
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps({
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())

attempts = []
for i in range(3):
    resp = call_ollama(prompt,
                       model=dp["llm_role_models"]["Binding"],
                       temperature=dp["llm_role_temperatures"]["Binding"],
                       max_tokens=dp["llm_role_max_tokens"]["Binding"])
    raw_text = resp.get("response","")
    # Per-attempt analyst summary
    a = {
        "attempt": i+1,
        "raw_text": raw_text,
        "raw_text_chars": len(raw_text),
        "raw_text_first_120": raw_text[:120],
        "raw_text_last_120": raw_text[-120:],
        "ollama_total_duration_ns": resp.get("total_duration"),
        "ollama_eval_duration_ns": resp.get("eval_duration"),
        "parses_as_json": False,
        "parse_error": None,
        "has_decision_summary": False,
        "has_extra_prose_around_json": False,
        "json_candidate_keys": [],
    }
    # Try to parse raw as JSON
    try:
        obj = json.loads(raw_text)
        a["parses_as_json"] = True
        a["json_candidate_keys"] = list(obj.keys()) if isinstance(obj, dict) else []
        a["has_decision_summary"] = isinstance(obj, dict) and "decision_summary" in obj
    except Exception as e:
        a["parse_error"] = str(e)
        # Try to find a JSON object inside the prose
        import re
        m = re.search(r"\{[\s\S]*\}", raw_text)
        if m:
            try:
                obj = json.loads(m.group(0))
                a["has_extra_prose_around_json"] = True
                a["json_candidate_keys"] = list(obj.keys()) if isinstance(obj, dict) else []
                a["has_decision_summary"] = isinstance(obj, dict) and "decision_summary" in obj
            except Exception as e2:
                a["parse_error"] += f" / inner JSON: {e2}"
    attempts.append(a)

# 6. Save the diagnostic
out = {
    "generated_at_utc": datetime.datetime.utcnow().isoformat(timespec="seconds")+"Z",
    "scenario": "svb_collapse",
    "model": dp["llm_role_models"]["Binding"],
    "temperature": dp["llm_role_temperatures"]["Binding"],
    "max_tokens": dp["llm_role_max_tokens"]["Binding"],
    "rag_index_used_by_procedure_upstream": dp.get("llm_rag_index"),
    "prompt_first_400": prompt[:400],
    "prompt_last_400": prompt[-400:],
    "prompt_chars": len(prompt),
    "attempts": attempts,
}
os.makedirs("demo/svb_collapse/diagnostics", exist_ok=True)
outpath = f"demo/svb_collapse/diagnostics/svb_binding_raw_responses_{datetime.date.today().isoformat()}.json"
with open(outpath, "w") as f: json.dump(out, f, indent=2)
print(f"Wrote {outpath}")
# Brief print summary
for a in attempts:
    print(f"  attempt {a['attempt']}: chars={a['raw_text_chars']}  parses_as_json={a['parses_as_json']}  has_decision_summary={a['has_decision_summary']}  has_extra_prose_around_json={a['has_extra_prose_around_json']}  keys={a['json_candidate_keys'][:8]}")
PY
```

**Success criteria.** Three Binding completions captured. The output file at `demo/svb_collapse/diagnostics/svb_binding_raw_responses_<date>.json` lists each attempt with `raw_text`, `parses_as_json`, `has_decision_summary`, `has_extra_prose_around_json`, and `json_candidate_keys`.

**On import failure.** If `from aegis.llm.role_runners import binding as binding_role` raises, list `AEGIS-eval/src/aegis/llm/role_runners/`, identify the Binding role file, and update the import. If the role runner does not expose a `build_prompt` helper, read the runner source, find the in-line prompt construction, and reproduce it here verbatim. Do NOT call the runner's `run()` method; that would re-invoke retry logic and reproduce the failure path without giving us the raw responses.

## Task 3: Categorize the failure mode

```zsh
python3 - <<'PY'
import json, glob, os
files = sorted(glob.glob("demo/svb_collapse/diagnostics/svb_binding_raw_responses_*.json"))
d = json.load(open(files[-1]))
print(f"Diagnostic: {files[-1]}")
print(f"Model: {d['model']}  Temp: {d['temperature']}")
n = len(d["attempts"])
parses = sum(1 for a in d["attempts"] if a["parses_as_json"])
has_ds = sum(1 for a in d["attempts"] if a["has_decision_summary"])
extra = sum(1 for a in d["attempts"] if a["has_extra_prose_around_json"])
print(f"\nOf {n} attempts:")
print(f"  parses cleanly as JSON:        {parses}")
print(f"  contains decision_summary:     {has_ds}")
print(f"  has JSON inside prose wrapper: {extra}")
print(f"\nFailure mode classification:")
if parses == n and has_ds == 0:
    print("  CLEAN_JSON_MISSING_FIELD")
elif extra > 0 and has_ds > 0:
    print("  JSON_WRAPPED_IN_PROSE")
elif parses == 0 and extra == 0:
    print("  INVALID_JSON")
elif parses < n and has_ds > 0:
    print("  INTERMITTENT_PARSE")
else:
    print("  MIXED  (inspect attempts manually)")
PY
```

**Success criteria.** A single named failure mode is printed.

## Final report

Write `handoffs/HANDOFF_16c_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 16c Report: SVB Binding role raw-response diagnostic

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- mandate-binding model loaded:                 yes | no
- diagnostic file written:                      <path>
- attempts captured:                            3
- attempts that parsed cleanly as JSON:         <n>/3
- attempts that contained decision_summary:     <n>/3
- attempts with JSON wrapped in prose:          <n>/3
- failure mode classification:                  <CLEAN_JSON_MISSING_FIELD|JSON_WRAPPED_IN_PROSE|INVALID_JSON|INTERMITTENT_PARSE|MIXED>

## Sample of attempt 1 raw response

<verbatim first 600 chars of attempt 1's raw_text, fenced as ```text```>

## Notes on prompt and Ollama call

- prompt chars sent to Binding:                 <n>
- model temperature:                            0.1 (frozen)
- model max_tokens:                             2048 (frozen)
- per-attempt Ollama eval_duration (ms):        <list>

## Anything the PI must decide before proceeding

- Forward the diagnostic to the upstream MANDATE team along with `demo/UPSTREAM_MANDATE_NOTE_decomposition_bias.md`.
- Decide whether to issue HANDOFF_16d that retries SVB with a higher Binding role retry count, or whether to accept the fallback as the SVB from-binaries record and move on to HANDOFF_04 or HANDOFF_08.

## Deviations from this handoff

<short list, empty if none>
```

Commit message: `Handoff 16c: SVB Binding role raw-response diagnostic`.
