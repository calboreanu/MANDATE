"""
MANDATE Constraint Policy Translators

Translates parsed MANDATE constraint ASTs into external policy languages
for deterministic enforcement at runtime.

Supported targets:
- OPA/Rego  (Open Policy Agent)
- Cedar     (Amazon Cedar)

Each translator accepts either raw constraint strings or parsed AST nodes
and produces idiomatic policy source in the target language.
"""

from mandate.translators.rego import (
    translate_to_rego,
    translate_constraint_to_rego,
)
from mandate.translators.cedar import (
    translate_to_cedar,
    translate_constraint_to_cedar,
)

__all__ = [
    "translate_to_rego",
    "translate_constraint_to_rego",
    "translate_to_cedar",
    "translate_constraint_to_cedar",
]
