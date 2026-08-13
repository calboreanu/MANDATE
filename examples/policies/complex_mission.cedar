// MANDATE constraint policy — auto-generated
// Mission: MANDATE-COMPLEX-001
// Constraints: 4

permit (
    principal,
    action == Mandate::Action::"execute",
    resource
)
when {
    context.capabilities.contains("network_access") &&
    !context.forbidden_actions.contains("external_api") &&
    context.data.classification in ["UNCLASSIFIED", "CUI"] &&
    context.outcome.confidence >= decimal("0.8") &&
    context.forbidden_actions.contains("data_exfiltration")
};
