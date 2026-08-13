# RunRecord Schema v1 — Documentation

Companion to `runrecord_schema_v1.json` (JSON Schema **Draft 2020-12**). The schema validates the per-run output records under `07_system_outputs/<system>/*.json` for the MANDATE 2026Q2 evaluation.

## How it was generated

Inferred (via `genson`) from the **full population of 12,036 RunRecords** across the nine output directories listed in the deposit plan: `mandate_primary`, `cond_a`, `cond_b`, and `baseline_1`…`baseline_6` (main + hold-out). **Every one of the 12,036 records validates against the schema (`12,036/12,036 pass`, Draft 2020-12 validator).**

> **Note on scope.** The briefing phrased the input as "50 records per system / 350 across 7 systems." An initial 50-per-system draft over-fit the sample — about 4.4% of the full corpus failed (concentrated in `baseline_3`), because `output.specification.{minimum,target,constraints}` has several variant shapes and at least one record carries a `null` specification that a small sample missed. The schema was therefore rebuilt from the **entire population**: a schema reviewers run against the real records must validate all of them, not just a sample. ("7 systems" most likely referred to the 7-system v1 main matrix, `mandate_primary` + B1–B6; Cond-A/Cond-B are included here too.)

`required` at each object level captures the fields present in **every** record. Fields that vary by system family — chiefly everything under `output` (MANDATE systems carry `output.artifact.*`; baselines carry `output.specification.*`) — are optional in the schema. This is deliberate: one schema validates all nine system types.

## Top-level RunRecord envelope (22 required fields)

The envelope is identical across all systems.

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string | Unique run id, `"<system>__<task_id>__r<NN>"`. |
| `task_id` | string | Corpus task identifier (e.g., `TASK-MAIN-FIN-003`). |
| `system_id` | string | System/condition: `mandate_primary`, `cond_a`, `cond_b`, `baseline_1..6`. |
| `system_label` | string | Human-readable system description. |
| `run_number` | integer | Run index within the task (seed replicate). |
| `seed` | integer | RNG seed for the run. |
| `started_at` | string | ISO-8601 start timestamp. |
| `wall_clock_ms` | number | Total wall-clock time (ms). |
| `local_compute_ms` | number | Local compute time (ms). |
| `api_cost_usd` | number \| null | API cost in USD. **`null` for local-only systems (`mandate_primary`, `cond_b`); populated for `cond_a` (~$0.025) and baselines.** |
| `model_versions` | object | Model identifiers, e.g. `{mlt, llm_model}`. |
| `decoding_params` | object | Run configuration (condition, backend, temperature, max tokens, profile mode, …). |
| `code_ref` | string | Code/stack version (e.g., `mlt-stack-1.0.0rc1`). |
| `harness_version` | string | Eval harness version. |
| `output_type` | string | `MANDATE_AS_CODE` (MANDATE systems) or `BASELINE_SCHEMA:specification` (baselines). |
| `output` | object | The system output; shape depends on `output_type` (see below). |
| `role_timings` | array | Six per-role timing objects: `role_name`, `status`, `duration_ms`, `llm_used`, `llm_fallback`, `llm_fallback_reason`. |
| `llm_roles_used` | array | Role names that invoked the LLM. |
| `any_llm_fallback` | boolean | Whether any role fell back to the deterministic path. |
| `fallback_roles` | array | Roles that fell back. |
| `errors` | array | Error strings (empty when `ok=true`). |
| `ok` | boolean | Whether the run produced a structurally valid result. |

## The `output` object (two families)

### MANDATE systems (`mandate_primary`, `cond_a`, `cond_b`) — `output_type = MANDATE_AS_CODE`

- `output.artifact` — the mandate-as-code artifact:
  - `mandate_id`, `version`, `generated`
  - `anchor` — `{ mission_intent, minimum, target, constraints[], risk_tolerance, anchor_hash }` (`anchor_hash` = RFC 8785 JCS + SHA-256 over the anchor; Formal Property 1)
  - `courses_of_action[]` — COA objects (`coa_id`, `approach`, `procedures`, `task_dag`, `risk_assessment`, `off_nominal_triggers`)
  - `recommendation` — `{ primary_coa, fallback_sequence[], rationale }`
  - `trace` — **object** `{ chain_hash, entry_count, entries[6] }`: the 6-entry hash-chained provenance (Formal Property 2). *Note `trace` is an object, not a list; the entries are at `trace.entries`.*
  - `registry_reference` — success-registry match info (`match_type`, `similar_mandates[]`, …)
  - `metadata` — NIST RMF mapping, `sources_consulted[]`, `input_hash`, `output_hash`, `extraction_failed_constraints`, …
- `output.gap_reports[]` — emitted specification-gap reports (`gap_id`, `gap_type`, `severity`, `detected_by`, `pipeline_stage`, `evidence`, `remediation`, `readiness_score`, …)
- `output.has_gaps` — boolean
- Cond-A adds `output.mission_input_metadata`; Cond-B adds `output.domain_profile_mode`, `output.domain_profile_name`, `output.extraction_failed_constraints`, `output.metadata`.

### Baselines (`baseline_1`…`baseline_6`) — `output_type = BASELINE_SCHEMA:specification`

- `output.specification` — the baseline's structured specification output
- `output.raw_text` — raw model text
- `output.schema_valid` — boolean
- `output.schema_errors[]` — schema-validation errors

Baselines have **no** `output.artifact`, `trace`, or `gap_reports` — this is the structural distinction the evaluation measures between MANDATE-as-code and free-form baseline output.

## Per-system example records (one per system)

Each block is a real sampled record with long free-text values truncated (`…⟨trunc⟩`) and large nested arrays/objects collapsed to their structure for readability. The exact source file is named so reviewers can open the full record.

### mandate_primary

*Source: `07_system_outputs/mandate_primary/mandate_primary__TASK-MAIN-INT-010__r02.json`*

