"""Tests for mandate.domain — Domain Profiles and Risk Model Configuration."""
import pytest

from mandate.domain import (
    BUILTIN_PROFILES,
    DEFENSE_INTEL_PROFILE,
    DomainProfile,
    INCIDENT_RESPONSE_PROFILE,
    PENTEST_PROFILE,
    PhaseTemplate,
    RiskModelConfig,
    get_domain_profile,
    list_domain_profiles,
)


# ── RiskModelConfig ──────────────────────────────────────────────────

class TestRiskModelConfig:
    def test_defaults(self):
        rm = RiskModelConfig()
        assert rm.low_ceiling == 2.0
        assert rm.medium_ceiling == 5.0
        assert rm.dag_complexity_threshold == 4
        assert rm.dag_high_complexity_threshold == 6
        assert rm.risk_factor_weight == 0.5

    def test_classify_low(self):
        rm = RiskModelConfig()
        assert rm.classify(0.0) == "LOW"
        assert rm.classify(1.5) == "LOW"
        assert rm.classify(2.0) == "LOW"

    def test_classify_medium(self):
        rm = RiskModelConfig()
        assert rm.classify(2.1) == "MEDIUM"
        assert rm.classify(3.5) == "MEDIUM"
        assert rm.classify(5.0) == "MEDIUM"

    def test_classify_high(self):
        rm = RiskModelConfig()
        assert rm.classify(5.1) == "HIGH"
        assert rm.classify(100.0) == "HIGH"

    def test_custom_thresholds(self):
        rm = RiskModelConfig(low_ceiling=1.0, medium_ceiling=3.0)
        assert rm.classify(1.0) == "LOW"
        assert rm.classify(1.1) == "MEDIUM"
        assert rm.classify(3.0) == "MEDIUM"
        assert rm.classify(3.1) == "HIGH"

    def test_zero_thresholds(self):
        rm = RiskModelConfig(low_ceiling=0.0, medium_ceiling=0.0)
        assert rm.classify(0.0) == "LOW"
        assert rm.classify(0.1) == "HIGH"


# ── PhaseTemplate ────────────────────────────────────────────────────

class TestPhaseTemplate:
    def test_basic_creation(self):
        pt = PhaseTemplate(
            phase_name="Recon",
            description_template="Scan {scope}",
            required_tool_classes=["RECON"],
        )
        assert pt.phase_name == "Recon"
        assert pt.depends_on_previous is True
        assert pt.risk_factors == []
        assert pt.optional_tool_classes == []

    def test_description_format(self):
        pt = PhaseTemplate(
            phase_name="Test",
            description_template="Check {scope} with {tools}",
            required_tool_classes=[],
        )
        result = pt.description_template.format(scope="10.0.0.0/24", tools="nmap")
        assert "10.0.0.0/24" in result
        assert "nmap" in result

    def test_risk_factors(self):
        pt = PhaseTemplate(
            phase_name="Exploit",
            description_template="Exploit targets",
            required_tool_classes=["EXPLOIT"],
            risk_factors=["parallel_exploitation", "detection_risk"],
        )
        assert len(pt.risk_factors) == 2


# ── DomainProfile ────────────────────────────────────────────────────

class TestDomainProfile:
    def test_basic_creation(self):
        dp = DomainProfile(domain_id="test", name="Test Domain")
        assert dp.domain_id == "test"
        assert dp.conservative_phases == []
        assert dp.moderate_phases == []
        assert dp.aggressive_phases == []

    def test_get_risk_model_default(self):
        dp = DomainProfile(domain_id="test", name="Test")
        rm = dp.get_risk_model()
        assert rm.low_ceiling == 2.0  # Default RiskModelConfig

    def test_get_risk_model_custom(self):
        custom_rm = RiskModelConfig(low_ceiling=1.0)
        dp = DomainProfile(
            domain_id="test", name="Test",
            risk_model=custom_rm,
        )
        assert dp.get_risk_model().low_ceiling == 1.0

    def test_tool_class_order_default(self):
        dp = DomainProfile(domain_id="test", name="Test")
        assert dp.tool_class_order == ["RECON", "SCAN", "EXPLOIT", "ANALYSIS"]


# ── Built-in Profiles ────────────────────────────────────────────────

