# Codex Handoff 19d: DomainProfile mapping patch for canonical-MANDATE adapter

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-23 (post-Cond-A-main audit)
**Adds, does not supersede:** HANDOFF_19 / 19b / 19c remain in force. This patch adds a feature flag (`--domain-profile-mode {default,auto}`) so the in-flight Stage 3 Cond-A run completes under its current default-DomainProfile behavior and the patched domain-aware logic is opt-in for Cond-B and any future v2.1 work.

**Estimated wall clock:** 30–45 minutes apparatus work + tests. No grading or system-run cost.
**Risk:** none if applied with the flag-default behavior preserved. The in-flight Cond-A run is NOT disturbed.

---

## Why this exists

Mid-Stage-3 audit on the first 1200 Cond-A records produced a substantive finding the v2 pivot was not designed to surface but that the data exposed:

```
COA approach text variety: only 3 unique strings across 1200 records:
  1200×  "Aggressive multi-vector approach with parallel execution"
   945×  "Conservative reconnaissance and scanning without exploitation"
    20×  "Moderate approach with targeted exploitation of confirmed vulnerabilities"
```

These are canonical MANDATE's **pentest DomainProfile** approach templates (RECON/SCAN/EXPLOIT vocabulary). The Cond-A adapter does not pass a `domain_profile` to `PipelineConfig`, so canonical Decomposition falls back to its built-in pentest default for every task — including NIST 800-37 financial reporting tasks and intelligence-collection threat-matrix tasks. The COAs are well-formed, multi-COA, schema-valid, and constraint-extracted cleanly. They're also semantically domain-mismatched.

