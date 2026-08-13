"""
The seven-ablation manifest (Workstream A4, PROTOCOL_LOCK Section 5).

Each entry is one ablation: its id, the MANDATE component it removes, the
kind of variant it is (apparatus-side config switch versus upstream AEGIS
variant), the rationale, and the precise change. PROTOCOL_LOCK fixes the
seven; this manifest only records what they are and how each is built.

PROTOCOL_LOCK Section 5 designates A1, A2 and A3 as primary ablations (main
paper) and A4 through A7 as secondary (supplement). The split is enforced
here so analysis Notebook 08 reads it from one place.

Inspection of the frozen MANDATE source (`AEGIS-eval/src/mandate/`):

  A3 emit_gaps lives in `PipelineConfig` and is read as `self.config.emit_gaps`
     in `pipeline.py`. Toggling it suppresses gap-report emission; the
     in-pipeline gap detection still runs. A3 is therefore a clean config
     switch.

  A5 success_registry is an Optional field on `PipelineConfig`. MANDATE-primary
     is instantiated with a populated registry; A5 supplies `None` instead.
     A5 is a config switch on the constructor argument.

  A1 (no role separation), A2 (no tolerance bands), A4 (no Validation role),
     A6 (no search-trace), A7 (no NIST RMF) all need source changes the
     PipelineConfig cannot express: the role list is constructed in
     `Pipeline.__init__` and includes `ValidationRole(self.config)` directly;
     `_make_trace_entry` is called inside every role; the tolerance-band
     structure is part of `models.py` and the anchor schema; and NIST RMF
     metadata is a separate component woven into the output. These ablations
     are built upstream as separate AEGIS git refs (variant tags), pinned in
     the pre-registration alongside the MANDATE-primary tag, and loaded by
     ref. Until those refs exist the ablation system raises a clear error
     and never silently falls back to MANDATE-primary.

NOTE (canonical path): MLT-Governance-Stack v1.0.0rc1 now implements A1, A2,
A4, A6 and A7 as canonical-engine config switches
(``mlt.mandate.PipelineConfig.ablate_*``). The canonical runner
``apparatus.systems.mandate_canonical.run_ablation`` /
``CanonicalAblationSystem`` executes all seven against the same MLT engine that
produces Cond-A/Cond-B (overrides in ``CANONICAL_ABLATION_OVERRIDES``). This
manifest is preserved as the original AEGIS-variant pre-registration record and
is intentionally left unchanged; the canonical path is layered on top of it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AblationKind(str, Enum):
    CONFIG_SWITCH = "config_switch"
    AEGIS_VARIANT = "aegis_variant"


PRIMARY_IDS = ("A1", "A2", "A3")
SECONDARY_IDS = ("A4", "A5", "A6", "A7")


@dataclass
class AblationSpec:
    """One ablation, as the pre-registration will pin it."""
    id: str                          # "A1" .. "A7"
    label: str
    removes: str                     # the MANDATE component removed
    rationale: str                   # what this ablation isolates
    kind: AblationKind
    is_primary: bool
    # config_switch: PipelineConfig kwargs the ablation applies on top of the
    # MANDATE-primary configuration; the system uses these to build a
    # PipelineConfig for this run.
    config_overrides: dict = field(default_factory=dict)
    # aegis_variant: the pinned AEGIS git ref (tag or commit) that provides
    # the ablated source. Empty until upstream builds and tags it; the
    # apparatus refuses to run the ablation while the ref is empty.
    aegis_ref: str = ""
    # Optional human note on the variant's expected behavior.
    notes: str = ""

    @property
    def system_id(self) -> str:
        return "ablation_%s" % self.id.lower()

    @property
    def system_label(self) -> str:
        return "Ablation %s (%s)" % (self.id, self.removes)

    @property
    def ready(self) -> bool:
        """The ablation can be run by the apparatus today."""
        if self.kind is AblationKind.CONFIG_SWITCH:
            return True
        return bool(self.aegis_ref)


# The seven ablations, in PROTOCOL_LOCK Section 5 order. Each entry's
# component target is read from the frozen MANDATE source so the change is
# concrete, not a description of intent.
ABLATIONS = {
    "A1": AblationSpec(
        id="A1",
        label="No role separation",
        removes="role decomposition: one LLM call serves all six roles",
        rationale=("Tests whether the 1+6 role decomposition contributes "
                   "beyond what a single well-prompted LLM call would give. "
                   "PROTOCOL_LOCK names it as a primary ablation."),
        kind=AblationKind.AEGIS_VARIANT,
        is_primary=True,
        aegis_ref="",
        notes=("Built upstream as an AEGIS variant tag, for example "
                "`mandate-eval-ablation-a1-2026q2-v1`. The variant replaces "
                "the six-role pipeline with a single combined prompt that "
                "asks one model to produce the full MANDATE-as-code output "
                "in one pass, on the same fine-tuned backend (or its base) "
                "to keep the model-family contrast intact.")),

    "A2": AblationSpec(
        id="A2",
        label="No tolerance bands",
        removes=("minimum / target / constraints anchor structure: collapsed "
                  "to a single threshold per field"),
        rationale=("Tests whether the three-band anchor (minimum, target, "
                   "constraints) carries information beyond a single "
                   "threshold. PROTOCOL_LOCK names it as a primary "
                   "ablation."),
        kind=AblationKind.AEGIS_VARIANT,
        is_primary=True,
        aegis_ref="",
        notes=("Built upstream as an AEGIS variant tag. The variant changes "
                "`models.MissionInput` / `models.AnchorSpec`, the "
                "mandate-as-code schema, and the Intake / Interpreter "
                "training so that anchor fields carry a single threshold. "
                "Grading reads the single-threshold anchor through a "
                "parallel ground-truth representation derived from the "
                "primary ground truth by collapsing the bands.")),

    "A3": AblationSpec(
        id="A3",
        label="No gap-report output",
        removes="GAP_REPORT artifact emission (emit_gaps=False)",
        rationale=("Tests whether emitting an explicit gap report changes "
                   "what the downstream system sees, beyond the gap "
                   "detection that happens inside the pipeline. "
                   "PROTOCOL_LOCK names it as a primary ablation."),
        kind=AblationKind.CONFIG_SWITCH,
        is_primary=True,
        config_overrides={"emit_gaps": False},
        notes=("In the MANDATE-primary configuration the apparatus sets "
                "`emit_gaps=True` so gap detection drives the GAP_REPORT "
                "output the protocol's O2 outcomes need. The A3 ablation "
                "leaves the in-pipeline detection running but suppresses "
                "the artifact, so any difference is attributable to the "
                "downstream artifact, not to detection capability.")),

    "A4": AblationSpec(
        id="A4",
        label="No Validation role",
        removes="the post-binding Validation role",
        rationale=("Tests whether the explicit Validation role catches "
                   "errors the other five roles miss, especially "
                   "fabrications and constraint inconsistencies."),
        kind=AblationKind.AEGIS_VARIANT,
        is_primary=False,
        aegis_ref="",
        notes=("`Pipeline.__init__` constructs the role list with "
                "`ValidationRole(self.config)` directly, so PipelineConfig "
                "cannot drop it. The variant rebuilds the role list "
                "without Validation and ends the pipeline at Binding.")),

    "A5": AblationSpec(
        id="A5",
        label="No Success Registry",
        removes="precedent-matching against the Success Registry",
        rationale=("Tests whether matching against the precedent registry "
                   "carries information beyond what the roles produce from "
                   "the request text alone."),
        kind=AblationKind.CONFIG_SWITCH,
        is_primary=False,
        config_overrides={"success_registry": None},
        notes=("MANDATE-primary is instantiated with a populated registry; "
                "A5 passes `None`. The pipeline's other state is unchanged. "
                "Be careful that MANDATE-primary actually sets the "
                "registry in `ollama_config`; if the field is None in "
                "primary too then A5 has no contrast.")),

    "A6": AblationSpec(
        id="A6",
        label="No search-trace",
        removes="`_make_trace_entry` outputs and the cryptographic trace chain",
        rationale=("Tests whether the trace chain influences validation "
                   "behavior or downstream consumption. Trace completeness "
                   "is not a primary comparative outcome (PROTOCOL_LOCK "
                   "Section 4.1) but A6 isolates its effect on the others."),
        kind=AblationKind.AEGIS_VARIANT,
        is_primary=False,
        aegis_ref="",
        notes=("Every role calls `_make_trace_entry` in `roles/base.py`; "
                "the variant short-circuits that call and the trace "
                "assembly in the Validation role, leaving the rest of the "
                "pipeline unchanged.")),

    "A7": AblationSpec(
        id="A7",
        label="No NIST AI RMF metadata",
        removes=("nist_rmf metadata fields and the associated compliance "
                  "hooks in the artifact"),
        rationale=("Tests whether the NIST AI RMF annotations affect the "
                   "outcomes; they sit alongside the substantive anchor and "
                   "are mostly compliance-oriented, so a near-zero effect "
                   "would be a useful null result."),
        kind=AblationKind.AEGIS_VARIANT,
        is_primary=False,
        aegis_ref="",
        notes=("`nist_rmf.py` is woven into the artifact post-pipeline. "
                "The variant removes the annotation step and the "
                "corresponding schema fields.")),
}


def get_ablation(ablation_id: str) -> AblationSpec:
    """Look up an ablation by id (case-insensitive). Raises KeyError on a
    miss, with the locked list, so a typo is never silently a different
    ablation."""
    key = (ablation_id or "").upper().strip()
    if key not in ABLATIONS:
        raise KeyError("unknown ablation id %r (the seven are: %s)"
                       % (ablation_id, ", ".join(sorted(ABLATIONS))))
    return ABLATIONS[key]


def list_ablations(*, primary: Optional[bool] = None,
                   ready_only: bool = False) -> list:
    """Return ablation specs, filtered by primary/secondary and/or readiness."""
    out = []
    for aid in sorted(ABLATIONS):
        spec = ABLATIONS[aid]
        if primary is not None and spec.is_primary is not primary:
            continue
        if ready_only and not spec.ready:
            continue
        out.append(spec)
    return out
