"""
Tests for the corpus CLI (Workstream C2).

The CLI is exercised end-to-end with a MockLLMClient (no API key, no
network) and the HashEmbedder fallback for dedup / leakage so
sentence-transformers is not required. The eval-host run uses Anthropic
plus the production sentence-transformer.

Run:  python3 -m pytest apparatus/corpus/tests/test_cli.py -q
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.corpus import cli


NUMBERED_FIVE = (
    "1. The CISO asks the SOC manager for a vulnerability posture summary "
    "by end of week covering all internet-facing assets.\n"
    "2. The director requests a patch compliance brief comparing this "
    "quarter to last across the financial-services subsidiary.\n"
    "3. The audit committee wants an incident summary of the ransomware "
    "containment over the weekend.\n"
    "4. The risk officer asks for a tailored threat briefing before the "
    "board meeting next Tuesday.\n"
    "5. The CTO requests a posture assessment focused on third-party "
    "access since the new vendor onboarding policy went live.")


SCAFFOLD_JSON = json.dumps({
    "mission_intent": "Brief the CISO on posture.",
    "minimum": [{"dimension": "delivery_date", "threshold": None,
                  "rationale": "deadline phrased as 'end of week'"}],
    "target": [], "constraints": [],
    "suspected_gaps": [{"field": "minimum.delivery_date",
                         "reason": "no concrete deadline given"}]})


def _run(argv, mock_default):
    """Invoke the CLI with the MockLLMClient default response patched in
    via the hidden `_mock_default` setting on each subcommand."""
    parser = cli.build_parser()
    args = parser.parse_args(argv)
    args._mock_default = mock_default
    return args.func(args)


def test_generate_writes_one_jsonl_per_domain(tmp_path):
    rc = _run(["generate", "--domain", "financial_reporting",
               "--n-runs", "2", "--out", str(tmp_path)],
              mock_default=NUMBERED_FIVE)
    assert rc == 0
    out = tmp_path / "financial_reporting.jsonl"
    assert out.exists()
    rows = [json.loads(l) for l in out.read_text().splitlines() if l]
    # 3 categories x 2 runs x up to 5 candidates = 30
    assert len(rows) == 30
    assert {r["domain"] for r in rows} == {"financial_reporting"}


def test_generate_runs_all_corpus_domains_when_none_specified(tmp_path):
    """Test renamed and updated 2026-06-04: DOMAIN_GUIDANCE now lists all
    four corpus domains (3 main + 1 holdout) per HANDOFF_08 registry fix.
    Generate with no --domain iterates every key in DOMAIN_GUIDANCE."""
    rc = _run(["generate", "--n-runs", "1", "--out", str(tmp_path)],
              mock_default=NUMBERED_FIVE)
    assert rc == 0
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == ["financial_reporting.jsonl",
                     "intelligence_collection_tasking.jsonl",
                     "security_operations_reporting.jsonl",
                     "software_engineering_specification.jsonl"]


def test_pilot_writes_one_file_per_domain(tmp_path):
    """Test updated 2026-06-04: same DOMAIN_GUIDANCE expansion as above.
    pilot iterates all four corpus domains."""
    rc = _run(["pilot", "--out", str(tmp_path)],
              mock_default=NUMBERED_FIVE)
    assert rc == 0
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == ["pilot_financial_reporting.jsonl",
                     "pilot_intelligence_collection_tasking.jsonl",
                     "pilot_security_operations_reporting.jsonl",
                     "pilot_software_engineering_specification.jsonl"]
    # 5 candidates per domain
    for fname in files:
        rows = [json.loads(l) for l in (tmp_path / fname).read_text()
                .splitlines() if l]
        assert len(rows) == 5


def test_scaffold_writes_anchor_scaffolds(tmp_path):
    tasks_path = tmp_path / "tasks.jsonl"
    tasks_path.write_text("\n".join(
        json.dumps({"task_id": "T%d" % i,
                    "text": "a stakeholder request %d" % i})
        for i in range(3)) + "\n")
    rc = _run(["scaffold", "--tasks", str(tasks_path),
                "--out", str(tmp_path / "scaffolds")],
               mock_default=SCAFFOLD_JSON)
    assert rc == 0
    out = tmp_path / "scaffolds" / "anchor_scaffolds.jsonl"
    rows = [json.loads(l) for l in out.read_text().splitlines() if l]
    assert len(rows) == 3
    assert all(r["parse_ok"] for r in rows)


def test_generate_perturbations_cli_writes_suite(tmp_path):
    selected = []
    pool_rows = []
    domains = ["financial_reporting", "intelligence_collection_tasking",
               "security_operations_reporting"]
    for i, domain in enumerate(domains, start=1):
        selected.append({"task_id": f"TASK-{i}", "domain": domain,
                         "category": "full_specification",
                         "candidate_idx": i})
        pool_rows.append({"domain": domain, "category": "full_specification",
                          "candidate_idx": i,
                          "text": f"Base request for {domain}"})

    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps({"selected": selected}))
    pool_path = tmp_path / "pool.jsonl"
    pool_path.write_text("\n".join(json.dumps(r) for r in pool_rows) + "\n")

    rc = _run(["generate-perturbations",
               "--selection", str(selection_path),
               "--pool", str(pool_path),
               "--out", str(tmp_path / "perturbations"),
               "--per-type", "1",
               "--base-count", "3",
               "--seed", "1"], mock_default="Perturbed request text.")
    assert rc == 0
    out = tmp_path / "perturbations" / "perturbation_suite.jsonl"
    rows = [json.loads(l) for l in out.read_text().splitlines() if l]
    assert len(rows) == 7
    assert all(r["request_text"] for r in rows)


def test_dedup_writes_report_and_kept_jsonl(tmp_path):
    candidates = tmp_path / "candidates.jsonl"
    rows = [
        {"text": "ransomware containment summary"},
        {"text": "ransomware containment summary"},      # exact duplicate
        {"text": "quarterly revenue variance versus budget"},
    ]
    candidates.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    rep_path = tmp_path / "dedup.json"
    kept_path = tmp_path / "kept.jsonl"
    rc = _run(["dedup", "--in", str(candidates), "--no-st",
                "--out", str(rep_path),
                "--kept-out", str(kept_path)], mock_default=None)
    assert rc == 0
    rep = json.loads(rep_path.read_text())
    assert rep["n_input"] == 3 and rep["n_dropped"] == 1
    kept = [json.loads(l) for l in kept_path.read_text().splitlines() if l]
    assert len(kept) == 2


def test_leakage_reads_aegis_seed_corpus_shape(tmp_path):
    # build a tiny reference in the AEGIS seed-corpus shape
    ref = {"examples": [
        {"seed_id": "s1", "payload": {
            "preprocessed_text": "ransomware containment summary"}},
        {"seed_id": "s2", "payload": {
            "preprocessed_text": "an unrelated financial expense analysis"}},
    ]}
    ref_path = tmp_path / "seed_corpus.json"
    ref_path.write_text(json.dumps(ref))

    cand_path = tmp_path / "candidates.jsonl"
    cand_path.write_text("\n".join(json.dumps(r) for r in [
        {"text": "ransomware containment summary"},          # leaks
        {"text": "wholly unrelated OSINT collection plan"},  # clean
    ]) + "\n")

    out_path = tmp_path / "leakage.json"
    rc = _run(["leakage", "--in", str(cand_path),
                "--reference", str(ref_path), "--no-st",
                "--out", str(out_path)], mock_default=None)
    assert rc == 0
    rep = json.loads(out_path.read_text())
    assert rep["n_candidates"] == 2 and rep["n_references"] == 2
    assert rep["n_flagged"] == 1
    assert rep["halt_triggered"] is True       # 50% > 5%
    assert 0 in rep["flagged_indices"]


def test_leakage_jsonl_reference_path(tmp_path):
    ref_path = tmp_path / "ref.jsonl"
    ref_path.write_text("\n".join(json.dumps({"text": t}) for t in [
        "the candidate corpus must not match this",
        "and not this either",
    ]) + "\n")
    cand_path = tmp_path / "cands.jsonl"
    cand_path.write_text(json.dumps({"text": "completely fresh text"})
                          + "\n")
    out_path = tmp_path / "leak.json"
    rc = _run(["leakage", "--in", str(cand_path),
                "--reference", str(ref_path), "--no-st",
                "--out", str(out_path)], mock_default=None)
    assert rc == 0
    rep = json.loads(out_path.read_text())
    assert rep["n_flagged"] == 0
    assert rep["halt_triggered"] is False


def test_parser_rejects_unknown_subcommand():
    import pytest
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["nonsense"])
