"""
Role 4: Binding

Performs risk assessment for each COA and generates the recommendation:
- Risk scoring based on scope, tool invasiveness, constraint strictness
- Assigns RiskAssessment (score, confidence_min/target, primary_factor) to each COA
- Selects primary COA + fallback sequence
- Generates recommendation rationale

When a RiskModelConfig is provided (via domain_profile or pipeline config),
uses configurable thresholds instead of hardcoded defaults.
When a ToolRegistry is provided, uses registry risk weights instead of
keyword-based heuristics.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..models import (
    COASpec,
    ConfidenceLevel,
    PipelineState,
    Recommendation,
    RiskAssessment,
    RiskLevel,
    RoleResult,
)
from .base import Role


class BindingRole(Role):
    """Binding role: risk assessment and recommendation engine."""

    ROLE_NAME = "Binding"

    def execute(self, state: PipelineState) -> RoleResult:
        if not state.coas:
            return self._fail("No COAs in state — Decomposition must run first")

        # ── Assess risk for each COA ──────────────────────────────
        for coa in state.coas:
            assessment = self._assess_risk(coa, state)
            coa.risk_assessment = assessment

        # ── Generate recommendation ───────────────────────────────
        recommendation = self._recommend(state.coas)
        state.recommendation = recommendation

        return self._success(
            f"Risk assessed for {len(state.coas)} COA(s), "
            f"recommended: {recommendation.primary_coa}",
            primary_coa=recommendation.primary_coa,
            risk_scores={
                c.coa_id: c.risk_assessment.score.value
                for c in state.coas
                if c.risk_assessment
            },
        )

    def _assess_risk(self, coa: COASpec, state: PipelineState) -> RiskAssessment:
        """
        Assess risk for a single COA.

        Scoring factors:
        1. Tool invasiveness (via registry weights or keyword heuristic)
        2. DAG depth/complexity
        3. Risk factors declared on nodes
        4. Constraint strictness (more FORBIDS = higher sensitivity)

        Uses RiskModelConfig from domain_profile or pipeline config
        when available; otherwise uses hardcoded defaults.
        """
        # Resolve risk model: domain_profile > config.risk_model > None (defaults)
        risk_model = None
        if self.config.domain_profile:
            risk_model = self.config.domain_profile.get_risk_model()
        elif self.config.risk_model:
            risk_model = self.config.risk_model

        score_points = 0.0
        registry = self.config.tool_registry

        # Factor 1: Tool invasiveness
        tool_classes = set()
        for node in coa.task_nodes:
            for tid in node.tool_ids:
                if registry:
                    # Use registry risk weights
                    weight = registry.risk_weight_for(tid)
                    score_points += weight
                    entry = registry.get_entry(tid)
                    if entry:
                        tool_classes.add(entry.tool_class)
                else:
                    # Keyword heuristic (legacy behavior)
                    tid_lower = tid.lower()
                    if any(kw in tid_lower for kw in ("exploit", "metasploit", "payload")):
                        tool_classes.add("EXPLOIT")
                        score_points += 3.0
                    elif any(kw in tid_lower for kw in ("scan", "nuclei", "nessus")):
                        tool_classes.add("SCAN")
                        score_points += 1.5
                    elif any(kw in tid_lower for kw in ("nmap", "recon", "enum")):
                        tool_classes.add("RECON")
                        score_points += 0.5
                    else:
                        score_points += 1.0

        # Factor 2: DAG complexity
        num_nodes = len(coa.task_nodes)
        dag_threshold = risk_model.dag_complexity_threshold if risk_model else 4
        dag_high_threshold = risk_model.dag_high_complexity_threshold if risk_model else 6
        if num_nodes > dag_threshold:
            score_points += 1.0
        if num_nodes > dag_high_threshold:
            score_points += 1.0

        # Factor 3: Declared risk factors
        risk_factors_total = sum(len(n.risk_factors) for n in coa.task_nodes)
        rf_weight = risk_model.risk_factor_weight if risk_model else 0.5
        score_points += risk_factors_total * rf_weight

        # Map score to risk level using configurable thresholds
        if risk_model:
            level_str = risk_model.classify(score_points)
            score = RiskLevel(level_str)
        else:
            if score_points <= 2.0:
                score = RiskLevel.LOW
            elif score_points <= 5.0:
                score = RiskLevel.MEDIUM
            else:
                score = RiskLevel.HIGH

        # Determine confidence levels based on tool availability
        # Expanded to include domain-specific analysis/documentation node names
        non_tool_names = {
            "Results Analysis", "Results Documentation",
            "Access Validation", "Post-Exploitation Analysis",
            "Incident Documentation", "Lessons Learned",
            "Collection Planning",
        }
        has_all_tools = all(
            len(n.tool_ids) > 0
            for n in coa.task_nodes
            if n.name not in non_tool_names
        )
        confidence_min = ConfidenceLevel.MEDIUM if has_all_tools else ConfidenceLevel.LOW
        confidence_target = ConfidenceLevel.HIGH if has_all_tools else ConfidenceLevel.MEDIUM

        # Primary factor
        high_risk_classes = {"EXPLOIT", "ERADICATE", "CONTAIN"}
        if tool_classes & high_risk_classes:
            primary_factor = "exploitation_risk"
        elif risk_factors_total > 2:
            primary_factor = "complexity_risk"
        else:
            primary_factor = "execution_uncertainty"

        return RiskAssessment(
            score=score,
            confidence_min=confidence_min,
            confidence_target=confidence_target,
            primary_factor=primary_factor,
        )

    def _recommend(self, coas: List[COASpec]) -> Recommendation:
        """
        Select primary COA and build fallback sequence.

        Strategy:
        - If multiple COAs exist, prefer the moderate option (COA-2)
        - Fallback ordering: lower risk first
        """
        if len(coas) == 1:
            return Recommendation(
                primary_coa=coas[0].coa_id,
                fallback_sequence=[],
                rationale=f"Single COA {coas[0].coa_id}: {coas[0].approach}",
            )

        # Sort by risk for fallback ordering
        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "UNASSESSABLE": 3}
        scored = [
            (
                c,
                risk_order.get(
                    c.risk_assessment.score.value if c.risk_assessment else "MEDIUM",
                    1,
                ),
            )
            for c in coas
        ]

        # Prefer COA-2 (moderate) if available
        primary = None
        if len(coas) >= 2:
            primary = coas[1]  # COA-2 (0-indexed)
        else:
            primary = scored[0][0]

        # Fallback: remaining COAs sorted by risk (lowest first)
        fallback = [
            c.coa_id
            for c, _ in sorted(scored, key=lambda x: x[1])
            if c.coa_id != primary.coa_id
        ]

        rationale = (
            f"Primary COA {primary.coa_id} balances mission objectives with "
            f"operational risk ({primary.risk_assessment.score.value if primary.risk_assessment else 'N/A'} risk). "
            f"Fallback sequence prioritizes lower-risk alternatives."
        )

        return Recommendation(
            primary_coa=primary.coa_id,
            fallback_sequence=fallback,
            rationale=rationale,
        )
