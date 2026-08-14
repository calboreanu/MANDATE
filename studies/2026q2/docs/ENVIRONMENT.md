# MANDATE 2026Q2 — Replication Environment

This document specifies the exact environment under which the MANDATE
2026Q2 evaluation was executed and against which the replication
package was authored. Reviewers replicating the work should be able to
match each tier of replication to a configuration below.

## Eval-host hardware

| Component | Spec |
|---|---|
| Machine | Mac mini M4 Pro |
| RAM | 64 GB unified memory |
| GPU | Apple M4 Pro GPU (integrated, 20-core) |
| Storage | 4 TB internal SSD |
| OS | macOS (Sequoia 15.x) |

The 2026Q2 evaluation was executed on a single Mac mini. The published
MANDATE paper §12 references "a Mac mini M4 Pro cluster" — this refers
to a single Mac mini configured as a self-contained Ollama host serving
six fine-tuned Qwen3 model variants, not a multi-node cluster. The
"cluster" wording in the paper describes the Ollama serving topology
(six concurrent role-specific model variants), not multi-machine
horizontal scaling.

## Python environment

| Item | Value |
|---|---|
| Python interpreter | Python 3.12.12 |
| Manager | pyenv (or any equivalent installer) |
| Virtual environment | `.venv/` at the apparatus root, created via `python -m venv` |
| Package list | Repository-root `requirements.txt` |

The on-disk `.venv/bin/python` is a symlink to a pyenv-managed 3.12.12.
The evaluation host used Python 3.12.12; reviewers should match it for
byte-faithful reproduction. This deposit intentionally does not ship the
stale host `environment.yml`. Install the pinned, annotated dependencies from
the repository-root `requirements.txt`; the underlying host freeze is retained
at `pre_registration/provenance_pip_freeze.txt`.

Setup:
```bash
cd "<apparatus root>"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # OR `pip install -e .` if pyproject.toml is present
```

## Ollama

| Item | Value |
|---|---|
| Ollama version | Reviewer should match the latest available; the 2026Q2 evaluation used a stable release available throughout May–June 2026 |
| Endpoint | `http://localhost:11434/api/generate` |
| Default timeout (apparatus) | 600 seconds per role invocation |
| Temperature | 0.0 (deterministic generation; see `decoding_params` in RunRecords) |

### Required Ollama models for full replication

**MANDATE-primary (Qwen3 fine-tunes, 6 role-specific models):**
- `mandate-intake` (fine-tuned from Qwen3-8B)
- `mandate-interpreter` (fine-tuned from Qwen3-32B)
- `mandate-decomposition` (fine-tuned from Qwen3-32B)
- `mandate-procedure` (fine-tuned from Qwen3-8B)
- `mandate-binding` (fine-tuned from Qwen3-32B)
- `mandate-validation` (fine-tuned from Qwen3-32B)

Fine-tuning specifications: LoRA, rank 8, α=20, 500 iterations,
learning rate `1e-5`, 4-bit quantization, MLX-LM toolchain. Training
set: 102 examples + 21 validation examples from the 125-example seed
corpus described in the published paper §12.

**Cross-LLM-family Cond-B (HANDOFF_22 — local Ollama only):**
- `qwen2.5:32b`
- `llama3.2:3b`
- `mistral:7b`
- `phi3:14b`

Pull each model:
```bash
ollama pull qwen2.5:32b
ollama pull llama3.2:3b
ollama pull mistral:7b
ollama pull phi3:14b
# (MANDATE fine-tunes require local creation from base + LoRA per the
# paper §12 procedure; they are not in the Ollama public registry)
```

Verify all models are present:
```bash
curl -s http://localhost:11434/api/tags | python -c "
import sys, json
tags = {m['name'] for m in json.load(sys.stdin)['models']}
print('Present:', sorted(tags))
"
```

## API keys (for grading + baseline runs)

`.env` at the apparatus root must contain:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

