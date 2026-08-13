# Setup

Project directory structure, environment, and tooling. Complete this setup on day 1 before any other work.

---

## 1. Project Root

Create the project root directory. Recommended location: `/work/mandate_eval_2026Q2/` or equivalent under the lab's shared storage so SMEs can access shared artifacts.

```bash
PROJECT_ROOT=/work/mandate_eval_2026Q2
mkdir -p $PROJECT_ROOT
cd $PROJECT_ROOT
git init
```

## 2. Directory Structure

Create the complete structure on day 1:

```
mandate_eval_2026Q2/
├── 00_preregistration/
│   ├── protocol_v1.0.md
│   ├── zenodo_doi.txt
│   └── approvals/
├── 01_pilot/
│   ├── tasks/
│   ├── signoffs/
│   ├── runs/
│   ├── grading/
│   └── pilot_findings_memo.md
├── 02_calibration/
│   ├── tasks/                     # Copy from package calibration_tasks/
│   ├── runs/
│   └── pass_fail_report.md
├── 03_corpus/
│   ├── candidates/                # Raw AI-generated candidate pool (~225 tasks)
│   ├── domain_security/           # Final 30 tasks per domain
│   ├── domain_financial/
│   ├── domain_intel/
│   ├── deduplication_report.md
│   ├── realism_audits/
│   └── tags/                       # corpus_freeze_v1
├── 04_ground_truth/
│   ├── scaffolds/                  # AI-scaffolded candidate anchors
│   ├── signoff_packets/            # Distributed to SMEs
│   ├── signed_anchors/             # Final signed ground truth
│   ├── overlap_sample/             # 12-task IRR overlap
│   ├── external_spotcheck/         # 9-task independent review
│   ├── irr_computation.ipynb
│   └── tags/                       # gt_freeze_v1
├── 05_baselines/
│   ├── calibration_logs/
│   ├── frozen_configs/
│   │   ├── baseline_1_singleprompt/
│   │   └── baseline_2_react/
│   └── tags/                       # baseline_freeze_v1
├── 06_perturbations/
│   ├── PERT-T1-001.json
│   ├── ...
│   └── tags/                       # perturbation_freeze_v1
├── 07_system_outputs/
│   ├── mandate/
│   │   ├── TASK-SEC-001/
│   │   │   ├── run_1/
│   │   │   ├── run_2/
│   │   │   └── run_3/
│   │   └── ...
│   ├── baseline_1/
│   ├── baseline_2/
│   ├── ablation_1_no_role_sep/
│   ├── ablation_2_no_registry/
│   ├── ablation_3_no_trace/
│   ├── anonymization_mapping.json   # KEEP OUT OF GRADER ACCESS
│   └── tags/                        # outputs_freeze_v1
├── 08_grading/
│   ├── judge_1_gpt4o/
│   ├── judge_2_claude_opus/
│   ├── judge_3_gemini_pro/
│   ├── ensemble_aggregated/
│   ├── inter_grader_sample/
│   ├── kappa_computation.ipynb
│   └── failure_coding/
│       └── failure_coding_master.csv
├── 09_analysis/
│   ├── 01_corpus_and_signoff_summary.ipynb
│   ├── 02_system_outputs_summary.ipynb
│   ├── 03_primary_hypothesis_tests.ipynb
│   ├── 04_exploratory_subgroups.ipynb
│   ├── 05_sensitivity_analyses.ipynb
│   ├── 06_ablation_results.ipynb
│   ├── 07_failure_modes.ipynb
│   ├── 08_final_tables_and_figures.ipynb
│   └── figures/
├── 10_report/
│   ├── final_report_v1.md
│   ├── executive_summary.md
│   └── deviation_log.md
├── 11_replication_package/
│   ├── README.md
│   ├── environment.yml
│   └── (assembled at end of project)
├── status_reports/
│   ├── week_01.md
│   ├── week_02.md
│   └── ...
├── prompts_used/
│   └── (snapshots of prompts as actually used per phase)
└── README.md                        # Project-level README
```

Bash script to create the structure:

