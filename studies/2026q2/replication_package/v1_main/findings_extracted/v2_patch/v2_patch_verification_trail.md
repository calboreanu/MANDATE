# v2 Candidate Binding-Refusal Patch: Full Verification Trail

Branch: `feature/binding-refusal-as-gap-sideload` (project) + corresponding upstream patch (parked on HANDOFF_17d).

## Three-level verification

### Level 1: Unit Tests (HANDOFF_17b)

**Total tests:** 1448 AEGIS-eval tests passing (1443 baseline + 5 new refusal-specific cases).

**New tests added in `tests/test_binding_refusal.py`:**
- `test_detect_structured_refusal_returns_text` — verifies the helper returns the error text on a clean `{error: <str>}` payload.
- `test_detect_structured_refusal_rejects_extra_keys` — verifies the helper rejects payloads with extra keys or non-string error values.
- `test_generate_validated_response_short_circuits_on_refusal` — verifies the parse loop does NOT consume the retry budget when the response is a refusal (adapter called exactly once).
- `test_binding_role_handles_structured_refusal` — verifies BindingRole.execute_with_llm catches the refusal and annotates the result.
- `test_binding_role_falls_back_on_malformed_json` — verifies BindingRole.execute_with_llm re-raises on malformed JSON so the existing fallback path runs.

### Level 2: Deterministic Stub-Adapter Replay (HANDOFF_17c Lane 3)

The HANDOFF_16c diagnostic captured three direct-Ollama refusal payloads. HANDOFF_17c Lane 3 feeds the first captured payload through the patched apparatus with a stub adapter, verifying:

- `generate_validated_response` short-circuit fires on the first call (zero retries)
- `last_parsed_payload` is preserved on the raised `ResponseParseError`
- Adapter called exactly once on refusal (not 3 times as the original behavior)

**Source diagnostic file:** `demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json`
- Captured attempts: 3
- All parse as JSON: True
- All have only the `error` key: True

### Level 3: Negative Testing (HANDOFF_17c Lane 1)

Volt Typhoon and CrowdStrike v2 sanity runs (full pipeline against the patched apparatus) confirmed the patch does not over-fire on non-refusal scenarios:

- Volt Typhoon v2: `any_llm_fallback=False`, zero Binding-attributed gap reports
- CrowdStrike v2: `any_llm_fallback=False`, zero Binding-attributed gap reports

## Files Modified (Patch Surface)

- `src/aegis/llm/response_parser.py`: added `detect_structured_refusal()` helper; extended `ResponseParseError` with `last_raw_response` and `last_parsed_payload`.
- `src/mandate/llm_support.py`: `generate_validated_response` short-circuits on detected refusal.
- `src/mandate/roles/binding.py`: `BindingRole.execute_with_llm` catches the refusal, runs deterministic recommendation as fallback summary, annotates artifact.
- `src/mandate/pipeline.py`: injects `GapSpec(UNASSESSABLE_RISK, detected_by='Binding')` when `llm_refused_with_error=True`.
- `tests/test_binding_refusal.py`: new 5-case test file.

## Why v1 Does Not Install the Patch

PROTOCOL_LOCK §13 binds the formal Phase 6 study to the v1 frozen tag `mandate-eval-primary-2026q2-v1` (commit 4f8af83). The v2 patch is a candidate evaluation question whose answer is what a future v2 study would measure. For the v1 study, the Binding refusal failure path is the apparatus behavior, and the 244/1500 refusal records are valid Phase 6 measurement data (the model is correctly refusing; the apparatus discards the explanation; the trade-off space is documented).