```json
{
  "run_id": "mandate_primary__TASK-MAIN-INT-010__r02",
  "task_id": "TASK-MAIN-INT-010",
  "system_id": "mandate_primary",
  "system_label": "MANDATE-primary",
  "run_number": 2,
  "seed": 20260607,
  "started_at": "2026-06-08T22:36:05Z",
  "wall_clock_ms": 103621.9311,
  "role_timings": [
    {
      "role_name": "Intake",
      "status": "success",
      "duration_ms": 11039.821,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    },
    "\u2026(+5 more, len=6)"
  ],
  "api_cost_usd": null,
  "local_compute_ms": 103621.9311,
  "model_versions": {
    "Intake": "mandate-intake",
    "Interpreter": "mandate-interpreter",
    "Decomposition": "mandate-decomp",
    "Procedure": "mandate-procedure",
    "Binding": "mandate-binding",
    "Validation": "mandate-validation"
  },
  "decoding_params": {
    "llm_backend": "ollama",
    "llm_base_url": "http://localhost:11434",
    "llm_timeout_s": 300.0,
    "llm_default_model": "",
    "llm_fallback_enabled": true,
    "llm_prompt_dir": "./AEGIS-eval/config/system-prompts",
    "llm_prompt_require_files": false,
    "llm_retrieval_k": 5,
    "llm_registry_top_k": 5,
    "llm_role_models": {
      "Intake": "mandate-intake",
      "Interpreter": "mandate-interpreter",
      "Decomposition": "mandate-decomp",
      "Procedure": "mandate-procedure",
      "Binding": "mandate-binding",
      "Validation": "mandate-validation"
    },
    "llm_role_temperatures": {
      "Intake": 0.0,
      "Interpreter": 0.1,
      "Decomposition": 0.2,
      "Procedure": 0.1,
      "Binding": 0.1,
      "Validation": 0.0
    },
    "llm_role_max_tokens": {
      "Intake": 1024,
      "Interpreter": 2048,
      "Decomposition": 4096,
      "Procedure": 4096,
      "Binding": 2048,
      "Validation": 2048
    },
    "llm_role_retries": {
      "Intake": 2,
      "Interpreter": 2,
      "Decomposition": 3,
      "Procedure": 3,
      "Binding": 2,
      "Validation": 2
    },
    "rag_retriever_wired": true
  },
  "code_ref": "mandate-eval-primary-2026q2-v1",
  "harness_version": "0.1.0",
  "output_type": "MANDATE_AS_CODE",
  "output": {
    "artifact": {
      "mandate_id": "TASK-MAIN-INT-010",
      "version": "1.0",
      "generated": "2026-06-08T22:36:16.847Z",
      "anchor": {
        "mission_intent": "We need a comprehensive intelligence collection plan focused on two interconnected threat streams identified in the late\u2026\u27e8trunc\u27e9",
        "minimum": {
          "description": "Validated collection requirements deconflicted through relevant mission managers."
        },
        "constraints": [],
        "anchor_hash": "0436733a3ab50276112a63b2ddb1a6c2abc3d71be9f044996e2bd39f366f7350",
        "target": {
          "description": "Finished collection package ready for COLISEUM entry by the end of next week."
        }
      },
      "courses_of_action": [
        {
          "coa_id": "COA-1",
          "approach": "Minimal manual assessment approach",
          "task_dag": {
            "nodes": [
              {
                "id": "1",
                "name": "Manual Assessment",
                "description": "Manual assessment of target scope"
              },
              "\u2026(+1 more, len=2)"
            ],
            "edges": [
              {
                "from": "1",
                "to": "2"
              }
            ]
          },
          "risk_assessment": {
            "score": "LOW",
            "confidence_min": "LOW",
            "confidence_target": "MEDIUM",
            "primary_factor": "execution_uncertainty"
          },
          "off_nominal_triggers": [
            "target.scope_violations > 0",
            "execution.rate > 100",
            "detection.signature_count > 0",
            "execution.unauthorized_attempts > 0"
          ],
          "procedures": [
            "Step 1: Manual Assessment",
            "Step 2: Results Documentation"
          ]
        }
      ],
      "recommendation": {
        "primary_coa": "COA-1",
        "fallback_sequence": [],
        "rationale": "Single COA COA-1: Minimal manual assessment approach"
      },
      "trace": {
        "chain_hash": "f3402a2fed53ce94f7e2a680e05f85b77cd3113b5beaf286bb6b3cd2e2a8d435",
        "entry_count": 6,
        "entries": [
          {
            "role": "Intake",
            "decision_type": "intake_phase",
            "timestamp": "2026-06-08T22:36:16.847Z",
            "parent_hashes": [],
            "search": {
              "query": "Intake phase execution for mission TASK-MAIN-INT-010",
              "source": "pipeline_state",
              "k": 12,
              "total_results": 12
            },
            "results": [
              {
                "id": "mission_id",
                "score": 1.0,
                "summary": "mission_id=TASK-MAIN-INT-010"
              },
              "\u2026(+4 more, len=5)"
            ],
            "selected": "Intake",
            "selection_criteria": "role completed without errors",
            "confidence": "HIGH",
            "selection": {
              "selected": "Intake",
              "criteria": "role completed without errors",
              "confidence": "HIGH",
              "rationale": "Intake complete: mission_id=TASK-MAIN-INT-010"
            },
            "rationale": "Intake complete: mission_id=TASK-MAIN-INT-010",
            "mission_id": "TASK-MAIN-INT-010",
            "risk": {},
            "search_trace_version": "1.0",
            "metadata": {
              "role_status": "success"
            },
            "hash": "79aaecf8af45332f42974cf8dc032367f0f00f7682678406bfc91dc1f24d8ef4"
          },
          "\u2026(+5 more, len=6)"
        ]
      },
      "registry_reference": {
        "similar_mandates": [],
        "match_type": "NOVEL",
        "similarity_description": "Success registry not configured."
      },
      "metadata": {
        "nist_rmf": {
          "framework": "NIST AI RMF 1.0",
          "generated_at": "2026-06-08T22:37:49.421Z",
          "MAP": {
            "1.1": {
              "status": "PARTIAL",
              "evidence": [
                "mission_intent_present=True",
                "scope_items=0"
              ],
              "notes": "Mission context and scope establishment."
            },
            "1.5": {
              "status": "PARTIAL",
              "evidence": [
                "risk_tolerance_present=False"
              ],
              "notes": "Risk context captured from anchor risk_tolerance."
            },
            "1.6": {
              "status": "PARTIAL",
              "evidence": [
                "constraint_count=0"
              ],
              "notes": "Constraints are captured as portable predicate strings."
            },
            "2.1": {
              "status": "SATISFIED",
              "evidence": [
                "coa_count=1",
                "task_nodes=2"
              ],
              "notes": "Task decomposition coverage."
            },
            "2.2": {
              "status": "PARTIAL",
              "evidence": [
                "alternative_coas=1"
              ],
              "notes": "Alternative COA exploration."
            },
            "3.2": {
              "status": "SATISFIED",
              "evidence": [
                "risk_assessment_coverage=1.0"
              ],
              "notes": "Risk-aware planning across generated COAs."
            },
            "5.1": {
              "status": "SATISFIED",
              "evidence": [
                "anchor_hash_present=True",
                "trace_entries=6"
              ],
              "notes": "Traceability and provenance linkage."
            }
          },
          "MEASURE": {
            "1.1": {
              "status": "SATISFIED",
              "evidence": [
                "minimum_satisfaction_score=1.0"
              ],
              "notes": "Minimum satisfaction measurement."
            },
            "2.3": {
              "status": "SATISFIED",
              "evidence": [
                "constraint_compliance_score=1.0"
              ],
              "notes": "Constraint compliance measurement."
            },
            "2.8": {
              "status": "SATISFIED",
              "evidence": [
                "risk_aggregation_score=1.0"
              ],
              "notes": "Risk aggregation and calibration checks."
            },
            "3.1": {
              "status": "SATISFIED",
              "evidence": [
                "off_nominal_trigger_count=4"
              ],
              "notes": "Operational monitoring readiness signals."
            }
          },
          "GOVERN": {
            "1.1": {
              "status": "PARTIAL",
              "evidence": [
                "constraint_policies_defined=False",
                "strict_mode=False"
              ],
              "notes": "Constraint grammar defines enforceable governance policies."
            },
            "1.2": {
              "status": "SATISFIED",
              "evidence": [
                "orchestrator_role=deterministic_1plus6",
                "agent_roles=intake,interpreter,decomposition,procedure,binding,validation"
              ],
              "notes": "Accountability is structurally enforced by the 1+6 architecture: one deterministic orchestrator routes all work through \u2026\u27e8trunc\u27e9"
            },
            "1.5": {
              "status": "NOT_SATISFIED",
              "evidence": [
                "risk_tolerance_integrated=False"
              ],
              "notes": "Risk tolerance from anchor feeds governance decisions."
            },
            "2.1": {
              "status": "PARTIAL",
              "evidence": [
                "training_data_validated=true",
                "adapter_manifest_required=true"
              ],
              "notes": "Training data pipeline includes quality validation and scaling checks. Model fine-tuning uses LoRA adapters with manifes\u2026\u27e8trunc\u27e9"
            },
            "3.2": {
              "status": "PARTIAL",
              "evidence": [
                "alternative_coas_explored=1"
              ],
              "notes": "COA diversity provides multiple approaches; human review recommended."
            },
            "4.1": {
              "status": "SATISFIED",
              "evidence": [
                "cryptographic_integrity=True"
              ],
              "notes": "Signed artifacts and hash-linked traces demonstrate commitment to verifiable AI."
            },
            "6.1": {
              "status": "PARTIAL",
              "evidence": [
                "strict_mode_enabled=False",
                "deployment_gate=lattice_execution_gate"
              ],
              "notes": "Deployment gated by LATTICE execution gate with signed audit trail."
            }
          },
          "MANAGE": {
            "1.1": {
              "status": "SATISFIED",
              "evidence": [
                "evidence_chain_entries=6",
                "hash_linked_provenance=True"
              ],
              "notes": "Risk management process is integrated through hash-linked evidence chains."
            },
            "2.1": {
              "status": "SATISFIED",
              "evidence": [
                "off_nominal_trigger_count=4"
              ],
              "notes": "Off-nominal triggers provide runtime monitoring predicates for deployed mandates."
            },
            "2.4": {
              "status": "PARTIAL",
              "evidence": [
                "gap_analysis_supported=true",
                "human_review_gate=lattice_hitl_threshold"
              ],
              "notes": "Gap analysis reports enable structured feedback; LATTICE HITL threshold gates low-confidence decisions for human review."
            },
            "3.1": {
              "status": "SATISFIED",
              "evidence": [
                "tripwire_triggers=4",
                "containment_fsm=lattice_containment",
                "safe_state=HALT"
              ],
              "notes": "Incident response via tripwire predicates, containment FSM, and HALT safe state."
            },
            "4.1": {
              "status": "SATISFIED",
              "evidence": [
                "validation_passed=True"
              ],
              "notes": "Validation role provides automated review; success registry tracks improvements."
            },
            "4.2": {
              "status": "PARTIAL",
              "evidence": [
                "audit_chain_preserved=true"
              ],
              "notes": "Signed audit chains are preserved for post-deployment review. Formal decommissioning procedures to be documented."
            }
          }
        },
        "sources_consulted": [
          "mission_input",
          "anchor",
          "courses_of_action",
          "constraints",
          "validation_algorithm",
          "trace_chain",
          "local_pipeline_state"
        ],
        "input_hash": "6129dc0fdcb8517ab409e76be4b2e3a6bd76623f549cf2eebbf91c5fe535b6f7",
        "output_hash": "b78221560c875d5128c62d118128430072d874d423e94e03a44f2868d4ef9807",
        "validation_focus": [
          "ANCHOR INTEGRITY",
          "DAG COMPLETENESS",
          "RESOURCE FEASIBILITY",
          "RISK COHERENCE"
        ]
      }
    },
    "gap_reports": [],
    "has_gaps": false
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": true,
  "fallback_roles": [
    "Binding"
  ],
  "llm_roles_used": [
    "Intake",
    "Interpreter",
    "Decomposition",
    "Procedure",
    "Binding",
    "Validation"
  ]
}
```