```bash
#!/bin/bash
set -e
PROJECT_ROOT=/work/mandate_eval_2026Q2
mkdir -p $PROJECT_ROOT
cd $PROJECT_ROOT

# Create all directories
mkdir -p 00_preregistration/approvals
mkdir -p 01_pilot/{tasks,signoffs,runs,grading}
mkdir -p 02_calibration/{tasks,runs}
mkdir -p 03_corpus/{candidates,domain_security,domain_financial,domain_intel,realism_audits,tags}
mkdir -p 04_ground_truth/{scaffolds,signoff_packets,signed_anchors,overlap_sample,external_spotcheck,tags}
mkdir -p 05_baselines/{calibration_logs,frozen_configs/baseline_1_singleprompt,frozen_configs/baseline_2_react,tags}
mkdir -p 06_perturbations/tags
mkdir -p 07_system_outputs/{mandate,baseline_1,baseline_2,ablation_1_no_role_sep,ablation_2_no_registry,ablation_3_no_trace,tags}
mkdir -p 08_grading/{judge_1_gpt4o,judge_2_claude_opus,judge_3_gemini_pro,ensemble_aggregated,inter_grader_sample,failure_coding}
mkdir -p 09_analysis/figures
mkdir -p 10_report
mkdir -p 11_replication_package
mkdir -p status_reports
mkdir -p prompts_used

# Init git
git init
echo "node_modules/" > .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".ipynb_checkpoints/" >> .gitignore
echo "07_system_outputs/anonymization_mapping.json" >> .gitignore  # Keep mapping out of accidental commits

git add .gitignore
git commit -m "Initial structure"

echo "Project structure created at $PROJECT_ROOT"
```

---

## 3. Python Environment

Create a conda environment from the spec in `ANALYSIS_PLAN.md`:

```bash
conda env create -f environment.yml
conda activate mandate_eval
```

Verify:

```bash
python -c "import numpy, pandas, scipy, sklearn, statsmodels, krippendorff; print('OK')"
```

---

## 4. Model Access

Set up API keys for the model families used in this evaluation:

| Purpose | Provider | API Key Environment Variable |
|---------|----------|------------------------------|
| Task generation, scaffolding | Anthropic | `ANTHROPIC_API_KEY` |
| Baseline 1, Judge 2 | Anthropic | `ANTHROPIC_API_KEY` |
| Judge 1 | OpenAI | `OPENAI_API_KEY` |
| Judge 3 | Google | `GOOGLE_API_KEY` |
| MANDATE internal (Qwen3) | Local Ollama | N/A |

Store keys in a `.env` file (gitignored). Verify access with a smoke test before Phase 0:

```python
import anthropic, openai
# Test calls to each provider
```

For MANDATE itself, verify Ollama is running and the Qwen3 fine-tuned models are loaded:

```bash
ollama list  # Should show all 6 fine-tuned MANDATE role models
```

If any are missing, check with Cal on which AEGIS (Autonomous Engineering Governance and Intelligence System) version to deploy from.

---

## 5. AEGIS Reference Implementation Access

Cal will provide read access to the AEGIS repository. Clone to:

```
/work/mandate_eval_2026Q2/tools/aegis/
```

Check out the specific git tag committed in the pre-registration. Do not modify AEGIS code during the evaluation.

---

## 6. Embedding Model for Deduplication

Use a sentence embedding model for corpus deduplication (Section 8.6 of playbook). Recommended: `BGE-large-en-v1.5` or `intfloat/e5-large-v2` from Hugging Face.

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-large-en-v1.5')
embeddings = model.encode([task_text_1, task_text_2, ...])
# Cosine similarity matrix
```

Validate the 0.85 cosine threshold on a calibration test: 20 known-distinct task pairs (no concerning similarity) and 20 known-paraphrase pairs (e.g., the three phrasings in Playbook Section 7.4). Threshold should achieve at least 90% paraphrase detection.

---

## 7. Tooling Checklist

Before declaring setup complete:

- [ ] Project root created with full directory structure
- [ ] Git initialized with .gitignore
- [ ] Python environment created and verified
- [ ] All API keys configured and tested
- [ ] Ollama running with Qwen3 fine-tuned models loaded
- [ ] AEGIS repository cloned at the committed git tag
- [ ] Embedding model downloaded and tested
- [ ] Zenodo account created for pre-registration deposit
- [ ] Calibration task files copied from package to `02_calibration/tasks/`
- [ ] This README and the playbook copied to project root
- [ ] Forms file copied for reference
- [ ] Slack channel or other comms set up for SMEs and Cal

When all items are checked, the project is ready for Phase 0.

---

## 8. Backup and Recovery

- Daily backup of `/work/mandate_eval_2026Q2/` to lab storage
- Git commit at the end of each phase with a tag
- Frozen tag artifacts (corpus_freeze_v1, gt_freeze_v1, etc.) are immutable; verify via git tag protection
- The anonymization mapping file is THE critical file to back up; loss compromises grading

---

**End of setup.**
