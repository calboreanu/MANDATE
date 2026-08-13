"""
Tool Capability Registry for MANDATE pipeline.

Maps tool identifiers to their capabilities, risk weights, and metadata.
Used by ProcedureRole for capability determination and BindingRole for
risk-weighted scoring.

Replaces the heuristic tool_class → capability mapping with a proper
registry that supports:

- Explicit tool registration with capabilities
- Tool class defaults for unregistered tools
- Risk weight assignment per tool
- Registry construction from ToolSpec lists

Usage:
    from mandate.registry import ToolRegistry, ToolRegistryEntry

    # Build from mission input tools
    registry = ToolRegistry.from_tools(mission_input.available_tools)

    # Or register explicitly
    registry = ToolRegistry()
    registry.register(ToolRegistryEntry(
        tool_id="nmap",
        tool_class="RECON",
        capabilities=["network_enumeration", "service_discovery", "os_detection"],
        risk_weight=0.5,
    ))

    caps = registry.capabilities_for("nmap")
    weight = registry.risk_weight_for("nmap")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import ToolSpec


# ── Default Mappings ─────────────────────────────────────────────────

DEFAULT_CLASS_CAPABILITIES: Dict[str, List[str]] = {
    # Pentest domain
    "RECON": ["network_enumeration", "service_discovery"],
    "SCAN": ["vulnerability_scanning", "port_scanning"],
    "EXPLOIT": ["exploitation", "payload_delivery"],
    "ANALYSIS": ["data_analysis", "report_generation"],
    # IT Operations / Incident Response domain
    "DETECT": ["threat_detection", "log_analysis", "alert_triage"],
    "CONTAIN": ["network_isolation", "process_termination", "access_revocation"],
    "ERADICATE": ["malware_removal", "persistence_cleanup", "patch_application"],
    "RECOVER": ["system_restoration", "data_recovery", "service_validation"],
    # Intelligence domain
    "COLLECT": ["signal_collection", "data_acquisition"],
    "PROCESS": ["signal_processing", "data_normalization"],
    "ANALYZE": ["pattern_analysis", "correlation_analysis"],
    "DISSEMINATE": ["report_generation", "intelligence_distribution"],
}

DEFAULT_CLASS_RISK_WEIGHT: Dict[str, float] = {
    "RECON": 0.5,
    "SCAN": 1.5,
    "EXPLOIT": 3.0,
    "ANALYSIS": 0.5,
    "DETECT": 0.5,
    "CONTAIN": 2.0,
    "ERADICATE": 2.5,
    "RECOVER": 1.0,
    "COLLECT": 1.0,
    "PROCESS": 0.5,
    "ANALYZE": 0.5,
    "DISSEMINATE": 1.5,
}


# ── Registry Entry ───────────────────────────────────────────────────

@dataclass
class ToolRegistryEntry:
    """Registry entry describing a tool's capabilities and risk profile."""
    tool_id: str
    tool_class: str
    capabilities: List[str] = field(default_factory=list)
    risk_weight: float = 1.0
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


# ── Registry ─────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Registry mapping tools to their capabilities and risk profiles.

    Supports three resolution strategies (in priority order):
    1. Explicit registration — tool_id looked up directly
    2. Tool class defaults — tool_class used for unregistered tools
    3. Fallback — generic "tool_execution" capability
    """

    def __init__(self) -> None:
        self._entries: Dict[str, ToolRegistryEntry] = {}
        self._class_capabilities: Dict[str, List[str]] = dict(DEFAULT_CLASS_CAPABILITIES)
        self._class_risk_weights: Dict[str, float] = dict(DEFAULT_CLASS_RISK_WEIGHT)

    def register(self, entry: ToolRegistryEntry) -> None:
        """Register a tool with explicit capabilities."""
        self._entries[entry.tool_id] = entry

    def unregister(self, tool_id: str) -> bool:
        """Remove a tool from the registry. Returns True if it existed."""
        return self._entries.pop(tool_id, None) is not None

    def register_class_capabilities(
        self, tool_class: str, capabilities: List[str]
    ) -> None:
        """Override default capabilities for a tool class."""
        self._class_capabilities[tool_class] = list(capabilities)

    def register_class_risk_weight(self, tool_class: str, weight: float) -> None:
        """Override default risk weight for a tool class."""
        self._class_risk_weights[tool_class] = weight

    def capabilities_for(self, tool_id: str, tool_class: str = "") -> List[str]:
        """
        Resolve capabilities for a tool.

        Resolution order:
        1. Explicit entry for tool_id
        2. Class defaults for tool_class
        3. Fallback: ["tool_execution"]
        """
        if tool_id in self._entries:
            return list(self._entries[tool_id].capabilities)
        if tool_class and tool_class in self._class_capabilities:
            return list(self._class_capabilities[tool_class])
        return ["tool_execution"]

    def risk_weight_for(self, tool_id: str, tool_class: str = "") -> float:
        """
        Resolve risk weight for a tool.

        Resolution order:
        1. Explicit entry for tool_id
        2. Class defaults for tool_class
        3. Fallback: 1.0
        """
        if tool_id in self._entries:
            return self._entries[tool_id].risk_weight
        if tool_class and tool_class in self._class_risk_weights:
            return self._class_risk_weights[tool_class]
        return 1.0

    def get_entry(self, tool_id: str) -> Optional[ToolRegistryEntry]:
        """Get the explicit registry entry for a tool (None if not registered)."""
        return self._entries.get(tool_id)

    def registered_tools(self) -> List[str]:
        """Return list of explicitly registered tool IDs."""
        return sorted(self._entries.keys())

    def has_tool(self, tool_id: str) -> bool:
        """Check if a tool is explicitly registered."""
        return tool_id in self._entries

    @classmethod
    def from_tools(cls, tools: List[ToolSpec]) -> ToolRegistry:
        """
        Build a registry from a list of ToolSpec objects.

        Each tool gets default capabilities from its tool_class and
        a risk weight from the class defaults.
        """
        registry = cls()
        for tool in tools:
            caps = registry._class_capabilities.get(
                tool.tool_class, ["tool_execution"]
            )
            weight = registry._class_risk_weights.get(tool.tool_class, 1.0)
            registry.register(ToolRegistryEntry(
                tool_id=tool.tool_id,
                tool_class=tool.tool_class,
                capabilities=list(caps),
                risk_weight=weight,
                description=tool.description,
                parameters=dict(tool.parameters),
            ))
        return registry

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to a dict (for debugging/inspection)."""
        return {
            "entries": {
                tid: {
                    "tool_class": e.tool_class,
                    "capabilities": e.capabilities,
                    "risk_weight": e.risk_weight,
                    "description": e.description,
                }
                for tid, e in sorted(self._entries.items())
            },
            "class_capabilities": {
                k: v for k, v in sorted(self._class_capabilities.items())
            },
            "class_risk_weights": {
                k: v for k, v in sorted(self._class_risk_weights.items())
            },
        }

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"ToolRegistry({len(self._entries)} tools registered)"
