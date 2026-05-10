# Lean and SMT Adapter Integration

This integration adds the first verifier-centric loop for Lean, Z3, and cvc5:

```text
ProblemSpec -> Candidate -> ToolAdapter.verify -> VerifierOutcome -> diagnostics for repair
```

The adapter layer is intentionally separate from candidate generation. A caller
constructs a `ProblemSpec` and a `Candidate`; the adapter only stages files,
runs the external verifier, writes artifacts, and normalizes the result.

## Shared Protocol

The shared contracts live in:

- `core/schemas.py`
- `core/tool_adapter.py`

`VerifierOutcome` always includes:

- `ok`
- `tool`
- `status`: `passed`, `failed`, `blocked`, or `skipped`
- `exit_code`
- `stdout_ref`
- `stderr_ref`
- `diagnostics`
- `artifact_refs`
- `manifest_ref`

Diagnostics preserve at least:

- `level`
- `message`
- `line`
- `column`

When a tool is unavailable, adapters return `status="blocked"` with
`exit_code=-1`; tests assert that shape instead of failing the whole suite.

## Artifact Layout

By default, adapters write under:

```text
artifacts/runs/<run_id>/verifier/<attempt_id>/<tool>/
```

Each verifier run writes:

- `candidate.lean` or `candidate.smt2`
- `run_command.txt`
- `stdout.txt`
- `stderr.txt`
- `manifest.json`

`manifest.json` records detected tool versions in `toolchain`. Unknown or
missing tools are recorded as `null`.

## Smoke Fixtures

Minimal fixtures live in:

```text
benchmarks/lean_smt_smoke/
  lean/
  smt/
```

The SMT fixtures cover `sat`, `unsat`, and syntax-error cases. The Lean fixtures
cover a valid theorem, a type error, and a syntax error.

## Smoke Commands

Run all adapter smoke tests:

```bash
python -m pytest tests/adapters
```

Run individual adapters:

```bash
python -m pytest tests/adapters/test_lean_smoke.py
python -m pytest tests/adapters/test_z3_smoke.py
python -m pytest tests/adapters/test_cvc5_smoke.py
```

Run the CLI wrappers directly:

```bash
python adapters/lean/verify.py --candidate benchmarks/lean_smt_smoke/lean/true.lean
python adapters/smt/z3/verify.py --candidate benchmarks/lean_smt_smoke/smt/sat.smt2 --expected sat
python adapters/smt/cvc5/verify.py --candidate benchmarks/lean_smt_smoke/smt/unsat.smt2 --expected unsat
```

The wrappers print `VerifierOutcome` JSON. They return process exit 0 by
default so orchestration can inspect structured JSON even for verifier failures.
Pass `--strict-exit` when shell status should follow verification success.

## Tool Resolution

Lean uses `lean` directly unless this repository contains `lakefile.lean` or
`lakefile.toml` and `lake` is available. In that case it runs:

```bash
lake env lean <candidate.lean>
```

Z3 uses:

```bash
z3 -smt2 <candidate.smt2>
```

cvc5 uses:

```bash
cvc5 --lang smt2 <candidate.smt2>
```

On `moore`, source the Cadence environment before running JasperGold workflows.
Lean/Z3/cvc5 are still discovered from `PATH` by these adapters.

## Repair-Friendly Diagnostics

Lean diagnostics are parsed from file-style messages:

```text
file.lean:line:column: error: message
```

SMT diagnostics are parsed from common solver parse-error formats such as:

```text
line N column M
file:N.M:
file:N:M:
```

If a verifier fails without a parseable location, the adapter still returns a
diagnostic with `line=null` and `column=null`.

## CVC4 Migration Note

No CVC4 adapter or invocation was found in the current repository census. New
SMT work targets cvc5 only. If old scripts later introduce CVC4, migrate them to
the cvc5 adapter and record any option differences in this document.
