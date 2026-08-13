# D-08 IRR Diagnostic — Empirical Evidence Report

**Generated from:** `08_grading/` (700 records, three judges)  
**Purpose:** characterize the PROTOCOL_LOCK Section 8 halt empirically before HANDOFF_14 disposition.

---

## 1. The Binding Failure

`mission_intent_match` minimum pairwise kappa = **0.296** (threshold 0.40). All three judges scored every record.

Pairwise breakdown on the main 700-record sample:

| Pair | Kappa | Above 0.40? |
|---|---:|---|
| GPT-4o ↔ Gemini Pro  | **0.709** | ✓ substantial agreement |
| GPT-4o ↔ Sonnet 4.6  | **0.331** | ✗ |
| Sonnet 4.6 ↔ Gemini Pro | **0.296** | ✗ — binding |

This is **not** a Gemini-reliability story. GPT-4o and Gemini agree at 0.71. Sonnet is the outlier against BOTH peers on this dimension.

---

## 2. Direction of Sonnet's Disagreement

Across all 700 records, the three-way score pattern (gpt, sonnet, gemini) distributes:

| Pattern (gpt, sonnet, gemini) | Count |
|---|---:|
| (1, 1, 1) | 568 |
| (0, 1, 0) | 50 |
| (1, 1, 0) | 35 |
| (0, 0, 0) | 21 |
| (1, 0, 1) | 13 |
| (1, 0, 0) | 7 |
| (0, 1, 1) | 4 |
| (0, 0, 1) | 2 |

- **All three agree:** 589 / 700 (84.1%)
- **Sonnet alone, scored HIGHER (1) when GPT+Gemini scored 0 (lenient):** 50
- **Sonnet alone, scored LOWER (0) when GPT+Gemini scored 1 (strict):** 13
- **Other (mixed) pattern:** 48

Of the 63 records where Sonnet disagrees with both peers, **50 are lenient (79%)** and **13 are strict (21%)**. Sonnet is not noisily off in both directions — it's **systematically biased one way** on `mission_intent_match`.

---

## 3. Per-System Effect

If the disagreement were just Sonnet noise, the Sonnet-vs-others delta would be similar across systems. If it's a systematic rubric difference that bites one system harder, the delta will vary.

| System | n | GPT-4o mean | Sonnet mean | Gemini mean | Sonnet − others |
|---|---:|---:|---:|---:|---:|
| `baseline_1` | 100 | 1.000 | 1.000 | 1.000 | +0.000 |
| `baseline_2` | 100 | 0.240 | 0.760 | 0.140 | +0.570 |
| `baseline_3` | 100 | 1.000 | 1.000 | 1.000 | +0.000 |
| `baseline_4` | 100 | 1.000 | 1.000 | 0.950 | +0.025 |
| `baseline_5` | 100 | 1.000 | 1.000 | 0.940 | +0.030 |
| `baseline_6` | 100 | 1.000 | 1.000 | 0.960 | +0.020 |
| `mandate_primary` | 100 | 0.990 | 0.810 | 0.880 | -0.125 |

---

## 4. Secondary Failures — Krippendorff Alpha

Two more dimensions are below 0.40 by Krippendorff alpha (the unified-agreement measure):

| Dimension | α | Status |
|---|---:|---|
| `trace_completeness`  | 0.281 | FAIL |
| `fabrication_count`   | 0.228 | FAIL |
| `mission_intent_match` | 0.464 | borderline (passes α, fails pairwise) |
| `gap_classification`  | 0.597 | pass |
| `minimum_coverage`    | 0.697 | pass |
| `target_coverage`     | 0.583 | pass |
| `constraint_coverage` | 0.656 | pass |

So the *coverage* dimensions (where judges count items) hold up well. The *judgment* dimensions (intent match, trace completeness, fabrication count) all fail.

---

## 5. Sample Disagreement Records — Read the Rationales

Each block shows: anon_id, system, three judges' scores, and each judge's rationale. The point is to see whether the disagreement is **principled** (different rubric thresholds) or **sloppy** (random noise).

