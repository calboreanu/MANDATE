"""Shared data models for the AEGIS execution chain."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class ToolBinding:
    """A tool bound to a TTP for a specific task."""
    tool_id: str
    tool_class: str          # RECON, SCAN, EXPLOIT, ANALYSIS
    ttp_id: str              # MITRE ATT&CK ID
    ttp_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    definition_hash: str = ""


@dataclass
class TaskNode:
    """A single node in a task DAG."""
    node_id: int
    name: str
    depends_on: List[int] = field(default_factory=list)
    tool_bindings: List[ToolBinding] = field(default_factory=list)
    parallel_group: Optional[int] = None


@dataclass
class CourseOfAction:
    """A course of action (COA) with its task DAG and risk profile."""
    coa_id: str
    name: str
    risk_level: str          # LOW, MEDIUM, HIGH
    description: str
    task_nodes: List[TaskNode] = field(default_factory=list)
    achieves_minimum: bool = True
    achieves_target: bool = False
    roe_compliant: bool = True


@dataclass
class MissionConfig:
    """Complete mission configuration for the Normal Mission scenario."""
    mission_id: str
    directive: str
    roe: List[str]
    targets: List[str]
    time_window: str
    authorization_ref: str
    anchor_intent: str
    anchor_minimum: str
    anchor_target: str
    constraints: List[str]
    coas: List[CourseOfAction] = field(default_factory=list)
    policy_id: str = ""
    policy_version: str = ""


@dataclass
class StepOutput:
    """A single step in the execution chain, for structured output."""
    step_num: int
    phase: str               # PRE-MISSION, AUTHORIZATION, EXECUTION, POST-MISSION
    framework: str           # MANDATE, LATTICE, TRACE
    title: str
    detail: str
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_num,
            "phase": self.phase,
            "framework": self.framework,
            "title": self.title,
            "detail": self.detail,
            "artifacts": self.artifacts,
        }


@dataclass
class ChainResult:
    """Final result of the full execution chain."""
    ok: bool
    steps: List[StepOutput] = field(default_factory=list)
    mandate_path: Optional[Path] = None
    policy_path: Optional[Path] = None
    bundle_path: Optional[Path] = None
    audit_path: Optional[Path] = None
    evidence_path: Optional[Path] = None
    summary: Dict[str, Any] = field(default_factory=dict)
