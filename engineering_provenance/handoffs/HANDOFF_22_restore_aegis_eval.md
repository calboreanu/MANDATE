# Codex Handoff 22: Restore corrupted AEGIS-eval/ tree from v1 tag

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-05
**Estimated wall clock:** 1 to 3 minutes (single bash command + verification).
**Blocked on:** Upstream AEGIS repo at `$AEGIS_PATH` (default `~/Desktop/AEGIS`) carries the `mandate-eval-primary-2026q2-v1` tag. The upstream working tree does NOT need to be clean for this handoff (unlike HANDOFF_17d) because `git archive` operates on the tagged commit, not on the working tree.

---

## Why this exists

HANDOFF_11a halted at the frozen-source precondition check because `AEGIS-eval/_AEGIS_EVAL_README.txt` was missing. Investigation confirmed the AEGIS-eval/ tree is partially corrupted on project main:

```
AEGIS-eval/src/mandate/roles/binding.py     MISSING  (expected; the v1 baseline file)
AEGIS-eval/src/mandate/llm_support.py       MISSING  (expected; used by every role)
AEGIS-eval/src/mandate/pipeline.py          MISSING  (expected; the pipeline runner)
AEGIS-eval/_AEGIS_EVAL_README.txt           MISSING  (the marker file)
AEGIS-eval/src/mandate/roles/intake.py      present
AEGIS-eval/src/mandate/roles/interpreter.py present
AEGIS-eval/src/mandate/roles/decomposition.py present
AEGIS-eval/src/mandate/roles/procedure.py   present
AEGIS-eval/src/mandate/roles/validation.py  present
AEGIS-eval/src/aegis/llm/*.py               present (apparatus-patched response_parser still has the v2 changes from HANDOFF_17b side-load)
```

Likely cause: an interrupted file operation in an earlier session removed several MANDATE source files. The `feature/binding-refusal-as-gap-sideload` branch has a complete AEGIS-eval/ but with v2-patched versions, which CANNOT be copied to main without installing the patch and violating PROTOCOL_LOCK §13. The correct recovery is to re-run the canonical recreation script.

**Definition of done.** `AEGIS-eval/` directory wiped and recreated from the v1 tag. All MANDATE source files present including the baseline (un-patched) `binding.py`, `llm_support.py`, `pipeline.py`. Marker file present with the v1 tag/commit. HANDOFF_11a's precondition checks all pass on re-run.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# 1. Confirm we are on project main with clean working tree (apart from the
#    .gitignored AEGIS-eval/ tree)
git branch --show-current
git status --porcelain | grep -v "AEGIS-eval/" | head -5

# 2. Confirm upstream AEGIS is reachable and has the v1 tag
: "${AEGIS_PATH:=$HOME/Desktop/AEGIS}"
[ -d "$AEGIS_PATH/.git" ] || { echo "AEGIS_PATH not a git repo: $AEGIS_PATH"; exit 1; }
git -C "$AEGIS_PATH" rev-parse --verify mandate-eval-primary-2026q2-v1^{commit} >/dev/null \
  || { echo "v1 tag missing in upstream AEGIS"; exit 1; }
echo "v1 tag at upstream commit: $(git -C "$AEGIS_PATH" rev-parse mandate-eval-primary-2026q2-v1^{commit})"

# Upstream tree dirty state is fine; git archive uses the tag, not HEAD.
git -C "$AEGIS_PATH" status --porcelain | wc -l | xargs echo "upstream changed paths (informational only):"

