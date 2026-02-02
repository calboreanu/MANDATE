"""
MANDATE Constraint Grammar Parser and Validator

Implements the EBNF grammar from the MANDATE paper v1.0:

    constraint      ::= predicate | constraint AND constraint | constraint OR constraint | NOT constraint
    predicate       ::= field comparator value | field IN set | REQUIRES capability | FORBIDS action
    field           ::= identifier ('.' identifier)*
    comparator      ::= '==' | '!=' | '<' | '<=' | '>' | '>=' | 'CONTAINS' | 'MATCHES'
    value           ::= string | number | boolean | timestamp | duration
    set             ::= '[' value (',' value)* ']'
    capability      ::= identifier
    action          ::= identifier

This module provides:
- parse_constraint(): Parse a constraint string into an AST
- validate_constraint(): Check if a constraint string is syntactically valid
- evaluate_constraint(): Evaluate a constraint against a state dictionary
- ConstraintError: Exception for parse/validation errors

EVALUATION SEMANTICS
--------------------
The evaluation functions are provided for simple runtime checking but have limitations:

1. **Duration/Timestamp Comparison**: The parser recognizes ISO 8601 durations (PT4H) and 
   timestamps (2026-02-06T17:00:00-05:00) as distinct types, but evaluation treats them
   as raw strings. For proper temporal comparison, the state must provide pre-converted
   numeric values (e.g., seconds for durations, Unix timestamps for dates), or use
   a downstream policy engine (OPA/Rego, Cedar) with temporal support.

2. **State Model for REQUIRES/FORBIDS**:
   - `state["capabilities"]`: List of available capabilities (e.g., ["network_access", "file_read"])
   - `state["forbidden_actions"]`: List of actions that are forbidden by policy
   
   The predicate `REQUIRES cap` returns True if `cap` is in capabilities.
   The predicate `FORBIDS action` returns True if `action` IS in forbidden_actions.
   
   Typical usage: `REQUIRES network_access AND NOT FORBIDS external_api`
   - First part checks capability is available
   - Second part checks the action is NOT forbidden (allowed)

3. **MATCHES Security Note**: The MATCHES comparator uses Python's re.match() with
   user-provided patterns. If constraint strings come from untrusted sources, there
   is potential for ReDoS (Regular Expression Denial of Service) attacks via
   catastrophic backtracking patterns. For production use:
   - Only use curated/trusted constraint patterns
   - Consider pattern length limits
   - Consider using RE2-compatible patterns or a RE2 engine

For production deployments requiring deterministic constraint checking, translate
MANDATE constraints to a policy engine (OPA/Rego, Cedar) as described in the paper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ConstraintError(Exception):
    """Raised when constraint parsing or validation fails."""
    pass


class EvaluationError(Exception):
    """Raised when constraint evaluation fails due to type mismatch or missing data."""
    pass


class Comparator(Enum):
    EQ = "=="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    CONTAINS = "CONTAINS"
    MATCHES = "MATCHES"


class BoolOp(Enum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


# AST Node Types
@dataclass
class FieldRef:
    """A dotted field reference like 'execution.duration' or 'risk.score'."""
    parts: List[str]
    
    def __str__(self) -> str:
        return ".".join(self.parts)


@dataclass
class LiteralValue:
    """A literal value: string, number, boolean, timestamp, or duration."""
    value: Any
    value_type: str  # 'string', 'number', 'boolean', 'timestamp', 'duration'
    
    def __str__(self) -> str:
        if self.value_type == "string":
            return f"'{self.value}'"
        return str(self.value)


@dataclass
class SetValue:
    """A set of values like ['UNCLASSIFIED', 'CUI']."""
    values: List[LiteralValue]
    
    def __str__(self) -> str:
        return "[" + ", ".join(str(v) for v in self.values) + "]"


@dataclass
class ComparisonPredicate:
    """A comparison like 'execution.duration <= PT4H'."""
    field: FieldRef
    comparator: Comparator
    value: LiteralValue
    
    def __str__(self) -> str:
        return f"{self.field} {self.comparator.value} {self.value}"


@dataclass
class InPredicate:
    """A set membership test like 'data.classification IN [...]'."""
    field: FieldRef
    values: SetValue
    
    def __str__(self) -> str:
        return f"{self.field} IN {self.values}"


@dataclass
class RequiresPredicate:
    """A capability requirement like 'REQUIRES network_access'."""
    capability: str
    
    def __str__(self) -> str:
        return f"REQUIRES {self.capability}"


@dataclass
class ForbidsPredicate:
    """
    An action prohibition like 'FORBIDS external_api'.
    
    Semantics: Returns True if the action IS in the forbidden_actions list.
    Typical usage with NOT: "NOT FORBIDS external_api" = action is allowed.
    """
    action: str
    
    def __str__(self) -> str:
        return f"FORBIDS {self.action}"


Predicate = Union[ComparisonPredicate, InPredicate, RequiresPredicate, ForbidsPredicate]


@dataclass
class NotExpr:
    """Logical NOT."""
    operand: "Constraint"
    
    def __str__(self) -> str:
        return f"NOT ({self.operand})"


@dataclass
class AndExpr:
    """Logical AND."""
    left: "Constraint"
    right: "Constraint"
    
    def __str__(self) -> str:
        return f"({self.left}) AND ({self.right})"


@dataclass
class OrExpr:
    """Logical OR."""
    left: "Constraint"
    right: "Constraint"
    
    def __str__(self) -> str:
        return f"({self.left}) OR ({self.right})"


Constraint = Union[Predicate, NotExpr, AndExpr, OrExpr]


class ConstraintLexer:
    """Tokenizes a constraint string."""
    
    TOKEN_PATTERNS = [
        (r'\s+', None),  # Skip whitespace
        (r'AND\b', 'AND'),
        (r'OR\b', 'OR'),
        (r'NOT\b', 'NOT'),
        (r'IN\b', 'IN'),
        (r'REQUIRES\b', 'REQUIRES'),
        (r'FORBIDS\b', 'FORBIDS'),
        (r'CONTAINS\b', 'CONTAINS'),
        (r'MATCHES\b', 'MATCHES'),
        (r'==', 'EQ'),
        (r'!=', 'NE'),
        (r'<=', 'LE'),
        (r'>=', 'GE'),
        (r'<', 'LT'),
        (r'>', 'GT'),
        (r'\[', 'LBRACKET'),
        (r'\]', 'RBRACKET'),
        (r'\(', 'LPAREN'),
        (r'\)', 'RPAREN'),
        (r',', 'COMMA'),
        (r"'[^']*'", 'STRING'),
        (r'"[^"]*"', 'STRING'),
        (r'true\b', 'TRUE'),
        (r'false\b', 'FALSE'),
        (r'P(?:T?\d+[YMWDHMS])+', 'DURATION'),  # ISO 8601 duration
        (r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?', 'TIMESTAMP'),
        (r'-?\d+\.\d+', 'FLOAT'),
        (r'-?\d+', 'INT'),
        (r'[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*', 'IDENTIFIER'),
    ]
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.tokens: List[tuple] = []
        self._tokenize()
    
    def _tokenize(self) -> None:
        while self.pos < len(self.text):
            match = None
            for pattern, token_type in self.TOKEN_PATTERNS:
                regex = re.compile(pattern)
                match = regex.match(self.text, self.pos)
                if match:
                    if token_type:  # Skip None (whitespace)
                        self.tokens.append((token_type, match.group()))
                    self.pos = match.end()
                    break
            if not match:
                raise ConstraintError(f"Unexpected character at position {self.pos}: '{self.text[self.pos]}'")
        self.tokens.append(('EOF', ''))


class ConstraintParser:
    """Recursive descent parser for constraint grammar."""
    
    def __init__(self, tokens: List[tuple]):
        self.tokens = tokens
        self.pos = 0
    
    def current(self) -> tuple:
        return self.tokens[self.pos]
    
    def peek(self, offset: int = 0) -> tuple:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return ('EOF', '')
    
    def consume(self, expected: Optional[str] = None) -> tuple:
        token = self.current()
        if expected and token[0] != expected:
            raise ConstraintError(f"Expected {expected}, got {token[0]} ('{token[1]}')")
        self.pos += 1
        return token
    
    def parse(self) -> Constraint:
        result = self.parse_or_expr()
        if self.current()[0] != 'EOF':
            raise ConstraintError(f"Unexpected token after expression: {self.current()}")
        return result
    
    def parse_or_expr(self) -> Constraint:
        left = self.parse_and_expr()
        while self.current()[0] == 'OR':
            self.consume('OR')
            right = self.parse_and_expr()
            left = OrExpr(left, right)
        return left
    
    def parse_and_expr(self) -> Constraint:
        left = self.parse_not_expr()
        while self.current()[0] == 'AND':
            self.consume('AND')
            right = self.parse_not_expr()
            left = AndExpr(left, right)
        return left
    
    def parse_not_expr(self) -> Constraint:
        if self.current()[0] == 'NOT':
            self.consume('NOT')
            operand = self.parse_not_expr()
            return NotExpr(operand)
        return self.parse_primary()
    
    def parse_primary(self) -> Constraint:
        if self.current()[0] == 'LPAREN':
            self.consume('LPAREN')
            expr = self.parse_or_expr()
            self.consume('RPAREN')
            return expr
        
        if self.current()[0] == 'REQUIRES':
            self.consume('REQUIRES')
            cap = self.consume('IDENTIFIER')
            return RequiresPredicate(cap[1])
        
        if self.current()[0] == 'FORBIDS':
            self.consume('FORBIDS')
            action = self.consume('IDENTIFIER')
            return ForbidsPredicate(action[1])
        
        # Must be a field-based predicate
        return self.parse_field_predicate()
    
    def parse_field_predicate(self) -> Predicate:
        field = self.parse_field()
        
        if self.current()[0] == 'IN':
            self.consume('IN')
            values = self.parse_set()
            return InPredicate(field, values)
        
        comparator = self.parse_comparator()
        value = self.parse_value()
        return ComparisonPredicate(field, comparator, value)
    
    def parse_field(self) -> FieldRef:
        token = self.consume('IDENTIFIER')
        parts = token[1].split('.')
        return FieldRef(parts)
    
    def parse_comparator(self) -> Comparator:
        token = self.current()
        mapping = {
            'EQ': Comparator.EQ,
            'NE': Comparator.NE,
            'LT': Comparator.LT,
            'LE': Comparator.LE,
            'GT': Comparator.GT,
            'GE': Comparator.GE,
            'CONTAINS': Comparator.CONTAINS,
            'MATCHES': Comparator.MATCHES,
        }
        if token[0] in mapping:
            self.consume()
            return mapping[token[0]]
        raise ConstraintError(f"Expected comparator, got {token[0]}")
    
    def parse_value(self) -> LiteralValue:
        token = self.current()
        
        if token[0] == 'STRING':
            self.consume()
            # Strip quotes
            val = token[1][1:-1]
            return LiteralValue(val, 'string')
        
        if token[0] == 'INT':
            self.consume()
            return LiteralValue(int(token[1]), 'number')
        
        if token[0] == 'FLOAT':
            self.consume()
            return LiteralValue(float(token[1]), 'number')
        
        if token[0] == 'TRUE':
            self.consume()
            return LiteralValue(True, 'boolean')
        
        if token[0] == 'FALSE':
            self.consume()
            return LiteralValue(False, 'boolean')
        
        if token[0] == 'DURATION':
            self.consume()
            return LiteralValue(token[1], 'duration')
        
        if token[0] == 'TIMESTAMP':
            self.consume()
            return LiteralValue(token[1], 'timestamp')
        
        if token[0] == 'IDENTIFIER':
            # Treat as string (e.g., enum values like HIGH, MEDIUM, LOW)
            self.consume()
            return LiteralValue(token[1], 'string')
        
        raise ConstraintError(f"Expected value, got {token[0]}")
    
    def parse_set(self) -> SetValue:
        self.consume('LBRACKET')
        values = []
        
        if self.current()[0] != 'RBRACKET':
            values.append(self.parse_value())
            while self.current()[0] == 'COMMA':
                self.consume('COMMA')
                values.append(self.parse_value())
        
        self.consume('RBRACKET')
        return SetValue(values)


def parse_constraint(text: str) -> Constraint:
    """
    Parse a constraint string into an AST.
    
    Args:
        text: The constraint string to parse
        
    Returns:
        A Constraint AST node
        
    Raises:
        ConstraintError: If the constraint is syntactically invalid
    """
    lexer = ConstraintLexer(text)
    parser = ConstraintParser(lexer.tokens)
    return parser.parse()


def validate_constraint(text: str) -> bool:
    """
    Check if a constraint string is syntactically valid.
    
    Args:
        text: The constraint string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parse_constraint(text)
        return True
    except ConstraintError:
        return False


