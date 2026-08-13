package mandate.mission.nm001

import rego.v1

# MANDATE mission: MANDATE-NM-001
# Auto-generated from 4 constraint(s)

default allow := false

allow if {
    # target.scope IN ['10.0.1.0/24', 'acme.example.com']
    input.target.scope in {"10.0.1.0/24", "acme.example.com"}
    # execution.duration <= PT4H
    input.execution.duration <= "PT4H"
    # FORBIDS data_exfiltration
    "data_exfiltration" in input.forbidden_actions
    # FORBIDS destructive_action
    "destructive_action" in input.forbidden_actions
}
