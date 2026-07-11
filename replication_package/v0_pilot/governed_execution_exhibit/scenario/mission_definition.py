"""Normal Mission scenario definition — matches the AEGIS JSX demo 'Normal Mission' flow."""
from models_dataclasses import (
    MissionConfig, CourseOfAction, TaskNode, ToolBinding,
)


def build_normal_mission() -> MissionConfig:
    """Build the Normal Mission configuration matching the JSX demo's 36-step scenario."""

    # ── Tool bindings ────────────────────────────────────────────────
    nmap_recon = ToolBinding(
        tool_id="nmap", tool_class="RECON",
        ttp_id="T1595", ttp_name="Active Scanning",
        parameters={"flags": ["-sn"], "ports": []},
    )
    nmap_discovery = ToolBinding(
        tool_id="nmap", tool_class="RECON",
        ttp_id="T1595", ttp_name="Active Scanning",
        parameters={"flags": ["-sS", "-T3"], "ports": [22, 80, 443, 8080, 8443]},
    )
    nmap_version = ToolBinding(
        tool_id="nmap", tool_class="SCAN",
        ttp_id="T1046", ttp_name="Network Service Discovery",
        parameters={"flags": ["-sV", "--version-intensity", "5"]},
    )
    nuclei_scan = ToolBinding(
        tool_id="nuclei", tool_class="SCAN",
        ttp_id="T1046", ttp_name="Network Service Discovery",
        parameters={"templates": ["cves/", "vulnerabilities/"], "rate_limit": 100},
    )
    metasploit_exploit = ToolBinding(
        tool_id="metasploit", tool_class="EXPLOIT",
        ttp_id="T1190", ttp_name="Exploit Public-Facing Application",
        parameters={"module": "exploit/multi/http/apache_mod_cgi_bash_env_exec"},
    )

    # ── Task DAG (12 nodes) ──────────────────────────────────────────
    nodes_coa1 = [
        TaskNode(1, "Passive reconnaissance", tool_bindings=[]),
        TaskNode(2, "Active host discovery", depends_on=[1], tool_bindings=[nmap_recon]),
        TaskNode(3, "Service enumeration (batch A)", depends_on=[2], parallel_group=1, tool_bindings=[nmap_discovery]),
        TaskNode(4, "Service enumeration (batch B)", depends_on=[2], parallel_group=1, tool_bindings=[nmap_discovery]),
        TaskNode(5, "Service fingerprinting (batch A)", depends_on=[3], parallel_group=2, tool_bindings=[nmap_version]),
        TaskNode(6, "Service fingerprinting (batch B)", depends_on=[4], parallel_group=2, tool_bindings=[nmap_version]),
        TaskNode(7, "Vulnerability scanning (thread 1)", depends_on=[5], parallel_group=3, tool_bindings=[nuclei_scan]),
        TaskNode(8, "Vulnerability scanning (thread 2)", depends_on=[5, 6], parallel_group=3, tool_bindings=[nuclei_scan]),
        TaskNode(9, "Vulnerability scanning (thread 3)", depends_on=[6], parallel_group=3, tool_bindings=[nuclei_scan]),
        TaskNode(10, "Finding validation", depends_on=[7, 8, 9]),
        TaskNode(11, "Report generation", depends_on=[10]),
        TaskNode(12, "Final summary", depends_on=[11]),
    ]

    nodes_coa2 = list(nodes_coa1)  # Same DAG, but node 11 adds exploit attempt
    nodes_coa2[10] = TaskNode(11, "Exploit attempt", depends_on=[10], tool_bindings=[metasploit_exploit])
    nodes_coa2.append(TaskNode(12, "Report generation", depends_on=[11]))

    nodes_coa3 = list(nodes_coa2)  # Aggressive — same as COA2 but parameters less constrained

    # ── COAs ─────────────────────────────────────────────────────────
    coa1 = CourseOfAction(
        coa_id="COA-1", name="Conservative",
        risk_level="LOW",
        description="Passive recon + enumeration only",
        task_nodes=nodes_coa1,
        achieves_minimum=True, achieves_target=False, roe_compliant=True,
    )
    coa2 = CourseOfAction(
        coa_id="COA-2", name="Moderate",
        risk_level="MEDIUM",
        description="Active scanning + vulnerability validation + exploit attempts",
        task_nodes=nodes_coa2,
        achieves_minimum=True, achieves_target=True, roe_compliant=True,
    )
    coa3 = CourseOfAction(
        coa_id="COA-3", name="Aggressive",
        risk_level="HIGH",
        description="Full scanning + aggressive exploit attempts",
        task_nodes=nodes_coa3,
        achieves_minimum=True, achieves_target=True, roe_compliant=True,
    )

    return MissionConfig(
        mission_id="AEGIS-NORMAL-001",
        directive="Conduct authorized penetration test against ACME Corp external perimeter",
        roe=[
            "No destructive actions",
            "No data exfiltration",
            "Testing window: 0200-0600 UTC",
            "No social engineering",
            "No denial-of-service",
        ],
        targets=["acme.example.com", "10.0.1.0/24", "10.0.1.5"],
        time_window="2026-12-31T06:00:00Z",
        authorization_ref="Contract #SW-2026-0847, signed ACME CISO",
        anchor_intent="Identify exploitable vulnerabilities in external-facing services",
        anchor_minimum="Enumerate external services and identify potential vulnerabilities",
        anchor_target="Achieve initial access via confirmed exploitable vulnerability",
        constraints=[
            "target.scope IN ['10.0.1.0/24', 'acme.example.com']",
            "execution.duration <= PT4H",
            "FORBIDS data_exfiltration",
            "FORBIDS destructive_action",
        ],
        coas=[coa1, coa2, coa3],
        policy_id="AEGIS_POLICY",
        policy_version="v1.0-normal",
    )
