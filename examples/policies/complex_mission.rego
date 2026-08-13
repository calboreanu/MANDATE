package mandate.mission.complex

import rego.v1

# MANDATE mission: MANDATE-COMPLEX-001
# Auto-generated from 4 constraint(s)

default allow := false

_h_1 if {
    "external_api" in input.forbidden_actions
}

allow if {
    # REQUIRES network_access AND NOT FORBIDS external_api
    "network_access" in input.capabilities
    not _h_1
    # data.classification IN ['UNCLASSIFIED', 'CUI']
    input.data.classification in {"UNCLASSIFIED", "CUI"}
    # outcome.confidence >= 0.8
    input.outcome.confidence >= 0.8
    # FORBIDS data_exfiltration
    "data_exfiltration" in input.forbidden_actions
}