### cond_a

*Source: `07_system_outputs/cond_a/cond_a__TASK-MAIN-SEC-014__r02.json`*

```json
{
  "run_id": "cond_a__TASK-MAIN-SEC-014__r02",
  "task_id": "TASK-MAIN-SEC-014",
  "system_id": "cond_a",
  "system_label": "MANDATE v1.0.0rc1, structured-input, deterministic",
  "run_number": 2,
  "seed": 20260625,
  "started_at": "2026-06-23T18:09:44Z",
  "wall_clock_ms": 26926.0812,
  "role_timings": [
    {
      "role_name": "PreExtractor",
      "status": "success",
      "duration_ms": 26915.4811,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    },
    "\u2026(+6 more, len=7)"
  ],
  "api_cost_usd": 0.025482,
  "local_compute_ms": 26926.0812,
  "model_versions": {
    "mlt": "mlt-stack-1.0.0rc1",
    "extraction_model": "claude-sonnet-4-6",
    "total_input_tokens": 994,
    "total_output_tokens": 1500
  },
  "decoding_params": {
    "condition": "cond_a",
    "pipeline_strict": false,
    "emit_gaps": true
  },
  "code_ref": "mlt-stack-1.0.0rc1",
  "harness_version": "0.1.0",
  "output_type": "MANDATE_AS_CODE",
  "output": {
    "artifact": {
      "mandate_id": "CM-SPEC-NIST-137",
      "version": "1.0",
      "generated": "2026-06-23T18:10:11.670Z",
      "anchor": {
        "mission_intent": "Develop a fully specified continuous monitoring program for the enterprise environment aligned with NIST SP 800-137, est\u2026\u27e8trunc\u27e9",
        "minimum": {
          "description": "The specification must define at minimum three monitoring tiers corresponding to high, moderate, and low system impact l\u2026\u27e8trunc\u27e9"
        },
        "constraints": [
          "REQUIRES nist_sp_800_137_alignment",
          "REQUIRES ciso_approval",
          "REQUIRES scap_validated_tooling_for_volatile_controls",
          "REQUIRES business_impact_analysis_integration",
          "REQUIRES role_assignment_for_all_monitoring_activities",
          "REQUIRES tiered_monitoring_by_system_impact_level",
          "FORBIDS production_modification",
          "target.completion_deadline <= '2025-end_of_next_month'"
        ],
        "anchor_hash": "5fbbeeab9c30393ec5e4f037b6649d831bb7d8b5b373a4be99b71738eb366bcd",
        "target": {
          "description": "Beyond the minimum, the specification should provide a fully integrated continuous monitoring framework that maps every \u2026\u27e8trunc\u27e9"
        },
        "risk_tolerance": {
          "max_autonomous_score": "LOW",
          "escalate_above": "MEDIUM"
        }
      },
      "courses_of_action": [
        {
          "coa_id": "COA-1",
          "approach": "Conservative reconnaissance and scanning without exploitation",
          "task_dag": {
            "nodes": [
              {
                "id": "1",
                "name": "Service Enumeration",
                "description": "Enumerate services on Enterprise environment security controls across all system impact levels (high, moderate, low), Hi\u2026\u27e8trunc\u27e9"
              },
              "\u2026(+2 more, len=3)"
            ],
            "edges": [
              {
                "from": "1",
                "to": "2"
              },
              "\u2026(+2 more, len=3)"
            ]
          },
          "risk_assessment": {
            "score": "MEDIUM",
            "confidence_min": "MEDIUM",
            "confidence_target": "HIGH",
            "primary_factor": "execution_uncertainty"
          },
          "off_nominal_triggers": [
            "target.scope_violations > 0",
            "execution.rate > 100"
          ],
          "procedures": [
            "Step 1: Service Enumeration using bia_repository",
            "Step 2: Vulnerability Scanning using scap_scanner, vulnerability_scanner",
            "Step 3: Results Analysis"
          ],
          "capabilities": [
            "port_scanning",
            "vulnerability_scanning"
          ]
        },
        "\u2026(+1 more, len=2)"
      ],
      "recommendation": {
        "primary_coa": "COA-3",
        "fallback_sequence": [
          "COA-1"
        ],
        "rationale": "Primary COA COA-3 balances mission objectives with operational risk (HIGH risk). Fallback sequence prioritizes lower-ris\u2026\u27e8trunc\u27e9"
      },
      "trace": {
        "chain_hash": "4eb5b248c4241f0c8a2f0df0823869461feb5b8e3de4f31ff932573134242314",
        "entry_count": 6,
        "entries": [
          {
            "role": "Intake",
            "decision_type": "intake_phase",
            "timestamp": "2026-06-23T18:10:11.670Z",
            "parent_hashes": [],
            "search": {
              "query": "Intake phase execution for mission CM-SPEC-NIST-137",
              "source": "pipeline_state",
              "k": 5,
              "total_results": 5
            },
            "results": [
              {
                "id": "mission_id",
                "score": 1.0,
                "summary": "mission_id=CM-SPEC-NIST-137"
              },
              "\u2026(+4 more, len=5)"
            ],
            "selected": "Intake",
            "selection_criteria": "role completed without errors",
            "confidence": "HIGH",
            "selection": {
              "selected": "Intake",
              "criteria": "role completed without errors",
              "confidence": "HIGH",
              "rationale": "Intake complete: mission_id=CM-SPEC-NIST-137"
            },
            "rationale": "Intake complete: mission_id=CM-SPEC-NIST-137",
            "mission_id": "CM-SPEC-NIST-137",
            "risk": {},
            "search_trace_version": "1.0",
            "metadata": {
              "role_status": "success"
            },
            "hash": "a98a737ffd8c77f5a61d48b441aff707f18d8fb095bd7938f721e53d253ba693"
          },
          "\u2026(+5 more, len=6)"
        ]
      },
      "registry_reference": {
        "similar_mandates": [],
        "match_type": "NOVEL",
        "similarity_description": "Success registry not configured."
      },
      "metadata": {
        "nist_rmf": {
          "framework": "NIST AI RMF 1.0",
          "generated_at": "2026-06-23T18:10:11.673Z",
          "MAP": {
            "1.1": {
              "status": "SATISFIED",
              "evidence": [
                "mission_intent_present=True",
                "scope_items=9"
              ],
              "notes": "Mission context and scope establishment."
            },
            "1.5": {
              "status": "SATISFIED",
              "evidence": [
                "risk_tolerance_present=True"
              ],
              "notes": "Risk context captured from anchor risk_tolerance."
            },
            "1.6": {
              "status": "SATISFIED",
              "evidence": [
                "constraint_count=8"
              ],
              "notes": "Constraints are captured as portable predicate strings."
            },
            "2.1": {
              "status": "SATISFIED",
              "evidence": [
                "coa_count=2",
                "task_nodes=7"
              ],
              "notes": "Task decomposition coverage."
            },
            "2.2": {
              "status": "SATISFIED",
              "evidence": [
                "alternative_coas=2"
              ],
              "notes": "Alternative COA exploration."
            },
            "3.2": {
              "status": "SATISFIED",
              "evidence": [
                "risk_assessment_coverage=1.0"
              ],
              "notes": "Risk-aware planning across generated COAs."
            },
            "5.1": {
              "status": "SATISFIED",
              "evidence": [
                "anchor_hash_present=True",
                "trace_entries=6"
              ],
              "notes": "Traceability and provenance linkage."
            }
          },
          "MEASURE": {
            "1.1": {
              "status": "SATISFIED",
              "evidence": [
                "minimum_satisfaction_score=1.0"
              ],
              "notes": "Minimum satisfaction measurement."
            },
            "2.3": {
              "status": "NOT_SATISFIED",
              "evidence": [
                "constraint_compliance_score=0.25"
              ],
              "notes": "Constraint compliance measurement."
            },
            "2.8": {
              "status": "SATISFIED",
              "evidence": [
                "risk_aggregation_score=1.0"
              ],
              "notes": "Risk aggregation and calibration checks."
            },
            "3.1": {
              "status": "SATISFIED",
              "evidence": [
                "off_nominal_trigger_count=4"
              ],
              "notes": "Operational monitoring readiness signals."
            }
          },
          "GOVERN": {
            "1.1": {
              "status": "PARTIAL",
              "evidence": [
                "constraint_policies_defined=True",
                "strict_mode=False"
              ],
              "notes": "Constraint grammar defines enforceable governance policies."
            },
            "1.2": {
              "status": "SATISFIED",
              "evidence": [
                "orchestrator_role=deterministic_1plus6",
                "agent_roles=intake,interpreter,decomposition,procedure,binding,validation"
              ],
              "notes": "Accountability is structurally enforced by the 1+6 architecture: one deterministic orchestrator routes all work through \u2026\u27e8trunc\u27e9"
            },
            "1.5": {
              "status": "SATISFIED",
              "evidence": [
                "risk_tolerance_integrated=True"
              ],
              "notes": "Risk tolerance from anchor feeds governance decisions."
            },
            "2.1": {
              "status": "PARTIAL",
              "evidence": [
                "training_data_validated=true",
                "adapter_manifest_required=true"
              ],
              "notes": "Training data pipeline includes quality validation and scaling checks. Model fine-tuning uses LoRA adapters with manifes\u2026\u27e8trunc\u27e9"
            },
            "3.2": {
              "status": "PARTIAL",
              "evidence": [
                "alternative_coas_explored=2"
              ],
              "notes": "COA diversity provides multiple approaches; human review recommended."
            },
            "4.1": {
              "status": "SATISFIED",
              "evidence": [
                "cryptographic_integrity=True"
              ],
              "notes": "Signed artifacts and hash-linked traces demonstrate commitment to verifiable AI."
            },
            "6.1": {
              "status": "PARTIAL",
              "evidence": [
                "strict_mode_enabled=False",
                "deployment_gate=lattice_execution_gate"
              ],
              "notes": "Deployment gated by LATTICE execution gate with signed audit trail."
            }
          },
          "MANAGE": {
            "1.1": {
              "status": "SATISFIED",
              "evidence": [
                "evidence_chain_entries=6",
                "hash_linked_provenance=True"
              ],
              "notes": "Risk management process is integrated through hash-linked evidence chains."
            },
            "2.1": {
              "status": "SATISFIED",
              "evidence": [
                "off_nominal_trigger_count=4"
              ],
              "notes": "Off-nominal triggers provide runtime monitoring predicates for deployed mandates."
            },
            "2.4": {
              "status": "PARTIAL",
              "evidence": [
                "gap_analysis_supported=true",
                "human_review_gate=lattice_hitl_threshold"
              ],
              "notes": "Gap analysis reports enable structured feedback; LATTICE HITL threshold gates low-confidence decisions for human review."
            },
            "3.1": {
              "status": "SATISFIED",
              "evidence": [
                "tripwire_triggers=4",
                "containment_fsm=lattice_containment",
                "safe_state=HALT"
              ],
              "notes": "Incident response via tripwire predicates, containment FSM, and HALT safe state."
            },
            "4.1": {
              "status": "PARTIAL",
              "evidence": [
                "validation_passed=False"
              ],
              "notes": "Validation role provides automated review; success registry tracks improvements."
            },
            "4.2": {
              "status": "PARTIAL",
              "evidence": [
                "audit_chain_preserved=true"
              ],
              "notes": "Signed audit chains are preserved for post-deployment review. Formal decommissioning procedures to be documented."
            }
          }
        },
        "sources_consulted": [
          "mission_input",
          "anchor",
          "courses_of_action",
          "constraints",
          "validation_algorithm",
          "trace_chain",
          "local_pipeline_state"
        ],
        "input_hash": "120be0c2bdb8f6e26e4d573613561a20a6f13928c9e14ccafcd65eb7caf0bc29",
        "output_hash": "d2645ec4b2731a26c5ed149deef07988a0f89bb94ae40d31c1435ec6aba28fb9"
      }
    },
    "gap_reports": [
      {
        "gap_id": "GAP-CM-SPEC-NIST-137-001",
        "gap_type": "UNKNOWN_PATTERN",
        "severity": "BLOCKING",
        "gap_source": "SPECIFICATION_GAP",
        "detected_by": "Validation",
        "pipeline_stage": 6,
        "location": {
          "category": "task_dag",
          "input_reference": "validation.constraint_compliance",
          "field_or_task": "courses_of_action[COA-1]"
        },
        "evidence": {
          "trace_entry_hashes": [
            "4df8f35e95f89e8fde259b6468cb9de551aab26087b35e838f2257640f1045f1"
          ]
        },
        "reason": "Constraint compliance failed: REQUIRES nist_sp_800_137_alignment: missing required capability 'nist_sp_800_137_alignment\u2026\u27e8trunc\u27e9",
        "remediation": {
          "action_required": "Modify task steps to satisfy all anchor constraints.",
          "responsible_party": "Mission Author",
          "complexity": "MEDIUM"
        },
        "readiness_score": {
          "completion_percentage": 40,
          "blocking": true,
          "partial_spec_available": true
        },
        "readiness_assessment": {
          "completeness_score": 0.4,
          "readiness_percentage": 40,
          "blocking_gap_count": 2,
          "recommendation": "INSUFFICIENT_FOR_AUTOMATION"
        },
        "trace_to_gap": "4df8f35e95f89e8fde259b6468cb9de551aab26087b35e838f2257640f1045f1"
      },
      "\u2026(+1 more, len=2)"
    ],
    "has_gaps": true,
    "mission_input_metadata": {
      "source_task_id": "TASK-MAIN-SEC-014",
      "extraction_model": "claude-sonnet-4-6",
      "extraction_cost_usd": 0.025482,
      "input_tokens": 994,
      "output_tokens": 1500,
      "raw_extraction_json": "{\"mission_id\": \"CM-SPEC-NIST-137\", \"intent\": \"Develop a fully specified continuous monitoring program for the enterprise\u2026\u27e8trunc\u27e9",
      "extraction_failed_constraints": [],
      "constraints_extracted": 8,
      "constraints_failed_grammar": 0
    }
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": false,
  "fallback_roles": [],
  "llm_roles_used": [
    "PreExtractor"
  ]
}
```