Canonical MLT v1.0.0rc1 ships three DomainProfiles in `mlt.mandate.domain`:
- `defense_intel` — Intelligence collection / analysis (planning → collection → processing → analysis → dissemination)
- `incident_response` — Security ops / incident handling
- `pentest` — Penetration testing (the default that's firing on everything today)

The corpus task ID convention is `TASK-MAIN-{DOMAIN}-{NUM}` where DOMAIN ∈ {FIN, INT, SEC}. Natural mapping:

| Task domain | Canonical profile | Rationale |
|---|---|---|
| INT (intelligence_collection_tasking) | `defense_intel` | Clean canonical match |
| SEC (security_operations_reporting) | `incident_response` | Security ops oriented; sharper match than `pentest` for "reporting" tasks |
| FIN (financial_reporting) | `None` (no profile passed) | Canonical MLT v1.0.0rc1 ships no financial profile; default deterministic path applies, with `None` passed explicitly so the choice is intentional rather than implicit |

`FIN → None` is a documented limitation, not a bug. Canonical MANDATE's DomainProfile registry doesn't ship a financial profile in v1.0.0rc1; building one is out of scope for v2.1. The Cond-A FIN records under `auto` mode will still fall through to canonical's default behavior, but the choice is explicit rather than implicit.

---

## Patch design — feature flag with default-off

**Critical operational constraint:** Stage 3 Cond-A main matrix (1200 records) is already committed to disk on default-DomainProfile logic. Cond-A holdout (~300 records) is still running on the same logic at the time of this handoff. We do NOT want to:
- Interrupt the in-flight Cond-A holdout run
- Mix records produced under different DomainProfile-selection logic within the same Cond-A condition

The patch therefore introduces a **`--domain-profile-mode {default,auto}` CLI flag**:
- `default` (default value): preserves current behavior — `domain_profile=None` is passed to canonical `PipelineConfig`. The in-flight Cond-A run continues to produce records consistent with the 1200 already committed.
- `auto`: maps task domain prefix (FIN/INT/SEC) to canonical profile per the table above.

Cond-A continues on `default`. Cond-B will fire with `auto` when its run command is issued (HANDOFF_19 §3, modified). A future v2.1 condition can re-run Cond-A with `auto` for direct comparison.

---

## Patch 1 — `apparatus/systems/mandate_canonical.py`

Add the mapping function near the top of the module, after the existing imports:

```python
"""
... existing module docstring ...
"""
import sys, time
from pathlib import Path

MLT_ROOT = Path.home() / "Desktop/MLT-Governance-Stack"
if str(MLT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(MLT_ROOT / "src"))

from mlt.mandate.pipeline import Pipeline
from mlt.mandate.models import PipelineConfig, MissionInput
from mlt.mandate.domain import get_domain_profile

# --- DomainProfile mapping for corpus task IDs ---------------------------
# Canonical MANDATE v1.0.0rc1 ships exactly three DomainProfiles:
# 'defense_intel', 'incident_response', 'pentest'. The corpus task IDs use
# the pattern TASK-MAIN-{FIN,INT,SEC}-{NUM}. The mapping below is opted
# into via the --domain-profile-mode auto flag; default preserves the
# current None behavior (canonical's pentest-flavored fallback path).
#
# Per HANDOFF_19d 2026-06-23 mid-Stage-3 audit: under default-None the
# canonical Decomposition role emits pentest-flavored COA approach text
# regardless of task domain. The 'auto' mapping fixes this for INT and
# SEC tasks. FIN tasks have no canonical financial profile to map to and
# fall through to None — documented limitation, not a bug.
_TASK_DOMAIN_TO_PROFILE_NAME = {
    "INT": "defense_intel",
    "SEC": "incident_response",
    "FIN": None,  # no canonical financial profile in MLT v1.0.0rc1
}


def _resolve_domain_profile(task_id: str, mode: str):
    """Resolve a canonical DomainProfile for a task given the mode.

    Args:
        task_id: the corpus task ID, e.g. 'TASK-MAIN-INT-034'.
        mode: 'default' (always None — preserves pre-patch behavior) or
              'auto' (map FIN/INT/SEC prefix to canonical profile name).

    Returns:
        A canonical DomainProfile object, or None if no profile applies.
    """
    if mode != "auto":
        return None
    parts = task_id.split("-")
    if len(parts) < 3:
        return None
    domain_code = parts[2]
    profile_name = _TASK_DOMAIN_TO_PROFILE_NAME.get(domain_code)
    if profile_name is None:
        return None
    return get_domain_profile(profile_name)
```

Then thread the parameter through both run functions:

```python
def run_cond_a(task_id: str, task_text: str, mission_input,
               seed: int = 20260623,
               domain_profile_mode: str = "default") -> dict:
    """Cond-A: pre-extracted MissionInput → canonical MANDATE."""
    profile = _resolve_domain_profile(task_id, domain_profile_mode)
    t0 = time.time()
    config = PipelineConfig(strict=False, domain_profile=profile)
    result = Pipeline(config).run(mission_input)
    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        # ... existing fields ...
        "code_ref": "mlt-stack-1.0.0rc1",
        "domain_profile_mode": domain_profile_mode,
        "domain_profile_name": (profile.domain_id if profile else None),
        # ... rest unchanged ...
    }


def run_cond_b(task_id: str, task_text: str, llm_adapter,
               seed: int = 20260623,
               retry_backoff_sec=DEFAULT_RETRY_BACKOFF_SEC,
               domain_profile_mode: str = "default") -> dict:
    """Cond-B: canonical MANDATE with LLM-augmented Interpreter."""
    profile = _resolve_domain_profile(task_id, domain_profile_mode)
    resilient_adapter = RetryingLLMClient(llm_adapter,
                                           retry_backoff_sec=retry_backoff_sec)
    # ... existing constraint-gap wrapper + MissionInput construction ...
    config = PipelineConfig(
        strict=False,
        llm_adapter=resilient_adapter,
        enable_llm_interpreter=True,
        domain_profile=profile,
    )
    # ... existing pipeline run + gap injection ...
    return {
        # ... existing fields ...
        "domain_profile_mode": domain_profile_mode,
        "domain_profile_name": (profile.domain_id if profile else None),
        # ...
    }
```

Two record-level fields are added to the output so downstream analysis can stratify by mode without re-deriving from task IDs:
- `domain_profile_mode`: `"default"` or `"auto"`
- `domain_profile_name`: `"defense_intel"`, `"incident_response"`, or `null`

## Patch 2 — `apparatus/run.py` CLI

Add the flag to `run-cond-a` and `run-cond-b` subparsers:

```python
sp_a = subparsers.add_parser("run-cond-a", ...)
# ... existing args ...
sp_a.add_argument("--domain-profile-mode",
                  choices=["default", "auto"],
                  default="default",
                  help="DomainProfile selection. 'default' passes None to "
                       "canonical PipelineConfig (preserves pre-HANDOFF_19d "
                       "behavior; pentest-flavored COA approaches across "
                       "all task domains). 'auto' maps task ID domain "
                       "prefix (INT->defense_intel, SEC->incident_response, "
                       "FIN->None) to canonical DomainProfile.")
```

Same flag on `run-cond-b`. Thread it through to `run_cond_a` / `run_cond_b` calls in `cmd_run_cond_a` / `cmd_run_cond_b`.

## Patch 3 — Tests

`apparatus/systems/tests/test_mandate_canonical.py`:

```python
def test_resolve_domain_profile_default_mode_returns_none():
    from apparatus.systems.mandate_canonical import _resolve_domain_profile
    assert _resolve_domain_profile("TASK-MAIN-INT-034", "default") is None
    assert _resolve_domain_profile("TASK-MAIN-SEC-001", "default") is None
    assert _resolve_domain_profile("TASK-MAIN-FIN-001", "default") is None


def test_resolve_domain_profile_auto_mode_routes_INT():
    from apparatus.systems.mandate_canonical import _resolve_domain_profile
    profile = _resolve_domain_profile("TASK-MAIN-INT-034", "auto")
    assert profile is not None
    assert profile.domain_id == "defense_intel"


def test_resolve_domain_profile_auto_mode_routes_SEC():
    from apparatus.systems.mandate_canonical import _resolve_domain_profile
    profile = _resolve_domain_profile("TASK-MAIN-SEC-014", "auto")
    assert profile is not None
    assert profile.domain_id == "incident_response"


def test_resolve_domain_profile_auto_mode_FIN_falls_back_to_none():
    from apparatus.systems.mandate_canonical import _resolve_domain_profile
    # FIN has no canonical financial profile; falls through to None.
    profile = _resolve_domain_profile("TASK-MAIN-FIN-001", "auto")
    assert profile is None


def test_resolve_domain_profile_malformed_task_id_returns_none():
    from apparatus.systems.mandate_canonical import _resolve_domain_profile
    assert _resolve_domain_profile("NO-COLONS", "auto") is None
    assert _resolve_domain_profile("", "auto") is None


def test_run_cond_a_records_domain_profile_metadata(monkeypatch):
    """The returned record carries domain_profile_mode and _name fields."""
    # ... mock canonical Pipeline.run() to return an artifact stub ...
    # ... call run_cond_a with domain_profile_mode="auto" on TASK-MAIN-INT-034 ...
    # ... assert record['domain_profile_mode'] == 'auto' ...
    # ... assert record['domain_profile_name'] == 'defense_intel' ...
    pass


def test_run_cond_a_default_mode_records_none_profile(monkeypatch):
    """Default mode records None for domain_profile_name."""
    pass
```

Total: at least 5 unit tests (the first five) plus 2 integration tests with mocked Pipeline.

After all patches: full apparatus test suite should grow from 297 → ~302.

---

## Operational sequence — do NOT disturb Stage 3 Cond-A

1. **Land all patches** (mandate_canonical.py, run.py, tests). All tests pass.
2. **Commit** with message: `HANDOFF_19d: opt-in DomainProfile mapping for canonical-MANDATE adapter (--domain-profile-mode auto). Default mode preserves pre-patch behavior; auto maps INT->defense_intel, SEC->incident_response, FIN->None (no canonical financial profile in MLT v1.0.0rc1). Mid-Stage-3 audit (1200 Cond-A records) showed canonical Decomposition emits pentest-flavored COA approaches across all task domains under default config. New v2.1 condition can opt into auto for sharper domain-grounded measurement.`
3. **Verify the in-flight Cond-A holdout run is unaffected.** The patch defaults `domain_profile_mode="default"` everywhere, so existing CLI invocations (which don't pass the flag) preserve pre-patch behavior. The Cond-A holdout records committed before AND after the patch are bit-for-bit identical in their planning logic.
4. **When Cond-A holdout completes, write the Stage 3 Cond-A report** as planned — with one added line: ``DomainProfile selection: default (canonical's None / pentest-flavored fallback). The HANDOFF_19d patch added opt-in `--domain-profile-mode auto` mapping for use in subsequent conditions.``
5. **Fire Cond-B with `--domain-profile-mode auto`** so the LLM-augmented condition uses domain-appropriate canonical profiles. This is the planned Stage 3 Cond-B launch from HANDOFF_19 §3, just with the new flag added.

```zsh
.venv/bin/python -m apparatus.run run-cond-b \
  --all \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --out 07_system_outputs/cond_b \
  --llm-backend anthropic \
  --llm-model claude-sonnet-4-6 \
  --runs-per-task 10 \
  --seed 20260623 \
  --skip-existing \
  --checkpoint-every 50 \
  --max-workers 5 \
  --domain-profile-mode auto
```

---

## Methodology consequence

Cond-A and Cond-B now measure two distinct DomainProfile axes:
- **Cond-A:** structured pre-extracted input under canonical default config (pentest-flavored). Quantifies MANDATE planning capability isolated from natural-language extraction AND from DomainProfile selection.
- **Cond-B:** LLM-augmented Interpreter end-to-end under domain-appropriate canonical profiles. Quantifies MANDATE as an integrated system with domain-aware planning.

The cross-condition comparison now triangulates THREE axes:
- v1 → Cond-A: structured-input axis (the natural-language-extraction-vs-structured-input contrast)
- Cond-A → Cond-B: end-to-end-LLM-vs-deterministic axis
- Cond-B vs hypothetical Cond-A-auto (future v2.1): DomainProfile-selection axis

This is a *richer* methodology than what HANDOFF_19 originally specified — the mid-run audit unlocked an axis we hadn't designed for.

## What this adds to the v2 finding catalog

After Stage 4 grading lands, the supplement Finding 6 (schema-mismatch effect) gets a companion **Finding 7 candidate**:

> *Canonical MANDATE under default DomainProfile produces pentest-flavored COA approaches across all task domains. The default DomainProfile is registered as the pentest profile in MLT v1.0.0rc1 and is selected when PipelineConfig.domain_profile is None. The 1200 Cond-A records on 120 unique tasks across three task domains (FIN, INT, SEC) produced only three unique COA approach strings, all drawn from the pentest profile's `conservative_phases` / `moderate_phases` / `aggressive_phases` templates. Cond-B under domain-appropriate DomainProfile selection (INT→defense_intel, SEC→incident_response) is expected to produce domain-grounded approach text on its respective records. The FIN domain has no canonical financial profile in MLT v1.0.0rc1; the absence is a documented limitation, not a v2 measurement deficiency.*

I'll draft this into the supplement when Stage 4 results land, with the v2 grading numbers quantifying the cross-condition delta.

## Why this matters operationally

Without this patch, the Cond-B run would also use the pentest default and produce semantically identical COA approach text to Cond-A — eliminating one of the most informative comparisons in the v2 design. The flag lets us preserve the in-flight Cond-A run's coherence while ensuring Cond-B can measure the domain-appropriate-profile axis.

The patch is small (one mapping function, one PipelineConfig field, two CLI flags, ~5 tests). It introduces zero risk to the in-flight run because the default-flag behavior is bit-for-bit identical to pre-patch behavior.
