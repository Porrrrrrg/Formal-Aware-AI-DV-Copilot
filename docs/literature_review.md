# Literature Review Notes

## FVEval

FVEval motivates evaluating LLM-generated SystemVerilog Assertions with formal tools rather than text similarity alone. It separates assertion-generation tasks such as natural-language-to-SVA and design-to-SVA, and it emphasizes syntax and functional correctness under formal checking.

JasperLoop-DV uses this idea for the SVA generation and repair modes: generated assertions are checked by JasperGold and scored by syntax/proof/vacuity outcomes.

## ProofLoop

ProofLoop motivates a loop in which RTL/formal context is gathered first, an LLM generates or repairs assertions, and a formal tool gives feedback that constrains the next repair attempt. This supports the idea that JasperGold feedback should be part of the prompt context, not only a post-hoc evaluation.

JasperLoop-DV extends this architecture toward DV workflow tasks: root-cause triage, assumption debugging, and coverage closure.

## Project Positioning

This project is not AI RTL generation. It is an AI-assisted DV workflow:

- write and repair SVA
- interpret counterexamples
- distinguish RTL, property, assumption, testbench, and coverage issues
- recommend next verification actions
