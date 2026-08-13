"""
Integration tests for Phase 5 — Domain Customization through the full pipeline.

Tests:
- Incident Response mission through pipeline with INCIDENT_RESPONSE_PROFILE
- Defense/Intelligence mission through pipeline with DEFENSE_INTEL_PROFILE
- Multi-COA mission with recommendation tracing
- Registry integration with ProcedureRole and BindingRole
- Risk model configuration effects on scoring
- Backward compatibility (no domain_profile = legacy behavior)
"""
import json
import pytest
from pathlib import Path

from mandate.domain import (
    DEFENSE_INTEL_PROFILE,
    DomainProfile,
    INCIDENT_RESPONSE_PROFILE,
    PENTEST_PROFILE,
    PhaseTemplate,
    RiskModelConfig,
)
from mandate.models import (
    MissionInput,
    PipelineConfig,
    PipelineState,
    ToolSpec,
)
from mandate.pipeline import Pipeline
from mandate.registry import ToolRegistry, ToolRegistryEntry
from mandate.roles.binding import BindingRole
from mandate.roles.decomposition import DecompositionRole
from mandate.roles.procedure import ProcedureRole


# ── Fixtures ─────────────────────────────────────────────────────────

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _load_mission(filename: str) -> MissionInput:
    """Load a mission input from the examples directory."""
    with open(EXAMPLES_DIR / filename) as f:
        return MissionInput.from_dict(json.load(f))


def _ir_tools():
    return [
        ToolSpec(tool_id="crowdstrike_falcon", tool_class="DETECT",
                 description="EDR platform"),
        ToolSpec(tool_id="splunk_enterprise", tool_class="DETECT",
                 description="SIEM platform"),
        ToolSpec(tool_id="palo_alto_firewall", tool_class="CONTAIN",
                 description="NGFW"),
        ToolSpec(tool_id="crowdstrike_rtr", tool_class="ERADICATE",
                 description="Remote remediation"),
        ToolSpec(tool_id="veeam_backup", tool_class="RECOVER",
                 description="Backup recovery"),
    ]


def _intel_tools():
    return [
        ToolSpec(tool_id="elint_receiver", tool_class="COLLECT",
                 description="ELINT receiver"),
        ToolSpec(tool_id="comint_processor", tool_class="COLLECT",
                 description="COMINT processor"),
        ToolSpec(tool_id="sigint_processor", tool_class="PROCESS",
                 description="Signal processing"),
        ToolSpec(tool_id="palantir_gotham", tool_class="ANALYZE",
                 description="Analysis platform"),
        ToolSpec(tool_id="intel_dissem_system", tool_class="DISSEMINATE",
                 description="Dissemination system"),
    ]


# ── DecompositionRole with Domain Profiles ───────────────────────────

