# Stage 10: RTL2Repair Real LLM Patch Subset

## Goal

Prepare Issue #97 Phase A: evaluate real LLM RTL patch proposal quality without mixing in SVA generation quality.

The target SVA for each case is deterministic/manual. The patch source is a real LLM only when `scripts/run_rtl2repair_llm_patch_subset.py` is invoked with an explicit LLM command and `--acknowledge-external-send`.

## Scope

- Add `--regression-candidates` support to `evaluation/run_rtl2repair_eval.py`.
- Provide small regression candidate suites for `arbiter_rr2`, `rv_buffer`, and `apb_regblock`.
- Define a three-case subset manifest for Phase A.
- Provide a runner that supports dry-run planning and gated real LLM execution.
- Keep results pending until an actual real LLM patch run is executed.

## Boundaries

- Do not run external LLM calls during scaffolding.
- Do not fabricate result rows.
- Do not change `final_results.md`.
- Do not change the `v1.3.1-rtl2repair-closure` curated evidence.
- Do not commit raw JSON, Jasper reports, logs, traces, waves, or generated artifacts.

## Validation

```bash
python -m compileall copilot tools evaluation scripts app
python -m pytest
python scripts/secret_scan.py
```
