# Analysis Plan and Notebook Structure

This document specifies how to compute every metric, statistical test, and visualization required by the pre-registration. Build the analysis notebooks following this structure exactly; the structure mirrors the pre-registration so the reporting maps 1:1 to what was committed.

---

## Notebook 1: `01_corpus_and_signoff_summary.ipynb`

**Inputs:** Frozen corpus, all SME signoffs, external spot-check.
**Outputs:** Corpus summary, IRR statistics, realism audit summary.

### Sections

1. **Corpus composition**
   - Tasks per domain
   - Category distribution within domain
   - Diversity dimensions (stakeholder type, deliverable format, time horizon, scope)
   - Word count distribution

2. **SME signoff completion**
   - Time per task per reviewer (mean, median, 95th percentile)
   - Deviation from AI scaffold (high / medium / low / none distribution)
   - Tasks flagged "requires discussion" with resolution

3. **Inter-rater reliability**
   - Pairwise Cohen's kappa on the 12-task overlap sample
     - Binary judgments: is task gap-triggering, is field X classified as Y
   - Krippendorff's alpha across all 3 reviewers on ordinal field classification
   - Report kappa with 95% CI via bootstrap

4. **External spot-check agreement**
   - Per-task agreement between external reviewer and SME-signed ground truth
   - Aggregate percent agreement and kappa
   - Discrepancy notes if external/internal kappa is meaningfully lower than internal/internal kappa

5. **Realism audit results**
   - Mean rating per task
   - Distribution of ratings
   - Tasks below 2.5 threshold and disposition

### Key computations

```python
# Cohen's kappa with bootstrap CI
from sklearn.metrics import cohen_kappa_score
from scipy.stats import bootstrap

def kappa_with_ci(rater1, rater2, n_bootstrap=10000):
    point = cohen_kappa_score(rater1, rater2)
    # Bootstrap over the paired ratings
    res = bootstrap(
        (list(zip(rater1, rater2)),),
        statistic=lambda paired: cohen_kappa_score(
            [p[0] for p in paired], [p[1] for p in paired]
        ),
        n_resamples=n_bootstrap,
        confidence_level=0.95,
    )
    return point, res.confidence_interval

# Krippendorff's alpha
# Use the krippendorff package
import krippendorff
alpha = krippendorff.alpha(
    reliability_data=ratings_matrix,
    level_of_measurement='ordinal'
)
```

---

## Notebook 2: `02_system_outputs_summary.ipynb`

**Inputs:** All system outputs across all 3 systems × 90 tasks × 3 runs + 150 perturbations × 3 runs.
**Outputs:** Execution success rates, timing distributions, stochastic stability.

### Sections

1. **Execution completion rates**
   - Per system: percentage of tasks producing valid output
   - Per system: percentage of perturbations producing valid output
   - Crash / timeout rates per system

2. **MANDATE-specific metrics**
   - Fallback rate to deterministic path
   - Per-role timing distributions (median, 95th percentile, max)
   - Trace chain length distribution

3. **Stochastic stability (3-run variance)**
   - Per task: agreement across 3 runs on key outputs (anchor fields extracted, gap flagged)
   - System-level stability rate: percentage of tasks where all 3 runs produced equivalent outputs
   - Tasks flagged unstable: list and qualitative note

### Key computations

```python
# Stability rate: fraction of tasks where output_run_1 == output_run_2 == output_run_3
def stability_rate(outputs_by_run, equivalence_fn):
    n_total = len(outputs_by_run)
    n_stable = sum(
        equivalence_fn(runs[0], runs[1]) and equivalence_fn(runs[1], runs[2])
        for runs in outputs_by_run.values()
    )
    return n_stable / n_total
```

---

## Notebook 3: `03_primary_hypothesis_tests.ipynb`

**Inputs:** All grader outputs (ensemble-aggregated), ground truth.
**Outputs:** Primary hypothesis test results with effect sizes and CIs.

### Sections

1. **Ensemble grading aggregation**
   - For each (system, task, run) tuple, aggregate the 3 judges:
     - Binary: majority vote
     - Continuous: median
     - Categorical: majority (escalate ties to human adjudication)
   - Report per-judge agreement rates

2. **Per-task metric computation**
   - Compute anchor completeness, gap F1, trace completeness, adversarial resistance, fabrication rate per (system, task) using median across 3 runs

3. **H1: Anchor completeness**
   - System A (MANDATE) vs Baseline 1
   - Paired comparison across the 90-task corpus
   - Wilcoxon signed-rank test
   - Cohen's d with 95% bootstrap CI

4. **H2: Gap detection F1**
   - System A vs Baseline 1 on gap-triggering tasks
   - System A vs Baseline 2 on gap-triggering tasks
   - McNemar's test on gap classification accuracy
   - Cohen's h with 95% bootstrap CI for each comparison

5. **H3: Trace completeness rate**
   - System A only: rate of complete trace chains
   - One-sample binomial test against 95% threshold
   - 95% Wilson CI on the rate

6. **H4: Adversarial resistance**
   - System A vs Baseline 1 vs Baseline 2 on 30 prompt injection trials each
   - Pairwise McNemar's tests
   - Cohen's h with 95% bootstrap CI

7. **Family-wise error correction**
   - Holm-Bonferroni applied across the 4 primary tests
   - Adjusted p-values reported alongside raw

### Key computations

