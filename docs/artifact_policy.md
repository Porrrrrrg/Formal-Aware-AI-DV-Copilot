# Artifact Policy

## Tracked

- source code
- prompts and playbooks
- JSON schemas
- benchmark RTL, properties, assumptions, manifests, coverage plans, and case JSON
- evaluation runners
- curated Markdown summaries in `evaluation/results/`
- canonical docs

## Local Or Untracked

- `jasper/reports/`
- raw JasperGold reports and logs
- VCD/FST/FSDB/WLF waveform and trace files
- generated harness/property files
- full JSON result outputs
- prompt preview dumps
- local reports and generated PDFs unless explicitly selected
- caches and temporary files
- full eval run artifacts under `artifacts/`, `runs/`, or `logs/`

## Rule

Commit benchmark collateral and curated summaries. Do not commit raw tool outputs or caches by default.

If a generated artifact is already tracked and should become local-only, use `git rm --cached <path>` after adding an ignore rule. Do not delete user-local results unless they are clearly disposable and the owner requested removal.