def _get_field_value(state: Dict[str, Any], field: FieldRef) -> Any:
    """Navigate a dotted field path in a state dictionary."""
    current = state
    for part in field.parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(f"Field '{field}' not found in state")
    return current


def _compare(left: Any, comparator: Comparator, right: Any, value_type: str) -> bool:
    """
    Evaluate a comparison operation with type awareness.
    
    Args:
        left: Left operand (from state)
        comparator: Comparison operator
        right: Right operand (from constraint literal)
        value_type: Type of the constraint literal ('string', 'number', 'boolean', 'duration', 'timestamp')
        
    Returns:
        Boolean result of comparison
        
    Raises:
        EvaluationError: If types are incompatible for comparison
    """
    # For duration/timestamp, warn if types don't match
    if value_type in ('duration', 'timestamp'):
        if not isinstance(left, (int, float, str)):
            raise EvaluationError(
                f"Cannot compare {value_type} '{right}' with state value of type {type(left).__name__}. "
                f"For {value_type} comparison, provide numeric values in state (e.g., seconds for duration, "
                f"Unix timestamp for dates) or use a policy engine with temporal support."
            )
        # If left is also a string, do string comparison (may not be semantically correct)
        # If left is numeric, we can't compare to string duration/timestamp without parsing
        if isinstance(left, (int, float)) and isinstance(right, str):
            raise EvaluationError(
                f"Type mismatch: state has numeric value {left} but constraint has {value_type} '{right}'. "
                f"Either provide the constraint as a number, or provide state value as a string."
            )
    
    if comparator == Comparator.EQ:
        return left == right
    elif comparator == Comparator.NE:
        return left != right
    elif comparator == Comparator.LT:
        return left < right
    elif comparator == Comparator.LE:
        return left <= right
    elif comparator == Comparator.GT:
        return left > right
    elif comparator == Comparator.GE:
        return left >= right
    elif comparator == Comparator.CONTAINS:
        try:
            return right in left
        except TypeError:
            raise EvaluationError(
                f"CONTAINS requires an iterable (list, string, etc.) on the left side, "
                f"but got {type(left).__name__}: {left!r}"
            )
    elif comparator == Comparator.MATCHES:
        # Security note: patterns should be from trusted sources to avoid ReDoS
        return bool(re.match(right, str(left)))
    return False