class TestDecompositionWithDomain:
    def test_ir_profile_generates_3_coas(self):
        config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="IR-001",
            intent="Contain ransomware",
            scope=["server-01"],
            available_tools=_ir_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="IR-001")
        result = role.execute(state)
        assert result.ok
        assert len(state.coas) == 3

    def test_ir_coa_names_match_profile(self):
        config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="IR-002",
            intent="Respond to incident",
            scope=["host-01"],
            available_tools=_ir_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="IR-002")
        role.execute(state)
        # Conservative COA should have "Threat Detection" node
        coa1_names = [n.name for n in state.coas[0].task_nodes]
        assert "Threat Detection" in coa1_names

    def test_ir_coa_approach_labels(self):
        config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="IR-003",
            intent="Handle incident",
            scope=["net-01"],
            available_tools=_ir_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="IR-003")
        role.execute(state)
        assert "incident response" in state.coas[0].approach.lower()
        assert "conservative" in state.coas[0].approach.lower()
        assert "moderate" in state.coas[1].approach.lower()

    def test_intel_profile_generates_3_coas(self):
        config = PipelineConfig(domain_profile=DEFENSE_INTEL_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="DI-001",
            intent="Collect SIGINT",
            scope=["AO-NORTH"],
            available_tools=_intel_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="DI-001")
        result = role.execute(state)
        assert result.ok
        assert len(state.coas) == 3

    def test_intel_coa_has_dissemination(self):
        config = PipelineConfig(domain_profile=DEFENSE_INTEL_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="DI-002",
            intent="Intelligence collection",
            scope=["SECTOR-7"],
            available_tools=_intel_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="DI-002")
        role.execute(state)
        # Moderate COA should have dissemination
        coa2_names = [n.name for n in state.coas[1].task_nodes]
        assert "Dissemination" in coa2_names

    def test_domain_gap_detection_ir(self):
        """IR profile should detect missing DETECT tools (first in order)."""
        config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
        role = DecompositionRole(config)
        # Only provide CONTAIN tools (no DETECT)
        mi = MissionInput(
            mission_id="IR-GAP",
            intent="Respond",
            scope=["host-01"],
            available_tools=[
                ToolSpec(tool_id="fw", tool_class="CONTAIN"),
            ],
        )
        state = PipelineState(mission_input=mi, mission_id="IR-GAP")
        role.execute(state)
        gap_fields = [g.field_or_task for g in state.gaps]
        assert "available_tools[DETECT]" in gap_fields

    def test_pentest_profile_matches_structure(self):
        """Pentest profile should produce structurally similar COAs."""
        config = PipelineConfig(domain_profile=PENTEST_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="PT-001",
            intent="Pentest target",
            scope=["10.0.1.0/24"],
            available_tools=[
                ToolSpec(tool_id="nmap", tool_class="RECON"),
                ToolSpec(tool_id="nuclei", tool_class="SCAN"),
                ToolSpec(tool_id="metasploit", tool_class="EXPLOIT"),
            ],
        )
        state = PipelineState(mission_input=mi, mission_id="PT-001")
        result = role.execute(state)
        assert result.ok
        assert len(state.coas) == 3

    def test_tool_binding_in_template_coas(self):
        """Tools should be bound to nodes in template-generated COAs."""
        config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="IR-BIND",
            intent="Respond",
            scope=["host-01"],
            available_tools=_ir_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="IR-BIND")
        role.execute(state)
        # Detection node should have both DETECT tools
        coa1 = state.coas[0]
        detect_node = [n for n in coa1.task_nodes if n.name == "Threat Detection"][0]
        assert "crowdstrike_falcon" in detect_node.tool_ids
        assert "splunk_enterprise" in detect_node.tool_ids

    def test_scope_in_descriptions(self):
        """Scope should appear in templated descriptions."""
        config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="IR-SCOPE",
            intent="Respond",
            scope=["server-alpha"],
            available_tools=_ir_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="IR-SCOPE")
        role.execute(state)
        descs = " ".join(n.description for n in state.coas[0].task_nodes)
        assert "server-alpha" in descs

    def test_dag_edges_consistent(self):
        """All COA edges should reference valid node IDs."""
        config = PipelineConfig(domain_profile=DEFENSE_INTEL_PROFILE)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="DI-EDGE",
            intent="Collect",
            scope=["AO"],
            available_tools=_intel_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="DI-EDGE")
        role.execute(state)
        for coa in state.coas:
            node_ids = {n.node_id for n in coa.task_nodes}
            for edge in coa.edges:
                assert edge["from"] in node_ids
                assert edge["to"] in node_ids


# ── ProcedureRole with ToolRegistry ──────────────────────────────────

class TestProcedureWithRegistry:
    def test_registry_caps_used(self):
        tools = _ir_tools()
        reg = ToolRegistry.from_tools(tools)
        config = PipelineConfig(
            domain_profile=INCIDENT_RESPONSE_PROFILE,
            tool_registry=reg,
        )
        role = ProcedureRole(config)
        mi = MissionInput(
            mission_id="IR-PROC",
            intent="Respond",
            scope=["host-01"],
            available_tools=tools,
        )
        state = PipelineState(mission_input=mi, mission_id="IR-PROC")
        # Run decomposition first to populate COAs
        DecompositionRole(config).execute(state)
        result = role.execute(state)
        assert result.ok
        # Check that capabilities were resolved
        all_caps = set()
        for coa in state.coas:
            all_caps.update(coa.capabilities)
        assert "threat_detection" in all_caps

    def test_fallback_without_registry(self):
        """Without registry, procedure still determines capabilities via heuristic."""
        config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
        role = ProcedureRole(config)
        mi = MissionInput(
            mission_id="IR-NREG",
            intent="Respond",
            scope=["host-01"],
            available_tools=_ir_tools(),
        )
        state = PipelineState(mission_input=mi, mission_id="IR-NREG")
        DecompositionRole(config).execute(state)
        result = role.execute(state)
        assert result.ok
        # Should still get some capabilities
        all_caps = set()
        for coa in state.coas:
            all_caps.update(coa.capabilities)
        assert len(all_caps) > 0


