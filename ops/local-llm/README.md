# Local Qwen serving for JasperLoop-DV

This directory contains a local Qwen deployment route for a single NVIDIA RTX
3090 Ti. The target is a localhost OpenAI-compatible endpoint usable by
Codex-style agents and by `JASPERLOOP_LLM_CMD` wrappers.

## Decision

- Preferred serving stack: vLLM.
- Backend fallback: SGLang.
- Low-friction fallback: Ollama.
- Default main model: `Qwen/Qwen3-14B-AWQ`.
- Fast development model: `Qwen/Qwen3-8B-AWQ`.
- Larger models: experiment only on this 24 GB single-GPU target.

The first-run defaults are intentionally conservative:

- `MAX_MODEL_LEN=24576`
- `GPU_MEMORY_UTILIZATION=0.82`
- `TENSOR_PARALLEL_SIZE=1`
- localhost bind only: `127.0.0.1`

Raise context length toward 32768 only after the healthcheck benchmark shows no
OOMs and acceptable p95 latency on real JasperLoop prompts.

## Files

- `env.example`: configuration and fallback policy.
- `run_vllm.sh`: environment probe plus vLLM OpenAI-compatible server.
- `run_sglang.sh`: SGLang fallback server.
- `run_ollama.md`: Ollama fallback notes.
- `healthcheck.py`: localhost healthcheck, latency probe, GPU/OOM logging.

## Setup flow

Use WSL/Ubuntu with the NVIDIA driver visible inside Linux. Do not run the
service as root.

```bash
cd /path/to/Formal-Aware-AI-DV-Copilot
cp ops/local-llm/env.example ops/local-llm/.env
```

Edit `ops/local-llm/.env`:

- Set `MODEL_CACHE_DIR` to a writable model directory.
- Set `LOG_DIR` to a writable log directory separate from model weights.
- Keep `ALLOW_MODEL_DOWNLOAD=false` for normal service starts.
- Set `ALLOW_MODEL_DOWNLOAD=true` only during model acquisition.

Install in a clean virtualenv that matches your local driver/CUDA capability:

```bash
python3 -m venv .venv-local-llm
source .venv-local-llm/bin/activate
python -m pip install -U pip wheel
python -m pip install "vllm>=0.8.5" openai
```

The scripts do compatibility probing at startup instead of assuming exact OS,
driver, CUDA, or cuDNN versions.

## Start vLLM

During model acquisition:

```bash
source .venv-local-llm/bin/activate
ALLOW_MODEL_DOWNLOAD=true bash ops/local-llm/run_vllm.sh
```

For offline service startup, set `QWEN_MODEL` in `.env` to the local snapshot
directory and keep `ALLOW_MODEL_DOWNLOAD=false`:

```bash
source .venv-local-llm/bin/activate
bash ops/local-llm/run_vllm.sh
```

Expected endpoint:

```text
http://127.0.0.1:8000/v1
```

Smoke request:

```bash
curl http://127.0.0.1:8000/v1/models
```

## Healthcheck and Manifest

```bash
source ops/local-llm/.env
python ops/local-llm/healthcheck.py --requests 5
```

The healthcheck appends JSONL records to `HEALTHCHECK_LOG` with:

- GPU utilization.
- VRAM used and total VRAM.
- request latency and p95 latency.
- tokens/s when the server returns usage fields.
- OOM count parsed from the service log.

To test cloud fallback behavior without enabling it by accident:

```bash
LOCAL_ONLY=false \
CLOUD_OPENAI_API_KEY="$OPENAI_API_KEY" \
CLOUD_OPENAI_MODEL="$OPENAI_MODEL" \
python ops/local-llm/healthcheck.py --check-cloud-fallback
```

Cloud fallback is disabled while `LOCAL_ONLY=true`.

## Fallback rules

Fallback to cloud is allowed only when `LOCAL_ONLY=false` and a cloud key/model
are present in environment variables. Keys must never be committed.

Recommended fallback triggers:

- local server unavailable or returns 5xx.
- local request timeout.
- any new OOM observed in the service log.
- p95 latency above `LATENCY_WARN_MS`, only when `CLOUD_FALLBACK_ON_LATENCY_WARN=true`.

Recommended local degradation before cloud:

1. Lower `MAX_MODEL_LEN` from 24576 to 16384.
2. Lower `GPU_MEMORY_UTILIZATION` to 0.78.
3. Switch `QWEN_MODEL` to `Qwen/Qwen3-8B-AWQ`.
4. Use SGLang or Ollama if vLLM compatibility is blocked.

## JasperLoop-DV integration

This repo already accepts any command that reads a prompt from stdin and writes
JSON to stdout through `JASPERLOOP_LLM_CMD`. Use a small wrapper around the
OpenAI-compatible endpoint and point it at:

```text
LOCAL_BASE_URL=http://127.0.0.1:8000/v1
SERVED_MODEL_NAME=Qwen/Qwen3-14B-AWQ
LOCAL_API_KEY=EMPTY
```

The wrapper should try local first. It may try cloud only when
`LOCAL_ONLY=false` and `CLOUD_OPENAI_API_KEY` is present.

## Agent handoff messages

For Orchestrator:

```text
ARTIFACT_READY: localhost:8000 已提供 Qwen OpenAI-compatible endpoint；默认模型为 Qwen/Qwen3-14B-AWQ。
```

For Research/Eval:

```text
ARTIFACT_READY: local Qwen healthcheck manifest scaffold 已生成；未运行真实 Qwen benchmark。
```
