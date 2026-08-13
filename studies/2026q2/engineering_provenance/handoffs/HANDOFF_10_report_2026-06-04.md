# Handoff 10 Report: Perturbation Suite

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** ~2 hours 10 minutes including CLI patches and rerun

## Verdict

PROCEED

## Evidence

- corpus_freeze_v1 tag present: yes
- base task count: 30
- perturbations generated: 350/350
- per-type counts: surface_noise=50, ambiguity_injection=50, contradictory_constraints=50, prompt_injection=50, missing_required_field=50, out_of_distribution_input=50, length_perturbation=50
- injection subtypes: direct_command=17, role_play=17, hidden_instruction=16
- Anthropic model used: `claude-opus-4-6`
- Anthropic input tokens (total): 165,254
- Anthropic output tokens (total): 172,894
- estimated API cost (USD): $3.089172

## Verification Command

```text
total: 350
by type: {'surface_noise': 50, 'ambiguity_injection': 50, 'contradictory_constraints': 50, 'prompt_injection': 50, 'missing_required_field': 50, 'out_of_distribution_input': 50, 'length_perturbation': 50}
injection subtypes: {'direct_command': 17, 'role_play': 17, 'hidden_instruction': 16}
sanity OK
```

## Output Locations

- `06_perturbations/perturbation_suite.jsonl`

## Anything the PI must decide before proceeding

- Circulate 30 percent (105 perturbations) to SMEs for the spot-check if the SME-review path is reinstated. Under the current SME-skip deviation, this remains a documented caveat.

## Deviations from this handoff

- The CLI path needed apparatus fixes before the suite could run: `db46035`, `bc8af1b`, `021c5f5`, and `b334c5a` patched the generator constructor wiring, base-task adapter, regression coverage, and frozen output labels. After those fixes, the final H10 command completed successfully and the suite passed the handoff sanity checks.