### Sample 1  ·  `OUT-030B58FE`  ·  system: `mandate_primary`

**Scores (mission_intent_match):** GPT-4o = `1`, Sonnet = `0`, Gemini = `1` → pattern: **sonnet_vs_others** (lower)

**GPT-4o rationale:**
> The system's mission_intent captures the operational purpose of developing a comprehensive specification for reliance on others' work in ICFR audits, aligning with PCAOB AS 2201 and AS 2605, and addressing fraud-related control deficiencies as required in the ground truth.

**Sonnet rationale:**
> The system's anchor.mission_intent field contains the raw input text verbatim rather than a synthesized statement of operational purpose; the system did not generate its own mission intent capturing the PCAOB-aligned specification governance purpose—it merely echoed the input.

**Gemini rationale:**
> The system correctly captured the mission intent by embedding the full, verbatim request text in the `mission_intent` field.

---

### Sample 2  ·  `OUT-0CB7048E`  ·  system: `mandate_primary`

**Scores (mission_intent_match):** GPT-4o = `1`, Sonnet = `0`, Gemini = `1` → pattern: **sonnet_vs_others** (lower)

**GPT-4o rationale:**
> The system's mission_intent captures the operational purpose of establishing a Risk Management Council aligned with OMB Circular A-123, including key elements such as membership composition, meeting cadence, escalation protocols, integration points, and the CRO function.

**Sonnet rationale:**
> The system's anchor reproduces the raw input text verbatim but the system's own mission_intent processing reduces it to 'manual assessment and documentation' — the COA rationale states 'directly addresses the need for a manual assessment and documentation,' which fundamentally mischaracterizes the operational purpose (standing up a formal RMC with ERM governance) as a generic assessment task.

**Gemini rationale:**
> The system's `mission_intent` is a verbatim copy of the user request, which fully captures the operational purpose defined in the ground truth.

---

### Sample 3  ·  `OUT-15389986`  ·  system: `mandate_primary`

**Scores (mission_intent_match):** GPT-4o = `1`, Sonnet = `0`, Gemini = `1` → pattern: **sonnet_vs_others** (lower)

**GPT-4o rationale:**
> The system's mission_intent captures the same operational purpose as the ground truth, including the focus on PRC intelligence services' use of AI-enabled surveillance, big data analytics, and extraterritorial operations, with paraphrasing allowed.

**Sonnet rationale:**
> The system's anchor.mission_intent field merely reproduces the raw input text verbatim rather than synthesizing an operational purpose statement; the anchor.target.description is a shallow paraphrase that omits key elements such as IP theft, sub-national freelancing, physical domain indicators, and the 10-business-day routing requirement, failing to capture the full operational purpose of the ground truth.

**Gemini rationale:**
> The system's `mission_intent` field is a direct copy of the ground truth's source text, thereby capturing the correct operational purpose.

---

### Sample 4  ·  `OUT-4516E1DB`  ·  system: `mandate_primary`

**Scores (mission_intent_match):** GPT-4o = `1`, Sonnet = `0`, Gemini = `1` → pattern: **sonnet_vs_others** (lower)

**GPT-4o rationale:**
> The system's mission_intent captures the operational purpose of developing a comprehensive specification for reliance on others' work in ICFR audits, aligning with PCAOB AS 2201 and AS 2605, and addressing fraud-related control deficiencies, consistent with the ground truth.

**Sonnet rationale:**
> The system's anchor.mission_intent field contains only the raw input text verbatim, not a synthesized operational purpose statement. The system did not extract or articulate the mission intent as a structured specification governing ICFR audit reliance frameworks; it merely echoed the input prompt.

**Gemini rationale:**
> The system's mission_intent is a verbatim copy of the input prompt, which successfully captures the operational purpose.

---

### Sample 5  ·  `OUT-2FEB5A31`  ·  system: `mandate_primary`

**Scores (mission_intent_match):** GPT-4o = `1`, Sonnet = `0`, Gemini = `0` → pattern: **other** (-)

