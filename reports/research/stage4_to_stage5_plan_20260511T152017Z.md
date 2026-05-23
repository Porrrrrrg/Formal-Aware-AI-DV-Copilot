# Stage 4 To Stage 5 Plan

Created UTC: `20260511T152017Z`

Base checkpoint: `581102fbe91c2724b12faf7200da5db735f68d1f`

Recommended Stage 4 tag: `stage4-checkpoint-581102f`

## Scope

Stage 5 should turn the Stage 4 evidence base into a repeatable local workflow
without changing Stage 4 claims. The work should remain explicit about which
layer produced each result: deterministic scaffold, LLM output, Moore/local
formal handoff, JasperGold proof, intent-alignment evaluation, or local Qwen
backend result.

## Stage 5A: Unified CLI / Agent Orchestrator

Build one repo-native orchestration entry point that can run bounded task lanes
with manifests, dry-run support, and explicit backend selection.

Expected capabilities:

- Select task family: SVA generation, SVA repair, failure triage, coverage
  closure, FVEval-compatible subset, or evidence packet validation.
- Select execution route: deterministic scaffold, Codex adapter if allowed by
  the operator, Qwen local adapter, or no-model validation.
- Emit a normalized run manifest with git SHA, branch, prompt/template version,
  backend, model route, commands, environment guardrails, artifact hashes, and
  claim boundary.
- Keep prompt payload export and reference-answer leakage checks available for
  audit runs.
- Keep Stage 4 report generation separate from runner logic so release
  checkpoint files remain report-only artifacts.

Exit criteria:

- A dry-run can enumerate cases and output paths without calling models or
  formal tools.
- A local deterministic run can reproduce scaffold-level metrics with a
  machine-readable manifest.
- The CLI refuses unsupported comparisons, such as Qwen-vs-Codex, unless
  required comparability metadata is present for both sides.

## Stage 5B: Moore/Local Handoff Boundary

Formalize the boundary between local candidate generation and Moore/JasperGold
proof execution.

Expected capabilities:

- Define a sanitized handoff schema for candidates that excludes raw prompts,
  raw Jasper logs, license output, generated harness dumps, and trace
  directories.
- Include stable hashes for handoff artifacts and normalized line endings.
- Support dry-run validation locally before any Moore transfer.
- Produce Moore-side manifests that separate syntax, proof, vacuity parsing,
  cover attempts, and tool-command blockers.
- Preserve the Stage 4 caveat that `not_flagged_vacuous` is not an independent
  explicit non-vacuity certificate unless a real independent certificate is
  implemented.

Exit criteria:

- Local and Moore manifests can be joined by handoff hash.
- Failed auxiliary cover/vacuity modes are represented as tool compatibility
  outcomes, not silently folded into proof success.
- Raw formal-tool artifacts remain outside committed report paths.

## Stage 5C: Intent Alignment Evaluator

Add an evaluation layer that tests whether proven assertions match the intended
task, rather than treating proof alone as success.

Expected capabilities:

- Compare generated or repaired assertions against task intent, reference
  templates where appropriate, signal constraints, temporal requirements, and
  known counterexample context.
- Report categories such as intent-aligned proven, proven but under-specified,
  proven but over-constrained, proven wrong-target, syntax-only, falsified, and
  unsupported.
- Keep exact/reference match separate from functional or semantic alignment.
- Treat Design2SVA exact/reference matching as non-equivalence unless an
  explicit equivalence procedure exists.

Exit criteria:

- Stage 5 reports can distinguish "Jasper proven" from "intent aligned and
  Jasper proven."
- Repair pass@1, repair pass@k, scaffold success, and intent-aligned formal
  success are separate metrics.
- The evaluator preserves the caveat that Jasper proof does not imply intent
  alignment.

## Stage 5D: Qwen Local Backend

Bring up Qwen as a local-only backend after a healthy OpenAI-compatible local
server exists.

Expected capabilities:

- Enforce `LOCAL_ONLY=true` and disable cloud fallback.
- Record backend, model ID, quantization, GPU, VRAM, context length, latency,
  token counts where available, and failure modes.
- Run a small bounded subset only after healthcheck passes.
- Report Qwen results independently before any comparison.

Exit criteria:

- Healthcheck passes against a local endpoint such as vLLM, SGLang, or Ollama.
- A 3+3+3 local-only subset can complete with valid manifests, or a readiness
  blocker report states exactly why it cannot.
- No Qwen-vs-Codex comparison is made until both sides have comparable backend,
  prompt, task, latency, token, fallback, hardware, and model metadata.

## Sequencing

1. Stage 5A should land first because the unified CLI/agent orchestrator defines
   the manifest and routing contract for later work.
2. Stage 5B should follow once the orchestrator can produce sanitized handoff
   artifacts and dry-run manifests.
3. Stage 5C should run after proof and scaffold outputs can be joined cleanly,
   because intent alignment needs both task metadata and candidate outcomes.
4. Stage 5D can proceed in parallel only after a healthy local Qwen endpoint is
   available; otherwise it should produce a readiness blocker report and stop.

## Non-Goals

- Do not rerun Stage 4 experiments as part of the release checkpoint.
- Do not modify Stage 4 benchmark labels, schemas, runner logic, or result
  semantics.
- Do not claim official FVEval reproduction unless the official metric and
  commercial property-equivalence flow are actually implemented.
- Do not treat best-of-candidates pass@k as single-output repair success.
- Do not treat `not_flagged_vacuous` as an independent explicit non-vacuity
  certificate.
- Do not infer intent alignment from Jasper proof alone.
- Do not make Qwen-vs-Codex claims until comparable Qwen data exists.
