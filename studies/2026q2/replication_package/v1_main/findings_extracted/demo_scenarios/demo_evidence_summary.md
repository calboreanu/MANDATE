# Demo Scenarios: Cross-Variant Comparison

Three real scenarios x three apparatus variants each. The variants differ in how source documents were extracted before being indexed for RAG:

- `output`: deterministic apparatus path (no Ollama LLM)
- `output_ollama`: full LLM pipeline against indices built from `mcp web_fetch` text-mode extraction
- `output_ollama_from_binaries`: full LLM pipeline against indices built from original PDF/DOCX/PPTX binaries via apparatus's pypdf/python-docx/python-pptx extractors

| Scenario | Variant | OK | Wall-Clock (s) | LLM Fallback | n_COAs | Fallback Roles |
|---|---|:-:|---:|:-:|---:|---|
| volt_typhoon | output | True | 0.0 | False | 1 | - |
| volt_typhoon | output_ollama | True | 238.5 | False | 1 | - |
| volt_typhoon | output_ollama_from_binaries | True | 166.7 | False | 1 | - |
| crowdstrike_outage | output | True | 0.0 | False | 1 | - |
| crowdstrike_outage | output_ollama | True | 212.0 | False | 1 | - |
| crowdstrike_outage | output_ollama_from_binaries | True | 172.0 | False | 1 | - |
| svb_collapse | output | True | 0.0 | False | 1 | - |
| svb_collapse | output_ollama | True | 195.8 | False | 1 | - |
| svb_collapse | output_ollama_from_binaries | True | 215.1 | True | 1 | Binding |
