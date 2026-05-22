# AGENTS.md

## Project Identity

This repository is the source tree for JasperLoop-DV, a JasperGold-in-the-loop AI design verification copilot.

The repository name may remain `Formal-Aware-AI-DV-Copilot`, but the project name in docs and reports should be `JasperLoop-DV`.

Core principle:

- The LLM is not the verification oracle.
- JasperGold is the formal oracle.
- The LLM/agent interprets structured formal evidence and proposes SVA generation, SVA repair, failure triage, and coverage closure actions.
- The project is not an AI RTL generator.

## Moore Wording Rule

`moore` is a server/environment where the project may be run. It is not part of the project architecture, implementation identity, or repository structure.

Allowed:

- `docs/environment/moore.md`
- Compatibility wrapper scripts that explain Moore is one possible JasperGold host

Not allowed:

- "implemented under moore path"
- "moore project structure"
- using `/home/.../moore/...` or `/vol/...` as a repository-root concept
- putting Moore setup in the main architecture narrative

Use environment-variable based wording instead:

- `JASPER_BIN`
- `JASPER_ENV`
- `PYTHON_BIN`
- repository root

## Tracked vs Untracked Artifacts

Tracked:

- source code
- prompts
- JSON schemas
- benchmark RTL/properties/manifests/cases
- evaluation runners
- curated Markdown result summaries
- docs

Untracked/local:

- `jasper/reports/`
- raw JasperGold logs
- traces
- generated waveform files
- local reports/PDFs unless explicitly selected
- caches
- temporary outputs
- full eval run artifacts

## Documentation Rules

Keep the canonical docs clear and non-duplicative:

- `README.md`: high-level quickstart and project summary
- `docs/architecture.md`: system architecture and dataflow
- `docs/methods.md`: structured evidence, manifests, JasperGold re-check, repair loop
- `docs/benchmark_catalog.md`: benchmark designs, cases, sources, and limitations
- `docs/evaluation.md`: runners, metrics, local/JasperGold/Codex results
- `docs/limitations_and_claims.md`: current claims, non-claims, caveats
- `docs/artifact_policy.md`: generated artifact handling
- `docs/environment/jaspergold.md`: generic JasperGold setup
- `docs/environment/moore.md`: Moore-specific instructions only
- `docs/codex/`: Codex usage, prompt audit, replay

When removing duplicated text, preserve important details by moving them to the canonical doc and replacing old files with short redirect notes if needed.

## Claims Policy

Never claim:

- Codex achieves a full benchmark score unless the Codex-backed run actually completed.
- Deterministic scaffold results are hosted LLM results.
- The system is production-ready.
- The agent can sign off RTL.
- JasperGold parsers work for all versions.
- FVEval integration is complete unless imported and evaluated.
- Coverage witness traces are fully integrated unless parser/schema/prompt/eval all support them.

Always preserve caveats around deterministic fallback results.

## Validation Commands

Run these after relevant changes when possible:

```bash
python -m compileall copilot tools evaluation scripts
python scripts/build_all_evidence_packets.py
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_all_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
python scripts/refresh_eval_results.py
```

If pytest exists:

```bash
pytest
```

For JasperGold environments only:

```bash
bash scripts/run_jasper_smoke.sh
bash scripts/run_jasper_sva_eval.sh
bash scripts/run_jasper_sva_repair_eval.sh
```

If JasperGold is unavailable, say so explicitly instead of pretending it ran.

## Coding Rules

- Prefer small, reversible changes.
- Keep compatibility wrappers when renaming scripts.
- Use environment variables instead of hardcoded host paths.
- Do not delete local artifacts unless they are clearly disposable. Prefer `.gitignore` and `git rm --cached` for tracked generated files.
- Update docs, references, and tests when renaming files.
- Report all validation commands run.
