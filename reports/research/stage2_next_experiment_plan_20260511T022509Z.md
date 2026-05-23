# Stage 2 Next Experiment Plan

UTC timestamp: 20260511T022509Z

This plan defines follow-up experiments based on Stage 2 evidence. It intentionally avoids new results and does not authorize a full Qwen benchmark until local readiness and a small local subset are healthy.

## Objectives

1. Explain and reduce the 7/18 Codex SVA repair residual behavioral failures.
2. Separate syntax repair performance from semantic and temporal repair performance.
3. Test whether counterexample-aware repair prompts improve real model repair behavior.
4. Quantify SVA repair-loop sensitivity through controlled ablations.
5. Bring up local Qwen and rerun readiness before any Qwen quality subset.
6. Defer any full Qwen benchmark until local Qwen passes readiness and a small subset.

## Experiment 1: SVA Repair Failure-Case Analysis

Question: Why did Codex repair succeed on 11/18 scaffold cases but miss 7/18?

Scope:

- Use the seven Stage 2D miss cases from `reports/llm/codex_full_error_cases_20260511T015713Z.md`.
- Classify each miss by bug type, repair intent, final scaffold failure, and whether the failure appears syntactic, signal-reference, reset-related, overbroad, or temporal/semantic.
- Do not rerun benchmarks in the analysis step.

Expected output:

- A case-level diagnostic table.
- A taxonomy of repair failure modes.
- A short list of prompt or evaluator changes to test next.

Success criteria:

- Each residual failure has a concrete hypothesized cause and one proposed intervention.

## Experiment 2: Syntax Versus Semantic/Temporal Repair Split

Question: Is SVA repair limited mainly by syntax cleanup, or by semantic/temporal property intent?

Design:

- Partition the 18 repair cases into syntax-only, unknown-signal, reset, overbroad, and temporal/semantic groups.
- Report success by group using the existing Stage 2D results first.
- For any future rerun, preserve the same partition and emit group-level metrics in the manifest.

Metrics:

- Valid JSON rate.
- Fallback rate.
- Scaffold repair success by group.
- Final exact match by group.
- Final JasperGold syntax/proof/vacuity outcomes when formal validation is added.

Success criteria:

- Group-level metrics identify whether failures concentrate in semantic/temporal cases or also affect syntax/reset cases.

## Experiment 3: Counterexample-Aware Repair Prompts

Question: Does exposing counterexample-specific failure information improve real model repair outputs?

Design:

- Compare current repair prompt against a prompt variant that explicitly structures Jasper counterexample fields, failing cycle, expected consequent, observed consequent, and relevant signal values.
- Keep benchmark split fixed.
- Keep gold labels and reference repairs out of prompts.
- Record model route, prompt version, output count, valid JSON, fallback, repair rounds, hallucinated signals, scaffold success, and final formal checks where available.

Minimum run before expansion:

- Run only the SVA repair subset first.
- Expand to all 18 SVA repair cases only if subset schema and fallback health remain clean.

Success criteria:

- Improvement over 11/18 scaffold repair success without increasing hallucinated signal rate, fallback rate, or schema drift.
- Any claimed formal improvement requires live JasperGold validation.

## Experiment 4: SVA Repair Ablations

Question: Which repair-loop components contribute to real model outcomes?

Candidate ablations:

- No feedback beyond compiler/scaffold failure.
- Jasper counterexample summary only.
- Structured signal whitelist only.
- Explicit temporal-template hints.
- One repair attempt versus multi-round repair.
- Candidate self-check requirement before final answer.

Controls:

- Same 18 repair cases.
- Same model route per comparison.
- Same schema and evaluator version.
- Separate scaffold success from formal proof success.

Success criteria:

- Identify at least one component with measurable benefit or show that current failures require a different intervention.

## Experiment 5: Local Qwen Server Bring-Up And Readiness Rerun

Question: Can the configured local Qwen route produce valid local-only structured outputs?

Prerequisites:

- Start one OpenAI-compatible local backend:
  - vLLM on `http://127.0.0.1:8000/v1`, or
  - SGLang on `http://127.0.0.1:30000/v1`, or
  - Ollama on `http://127.0.0.1:11434/v1`.
- Preserve `LOCAL_ONLY=true`.
- Keep cloud fallback disabled and verify dummy cloud variables do not cause a fallback call.

Readiness criteria:

- `/v1/models` reachable for the chosen backend.
- Healthcheck returns valid JSON.
- Manifest records model ID, quantization, backend, endpoint, GPU, VRAM, serving config, local-only policy, and cloud-not-called status.

Success criteria:

- Readiness status becomes healthy without cloud fallback.

## Experiment 6: Local Qwen Small Subset Before Full Benchmark

Question: After readiness is healthy, can local Qwen complete the same small structured-output subset without fallback?

Gate:

- Do not run this until Experiment 5 passes.

Subset:

- Same 3 SVA repair, 3 triage, and 3 coverage cases used in Stage 2B and Stage 2C.

Metrics:

- Valid JSON rate.
- Fallback rate.
- LLM error rate.
- Hallucinated signal rate where defined.
- SVA repair scaffold success.
- Triage issue/action accuracy.
- Coverage gap/action accuracy.
- Latency and token/throughput metadata where available.

Success criteria:

- Valid JSON 9/9.
- Fallback 0/9.
- LLM errors 0/9.
- No cloud fallback.

Expansion rule:

- No full Qwen benchmark until the local 3+3+3 subset is healthy and the manifest verifies local-only execution.

## Reporting Requirements

Every future experiment report should explicitly separate:

- Deterministic scaffold output.
- JasperGold-backed validation.
- Real model output by route and model.
- Fallback output.
- Schema or transport failures.

Every future claim should state:

- Benchmark case count.
- Model route and version.
- Whether final JasperGold proof was run.
- Whether raw artifacts are committed, local-only, or hash-referenced.
- Which claims remain unsupported.