# 3. Confirm recreate script is present and executable
test -x setup/recreate_aegis_eval.sh || chmod +x setup/recreate_aegis_eval.sh
ls -l setup/recreate_aegis_eval.sh
```

**Success criteria.** Project main confirmed; v1 tag exists upstream; recreate script present.

## Decision boundary

You may decide:
- Whether to back up the current corrupted AEGIS-eval/ to a sister directory before wiping (recommended: `mv AEGIS-eval AEGIS-eval.corrupted-backup-$(date +%s)` so we can inspect the corruption postmortem). The recreate script's `--force` flag wipes without backup; if you want the backup, do it before calling the script.

You must escalate:
- The v1 tag is absent in upstream AEGIS.
- `git archive --format=tar mandate-eval-primary-2026q2-v1` errors out (would indicate a damaged tag in upstream).
- After recreation, `AEGIS-eval/src/mandate/roles/binding.py` is still missing (would indicate the v1 tag itself does not contain that file, which would be a fundamental tag-content issue, not a recovery issue).

You may not:
- Copy files from `feature/binding-refusal-as-gap-sideload` to project main. Those files carry the v2 patch and would silently install it on the v1 baseline path, breaking PROTOCOL_LOCK §13.
- Modify the v1 tag in upstream AEGIS.

---

## Task 1: Back up the corrupted tree and recreate

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# Optional but recommended: preserve the corrupted state for postmortem
BACKUP="AEGIS-eval.corrupted-backup-$(date +%Y%m%d-%H%M%S)"
mv AEGIS-eval "$BACKUP"
echo "backed up corrupted tree to $BACKUP"

# Recreate from v1 tag
bash setup/recreate_aegis_eval.sh
```

**Success criteria.** The recreate script prints "AEGIS-eval recreated:" with the v1 tag and commit `4f8af83`. The `AEGIS-eval/` directory exists fresh.

**Alternative if you don't want the backup.** Skip the `mv` and use `--force` instead:

```zsh
FORCE=1 bash setup/recreate_aegis_eval.sh
```

## Task 2: Verify the restored tree

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# Marker file present with v1 provenance
test -f AEGIS-eval/_AEGIS_EVAL_README.txt
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null
grep "4f8af83" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null
echo "marker file present with v1 provenance"

# The four previously-missing MANDATE source files
for f in src/mandate/roles/binding.py \
         src/mandate/llm_support.py \
         src/mandate/pipeline.py \
         src/aegis/llm/response_parser.py; do
  test -f "AEGIS-eval/$f" || { echo "STILL MISSING $f"; exit 1; }
done
echo "all four previously-missing files restored"

# Quick sanity that binding.py is the v1 baseline (no refusal-detection helper)
if grep -q "detect_structured_refusal" AEGIS-eval/src/aegis/llm/response_parser.py; then
  echo "WARNING: response_parser.py has v2 patch markers; expected v1 baseline"
  exit 1
fi
if grep -q "llm_refused_with_error" AEGIS-eval/src/mandate/roles/binding.py; then
  echo "WARNING: binding.py has v2 patch markers; expected v1 baseline"
  exit 1
fi
echo "v1 baseline confirmed (no v2 patch markers present)"

# Quick import smoke test
PYTHONPATH="AEGIS-eval/src:$PWD" python3 -c "
from mandate.roles.binding import BindingRole
from mandate.llm_support import generate_validated_response
from aegis.llm.rag_retriever import build_rag_index
print('all v1 modules import cleanly')
"
```

**Success criteria.** All checks print confirmation. The v1 baseline is restored without any v2 patch markers.

## Task 3: Re-fire HANDOFF_11a precondition gate

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# Reproduce HANDOFF_11a's precondition 4 check
test -d AEGIS-eval/ && test -f AEGIS-eval/_AEGIS_EVAL_README.txt && \
  grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null \
  && echo "HANDOFF_11a precondition 4 will now pass"
```

**Success criteria.** "HANDOFF_11a precondition 4 will now pass" prints.

## Report

`handoffs/HANDOFF_22_report_<YYYY-MM-DD>.md` with:
- Path of the backup directory (if backup was taken)
- v1 tag commit hash from upstream AEGIS
- The four previously-missing files now present (yes/no each)
- v1 baseline confirmed (no v2 patch markers)
- HANDOFF_11a precondition 4 now passes (yes/no)
- PROCEED verdict

After 22 PROCEED, re-fire HANDOFF_11a immediately (the rest of its body is unchanged).

Commit message: `Handoff 22: restore AEGIS-eval v1 tree (binding.py, llm_support.py, pipeline.py, marker)`.
