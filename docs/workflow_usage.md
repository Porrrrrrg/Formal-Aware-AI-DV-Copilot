# JasperLoop Workflow Usage

Stage 5D adds a safe workflow wrapper:

```bash
python -m app.cli workflow --help
python -m app.cli workflow repair --dry-run --out-dir artifacts/workflow-smoke
python -m app.cli workflow triage --dry-run --case-id arbiter_A1
python -m app.cli workflow coverage --dry-run --case-id apb_C10
```

## Dry-Run First Policy

Workflow commands default to dry-run behavior. A dry-run may load local benchmark metadata,
build local stub artifacts, validate local JSON schemas, prepare local manifests, and run
static intent-alignment heuristics. It does not call Codex, Qwen, JasperGold, Moore, network
services, or cloud fallback.

The workflow manifest is the primary artifact. It records planned steps, executed local steps,
artifact references, the backend route, verifier requirements, imported verifier context, intent
alignment output, and the final report path.

## Backend Choices

- `replay`: default route. Uses existing benchmark/reference metadata or replayable local context.
- `local`: uses deterministic structured local fallbacks only.
- `codex`: external route. The workflow can plan this route only when the external-send gate is
  acknowledged, and dry-run still sends no prompt.

## External-Send Gate

External routes are blocked unless `--require-explicit-external-send` is present. This flag is an
acknowledgement for route planning, not permission to send during dry-run. In dry-run,
`external_send_allowed` remains false and no model process is invoked.

## Moore Handoff Boundary

`--prepare-moore-handoff` writes a handoff manifest that describes the future Moore/JasperGold
boundary. It does not run Moore, JasperGold, or any TCL script. Imported verifier results must be
sanitized JSON summaries, not raw logs, traces, license output, or generated harness dumps.

## Intent Alignment Boundary

`--run-intent-alignment` can run the Stage 5C static/offline intent-alignment evaluator when the
workflow has candidate SVA, reference SVA, and intent metadata. It is a heuristic review step for
semantic risk and manual-review triage. It is not a formal equivalence proof.

Proof status and intent alignment are separate. A JasperGold proof pass can show that a candidate
meets the checked property under the given assumptions, but it does not prove that the property
matches the intended requirement. The workflow records imported proof status as context only.

## Repair Metrics Boundary

Best-of-k is not single-output success. It is an upper-bound search metric that asks whether any
candidate in a set worked. Workflow reports preserve that boundary and do not reinterpret upstream
best-of-k results as the success rate of a single generated repair.

## Outputs

Typical repair dry-run outputs:

- `workflow_manifest.json`: `WorkflowManifest` with planned/executed steps and artifact refs.
- `workflow_report.md`: human-reviewable report with the claim boundary.
- `problem_spec_stub.json`: local typed stub for workflow context.
- `repair_candidate.json`: schema-compatible repair candidate.
- `candidate_stub.json`: local typed candidate stub.
- `intent_alignment_result.json`: optional, when requested and inputs are available.
- `moore_handoff_manifest.json`: optional, when requested.