### cond_b

*Source: `07_system_outputs/cond_b/cond_b__TASK-MAIN-INT-031__r08.json`*

```json
{
  "run_id": "cond_b__TASK-MAIN-INT-031__r08",
  "task_id": "TASK-MAIN-INT-031",
  "system_id": "cond_b",
  "system_label": "MANDATE v1.0.0rc1, LLM-augmented Interpreter, end-to-end",
  "run_number": 8,
  "seed": 20260631,
  "started_at": "2026-06-23T23:30:03Z",
  "wall_clock_ms": 113871.5589,
  "role_timings": [
    {
      "role_name": "Intake",
      "status": "success",
      "duration_ms": 12271.818,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    },
    "\u2026(+5 more, len=6)"
  ],
  "api_cost_usd": null,
  "local_compute_ms": 113871.5589,
  "model_versions": {
    "mlt": "mlt-stack-1.0.0rc1",
    "llm_model": "claude-sonnet-4-6"
  },
  "decoding_params": {
    "condition": "cond_b",
    "pipeline_strict": false,
    "emit_gaps": true,
    "llm_fallback_enabled": true,
    "llm_backend": "anthropic",
    "llm_max_tokens": 4096,
    "llm_temperature": 0.0,
    "domain_profile_mode": "auto",
    "domain_profile_name": "defense_intel"
  },
  "code_ref": "mlt-stack-1.0.0rc1",
  "harness_version": "0.1.0",
  "output_type": "MANDATE_AS_CODE",
  "output": {
    "artifact": {
      "mandate_id": "INTAKE-PIAB-ASSESS-001",
      "version": "1.0",
      "generated": "2026-06-23T23:30:15.806Z",
      "anchor": {
        "mission_intent": "Produce a comprehensive assessment of how effectively the President's Intelligence Advisory Board is fulfilling its mand\u2026\u27e8trunc\u27e9",
        "minimum": {
          "description": "A finished assessment document that (1) covers all sixteen current PIAB members without omission, including at least a b\u2026\u27e8trunc\u27e9"
        },
        "constraints": [
          "REQUIRES nsc_staff_review_before_delivery",
          "REQUIRES feedback_from_all_sixteen_piab_members",
          "REQUIRES iob_composition_sufficiency_analysis",
          "REQUIRES individual_member_contribution_coverage",
          "REQUIRES iob_compliance_oversight_review",
          "REQUIRES omb_coordination_role_evaluation",
          "REQUIRES decade_scoped_advisory_citizen_inclusion",
          "scope.delivery_deadline == 'close_of_business_friday'",
          "\u2026(+3 more, len=11)"
        ],
        "anchor_hash": "39f654430d425b7d9203cdc2b9c3b85061d11b7db80e10e75b4178ef49bee5f1",
        "target": {
          "description": "A comprehensive, analytically rigorous assessment that (1) evaluates the full effectiveness of the PIAB in fulfilling it\u2026\u27e8trunc\u27e9"
        },
        "risk_tolerance": {
          "max_autonomous_score": "LOW",
          "escalate_above": "MEDIUM"
        }
      },
      "courses_of_action": [
        {
          "coa_id": "COA-1",
          "approach": "Conservative defense/intelligence operations approach",
          "task_dag": {
            "nodes": [
              {
                "id": "1",
                "name": "Collection Planning",
                "description": "Develop collection requirements for Assessment of PIAB mandate fulfillment regarding independent counsel on IC performan\u2026\u27e8trunc\u27e9"
              },
              "\u2026(+2 more, len=3)"
            ],
            "edges": [
              {
                "from": "1",
                "to": "2"
              },
              "\u2026(+1 more, len=2)"
            ]
          },
          "risk_assessment": {
            "score": "LOW",
            "confidence_min": "LOW",
            "confidence_target": "MEDIUM",
            "primary_factor": "execution_uncertainty"
          },
          "off_nominal_triggers": [
            "target.scope_violations > 0",
            "execution.rate > 100"
          ],
          "procedures": [
            "Step 1: Collection Planning",
            "Step 2: Single-Source Collection",
            "Step 3: Processing"
          ]
        },
        "\u2026(+2 more, len=3)"
      ],
      "recommendation": {
        "primary_coa": "COA-2",
        "fallback_sequence": [
          "COA-1",
          "COA-3"
        ],
        "rationale": "COA-2 selected via Search-Select-Trace: Search across COA-1 (3 tasks, single-source, no analysis/dissemination nodes), C\u2026\u27e8trunc\u27e9"
      },
      "trace": {
        "chain_hash": "1e2682808f6d646f386abae0a57ad1f02e6a4f97010e75e92093af6747da46c3",
        "entry_count": 6,
        "entries": [
          {
            "role": "Intake",
            "decision_type": "intake_phase",
            "timestamp": "2026-06-23T23:30:15.806Z",
            "parent_hashes": [],
            "search": {
              "query": "Intake phase execution for mission INTAKE-PIAB-ASSESS-001",
              "source": "pipeline_state",
              "k": 12,
              "total_results": 12
            },
            "results": [
              {
                "id": "mission_id",
                "score": 1.0,
                "summary": "mission_id=INTAKE-PIAB-ASSESS-001"
              },
              "\u2026(+4 more, len=5)"
            ],
            "selected": "Intake",
            "selection_criteria": "role completed without errors",
            "confidence": "HIGH",
            "selection": {
              "selected": "Intake",
              "criteria": "role completed without errors",
              "confidence": "HIGH",
              "rationale": "Intake complete: mission_id=INTAKE-PIAB-ASSESS-001"
            },
            "rationale": "Intake complete: mission_id=INTAKE-PIAB-ASSESS-001",
            "mission_id": "INTAKE-PIAB-ASSESS-001",
            "risk": {},
            "search_trace_version": "1.0",
            "metadata": {
              "role_status": "success"
            },
            "hash": "db2c03a0762a18aa10fc2aea7db8262f034277254e2957799ff5f9335f1c7f8b"
          },
          "\u2026(+5 more, len=6)"
        ]
      },
      "registry_reference": {
        "similar_mandates": [],
        "match_type": "NOVEL",
        "similarity_description": "Success registry not configured."
      },
      "metadata": {
        "nist_rmf": {
          "framework": "NIST AI RMF 1.0",
          "generated_at": "2026-06-23T23:31:57.395Z",
          "MAP": {
            "1.1": {
              "status": "SATISFIED",
              "evidence": [
                "mission_intent_present=True",
                "scope_items=9"
              ],
              "notes": "Mission context and scope establishment."
            },
            "1.5": {
              "status": "SATISFIED",
              "evidence": [
                "risk_tolerance_present=True"
              ],
              "notes": "Risk context captured from anchor risk_tolerance."
            },
            "1.6": {
              "status": "SATISFIED",
              "evidence": [
                "constraint_count=11"
              ],
              "notes": "Constraints are captured as portable predicate strings."
            },
            "2.1": {
              "status": "SATISFIED",
              "evidence": [
                "coa_count=3",
                "task_nodes=12"
              ],
              "notes": "Task decomposition coverage."
            },
            "2.2": {
              "status": "SATISFIED",
              "evidence": [
                "alternative_coas=3"
              ],
              "notes": "Alternative COA exploration."
            },
            "3.2": {
              "status": "SATISFIED",
              "evidence": [
                "risk_assessment_coverage=1.0"
              ],
              "notes": "Risk-aware planning across generated COAs."
            },
            "5.1": {
              "status": "SATISFIED",
              "evidence": [
                "anchor_hash_present=True",
                "trace_entries=6"
              ],
              "notes": "Traceability and provenance linkage."
            }
          },
          "MEASURE": {
            "1.1": {
              "status": "SATISFIED",
              "evidence": [
                "minimum_satisfaction_score=1.0"
              ],
              "notes": "Minimum satisfaction measurement."
            },
            "2.3": {
              "status": "NOT_SATISFIED",
              "evidence": [
                "constraint_compliance_score=0.364"
              ],
              "notes": "Constraint compliance measurement."
            },
            "2.8": {
              "status": "SATISFIED",
              "evidence": [
                "risk_aggregation_score=1.0"
              ],
              "notes": "Risk aggregation and calibration checks."
            },
            "3.1": {
              "status": "SATISFIED",
              "evidence": [
                "off_nominal_trigger_count=6"
              ],
              "notes": "Operational monitoring readiness signals."
            }
          },
          "GOVERN": {
            "1.1": {
              "status": "PARTIAL",
              "evidence": [
                "constraint_policies_defined=True",
                "strict_mode=False"
              ],
              "notes": "Constraint grammar defines enforceable governance policies."
            },
            "1.2": {
              "status": "SATISFIED",
              "evidence": [
                "orchestrator_role=deterministic_1plus6",
                "agent_roles=intake,interpreter,decomposition,procedure,binding,validation"
              ],
              "notes": "Accountability is structurally enforced by the 1+6 architecture: one deterministic orchestrator routes all work through \u2026\u27e8trunc\u27e9"
            },
            "1.5": {
              "status": "SATISFIED",
              "evidence": [
                "risk_tolerance_integrated=True"
              ],
              "notes": "Risk tolerance from anchor feeds governance decisions."
            },
            "2.1": {
              "status": "PARTIAL",
              "evidence": [
                "training_data_validated=true",
                "adapter_manifest_required=true"
              ],
              "notes": "Training data pipeline includes quality validation and scaling checks. Model fine-tuning uses LoRA adapters with manifes\u2026\u27e8trunc\u27e9"
            },
            "3.2": {
              "status": "PARTIAL",
              "evidence": [
                "alternative_coas_explored=3"
              ],
              "notes": "COA diversity provides multiple approaches; human review recommended."
            },
            "4.1": {
              "status": "SATISFIED",
              "evidence": [
                "cryptographic_integrity=True"
              ],
              "notes": "Signed artifacts and hash-linked traces demonstrate commitment to verifiable AI."
            },
            "6.1": {
              "status": "PARTIAL",
              "evidence": [
                "strict_mode_enabled=False",
                "deployment_gate=lattice_execution_gate"
              ],
              "notes": "Deployment gated by LATTICE execution gate with signed audit trail."
            }
          },
          "MANAGE": {
            "1.1": {
              "status": "SATISFIED",
              "evidence": [
                "evidence_chain_entries=6",
                "hash_linked_provenance=True"
              ],
              "notes": "Risk management process is integrated through hash-linked evidence chains."
            },
            "2.1": {
              "status": "SATISFIED",
              "evidence": [
                "off_nominal_trigger_count=6"
              ],
              "notes": "Off-nominal triggers provide runtime monitoring predicates for deployed mandates."
            },
            "2.4": {
              "status": "PARTIAL",
              "evidence": [
                "gap_analysis_supported=true",
                "human_review_gate=lattice_hitl_threshold"
              ],
              "notes": "Gap analysis reports enable structured feedback; LATTICE HITL threshold gates low-confidence decisions for human review."
            },
            "3.1": {
              "status": "SATISFIED",
              "evidence": [
                "tripwire_triggers=6",
                "containment_fsm=lattice_containment",
                "safe_state=HALT"
              ],
              "notes": "Incident response via tripwire predicates, containment FSM, and HALT safe state."
            },
            "4.1": {
              "status": "PARTIAL",
              "evidence": [
                "validation_passed=False"
              ],
              "notes": "Validation role provides automated review; success registry tracks improvements."
            },
            "4.2": {
              "status": "PARTIAL",
              "evidence": [
                "audit_chain_preserved=true"
              ],
              "notes": "Signed audit chains are preserved for post-deployment review. Formal decommissioning procedures to be documented."
            }
          }
        },
        "sources_consulted": [
          "mission_input",
          "anchor",
          "courses_of_action",
          "constraints",
          "validation_algorithm",
          "trace_chain",
          "local_pipeline_state"
        ],
        "input_hash": "e7a1eff37ba6e883e7a827a96333dbd812c8032cd4e5e1530f5b33cc4e32a4bb",
        "output_hash": "ec78bb51aa0c65a9578304d66b31af3a51492dd34ad656ce8db47067a791f6f5",
        "validation_focus": [
          "Minimum satisfaction check: COA-1 fails \u2014 intelligence cycle incomplete, no Analysis or Dissemination nodes present",
          "Target feasibility check: COA-2 passes \u2014 full five-node cycle covers planning through dissemination with bounded risk",
          "Constraint compliance check: All 11 constraints reviewed; no explicit violations detected across COA-2 task chain",
          "Risk aggregation check: COA-3 exceeds acceptable risk threshold \u2014 four distinct high-severity risk factors across four nodes without mitigation tools assigned",
          "Anchor integrity check: No upstream anchor intent, minimums, targets, or constraints rewritten by downstream roles",
          "Gap status: One non-blocking gap (MISSING_CAPABILITY: available_tools) remains open; does not block mandate issuance but limits execution to manual methods",
          "Recommended COA: COA-2 (Moderate defense/intelligence operations approach) selected as mandate-compliant course of action"
        ]
      }
    },
    "gap_reports": [
      {
        "gap_id": "GAP-INTAKE-PIAB-ASSESS-001-001",
        "gap_type": "MISSING_CAPABILITY",
        "severity": "DEGRADING",
        "gap_source": "SPECIFICATION_GAP",
        "detected_by": "Decomposition",
        "pipeline_stage": 3,
        "location": {
          "category": "capability",
          "input_reference": "mission_input",
          "field_or_task": "available_tools"
        },
        "evidence": {
          "trace_entry_hashes": [
            "ea009634abf6954087eebc5463eb2b6b7f54b35b620574e64e808d902fca9d4c"
          ]
        },
        "reason": "No tools specified in mission input. COA generation limited to manual assessment approach.",
        "remediation": {
          "action_required": "Provide available_tools with tool_id, tool_class, and description for each available tool.",
          "responsible_party": "Mission Author",
          "complexity": "MEDIUM"
        },
        "readiness_score": {
          "completion_percentage": 10,
          "blocking": false,
          "partial_spec_available": false
        },
        "readiness_assessment": {
          "completeness_score": 0.325,
          "readiness_percentage": 32,
          "blocking_gap_count": 3,
          "recommendation": "INSUFFICIENT_FOR_AUTOMATION"
        },
        "trace_to_gap": "ea009634abf6954087eebc5463eb2b6b7f54b35b620574e64e808d902fca9d4c"
      },
      "\u2026(+3 more, len=4)"
    ],
    "has_gaps": true,
    "metadata": {
      "extraction_failed_constraints": 0
    },
    "extraction_failed_constraints": 0,
    "domain_profile_mode": "auto",
    "domain_profile_name": "defense_intel"
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": false,
  "fallback_roles": [],
  "llm_roles_used": [
    "Intake",
    "Interpreter",
    "Decomposition",
    "Procedure",
    "Binding",
    "Validation"
  ]
}
```

