# Lean and SMT Adapter Integration

This integration adds the first verifier-centric loop for Lean, Z3, and cvc5:

```text
ProblemSpec -> Candidate -> VerifierAdapter.verify -> VerifierOutcome -> diagnostics for repair
```

The adapter layer is intentionally separate from candidate generation. A caller
constructs a `ProblemSpec` and a `Candidate`; the adapter only stages files,
runs the external verifier, writes artifacts, and normalizes the result.

## Shared Protocol

The shared contracts live in:

- `app/models/core.py`
- `schemas/v1/core.schema.json`
- `app/core/protocols.py`

`VerifierOutcome` always includes:

- `ok`
- `tool`
- `status`: `passed`, `failed`, `blocked`, `unknown`, `timeout`, or `error`
- `exit_code`
- `stdout_ref`
- `stderr_ref`
- `diagnostics`
- `artifact_refs`

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
artifacts/runs/<YYYYMMDD>/<run_id>/verifier/
```

Each verifier run writes:

- `<attempt_id>_<tool>.candidate.lean` or `<attempt_id>_<tool>.candidate.smt2`
- `<attempt_id>_<tool>.run_command.txt`
- `<attempt_id>_<tool>.stdout.txt`
- `<attempt_id>_<tool>.stderr.txt`

Tool versions and solver status are stored in `VerifierOutcome.metadata`; raw
stdout and stderr are referenced only through artifact keys.

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

In JasperGold-capable environments, source the Cadence environment before running JasperGold workflows when the local installation requires it.
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
