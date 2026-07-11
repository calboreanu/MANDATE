"""
Corpus authoring CLI (Workstream C2).

Turn the corpus pipeline into a single-command entry point Cal can run on
the eval host. Subcommands:

  generate    PROMPTS Section 1 task generation across domains x categories
  scaffold    PROMPTS Section 2 anchor scaffolding for a tasks file
  dedup       cosine-0.85 dedup of a candidates file
  leakage     cosine-0.85 leakage audit against a reference set
  pilot       the §13 action 7 shortcut: one full sweep that produces the
              six pilot tasks the pilot phase reads from

The eval host needs ANTHROPIC_API_KEY in the environment for generate /
scaffold / pilot, and `sentence-transformers` for the production embedder
(falls back to HashEmbedder with a clear warning, useful for smoke testing
but not for the real 0.85 gate).

Usage:

  python3 -m apparatus.corpus.cli generate \\
      --domain security_operations_reporting \\
      --n-runs 5 \\
      --out 03_corpus/candidates/

  python3 -m apparatus.corpus.cli scaffold \\
      --tasks 03_corpus/corpus_frozen.jsonl \\
      --out 04_ground_truth/scaffolds/

  python3 -m apparatus.corpus.cli dedup \\
      --in 03_corpus/candidates/ \\
      --out 03_corpus/dedup_report.json

  python3 -m apparatus.corpus.cli leakage \\
      --in 03_corpus/candidates/ \\
      --reference AEGIS-eval/training/seed_corpus.json \\
      --out 03_corpus/leakage_audit.json

  python3 -m apparatus.corpus.cli pilot --out 03_corpus/pilot/
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

# --- shared helpers ---------------------------------------------------------

DEFAULT_GEN_MODEL = "claude-opus-4-6"
DEFAULT_SCAFFOLD_MODEL = "claude-opus-4-6"
DEFAULT_THRESHOLD = 0.85


def _stderr(msg):
    print(msg, file=sys.stderr, flush=True)


def _load_dotenv(path: str = ".env") -> int:
    """Load `KEY=value` lines from `path` into os.environ if not already set.

    Looks first at `path` in the current working directory, then walks up
    one parent (so the CLI loads `.env` whether it is run from the project
    root or from a subdirectory). Quiet on a missing file; the CLI handles
    a missing key downstream with a clear error.

    Returns the number of keys loaded. The CLI's eval-host run-modes use
    this so a `.env` in the project root reliably reaches the LLM clients,
    without the operator having to source it in every shell invocation.
    """
    candidates = [path, os.path.join("..", path)]
    loaded = 0
    for p in candidates:
        if not os.path.isfile(p):
            continue
        try:
            with open(p) as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, _, v = s.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and v and k not in os.environ:
                        os.environ[k] = v
                        loaded += 1
        except OSError:
            continue
        break
    return loaded


def _load_jsonl(path):
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _write_jsonl(path, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")


def _write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str, ensure_ascii=False)


def _make_anthropic_client(api_key=None, mock_default=None):
    """Build the LLM client. If `mock_default` is set (the tests pass it),
    use MockLLMClient instead and never touch the Anthropic SDK."""
    if mock_default is not None:
        from ..baselines.llm_client import MockLLMClient
        return MockLLMClient(default=mock_default)
    from ..baselines.llm_client import AnthropicClient
    return AnthropicClient(api_key=api_key or os.environ.get(
        "ANTHROPIC_API_KEY"))


def _make_embedder(prefer_st: bool = True):
    """Return (embedder, name). Falls back to HashEmbedder if
    sentence-transformers is not installed."""
    from .embeddings import (SentenceTransformerEmbedder, HashEmbedder,
                              DEFAULT_ST_MODEL)
    if prefer_st:
        try:
            return (SentenceTransformerEmbedder(model_name=DEFAULT_ST_MODEL),
                     "sentence-transformer:%s" % DEFAULT_ST_MODEL)
        except ImportError:
            _stderr("warning: sentence-transformers not installed; "
                     "falling back to HashEmbedder. Install on the eval "
                     "host for the real 0.85 similarity gate.")
    return HashEmbedder(dim=512), "HashEmbedder(dim=512)"


def _extract_reference_texts(path):
    """Pull text strings from a reference corpus file.

    Supports two shapes:
      JSONL with a `text` or `request_text` or `preprocessed_text` field.
      A JSON object with an `examples` list whose items carry payload-style
      nested text (the AEGIS seed_corpus.json shape).
    Returns a list of strings.
    """
    if path.endswith(".jsonl"):
        texts = []
        for row in _load_jsonl(path):
            t = (row.get("text") or row.get("request_text")
                 or row.get("preprocessed_text") or "")
            if t:
                texts.append(t)
        return texts
    # JSON
    with open(path) as f:
        data = json.load(f)
    examples = data.get("examples") if isinstance(data, dict) else None
    if not examples:
        examples = data if isinstance(data, list) else []
    texts = []
    for ex in examples:
        if not isinstance(ex, dict):
            continue
        payload = ex.get("payload") or {}
        t = (ex.get("text") or ex.get("request_text")
             or payload.get("preprocessed_text")
             or payload.get("request_text")
             or payload.get("text") or "")
        if t:
            texts.append(t)
    return texts


# --- generate ---------------------------------------------------------------

def cmd_generate(args) -> int:
    from .generator import TaskGenerator
    from .prompts import DOMAIN_GUIDANCE

    domains = args.domain or list(DOMAIN_GUIDANCE)
    for d in domains:
        if d not in DOMAIN_GUIDANCE:
            _stderr("unknown domain: %s (one of %s)"
                     % (d, ", ".join(DOMAIN_GUIDANCE)))
            return 2
    client = _make_anthropic_client(mock_default=args._mock_default)
    gen = TaskGenerator(client=client, model=args.model)
    os.makedirs(args.out, exist_ok=True)
    total = 0
    for d in domains:
        cands = gen.generate_batch(domain=d, n_runs=args.n_runs)
        out_path = os.path.join(args.out, "%s.jsonl" % d)
        _write_jsonl(out_path, [c.to_dict() for c in cands])
        total += len(cands)
        print("  %s: %d candidates -> %s" % (d, len(cands), out_path))
    print("generated %d candidates across %d domains" % (total, len(domains)))
    return 0


# --- scaffold ---------------------------------------------------------------

def cmd_scaffold(args) -> int:
    from .scaffolder import AnchorScaffolder

    tasks = _load_jsonl(args.tasks)
    client = _make_anthropic_client(mock_default=args._mock_default)
    sc = AnchorScaffolder(client=client, model=args.model,
                           temperature=getattr(args, "temperature", 0.0),
                           max_tokens=getattr(args, "max_tokens", 4096))
    os.makedirs(args.out, exist_ok=True)
    rows = []
    for t in tasks:
        out = sc.scaffold(task_id=t.get("task_id") or t.get("candidate_id"),
                          request_text=t.get("text", ""))
        rows.append(out.to_dict())
    out_path = os.path.join(args.out, "anchor_scaffolds.jsonl")
    _write_jsonl(out_path, rows)
    parsed = sum(1 for r in rows if r.get("parse_ok"))
    print("scaffolded %d tasks (%d parsed ok) -> %s"
          % (len(rows), parsed, out_path))
    return 0


# --- dedup ------------------------------------------------------------------

def _gather_candidate_files(path):
    """Accept either a directory of .jsonl files or a single .jsonl file."""
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.jsonl")))
    return [path] if os.path.isfile(path) else []


def cmd_dedup(args) -> int:
    from .embeddings import cosine_dedup

    files = _gather_candidate_files(args.in_path)
    rows = []
    for fp in files:
        rows.extend(_load_jsonl(fp))
    if not rows:
        _stderr("no candidates found at %s" % args.in_path)
        return 2
    embedder, embedder_name = _make_embedder(prefer_st=not args.no_st)
    texts = [r.get("text", "") for r in rows]
    print("embedding %d candidates via %s..." % (len(texts), embedder_name))
    embeddings = embedder.embed(texts)
    report = cosine_dedup(embeddings, threshold=args.threshold)
    kept_rows = [rows[i] for i in report.kept_indices]

    rep_path = args.out or "dedup_report.json"
    _write_json(rep_path, {
        "embedder": embedder_name,
        "input_files": files,
        "n_input": report.n_in, "n_kept": report.n_kept,
        "n_dropped": report.n_dropped, "threshold": report.threshold,
        "dropped": [{"kept_idx": k, "dropped_idx": d,
                      "similarity": float(s)}
                     for k, d, s in report.dropped],
    })
    if args.kept_out:
        _write_jsonl(args.kept_out, kept_rows)
    print("kept %d / %d (dropped %d at threshold %.2f) -> %s"
          % (report.n_kept, report.n_in, report.n_dropped,
             report.threshold, rep_path))
    return 0


# --- leakage ----------------------------------------------------------------

def cmd_leakage(args) -> int:
    from .embeddings import leakage_audit

    files = _gather_candidate_files(args.in_path)
    cand_rows = []
    for fp in files:
        cand_rows.extend(_load_jsonl(fp))
    if not cand_rows:
        _stderr("no candidates found at %s" % args.in_path)
        return 2

    ref_texts = _extract_reference_texts(args.reference)
    if not ref_texts:
        _stderr("no reference texts extracted from %s" % args.reference)
        return 2

    embedder, embedder_name = _make_embedder(prefer_st=not args.no_st)
    cand_texts = [r.get("text", "") for r in cand_rows]
    print("embedding %d candidates and %d references via %s..."
          % (len(cand_texts), len(ref_texts), embedder_name))
    cand_emb = embedder.embed(cand_texts)
    ref_emb = embedder.embed(ref_texts)
    report = leakage_audit(cand_emb, ref_emb, threshold=args.threshold)

    out_path = args.out or "leakage_audit.json"
    _write_json(out_path, {
        "embedder": embedder_name,
        "candidate_files": files, "reference_file": args.reference,
        "threshold": report.threshold,
        "n_candidates": report.n_candidates,
        "n_references": report.n_references,
        "n_flagged": len(report.flagged_indices),
        "overlap_rate": report.overlap_rate,
        "halt_threshold_pct": 5.0,
        "halt_triggered": report.overlap_rate > 0.05,
        "flagged_indices": report.flagged_indices,
        "matches": report.matches,
    })
    print("overlap %d / %d (%.2f%%) at threshold %.2f -> %s"
          % (len(report.flagged_indices), report.n_candidates,
             100.0 * report.overlap_rate, report.threshold, out_path))
    if report.overlap_rate > 0.05:
        print("HALT: PROTOCOL_LOCK Section 13 fires above 5%; regenerate "
              "or substitute the flagged tasks")
    return 0


# --- pilot ------------------------------------------------------------------

def cmd_source_build(args) -> int:
    """PROMPTS Section 1.1 build: fetch the curated per-domain source set
    and build the AEGIS-format Jaccard chunk index. Real data only; no
    source is fabricated, every failure is recorded."""
    from .sources.fetch import build_domain_index
    import json as _json
    from .prompts import DOMAIN_GUIDANCE

    domains = args.domain or list(DOMAIN_GUIDANCE)
    overall = {}
    for d in domains:
        if d not in DOMAIN_GUIDANCE:
            _stderr("unknown domain: %s" % d)
            return 2
        print("building", d, "...")
        report = build_domain_index(domain=d, project_root=args.project_root)
        overall[d] = report.to_dict()
        print("  fetched:    %d" % len(report.fetched))
        print("  failed:     %d" % len(report.failed))
        for f in report.failed:
            print("    [FAIL] %s -- %s" % (f.spec.title, f.error))
        print("  files indexed:  %d" % report.files_indexed)
        print("  chunks indexed: %d" % report.chunks_indexed)
        print("  index path:     %s" % report.index_path)
    out_path = args.out or os.path.join(args.project_root, "rag",
                                          "embeddings", "build_report.json")
    _write_json(out_path, overall)
    print("build report written:", out_path)
    return 0


def cmd_ingest_manual(args) -> int:
    """Ingest PI-downloaded PDFs for a domain whose curated URLs do not
    fetch reliably (Handoff 07b/07c/07d documented JCS.mil, GAO, CIA
    static-CDN, and several dni.gov paths as unreachable from the eval
    host). Each PDF must have a manifest entry providing its title, URL,
    and download date; ingest skips PDFs without manifest entries."""
    from .sources.manual import (ingest_manual_sources,
                                   manifest_template, save_manifest,
                                   load_manifest, MANIFEST_NAME)
    from .prompts import DOMAIN_GUIDANCE

    if args.domain not in DOMAIN_GUIDANCE:
        _stderr("unknown domain: %s" % args.domain)
        return 2
    manual_dir = args.manual_dir or os.path.join(
        args.project_root, "rag", "sources", args.domain, "manual")
    sources_dir = args.sources_dir or os.path.join(
        args.project_root, "rag", "sources", args.domain)
    os.makedirs(manual_dir, exist_ok=True)
    os.makedirs(sources_dir, exist_ok=True)

    if args.init_manifest:
        # write a manifest template (with the example entry) and stop
        manifest_path = os.path.join(manual_dir, MANIFEST_NAME)
        if os.path.exists(manifest_path) and not args.force:
            _stderr("manifest already exists: %s (pass --force to "
                     "overwrite)" % manifest_path)
            return 4
        save_manifest(manual_dir, manifest_template(args.domain))
        print("wrote manifest template:", manifest_path)
        print("fill in entries for every PDF you place in", manual_dir,
              "then run `ingest-manual` again without --init-manifest")
        return 0

    rep = ingest_manual_sources(domain=args.domain,
                                 manual_dir=manual_dir,
                                 sources_dir=sources_dir)
    print("ingested:", len(rep.ingested))
    for e in rep.ingested:
        print("  + %-40s sha256=%s..." % (e.filename, e.sha256[:12]))
    print("skipped (no manifest entry):", len(rep.skipped))
    for s in rep.skipped:
        print("  ? %s -- %s" % (s["filename"], s["reason"]))
    print("failed:", len(rep.failed))
    for f in rep.failed:
        print("  ! %s -- %s" % (f["filename"], f["reason"]))

    if args.rebuild_index:
        from .sources.fetch import (build_domain_index)
        # rebuild the domain index using the .txt files now in sources_dir,
        # without refetching curated URLs (which the PI knows do not work
        # from the eval host for this domain).
        from aegis.llm.rag_retriever import build_rag_index  # type: ignore
        index_path = os.path.join(args.project_root, "rag", "embeddings",
                                    "%s.jsonl" % args.domain)
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        summary = build_rag_index(input_dir=sources_dir,
                                   output_path=index_path,
                                   source=args.domain.upper(),
                                   chunk_size=1200, chunk_overlap=200)
        print("rebuilt index:", index_path)
        print("  files indexed: %d   chunks indexed: %d"
              % (summary.get("files_indexed", 0),
                 summary.get("chunks_indexed", 0)))
    return 0


def cmd_source_generate(args) -> int:
    """PROMPTS Section 1 source-conditioned generation: sample chunks from
    the per-domain index, generate one candidate per chunk. Writes a JSONL
    of TaskCandidate records each carrying a `derived_from` reference."""
    from .source_conditioned import (SourceConditionedGenerator,
                                       load_chunks, sample_chunks,
                                       candidate_to_record)
    from .prompts import DOMAIN_GUIDANCE, CATEGORIES

    if args.domain not in DOMAIN_GUIDANCE:
        _stderr("unknown domain: %s" % args.domain)
        return 2
    if args.category not in CATEGORIES:
        _stderr("unknown category: %s" % args.category)
        return 2

    index_path = args.index or os.path.join(args.project_root, "rag",
                                              "embeddings",
                                              "%s.jsonl" % args.domain)
    if not os.path.isfile(index_path):
        _stderr("index not found: %s "
                 "(run `source-build --domain %s` first)"
                 % (index_path, args.domain))
        return 3

    chunks = load_chunks(index_path)
    if not chunks:
        _stderr("index has no chunks: %s" % index_path)
        return 3
    sampled = sample_chunks(chunks, n=args.n_chunks, seed=args.seed)
    if len(sampled) < args.n_chunks:
        _stderr("warning: requested %d chunks, pool only has %d"
                 % (args.n_chunks, len(sampled)))

    client = _make_anthropic_client(mock_default=args._mock_default)
    gen = SourceConditionedGenerator(client=client, model=args.model)
    records = []
    for i, ch in enumerate(sampled, start=1):
        cand = gen.generate_one(domain=args.domain, category=args.category,
                                  chunk=ch, candidate_idx=i)
        records.append(candidate_to_record(cand, chunk=ch))

    out_dir = args.out or os.path.join(args.project_root, "03_corpus",
                                          "candidates_source_first")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
                             "%s_%s.jsonl" % (args.domain, args.category))
    _write_jsonl(out_path, records)
    print("wrote", len(records), "source-derived candidates ->", out_path)
    return 0


def cmd_select_main(args) -> int:
    """Two-step PI selection helper for the 40-per-domain main corpus.

    --propose writes a markdown file with one section per (domain x
    category), water-filled across sources so no single document
    dominates each cell. The PI edits the `[x]` checkboxes.

    --apply reads the edited markdown and writes main_selection.json in
    the Handoff-06-compatible shape. Validates 40 per domain.
    """
    from .selection import (stratified_propose, render_proposal_md,
                              parse_proposal, build_selection_json,
                              DEFAULT_CATEGORY_TARGETS)

    if args.propose == args.apply:
        _stderr("pick exactly one of --propose or --apply")
        return 2
    pool_path = args.pool or os.path.join(args.project_root,
                                            "03_corpus", "main",
                                            "candidates_main.jsonl")
    if not os.path.isfile(pool_path):
        _stderr("pool not found: %s" % pool_path)
        return 3
    candidates = _load_jsonl(pool_path)

    if args.propose:
        accepted = stratified_propose(candidates,
                                        targets=DEFAULT_CATEGORY_TARGETS)
        out = render_proposal_md(candidates, accepted,
                                   targets=DEFAULT_CATEGORY_TARGETS)
        out_path = args.proposal or os.path.join(
            args.project_root, "03_corpus", "main", "selection_proposal.md")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(out)
        print("wrote proposal:", out_path)
        print("candidates pre-marked accepted:", len(accepted))
        from collections import Counter
        by_dom = Counter(d for (d, _, _) in accepted)
        for d, n in sorted(by_dom.items()):
            print("  %-32s %d" % (d, n))
        print("\nEdit the file, then run "
              "`select-main --apply --proposal %s` to build "
              "main_selection.json" % out_path)
        return 0

    # --apply
    proposal_path = args.proposal or os.path.join(
        args.project_root, "03_corpus", "main", "selection_proposal.md")
    if not os.path.isfile(proposal_path):
        _stderr("proposal not found: %s" % proposal_path)
        return 3
    with open(proposal_path) as f:
        proposal_text = f.read()
    accepted = parse_proposal(proposal_text)
    rep = build_selection_json(candidates, accepted)
    print("accepted per domain:")
    for d, n in sorted(rep.accepted_per_domain.items()):
        print("  %-32s %d" % (d, n))
    print("per (domain, category):")
    for k, n in sorted(rep.per_category.items()):
        print("  %-50s %d" % (k, n))
    if rep.errors:
        _stderr("selection invalid:")
        for e in rep.errors:
            _stderr("  - %s" % e)
        return 4
    out_path = args.out or os.path.join(args.project_root, "03_corpus",
                                          "main", "main_selection.json")
    obj = {"selected": rep.selection,
            "selected_by": args.selected_by,
            "selected_at": args.selected_at,
            "notes": ""}
    _write_json(out_path, obj)
    print("wrote selection:", out_path)
    print("total selected:", len(rep.selection))
    return 0


def cmd_realism_form(args) -> int:
    """Generate a per-rater CSV template for the FORMS Section 4 realism
    audit. Each SME gets one CSV and rates each task 1 to 5."""
    from .realism import write_template

    sel = json.load(open(args.selection))
    if "selected" not in sel:
        _stderr("not a selection file: %s" % args.selection)
        return 2
    # resolve text from the pool
    pool = {(c["domain"], c["category"], int(c["candidate_idx"])): c
            for c in _load_jsonl(args.pool)}
    tasks = []
    for s in sel["selected"]:
        key = (s["domain"], s["category"], int(s["candidate_idx"]))
        c = pool.get(key)
        if c is None:
            _stderr("selection entry not in pool: %s" % s.get("task_id"))
            return 3
        tasks.append({"task_id": s["task_id"], "text": c["text"],
                      "domain": s["domain"], "category": s["category"]})
    out_path = args.out or os.path.join(
        args.project_root, "04_ground_truth", "realism",
        "rater_%s.csv" % args.rater_id)
    write_template(tasks, args.rater_id, out_path)
    print("wrote template:", out_path)
    print("rater:", args.rater_id, " tasks:", len(tasks))
    return 0


def cmd_realism_aggregate(args) -> int:
    """Read every rater CSV under `--inputs` and produce the audit
    summary: per-task mean/median, below-threshold halt list, Krippendorff
    alpha across raters."""
    from .realism import parse_inputs, aggregate

    paths = args.inputs or [os.path.join(args.project_root,
                                           "04_ground_truth", "realism")]
    ratings = parse_inputs(paths)
    report = aggregate(ratings)
    print("raters:", report["n_raters"], " tasks:", report["n_tasks"])
    print("halt threshold:", report["halt_threshold"],
          " halt count:", report["halt_count"])
    if report["krippendorff_alpha"] is not None:
        print("Krippendorff alpha (interval):",
              "%.3f" % report["krippendorff_alpha"])
    if report["halt_list"]:
        print("\nBelow-threshold tasks (review or substitute):")
        for tid in report["halt_list"]:
            s = report["by_task"][tid]
            print("  %s  mean=%.2f  n_ratings=%d"
                  % (tid, s["mean"] or 0.0, s["n_ratings"]))
    out_path = args.out or os.path.join(
        args.project_root, "04_ground_truth", "realism",
        "realism_audit_report.json")
    _write_json(out_path, report)
    print("\nreport written:", out_path)
    return 0


def cmd_generate_perturbations(args) -> int:
    """Phase 5: generate the 350-perturbation suite from the frozen main
    corpus. 7 perturbation types x 50 each (PROMPTS Section 3,
    PROTOCOL_LOCK Section 1). Stratified base = 30 tasks across the three
    domains.

    Requires `corpus_freeze_v1` (the suite is read at every later phase
    against the frozen base; running against a moving corpus breaks
    Phase 6 anonymization)."""
    from ..perturbations.generator import (PerturbationGenerator,
                                              PERTURBATION_TYPES,
                                              TARGET_PER_TYPE)

    sel = json.load(open(args.selection))
    pool = {(c["domain"], c["category"], int(c["candidate_idx"])): c
            for c in _load_jsonl(args.pool)}
    from types import SimpleNamespace

    # Resolve selected -> base tasks
    all_tasks = []
    for s in sel["selected"]:
        key = (s["domain"], s["category"], int(s["candidate_idx"]))
        c = pool.get(key)
        if c is None:
            _stderr("selection entry not in pool: %s" % s.get("task_id"))
            return 3
        all_tasks.append(SimpleNamespace(
            task_id=s["task_id"], request_text=c["text"],
            domain=s["domain"], category=s["category"]))

    # Stratified base: take ~10 per domain to total 30
    by_dom = {}
    for t in all_tasks:
        by_dom.setdefault(t.domain, []).append(t)
    import random
    rng = random.Random(args.seed)
    target_per_domain = max(1, args.base_count // max(1, len(by_dom)))
    base = []
    for d in sorted(by_dom):
        tasks = list(by_dom[d])
        rng.shuffle(tasks)
        base.extend(tasks[:target_per_domain])
    if len(base) > args.base_count:
        base = base[:args.base_count]
    print("base task count:", len(base), " (target %d)" % args.base_count)

    client = _make_anthropic_client(mock_default=args._mock_default)
    gen = PerturbationGenerator(llm_client=client, model=args.model)

    suite = gen.generate_suite(base_tasks=base, per_type=args.per_type)
    print("generated:", len(suite), "perturbations (target %d x %d = %d)"
          % (len(PERTURBATION_TYPES), args.per_type,
             len(PERTURBATION_TYPES) * args.per_type))

    out_dir = args.out or os.path.join(args.project_root, "06_perturbations")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "perturbation_suite.jsonl")
    _write_jsonl(out_path, [p.to_dict() for p in suite])
    print("wrote suite:", out_path)
    return 0


def cmd_pilot(args) -> int:
    """Execution-plan §13 action 7: produce the six pilot tasks. One
    PROMPTS Section 1 run per (domain, full_specification) generates up
    to 5 candidates per domain across 3 domains; the Lead Analyst then
    selects 2 per domain for the 6-task pilot set."""
    from .generator import TaskGenerator
    from .prompts import DOMAIN_GUIDANCE

    client = _make_anthropic_client(mock_default=args._mock_default)
    gen = TaskGenerator(client=client, model=args.model)
    os.makedirs(args.out, exist_ok=True)
    total = 0
    for d in DOMAIN_GUIDANCE:
        cands = gen.generate_run(domain=d, category="full_specification",
                                  run_idx=1)
        out_path = os.path.join(args.out, "pilot_%s.jsonl" % d)
        _write_jsonl(out_path, [c.to_dict() for c in cands])
        total += len(cands)
        print("  %s: %d candidates -> %s" % (d, len(cands), out_path))
    print("pilot candidates: %d. Lead Analyst selects 2 per domain for the "
          "6-task pilot." % total)
    return 0


# --- argparse ---------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="apparatus.corpus.cli",
        description="MANDATE evaluation corpus authoring (Workstream C2).")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="PROMPTS Section 1 task generation")
    g.add_argument("--domain", action="append",
                   help="domain (repeatable). Default: all three.")
    g.add_argument("--n-runs", type=int, default=5,
                   help="runs per (domain x category); default 5.")
    g.add_argument("--model", default=DEFAULT_GEN_MODEL)
    g.add_argument("--out", default="03_corpus/candidates")
    g.set_defaults(func=cmd_generate, _mock_default=None)

    s = sub.add_parser("scaffold", help="PROMPTS Section 2 anchor scaffolding")
    s.add_argument("--tasks", required=True, help="JSONL of tasks to scaffold")
    s.add_argument("--model", default=DEFAULT_SCAFFOLD_MODEL)
    s.add_argument("--out", default="04_ground_truth/scaffolds")
    s.add_argument("--max-tokens", type=int, default=4096,
                   help="LLM max_tokens; default 4096. Bump if scaffolds "
                        "truncate (HANDOFF_06b 2026-06-04 halt was 2048 "
                        "hitting the ceiling mid-JSON).")
    s.add_argument("--temperature", type=float, default=0.0,
                   help="LLM sampling temperature; default 0.0.")
    s.set_defaults(func=cmd_scaffold, _mock_default=None)

    d = sub.add_parser("dedup", help="cosine 0.85 dedup of candidates")
    d.add_argument("--in", dest="in_path", required=True,
                   help="directory of *.jsonl candidate files, or one file")
    d.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    d.add_argument("--out", default="03_corpus/dedup_report.json")
    d.add_argument("--kept-out", default="",
                   help="optional path to write the deduplicated JSONL")
    d.add_argument("--no-st", action="store_true",
                   help="force the HashEmbedder fallback (testing only)")
    d.set_defaults(func=cmd_dedup, _mock_default=None)

    l = sub.add_parser("leakage", help="cosine 0.85 leakage audit")
    l.add_argument("--in", dest="in_path", required=True,
                   help="directory of *.jsonl candidate files, or one file")
    l.add_argument("--reference", required=True,
                   help="path to a reference corpus (jsonl or json)")
    l.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    l.add_argument("--out", default="03_corpus/leakage_audit.json")
    l.add_argument("--no-st", action="store_true")
    l.set_defaults(func=cmd_leakage, _mock_default=None)

    sb = sub.add_parser("source-build",
                          help=("PROMPTS Section 1.1: fetch the curated "
                                 "per-domain source set and build the "
                                 "Jaccard chunk index"))
    sb.add_parser_root = True
    sb.add_argument("--domain", action="append",
                     help="domain (repeatable). Default: all three.")
    sb.add_argument("--project-root", default=os.getcwd(),
                     help="absolute project root; defaults to cwd.")
    sb.add_argument("--out", default="",
                     help="path for the cross-domain build_report.json")
    sb.set_defaults(func=cmd_source_build, _mock_default=None)

    im = sub.add_parser("ingest-manual",
                          help=("Manual-source fallback: index PI-"
                                 "downloaded PDFs for a domain whose "
                                 "curated URLs do not fetch reliably"))
    im.add_argument("--domain", required=True)
    im.add_argument("--project-root", default=os.getcwd())
    im.add_argument("--manual-dir", default="",
                     help="default rag/sources/<domain>/manual/")
    im.add_argument("--sources-dir", default="",
                     help="default rag/sources/<domain>/")
    im.add_argument("--init-manifest", action="store_true",
                     help="write a manifest template into manual-dir "
                          "and stop")
    im.add_argument("--force", action="store_true",
                     help="overwrite an existing manifest template")
    im.add_argument("--rebuild-index", action="store_true",
                     help="after ingest, rebuild the per-domain Jaccard "
                          "index from the sources directory")
    im.set_defaults(func=cmd_ingest_manual, _mock_default=None)

    sg = sub.add_parser("source-generate",
                          help=("PROMPTS Section 1 (source-conditioned): "
                                 "one candidate per sampled source chunk"))
    sg.add_argument("--domain", required=True)
    sg.add_argument("--category", required=True,
                     help="full_specification | gap_triggering | "
                          "stretch_case")
    sg.add_argument("--n-chunks", type=int, default=25,
                     help="chunks to sample (one candidate each); "
                          "default 25.")
    sg.add_argument("--seed", type=int, default=20260601)
    sg.add_argument("--model", default=DEFAULT_GEN_MODEL)
    sg.add_argument("--index", default="",
                     help="explicit index path; default "
                          "rag/embeddings/<domain>.jsonl")
    sg.add_argument("--project-root", default=os.getcwd())
    sg.add_argument("--out", default="",
                     help="output directory; default "
                          "03_corpus/candidates_source_first/")
    sg.set_defaults(func=cmd_source_generate, _mock_default=None)

    sm = sub.add_parser("select-main",
                          help=("PI selection helper for the 40-per-"
                                 "domain main corpus: --propose writes "
                                 "a checkbox markdown, --apply consumes "
                                 "the edited file"))
    sm.add_argument("--propose", action="store_true")
    sm.add_argument("--apply", action="store_true")
    sm.add_argument("--pool", default="",
                     help="default 03_corpus/main/candidates_main.jsonl")
    sm.add_argument("--proposal", default="",
                     help="default 03_corpus/main/selection_proposal.md")
    sm.add_argument("--out", default="",
                     help="default 03_corpus/main/main_selection.json")
    sm.add_argument("--project-root", default=os.getcwd())
    sm.add_argument("--selected-by", default="Cal")
    sm.add_argument("--selected-at", default="")
    sm.set_defaults(func=cmd_select_main, _mock_default=None)

    rf = sub.add_parser("realism-form",
                          help=("FORMS Section 4: write a per-rater CSV "
                                 "template for one SME"))
    rf.add_argument("--selection", required=True,
                     help="path to main_selection.json (or pilot)")
    rf.add_argument("--pool", required=True,
                     help="path to candidates_main.jsonl (or pilot pool)")
    rf.add_argument("--rater-id", required=True,
                     help="SME identifier, e.g. carter, mckay")
    rf.add_argument("--out", default="")
    rf.add_argument("--project-root", default=os.getcwd())
    rf.set_defaults(func=cmd_realism_form, _mock_default=None)

    ra = sub.add_parser("realism-aggregate",
                          help=("Aggregate rater CSVs into the audit "
                                 "report, halt list, Krippendorff alpha"))
    ra.add_argument("--inputs", nargs="+", default=[],
                     help="rater CSVs or directories of them; default "
                          "04_ground_truth/realism/")
    ra.add_argument("--out", default="")
    ra.add_argument("--project-root", default=os.getcwd())
    ra.set_defaults(func=cmd_realism_aggregate, _mock_default=None)

    gp = sub.add_parser("generate-perturbations",
                          help=("Phase 5: 350-perturbation suite from "
                                 "frozen main corpus (7 types x 50)"))
    gp.add_argument("--selection", required=True,
                     help="main_selection.json")
    gp.add_argument("--pool", required=True,
                     help="candidates_main.jsonl")
    gp.add_argument("--out", default="",
                     help="default 06_perturbations/")
    gp.add_argument("--model", default=DEFAULT_GEN_MODEL)
    gp.add_argument("--per-type", type=int, default=50,
                     help="perturbations per type (default 50)")
    gp.add_argument("--base-count", type=int, default=30,
                     help="stratified base task count (default 30)")
    gp.add_argument("--seed", type=int, default=20260605)
    gp.add_argument("--project-root", default=os.getcwd())
    gp.set_defaults(func=cmd_generate_perturbations, _mock_default=None)

    pi = sub.add_parser("pilot",
                         help=("§13 action 7: produce the six pilot tasks "
                                "(one Section 1 run per domain, "
                                "full_specification only)"))
    pi.add_argument("--model", default=DEFAULT_GEN_MODEL)
    pi.add_argument("--out", default="03_corpus/pilot")
    pi.set_defaults(func=cmd_pilot, _mock_default=None)

    return p


def main(argv=None) -> int:
    # Auto-load .env so a key placed by the operator at the project root is
    # picked up regardless of how the calling shell handles environment
    # propagation across invocations.
    _load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