**GPT-4o rationale:**
> The system's mission_intent captures the operational purpose of assessing HTS's governance capacity and willingness, jihadist dynamics, ISIS reconstitution risks, and atrocity reporting, aligning with the ground truth despite minor paraphrasing.

**Sonnet rationale:**
> The system's anchor.mission_intent field is a near-verbatim copy of the input request text (with '36 hours' substituted for '72 hours'), but the system's own generated mission_intent field is absent as a structured output; the anchor merely stores the raw input. The system produced no synthesized mission intent statement capturing the operational purpose as defined in the ground truth (fused multi-INT assessment within 72 hours covering HTS governance capacity, jihadist reconstitution, atrocity reporting, and policymaker engagement decisions). The timeline discrepancy (36 vs 72 hours) also represents a material factual error.

**Gemini rationale:**
> The system's mission intent specifies a 36-hour timeline for the fused assessment, which directly contradicts the 72-hour timeline required by the ground truth.

---

### Sample 6  ·  `OUT-33750E0D`  ·  system: `mandate_primary`

**Scores (mission_intent_match):** GPT-4o = `1`, Sonnet = `1`, Gemini = `0` → pattern: **other** (-)

**GPT-4o rationale:**
> The system's mission_intent captures the operational purpose of conducting a comprehensive review and classification of professional service engagements over the past three fiscal years under the Sarbanes-Oxley framework, aligning with the ground truth.

**Sonnet rationale:**
> The system's anchor mission_intent field reproduces the original request verbatim, which captures the same operational purpose as the ground truth's paraphrased mission_intent regarding comprehensive review and classification of professional service engagements under SOX for the Audit Committee.

**Gemini rationale:**
> The system's summary in `anchor.minimum.description` is overly brief and omits key elements like the Sarbanes-Oxley framework, the SEC representation standard, and the specific classification categories.

---

### Sample 7  ·  `OUT-00450D0F`  ·  system: `baseline_2`

**Scores (mission_intent_match):** GPT-4o = `0`, Sonnet = `1`, Gemini = `0` → pattern: **sonnet_vs_others** (higher)

**GPT-4o rationale:**
> The system's mission intent omits key elements such as documenting risk attributes, assessing controls, and producing a risk matrix for engagement partner review, which are explicitly required in the ground truth.

**Sonnet rationale:**
> The system's mission_intent captures the core operational purpose—evaluating all identified significant risks per AS 2110 for year-end consolidated financial statement audit planning—though it omits the deliverable specifics (risk matrix with linked control assessments) and the engagement partner review purpose mentioned in the ground truth.

**Gemini rationale:**
> The system's mission intent omits several key operational purposes from the ground truth, including documenting risk attributes, producing the specific deliverable, and the purpose of partner review.

---

### Sample 8  ·  `OUT-0669F096`  ·  system: `baseline_2`

**Scores (mission_intent_match):** GPT-4o = `0`, Sonnet = `1`, Gemini = `0` → pattern: **sonnet_vs_others** (higher)

**GPT-4o rationale:**
> The system's mission intent omits key details from the ground truth, such as documenting actions for each risk entry, assigning them to management processes, and producing a draft disclosure for senior leadership review in time for the OMB Strategic Review submission window.

**Sonnet rationale:**
> The system captures updating the risk profile with proposed actions to reduce residual exposure and preparing for the Strategic Review cycle, which aligns with the ground truth's core operational purpose, though it omits the senior leadership review and OMB submission window framing.

**Gemini rationale:**
> The system's intent is a high-level summary that omits key operational requirements like documenting actions for each risk, assigning them to management processes, and producing a draft for leadership review.

---

## 6. The Key Sub-Finding (read the rationales)

The sample disagreement records expose **two distinct rubric criteria** that Sonnet applies and the other two judges do not. These are not random noise — they are two different judgment dimensions hiding inside one score:

**(A) Sonnet treats `verbatim-copy of input` as NOT a synthesis (→ score 0).**

