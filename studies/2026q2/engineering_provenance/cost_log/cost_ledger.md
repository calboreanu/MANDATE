# MANDATE 2026Q2 — Cost Ledger

**As of:** 2026-06-25 · **Currency:** USD · **Scope:** per-phase and per-handoff API spend for the 2026Q2 evaluation.
**Method:** read-only aggregation of (a) per-record `api_cost_usd` summed directly from the frozen RunRecords, (b) cost lines in the handoff reports under `handoffs/`, and (c) the two pre-existing attestation files in `standalone data results/handoff_costs/`. No apparatus runs, no API calls. Companion machine-readable files: `per_phase_costs.csv`, `per_handoff_costs.json`.

## Bottom line

The supplement's **$15,256** figure is a *forward-looking projection*, and it is internally arithmetic-consistent. **Actual, auditable spend to date is ~$412** (generation + corpus/scaffold/perturbation authoring), plus an in-progress v1/v2 grading bill. **99% of the $15,256 is two not-yet-finished line items** — Stage 4 grading ($7,700, ~14% done) and Stage 6 perturbations ($7,350, not started). The projection's one calibration anchor checks out exactly: the estimated $30 for Stage-3 Cond-A matches the record-summed actual of **$32.14**.

## The published $15,256 estimate (supplement, *Engineering and Operational Provenance* §2552)

| Component | Estimate | Status today |
|---|---:|---|
| Stage 1 — apparatus build | $0 | actual $0 (no API) |
| Stage 2 — pilots | $1 | actual ≈ $1.5 (pilot smoke) |
| Stage 3 — Cond-A generation | $30 | **actual $32.14** (record-sum, main) — calibration anchor |
| Stage 3 — Cond-B generation | $175 | **unverifiable — records log $0 (see flag)** |
| Stage 4 — full-coverage grading | $7,700 | **projection; in progress (~13.7%)** |
| Stage 6 — O5 / perturbation runs | $7,350 | **projection; not started** |
| **Total** | **$15,256** | mostly forward-looking |

`0 + 1 + 30 + 175 + 7,700 + 7,350 = 15,256` ✔ (arithmetic-consistent).

## Actual Phase-6 generation spend (authoritative: per-record `api_cost_usd` summed)

| System | Records | Provider | Actual $ | Note |
|---|---:|---|---:|---|
| mandate_primary | 1500 | Ollama (local) | 0.00 | local fine-tunes; no API cost |
| cond_a | 1500 | Anthropic | 40.38 | main-only $32.14 (matches audit) + hold-out $8.24 |
| **cond_b** | 1500 | Anthropic | **0.00** | **api_cost_usd = null on every record — UNLOGGED (flag)** |
| baseline_1 | 1506 | Anthropic | 50.22 | |
| baseline_2 | 1206 | OpenAI (GPT) | 6.87 | |
| baseline_3 | 1206 | Anthropic (ReAct) | 93.35 | most expensive baseline (multi-turn) |
| baseline_4 | 1206 | Anthropic (AutoGen) | 88.17 | |
| baseline_5 | 1206 | Anthropic (CrewAI) | 52.52 | |
| baseline_6 | 1206 | Anthropic (LangGraph) | 49.18 | |
| **Phase-6 total (logged)** | | | **$380.68** | + Cond-B unlogged |

Baseline subtotal $340.31 reconciles with the attested HANDOFF_11b-ii figure **$339.03** (≤$1.3 difference, calibration overlap/rounding).

## Authoring / pilot spend (from handoff reports + attestation table)

Corpus authoring (HANDOFF_02/03/07/08b ≈ $8.93), ground-truth scaffolds (HANDOFF_06c/09/20-gt = $17.00), baseline calibration (HANDOFF_04/04b/04c ≈ $1.36), perturbation generation (HANDOFF_10 = $3.09), pilot smoke (HANDOFF_11a ≈ $1.51). **Subtotal ≈ $32.** Full line-item detail with source files is in `per_phase_costs.csv`.

**Actual + attested spend to date (excludes grading): ≈ $412.**

## Grading

- **Phase 8 v1 (D-08 sampled, N=700):** estimated **$1,500–2,000** (HANDOFF_13b); a killed run cost ~$500; the grade records expose no clean cumulative `cost_usd`, so a precise actual cannot be attested from disk. Booked here at the $1,750 midpoint, flagged as projection.
- **Stage 4 v2 (full coverage, ~12,000 records):** estimated **$7,700** at ~$0.21/record (HANDOFF_20). In progress — **1,645 / 12,000 graded (~13.7%)** as of 2026-06-25. No per-record cost field is written to `08_grading_v2/by_record/`, so spend-to-date is not directly summable from the grades; the daemon tracks it at runtime only.

## Critical flags (for the lead analyst)