### baseline_1

*Source: `07_system_outputs/baseline_1/baseline_1__TASK-MAIN-SEC-016__r07.json`*

```json
{
  "run_id": "baseline_1__TASK-MAIN-SEC-016__r07",
  "task_id": "TASK-MAIN-SEC-016",
  "system_id": "baseline_1",
  "system_label": "B1 single-prompt planner (Claude)",
  "run_number": 7,
  "seed": 20260612,
  "started_at": "2026-06-13T20:44:19Z",
  "wall_clock_ms": 30967.416,
  "role_timings": [
    {
      "role_name": "generate",
      "status": "success",
      "duration_ms": 30967.397,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    }
  ],
  "api_cost_usd": 0.026805,
  "local_compute_ms": null,
  "model_versions": {
    "model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "total_input_tokens": 575,
    "total_output_tokens": 1672
  },
  "decoding_params": {
    "temperature": 0.0
  },
  "code_ref": "",
  "harness_version": "0.1.0",
  "output_type": "BASELINE_SCHEMA:specification",
  "output": {
    "specification": {
      "mission_intent": "Establish a SOC-led external monitoring capability to detect unauthorized replication or impersonation of organizational\u2026\u27e8trunc\u27e9",
      "minimum": [
        {
          "dimension": "Regulatory alignment",
          "threshold": "NIST 800-53 Rev. 5",
          "rationale": "The request explicitly frames the capability as fulfilling NIST 800-53 Rev. 5 obligations; compliance with this framewor\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+6 more, len=7)"
      ],
      "target": [
        {
          "dimension": "Detection latency",
          "objective": null,
          "rationale": "Faster detection of unauthorized replication reduces organizational risk, but no specific detection time window was stat\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+4 more, len=5)"
      ],
      "constraints": [
        {
          "predicate": "capability_scope includes_only external websites AND social media channels",
          "rationale": "The request scopes discovery processes specifically to external websites and social media; internal monitoring is not me\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+4 more, len=5)"
      ],
      "suspected_gaps": [
        {
          "field": "Scanning cadence definition",
          "reason": "The request uses 'periodic' without specifying frequency (e.g., daily, weekly). Without a defined cadence, SLA complianc\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+7 more, len=8)"
      ]
    },
    "raw_text": "{\n  \"mission_intent\": \"Establish a SOC-led external monitoring capability to detect unauthorized replication or imperson\u2026\u27e8trunc\u27e9",
    "schema_valid": true,
    "schema_errors": []
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": false,
  "fallback_roles": [],
  "llm_roles_used": [
    "generate"
  ]
}
```

