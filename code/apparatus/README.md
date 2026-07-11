# Evaluation Apparatus (Workstream B)

The software that turns "run the MANDATE pipeline" into a blinded, pre-registered, multi-system comparison. This directory is not part of the package's SETUP tree; it holds Workstream B of the execution plan.

## Status

| Component | Plan ref | State |
|-----------|----------|-------|
| Uniform run harness | B1 | **Built and tested.** `harness/` |
| MANDATE-primary adapter | B1 / A2 | **Built and tested** (deterministic). Ollama mode now wires the Procedure-role RAG retriever, corrected after the apparatus audit. Reads MANDATE from `./AEGIS-eval/`, a frozen checkout at the pinned tag, so the live AEGIS working tree can drift without shifting the system under test. See `APPARATUS_AUDIT_v1` and the "Frozen AEGIS-eval" section below. |
| Reference self-test system | B1 | **Built and tested.** |
| A1 verification script | A1 | Built. **The 2026-05-23 A1 PASS is superseded:** it ran before the RAG retriever was wired into MANDATE-primary. A1 must be re-run on the eval host with the corrected config (`APPARATUS_AUDIT_v1`). `verify_mandate_primary.py`. |
| Baselines B1-B3 | B2 | **Built and mock-tested.** Single-prompt (Claude, GPT) and ReAct, in `baselines/`. Live calibration is Phase 4. |
| Baselines B4-B6 | B2 | **Apparatus shells built and mock-tested.** `baselines/multi_agent.py`: B4 PlannerReviewer (AutoGen-shape), B5 SequentialCrew (CrewAI-shape), B6 GraphRevision (LangGraph-shape). Each runs the framework's orchestration pattern with direct LLMClient calls so it is deterministic and mock-testable today; the framework integration (autogen-agentchat, crewai, langgraph) is the final step of Phase 4 baseline calibration on the eval host. Per Decisions memo Section 4 all three share one model so the framework is the variable. |
| Perturbation generator | B3 | **Built and mock-tested.** Seven types, three injection sub-types, in `perturbations/`. Generating the suite is Phase 5. |
| Anonymization pipeline | B4 | **Built and tested.** `anonymize.py`: strips identity, assigns random IDs, keeps the mapping separate. |
| Three-judge grading pipeline | B5 | **Built and mock-tested.** `grading/`: rubric, three judges, ensemble aggregation, inter-judge reliability. Live judges run in Phase 8. |
| Analysis modules | B6 | **Built and tested.** `analysis/`: `power.py` (simulation power), `models.py` (primary hypothesis tests), `descriptive.py` (corpus, sign-off, system-output summaries), `failure_modes.py` (the nine-category taxonomy). |
| Analysis notebooks 01-10 | B6 | **All built.** `09_analysis/`: 03 (power) runs now; 01, 02, 04-10 are drivers over the analysis modules that run in their phases and skip cleanly until their study inputs exist. |
| O1-O5 outcome scorers | B7 | **Built and tested.** `scoring/`: derives the five primary outcomes (and secondary O2b) from the three-judge grading, then collapses runs to the task-level unit of analysis. |
| Ablation variants A1-A7 | A4 | **Apparatus side built and tested.** `ablations/`: manifest, AblationSystem, tests. A3 (`emit_gaps=False`) and A5 (`success_registry=None`) are PipelineConfig switches and run today from AEGIS-eval. A1, A2, A4, A6, A7 require upstream AEGIS variant tags; the apparatus refuses to silently substitute MANDATE-primary until each variant's `aegis_ref` is pinned. |
| Corpus authoring pipeline | C2 | **Built and tested with a turn-key CLI.** `corpus/`: PROMPTS Section 1 task generator, PROMPTS Section 2 anchor scaffolder, cosine-0.85 dedup with sentence-transformer backend and a deterministic test fallback, leakage audit against the training corpus. `corpus/cli.py` exposes the pipeline as `python3 -m apparatus.corpus.cli {generate,scaffold,dedup,leakage,pilot}` so the eval-host run is one command per step. The §13 action 7 six-pilot-task sweep is `python3 -m apparatus.corpus.cli pilot`. Generation runs with `ANTHROPIC_API_KEY` set and the pinned Claude Opus 4 model. |
| Run ledger glue | B7 | Run ledger built (`harness/ledger.py`). |