class TestPentestProfile:
    def test_identity(self):
        assert PENTEST_PROFILE.domain_id == "pentest"
        assert PENTEST_PROFILE.name == "Penetration Testing"

    def test_has_all_phase_levels(self):
        assert len(PENTEST_PROFILE.conservative_phases) >= 2
        assert len(PENTEST_PROFILE.moderate_phases) >= 3
        assert len(PENTEST_PROFILE.aggressive_phases) >= 3

    def test_conservative_no_exploit(self):
        for phase in PENTEST_PROFILE.conservative_phases:
            assert "EXPLOIT" not in phase.required_tool_classes

    def test_moderate_has_exploit(self):
        exploit_phases = [
            p for p in PENTEST_PROFILE.moderate_phases
            if "EXPLOIT" in p.required_tool_classes
        ]
        assert len(exploit_phases) >= 1

    def test_aggressive_has_risk_factors(self):
        all_rf = []
        for p in PENTEST_PROFILE.aggressive_phases:
            all_rf.extend(p.risk_factors)
        assert "parallel_exploitation" in all_rf

    def test_risk_model(self):
        rm = PENTEST_PROFILE.get_risk_model()
        assert rm.low_ceiling == 2.0
        assert rm.medium_ceiling == 5.0


class TestIncidentResponseProfile:
    def test_identity(self):
        assert INCIDENT_RESPONSE_PROFILE.domain_id == "incident_response"
        assert "Incident Response" in INCIDENT_RESPONSE_PROFILE.name

    def test_tool_class_order(self):
        assert INCIDENT_RESPONSE_PROFILE.tool_class_order == [
            "DETECT", "CONTAIN", "ERADICATE", "RECOVER"
        ]

    def test_conservative_phases(self):
        phases = INCIDENT_RESPONSE_PROFILE.conservative_phases
        assert len(phases) >= 2
        names = [p.phase_name for p in phases]
        assert "Threat Detection" in names

    def test_moderate_has_eradication(self):
        phases = INCIDENT_RESPONSE_PROFILE.moderate_phases
        eradicate_phases = [
            p for p in phases
            if "ERADICATE" in p.required_tool_classes
        ]
        assert len(eradicate_phases) >= 1

    def test_aggressive_has_concurrent_ops(self):
        phases = INCIDENT_RESPONSE_PROFILE.aggressive_phases
        all_rf = []
        for p in phases:
            all_rf.extend(p.risk_factors)
        assert "concurrent_operations" in all_rf

    def test_risk_model_tighter_than_pentest(self):
        ir_rm = INCIDENT_RESPONSE_PROFILE.get_risk_model()
        pt_rm = PENTEST_PROFILE.get_risk_model()
        assert ir_rm.low_ceiling <= pt_rm.low_ceiling

    def test_domain_capabilities(self):
        caps = INCIDENT_RESPONSE_PROFILE.tool_class_capabilities
        assert "DETECT" in caps
        assert "threat_detection" in caps["DETECT"]


class TestDefenseIntelProfile:
    def test_identity(self):
        assert DEFENSE_INTEL_PROFILE.domain_id == "defense_intel"

    def test_tool_class_order(self):
        assert DEFENSE_INTEL_PROFILE.tool_class_order == [
            "COLLECT", "PROCESS", "ANALYZE", "DISSEMINATE"
        ]

    def test_conservative_collection_first(self):
        phases = DEFENSE_INTEL_PROFILE.conservative_phases
        # First phase should not depend on previous
        assert phases[0].depends_on_previous is False

    def test_moderate_has_dissemination(self):
        phases = DEFENSE_INTEL_PROFILE.moderate_phases
        dissem_phases = [
            p for p in phases
            if "DISSEMINATE" in p.required_tool_classes
        ]
        assert len(dissem_phases) >= 1

    def test_aggressive_classification_handling(self):
        phases = DEFENSE_INTEL_PROFILE.aggressive_phases
        all_rf = []
        for p in phases:
            all_rf.extend(p.risk_factors)
        assert "classification_handling" in all_rf

    def test_risk_model_tightest(self):
        rm = DEFENSE_INTEL_PROFILE.get_risk_model()
        assert rm.low_ceiling <= 1.0  # Tightest risk bands
        assert rm.risk_factor_weight >= 1.0  # Highest risk factor weight


# ── Profile Registry ─────────────────────────────────────────────────

class TestProfileRegistry:
    def test_builtin_profiles_dict(self):
        assert "pentest" in BUILTIN_PROFILES
        assert "incident_response" in BUILTIN_PROFILES
        assert "defense_intel" in BUILTIN_PROFILES

    def test_get_domain_profile(self):
        p = get_domain_profile("pentest")
        assert p is PENTEST_PROFILE

    def test_get_domain_profile_unknown(self):
        assert get_domain_profile("nonexistent") is None

    def test_list_domain_profiles(self):
        profiles = list_domain_profiles()
        assert "pentest" in profiles
        assert "incident_response" in profiles
        assert "defense_intel" in profiles
        # Verify sorted
        assert profiles == sorted(profiles)