def evaluate_constraint(constraint: Constraint, state: Dict[str, Any]) -> bool:
    """
    Evaluate a constraint against a state dictionary.
    
    Args:
        constraint: The parsed constraint AST
        state: A dictionary representing the current state/context.
               Expected keys for capability/action predicates:
               - 'capabilities': List[str] of available capabilities
               - 'forbidden_actions': List[str] of actions forbidden by policy
               
    Returns:
        True if the constraint is satisfied, False otherwise
        
    Raises:
        KeyError: If a required field is not found in state
        EvaluationError: If types are incompatible for comparison
        
    Note:
        For duration/timestamp comparisons, the state should provide values
        in a comparable format (both strings or both numbers). This evaluator
        does NOT parse ISO 8601 durations/timestamps. For production use,
        translate constraints to a policy engine (OPA/Rego, Cedar).
    """
    if isinstance(constraint, ComparisonPredicate):
        field_value = _get_field_value(state, constraint.field)
        return _compare(
            field_value, 
            constraint.comparator, 
            constraint.value.value,
            constraint.value.value_type
        )
    
    elif isinstance(constraint, InPredicate):
        field_value = _get_field_value(state, constraint.field)
        allowed = [v.value for v in constraint.values.values]
        return field_value in allowed
    
    elif isinstance(constraint, RequiresPredicate):
        # REQUIRES capability: True if capability is available
        capabilities = state.get('capabilities', [])
        return constraint.capability in capabilities
    
    elif isinstance(constraint, ForbidsPredicate):
        # FORBIDS action: True if action IS in the forbidden list
        # Typical usage: "NOT FORBIDS x" = action x is allowed (not forbidden)
        forbidden = state.get('forbidden_actions', [])
        return constraint.action in forbidden
    
    elif isinstance(constraint, NotExpr):
        return not evaluate_constraint(constraint.operand, state)
    
    elif isinstance(constraint, AndExpr):
        return (evaluate_constraint(constraint.left, state) and 
                evaluate_constraint(constraint.right, state))
    
    elif isinstance(constraint, OrExpr):
        return (evaluate_constraint(constraint.left, state) or 
                evaluate_constraint(constraint.right, state))
    
    raise ConstraintError(f"Unknown constraint type: {type(constraint)}")


def evaluate_constraint_string(text: str, state: Dict[str, Any]) -> bool:
    """
    Parse and evaluate a constraint string against a state dictionary.
    
    Convenience function combining parse_constraint and evaluate_constraint.
    
    Args:
        text: The constraint string
        state: The state dictionary to evaluate against
        
    Returns:
        True if the constraint is satisfied, False otherwise
        
    Raises:
        ConstraintError: If the constraint is syntactically invalid
        KeyError: If a required field is not found in state
        EvaluationError: If types are incompatible for comparison
    """
    ast = parse_constraint(text)
    return evaluate_constraint(ast, state)
