# Qwen Runtime Fix Summary

- Timestamp UTC: `2026-05-11T20:26:43Z`
- Git SHA: `d31e5015b557711344cd1f6acc2dfc600afcd69e`
- Branch/worktree: `stage5/qwen-runtime-fix` at `D:\AI-DV\jl-stage5-qwen-runtime-fix`
- Result: local Qwen OpenAI-compatible endpoint reached and 3+3+3 workflow subset completed
- Claim boundary: local runtime/workflow readiness only; no full benchmark, no JasperGold/Moore run, no Qwen-vs-Codex comparison

## Environment

- Host OS: Windows 11 Pro 10.0.26200, PowerShell worktree rooted under `D:\AI-DV`
- WSL: Ubuntu 24.04.2 LTS on WSL2, Linux `6.6.114.1-microsoft-standard-WSL2`
- GPU: NVIDIA GeForce RTX 3090 Ti
- Windows NVIDIA-SMI: driver `591.86`, CUDA `13.1`, VRAM `24564 MiB`
- WSL NVIDIA-SMI: driver `591.86`, CUDA `13.1`, VRAM `24564 MiB`
- Python: Windows `3.11.9`; WSL `/usr/bin/python3` `3.12.3`
- WSL runtime stack installed outside the repo at `D:\AI-DV\.qwen-vllm-venv`: vLLM `0.20.2`, Torch `2.11.0+cu130`, Torch CUDA `13.0`

## Endpoint

- Model: `Qwen/Qwen3-14B-AWQ`
- Backend: vLLM direct invocation from WSL
- Endpoint: `http://127.0.0.1:8000/v1`
- Startup settings: `max_model_len=8192`, `gpu_memory_utilization=0.78`, `max_num_seqs=1`, `tensor_parallel_size=1`
- `/v1/models`: reachable
- Served model metadata reported `max_model_len=8192`
- Loaded VRAM snapshot after startup: `20406 MiB` used, `3908 MiB` free

## Launcher Findings

The repo endpoint was brought up by direct `vllm serve`, not by committing code changes. Three integration issues were found in the documented WSL launcher path:

- `ops/local-llm/run_vllm.sh` has CRLF line endings in this worktree; WSL bash failed with `set: pipefail\r: invalid option name`.
- The launcher probes `nvidia-smi --query-gpu=name,driver_version,cuda_version,memory.total`; this WSL NVIDIA-SMI rejected `cuda_version` as an invalid query field.
- vLLM `0.20.2` rejected the launcher-style reasoning flags with `vllm: error: unrecognized arguments: --enable-reasoning`; direct startup succeeded after omitting reasoning parser flags.

These findings are documented only. No workflow code, launcher code, schemas, benchmark labels, Stage 4/5 reports, or repo hygiene files were modified.

## Verification

- `/v1/models` returned `Qwen/Qwen3-14B-AWQ`.
- `LOCAL_ONLY=true` was set for workflow commands.
- Dummy cloud variables `CLOUD_OPENAI_API_KEY=dummy-not-used` and `CLOUD_OPENAI_MODEL=dummy-not-used` were present during workflow verification.
- Dry run passed:
  - `python -m app.cli workflow repair --backend local --local-only --dry-run --out-dir artifacts/qwen-runtime-dry-run`
- Local subset passed:
  - `python -m app.cli workflow demo --backend local --run-local-subset --local-only --acknowledge-local-model-run --out-dir artifacts/qwen-demo`

## Subset Result

- Report: `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`
- Manifest: `reports/local_llm/qwen_workflow_subset_manifest_20260511T202620Z.json`
- Case count: `9`
- Status: `ok`
- Valid JSON: `true`
- Cloud fallback allowed: `false`
- Cloud fallback called: `false`
- Fallback count: `0`
- LLM error count: `0`
- Latency total: `15597.22 ms`

No 30B profile was attempted because the safe 14B profile already satisfied the requested endpoint and subset smoke goals, and the 3090 Ti had less than 4 GiB free after loading the 14B AWQ endpoint.