## Layout

```
apparatus/
  harness/
    records.py    RunRecord + RoleTiming: the one schema every system emits
    system.py     the System interface (enforces the same-input contract)
    ledger.py     append-only JSONL run ledger
    runner.py     Task loader + run_matrix orchestrator
  systems/
    reference.py        dependency-free system, for harness self-test
    mandate_primary.py  wraps the AEGIS MANDATE pipeline (deterministic + ollama)
  baselines/
    schema.py           the baseline specification schema (shared, B1-B6)
    llm_client.py       Anthropic / OpenAI / mock LLM clients, with cost
    prompts.py          baseline prompts (single-prompt, ReAct)
    base.py             BaselineSystem base + JSON extraction
    single_prompt.py    B1 (Claude) and B2 (GPT)
    react.py            B3 (ReAct, Claude)
    multi_agent.py      B4 (PlannerReviewer / AutoGen-shape),
                        B5 (SequentialCrew / CrewAI-shape),
                        B6 (GraphRevision / LangGraph-shape)
    MULTI_AGENT_BASELINES.md  design note for B4 / B5 / B6
    tests/test_baselines.py     mock-client B1-B3 tests
    tests/test_multi_agent.py   mock-client B4-B6 tests
  perturbations/
    prompts.py          the 7 perturbation prompts (verbatim from PROMPTS.md 3)
    generator.py        PerturbationGenerator + PerturbedTask
    tests/test_perturbations.py
  grading/
    rubric.py           grader + schema-validity prompts (verbatim, PROMPTS 4/4a)
    judge.py            Judge, JudgeScore, SchemaCheck, three judge factories
    ensemble.py         majority/median aggregation, Cohen kappa, Krippendorff
    pipeline.py         GradingPipeline: orchestration, double-grading, IRR
    tests/test_grading.py
  analysis/
    power.py            Workstream B6: simulation-based power analysis
                        (drives 09_analysis/03_power_confirmation.ipynb)
    models.py           primary hypothesis tests: planned models, effect
                        sizes with bootstrap CIs, Holm correction,
                        robustness checks (drives notebook 04)
    descriptive.py      corpus / sign-off / IRR summaries (notebook 01) and
                        system-output / stability summaries (notebook 02)
    failure_modes.py    the nine-category failure taxonomy and distribution
                        (notebook 09)
    tests/test_power.py
    tests/test_models.py
    tests/test_descriptive.py
    tests/test_failure_modes.py
  scoring/
    outcomes.py         Workstream B7: derive O1-O5 (and secondary O2b)
                        per run from the three-judge grading
    aggregate.py        collapse runs to the task-level unit of analysis
                        (median across runs); the long-format table for
                        analysis notebook 04
    tests/test_scoring.py
  ablations/
    manifest.py         Workstream A4: the 7 ablation specs
                        (PROTOCOL_LOCK Section 5)
    system.py           AblationSystem: same harness path as MANDATE-
                        primary, ablation identity recorded on every run
    tests/test_ablations.py
  corpus/
    prompts.py          Workstream C2: PROMPTS Section 1 (task generation)
                        and Section 2 (anchor scaffolding), verbatim
    generator.py        TaskGenerator + TaskCandidate; parses the
                        numbered output into 5 candidates per run
    scaffolder.py       AnchorScaffolder + ScaffoldedAnchor for SME review
    embeddings.py       SentenceTransformerEmbedder (production) plus
                        HashEmbedder (tests); cosine_dedup at 0.85;
                        leakage_audit against a reference set
    cli.py              turn-key CLI: generate / scaffold / dedup /
                        leakage / pilot (§13 action 7 shortcut)
    tests/test_corpus.py
    tests/test_cli.py
  anonymize.py          Workstream B4: strip identity, assign random IDs,
                        keep the mapping separate
  tests/
    test_harness.py     dependency-free harness tests
    test_anonymize.py   anonymization tests
  run_demo.py             integration demo against the real AEGIS pipeline
  verify_mandate_primary.py  Workstream A1: confirms MANDATE-primary runs the
                          fine-tuned models with no silent fallback
```

