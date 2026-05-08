# Final Report Draft

## 1. Introduction

AI-assisted DV is most useful when constrained by formal evidence. JasperLoop-DV studies how structured JasperGold feedback can improve assertion generation, repair, failure triage, and coverage closure.

## 2. Background

Topics to cover:

- formal verification
- SystemVerilog Assertions
- assumptions and overconstraint
- counterexamples
- cover reachability and vacuity

## 3. Related Work

Discuss FVEval, ProofLoop, and LLM-assisted DV/debug workflows.

## 4. System Design

Describe the JasperGold runner, evidence extractor, evidence packet, and four agent modes.

## 5. Benchmarks

Describe arbiter, ready/valid buffer, APB-lite register block, and optional FVEval subset.

## 6. Method

Explain JasperGold invocation, parser logic, repair loop, triage prompts, coverage closure prompts, baselines, and ablations.

## 7. Evaluation

Report syntax, proof, repair, triage, coverage closure, JSON validity, hallucinated signal, and unsupported recommendation metrics.

## 8. Results

Add result tables and case studies.

## 9. Error Analysis

Expected categories:

- hallucinated signal
- property-vs-RTL ambiguity
- bounded proof limitations
- vacuity and overconstraint

## 10. Limitations

Small benchmark size, manual labels, reliance on JasperGold, and no signoff guarantee.

## 11. Conclusion

Formal-tool feedback plus structured DV evidence can make AI assistance more reliable for assertion repair and failure diagnosis.