### baseline_2

*Source: `07_system_outputs/baseline_2/baseline_2__TASK-MAIN-INT-040__r09.json`*

```json
{
  "run_id": "baseline_2__TASK-MAIN-INT-040__r09",
  "task_id": "TASK-MAIN-INT-040",
  "system_id": "baseline_2",
  "system_label": "B2 single-prompt planner (GPT)",
  "run_number": 9,
  "seed": 20260614,
  "started_at": "2026-06-13T11:23:06Z",
  "wall_clock_ms": 3678.519,
  "role_timings": [
    {
      "role_name": "generate",
      "status": "success",
      "duration_ms": 3678.4918,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    }
  ],
  "api_cost_usd": 0.005755,
  "local_compute_ms": null,
  "model_versions": {
    "model": "gpt-4o",
    "provider": "openai",
    "total_input_tokens": 542,
    "total_output_tokens": 440
  },
  "decoding_params": {
    "temperature": 0.0
  },
  "code_ref": "",
  "harness_version": "0.1.0",
  "output_type": "BASELINE_SCHEMA:specification",
  "output": {
    "specification": {
      "mission_intent": "Establish a coordination mechanism to synchronize intelligence exchanges between CIA and DIA, ensuring no duplication of\u2026\u27e8trunc\u27e9",
      "minimum": [
        {
          "dimension": "Operational readiness",
          "threshold": "Fully operational within two weeks",
          "rationale": "The request specifies a two-week timeline for the mechanism to be fully operational."
        },
        "\u2026(+2 more, len=3)"
      ],
      "target": [
        {
          "dimension": "Private sector integration",
          "objective": "Incorporate a private sector partnership integration layer",
          "rationale": "This is a desired feature to enhance the mechanism with commercial threat data feeds."
        },
        "\u2026(+1 more, len=2)"
      ],
      "constraints": [
        {
          "predicate": "relationship_degradation == none",
          "rationale": "The request specifies no degradation to any existing bilateral relationship."
        },
        "\u2026(+1 more, len=2)"
      ],
      "suspected_gaps": [
        {
          "field": "threshold for private sector integration",
          "reason": "The request does not specify a required threshold for the integration of private sector partnerships."
        },
        "\u2026(+1 more, len=2)"
      ]
    },
    "raw_text": "{\n  \"mission_intent\": \"Establish a coordination mechanism to synchronize intelligence exchanges between CIA and DIA, ens\u2026\u27e8trunc\u27e9",
    "schema_valid": true,
    "schema_errors": []
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": false,
  "fallback_roles": [],
  "llm_roles_used": [
    "generate"
  ]
}
```

