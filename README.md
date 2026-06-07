# JasperLoop-DV

JasperLoop-DV is a JasperGold-in-the-loop AI design verification copilot research prototype.

Core principle:

- The LLM is not the verification oracle.
- JasperGold is the formal oracle when formal checks are actually run.
- The agent layer interprets structured evidence and proposes SVA repair, failure triage, and coverage closure actions.
- The project is not an AI RTL generator.

## Architecture

```text
RTL + specs + SVA + assumptions + coverage goals
        |
        v
JasperGold/Cadence runs in a configured environment
        |
        v
report / trace / vacuity / coverage parsers
        |
        v
schema-validated evidence packet
        |
        +--> SVA repair
        +--> failure triage
        +--> coverage closure
        +--> SVA generation scaffolds
        |
        v
candidate output, recommendation, or JasperGold re-check
        |
        v
DV engineer review
```

See [architecture.md](docs/architecture.md) for the component map.

## Final Results

The final curated result table is [final_results.md](evaluation/results/final_results.md).

| Task | Backend | Cases | JSON validity | Fallback | Hallucinated signal | Task metric | Formal status |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| SVA repair | local Qwen/Qwen3-14B-AWQ | 23 | 1.000 | 0.000 | 0.043 | exact/repair success 0.913 | local output only |
| SVA repair re-check | JasperGold on saved local Qwen finals | 23 | n/a | n/a | n/a | 22/23 syntax pass, 22 proven | JasperGold-backed for saved SVA repair finals |
| Failure triage | local Qwen/Qwen3-14B-AWQ | 53 | 1.000 | 0.000 | 0.000 | issue/action 1.000/1.000 | not formal proof |
| Coverage closure | local Qwen/Qwen3-14B-AWQ | 14 | 1.000 | 0.000 | n/a | gap/action 1.000/1.000 | local output only |

These rows are intentionally separated from deterministic scaffold, replay, and historical PR results.

## Quickstart

Install the package in editable mode and run the local validation suite:

```bash
python -m pip install -e .
python -m compileall copilot tools evaluation scripts
python -m pytest
python scripts/build_all_evidence_packets.py
python scripts/refresh_eval_results.py --allow-rebuild-packets
```

Local deterministic evaluation runners are available for development:

```bash
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
```

JSON outputs under `evaluation/results/` are local artifacts by default and are ignored unless explicitly curated.

Retrieval-assisted Design2SVA and RTL2Repair dry-run paths are available for
local scaffold development:

```bash
python evaluation/run_design2sva_eval.py --limit 3 --k 3 --dry-run --out evaluation/results/design2sva_eval_local.json
python tools/rtl_project_intake.py --rtl benchmarks/arbiter_rr2/rtl/arbiter_rr2_correct.sv --top arbiter_rr2 --clock clk --reset rst --reset-polarity active_high --out artifacts/rtl2repair/arbiter_intake/rtl_project_manifest.json
python evaluation/run_rtl2repair_eval.py --manifest artifacts/rtl2repair/arbiter_intake/rtl_project_manifest.json --intent "The arbiter must never grant both clients in the same cycle." --k 2 --max-sva-rounds 1 --max-rtl-rounds 0 --dry-run --out artifacts/rtl2repair/arbiter_dry_run/rtl2repair_eval.json
```

See [rtl2repair.md](docs/rtl2repair.md). RTL2Repair drafts and debugs
candidate assertions and can propose scratch-only RTL patches; it does not sign
off RTL or infer complete arbitrary-RTL specifications.

## Real LLM Backend

The model backend is intentionally generic:

```text
JASPERLOOP_LLM_CMD = command that reads prompt text from stdin and writes one JSON object to stdout
```

Preflight:

```bash
python scripts/doctor_llm_backend.py --json
python scripts/test_llm_backend_contract.py
```

See [llm_backend.md](docs/environment/llm_backend.md) for Codex CLI, generic command, and replay routes. Current final real-model results use a local vLLM `Qwen/Qwen3-14B-AWQ` backend through `JASPERLOOP_LLM_CMD`; they are not Codex CLI performance.

## JasperGold

Use the generic JasperGold scripts only in a shell where Cadence/JasperGold is available:

```bash
export JASPER_BIN=/path/to/jg
bash scripts/run_jasper_smoke.sh
bash scripts/run_jasper_sva_eval.sh
bash scripts/run_jasper_sva_repair_eval.sh
```

Moore is one possible JasperGold host environment. It is not project identity or repository structure. See [moore.md](docs/environment/moore.md).

## Repository Layout

```text
benchmarks/          RTL, properties, manifests, and benchmark cases
copilot/             agent logic, prompts, schemas, rules, and LLM adapters
evaluation/          benchmark runners, metrics, fixtures, and final results
jasper/              shared JasperGold Tcl scripts; raw reports are ignored
scripts/             validation, backend doctor, refresh, and run helpers
tools/               parsers, evidence-packet builders, and Jasper wrappers
tests/               unit and integration tests
docs/                canonical architecture, evaluation, environment, and reports
```

## Artifact Policy

Tracked:

- source code
- tests
- schemas and prompts
- benchmark collateral
- core scripts and Tcl
- curated final Markdown summaries
- small test fixtures

Ignored/local:

- raw Qwen or other LLM outputs
- JasperGold reports, traces, logs, waves, and generated harnesses
- local reports and generated PDFs
- caches and temporary run directories

See [artifact_policy.md](docs/artifact_policy.md).

## Claim Boundaries

JasperLoop-DV is a research prototype. The current repository does not claim:

- Codex CLI benchmark performance
- official FVEval performance
- production DV signoff
- full semantic intent equivalence from proof pass
- JasperGold-backed validation for triage or coverage recommendations
- generalization beyond the included benchmark scope
- RTL2Repair production signoff, full semantic equivalence, or complete
  specification inference for arbitrary RTL

See [limitations_and_claims.md](docs/limitations_and_claims.md) and [final_research_summary.md](docs/reports/final_research_summary.md).