# ── BindingRole with Configurable Risk Model ─────────────────────────

class TestBindingWithRiskModel:
    def test_ir_risk_model_applied(self):
        """IR risk model has tighter thresholds — should affect scoring."""
        tools = _ir_tools()
        reg = ToolRegistry.from_tools(tools)
        config = PipelineConfig(
            domain_profile=INCIDENT_RESPONSE_PROFILE,
            tool_registry=reg,
        )
        mi = MissionInput(
            mission_id="IR-RISK",
            intent="Respond",
            scope=["host-01"],
            available_tools=tools,
        )
        state = PipelineState(mission_input=mi, mission_id="IR-RISK")
        DecompositionRole(config).execute(state)
        ProcedureRole(config).execute(state)
        binding = BindingRole(config)
        result = binding.execute(state)
        assert result.ok
        # Every COA should have a risk assessment
        for coa in state.coas:
            assert coa.risk_assessment is not None

    def test_registry_weights_affect_scoring(self):
        """Custom registry weights should change risk scoring."""
        tools = [ToolSpec(tool_id="safe_tool", tool_class="RECON")]
        low_reg = ToolRegistry()
        low_reg.register(ToolRegistryEntry(
            tool_id="safe_tool", tool_class="RECON",
            capabilities=["scan"], risk_weight=0.1,
        ))
        high_reg = ToolRegistry()
        high_reg.register(ToolRegistryEntry(
            tool_id="safe_tool", tool_class="RECON",
            capabilities=["scan"], risk_weight=10.0,
        ))

        mi = MissionInput(
            mission_id="RISK-CMP",
            intent="Test",
            scope=["target"],
            available_tools=tools,
        )

        # Low registry
        config_low = PipelineConfig(tool_registry=low_reg)
        state_low = PipelineState(mission_input=mi, mission_id="RISK-CMP")
        DecompositionRole(config_low).execute(state_low)
        ProcedureRole(config_low).execute(state_low)
        BindingRole(config_low).execute(state_low)

        # High registry
        config_high = PipelineConfig(tool_registry=high_reg)
        state_high = PipelineState(mission_input=mi, mission_id="RISK-CMP")
        DecompositionRole(config_high).execute(state_high)
        ProcedureRole(config_high).execute(state_high)
        BindingRole(config_high).execute(state_high)

        # High-risk registry should produce higher/equal risk scores
        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        low_score = risk_order[state_low.coas[0].risk_assessment.score.value]
        high_score = risk_order[state_high.coas[0].risk_assessment.score.value]
        assert high_score >= low_score

    def test_explicit_risk_model_on_config(self):
        """risk_model on PipelineConfig (without domain_profile) should be used."""
        rm = RiskModelConfig(low_ceiling=0.0, medium_ceiling=0.0)  # Everything is HIGH
        config = PipelineConfig(risk_model=rm)
        mi = MissionInput(
            mission_id="RM-001",
            intent="Test",
            scope=["target"],
            available_tools=[ToolSpec(tool_id="nmap", tool_class="RECON")],
        )
        state = PipelineState(mission_input=mi, mission_id="RM-001")
        DecompositionRole(config).execute(state)
        ProcedureRole(config).execute(state)
        BindingRole(config).execute(state)
        # With ceiling=0, any tool use should produce HIGH
        assert state.coas[0].risk_assessment.score.value == "HIGH"


# ── Full Pipeline Integration ────────────────────────────────────────