### baseline_3

*Source: `07_system_outputs/baseline_3/baseline_3__TASK-MAIN-SEC-020__r10.json`*

```json
{
  "run_id": "baseline_3__TASK-MAIN-SEC-020__r10",
  "task_id": "TASK-MAIN-SEC-020",
  "system_id": "baseline_3",
  "system_label": "B3 ReAct (Claude)",
  "run_number": 10,
  "seed": 20260615,
  "started_at": "2026-06-14T09:54:31Z",
  "wall_clock_ms": 55384.8426,
  "role_timings": [
    {
      "role_name": "react_step_1",
      "status": "success",
      "duration_ms": 1839.427,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    },
    "\u2026(+3 more, len=4)"
  ],
  "api_cost_usd": 0.051513,
  "local_compute_ms": null,
  "model_versions": {
    "model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "total_input_tokens": 4751,
    "total_output_tokens": 2484
  },
  "decoding_params": {
    "temperature": 0.0
  },
  "code_ref": "",
  "harness_version": "0.1.0",
  "output_type": "BASELINE_SCHEMA:specification",
  "output": {
    "specification": {
      "mission_intent": "Produce a written gap analysis report that evaluates the organization's existing single centralized log server architect\u2026\u27e8trunc\u27e9",
      "minimum": {
        "deliverable_type": "Written gap analysis report (PDF or Word) with executive summary",
        "mandatory_content_sections": [
          "Current-state description of single-server architecture and its consolidated roles",
          "Explicit mapping of current architecture against NIST SP 800-92 second-tier requirements with section citations",
          "Risk assessment of single-server approach with qualitative or semi-quantitative risk ratings",
          "Organizational suitability evaluation with a clear conclusion",
          "Redundancy capabilities assessment with identified gaps",
          "Failover arrangements analysis for log generators when primary server is unavailable",
          "Log data sharing and inter-server redundancy capability assessment",
          "Clear recommendation on single-server vs. multi-server topology with rationale",
          "\u2026(+2 more, len=10)"
        ],
        "every_gap_finding_must_cite_nist_sp_800_92_section": true,
        "recommendations_must_include": [
          "action",
          "gap or risk addressed",
          "priority rating (High/Medium/Low)"
        ],
        "executive_summary_required": true,
        "audience": "SOC leadership team",
        "deadline": "EOB Friday of next week",
        "current_state_must_be_validated_against_infrastructure_documentation_or_sme": true
      },
      "target": {
        "executive_summary_length": "1 page or less",
        "gap_findings_format": "Tabular: Gap Area | Current State | NIST Requirement | Risk Level | Recommendation",
        "nist_version": "NIST SP 800-92 current published version; note any relevant draft revision such as SP 800-92r1",
        "report_suitable_for_quarterly_infrastructure_review_package": true,
        "soc_leadership_acceptance_signoff": true
      },
      "constraints": {
        "scope_boundary": "Log management infrastructure only; excludes SIEM tuning, detection logic, and endpoint configuration unless directly re\u2026\u27e8trunc\u27e9",
        "implementation_out_of_scope": "Report informs decisions only; no architectural changes are to be executed as part of this deliverable",
        "procurement_cost_analysis_out_of_scope": "May be noted qualitatively but is not a required deliverable",
        "log_content_quality_and_detection_rules_out_of_scope": true
      },
      "suspected_gaps": [
        "Exact organizational size and operational footprint metrics not provided; suitability evaluation threshold for when single-server is appropriate vs. inappropriate cannot be set without this data",
        "Quarterly infrastructure review meeting date not specified beyond 'end of next week'; precise deadline should be confirmed",
        "No risk tolerance or risk acceptance thresholds defined by leadership; risk rating scale (e.g., High/Medium/Low criteria) must be established or assumed by the analyst",
        "No information provided on existing failover or buffering mechanisms at log generators; current-state accuracy depends on SME or documentation access not confirmed",
        "Whether SP 800-92r1 or a successor revision is the authoritative reference has not been confirmed; analyst must verify current published version",
        "Acceptance sign-off process and reviewer identity beyond 'SOC leadership' not specified",
        "No guidance given on whether cost or resource constraints should bound architectural recommendations, leaving recommendation scope undefined"
      ]
    },
    "raw_text": "{\n  \"mission_intent\": \"Produce a written gap analysis report that evaluates the organization's existing single centraliz\u2026\u27e8trunc\u27e9",
    "schema_valid": false,
    "schema_errors": [
      "constraints: {'scope_boundary': 'Log management infrastructure only; excludes SIEM tuning, detection logic, and endpoint configuration unless directly relevant to log transport or storage architecture', 'implementation_out_of_scope': 'Report informs decisions only; no architectural changes are to be executed as part of this deliverable', 'procurement_cost_analysis_out_of_scope': 'May be noted qualitatively but is not a required deliverable', 'log_content_quality_and_detection_rules_out_of_scope': True} is not of type 'array'",
      "minimum: {'deliverable_type': 'Written gap analysis report (PDF or Word) with executive summary', 'mandatory_content_sections': ['Current-state description of single-server architecture and its consolidated roles', 'Explicit mapping of current architecture against NIST SP 800-92 second-tier requirements with section citations', 'Risk assessment of single-server approach with qualitative or semi-quantitative risk ratings', 'Organizational suitability evaluation with a clear conclusion', 'Redundancy capabilities assessment with identified gaps', 'Failover arrangements analysis for log generators when primary server is unavailable', 'Log data sharing and inter-server redundancy capability assessment', 'Clear recommendation on single-server vs. multi-server topology with rationale', 'Prioritized architectural change recommendations with what, why, and priority level', 'Scalability concerns flagged explicitly'], 'every_gap_finding_must_cite_nist_sp_800_92_section': True, 'recommendations_must_include': ['action', 'gap or risk addressed', 'priority rating (High/Medium/Low)'], 'executive_summary_required': True, 'audience': 'SOC leadership team', 'deadline': 'EOB Friday of next week', 'current_state_must_be_validated_against_infrastructure_documentation_or_sme': True} is not of type 'array'",
      "suspected_gaps/0: 'Exact organizational size and operational footprint metrics not provided; suitability evaluation threshold for when single-server is appropriate vs. inappropriate cannot be set without this data' is not of type 'object'",
      "suspected_gaps/1: \"Quarterly infrastructure review meeting date not specified beyond 'end of next week'; precise deadline should be confirmed\" is not of type 'object'",
      "suspected_gaps/2: 'No risk tolerance or risk acceptance thresholds defined by leadership; risk rating scale (e.g., High/Medium/Low criteria) must be established or assumed by the analyst' is not of type 'object'",
      "suspected_gaps/3: 'No information provided on existing failover or buffering mechanisms at log generators; current-state accuracy depends on SME or documentation access not confirmed' is not of type 'object'",
      "suspected_gaps/4: 'Whether SP 800-92r1 or a successor revision is the authoritative reference has not been confirmed; analyst must verify current published version' is not of type 'object'",
      "suspected_gaps/5: \"Acceptance sign-off process and reviewer identity beyond 'SOC leadership' not specified\" is not of type 'object'",
      "\u2026(+2 more, len=10)"
    ]
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": false,
  "fallback_roles": [],
  "llm_roles_used": [
    "react_step_1",
    "react_step_2",
    "react_step_3",
    "finalize"
  ]
}
```

### baseline_4

*Source: `07_system_outputs/baseline_4/baseline_4__TASK-MAIN-FIN-036__r07.json`*

