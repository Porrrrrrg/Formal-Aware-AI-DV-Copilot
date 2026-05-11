# Qwen Local Bring-Up Summary

- Timestamp (UTC): `2026-05-11T19:32:36Z`
- Branch: `stage5/qwen-local-bringup`
- Worktree: `D:\AI-DV\jl-stage5-qwen-bringup`
- Base Git SHA: `5c3da97ef627fb0df6f52de18760406f847d77eb`
- Status: `blocked`
- Blocker: no documented local OpenAI-compatible endpoint was reachable.

## Scope

This Stage 5G bring-up checked the existing local Qwen utilities and workflow path only. It did not start a server, download models, run a full Qwen benchmark, compare Qwen with Codex, call JasperGold/Moore, or call cloud fallback.

## Readiness Checks

| Check | Result |
| --- | --- |
| `http://127.0.0.1:8000/v1/models` | unreachable, `Unable to connect to the remote server` |
| `http://127.0.0.1:30000/v1/models` | unreachable, `Unable to connect to the remote server` |
| `http://127.0.0.1:11434/v1/models` | unreachable, `Unable to connect to the remote server` |
| `LOCAL_ONLY=true` | enforced for dry-run and healthcheck |
| Dummy cloud env vars | present; fallback remained disabled and not called |

## Recorded Runtime Metadata

- Model ID: `Qwen/Qwen3-14B-AWQ`
- Backend type: `vllm` for healthcheck default; workflow dry-run inferred `unknown` without `SERVING_BACKEND`
- Endpoint URL: `http://127.0.0.1:8000/v1`
- GPU: `NVIDIA GeForce RTX 3090 Ti`
- VRAM: `24564 MB` total (`23.99 GB`), `2227 MB` used at probe time
- Max model length: `24576`
- Healthcheck local status: `local_unavailable`
- Valid JSON: `false`
- Fallback count: `0`
- LLM error count: `1`
- Healthcheck latency: `2035.47 ms`
- Cloud fallback called: `false`
- Hallucinated signals: not applicable; subset was not run.

## Workflow Dry-Run

Command:

```powershell
python -m app.cli workflow repair --backend local --local-only --dry-run --out-dir artifacts/qwen-dry-run
```

Result: passed with `status=dry_run`, `cloud_fallback_allowed=false`, and `cloud_fallback_called=false`.

## Subset Decision

The executable 3+3+3 subset was not attempted because all checked `/v1/models` endpoints were unavailable. Running the subset without a healthy local endpoint would have produced a fallback or fake result, which is outside the Stage 5G acceptance boundary.

## Artifacts

- Bring-up manifest: `reports/local_llm/qwen_bringup_manifest_20260511T193236Z.json`
- Dry-run manifest: `artifacts/qwen-dry-run/workflow_manifest.json`
- Healthcheck artifact: `artifacts/qwen-health/qwen_health_20260511T193221Z.json`

## Validation

- `python -m app.cli workflow repair --backend local --local-only --dry-run --out-dir artifacts/qwen-dry-run`: passed
- `python -m pytest -q`: passed, `324 passed in 9.91s`
- `python -m ruff check .`: passed
- `git diff --check`: passed
