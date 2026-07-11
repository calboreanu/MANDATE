# MANDATE-primary Provenance Evidence

Generated: 2026-06-03T11:21:39Z  
Host: lattice-ws01  
Captured by: setup/capture_provenance.sh

This file records the model and configuration pinning evidence for
PROTOCOL_LOCK Section 10. Transcribe the values into
00_preregistration/TO_FILL_TRACKER.md (rows D1-D9) and the
pre-registration before deposit.

## AEGIS repository

- path: `./AEGIS-eval`
- frozen extraction: `git archive` output, intentionally not a git repository
- tag: `mandate-eval-primary-2026q2-v1`
- commit: `4f8af83d12ef1ffdedcf7c5f53a0f9a2c062b06f`
- marker: `./AEGIS-eval/_AEGIS_EVAL_README.txt`

## MANDATE decoding parameters

- source: `./AEGIS-eval/configs/llm_defaults.json`
- llm_backend: `ollama`
- llm_base_url: `http://localhost:11434`
- llm_timeout_s: `300.0`
- llm_fallback_enabled: `true` (A1 observed zero fallback)
- llm_role_models:
  - Intake: `mandate-intake`
  - Interpreter: `mandate-interpreter`
  - Decomposition: `mandate-decomp`
  - Procedure: `mandate-procedure`
  - Binding: `mandate-binding`
  - Validation: `mandate-validation`
- llm_role_temperatures:
  - Intake: `0.0`
  - Interpreter: `0.1`
  - Decomposition: `0.2`
  - Procedure: `0.1`
  - Binding: `0.1`
  - Validation: `0.0`

## Ollama

- version: `ollama version is 0.21.1`
- models directory: `/Users/ws01admin/.ollama/models`

```
NAME                          ID              SIZE      MODIFIED     
trace-watcher:latest          84e75ec7cdb2    4.4 GB    10 days ago     
mandate-binding:latest        72a185685156    20 GB     10 days ago     
mandate-validation:latest     6b2071cfce25    20 GB     10 days ago     
trace-executor:latest         a32729a678fd    20 GB     10 days ago     
mandate-interpreter:latest    27c8e9c3110a    20 GB     10 days ago     
mandate-intake:latest         c9f9b92b86f8    5.2 GB    10 days ago     
mandate-procedure:latest      2215ac70cdc8    5.2 GB    10 days ago     
mandate-decomp:latest         01483a524475    20 GB     10 days ago     
mistral-large:123b            bbcf36dc47ad    73 GB     10 days ago     
llama3.3:70b                  a6eb4748fd29    42 GB     10 days ago     
gemma3:27b                    a418f5838eaf    17 GB     10 days ago     
qwen3:32b                     030ee887880f    20 GB     10 days ago     
qwen3:8b                      500a1f067a9f    5.2 GB    10 days ago     
lattice-planner:latest        769f84163318    20 GB     3 months ago    
test-model-fromfile:latest    895920c6c195    5.2 GB    3 months ago    
qwen3-8b-localtest:latest     ba0e2102dd01    4.6 GB    3 months ago    
codellama:13b                 9f438cb9cd58    7.4 GB    3 months ago    
mistral:7b                    6577803aa9a0    4.4 GB    3 months ago    
llama3.1:8b                   46e0c10c039e    4.9 GB    3 months ago    
```

## MANDATE backend model digests

For each model: the Ollama manifest file, its SHA-256, and the layer
digests inside it (the weights blob is one of these sha256 digests).