class TestFullPipelineIntegration:
    def test_ir_pipeline_end_to_end(self):
        """Full pipeline with IR profile produces valid artifact."""
        config = PipelineConfig(
            domain_profile=INCIDENT_RESPONSE_PROFILE,
            tool_registry=ToolRegistry.from_tools(_ir_tools()),
            strict=True,
        )
        mi = MissionInput(
            mission_id="MANDATE-IR-E2E",
            intent="Contain and eradicate ransomware infection",
            scope=["fileserver-01.corp.local"],
            time_limit="PT8H",
            minimum_outcome="Contain ransomware spread",
            target_outcome="Full eradication and restoration",
            constraints=[
                "execution.duration <= PT8H",
                "FORBIDS data_destruction",
                "FORBIDS unauthorized_system_shutdown",
            ],
            risk_tolerance="MEDIUM",
            available_tools=_ir_tools(),
        )
        pipeline = Pipeline(config)
        result = pipeline.run(mi)
        assert result.ok
        assert result.artifact is not None
        assert result.artifact["mandate_id"] == "MANDATE-IR-E2E"
        # Should have 3 COAs
        assert len(result.artifact["courses_of_action"]) == 3

    def test_intel_pipeline_end_to_end(self):
        """Full pipeline with defense/intel profile produces valid artifact."""
        config = PipelineConfig(
            domain_profile=DEFENSE_INTEL_PROFILE,
            tool_registry=ToolRegistry.from_tools(_intel_tools()),
            strict=True,
        )
        mi = MissionInput(
            mission_id="MANDATE-DI-E2E",
            intent="Collect and analyze signals intelligence",
            scope=["AO-NORTH-SECTOR-7"],
            time_limit="PT24H",
            minimum_outcome="Identify active emitters",
            target_outcome="Pattern-of-life analysis and network mapping",
            constraints=[
                "execution.duration <= PT24H",
                "FORBIDS active_transmission",
                "FORBIDS classification_spillage",
            ],
            risk_tolerance="LOW",
            available_tools=_intel_tools(),
        )
        pipeline = Pipeline(config)
        result = pipeline.run(mi)
        assert result.ok
        assert result.artifact is not None
        assert len(result.artifact["courses_of_action"]) == 3

    def test_multi_coa_recommendation_tracing(self):
        """Multi-COA mission should produce recommendation with fallback sequence."""
        config = PipelineConfig(strict=True)
        mi = MissionInput(
            mission_id="MANDATE-MC-E2E",
            intent="Assess cloud security",
            scope=["aws-us-east-1", "gcp-us-central1"],
            minimum_outcome="Asset inventory and misconfigurations",
            target_outcome="Full security assessment",
            constraints=[
                "FORBIDS data_exfiltration",
                "FORBIDS service_disruption",
            ],
            risk_tolerance="LOW",
            available_tools=[
                ToolSpec(tool_id="prowler", tool_class="RECON"),
                ToolSpec(tool_id="trivy", tool_class="SCAN"),
                ToolSpec(tool_id="pacu", tool_class="EXPLOIT"),
            ],
        )
        pipeline = Pipeline(config)
        result = pipeline.run(mi)
        assert result.ok
        rec = result.artifact["recommendation"]
        assert rec["primary_coa"] == "COA-2"  # Moderate preferred
        assert len(rec["fallback_sequence"]) >= 1
        assert rec["rationale"]

    def test_backward_compatibility_no_profile(self):
        """Pipeline without domain_profile still works (legacy behavior)."""
        config = PipelineConfig(strict=True)
        mi = MissionInput(
            mission_id="MANDATE-LEGACY",
            intent="Pentest target network",
            scope=["10.0.1.0/24"],
            minimum_outcome="Enumerate services",
            target_outcome="Achieve initial access",
            constraints=[
                "FORBIDS data_exfiltration",
            ],
            risk_tolerance="LOW",
            available_tools=[
                ToolSpec(tool_id="nmap", tool_class="RECON"),
                ToolSpec(tool_id="nuclei", tool_class="SCAN"),
                ToolSpec(tool_id="metasploit", tool_class="EXPLOIT"),
            ],
        )
        pipeline = Pipeline(config)
        result = pipeline.run(mi)
        assert result.ok
        assert result.artifact is not None

    def test_example_ir_mission_file(self):
        """Load and run the incident_response_mission.json example."""
        mi = _load_mission("incident_response_mission.json")
        config = PipelineConfig(
            domain_profile=INCIDENT_RESPONSE_PROFILE,
            tool_registry=ToolRegistry.from_tools(mi.available_tools),
            strict=True,
        )
        pipeline = Pipeline(config)
        result = pipeline.run(mi)
        assert result.ok
        assert result.artifact is not None

    def test_example_defense_intel_mission_file(self):
        """Load and run the defense_intel_mission.json example."""
        mi = _load_mission("defense_intel_mission.json")
        config = PipelineConfig(
            domain_profile=DEFENSE_INTEL_PROFILE,
            tool_registry=ToolRegistry.from_tools(mi.available_tools),
            strict=True,
        )
        pipeline = Pipeline(config)
        result = pipeline.run(mi)
        assert result.ok
        assert result.artifact is not None

    def test_example_multi_coa_mission_file(self):
        """Load and run the multi_coa_mission.json example."""
        mi = _load_mission("multi_coa_mission.json")
        config = PipelineConfig(strict=True)
        pipeline = Pipeline(config)
        result = pipeline.run(mi)
        assert result.ok
        assert result.artifact is not None
        assert len(result.artifact["courses_of_action"]) == 3


