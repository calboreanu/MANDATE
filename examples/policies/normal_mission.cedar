// MANDATE constraint policy — auto-generated
// Mission: MANDATE-NM-001
// Constraints: 4

permit (
    principal,
    action == Mandate::Action::"execute",
    resource
)
when {
    context.target.scope in ["10.0.1.0/24", "acme.example.com"] &&
    context.execution.duration <= "PT4H" &&
    context.forbidden_actions.contains("data_exfiltration") &&
    context.forbidden_actions.contains("destructive_action")
};