### mandate-intake
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/mandate-intake/latest`
- manifest sha256: `c9f9b92b86f819c8083225ef952c55a59b08018856b4d8d8077faa16416efccb`
- layer digests:
  - `sha256:0bf5f6f0b5893a10467a3b7022e1fafabfee70865d64e9212d4ca98b290b07ff`
  - `sha256:27ed580b03afb1655acfa6a21e33263086c2b592b9a35c4bd6622c52d1d694ce`
  - `sha256:a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f`
  - `sha256:ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`
  - `sha256:b750e597f749e2d740f2caf8c702a5aa4822c776d33c151d54fb0581d9856329`
  - `sha256:d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12`

### mandate-interpreter
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/mandate-interpreter/latest`
- manifest sha256: `27c8e9c3110a0436f374f5df308dd6a4e0eac1a6924ac7010623a6075121cb9b`
- layer digests:
  - `sha256:21df0760dfcc22fc7ec625283de7b1ddafc616b0c2e78189045d3baeb1483a87`
  - `sha256:3291abe70f16ee9682de7bfae08db5373ea9d6497e614aaad63340ad421d6312`
  - `sha256:785e0eca99cd1697c93660829e359aabc942df4e5f78c4983510f68439dd68dc`
  - `sha256:875256ce7b1dbe6b53d72e68c2778fc9193d3568b61bb7b58c6b8ef32ba3415f`
  - `sha256:ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`
  - `sha256:d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12`

### mandate-decomp
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/mandate-decomp/latest`
- manifest sha256: `01483a524475c9c57a21a4230b9f38449b0d3c0e25193353bc5b02ad0b73ceca`
- layer digests:
  - `sha256:3291abe70f16ee9682de7bfae08db5373ea9d6497e614aaad63340ad421d6312`
  - `sha256:7975ee66bfd5c6206788eab8256760da19f4127fa94ee0bbf79e8e181a9d5a6c`
  - `sha256:875256ce7b1dbe6b53d72e68c2778fc9193d3568b61bb7b58c6b8ef32ba3415f`
  - `sha256:8b6046de0c9151684dfa725654d7a4f6d477fb4d251b658c7f8e042705cc3fa3`
  - `sha256:ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`
  - `sha256:d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12`

### mandate-procedure
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/mandate-procedure/latest`
- manifest sha256: `2215ac70cdc86b47bc63793b522722b795dcbb4cae6a4b4d589d028543e193d9`
- layer digests:
  - `sha256:27ed580b03afb1655acfa6a21e33263086c2b592b9a35c4bd6622c52d1d694ce`
  - `sha256:348552a7d65d9f57f1fc718181228c0ac1a253ee747ac92a75b8888dd4fc706d`
  - `sha256:4b7e0cce4ab5be296885aae7d405d7cbf92f5d295748b8925baf24912d138562`
  - `sha256:a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f`
  - `sha256:ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`
  - `sha256:d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12`

### mandate-binding
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/mandate-binding/latest`
- manifest sha256: `72a185685156671f75fe598ee0eb4b08cefae0c3e17378326ab5e34042abc96d`
- layer digests:
  - `sha256:3291abe70f16ee9682de7bfae08db5373ea9d6497e614aaad63340ad421d6312`
  - `sha256:875256ce7b1dbe6b53d72e68c2778fc9193d3568b61bb7b58c6b8ef32ba3415f`
  - `sha256:ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`
  - `sha256:d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12`
  - `sha256:d96148482f9bade24938d02d18005a04cd6b0e14b033f7f317b34503e25505b3`
  - `sha256:dca468e17f66f2a1d8dc823edd38061fca4fdde3d4b7c0ea741364c13685f95f`

### mandate-validation
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/mandate-validation/latest`
- manifest sha256: `6b2071cfce25ccd78b1bcc55edacde3227ccd788d8d1f202d919d2dcd2fabbfe`
- layer digests:
  - `sha256:049d335299a83c6de592faf6bdc6abff234c8f139b372a6e266382c39710db03`
  - `sha256:3291abe70f16ee9682de7bfae08db5373ea9d6497e614aaad63340ad421d6312`
  - `sha256:9d78f5dcc3d5210ee3a734cb2e6a6c3df5216fa314f1ac922cff30db2112ef59`
  - `sha256:a7b9caca7bcd6c224074e7360e70f406aef98b4052324b0589a02e94ae28c21c`
  - `sha256:ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`
  - `sha256:d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12`