## The same-input contract

The harness passes every system exactly one thing: the raw `request_text`
string. No structure, no hints, no extra context. This enforces PROTOCOL_LOCK
Section 11 (baseline fairness) at the interface level, so it cannot be
violated by accident when the baselines are added.

## MANDATE modes

`MandatePrimarySystem` runs in two modes:

- **deterministic**: the AEGIS rule-based path. Used for harness testing and
  as a substrate for some ablations. This is NOT MANDATE-primary as the
  protocol defines it.
- **ollama**: the fine-tuned six-role configuration. This IS MANDATE-primary.
  Confirming it runs with no silent fallback to the deterministic path is
  Workstream A1 and happens on the eval host with the fine-tuned models.

Every RunRecord carries the per-role `llm_used` and `llm_fallback` flags and a
derived `any_llm_fallback`. The execution plan flags this as the key
silent-failure detector: a MANDATE-primary run that fell back on any
fine-tuned role is not a clean observation and must be caught by the analysis.

## Frozen AEGIS-eval (the MANDATE source under test)

The evaluation imports MANDATE from a dedicated, read-only checkout at
`./AEGIS-eval/`, recreated from the upstream AEGIS tag
`mandate-eval-primary-2026q2-v1` (commit `4f8af83`). This separation matters:
the live AEGIS working tree at `~/Desktop/AEGIS` is where the framework is
iterated; pointing the eval at it would let upstream changes silently shift
the system under test. `AEGIS-eval/` is frozen at the tagged state and is
the path the apparatus reads, so MANDATE-primary runs independently of
whatever AEGIS does upstream after the freeze.

To recreate `AEGIS-eval/` (also the path a replicator would follow):

```bash
# from a clone of the upstream AEGIS:
mkdir -p AEGIS-eval
git archive mandate-eval-primary-2026q2-v1 | tar -x -C AEGIS-eval
```

Run the deterministic smoke test from the frozen tree:

```bash
python3 apparatus/run_demo.py --aegis ./AEGIS-eval
```

This is the independence proof: MANDATE-primary imports and runs from the
frozen tree alone, with no reference to the live AEGIS path. The A1
verification on the eval host (`apparatus/verify_mandate_primary.py`) runs
against this same path, in `ollama` mode against the fine-tuned models.

`AEGIS-eval/` is gitignored: it is reproducible from upstream and not part
of the eval repository's committed content. Every RunRecord still records
`code_ref` as the AEGIS tag / commit, which is the durable provenance.

## Outcome scoring (Workstream B7)

`scoring/` is the coded path from grading to the pre-registered hypotheses.
The three-judge grading pipeline produces rubric dimensions; it does not
produce the five primary outcomes. `scoring/outcomes.py` derives them, one
run at a time, exactly as PROTOCOL_LOCK Section 4 operationalizes each:

- **O1** anchor completeness is the count-weighted coverage across the
  minimum, target and constraint field groups, weighted by the ground-truth
  field counts. An unweighted mean of the three rubric coverages is a
  different estimand and is not used.
- **O2a** gap recall and **O2b** gap precision map the ensemble
  `gap_classification` to recall (TP / FN) and precision (TP / FP)
  observations, on the gap-triggering task subset.
- **O3** fabrication rate is the ensemble-median fabrication count.
- **O4** schema validity is the strict majority of the judges' Section 4a
  schema checks (`grading.ensemble.aggregate_schema`).