```json
{
  "run_id": "baseline_4__TASK-MAIN-FIN-036__r07",
  "task_id": "TASK-MAIN-FIN-036",
  "system_id": "baseline_4",
  "system_label": "B4 AutoGen (planner+reviewer)",
  "run_number": 7,
  "seed": 20260612,
  "started_at": "2026-06-13T17:45:14Z",
  "wall_clock_ms": 53373.322,
  "role_timings": [
    {
      "role_name": "planner",
      "status": "success",
      "duration_ms": 33745.718,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    },
    "\u2026(+1 more, len=2)"
  ],
  "api_cost_usd": 0.06516,
  "local_compute_ms": null,
  "model_versions": {
    "model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "total_input_tokens": 2905,
    "total_output_tokens": 3763
  },
  "decoding_params": {
    "temperature": 0.0
  },
  "code_ref": "",
  "harness_version": "0.1.0",
  "output_type": "BASELINE_SCHEMA:specification",
  "output": {
    "specification": {
      "mission_intent": "Evaluate all identified control deficiencies across financial reporting processes, classify each as a significant defici\u2026\u27e8trunc\u27e9",
      "minimum": [
        {
          "dimension": "Framework compliance",
          "threshold": "AS 2201 applied to every deficiency classification",
          "rationale": "The request explicitly mandates use of the AS 2201 framework as the governing standard for all classifications."
        },
        "\u2026(+5 more, len=6)"
      ],
      "target": [
        {
          "dimension": "Population completeness",
          "objective": "All Q3 control testing results incorporated before final classification",
          "rationale": "The complete population from the outsourced testing team is not available until Monday; incorporating it would be aspira\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+2 more, len=3)"
      ],
      "constraints": [
        {
          "predicate": "delivery_deadline <= end_of_day Friday",
          "rationale": "The request sets an explicit hard deadline of end of day Friday for the audit committee package."
        },
        "\u2026(+4 more, len=5)"
      ],
      "suspected_gaps": [
        {
          "field": "Population completeness at delivery",
          "reason": "The complete Q3 control testing results will not be available until Monday, yet the deliverable is due Friday. The reque\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+8 more, len=9)"
      ]
    },
    "raw_text": "```json\n{\n  \"mission_intent\": \"Evaluate all identified control deficiencies across financial reporting processes, classi\u2026\u27e8trunc\u27e9",
    "schema_valid": true,
    "schema_errors": []
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": false,
  "fallback_roles": [],
  "llm_roles_used": [
    "planner",
    "reviewer"
  ]
}
```

### baseline_5

*Source: `07_system_outputs/baseline_5/baseline_5__TASK-MAIN-FIN-036__r06.json`*

```json
{
  "run_id": "baseline_5__TASK-MAIN-FIN-036__r06",
  "task_id": "TASK-MAIN-FIN-036",
  "system_id": "baseline_5",
  "system_label": "B5 CrewAI (sequential crew)",
  "run_number": 6,
  "seed": 20260611,
  "started_at": "2026-06-14T03:55:45Z",
  "wall_clock_ms": 50078.1808,
  "role_timings": [
    {
      "role_name": "analyst",
      "status": "success",
      "duration_ms": 26216.2678,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    },
    "\u2026(+1 more, len=2)"
  ],
  "api_cost_usd": 0.042546,
  "local_compute_ms": null,
  "model_versions": {
    "model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "total_input_tokens": 2177,
    "total_output_tokens": 2401
  },
  "decoding_params": {
    "temperature": 0.0
  },
  "code_ref": "",
  "harness_version": "0.1.0",
  "output_type": "BASELINE_SCHEMA:specification",
  "output": {
    "specification": {
      "mission_intent": "Evaluate all identified control deficiencies in financial reporting processes, classify each as a significant deficiency\u2026\u27e8trunc\u27e9",
      "minimum": [
        {
          "dimension": "Population completeness",
          "threshold": "All deficiencies identified to date must be assessed; any deficiency excluded due to incomplete Q3 testing data must be \u2026\u27e8trunc\u27e9",
          "rationale": "Complete population of Q3 control testing results is not available until the following Monday; assessments based on a pa\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+5 more, len=6)"
      ],
      "target": [
        {
          "dimension": "Classification accuracy",
          "objective": "Each deficiency is classified at the correct severity level such that no material weakness is understated and no signifi\u2026\u27e8trunc\u27e9",
          "rationale": "The request asks for the 'best possible' classification, which in a professional audit context means accurate and defens\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+3 more, len=4)"
      ],
      "constraints": [
        {
          "predicate": "classification_basis excludes incomplete_Q3_testing_results_as_if_complete",
          "rationale": "Treating a partial population as complete without disclosure would misrepresent the scope of the assessment to the audit\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+5 more, len=6)"
      ],
      "suspected_gaps": [
        {
          "field": "Population completeness \u2014 definition of 'identified to date'",
          "reason": "The minimum threshold requires assessing 'all deficiencies identified to date' but does not define the precise cutoff: w\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+9 more, len=10)"
      ]
    },
    "raw_text": "{\n  \"mission_intent\": \"Evaluate all identified control deficiencies in financial reporting processes, classify each as a\u2026\u27e8trunc\u27e9",
    "schema_valid": true,
    "schema_errors": []
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": false,
  "fallback_roles": [],
  "llm_roles_used": [
    "analyst",
    "gap_reviewer"
  ]
}
```

### baseline_6

*Source: `07_system_outputs/baseline_6/baseline_6__TASK-MAIN-FIN-039__r02.json`*

```json
{
  "run_id": "baseline_6__TASK-MAIN-FIN-039__r02",
  "task_id": "TASK-MAIN-FIN-039",
  "system_id": "baseline_6",
  "system_label": "B6 LangGraph (draft / review / revise)",
  "run_number": 2,
  "seed": 20260607,
  "started_at": "2026-06-14T12:42:05Z",
  "wall_clock_ms": 39442.5759,
  "role_timings": [
    {
      "role_name": "draft",
      "status": "success",
      "duration_ms": 37704.1879,
      "llm_used": true,
      "llm_fallback": false,
      "llm_fallback_reason": ""
    },
    "\u2026(+1 more, len=2)"
  ],
  "api_cost_usd": 0.042234,
  "local_compute_ms": null,
  "model_versions": {
    "model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "total_input_tokens": 3163,
    "total_output_tokens": 2183
  },
  "decoding_params": {
    "temperature": 0.0
  },
  "code_ref": "",
  "harness_version": "0.1.0",
  "output_type": "BASELINE_SCHEMA:specification",
  "output": {
    "specification": {
      "mission_intent": "Develop a comprehensive risk-of-material-misstatement assessment template covering all five COSO/ICFR components across \u2026\u27e8trunc\u27e9",
      "minimum": [
        {
          "dimension": "ICFR component coverage",
          "threshold": "All five components addressed: control environment, risk assessment, information and communication, control activities, \u2026\u27e8trunc\u27e9",
          "rationale": "The request explicitly names all five components and requires the template to be 'complete,' making full coverage a non-\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+8 more, len=9)"
      ],
      "target": [
        {
          "dimension": "Template usability and reusability",
          "objective": "Structured so the template can be reused or updated in future audit cycles with minimal rework",
          "rationale": "The request does not specify this, but a 'best efforts' deliverable of this scope implies long-term utility; this is asp\u2026\u27e8trunc\u27e9"
        },
        "\u2026(+3 more, len=4)"
      ],
      "constraints": [
        {
          "predicate": "framework == PCAOB AS 2110",
          "rationale": "Explicitly required as the governing standard for the risk-of-material-misstatement assessment structure."
        },
        "\u2026(+7 more, len=8)"
      ],
      "suspected_gaps": [
        {
          "field": "Definition of 'end of business Friday'",
          "reason": "No time zone is specified. With 12 jurisdictions involved, the team and partner may be in different locations, creating \u2026\u27e8trunc\u27e9"
        },
        "\u2026(+9 more, len=10)"
      ]
    },
    "raw_text": "{\n  \"mission_intent\": \"Develop a comprehensive risk-of-material-misstatement assessment template covering all five COSO/\u2026\u27e8trunc\u27e9",
    "schema_valid": true,
    "schema_errors": []
  },
  "ok": true,
  "errors": [],
  "any_llm_fallback": false,
  "fallback_roles": [],
  "llm_roles_used": [
    "draft",
    "review"
  ]
}
```

---

*Schema and documentation generated 2026-06-25 from frozen `07_system_outputs`. Read-only analysis; no apparatus runs or API calls.*

