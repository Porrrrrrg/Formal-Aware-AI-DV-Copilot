# RTL2Repair Integration Audit

## Branch Purpose

Branch: `feature/rtl2repair-loop`

Base reference used for this audit: `origin/main` at `8e8a7a5be68c5b0ef20a7757b144c55265ae159b`

Head: `d412d307814580c522ecaa652c60918b36d5cd54`

Purpose: stabilize the RTL2Repair closed-loop infrastructure for PR review and eventual main integration. The branch adds arbitrary RTL intake, generated-SVA checking against dynamic manifests, FormalDebugBundle triage, SVA repair support, scratch-only RTL patch proposal plumbing, patched-manifest target/regression recheck, and a deterministic replay-patch path for JasperGold closure experiments.

This branch does not claim production RTL signoff, arbitrary RTL auto-repair, or complete specification inference.

## Commit List

- `d412d30` Add RTL2Repair replay patch closure path
- `8613440` Close RTL2Repair patch recheck loop
- `4f30607` Merge origin/main into RTL2Repair loop
- `4cac6fd` Document RTL2Repair claim boundaries
- `32e9ada` Add RTL2Repair evaluation runner
- `865d3e1` Add RTL repair patch safety tools
- `3f75ae1` Add debug-backed Design2SVA repair agent
- `71a6e76` Add formal debug bundle builder
- `54c6a88` Support dynamic SVA check manifests
- `3cd2c83` Add RTL project intake manifest flow

## Feature Files

Tools:

- `tools/rtl_project_intake.py`
- `tools/check_generated_sva.py`
- `tools/build_formal_debug_bundle.py`
- `tools/apply_rtl_patch.py`
- `tools/build_patched_manifest.py`
- `tools/rtl_patch_safety.py`

Agents and prompts:

- `copilot/agents/design2sva_repair_agent.py`
- `copilot/agents/rtl_repair_agent.py`
- `copilot/prompts/design2sva_repair_prompt.md`
- `copilot/prompts/rtl_repair_prompt.md`

Schemas:

- `copilot/schemas/rtl_project_manifest.schema.json`
- `copilot/schemas/rtl2sva_task.schema.json`
- `copilot/schemas/formal_debug_bundle.schema.json`
- `copilot/schemas/design2sva_repair_candidate.schema.json`
- `copilot/schemas/rtl_repair_candidate.schema.json`
- `copilot/schemas/rtl_patch_recheck.schema.json`

Evaluation and fixtures:

- `evaluation/run_rtl2repair_eval.py`
- `evaluation/fixtures/rtl_repair_replay_outputs.jsonl`
- `scripts/run_rtl2repair_demo.py`

Tests:

- `tests/test_rtl_project_intake.py`
- `tests/test_dynamic_check_generated_sva.py`
- `tests/test_formal_debug_bundle.py`
- `tests/test_design2sva_repair_agent.py`
- `tests/test_rtl_repair_agent.py`
- `tests/test_rtl_patch_safety.py`
- `tests/test_rtl2repair_eval.py`
- `tests/test_rtl2repair_candidate_quality.py`
- `tests/test_rtl2repair_patch_recheck.py`
- `tests/test_rtl2repair_replay_patch.py`

## Documentation And Config

- `README.md` adds a bounded RTL2Repair dry-run entry point and non-claim.
- `docs/rtl2repair.md` is the canonical RTL2Repair usage and boundary document.
- `docs/limitations_and_claims.md` preserves non-claims for RTL signoff and arbitrary specification inference.
- `docs/codex/README.md` documents optional local Codex orchestration config files.
- `.codex/config.toml` and `.codex/agents/*.toml` are optional local orchestration configs, not runtime dependencies.

## Validation Commands

Commands used for local stabilization:

```bash
python -m compileall copilot tools evaluation scripts app
python -m pytest
python scripts/secret_scan.py
```

Current local validation status:

- `compileall`: passed
- `pytest`: `459 passed, 2 skipped`
- `secret_scan`: passed

## Dry-Run Smoke

```bash
python tools/rtl_project_intake.py \
  --rtl benchmarks/arbiter_rr2/rtl/arbiter_rr2_correct.sv \
  --top arbiter_rr2 \
  --clock clk \
  --reset rst \
  --reset-polarity active_high \
  --out artifacts/rtl2repair/arbiter_intake/rtl_project_manifest.json

python evaluation/run_rtl2repair_eval.py \
  --manifest artifacts/rtl2repair/arbiter_intake/rtl_project_manifest.json \
  --intent "The arbiter must never grant both clients in the same cycle." \
  --k 2 \
  --max-sva-rounds 1 \
  --max-rtl-rounds 0 \
  --dry-run \
  --out artifacts/rtl2repair/arbiter_dry_run/rtl2repair_eval.json
```

Expected status: local plumbing only, `formal_metrics_status=not_run`, no patch accepted.

## Replay Patch Closure Command

```bash
python evaluation/run_rtl2repair_eval.py \
  --rtl benchmarks/arbiter_rr2/rtl/arbiter_rr2_bug_double_grant.sv \
  --top arbiter_rr2 \
  --clock clk \
  --reset rst \
  --reset-polarity active_high \
  --intent "The arbiter must never grant both clients in the same cycle." \
  --k 3 \
  --max-sva-rounds 3 \
  --max-rtl-rounds 1 \
  --rtl-repair-replay evaluation/fixtures/rtl_repair_replay_outputs.jsonl \
  --jasper-check \
  --out artifacts/rtl2repair/arbiter_double_grant_jasper/rtl2repair_eval.json
```

This is JasperGold-backed only when run in a configured Cadence/JasperGold environment with a real `JASPER_BIN`. The deterministic replay fixture removes LLM patch-generation variance but still goes through patch safety, scratch apply, patched manifest generation, and target/regression recheck.

## Artifact Policy

Raw artifacts must remain untracked:

- `artifacts/`
- `jasper/reports/` except `jasper/reports/.gitkeep`
- top-level `reports/`
- `local_reports/`
- `runs/`
- raw logs, reports, traces, waves, and EDA project output

Curated Markdown summaries may live under `docs/reports/` or `evaluation/results/`.

Current raw-artifact check found only the allowed tracked `jasper/reports/.gitkeep`.

## Claim Boundaries

- LLM outputs are candidates, not the verification oracle.
- JasperGold is the formal oracle when formal checks actually run.
- RTL patches are proposals and require scratch apply, formal recheck, and engineer review.
- A proof pass is scoped to the checked RTL, harness, assumptions, property, tool version, and command environment.
- Dry-run and replay plumbing are not measured real LLM performance.
- No production RTL signoff or arbitrary-RTL semantic completeness is claimed.

## Known Limitations

- JasperGold replay closure is pending until run on Moore or another configured JasperGold host.
- Regression recheck currently uses accepted SVAs from the current run; native-property regression expansion is future work.
- Deterministic replay patch quality does not measure LLM patch proposal quality.
- No `final_results.md` row should be added until a curated formal result exists.

## Merge Recommendation

Open a PR from `feature/rtl2repair-loop` to `main` with a squash merge preferred for main history clarity. The PR should state that the branch is RTL2Repair infrastructure plus local validation, with JasperGold closure evidence pending unless a separate Moore/JasperGold run is attached as curated evidence.