### qwen3:8b
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/qwen3/8b`
- manifest sha256: `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`
- layer digests:
  - `sha256:05a61d37b08453e59290add468e3bb2f688e23a01e967fecb0e2fa41218cea76`
  - `sha256:a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f`
  - `sha256:ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`
  - `sha256:cff3f395ef3756ab63e58b0ad1b32bb6f802905cae1472e6a12034e4246fbbdb`
  - `sha256:d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12`

### qwen3:32b
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/qwen3/32b`
- manifest sha256: `030ee887880fc378860c2dd35101da424377520441ae4bfe7be6deff8ade7840`
- layer digests:
  - `sha256:3291abe70f16ee9682de7bfae08db5373ea9d6497e614aaad63340ad421d6312`
  - `sha256:ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4`
  - `sha256:afdf5c7585b363536f93782f1e44f1b81db4237847cd8b4bd2c5c33b0d76c94b`
  - `sha256:cff3f395ef3756ab63e58b0ad1b32bb6f802905cae1472e6a12034e4246fbbdb`
  - `sha256:d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12`

### llama3.3:70b
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/llama3.3/70b`
- manifest sha256: `a6eb4748fd2990ad2952b2335a95a7f952d1a06119a0aa6a2df6cd052a93a3fa`
- layer digests:
  - `sha256:4824460d29f2058aaf6e1118a63a7a197a09bed509f0e7d4e2efb1ee273b447d`
  - `sha256:53a87df39647944ad2f0a3010a1d4a60ba76a1f8d5025bb7e76986e966d28ab6`
  - `sha256:56bb8bd477a519ffa694fc449c2413c6f0e1d3b1c88fa7e3c9d88d3ae49d4dcb`
  - `sha256:948af2743fc78a328dcb3b0f5a31b3d75f415840fdb699e8b1235978392ecf85`
  - `sha256:bc371a43ce90cc42fc9abb0d89a5959fbae91a53792d4dcd9b51aa48bd369b06`
  - `sha256:c7091aa45e9be6c15e1e5c8d5489d47f18183bf5077b3d3697924e1d18ad1b2a`

### mistral-large:123b
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/mistral-large/123b`
- manifest sha256: `bbcf36dc47addf03bc2f317b1a5e451a0b5a64417eb9e2de1963ebac4909c238`
- layer digests:
  - `sha256:06a6f77f3e9529e5c8826794c2057c2270968fae4c5cb99432d00671082e6ba8`
  - `sha256:679a26de66f6bef1d81e83649b27e0c7f6c5c15079e62542c9b96e960e8c0657`
  - `sha256:96adabcf2c08a0e1a81a2f217bd8443499a940ada2e7820aec248ca87414ab97`
  - `sha256:ac9aa3c4956dba22deb5330f3dfc21a403d74742ef7227033235a92a3808e4da`
  - `sha256:f40bfe11b0b1999a1353589c54e9de6aa2216da0d307ff98d9485dcd18ce074e`

### gemma3:27b
- manifest: `/Users/ws01admin/.ollama/models/manifests/registry.ollama.ai/library/gemma3/27b`
- manifest sha256: `a418f5838eaf7fe2cfe0a3046c8384b68ba43a4435542c942f9db00a5f342203`
- layer digests:
  - `sha256:3116c52250752e00dd06b16382e952bd33c34fd79fc4fe3a5d2c77cf7de1b14b`
  - `sha256:dd084c7d92a3c1c14cc09ae77153b903fd2024b64a100a0cc8ec9316063d2dbc`
  - `sha256:e0a42594d802e5d31cdc786deb4823edb8adff66094d49de8fffe976d753e348`
  - `sha256:e796792eba26c4d3b04b0ac5adb01a453dd9ec2dfd83b6c59cbf6fe5f30b0f68`
  - `sha256:f838f048d36876f9f411d302e8fc45cea6793a37cd978af1b6a0b042fcfb2f31`

## Python environment

- interpreter: `/Users/ws01admin/Desktop/MANDATE Evaluation/mandate_eval_2026Q2/.venv/bin/python`
- version: `3.12.12`
- full package versions: see `provenance_pip_freeze.txt` in this folder

## Transcription checklist

Map the values above into TO_FILL_TRACKER.md:

- D3 AEGIS git tag: create a tag at the commit above, then record it
- D4 MANDATE model SHA-256: the six mandate-* manifest hashes above
- D5 Ollama version: the version above
- D9 / package versions: provenance_pip_freeze.txt