# ── Edge Cases ───────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_domain_profile(self):
        """Profile with no phases should fall back to minimal COA."""
        empty = DomainProfile(domain_id="empty", name="Empty")
        config = PipelineConfig(domain_profile=empty)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="EMPTY",
            intent="Test",
            scope=["target"],
            available_tools=[ToolSpec(tool_id="x", tool_class="Y")],
        )
        state = PipelineState(mission_input=mi, mission_id="EMPTY")
        result = role.execute(state)
        assert result.ok
        # Should get minimal COA
        assert len(state.coas) == 1
        assert "manual" in state.coas[0].approach.lower()

    def test_partial_tool_coverage(self):
        """Profile phases with missing tool classes should still produce COAs."""
        config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
        role = DecompositionRole(config)
        # Only DETECT and RECOVER — no CONTAIN or ERADICATE
        mi = MissionInput(
            mission_id="PARTIAL",
            intent="Respond",
            scope=["host"],
            available_tools=[
                ToolSpec(tool_id="falcon", tool_class="DETECT"),
                ToolSpec(tool_id="veeam", tool_class="RECOVER"),
            ],
        )
        state = PipelineState(mission_input=mi, mission_id="PARTIAL")
        result = role.execute(state)
        assert result.ok
        # Should still generate COAs (phases without tools get empty tool_ids)
        assert len(state.coas) >= 1

    def test_custom_domain_profile(self):
        """Custom (user-defined) domain profile should work."""
        custom = DomainProfile(
            domain_id="custom",
            name="Custom Domain",
            conservative_phases=[
                PhaseTemplate(
                    phase_name="Step Alpha",
                    description_template="Do alpha on {scope}",
                    required_tool_classes=["ALPHA"],
                    depends_on_previous=False,
                ),
                PhaseTemplate(
                    phase_name="Step Beta",
                    description_template="Do beta",
                    required_tool_classes=["BETA"],
                ),
            ],
            tool_class_order=["ALPHA", "BETA"],
        )
        config = PipelineConfig(domain_profile=custom)
        role = DecompositionRole(config)
        mi = MissionInput(
            mission_id="CUSTOM",
            intent="Custom operation",
            scope=["zone-1"],
            available_tools=[
                ToolSpec(tool_id="a_tool", tool_class="ALPHA"),
                ToolSpec(tool_id="b_tool", tool_class="BETA"),
            ],
        )
        state = PipelineState(mission_input=mi, mission_id="CUSTOM")
        result = role.execute(state)
        assert result.ok
        assert len(state.coas) >= 1
        names = [n.name for n in state.coas[0].task_nodes]
        assert "Step Alpha" in names
        assert "Step Beta" in names

    def test_risk_model_domain_takes_priority_over_config(self):
        """domain_profile.risk_model should override config.risk_model."""
        domain_rm = RiskModelConfig(low_ceiling=0.0, medium_ceiling=0.0)
        config_rm = RiskModelConfig(low_ceiling=999.0, medium_ceiling=999.0)
        profile = DomainProfile(
            domain_id="test", name="Test",
            risk_model=domain_rm,
            conservative_phases=[
                PhaseTemplate(
                    phase_name="Step",
                    description_template="Do step",
                    required_tool_classes=["RECON"],
                    depends_on_previous=False,
                ),
            ],
        )
        config = PipelineConfig(
            domain_profile=profile,
            risk_model=config_rm,
        )
        mi = MissionInput(
            mission_id="PRI-001",
            intent="Test priority",
            scope=["target"],
            minimum_outcome="Min",
            target_outcome="Target",
            constraints=["FORBIDS nothing_important"],
            risk_tolerance="LOW",
            available_tools=[ToolSpec(tool_id="nmap", tool_class="RECON")],
        )
        pipeline = Pipeline(config)
        result = pipeline.run(mi)
        assert result.ok
        # Domain's ceiling=0 means everything is HIGH
        coa = result.artifact["courses_of_action"][0]
        assert coa["risk_assessment"]["score"] == "HIGH"
