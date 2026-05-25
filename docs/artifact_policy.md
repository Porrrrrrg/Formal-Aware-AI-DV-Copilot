# Artifact Policy

Tracked files should be source-like, reviewable, and useful to a fresh clone.

## Tracked

- source code
- tests
- prompts
- JSON schemas
- benchmark RTL, properties, manifests, and cases
- core evaluation runners
- JasperGold Tcl helpers
- curated final Markdown summaries
- small fixture files needed by tests

## Ignored Or Local

- `jasper/reports/` except `jasper/reports/.gitkeep`
- `artifacts/`
- `local_reports/`
- `reports/`
- `runs/`
- raw Qwen or other LLM JSON outputs
- JasperGold logs, reports, traces, waves, and generated harnesses
- generated PDFs and local presentation exports
- caches and virtual environments

Use `git rm --cached` for accidentally tracked local artifacts. Do not replace clutter by moving it into an archive folder; merge useful content into canonical docs and delete the old file.
