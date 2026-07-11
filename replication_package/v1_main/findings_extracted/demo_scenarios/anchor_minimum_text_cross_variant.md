# Demo: Anchor Minimum Text Across Variants

The Interpreter role's anchor.minimum.description verbatim across the three variants per scenario. This is the demo-era evidence for the content-tripwire mode flip: same scenario, same request paragraph, different chunks → different Interpreter output.

## volt_typhoon

### output
```
Minimally satisfy: Team, this is the CISO speaking. CISA has now published two binding-direction advisories (AA23-144A and AA24-038A) namin
```

### output_ollama
```
Minimally satisfy: Team, this is the CISO speaking. CISA has now published two binding-direction advisories (AA23-144A and AA24-038A) namin
```

### output_ollama_from_binaries
```
Minimally satisfy: Team, this is the CISO speaking. CISA has now published two binding-direction advisories (AA23-144A and AA24-038A) namin
```

## crowdstrike_outage

### output
```
Minimally satisfy: Team, this is the CIO. As we discussed at the executive briefing, the board has formally requested a strategy memo follo
```

### output_ollama
```
Three distinct strategic options for endpoint security architecture with (a) operational and capex implications, (b) residual risk profile after one year, (c) vendor-relationship and contractual changes, and (d) implementation timeline.
```

### output_ollama_from_binaries
```
Minimally satisfy: Team, this is the CIO. As we discussed at the executive briefing, the board has formally requested a strategy memo follo
```

## svb_collapse

### output
```
Minimally satisfy: Team, this is the CFO. The audit committee has asked for a strategy memo following the Silicon Valley Bank collapse of M
```

### output_ollama
```
Minimally satisfy: Team, this is the CFO. The audit committee has asked for a strategy memo following the Silicon Valley Bank collapse of M
```

### output_ollama_from_binaries
```
Three distinct strategic options with operational/capex implications, residual risk profiles modeled against SVB-class deposit outflow, contractual/personnel changes, and implementation timelines aligned with next SOX 404 cycle.
```