```python
# McNemar's test on paired binary outcomes
from statsmodels.stats.contingency_tables import mcnemar

def mcnemar_paired(system_a_results, system_b_results):
    # results are arrays of binary outcomes per task
    table = [[0, 0], [0, 0]]
    for a, b in zip(system_a_results, system_b_results):
        table[1-a][1-b] += 1
    result = mcnemar(table, exact=True)
    return result.statistic, result.pvalue

# Cohen's h
import numpy as np
def cohens_h(p1, p2):
    return 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))

# Holm-Bonferroni
from statsmodels.stats.multitest import multipletests
pvals = [p_h1, p_h2_b1, p_h2_b2, p_h3, p_h4_b1, p_h4_b2]
rejected, pvals_corrected, _, _ = multipletests(pvals, alpha=0.05, method='holm')
```

---

## Notebook 4: `04_exploratory_subgroups.ipynb`

**Inputs:** Per-task metrics from Notebook 3.
**Outputs:** Subgroup analyses with FDR-corrected p-values.

### Sections

1. **Per-domain breakdown**
   - Each primary metric × 3 domains
   - System comparisons per domain

2. **Gap-triggering vs full-specification subgroup**
   - Performance on each subset

3. **Stakeholder type subgroup**
   - Executive vs operational stakeholder performance

4. **Task complexity subgroup**
   - Tertile split on word count
   - Performance per tertile

5. **Per-sub-type adversarial resistance**
   - Direct command vs social engineering vs fake authority injection
   - Per-system rates

6. **Ablation comparisons (deferred until Notebook 6)**

7. **FDR correction (Benjamini-Hochberg)**

### Key computations

```python
# Benjamini-Hochberg FDR
from statsmodels.stats.multitest import multipletests
rejected, pvals_corrected, _, _ = multipletests(
    subgroup_pvals, alpha=0.05, method='fdr_bh'
)
```

---

## Notebook 5: `05_sensitivity_analyses.ipynb`

**Inputs:** Per-task metrics, SME IRR by task.
**Outputs:** Robustness of headline findings to 3 sensitivity perturbations.

### Sections

1. **Sensitivity 1: Exclude low-IRR tasks**
   - Drop tasks where SME pairwise kappa < 0.4 on that task's domain
   - Re-run primary tests
   - Compare to headline finding

2. **Sensitivity 2: Mean vs median across runs**
   - Re-compute per-task metrics using mean instead of median
   - Re-run primary tests

3. **Sensitivity 3: Drop worst run per task**
   - Re-compute metrics dropping the worst run per task
   - Re-run primary tests

4. **Sensitivity stability table**
   - For each primary finding: does the effect direction hold under all 3 sensitivities? Does statistical significance hold?

---

## Notebook 6: `06_ablation_results.ipynb`

**Inputs:** Ablation system outputs on 20-task subset.
**Outputs:** Component-contribution analysis.

### Sections

1. **Per-ablation metric computation**
   - Anchor completeness, gap F1, trace completeness, fabrication rate
   - For full MANDATE, Ablation 1, Ablation 2, Ablation 3

2. **Paired comparison: full MANDATE vs each ablation**
   - Wilcoxon signed-rank tests
   - Effect sizes

3. **Interpretation**
   - Which components contribute meaningfully?
   - Which contribute less than expected?

---

## Notebook 7: `07_failure_modes.ipynb`

**Inputs:** Failure coding master CSV.
**Outputs:** Failure mode distribution analysis.

### Sections

1. **Failure category distribution per system**
   - Stacked bar chart per system

2. **Failure patterns by domain**
   - Are some failure modes domain-specific?

3. **Failure mode by perturbation type**
   - For perturbation runs only, which perturbations cause which failure modes?

4. **Qualitative narrative**
   - Top 3 failure patterns per system with example excerpts (anonymized)

---

## Notebook 8: `08_final_tables_and_figures.ipynb`

**Inputs:** Output tables from all previous notebooks.
**Outputs:** Publication-ready tables and figures.

### Sections

1. **Table 1: Primary results**
2. **Table 2: Per-domain breakdown**
3. **Table 3: Robustness**
4. **Table 4: Ablations**
5. **Table 5: Inter-rater reliability**
6. **Figure 1: Anchor completeness distribution per system**
7. **Figure 2: Gap detection precision-recall**
8. **Figure 3: Robustness retention by perturbation type**
9. **Figure 4: Failure mode distribution**
10. **Figure 5: Ablation component contribution**

All figures rendered as SVG and PNG, deposited in `06_analysis/figures/`.

---

## Environment Specification

Reproducibility requires pinned versions. Save the following as `environment.yml`:

```yaml
name: mandate_eval
channels:
  - conda-forge
dependencies:
  - python=3.11
  - numpy>=1.26
  - pandas>=2.1
  - scipy>=1.11
  - scikit-learn>=1.4
  - statsmodels>=0.14
  - matplotlib>=3.8
  - seaborn>=0.13
  - jupyter
  - pip
  - pip:
    - krippendorff>=0.6
    - sentence-transformers>=2.5
    - pyyaml
    - ollama
```

Pin specific versions before deposit. Record exact `pip freeze` output in the replication package.

---

## Computational Reproducibility Checklist

Before depositing the replication package:

- [ ] All notebooks execute end-to-end from a clean environment
- [ ] All random seeds are set explicitly
- [ ] All file paths are relative, not absolute
- [ ] All API model versions are pinned in pre-registration
- [ ] All analysis library versions are pinned in environment.yml
- [ ] All result tables in the final report are reproducible from the notebooks
- [ ] All figures in the final report are reproducible from the notebooks
- [ ] The README in the replication package describes the order of execution

---

**End of analysis plan.**
