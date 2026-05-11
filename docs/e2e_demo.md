# JasperLoop End-to-End Replay Demo

The Stage 5F demo exercises the local workflow path for one representative SVA
repair case:

```bash
python -m app.cli workflow repair \
  --case examples/workflows/sva_repair_demo/demo_case.json \
  --backend replay \
  --run-intent-alignment \
  --prepare-moore-handoff \
  --out-dir artifacts/workflow-demo \
  --dry-run
```

The helper wrapper runs the same command and writes bounded report copies:

```bash
python scripts/run_e2e_demo.py
```

## What The Demo Proves

The demo proves that JasperLoop can load a structured repair case, preserve
problem context, replay a deterministic repair candidate, prepare a Moore
handoff manifest, import a sanitized verifier-result artifact, run static intent
alignment, and emit a human-reviewable `WorkflowManifest` and report without
external services.

## What It Does Not Prove

The demo does not prove production readiness, model quality, formal
equivalence, benchmark success rate, or a new JasperGold/Moore result. It does
not call Codex, Qwen, JasperGold, Moore, or any network service. It does not
change benchmark labels or reinterpret prior Stage 4/5 reports.

## Why Replay Backend Is Used

`--backend replay` keeps the demo reproducible and offline. The repair candidate
comes from `examples/workflows/sva_repair_demo/replay_candidate.json`, and the
verifier context comes from a sanitized sample artifact. This demonstrates the
workflow contract and artifact boundaries without depending on model or
verifier availability.

## Replacing Replay Later

To replace replay with Codex later, add an explicit external-send gate, send the
same structured prompt context to the Codex backend, validate the returned JSON
against the repair candidate schema, and preserve the same manifest fields for
review.

To replace replay with local Qwen later, run with `--backend local`,
`--local-only`, and `--acknowledge-local-model-run` against a configured local
OpenAI-compatible endpoint. Cloud fallback must remain disabled unless a future
policy explicitly changes that boundary.

## Moore Handoff Execution

`--prepare-moore-handoff` writes a local `moore_handoff_manifest.json`. A future
Moore-side execution would consume that manifest, run the configured proof flow
outside this dry-run command, and return a sanitized summary JSON. The workflow
then imports that JSON with `--verifier-result` or a fixture-declared verifier
sample. Raw logs, traces, license output, and generated harness dumps should not
be committed.

## Intent Alignment Versus Jasper Proof

Intent alignment is separate from Jasper proof because a property can be proven
under a harness and still be the wrong property for the intended requirement.
The Stage 5C alignment check is a static review aid for semantic risk. Jasper
proof status is verifier evidence. The workflow report records both dimensions
without treating one as a substitute for the other.
