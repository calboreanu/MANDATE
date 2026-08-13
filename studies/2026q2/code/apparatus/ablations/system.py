"""
Ablation system adapter (Workstream A4).

`AblationSystem` is a thin wrapper over `MandatePrimarySystem` that produces
the ablation's run identity and applies its specification: a config switch
ablation is run from the same MANDATE source with PipelineConfig overrides;
an AEGIS-variant ablation is run from the pinned variant ref's source path.
A variant ablation whose ref is not yet set refuses to run, loudly, so an
unbuilt variant cannot quietly degrade into "MANDATE-primary minus nothing."

The same RunRecord schema the rest of the apparatus expects flows out of
`run()`. Anonymization, scoring, grading and analysis treat ablation runs the
same as MANDATE-primary runs except for the system identity.
"""
from __future__ import annotations

from typing import Optional

from ..systems.mandate_primary import MandatePrimarySystem
from .manifest import AblationSpec, AblationKind, get_ablation


class AblationNotReadyError(RuntimeError):
    """An AEGIS-variant ablation was invoked before its variant ref exists."""


class AblationSystem(MandatePrimarySystem):
    """Run one ablation through the same harness pathway as MANDATE-primary.

    Construction options:
      ablation_id: one of A1 through A7.
      primary_aegis_src_path: the MANDATE-primary source path (the frozen
         AEGIS-eval/src). For a config_switch ablation this is also where
         the ablation runs from. For an AEGIS-variant ablation the system
         needs the variant's own source path passed as variant_src_path.
      variant_src_path: the source path of the pinned AEGIS variant (only
         used for AEGIS-variant ablations). Empty until upstream tags the
         variant.
      primary_code_ref: the AEGIS-primary code_ref recorded on every
         RunRecord. For a variant ablation the spec's aegis_ref overrides
         this in the record so the run's provenance is the variant's ref,
         not MANDATE-primary's.
      mode and ollama_config: same meaning as MandatePrimarySystem; the
         config_overrides from the ablation spec are layered on top.
    """

    def __init__(self, *, ablation_id: str, primary_aegis_src_path: str,
                 variant_src_path: str = "",
                 primary_code_ref: str = "",
                 mode: str = "deterministic",
                 ollama_config: Optional[dict] = None):
        spec: AblationSpec = get_ablation(ablation_id)
        self.spec = spec

        if spec.kind is AblationKind.AEGIS_VARIANT:
            if not spec.aegis_ref:
                raise AblationNotReadyError(
                    "ablation %s (%s) is an AEGIS variant and its pinned "
                    "git ref is not set yet. Build and tag the variant "
                    "upstream, then set ABLATIONS[%r].aegis_ref before "
                    "running. The apparatus will not silently fall back "
                    "to MANDATE-primary for an ablation."
                    % (spec.id, spec.label, spec.id))
            if not variant_src_path:
                raise AblationNotReadyError(
                    "ablation %s requires the variant_src_path argument "
                    "pointing at a checkout of the variant ref %r"
                    % (spec.id, spec.aegis_ref))
            src = variant_src_path
            code_ref = spec.aegis_ref
        else:
            src = primary_aegis_src_path
            code_ref = primary_code_ref

        # Build the ablation's PipelineConfig overrides on top of the
        # supplied ollama_config (for ollama mode). For deterministic mode
        # the overrides feed PipelineConfig directly.
        merged_ollama = dict(ollama_config or {})
        if spec.kind is AblationKind.CONFIG_SWITCH and \
                spec.config_overrides:
            for k, v in spec.config_overrides.items():
                merged_ollama[k] = v

        super().__init__(aegis_src_path=src, mode=mode,
                         ollama_config=merged_ollama, code_ref=code_ref)
        # override identity after super().__init__
        self.system_id = spec.system_id
        self.system_label = spec.system_label
        self._config_overrides = dict(spec.config_overrides)

    def _build_config(self):
        """Apply the ablation's PipelineConfig overrides in deterministic
        mode too (the parent only applies ollama_config in ollama mode)."""
        from mandate.models import PipelineConfig
        if self.mode == "deterministic":
            return PipelineConfig(**self._config_overrides) \
                if self._config_overrides else PipelineConfig()
        return PipelineConfig(**self.ollama_config)

    def describe(self) -> dict:
        d = super().describe()
        d.update({
            "ablation_id": self.spec.id,
            "ablation_kind": self.spec.kind.value,
            "ablation_removes": self.spec.removes,
            "ablation_config_overrides": dict(self._config_overrides),
            "ablation_aegis_ref": self.spec.aegis_ref,
            "is_primary_ablation": self.spec.is_primary,
        })
        return d