This bites `mandate_primary` specifically. In samples 2-4, mandate_primary's `anchor.mission_intent` field is a verbatim copy of the raw user request.

- GPT-4o:  *"captures the operational purpose"* → **1**  (content matches → match)
- Gemini:  *"verbatim copy of the input prompt, which successfully captures"* → **1**  (content matches → match)
- Sonnet:  *"merely reproduces the raw input text verbatim rather than synthesizing an operational purpose statement... did not extract or articulate the mission intent as a structured specification"* → **0**  (no synthesis → no match)

Sonnet is reading the eval rubric strictly: the system was supposed to *synthesize* a mission_intent, not just echo the input. The other judges are giving credit for content matching even when the system did no synthesis work.

**This is a genuine product critique that Sonnet is catching and the other two are missing**, not a Sonnet artifact.

**(B) Sonnet treats `core captured + details omitted` as a MATCH (→ score 1).**

This bites `baseline_2` (the weakest baseline). In samples 7-8, baseline_2 paraphrases with omissions.

- GPT-4o, Gemini: *"omits key elements"* → **0**  (incomplete → no match)
- Sonnet: *"captures the core operational purpose, though it omits..."* → **1**  (core captured → match)

Sonnet is more forgiving on detail completeness when the *core* is captured. The other two judges apply a stricter completeness threshold.

---

## 7. What This Means for HANDOFF_14

**Empirical findings:**

1. The kappa fail is real, but **589/700 (84.1%) of records show full three-judge agreement**. The 0.40 threshold is conservative — α for `mission_intent_match` is 0.464, just above the unified-agreement bar.
2. The disagreement is *not* provider noise. It's two principled rubric criteria Sonnet applies that the other two judges do not: **(A)** verbatim-copy ≠ synthesis (catches `mandate_primary`), and **(B)** core-captured-with-omissions = match (gives credit to `baseline_2`).
3. **Sonnet's critique of `mandate_primary` is substantively correct** (per sample-record reading). The system is echoing input into mission_intent rather than producing a synthesized specification. GPT-4o and Gemini miss this because they grade on content alignment.
4. **Coverage dimensions hold IRR** (α 0.58–0.70). The product critique on `mandate_primary` does not depend on resolving the intent-match kappa — its coverage numbers (0.179 / 0.069 / 0.010) are robust across all three judges.
5. `trace_completeness` (α 0.28) and `fabrication_count` (α 0.23) fail because they are integer-count judgments where judges rarely agree on exact numbers. Same pattern: Sonnet is harsher on mandate_primary specifically (trace_completeness Sonnet=1.0 vs others=2.0 across every record).

**Disposition recommendations (evidence-based):**

**Recommended: publish under discovery / halt framing.** The headline is *richer* than "judges disagreed":

> Three frontier judges grading mandate specifications agreed on what to *count* (coverage α 0.58–0.70) but disagreed on two implicit rubric criteria: (1) whether verbatim-copy of the user request counts as 'synthesis', and (2) whether 'core captured + details omitted' counts as 'match'. The Sonnet judge applied both criteria more strictly on `mandate_primary` and more leniently on the weakest baseline. These are protocol-level rubric ambiguities, not judge noise — the appropriate response is to specify the rubric, not swap the judges.

**Coverage claims are publishable as-is.** No re-grading needed. mandate_primary's coverage failures (0.179 / 0.069 / 0.010 vs baselines 0.85–0.96) are the strongest empirical finding in the run and are robust across all three judges.

**Do not waste $59 re-grading.** The IRR fail is principled. Re-grading with the same rubric will reproduce the disagreement.

**For HANDOFF_14:** add a paragraph to the protocol fixing both rubric ambiguities ('verbatim input ≠ synthesis' and 'minimum threshold for what counts as a match in the presence of omissions'). Then a re-grade is a clean test of whether the protocol fix closes the gap.

**Asterisk, do not drop, the intent / trace / fabrication scores.** Report them per-judge with the rubric divergence explicitly noted. Drop only the *cross-system ranking* claim on those three dimensions.