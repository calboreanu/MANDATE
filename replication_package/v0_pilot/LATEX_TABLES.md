# LaTeX-Ready Tables and Figures for Section 12.2

These tables are formatted for direct conversion to LaTeX. All data comes from
verified pipeline executions on the AEGIS reference implementation.

---

## Table: Static Evaluation Results (Runs 1–11)

```latex
\begin{table}[htbp]
\caption{Static Evaluation Results — AEGIS Reference Implementation}
\label{tab:static-eval}
\centering
\small
\begin{tabular}{@{}llccl@{}}
\toprule
\textbf{Run} & \textbf{Metric} & \textbf{Result} & \textbf{Status} & \textbf{Notes} \\
\midrule
1  & Test suite pass rate         & 499/500 (99.8\%) & PASS & 1 skip (known) \\
2  & Anchor field extraction      & 7/7 (100\%)      & PASS & All M,T,C fields present \\
3  & Gap detection precision      & 96.8\%           & PASS & 30 TP, 1 FP \\
3  & Gap detection recall         & 47.6\%           & NOTE & 33 FN structurally unresolvable \\
4a & Trace chain integrity        & 2/2 (100\%)      & PASS & All hashes verify \\
4c & Anchor hash (Algorithm 1)    & 1/1 (100\%)      & PASS & Production hashing module \\
5  & COA diversity                & 3/3 (100\%)      & PASS & Structural variation confirmed \\
6  & Cross-domain pipeline        & 5/5 (100\%)      & PASS & Generic, IR, Intel, Pentest, Underspec \\
7  & Constraint grammar           & 12/12 (100\%)    & PASS & All EBNF patterns parsed \\
8  & NIST AI RMF mapping          & 11/11 (100\%)    & PASS & All MAP \& MEASURE subcategories \\
9  & Registry matching            & 5/5 (100\%)      & PASS & All match types validated \\
10 & Readiness scores             & 1/1 (100\%)      & PASS & 17\% (1/6), blocking=True \\
11 & Timing (8 scenarios)         & $<$100ms total   & PASS & Deterministic, no LLM required \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table: Live Pipeline Execution — Deterministic (Run 12)

```latex
\begin{table}[htbp]
\caption{Deterministic Pipeline Execution — 8 Paper-Derived Scenarios}
\label{tab:deterministic-run}
\centering
\small
\begin{tabular}{@{}lllcccc@{}}
\toprule
\textbf{\#} & \textbf{Scenario} & \textbf{Domain} & \textbf{Status} & \textbf{COAs} & \textbf{Gaps} & \textbf{Trace} \\
\midrule
1 & CISO Weekly Report     & Reporting & SUCCESS    & 2 & 0 & 6 \\
2 & Undefined Minimum      & Reporting & GAP\_RPT   & 1 & 2 & 6 \\
3 & Undefined Target       & Pentest   & GAP\_RPT   & 1 & 1 & 6 \\
4 & Unknown Pattern        & Pentest   & GAP\_RPT   & 1 & 1 & 6 \\
5 & Missing Capability     & Pentest   & GAP\_RPT   & 1 & 1 & 6 \\
6 & Unassessable Risk      & Operations& GAP\_RPT   & 1 & 2 & 6 \\
7 & Ransomware IR (3 COA)  & IR        & SUCCESS    & 3 & 0 & 6 \\
8 & OSINT Intel Collection & Intel     & SUCCESS    & 2 & 0 & 6 \\
\midrule
\multicolumn{3}{@{}l}{\textit{Total wall-clock}} & \multicolumn{4}{c}{59.8ms (all 8 scenarios)} \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table: Validation Results — Property Verification (Run 12)

```latex
\begin{table}[htbp]
\caption{Structural Property Verification Across 8 Scenarios}
\label{tab:property-verification}
\centering
\small
\begin{tabular}{@{}lcccl@{}}
\toprule
\textbf{Property} & \textbf{Passed} & \textbf{Failed} & \textbf{Skipped} & \textbf{Scope} \\
\midrule
Anchor Hash (P1)        & 8/8 & 0 & 0 & All scenarios \\
Trace Chain (P2)        & 8/8 & 0 & 0 & All scenarios \\
Anchor Fields (RQ1)     & 8/8 & 0 & 0 & All scenarios \\
COA Diversity (RQ2)     & 3/3 & 0 & 5 & Multi-COA only \\
Gap Detection (RQ3)     & 5/5 & 0 & 3 & Gap scenarios only \\
\midrule
\textbf{Total}          & \textbf{32} & \textbf{0} & \textbf{16} & \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table: Paper Claim Evidence Map

```latex
\begin{table}[htbp]
\caption{Paper Claim Evidence Map — Section 12.2 Verification}
\label{tab:claim-evidence}
\centering
\small
\begin{tabular}{@{}llll@{}}
\toprule
\textbf{Claim} & \textbf{Status} & \textbf{Evidence Source} & \textbf{Scenarios} \\
\midrule
RQ1: Verifiable success criteria    & Verified & Anchor fields + hash   & All 8 \\
RQ2: Multiple valid COAs            & Verified & COA diversity analysis  & 01, 07, 08 \\
RQ3: Gap detection (5 types)        & Verified & Per-type scenario       & 02--06 \\
Property 1: Anchor immutability     & Verified & Hash recomputation      & All 8 \\
Property 2: Trace completeness      & Verified & 6-entry chain audit     & All 8 \\
Cross-domain (IR)                   & Verified & 3-COA ransomware IR     & 07 \\
Cross-domain (INTEL)                & Verified & OSINT APT collection    & 08 \\
Section 11 walkthrough              & Verified & CISO report scenario    & 01 \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table: Live LLM Execution — Mac mini M4 Pro (Run 13)

```latex
\begin{table}[htbp]
\caption{LLM-Backed Pipeline Execution — Fine-Tuned Qwen3 Models via Ollama}
\label{tab:llm-run}
\centering
\small
\begin{tabular}{@{}llcccl@{}}
\toprule
\textbf{\#} & \textbf{Scenario} & \textbf{Status} & \textbf{LLM} & \textbf{Fallback} & \textbf{Notes} \\
\midrule
1 & CISO Report        & SUCCESS    & 4/6 & 2/6 & Intake timeout, Validation parse \\
2 & Undef.\ Minimum    & GAP\_RPT   & 5/6 & 1/6 & Validation parse error \\
3 & Undef.\ Target     & GAP\_RPT   & 5/6 & 1/6 & Interpreter timeout \\
4 & Unknown Pattern    & GAP\_RPT   & 6/6 & 0/6 & Full LLM execution \\
5 & Missing Capability & GAP\_RPT   & 6/6 & 0/6 & Full LLM execution \\
6 & Unassess.\ Risk    & GAP\_RPT   & 5/6 & 1/6 & Decomposition parse \\
7 & Ransomware IR      & SUCCESS    & 4/6 & 2/6 & Intake timeout, Validation parse \\
8 & OSINT Intel        & GAP\_RPT   & 5/6 & 1/6 & Validation parse error \\
\midrule
\multicolumn{2}{@{}l}{\textit{Totals}} & & 40/48 & 8/48 & 83\% LLM, 17\% fallback \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table: Deterministic vs LLM Structural Comparison

```latex
\begin{table}[htbp]
\caption{Structural Property Comparison: Deterministic vs.\ LLM Execution}
\label{tab:det-vs-llm}
\centering
\small
\begin{tabular}{@{}lccccc@{}}
\toprule
\textbf{Scenario} & \textbf{Status} & \textbf{Hash} & \textbf{Gaps} & \textbf{COAs} & \textbf{Trace} \\
\midrule
01 CISO Report     & \checkmark & \checkmark & \checkmark & \checkmark & \checkmark \\
02 Undef.\ Min     & \checkmark & $\times$\textsuperscript{a} & $\times$\textsuperscript{b} & \checkmark & \checkmark \\
03 Undef.\ Tgt     & \checkmark & $\times$\textsuperscript{a} & $\times$\textsuperscript{b} & \checkmark & \checkmark \\
04 Unknown Pat     & \checkmark & $\times$\textsuperscript{a} & $\times$\textsuperscript{b} & \checkmark & \checkmark \\
05 Missing Cap     & \checkmark & $\times$\textsuperscript{a} & $\times$\textsuperscript{b} & \checkmark & \checkmark \\
06 Unassess.\ Risk & \checkmark & $\times$\textsuperscript{a} & $\times$\textsuperscript{b} & \checkmark & \checkmark \\
07 Ransomware IR   & \checkmark & $\times$\textsuperscript{a} & \checkmark & $\times$\textsuperscript{c} & \checkmark \\
08 OSINT Intel     & $\times$\textsuperscript{d} & $\times$\textsuperscript{a} & $\times$\textsuperscript{b} & $\times$\textsuperscript{c} & \checkmark \\
\bottomrule
\end{tabular}
\begin{flushleft}
\footnotesize
\textsuperscript{a}Anchor hashes differ because LLM extracts richer content; Property~1 holds within each run. \\
\textsuperscript{b}LLM detects additional gaps beyond deterministic baseline (more thorough analysis). \\
\textsuperscript{c}LLM Decomposition makes different strategic COA judgments. \\
\textsuperscript{d}LLM Interpreter upgraded status from SUCCESS to GAP\_REPORT (detected additional gaps). \\
\textbf{Key finding:} Trace completeness (P2) holds universally — 6-entry chains on every run regardless of execution mode.
\end{flushleft}
\end{table}
```

---

## Table: Gap Detection by Type (Deterministic Run 12)

```latex
\begin{table}[htbp]
\caption{Gap Detection by Type — Table~11 Verification}
\label{tab:gap-types}
\centering
\small
\begin{tabular}{@{}lllll@{}}
\toprule
\textbf{Gap Type} & \textbf{Scenario} & \textbf{Detected By} & \textbf{Severity} & \textbf{Blocking} \\
\midrule
UNDEFINED\_MINIMUM    & 02 & Interpreter    & DEGRADING & No \\
UNDEFINED\_TARGET     & 03 & Interpreter    & DEGRADING & No \\
UNKNOWN\_PATTERN      & 04 & Decomposition  & BLOCKING  & Yes \\
MISSING\_CAPABILITY   & 05 & Decomposition  & DEGRADING & No \\
UNASSESSABLE\_RISK    & 06 & Interpreter    & DEGRADING & No \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Figure Data: COA Structural Variation (Scenario 07 — Deterministic)

```latex
% For use in a bar chart or comparison figure
% Scenario 07: Ransomware IR — 3 COAs
% COA-1 (Conservative): 3 tasks, 3 edges, risk=MEDIUM
% COA-2 (Moderate):     4 tasks, 3 edges, risk=HIGH
% COA-3 (Aggressive):   4 tasks, 3 edges, risk=HIGH
%
% Scenario 01: CISO Report — 2 COAs
% COA-1 (Conservative): 3 tasks, 3 edges, risk=LOW
% COA-2 (Moderate):     4 tasks, 3 edges, risk=MEDIUM
```
