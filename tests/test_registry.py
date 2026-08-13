"""Tests for mandate.registry — Tool Capability Registry."""
import pytest

from mandate.models import ToolSpec
from mandate.registry import (
    DEFAULT_CLASS_CAPABILITIES,
    DEFAULT_CLASS_RISK_WEIGHT,
    ToolRegistry,
    ToolRegistryEntry,
)


# ── ToolRegistryEntry ────────────────────────────────────────────────

class TestToolRegistryEntry:
    def test_basic_creation(self):
        entry = ToolRegistryEntry(
            tool_id="nmap", tool_class="RECON",
            capabilities=["network_enumeration"],
            risk_weight=0.5,
        )
        assert entry.tool_id == "nmap"
        assert entry.tool_class == "RECON"
        assert entry.capabilities == ["network_enumeration"]
        assert entry.risk_weight == 0.5

    def test_defaults(self):
        entry = ToolRegistryEntry(tool_id="x", tool_class="Y")
        assert entry.capabilities == []
        assert entry.risk_weight == 1.0
        assert entry.description == ""
        assert entry.parameters == {}


# ── ToolRegistry ─────────────────────────────────────────────────────

class TestToolRegistryBasic:
    def test_empty_registry(self):
        reg = ToolRegistry()
        assert len(reg) == 0
        assert reg.registered_tools() == []
        assert not reg.has_tool("nmap")

    def test_register_and_lookup(self):
        reg = ToolRegistry()
        entry = ToolRegistryEntry(
            tool_id="nmap", tool_class="RECON",
            capabilities=["net_enum", "svc_disco"],
            risk_weight=0.5,
        )
        reg.register(entry)
        assert reg.has_tool("nmap")
        assert len(reg) == 1
        assert reg.capabilities_for("nmap") == ["net_enum", "svc_disco"]
        assert reg.risk_weight_for("nmap") == 0.5

    def test_get_entry(self):
        reg = ToolRegistry()
        entry = ToolRegistryEntry(tool_id="x", tool_class="Y")
        reg.register(entry)
        assert reg.get_entry("x") is entry
        assert reg.get_entry("unknown") is None

    def test_unregister(self):
        reg = ToolRegistry()
        reg.register(ToolRegistryEntry(tool_id="x", tool_class="Y"))
        assert reg.unregister("x") is True
        assert reg.unregister("x") is False
        assert not reg.has_tool("x")

    def test_registered_tools_sorted(self):
        reg = ToolRegistry()
        reg.register(ToolRegistryEntry(tool_id="z", tool_class="A"))
        reg.register(ToolRegistryEntry(tool_id="a", tool_class="B"))
        assert reg.registered_tools() == ["a", "z"]


class TestToolRegistryResolution:
    """Test the 3-tier resolution: explicit → class → fallback."""

    def test_explicit_entry_wins(self):
        reg = ToolRegistry()
        reg.register(ToolRegistryEntry(
            tool_id="nmap", tool_class="RECON",
            capabilities=["custom_cap"],
            risk_weight=9.9,
        ))
        # Even with tool_class hint, explicit entry wins
        assert reg.capabilities_for("nmap", "RECON") == ["custom_cap"]
        assert reg.risk_weight_for("nmap", "RECON") == 9.9

    def test_class_default_fallback(self):
        reg = ToolRegistry()
        caps = reg.capabilities_for("unknown_tool", "RECON")
        assert caps == DEFAULT_CLASS_CAPABILITIES["RECON"]
        weight = reg.risk_weight_for("unknown_tool", "RECON")
        assert weight == DEFAULT_CLASS_RISK_WEIGHT["RECON"]

    def test_ultimate_fallback(self):
        reg = ToolRegistry()
        assert reg.capabilities_for("totally_unknown") == ["tool_execution"]
        assert reg.risk_weight_for("totally_unknown") == 1.0

    def test_class_override(self):
        reg = ToolRegistry()
        reg.register_class_capabilities("RECON", ["custom_a", "custom_b"])
        reg.register_class_risk_weight("RECON", 99.0)
        assert reg.capabilities_for("x", "RECON") == ["custom_a", "custom_b"]
        assert reg.risk_weight_for("x", "RECON") == 99.0


