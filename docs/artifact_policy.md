# Artifact Policy

This policy defines what belongs in git and what must remain local or external.
It preserves research evidence while keeping raw machine-specific outputs out of
the repository.

## Keep In Git

Keep these artifacts tracked:

- Source code, tests, schemas, prompts, workflow definitions, and operational scripts.
- Canonical benchmark assets under `benchmarks/`.
- Demo fixtures under `examples/` that are referenced by tests or docs.
- Release ledgers, checkpoints, manifests, and artifact inventories under `reports/release/`.
- Sanitized report summaries and manifests that support claims, including Jasper,
  workflow, alignment, FVEval, benchmark, and status reports.
- Historical coordination reports when they are needed for audit trail or stage
  reconstruction.

## Keep Out Of Git

Do not commit these local artifacts:

- Raw JasperGold or EDA output: `*.log`, `*.rpt`, `*.jou`, `*.vcd`, `*.fsdb`, `*.wlf`.
- Generated Jasper work directories and raw report trees: `jasper/reports/**`,
  `jgproject/`, `.formal/`, `INCA_libs/`, `xcelium.d/`.
- Trace directories: `traces/`, `trace/`, `trace_*`, and `*_trace/`.
- Local scratch artifacts: `artifacts/**`, `dist/`, cache directories, and temp exports.
- Python caches, virtual environments, and local test caches.
- Secrets and machine-local configuration: `.env`, `*.local.json`, `*.local.yaml`.
- Raw local LLM logs, local model caches, and ad hoc prompt/response dumps.

## Sanitized Jasper Evidence

Sanitized Jasper evidence may be committed when it is bounded and reviewable:

- Markdown summaries that state command context, claim boundary, pass/fail
  status, and known limitations.
- JSON manifests that capture case IDs, statuses, hashes, and sanitized paths.
- Small fixture outputs used by tests or demos.

Raw logs, waveforms, traces, generated harness dumps, license output, and
machine-local work directories must remain in ignored local paths or external
artifact storage.

## Reports Retention

Reports are classified in `reports/index.md`:

- `current`: active evidence or a current entry point for a stage/workflow.
- `historical`: retained audit trail that may contain old branch names,
  machine paths, or superseded operational instructions.
- `archive-candidate`: generated payloads or stale coordination material that
  should be indexed before any future move.
- `owned-elsewhere`: material that should be handled by another owning effort.

Do not delete, archive, or externalize reports in a hygiene-only change unless a
cleanup plan explicitly marks the files removable and the owner has approved the
move.

## Adding New Artifacts

Before adding generated outputs:

1. Prefer a summary plus manifest over raw logs.
2. Put raw local outputs in ignored paths.
3. Add or update an entry in `reports/index.md` for new report families.
4. Keep machine-specific absolute paths out of current docs and new manifests
   unless the path is intentionally historical evidence.
5. Run `python -m pytest -q`, `python -m ruff check .`, and `git diff --check`.
