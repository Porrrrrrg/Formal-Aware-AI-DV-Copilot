# Typed Core IR

This project uses a small typed intermediate representation as the contract between
orchestration, model agents, verifier adapters, and artifact storage. The v1 authority
is `app/models/core.py`; `schemas/v1/core.schema.json` is generated from those
Pydantic models and tested for drift in `tests/core/test_schemas.py`.

## Core Objects

- `RunManifest`: replay ledger for one run. It records the canonical run ID, UTC
  creation time, git SHA, dataset and prompt versions, model snapshot, toolchain
  versions, status, and the `ArtifactManifest` key.
- `ProblemSpec`: tool-neutral verification input. It contains the target tool,
  language, statement, assumptions, and artifact references for context. Tool-specific
  configuration must stay in artifacts or metadata, not as top-level fields.
- `Candidate`: generated proof, query, or repair payload. It carries producer and
  token accounting plus artifact references, but not verifier-specific output.
- `VerifierOutcome`: normalized result returned by all verifier adapters. Raw
  stdout and stderr are stored as artifacts and referenced through `stdout_ref` and
  `stderr_ref`.
- `ArtifactManifest`: per-run index of produced artifacts with sha256, size, media
  type, encoding, and canonical key.

## Naming Rules

Artifact keys are POSIX-style relative paths under the artifact root. They may not
start with `/`, contain `..`, contain Windows separators, or use empty path segments.

Canonical keys:

```text
runs/<YYYYMMDD>/<run_id>/manifest.json
problems/<problem_id>.json
runs/<YYYYMMDD>/<run_id>/candidates/<candidate_id>.json
runs/<YYYYMMDD>/<run_id>/verifier/<outcome_id>.json
runs/<YYYYMMDD>/<run_id>/verifier/<attempt_id>_<tool>.stdout.txt
runs/<YYYYMMDD>/<run_id>/verifier/<attempt_id>_<tool>.stderr.txt
runs/<YYYYMMDD>/<run_id>/artifacts.json
```

ID rules:

```text
run_<UTC timestamp>_<git short sha>_<nonce>
problem_<tool>_<statement sha12>
attempt_<0000-9999>
cand_<attempt>_<producer slug>_<content sha12>
verify_<attempt>_<tool>_<payload sha12>
```

`app/core/artifacts.py` implements these rules and the filesystem-backed
`ArtifactStore`. The store writes canonical JSON for typed objects and computes a
sha256 digest for every payload.

## Adapter Contract

Adapters depend on `app/core/protocols.py`:

- `ToolAdapter.probe()` returns availability and version information.
- `ToolAdapter.supports(problem)` checks whether a problem can be processed.
- `VerifierAdapter.verify(problem, candidate, artifacts)` returns `VerifierOutcome`.

Adapters should write raw logs, proof scripts, SMT2 files, proof objects, and traces
through the provided artifact writer, then return artifact references in
`VerifierOutcome`. They should not raise raw stderr strings across the adapter
boundary.

## State Machine

The run status transition table is defined in `app/models/core.py`:

```text
queued -> running | blocked | canceled
running -> passed | failed | blocked | review | canceled
blocked -> queued | running | canceled
review -> running | passed | failed
failed -> review
passed, canceled -> terminal
```

Use `advance_run_status()` instead of mutating `RunManifest.status` directly.

## Schema Drift Guard

The committed JSON Schema must match `core_schema_document()` exactly. CI should run:

```bash
python -m pytest tests/core/test_schemas.py
```

This catches Pydantic and schema drift, round-trip serialization failures, extra
tool-specific top-level fields, and artifact naming regressions.
