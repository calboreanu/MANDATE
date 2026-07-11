"""
Ablation variants for the MANDATE evaluation (Workstream A4).

PROTOCOL_LOCK Section 5 names seven ablations against MANDATE-primary, on the
30-task ablation subset, scored with the same outcomes as the primary
analysis. A1, A2 and A3 are primary ablations (main paper); A4 through A7 are
secondary (supplement).

The execution plan distinguishes two kinds of ablation:

  config_switch
      The ablation is expressible as a PipelineConfig change on the same
      frozen MANDATE source. The apparatus produces it directly. A3 (no gap
      output) and A5 (no Success Registry) are config switches.

  aegis_variant
      The ablation requires a modified MANDATE source (a different role
      composition, a different anchor schema, a different trace path). The
      apparatus does not patch AEGIS; instead the variant is built upstream,
      tagged as a separate git ref alongside the pinned MANDATE-primary tag,
      and the apparatus loads it by ref. A1, A2, A4, A6 and A7 are aegis
      variants; until their refs exist the ablation system raises a clear
      error rather than silently substituting a different ablation.

The same harness records, anonymization, scoring, grading and analysis path
that handle MANDATE-primary handle every ablation: the difference is the
system identity and the source it imports from.
"""
from .manifest import (ABLATIONS, AblationSpec, AblationKind, PRIMARY_IDS,
                       SECONDARY_IDS, get_ablation, list_ablations)
from .system import AblationSystem, AblationNotReadyError

__all__ = ["ABLATIONS", "AblationSpec", "AblationKind", "PRIMARY_IDS",
           "SECONDARY_IDS", "get_ablation", "list_ablations",
           "AblationSystem", "AblationNotReadyError"]