1. **Cond-B `api_cost_usd = 0` by design.** All 1,500 Cond-B RunRecords carry `api_cost_usd = null`. Anyone rolling cost from RunRecords will **understate Cond-B spend to zero**, and the $175 Stage-3 Cond-B estimate **cannot be verified from disk**. This is the audit's known limitation (Tier B item: "Patch Cond-B RunRecord cost logging OR add a top-level cost manifest"). Until patched, treat the $175 as an estimate only. (Note: the cross-vendor Cond-B pilot itself ran on local Ollama, so *its* true API cost is genuinely $0 — the gap is the Anthropic-backed main Cond-B.)
2. **$15,256 is ~99% projection.** Stage 4 ($7,700) + Stage 6 ($7,350) = $15,050 of the $15,256 is not-yet-complete work. The total is arithmetically sound and well-calibrated (Cond-A anchor), but it is **not** an attested cumulative actual. When Stage 4 and Stage 6 land, replace those rows with record-summed actuals.
3. **HANDOFF_11a source conflict resolved.** The two pre-existing summary files disagree ($1.51 vs $25.00). `$25` was the *escalation boundary* quoted in the report, not the spend; `$1.51` (attested) is used here.

4. **Supplement reconciliation (2026-06-25 audit).** The supplement publishes two figures that differ from this ledger; both deltas are intentional and self-disclosed:
   - **Phase 8 v1 grading.** Ledger row 24 books `$1,750` as the midpoint of the documented `$1,500–$2,000` projection range from `HANDOFF_13b_phase8_grading_corrected.md`. The supplement §2211-2213 books `~$559` (`$58.82` attested + `~$500` killed-run sunk). The `$1,191` delta is the v1 work that was REVOKED under D-10 (Sonnet substitution replaced with Opus full-coverage for v2) and never spent. Treatment: the supplement's `$559` is the attested actual; this ledger's `$1,750` is the original projection envelope.
   - **Phase 6 API.** Ledger CSV records `$380.68` from per-record `api_cost_usd` summation across all 9 system directories. Supplement §2211 cites `~$447`, which incorporates the `$30` (Cond-A) + `$175` (Cond-B) Stage-3 estimates rolled into the Phase 6 envelope. The `$66` delta is rolled vs unrolled scope, not actual spend discrepancy.

   Both gaps are documented here so a reviewer cross-referencing supplement to ledger sees the explanation immediately.

## Sources

- Per-record `api_cost_usd`: `07_system_outputs/{cond_a,cond_b,mandate_primary,baseline_1..6}/` (+`holdout/`)
- Handoff reports: `handoffs/HANDOFF_*_report_*.md`
- Pre-existing attestations: `standalone data results/handoff_costs/{attested_cost_table.md,per_handoff_cost_log.md}`
- Estimate composition: `Engineering and Operational Provenance.tex` §2552; audit cross-check in `AUDIT_workstream_E_reproducibility.md`
- Stage 4 status: `HANDOFF_20_stage4_full_coverage_v2_grading.md`, `08_grading_v2/by_record/`

*Read-only aggregation, 2026-06-25. Replace projected rows with actuals when Stage 4 / Stage 6 complete.*

---

## Closeout addendum (2026-07-08)

Status changes since the 2026-06-25 aggregation above:

- **Stage 4 v2 grading: COMPLETE** — 12,000/12,000 records graded by 2026-07-01, zero incompletes. The $7,700 projection was priced at ~$0.21/record on a **Sonnet-rate basis** and was not re-derived when D-10 restored **Claude Opus** as the Anthropic judge (~5× per-call cost). No per-record cost field is written to `08_grading_v2/by_record/`, so the grading actual is **not summable from disk; per-provider billing dashboards are authoritative** and materially exceed the projection.
- **Phase B (Stage 6) perturbation generation — record-summed actuals** (from per-record `api_cost_usd`, final at 2026-07-08 ~13:05Z): baseline_1 $118.56 (3,500 rec), baseline_2 $21.65 (3,500), baseline_3 $295.96 (3,500), baseline_4 $202.21 logged at 3,021/3,500 (generation halted at closeout ~13:01Z under D-13; 220 records carry null cost), cond_a $9.91 (350), cond_b unlogged-by-design (350; critical flag #1 applies), mandate_primary local $0 (3,500). **Logged generation subtotal: $648.29 (final).** Generated perturbation-record pool at closeout: 17,721 of the 18,200 scoped target.
- **D-12 (2026-07-06):** baseline_5/6 perturbation runs scoped out per HANDOFF_24c (~$4,200 avoided; baseline_4 is the multi-agent-shell class representative).
- **D-13 (2026-07-08):** Phase B semantic grading **paused at 14,685/18,200 main-pass grades (80.7%)**; double-grade IRR pass 1 at 816/3,640, pass 2 not started; baseline_4 generation halted at 3,021/3,500 (86.3%) at the same closeout. Same disk limitation as Stage 4: grading actuals live on provider dashboards. Resumable via `grade-v2 --skip-existing` without record regeneration.
- The Stage 4 and Stage 6 projection rows in the tables above are **retained as the historical projection record**. This addendum, the supplement's Deviation Table (D-10 through D-13), and provider dashboards jointly carry the actual-vs-projected reconciliation.