class TestToolRegistryFromTools:
    """Test ToolRegistry.from_tools() factory."""

    def test_from_tools_basic(self):
        tools = [
            ToolSpec(tool_id="nmap", tool_class="RECON", description="mapper"),
            ToolSpec(tool_id="nuclei", tool_class="SCAN", description="scanner"),
        ]
        reg = ToolRegistry.from_tools(tools)
        assert len(reg) == 2
        assert reg.has_tool("nmap")
        assert reg.has_tool("nuclei")

    def test_from_tools_capabilities(self):
        tools = [ToolSpec(tool_id="nmap", tool_class="RECON")]
        reg = ToolRegistry.from_tools(tools)
        caps = reg.capabilities_for("nmap")
        assert "network_enumeration" in caps
        assert "service_discovery" in caps

    def test_from_tools_risk_weight(self):
        tools = [
            ToolSpec(tool_id="nmap", tool_class="RECON"),
            ToolSpec(tool_id="metasploit", tool_class="EXPLOIT"),
        ]
        reg = ToolRegistry.from_tools(tools)
        assert reg.risk_weight_for("nmap") == 0.5
        assert reg.risk_weight_for("metasploit") == 3.0

    def test_from_tools_unknown_class(self):
        tools = [ToolSpec(tool_id="custom", tool_class="UNKNOWN_CLASS")]
        reg = ToolRegistry.from_tools(tools)
        assert reg.capabilities_for("custom") == ["tool_execution"]
        assert reg.risk_weight_for("custom") == 1.0

    def test_from_tools_preserves_parameters(self):
        tools = [ToolSpec(
            tool_id="nmap", tool_class="RECON",
            parameters={"timing": "T3"},
        )]
        reg = ToolRegistry.from_tools(tools)
        entry = reg.get_entry("nmap")
        assert entry.parameters == {"timing": "T3"}

    def test_from_tools_ir_domain(self):
        tools = [
            ToolSpec(tool_id="falcon", tool_class="DETECT"),
            ToolSpec(tool_id="firewall", tool_class="CONTAIN"),
        ]
        reg = ToolRegistry.from_tools(tools)
        assert "threat_detection" in reg.capabilities_for("falcon")
        assert "network_isolation" in reg.capabilities_for("firewall")
        assert reg.risk_weight_for("falcon") == 0.5
        assert reg.risk_weight_for("firewall") == 2.0


class TestToolRegistryToDict:
    def test_serialization(self):
        reg = ToolRegistry()
        reg.register(ToolRegistryEntry(
            tool_id="x", tool_class="Y",
            capabilities=["a"], risk_weight=1.5,
        ))
        d = reg.to_dict()
        assert "entries" in d
        assert "x" in d["entries"]
        assert d["entries"]["x"]["capabilities"] == ["a"]
        assert "class_capabilities" in d
        assert "class_risk_weights" in d

    def test_repr(self):
        reg = ToolRegistry()
        assert "0 tools" in repr(reg)
        reg.register(ToolRegistryEntry(tool_id="x", tool_class="Y"))
        assert "1 tools" in repr(reg)


# ── Default Mappings ─────────────────────────────────────────────────

class TestDefaultMappings:
    def test_pentest_classes_present(self):
        for cls in ["RECON", "SCAN", "EXPLOIT", "ANALYSIS"]:
            assert cls in DEFAULT_CLASS_CAPABILITIES
            assert cls in DEFAULT_CLASS_RISK_WEIGHT

    def test_ir_classes_present(self):
        for cls in ["DETECT", "CONTAIN", "ERADICATE", "RECOVER"]:
            assert cls in DEFAULT_CLASS_CAPABILITIES
            assert cls in DEFAULT_CLASS_RISK_WEIGHT

    def test_intel_classes_present(self):
        for cls in ["COLLECT", "PROCESS", "ANALYZE", "DISSEMINATE"]:
            assert cls in DEFAULT_CLASS_CAPABILITIES
            assert cls in DEFAULT_CLASS_RISK_WEIGHT

    def test_exploit_is_highest_risk(self):
        assert DEFAULT_CLASS_RISK_WEIGHT["EXPLOIT"] >= DEFAULT_CLASS_RISK_WEIGHT["SCAN"]
        assert DEFAULT_CLASS_RISK_WEIGHT["SCAN"] >= DEFAULT_CLASS_RISK_WEIGHT["RECON"]