These are used by:
- **Phase 8 / Stage 4 grading** (Claude Opus 4.6 + GPT-4o + Gemini 2.5 Pro three-judge ensemble)
- **Baselines B1–B6** (Claude Sonnet 4.6 + GPT-4o orchestration)
- **Cond-B Anthropic backend** (Claude Sonnet 4.6 for the LLM-augmented Interpreter)
- **Ground-truth scaffolds** (Claude Opus 4.6 — already authored and frozen at `gt_freeze_v1`; reviewers replicating from scratch would need new keys, but the replication package distributes the scaffolds as part of `gt_freeze_v1`)

Tier 1 (read-only) verification does NOT require any API keys. Tier 2
re-grading requires all three. Tier 3 baseline re-runs require Anthropic
+ OpenAI. Tier 4 fine-tune replication requires the Ollama
infrastructure above plus the MLX-LM toolchain on Apple Silicon.

## Disk and resource budget

| Tier | Disk | Wall clock | API spend |
|---|---|---|---|
| Tier 1 — read-only | ~0.7 GB checkout | minutes | $0 |
| Tier 2 — re-grade | ~1 GB plus new grade outputs | 24–36 hours (full coverage; ~100 grades/hr at the recorded daemon throughput) | ~$7,700 |
| Tier 3 — re-baselines | Several GB plus generated outputs/model caches | 1–2 days per baseline (varies by API rate-limit) | ~$200–$2,000 per baseline |
| Tier 4 — re-MANDATE | Model/fine-tune storage dominates; budget tens of GB | Multi-day (fine-tune + 1500-record generation) | $0 (local Ollama only) |

## Non-default environment variables used

- `EVAL_ROOT` — apparatus root; defaults to current working directory in most scripts. Used in `cross_vendor/README.md` reproduction script.
- `DEPOSIT_ROOT` — deposit root; defaults to `~/Desktop/Mandate Data`. Used in cross-deposit analysis scripts.
- `AEGIS_PRIVATE_KEY_PASSPHRASE` — optional; the AEGIS test suite warns "private key will be loaded/saved without encryption" when unset. Not required for MANDATE evaluation.

## Known environment constraints

1. **Ollama swapping cost.** A single Mac mini cannot keep all six MANDATE
   fine-tunes resident in GPU memory simultaneously. Ollama swaps models
   on-demand per role invocation; the apparatus tolerates this via the
   600s timeout and structured retry layer (HANDOFF_19c). Wall-clock
   per record is ~100 s steady-state.
2. **Apple Silicon required for fine-tuning.** The MLX-LM toolchain is
   Apple Silicon-only. Reviewers without Apple Silicon hardware cannot
   replicate the MANDATE fine-tunes; the fine-tuned adapters are not
   distributed with this deposit: they belong to the proprietary AEGIS
   evaluation tree (available on request; see `docs/EXCLUSIONS.md`), with
   their manifests deposited at
   `replication_package/v0_5_pilot/logs/adapter_manifest_*.json`.
3. **API rate limits.** Stage 4 grading (Opus + GPT-4o + Gemini) is
   subject to provider rate limits. The HANDOFF_20 retry-layer and
   probe-gate (HANDOFF_19c) handle this gracefully; reviewers should not
   need to adjust beyond setting their API keys.
4. **Gemini 503 sensitivity.** Gemini 2.5 Pro periodically returns 503
   "high demand" during peak hours. The `handoff20_resume_daemon.py`
   pattern (15-minute probe gate, 2 consecutive 5/5 healthy intervals
   before re-firing `grade-v2 --skip-existing`) is the documented
   resilience pattern.

## See also

- `REPLICATION_INSTRUCTIONS.md` — tier-by-tier execution steps
- `cost_ledger.md` — per-phase cost actuals and projections
- Supplement §1.1 + §2 — methodology
- `CLAIM_TO_DATA_MAP.md` — claim-level evidence paths and checks
- `EXCLUSIONS.md` — components required for regeneration but not redistributed
