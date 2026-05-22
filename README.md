# JasperLoop-DV

JasperLoop-DV is a JasperGold-in-the-loop AI design verification copilot for SVA generation, SVA repair, failure triage, and coverage-closure recommendations.

**Central principle:** the LLM is not the verification oracle. JasperGold is the formal oracle for syntax, proof, counterexamples, cover reachability, and vacuity when those checks are actually run. The LLM/agent interprets structured formal evidence and proposes candidate assertions, repairs, diagnoses, rankings, and next actions for DV engineer review.

JasperLoop-DV is not an AI RTL generator and is not a signoff authority.

## Repository Structure

```text
benchmarks/          RTL, properties, assumptions, coverage plans, manifests, cases
copilot/             agents, prompts, schemas, baselines, LLM adapters
evaluation/          metrics, evaluation runners, curated Markdown result summaries
jasper/              common JasperGold TCL flows; raw reports stay local
scripts/             local eval, prompt export, JasperGold wrapper scripts
tools/               parsers, evidence-packet builders, validators, Jasper runner
docs/                canonical project, method, environment, and result docs
artifacts/           local generated artifacts; gitignored
```

The project is repository-root based. JasperGold/Cadence runs can be executed in any environment where the required tools are available.

## Quickstart

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m compileall copilot tools evaluation scripts
python scripts/build_all_evidence_packets.py
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_all_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
python scripts/refresh_eval_results.py
```

The local evaluation path uses deterministic scaffold/fallback systems unless `--llm`, `--llm-command`, `--jasper-check`, or `--jasper-dry-run` is explicitly enabled.

## JasperGold Environment

Generic JasperGold runs use environment variables:

```bash
export JASPER_BIN=/path/to/jg
export PYTHON_BIN=python3.11
bash scripts/run_jasper_smoke.sh
bash scripts/run_jasper_sva_eval.sh
bash scripts/run_jasper_sva_repair_eval.sh
```

If your shell requires a Cadence setup script, set `JASPER_ENV` or source the setup before running the wrapper. See [docs/environment/jaspergold.md](docs/environment/jaspergold.md).

## Benchmarks

The primary local DV benchmark includes:

- `arbiter_rr2`: two-client round-robin arbiter
- `rv_buffer`: single-entry ready/valid buffer
- `apb_regblock`: small APB-lite register block
- `fifo_1r1w`: optional FIFO benchmark with reset, underflow/overflow, ordering, and simultaneous push/pop cases

The repository also includes `benchmarks/external/fveval_subset/` for a local FVEval subset import or adapter scaffold. Its results are not official FVEval reproduction results unless the exact FVEval flow is imported and run.

See [docs/benchmark_catalog.md](docs/benchmark_catalog.md).

## Current Results Boundary

Curated Markdown summaries live in `evaluation/results/`. They separate:

- deterministic scaffold/fallback results
- hosted or CLI LLM results, when explicitly run
- replayed LLM outputs
- JasperGold-backed syntax/proof/vacuity checks
- local Python validation results

Deterministic scaffold results validate plumbing and evaluation contracts. They are not Codex performance numbers.

## Claims And Non-Claims

Current claims:

- Structured evidence packets give the agent a reproducible boundary between formal evidence and LLM reasoning.
- Local deterministic runners can exercise SVA generation, repair, triage, and coverage-closure plumbing without a hosted model.
- JasperGold re-checks, when run, bind SVA syntax/proof/vacuity claims to the configured harness, assumptions, and tool environment.

Non-claims:

- The project is not production-ready.
- The agent cannot sign off RTL.
- JasperGold proof of one property does not prove semantic intent equivalence.
- FVEval integration is not complete unless the local data and evaluation flow are actually imported and run.
- Coverage witness traces are only fully integrated when parser, schema, prompts, and eval all consume witness events.

See [docs/limitations_and_claims.md](docs/limitations_and_claims.md).

## Documentation Index

- [Architecture](docs/architecture.md)
- [Methods](docs/methods.md)
- [Benchmark catalog](docs/benchmark_catalog.md)
- [Evaluation](docs/evaluation.md)
- [Artifact policy](docs/artifact_policy.md)
- [Limitations and claims](docs/limitations_and_claims.md)
- [Generic JasperGold setup](docs/environment/jaspergold.md)
- [Codex CLI usage](docs/codex/codex_cli_usage.md)
- [Prompt audit](docs/codex/prompt_audit.md)
