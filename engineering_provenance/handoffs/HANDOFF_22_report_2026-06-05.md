# Handoff 22 Report: Restore AEGIS-eval v1 Tree

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-05
**Wall clock:** <5 minutes

## Verdict

PROCEED

## Backup

Corrupted tree backup:

```text
AEGIS-eval.corrupted-backup-20260605-063244
```

## Upstream v1 Tag

Upstream AEGIS path:

```text
/Users/ws01admin/Desktop/AEGIS
```

v1 tag commit:

```text
4f8af83d12ef1ffdedcf7c5f53a0f9a2c062b06f
```

Upstream changed paths were informational only for this handoff: `415`.

## Restored Files

| file | present after restore |
|---|---|
| `AEGIS-eval/_AEGIS_EVAL_README.txt` | yes |
| `AEGIS-eval/src/mandate/roles/binding.py` | yes |
| `AEGIS-eval/src/mandate/llm_support.py` | yes |
| `AEGIS-eval/src/mandate/pipeline.py` | yes |
| `AEGIS-eval/src/aegis/llm/response_parser.py` | yes |

## v1 Baseline Confirmation

Passed.

- `AEGIS-eval/_AEGIS_EVAL_README.txt` contains `mandate-eval-primary-2026q2-v1`.
- `AEGIS-eval/_AEGIS_EVAL_README.txt` contains `4f8af83`.
- `response_parser.py` does not contain `detect_structured_refusal`.
- `binding.py` does not contain `llm_refused_with_error`.
- Import smoke test passed for `BindingRole`, `generate_validated_response`, and `build_rag_index`.

## HANDOFF_11a Precondition 4

Passed.

```text
HANDOFF_11a precondition 4 will now pass
```

## Notes

- `AEGIS-eval/` is intentionally gitignored in this project and has zero tracked files. The restored tree is present on disk for Phase 6 execution; the project record for this restoration is this report.
- Pre-existing non-AEGIS working-tree changes were observed during the precondition check and left untouched.

## Deviations from this handoff

- None. The corrupted tree was backed up, `AEGIS-eval/` was recreated from the upstream v1 tag using `setup/recreate_aegis_eval.sh`, and all verification checks passed.
