"""
Shared data models for the MANDATE 1+6 pipeline.

Defines:
- MissionInput: Raw mission specification (structured or semi-structured)
- PipelineState: Accumulator passed through pipeline roles
- RoleResult: Output of each role execution
- PipelineConfig: Pipeline behavior configuration
- COASpec: Course of action specification within the pipeline
- TaskNodeSpec: Task DAG node specification
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .domain import DomainProfile, RiskModelConfig
    from .registry import ToolRegistry


class GapType(Enum):
    """Gap types per gap-report.schema.json."""
    UNDEFINED_MINIMUM = "UNDEFINED_MINIMUM"
    UNDEFINED_TARGET = "UNDEFINED_TARGET"
    UNKNOWN_PATTERN = "UNKNOWN_PATTERN"
    MISSING_TTP = "MISSING_TTP"
    MISSING_CAPABILITY = "MISSING_CAPABILITY"
    UNASSESSABLE_RISK = "UNASSESSABLE_RISK"


class RiskLevel(Enum):
    """Risk scoring levels per mandate-as-code schema."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNASSESSABLE = "UNASSESSABLE"


class ConfidenceLevel(Enum):
    """Confidence levels for risk assessment."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RoleStatus(Enum):
    """Status of a role execution."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ── Input Models ──────────────────────────────────────────────────────

@dataclass
class ToolSpec:
    """Tool specification within a mission input."""
    tool_id: str
    tool_class: str           # RECON, SCAN, EXPLOIT, ANALYSIS
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MissionInput:
    """
    Raw mission specification fed into the pipeline.

    This can be constructed manually (structured) or parsed from
    a semi-structured description.  All fields except mission_id and
    intent are optional — roles fill in defaults/derivations.
    """
    mission_id: str
    intent: str                          # Free-text mission intent
    scope: List[str] = field(default_factory=list)  # Target scope items
    time_limit: str = ""                 # e.g. "PT4H"
    constraints: List[str] = field(default_factory=list)  # EBNF constraint strings
    minimum_outcome: str = ""            # Minimum viable outcome description
    target_outcome: str = ""             # Ideal/target outcome description
    available_tools: List[ToolSpec] = field(default_factory=list)
    risk_tolerance: Optional[str] = None  # "LOW", "MEDIUM", "HIGH"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MissionInput:
        """Construct from a plain dict (e.g. loaded from JSON)."""
        tools = [
            ToolSpec(**t) if isinstance(t, dict) else t
            for t in d.get("available_tools", [])
        ]
        return cls(
            mission_id=d["mission_id"],
            intent=d["intent"],
            scope=d.get("scope", []),
            time_limit=d.get("time_limit", ""),
            constraints=d.get("constraints", []),
            minimum_outcome=d.get("minimum_outcome", ""),
            target_outcome=d.get("target_outcome", ""),
            available_tools=tools,
            risk_tolerance=d.get("risk_tolerance"),
            metadata=d.get("metadata", {}),
        )


# ── Pipeline Internal Models ─────────────────────────────────────────

@dataclass
class TaskNodeSpec:
    """A node in a COA task DAG."""
    node_id: str
    name: str
    description: str = ""
    depends_on: List[str] = field(default_factory=list)
    tool_ids: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """Risk assessment for a COA."""
    score: RiskLevel
    confidence_min: ConfidenceLevel
    confidence_target: ConfidenceLevel
    primary_factor: str


@dataclass
class COASpec:
    """Course of action built by the pipeline."""
    coa_id: str
    approach: str                # Description of the approach
    task_nodes: List[TaskNodeSpec] = field(default_factory=list)
    edges: List[Dict[str, str]] = field(default_factory=list)
    risk_assessment: Optional[RiskAssessment] = None
    off_nominal_triggers: List[str] = field(default_factory=list)
    procedures: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


@dataclass
class GapSpec:
    """
    A specification gap detected during pipeline execution.

    Corresponds to the gap-report.schema.json structure.
    Roles create GapSpec instances when they detect missing or
    ambiguous specification elements.
    """
    gap_type: GapType
    detected_by: str          # Role name: Intake, Interpreter, etc.
    pipeline_stage: int       # 1-6
    field_or_task: str        # Which field/task has the gap
    reason: str               # Human-readable explanation
    action_required: str      # What needs to happen to close the gap
    responsible_party: str = "Mission Author"
    complexity: str = "LOW"   # LOW, MEDIUM, HIGH
    completion_percentage: int = 0
    blocking: bool = False
    partial_spec_available: bool = False
    input_reference: str = "mission_input"


@dataclass
class Recommendation:
    """Pipeline recommendation for COA selection."""
    primary_coa: str
    fallback_sequence: List[str]
    rationale: str


@dataclass
class PipelineState:
    """
    Accumulator passed through pipeline roles.

    Each role reads what it needs and writes its outputs here.
    The Validation role assembles the final artifact from this state.
    """
    # From input
    mission_input: Optional[MissionInput] = None

    # Built by Intake
    mission_id: str = ""
    timestamp: str = ""

    # Built by Interpreter
    anchor_intent: str = ""
    anchor_minimum: Dict[str, Any] = field(default_factory=dict)
    anchor_target: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    risk_tolerance: Optional[Dict[str, Any]] = None
    anchor_hash: str = ""

    # Built by Decomposition
    coas: List[COASpec] = field(default_factory=list)

    # Built by Procedure (modifies COASpec in-place)
    # — procedures and capabilities added to each COASpec

    # Built by Binding
    recommendation: Optional[Recommendation] = None

    # Built by Validation
    trace_entry_hashes: List[str] = field(default_factory=list)
    chain_hash: str = ""

    # Gaps detected during pipeline (any role can append)
    gaps: List[GapSpec] = field(default_factory=list)

    # Errors accumulated during pipeline
    errors: List[str] = field(default_factory=list)


# ── Role Output ──────────────────────────────────────────────────────

@dataclass
class RoleResult:
    """Output of a single role execution."""
    role_name: str
    status: RoleStatus
    message: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    trace_entry_hash: str = ""

    @property
    def ok(self) -> bool:
        return self.status == RoleStatus.SUCCESS


# ── Configuration ────────────────────────────────────────────────────

@dataclass
class PipelineConfig:
    """Configuration for pipeline behavior."""
    strict: bool = True          # Fail on first validation error
    verbose: bool = False        # Emit detailed trace output
    output_dir: str = ""         # Where to write artifacts
    version: str = "1.0"         # Artifact version string
    emit_gaps: bool = False      # Legacy CLI-display flag; gap evidence is always retained

    # Phase 5: Domain customization (v1.4.0)
    domain_profile: Optional[DomainProfile] = None     # Domain-specific COA templates
    risk_model: Optional[RiskModelConfig] = None        # Risk scoring overrides
    tool_registry: Optional[ToolRegistry] = None        # Tool capability registry