- **O5** adversarial resistance is `1 - adversarial_compliance` on
  prompt-injection trials; its unit of analysis is the perturbation.

`scoring/aggregate.py` then collapses runs to the task-level unit of analysis
(median across runs, PROTOCOL_LOCK Section 6.3; per perturbation for O5) and
emits the long-format table that analysis notebook 04 feeds to the
mixed-effects models. Runs flagged not clean (a failed run, or a silent
fine-tuned-role fallback) are excluded from the median and counted, so the
exclusion is visible.

One open item for the PI, flagged here rather than resolved in code: O2b
precision is defined as TP / (TP + FP) **on gap-triggering tasks**, but on a
gap-triggering task the ground truth expects a gap, so a clean false positive
is structurally rare on that subset and O2b can be near-degenerate. The
scorer implements the estimand as written; whether O2b is measured on a wider
subset is a pre-registration decision.

## Analysis layer (Workstream B6)

`analysis/` holds the statistics, and `09_analysis/` holds the ten notebooks
that drive them. The split is deliberate: every computation that has to be
correct lives in a unit-tested module, and each notebook is a thin driver
that loads its phase's study inputs and calls the module.

`models.py` is the primary analysis (Notebook 04). For each of O1, O2a, O3,
O4, O5 it fits the pre-registered model (a linear mixed model for the
bounded-continuous outcomes, a Poisson GEE for the fabrication count, a
logistic GEE for the binary rates), estimates the effect size with a
domain-stratified bootstrap CI, runs the model-free robustness check
(Wilcoxon or McNemar), applies the Holm-Bonferroni correction across the
family of five, and compares each result to its operational threshold. For
this two-system paired design the planned model's system test equals the
within-task paired comparison; if the model fails to converge, the exact
paired test stands in and the substitution is recorded in `model_method`,
never hidden.

`descriptive.py` carries the Notebook 01 and 02 summaries: corpus
composition, SME sign-off, inter-rater reliability with bootstrap CIs and the
McHugh bands, execution completion, MANDATE fallback accounting, per-role
timing, and stochastic stability. `failure_modes.py` carries the Notebook 09
nine-category failure taxonomy, validates a coding against it, and offers an
advisory category suggestion that never replaces the manual coding.

The notebooks 01, 02, 04-10 run in their respective phases (3, 6, 7, 8). Each
loads its study input from the canonical path and, when that input is not yet
present, prints a clear gated-status block and skips its analysis. None
fabricates study data. Notebook 03 (power confirmation) is the exception: it
needs no study data and runs now.

## How to run

```bash
# full apparatus unit suite (no AEGIS, no API needed)
python3 -m pytest apparatus -q

# harness unit tests only
python3 -m pytest apparatus/tests -q

# integration demo against the real AEGIS deterministic pipeline
python3 apparatus/run_demo.py --aegis /path/to/AEGIS
```

The demo writes to `apparatus/_demo_output/`, which is gitignored and is not
part of the study record.

## Verification status, 2026-05-23

Full apparatus unit suite: 193 of 193 pass (harness, MANDATE adapter, all
six baselines B1-B6, perturbations, anonymization, three-judge grading,
power simulation, the B7 O1-O5 scorers, the B6 analysis modules, the
seven A4 ablation specs with their A3 / A5 config-switch smoke runs from
AEGIS-eval, the C2 corpus pipeline, and the corpus CLI). The nine analysis notebooks 01, 02, 04-10 were each executed
end to end in their no-data state: every notebook runs cleanly, prints its
gated-status block, and skips its analysis until the study inputs of its
phase exist. Notebook 03 (power) runs the real power confirmation now,
since it needs no study data.

The demo executed the real AEGIS deterministic MANDATE pipeline over the six
calibration tasks: 6 of 6 runs ok, six role timings captured per run, the
mandate-as-code artifact captured in each RunRecord, ledgers and per-run
output JSON written. No study data was generated; the calibration tasks are
a positive control, and deterministic mode is not the protocol's
MANDATE-primary.
