"""
Perturbation generator (Workstream B3).

Transforms a base task's request text into a perturbed variant by applying one
of the seven perturbation prompts (prompts.py). For the three types that
append an internal tracking note (contradictory, missing_field, length), the
note is split off into metadata so a system under test never sees it.

Generating the actual 350-perturbation suite is Phase 5 and is gated on the
pre-registration deposit. This module is the tool; running it for real is
later. It uses the baseline LLM client (apparatus/baselines/llm_client.py).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .prompts import (PERTURBATION_TYPES, PERTURBATION_SYSTEM,
INJECTION_SUBTYPES, TARGET_PER_TYPE)

# Placeholder default; pinned at the deposit. PROMPTS.md Section 3 specifies
# "Claude Opus 4 or equivalent" as the perturbation-generation model.
DEFAULT_PERTURBATION_MODEL = "claude-opus-4-6"

OUTPUT_TYPE_LABELS = {
    "surface_noise": "surface_noise",
    "ambiguity": "ambiguity_injection",
    "contradictory": "contradictory_constraints",
    "prompt_injection": "prompt_injection",
    "missing_field": "missing_required_field",
    "ood": "out_of_distribution_input",
    "length": "length_perturbation",
}

OUTPUT_SUBTYPE_LABELS = {
    "direct": "direct_command",
    "social_engineering": "role_play",
    "fake_authority": "hidden_instruction",
}


@dataclass
class PerturbedTask:
    """One generated perturbation. request_text is what a system receives;
    internal_note is the stripped tracking note, kept only as eval metadata."""
    perturbation_id: str
    base_task_id: str
    domain: str
    perturbation_type: str
    sub_type: str
    request_text: str
    internal_note: str = ""
    model: str = ""
    generation_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "perturbation_id": self.perturbation_id,
            "base_task_id": self.base_task_id,
            "domain": self.domain,
            "perturbation_type": OUTPUT_TYPE_LABELS.get(
                self.perturbation_type, self.perturbation_type),
            "sub_type": OUTPUT_SUBTYPE_LABELS.get(self.sub_type,
                                                  self.sub_type),
            "request_text": self.request_text,
            "internal_note": self.internal_note,
            "model": self.model,
            "generation_ms": round(self.generation_ms, 3),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


def _split_internal_note(text: str, note_prefix: Optional[str]):
    """Return (clean_text, note). If note_prefix is set and present, the note
    from that marker to the end is split off."""
    if not note_prefix:
        return text.strip(), ""
    idx = text.find(note_prefix)
    if idx == -1:
        return text.strip(), ""
    return text[:idx].strip(), text[idx:].strip()


def _subtype_distribution(count: int) -> list:
    """Spread `count` injection trials across the 3 sub-types as evenly as
    possible. count=50 -> [17, 17, 16]."""
    base, rem = divmod(count, len(INJECTION_SUBTYPES))
    return [base + (1 if i < rem else 0) for i in range(len(INJECTION_SUBTYPES))]


class PerturbationGenerator:
    def __init__(self, llm_client, model: str = DEFAULT_PERTURBATION_MODEL,
                 temperature: float = 0.7):
        # temperature > 0 so the 50 trials of a type are not near-identical;
        # the value is pinned when the suite is frozen.
        self.client = llm_client
        self.model = model
        self.temperature = temperature

    def generate(self, base_task, perturbation_type: str,
                 sub_type: Optional[str] = None,
                 perturbation_id: Optional[str] = None) -> PerturbedTask:
        """Generate one perturbation of `base_task`."""
        if perturbation_type not in PERTURBATION_TYPES:
            raise ValueError("unknown perturbation type: %r (known: %s)"
                             % (perturbation_type,
                                ", ".join(sorted(PERTURBATION_TYPES))))
        spec = PERTURBATION_TYPES[perturbation_type]

        if perturbation_type == "prompt_injection":
            if sub_type is None:
                raise ValueError("prompt_injection requires a sub_type "
                                 "(one of %s)" % ", ".join(INJECTION_SUBTYPES))
            if sub_type not in spec["sub_prompts"]:
                raise ValueError("unknown injection sub_type: %r" % sub_type)
            prompt_template = spec["sub_prompts"][sub_type]
        else:
            sub_type = ""
            prompt_template = spec["prompt"]

        rendered = prompt_template.replace("{BASE_REQUEST_TEXT}",
                                           base_task.request_text)
        t0 = time.time()
        resp = self.client.generate(system=PERTURBATION_SYSTEM, user=rendered,
                                    model=self.model,
                                    temperature=self.temperature,
                                    max_tokens=4096)
        elapsed = (time.time() - t0) * 1000.0

        clean, note = _split_internal_note(resp.text, spec["note_prefix"])
        pid = perturbation_id or ("PERT-%s-%s"
                                  % (perturbation_type.upper(),
                                     base_task.task_id))
        return PerturbedTask(
            perturbation_id=pid,
            base_task_id=base_task.task_id,
            domain=getattr(base_task, "domain", ""),
            perturbation_type=perturbation_type,
            sub_type=sub_type,
            request_text=clean,
            internal_note=note,
            model=self.model,
            generation_ms=elapsed,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
        )

    def generate_batch(self, base_tasks: list, perturbation_type: str,
                       count: int) -> list:
        """Generate `count` perturbations of one type, cycling base_tasks.
        For prompt_injection the count is split across the three sub-types."""
        if not base_tasks:
            raise ValueError("base_tasks is empty")
        out = []
        if perturbation_type == "prompt_injection":
            dist = _subtype_distribution(count)
            n = 0
            for sub, sub_count in zip(INJECTION_SUBTYPES, dist):
                for _ in range(sub_count):
                    base = base_tasks[n % len(base_tasks)]
                    pid = "PERT-INJECTION-%s-%03d" % (sub.upper()[:3], n + 1)
                    out.append(self.generate(base, perturbation_type,
                                             sub_type=sub, perturbation_id=pid))
                    n += 1
        else:
            for i in range(count):
                base = base_tasks[i % len(base_tasks)]
                pid = "PERT-%s-%03d" % (perturbation_type.upper(), i + 1)
                out.append(self.generate(base, perturbation_type,
                                         perturbation_id=pid))
        return out

    def generate_suite(self, base_tasks: list,
                        per_type: int = TARGET_PER_TYPE) -> list:
        """Generate the full perturbation suite: every type at `per_type`
        trials. With the default this is 7 x 50 = 350 (PROTOCOL_LOCK Section
        1). NOTE: running this for real is Phase 5, gated on the deposit."""
        suite = []
        for ptype in PERTURBATION_TYPES:
            suite.extend(self.generate_batch(base_tasks, ptype, per_type))
        return suite
