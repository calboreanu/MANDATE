"""
Role 2: Decomposition

Generates courses of action (COAs) from the anchor and mission input.

Deterministic, rule-based COA generation:
- Analyzes scope breadth and tool availability
- Generates 1-3 COAs with increasing aggressiveness
- Builds task DAGs with dependency edges
- Validates DAG acyclicity

When a DomainProfile is configured, phase templates replace the
hardcoded pentest heuristics, enabling domain-specific COA structures
(incident response, intelligence operations, etc.).

This role does NOT use LLM generation — it uses template-based
heuristics to produce valid COA structures. LLM-based COA generation
can be layered on top by providing pre-built COASpecs in MissionInput.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from ..models import (
    COASpec,
    GapSpec,
    GapType,
    MissionInput,
    PipelineState,
    RoleResult,
    TaskNodeSpec,
    ToolSpec,
)
from .base import Role


# ── Tool classification ───────────────────────────────────────────────

TOOL_CLASS_ORDER = ["RECON", "SCAN", "EXPLOIT", "ANALYSIS"]
TOOL_CLASS_RISK = {
    "RECON": "LOW",
    "SCAN": "MEDIUM",
    "EXPLOIT": "HIGH",
    "ANALYSIS": "LOW",
}


class DecompositionRole(Role):
    """Decomposition role: COA generation and task DAG construction."""

    ROLE_NAME = "Decomposition"

    def execute(self, state: PipelineState) -> RoleResult:
        mi = state.mission_input
        if mi is None:
            return self._fail("No MissionInput in state")

        tools = mi.available_tools
        scope = mi.scope
        gaps_before = len(state.gaps)

        # ── Detect MISSING_CAPABILITY gaps ─────────────────────────
        self._detect_capability_gaps(state, tools, scope)

        # ── Build COAs based on tool availability ─────────────────
        coas = self._generate_coas(mi, tools, scope)

        if not coas:
            return self._fail("Could not generate any courses of action")

        state.coas = coas

        new_gaps = len(state.gaps) - gaps_before
        msg = f"Generated {len(coas)} COA(s)"
        if new_gaps:
            msg += f" ({new_gaps} gap(s) detected)"

        return self._success(
            msg,
            coa_count=len(coas),
            coa_ids=[c.coa_id for c in coas],
            gaps_detected=new_gaps,
        )

    def _detect_capability_gaps(
        self,
        state: PipelineState,
        tools: List[ToolSpec],
        scope: List[str],
    ) -> None:
        """Detect MISSING_CAPABILITY and UNKNOWN_PATTERN gaps."""
        if not tools:
            state.gaps.append(GapSpec(
                gap_type=GapType.MISSING_CAPABILITY,
                detected_by=self.ROLE_NAME,
                pipeline_stage=3,
                field_or_task="available_tools",
                reason="No tools specified in mission input. COA generation "
                       "limited to manual assessment approach.",
                action_required="Provide available_tools with tool_id, tool_class, "
                                "and description for each available tool.",
                responsible_party="Mission Author",
                complexity="MEDIUM",
                completion_percentage=10,
                blocking=False,
                partial_spec_available=False,
            ))
        else:
            # Check for expected tool classes based on domain profile
            classes = {t.tool_class for t in tools}
            profile = self.config.domain_profile
            if profile:
                expected_first = (
                    profile.tool_class_order[0]
                    if profile.tool_class_order
                    else None
                )
                if expected_first and expected_first not in classes:
                    state.gaps.append(GapSpec(
                        gap_type=GapType.MISSING_CAPABILITY,
                        detected_by=self.ROLE_NAME,
                        pipeline_stage=3,
                        field_or_task=f"available_tools[{expected_first}]",
                        reason=f"No {expected_first}-class tools available. "
                               f"This tool class is typically required first in "
                               f"{profile.name} operations.",
                        action_required=f"Add at least one {expected_first}-class tool "
                                        f"or confirm manual {expected_first.lower()} approach.",
                        responsible_party="Mission Author",
                        complexity="LOW",
                        completion_percentage=50,
                        blocking=False,
                        partial_spec_available=True,
                    ))
            else:
                if "RECON" not in classes:
                    state.gaps.append(GapSpec(
                        gap_type=GapType.MISSING_CAPABILITY,
                        detected_by=self.ROLE_NAME,
                        pipeline_stage=3,
                        field_or_task="available_tools[RECON]",
                        reason="No RECON-class tools available. Reconnaissance is "
                               "typically required for target enumeration.",
                        action_required="Add at least one RECON-class tool (e.g., nmap, "
                                        "masscan) or confirm manual reconnaissance.",
                        responsible_party="Mission Author",
                        complexity="LOW",
                        completion_percentage=50,
                        blocking=False,
                        partial_spec_available=True,
                    ))

        # ── Detect scope gaps ──────────────────────────────────────
        if not scope:
            state.gaps.append(GapSpec(
                gap_type=GapType.UNKNOWN_PATTERN,
                detected_by=self.ROLE_NAME,
                pipeline_stage=3,
                field_or_task="scope",
                reason="No target scope defined. Cannot generate targeted "
                       "COAs without knowing the operational boundary.",
                action_required="Define scope as a list of target identifiers "
                                "(IP ranges, hostnames, or asset references).",
                responsible_party="Mission Author",
                complexity="LOW",
                completion_percentage=0,
                blocking=True,
                partial_spec_available=False,
            ))

    def _generate_coas(
        self,
        mi: MissionInput,
        tools: List[ToolSpec],
        scope: List[str],
    ) -> List[COASpec]:
        """Generate 1-3 COAs. Uses domain profile templates if configured."""
        profile = self.config.domain_profile
        if profile:
            return self._generate_domain_coas(mi, tools, scope, profile)
        return self._generate_default_coas(mi, tools, scope)

    # ── Domain-profile-driven COA generation ──────────────────────

    def _generate_domain_coas(
        self,
        mi: MissionInput,
        tools: List[ToolSpec],
        scope: List[str],
        profile: Any,
    ) -> List[COASpec]:
        """Generate COAs from domain profile phase templates."""
        by_class: Dict[str, List[ToolSpec]] = {}
        for t in tools:
            by_class.setdefault(t.tool_class, []).append(t)

        coas: List[COASpec] = []

        # Try conservative
        if profile.conservative_phases:
            coa = self._build_coa_from_template(
                "COA-1", "Conservative", profile.conservative_phases,
                by_class, scope, profile,
            )
            if coa:
                coas.append(coa)

        # Try moderate
        if profile.moderate_phases:
            coa = self._build_coa_from_template(
                "COA-2", "Moderate", profile.moderate_phases,
                by_class, scope, profile,
            )
            if coa:
                coas.append(coa)

        # Try aggressive
        if profile.aggressive_phases:
            coa = self._build_coa_from_template(
                "COA-3", "Aggressive", profile.aggressive_phases,
                by_class, scope, profile,
            )
            if coa:
                coas.append(coa)

        if not coas:
            coas.append(self._build_minimal_coa(mi, scope))

        return coas

    def _build_coa_from_template(
        self,
        coa_id: str,
        label: str,
        phases: List[Any],
        by_class: Dict[str, List[ToolSpec]],
        scope: List[str],
        profile: Any,
    ) -> COASpec:
        """Build a COA from phase templates, binding available tools."""
        nodes: List[TaskNodeSpec] = []
        node_id = 1
        scope_str = ", ".join(scope[:3]) or "target scope"

        for phase in phases:
            # Collect tool IDs from required + optional classes
            tool_ids: List[str] = []
            for tc in phase.required_tool_classes:
                tool_ids.extend(t.tool_id for t in by_class.get(tc, []))
            for tc in phase.optional_tool_classes:
                tool_ids.extend(t.tool_id for t in by_class.get(tc, []))

            # Format description
            desc = phase.description_template.format(
                scope=scope_str,
                tools=", ".join(tool_ids) if tool_ids else "manual",
            )

            # Build dependencies
            depends: List[str] = []
            if phase.depends_on_previous and node_id > 1:
                depends = [str(node_id - 1)]

            node = TaskNodeSpec(
                node_id=str(node_id),
                name=phase.phase_name,
                description=desc,
                depends_on=depends,
                tool_ids=tool_ids,
                risk_factors=list(phase.risk_factors),
            )
            nodes.append(node)
            node_id += 1

        edges = self._build_edges(nodes)

        return COASpec(
            coa_id=coa_id,
            approach=f"{label} {profile.name.lower()} approach",
            task_nodes=nodes,
            edges=edges,
        )

    # ── Default COA generation (v1.0-1.3 behavior) ───────────────

    def _generate_default_coas(
        self,
        mi: MissionInput,
        tools: List[ToolSpec],
        scope: List[str],
    ) -> List[COASpec]:
        """Generate 1-3 COAs based on available tools and scope (legacy behavior)."""
        # Group tools by class
        by_class: Dict[str, List[ToolSpec]] = {}
        for t in tools:
            by_class.setdefault(t.tool_class, []).append(t)

        coas: List[COASpec] = []

        # COA-1: Conservative (RECON + SCAN only)
        recon_tools = by_class.get("RECON", [])
        scan_tools = by_class.get("SCAN", [])
        if recon_tools or scan_tools:
            coa1 = self._build_conservative_coa(
                mi, recon_tools, scan_tools, scope
            )
            coas.append(coa1)

        # COA-2: Moderate (RECON + SCAN + limited EXPLOIT)
        exploit_tools = by_class.get("EXPLOIT", [])
        if (recon_tools or scan_tools) and exploit_tools:
            coa2 = self._build_moderate_coa(
                mi, recon_tools, scan_tools, exploit_tools, scope
            )
            coas.append(coa2)

        # COA-3: Aggressive (all tools, parallel execution)
        if len(tools) >= 3:
            coa3 = self._build_aggressive_coa(mi, tools, scope)
            coas.append(coa3)

        # If no tools available, generate a single minimal COA
        if not coas:
            coas.append(self._build_minimal_coa(mi, scope))

        return coas

    def _build_conservative_coa(
        self,
        mi: MissionInput,
        recon: List[ToolSpec],
        scan: List[ToolSpec],
        scope: List[str],
    ) -> COASpec:
        """Conservative: sequential RECON then SCAN, no exploitation."""
        nodes: List[TaskNodeSpec] = []
        node_id = 1

        # Phase 1: Enumeration
        enum_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Service Enumeration",
            description=f"Enumerate services on {', '.join(scope[:3])}",
            tool_ids=[t.tool_id for t in recon],
        )
        nodes.append(enum_node)
        node_id += 1

        # Phase 2: Scanning (depends on enumeration)
        if scan:
            scan_node = TaskNodeSpec(
                node_id=str(node_id),
                name="Vulnerability Scanning",
                description="Scan enumerated services for vulnerabilities",
                depends_on=[enum_node.node_id],
                tool_ids=[t.tool_id for t in scan],
            )
            nodes.append(scan_node)
            node_id += 1

        # Phase 3: Analysis
        analysis_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Results Analysis",
            description="Analyze and correlate scan results",
            depends_on=[n.node_id for n in nodes],
        )
        nodes.append(analysis_node)

        edges = self._build_edges(nodes)

        return COASpec(
            coa_id="COA-1",
            approach="Conservative reconnaissance and scanning without exploitation",
            task_nodes=nodes,
            edges=edges,
        )

    def _build_moderate_coa(
        self,
        mi: MissionInput,
        recon: List[ToolSpec],
        scan: List[ToolSpec],
        exploit: List[ToolSpec],
        scope: List[str],
    ) -> COASpec:
        """Moderate: RECON -> SCAN -> targeted EXPLOIT."""
        nodes: List[TaskNodeSpec] = []
        node_id = 1

        # Phase 1: Enumeration
        enum_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Service Enumeration",
            description=f"Enumerate services on {', '.join(scope[:3])}",
            tool_ids=[t.tool_id for t in recon],
        )
        nodes.append(enum_node)
        node_id += 1

        # Phase 2: Vulnerability scanning
        scan_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Vulnerability Scanning",
            description="Scan for known vulnerabilities",
            depends_on=[enum_node.node_id],
            tool_ids=[t.tool_id for t in scan],
        )
        nodes.append(scan_node)
        node_id += 1

        # Phase 3: Targeted exploitation
        exploit_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Targeted Exploitation",
            description="Attempt exploitation of confirmed vulnerabilities",
            depends_on=[scan_node.node_id],
            tool_ids=[t.tool_id for t in exploit[:1]],  # Limit to first exploit tool
            risk_factors=["requires_confirmed_vulnerability", "scope_limited"],
        )
        nodes.append(exploit_node)
        node_id += 1

        # Phase 4: Validation
        validate_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Access Validation",
            description="Validate and document achieved access",
            depends_on=[exploit_node.node_id],
        )
        nodes.append(validate_node)

        edges = self._build_edges(nodes)

        return COASpec(
            coa_id="COA-2",
            approach="Moderate approach with targeted exploitation of confirmed vulnerabilities",
            task_nodes=nodes,
            edges=edges,
        )

    def _build_aggressive_coa(
        self,
        mi: MissionInput,
        all_tools: List[ToolSpec],
        scope: List[str],
    ) -> COASpec:
        """Aggressive: parallel scanning, multi-vector exploitation."""
        nodes: List[TaskNodeSpec] = []
        node_id = 1

        # Group tools
        recon = [t for t in all_tools if t.tool_class == "RECON"]
        scan = [t for t in all_tools if t.tool_class == "SCAN"]
        exploit = [t for t in all_tools if t.tool_class == "EXPLOIT"]

        # Phase 1: Parallel enumeration
        enum_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Parallel Enumeration",
            description=f"Multi-tool enumeration of {', '.join(scope[:3])}",
            tool_ids=[t.tool_id for t in recon],
        )
        nodes.append(enum_node)
        node_id += 1

        # Phase 2: Aggressive scanning (all scan tools in parallel)
        scan_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Comprehensive Scanning",
            description="Full vulnerability scan with all available scanners",
            depends_on=[enum_node.node_id],
            tool_ids=[t.tool_id for t in scan],
        )
        nodes.append(scan_node)
        node_id += 1

        # Phase 3: Multi-vector exploitation
        exploit_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Multi-Vector Exploitation",
            description="Parallel exploitation attempts across confirmed vulnerabilities",
            depends_on=[scan_node.node_id],
            tool_ids=[t.tool_id for t in exploit],
            risk_factors=[
                "parallel_exploitation",
                "increased_detection_risk",
                "broader_attack_surface",
            ],
        )
        nodes.append(exploit_node)
        node_id += 1

        # Phase 4: Post-exploitation
        post_node = TaskNodeSpec(
            node_id=str(node_id),
            name="Post-Exploitation Analysis",
            description="Analyze achieved access and document findings",
            depends_on=[exploit_node.node_id],
        )
        nodes.append(post_node)

        edges = self._build_edges(nodes)

        return COASpec(
            coa_id="COA-3",
            approach="Aggressive multi-vector approach with parallel execution",
            task_nodes=nodes,
            edges=edges,
        )

    def _build_minimal_coa(
        self,
        mi: MissionInput,
        scope: List[str],
    ) -> COASpec:
        """Minimal COA when no specific tools are available."""
        nodes = [
            TaskNodeSpec(
                node_id="1",
                name="Manual Assessment",
                description=f"Manual assessment of {', '.join(scope[:3]) or 'target scope'}",
            ),
            TaskNodeSpec(
                node_id="2",
                name="Results Documentation",
                description="Document assessment findings",
                depends_on=["1"],
            ),
        ]
        edges = self._build_edges(nodes)

        return COASpec(
            coa_id="COA-1",
            approach="Minimal manual assessment approach",
            task_nodes=nodes,
            edges=edges,
        )

    def _build_edges(self, nodes: List[TaskNodeSpec]) -> List[Dict[str, str]]:
        """Build edge list from node dependency declarations."""
        edges = []
        for node in nodes:
            for dep_id in node.depends_on:
                edges.append({"from": dep_id, "to": node.node_id})
        return edges

    def _validate_dag(self, nodes: List[TaskNodeSpec]) -> List[str]:
        """
        Validate that the task graph is a valid DAG (no cycles).

        Returns list of error messages (empty if valid).
        """
        errors = []
        node_ids = {n.node_id for n in nodes}

        # Check all dependencies reference valid nodes
        for node in nodes:
            for dep in node.depends_on:
                if dep not in node_ids:
                    errors.append(
                        f"Node {node.node_id} depends on non-existent node {dep}"
                    )

        # Topological sort to detect cycles
        if not errors:
            visited: Set[str] = set()
            in_stack: Set[str] = set()
            dep_map = {n.node_id: n.depends_on for n in nodes}

            def _visit(nid: str) -> bool:
                if nid in in_stack:
                    return True  # Cycle!
                if nid in visited:
                    return False
                in_stack.add(nid)
                for dep in dep_map.get(nid, []):
                    if _visit(dep):
                        return True
                in_stack.discard(nid)
                visited.add(nid)
                return False

            for nid in node_ids:
                if _visit(nid):
                    errors.append(f"Cycle detected involving node {nid}")
                    break

        return errors
