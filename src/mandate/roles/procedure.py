"""
Role 3: Procedure

For each COA's task nodes:
- Determines required capabilities
- Generates off-nominal triggers (valid EBNF constraint grammar)
- Builds procedure steps from task DAG topological order
- Adds tool binding placeholders

Off-nominal triggers must be valid constraint grammar strings that
pass mandate.constraints.validate_constraint().
"""
from __future__ import annotations

from typing import Any, Dict, List, Set

from ..constraints import validate_constraint
from ..models import COASpec, PipelineState, RoleResult, TaskNodeSpec
from .base import Role


# ── Standard trigger templates ────────────────────────────────────────
# These are valid EBNF constraint grammar strings

SCOPE_VIOLATION_TRIGGER = "target.scope_violations > 0"
RATE_LIMIT_TRIGGER = "execution.rate > 100"
DETECTION_TRIGGER = "detection.signature_count > 0"
DURATION_TRIGGER = "execution.duration > 0"
UNAUTHORIZED_TRIGGER = "execution.unauthorized_attempts > 0"


# Tool-class to capability mapping (fallback when no registry is configured)
TOOL_CLASS_CAPABILITIES = {
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

# Risk-based trigger selection
RISK_TRIGGER_MAP = {
    "LOW": [SCOPE_VIOLATION_TRIGGER, RATE_LIMIT_TRIGGER],
    "MEDIUM": [SCOPE_VIOLATION_TRIGGER, RATE_LIMIT_TRIGGER, DETECTION_TRIGGER],
    "HIGH": [
        SCOPE_VIOLATION_TRIGGER,
        RATE_LIMIT_TRIGGER,
        DETECTION_TRIGGER,
        UNAUTHORIZED_TRIGGER,
    ],
}


class ProcedureRole(Role):
    """Procedure role: tool binding and trigger generation."""

    ROLE_NAME = "Procedure"

    def execute(self, state: PipelineState) -> RoleResult:
        if not state.coas:
            return self._fail("No COAs in state — Decomposition must run first")

        total_procedures = 0
        total_triggers = 0

        for coa in state.coas:
            # Generate procedures from topological order
            procedures = self._generate_procedures(coa)
            coa.procedures = procedures
            total_procedures += len(procedures)

            # Determine capabilities needed
            capabilities = self._determine_capabilities(coa)
            coa.capabilities = capabilities

            # Generate off-nominal triggers based on COA risk profile
            triggers = self._generate_triggers(coa)
            coa.off_nominal_triggers = triggers
            total_triggers += len(triggers)

        return self._success(
            f"Generated {total_procedures} procedures, {total_triggers} triggers across {len(state.coas)} COA(s)",
            procedure_count=total_procedures,
            trigger_count=total_triggers,
        )

    def _generate_procedures(self, coa: COASpec) -> List[str]:
        """
        Generate procedure descriptions from task DAG topological order.

        Returns list of human-readable procedure step strings.
        """
        # Topological sort
        ordered = self._topological_sort(coa.task_nodes, coa.edges)

        procedures = []
        for i, node in enumerate(ordered, 1):
            tools_str = ""
            if node.tool_ids:
                tools_str = f" using {', '.join(node.tool_ids)}"
            procedures.append(
                f"Step {i}: {node.name}{tools_str}"
            )

        return procedures

    def _determine_capabilities(self, coa: COASpec) -> List[str]:
        """
        Determine unique capabilities required by a COA's tools.

        Uses ToolRegistry if configured on pipeline config, otherwise
        falls back to tool_class heuristic matching.
        """
        capabilities: Set[str] = set()
        registry = self.config.tool_registry

        if registry:
            # Use registry for capability lookup
            for node in coa.task_nodes:
                for tool_id in node.tool_ids:
                    caps = registry.capabilities_for(tool_id)
                    capabilities.update(caps)
        else:
            # Fallback: heuristic matching by tool class name
            for node in coa.task_nodes:
                for tool_id in node.tool_ids:
                    matched = False
                    for tool_class, caps in TOOL_CLASS_CAPABILITIES.items():
                        if tool_class.lower() in tool_id.lower():
                            capabilities.update(caps)
                            matched = True
                            break
                    if not matched:
                        # Check domain profile capabilities if available
                        profile = self.config.domain_profile
                        if profile and profile.tool_class_capabilities:
                            for tc, caps in profile.tool_class_capabilities.items():
                                if tc.lower() in tool_id.lower():
                                    capabilities.update(caps)
                                    matched = True
                                    break

        # Default capabilities if none matched
        if not capabilities:
            for node in coa.task_nodes:
                if node.tool_ids:
                    capabilities.add("tool_execution")

        return sorted(capabilities)

    def _generate_triggers(self, coa: COASpec) -> List[str]:
        """
        Generate off-nominal triggers for a COA.

        All triggers must be valid EBNF constraint grammar.
        """
        # Determine risk level from COA analysis
        risk = self._assess_coa_risk(coa)
        triggers = list(RISK_TRIGGER_MAP.get(risk, RISK_TRIGGER_MAP["MEDIUM"]))

        # Validate all triggers
        valid_triggers = []
        for trigger in triggers:
            if validate_constraint(trigger):
                valid_triggers.append(trigger)

        return valid_triggers

    def _assess_coa_risk(self, coa: COASpec) -> str:
        """Simple heuristic risk assessment based on tool types and DAG depth."""
        has_exploit = False
        has_parallel_risk = False

        for node in coa.task_nodes:
            for tid in node.tool_ids:
                if any(kw in tid.lower() for kw in ("exploit", "metasploit", "payload")):
                    has_exploit = True
            if node.risk_factors:
                if "parallel_exploitation" in node.risk_factors:
                    has_parallel_risk = True

        if has_exploit and has_parallel_risk:
            return "HIGH"
        elif has_exploit:
            return "MEDIUM"
        return "LOW"

    def _topological_sort(
        self,
        nodes: List[TaskNodeSpec],
        edges: List[Dict[str, str]],
    ) -> List[TaskNodeSpec]:
        """Sort task nodes in dependency order."""
        node_map = {n.node_id: n for n in nodes}
        in_degree = {n.node_id: 0 for n in nodes}

        for edge in edges:
            to_id = edge["to"]
            if to_id in in_degree:
                in_degree[to_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            nid = queue.pop(0)
            result.append(node_map[nid])
            for edge in edges:
                if edge["from"] == nid:
                    to_id = edge["to"]
                    in_degree[to_id] -= 1
                    if in_degree[to_id] == 0:
                        queue.append(to_id)

        # Append any remaining nodes (shouldn't happen in valid DAG)
        seen = {n.node_id for n in result}
        for node in nodes:
            if node.node_id not in seen:
                result.append(node)

        return result
