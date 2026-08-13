"""
Domain Profiles for MANDATE pipeline customization.

A DomainProfile defines how the DecompositionRole generates COAs
for a specific operational domain. Each profile specifies:

- Phase templates for conservative, moderate, and aggressive COAs
- Tool class ordering and capability mapping
- Risk threshold overrides

Built-in profiles:

- PENTEST_PROFILE: Penetration testing (default, matches v1.0-1.3 behavior)
- INCIDENT_RESPONSE_PROFILE: IT incident response (detect/contain/eradicate/recover)
- DEFENSE_INTEL_PROFILE: Defense/intelligence operations (collection/processing/analysis)

Usage:
    from mandate.domain import INCIDENT_RESPONSE_PROFILE
    from mandate.models import PipelineConfig

    config = PipelineConfig(domain_profile=INCIDENT_RESPONSE_PROFILE)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Phase Template ───────────────────────────────────────────────────

@dataclass
class PhaseTemplate:
    """
    Template for a single phase in a domain-specific COA.

    Phase templates define the structure of each step without
    binding to specific tools — tool binding happens at runtime
    based on available_tools in the MissionInput.

    Attributes:
        phase_name: Human-readable phase label (e.g. "Service Enumeration")
        description_template: Format string; may contain {scope} and {tools}
        required_tool_classes: Tool classes needed (phase skipped if none available)
        optional_tool_classes: Additional tool classes that enhance this phase
        risk_factors: Risk factors declared for this phase
        depends_on_previous: If True, adds dependency on prior phase node
    """
    phase_name: str
    description_template: str
    required_tool_classes: List[str]
    optional_tool_classes: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    depends_on_previous: bool = True


# ── Risk Model Configuration ─────────────────────────────────────────

@dataclass
class RiskModelConfig:
    """
    Configurable risk scoring thresholds.

    Replaces the hardcoded thresholds in BindingRole._assess_risk()
    with domain-tunable values.

    Attributes:
        low_ceiling: score <= low_ceiling → LOW risk
        medium_ceiling: score <= medium_ceiling → MEDIUM risk, else HIGH
        dag_complexity_threshold: Extra +1.0 if DAG nodes > this
        dag_high_complexity_threshold: Extra +1.0 if DAG nodes > this
        risk_factor_weight: Points added per declared risk factor
    """
    low_ceiling: float = 2.0
    medium_ceiling: float = 5.0
    dag_complexity_threshold: int = 4
    dag_high_complexity_threshold: int = 6
    risk_factor_weight: float = 0.5

    def classify(self, score: float) -> str:
        """Classify a numeric risk score into LOW/MEDIUM/HIGH."""
        if score <= self.low_ceiling:
            return "LOW"
        elif score <= self.medium_ceiling:
            return "MEDIUM"
        return "HIGH"


# ── Domain Profile ───────────────────────────────────────────────────

@dataclass
class DomainProfile:
    """
    Domain-specific configuration for pipeline behavior.

    When provided to PipelineConfig, the DecompositionRole uses
    the phase templates instead of its hardcoded heuristics, and
    the BindingRole uses the risk model overrides.
    """
    domain_id: str
    name: str
    description: str = ""

    # Phase templates for each aggressiveness level
    conservative_phases: List[PhaseTemplate] = field(default_factory=list)
    moderate_phases: List[PhaseTemplate] = field(default_factory=list)
    aggressive_phases: List[PhaseTemplate] = field(default_factory=list)

    # Tool class ordering for this domain
    tool_class_order: List[str] = field(
        default_factory=lambda: ["RECON", "SCAN", "EXPLOIT", "ANALYSIS"]
    )

    # Domain-specific tool class → capabilities override
    tool_class_capabilities: Dict[str, List[str]] = field(default_factory=dict)

    # Risk model overrides (None = use defaults)
    risk_model: Optional[RiskModelConfig] = None

    def get_risk_model(self) -> RiskModelConfig:
        """Return the risk model (domain-specific or default)."""
        return self.risk_model or RiskModelConfig()


# ── Built-in Profile: Penetration Testing ────────────────────────────

PENTEST_PROFILE = DomainProfile(
    domain_id="pentest",
    name="Penetration Testing",
    description="Standard penetration testing methodology: reconnaissance, "
                "scanning, exploitation, and post-exploitation analysis.",
    conservative_phases=[
        PhaseTemplate(
            phase_name="Service Enumeration",
            description_template="Enumerate services on {scope}",
            required_tool_classes=["RECON"],
            depends_on_previous=False,
        ),
        PhaseTemplate(
            phase_name="Vulnerability Scanning",
            description_template="Scan enumerated services for vulnerabilities",
            required_tool_classes=["SCAN"],
        ),
        PhaseTemplate(
            phase_name="Results Analysis",
            description_template="Analyze and correlate scan results",
            required_tool_classes=[],
            optional_tool_classes=["ANALYSIS"],
        ),
    ],
    moderate_phases=[
        PhaseTemplate(
            phase_name="Service Enumeration",
            description_template="Enumerate services on {scope}",
            required_tool_classes=["RECON"],
            depends_on_previous=False,
        ),
        PhaseTemplate(
            phase_name="Vulnerability Scanning",
            description_template="Scan for known vulnerabilities",
            required_tool_classes=["SCAN"],
        ),
        PhaseTemplate(
            phase_name="Targeted Exploitation",
            description_template="Attempt exploitation of confirmed vulnerabilities",
            required_tool_classes=["EXPLOIT"],
            risk_factors=["requires_confirmed_vulnerability", "scope_limited"],
        ),
        PhaseTemplate(
            phase_name="Access Validation",
            description_template="Validate and document achieved access",
            required_tool_classes=[],
        ),
    ],
    aggressive_phases=[
        PhaseTemplate(
            phase_name="Parallel Enumeration",
            description_template="Multi-tool enumeration of {scope}",
            required_tool_classes=["RECON"],
            depends_on_previous=False,
        ),
        PhaseTemplate(
            phase_name="Comprehensive Scanning",
            description_template="Full vulnerability scan with all available scanners",
            required_tool_classes=["SCAN"],
        ),
        PhaseTemplate(
            phase_name="Multi-Vector Exploitation",
            description_template="Parallel exploitation attempts across confirmed vulnerabilities",
            required_tool_classes=["EXPLOIT"],
            risk_factors=[
                "parallel_exploitation",
                "increased_detection_risk",
                "broader_attack_surface",
            ],
        ),
        PhaseTemplate(
            phase_name="Post-Exploitation Analysis",
            description_template="Analyze achieved access and document findings",
            required_tool_classes=[],
            optional_tool_classes=["ANALYSIS"],
        ),
    ],
    tool_class_order=["RECON", "SCAN", "EXPLOIT", "ANALYSIS"],
    risk_model=RiskModelConfig(
        low_ceiling=2.0,
        medium_ceiling=5.0,
    ),
)


# ── Built-in Profile: Incident Response ──────────────────────────────

INCIDENT_RESPONSE_PROFILE = DomainProfile(
    domain_id="incident_response",
    name="Incident Response",
    description="IT incident response methodology following NIST SP 800-61: "
                "detection, containment, eradication, and recovery.",
    conservative_phases=[
        PhaseTemplate(
            phase_name="Threat Detection",
            description_template="Analyze alerts and logs for indicators of compromise on {scope}",
            required_tool_classes=["DETECT"],
            depends_on_previous=False,
        ),
        PhaseTemplate(
            phase_name="Initial Containment",
            description_template="Isolate affected systems to prevent lateral movement",
            required_tool_classes=["CONTAIN"],
        ),
        PhaseTemplate(
            phase_name="Incident Documentation",
            description_template="Document findings and containment actions for post-incident review",
            required_tool_classes=[],
        ),
    ],
    moderate_phases=[
        PhaseTemplate(
            phase_name="Threat Detection",
            description_template="Analyze alerts and correlate indicators of compromise on {scope}",
            required_tool_classes=["DETECT"],
            depends_on_previous=False,
        ),
        PhaseTemplate(
            phase_name="Containment",
            description_template="Isolate affected systems and revoke compromised credentials",
            required_tool_classes=["CONTAIN"],
            risk_factors=["service_disruption"],
        ),
        PhaseTemplate(
            phase_name="Eradication",
            description_template="Remove malware, close attack vectors, and apply patches",
            required_tool_classes=["ERADICATE"],
            risk_factors=["system_modification"],
        ),
        PhaseTemplate(
            phase_name="Recovery",
            description_template="Restore systems from clean backups and validate service health",
            required_tool_classes=["RECOVER"],
        ),
    ],
    aggressive_phases=[
        PhaseTemplate(
            phase_name="Parallel Detection",
            description_template="Multi-source threat detection across {scope} using all available sensors",
            required_tool_classes=["DETECT"],
            depends_on_previous=False,
        ),
        PhaseTemplate(
            phase_name="Simultaneous Containment and Eradication",
            description_template="Concurrent isolation and threat removal to minimize attacker dwell time",
            required_tool_classes=["CONTAIN", "ERADICATE"],
            risk_factors=[
                "concurrent_operations",
                "service_disruption",
                "aggressive_remediation",
            ],
        ),
        PhaseTemplate(
            phase_name="Full Recovery",
            description_template="Complete system restoration with enhanced monitoring",
            required_tool_classes=["RECOVER"],
        ),
        PhaseTemplate(
            phase_name="Lessons Learned",
            description_template="Post-incident review and control improvement recommendations",
            required_tool_classes=[],
        ),
    ],
    tool_class_order=["DETECT", "CONTAIN", "ERADICATE", "RECOVER"],
    tool_class_capabilities={
        "DETECT": ["threat_detection", "log_analysis", "alert_triage"],
        "CONTAIN": ["network_isolation", "process_termination", "access_revocation"],
        "ERADICATE": ["malware_removal", "persistence_cleanup", "patch_application"],
        "RECOVER": ["system_restoration", "data_recovery", "service_validation"],
    },
    risk_model=RiskModelConfig(
        low_ceiling=1.5,       # IR is inherently higher risk
        medium_ceiling=4.0,
        risk_factor_weight=0.75,  # Risk factors matter more in IR
    ),
)


# ── Built-in Profile: Defense / Intelligence ─────────────────────────

DEFENSE_INTEL_PROFILE = DomainProfile(
    domain_id="defense_intel",
    name="Defense/Intelligence Operations",
    description="Intelligence collection and analysis following the intelligence cycle: "
                "planning, collection, processing, analysis, and dissemination.",
    conservative_phases=[
        PhaseTemplate(
            phase_name="Collection Planning",
            description_template="Develop collection requirements for {scope}",
            required_tool_classes=[],
            depends_on_previous=False,
        ),
        PhaseTemplate(
            phase_name="Single-Source Collection",
            description_template="Execute primary collection against designated targets",
            required_tool_classes=["COLLECT"],
        ),
        PhaseTemplate(
            phase_name="Processing",
            description_template="Process and normalize collected data for analysis",
            required_tool_classes=["PROCESS"],
        ),
    ],
    moderate_phases=[
        PhaseTemplate(
            phase_name="Collection Planning",
            description_template="Develop multi-source collection plan for {scope}",
            required_tool_classes=[],
            depends_on_previous=False,
        ),
        PhaseTemplate(
            phase_name="Multi-Source Collection",
            description_template="Execute collection across multiple intelligence disciplines",
            required_tool_classes=["COLLECT"],
            risk_factors=["multi_source_correlation"],
        ),
        PhaseTemplate(
            phase_name="Processing and Exploitation",
            description_template="Process, exploit, and normalize collected intelligence",
            required_tool_classes=["PROCESS"],
        ),
        PhaseTemplate(
            phase_name="Analysis",
            description_template="Produce all-source analysis with confidence assessments",
            required_tool_classes=["ANALYZE"],
        ),
        PhaseTemplate(
            phase_name="Dissemination",
            description_template="Distribute finished intelligence to authorized consumers",
            required_tool_classes=["DISSEMINATE"],
            risk_factors=["classification_handling"],
        ),
    ],
    aggressive_phases=[
        PhaseTemplate(
            phase_name="Full-Spectrum Collection",
            description_template="Execute maximum collection posture against {scope}",
            required_tool_classes=["COLLECT"],
            depends_on_previous=False,
            risk_factors=["high_visibility", "resource_intensive"],
        ),
        PhaseTemplate(
            phase_name="Parallel Processing",
            description_template="Concurrent processing pipelines for all collected data",
            required_tool_classes=["PROCESS"],
        ),
        PhaseTemplate(
            phase_name="Multi-INT Fusion Analysis",
            description_template="Fused analysis across all intelligence disciplines",
            required_tool_classes=["ANALYZE"],
            risk_factors=["cross_domain_correlation", "classification_handling"],
        ),
        PhaseTemplate(
            phase_name="Rapid Dissemination",
            description_template="Priority dissemination to operational and strategic consumers",
            required_tool_classes=["DISSEMINATE"],
            risk_factors=["classification_handling", "time_sensitive"],
        ),
    ],
    tool_class_order=["COLLECT", "PROCESS", "ANALYZE", "DISSEMINATE"],
    tool_class_capabilities={
        "COLLECT": ["signal_collection", "data_acquisition"],
        "PROCESS": ["signal_processing", "data_normalization"],
        "ANALYZE": ["pattern_analysis", "correlation_analysis"],
        "DISSEMINATE": ["report_generation", "intelligence_distribution"],
    },
    risk_model=RiskModelConfig(
        low_ceiling=1.0,       # Intel ops have tighter risk bands
        medium_ceiling=3.0,
        dag_complexity_threshold=3,
        risk_factor_weight=1.0,  # Risk factors are heavily weighted
    ),
)


# ── Profile Registry ─────────────────────────────────────────────────

BUILTIN_PROFILES: Dict[str, DomainProfile] = {
    "pentest": PENTEST_PROFILE,
    "incident_response": INCIDENT_RESPONSE_PROFILE,
    "defense_intel": DEFENSE_INTEL_PROFILE,
}


def get_domain_profile(domain_id: str) -> Optional[DomainProfile]:
    """Look up a built-in domain profile by ID."""
    return BUILTIN_PROFILES.get(domain_id)


def list_domain_profiles() -> List[str]:
    """Return list of available built-in domain profile IDs."""
    return sorted(BUILTIN_PROFILES.keys())
