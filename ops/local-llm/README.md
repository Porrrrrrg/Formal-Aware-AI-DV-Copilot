# Local Qwen Serving For JasperLoop-DV

This directory contains a local Qwen deployment route for a single NVIDIA RTX
3090 Ti. The target is a localhost OpenAI-compatible endpoint usable by
Codex-style agents and by `JASPERLOOP_LLM_CMD` wrappers.

## Decision

- Preferred serving stack: vLLM.
- Backend fallback: SGLang.
- Low-friction local fallback: Ollama.
- Default safe profile: `safe_profile` -> `Qwen/Qwen3-14B-AWQ`.
- Larger MoE profile: `big_profile` -> `Qwen/Qwen3-30B-A3B-Instruct-2507`
  or an explicitly configured local quantized 30B-A3B snapshot.
- Dense experimental profile only: `experimental_dense_profile` ->
  `Qwen/Qwen3-32B-AWQ`.
- Fast development local fallback: `Qwen/Qwen3-8B-AWQ`.
- `Qwen/Qwen3-32B-AWQ` is not used by safe or big profiles.

The first-run defaults are intentionally conservative:

- `MAX_MODEL_LEN=24576`
- `GPU_MEMORY_UTILIZATION=0.82`
- `MAX_NUM_SEQS=1`
- `TENSOR_PARALLEL_SIZE=1`
- localhost bind only: `127.0.0.1`

Raise context length toward 32768 only after local manifests show no OOMs on
real JasperLoop prompts.

## Files

- `env.example`: configuration, profiles, and fallback policy.
- `run_vllm.sh`: environment probe plus vLLM OpenAI-compatible server.
- `run_sglang.sh`: SGLang fallback server.
- `run_ollama.md`: Ollama fallback notes.
- `healthcheck.py`: JSON-only localhost healthcheck and reproducible manifest writer.

## Setup Flow

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
- Keep `QWEN_PROFILE=safe_profile` unless you are explicitly testing another
  profile.

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

## JSON-Only Healthcheck

```bash
source ops/local-llm/.env
python ops/local-llm/healthcheck.py
```

The healthcheck sends one prompt to the local model and asks for schema-shaped
JSON. It also writes:

- `reports/local_llm/qwen_health_<UTC>.json`
- `reports/local_llm/run_manifest.json`

Both files include these manifest fields:

- `model_name`
- `quantization`
- `backend`
- `gpu_name`
- `vram_gb`
- `max_model_len`
- `gpu_memory_utilization`
- `max_num_seqs`
- `LOCAL_ONLY`
- `cloud_fallback_allowed`
- `git_sha`
- `prompt_version`
- `schema_version`

If the local server is down, the report records `local_unavailable` and still
updates `run_manifest.json`.

To audit cloud fallback policy without calling cloud:

```bash
LOCAL_ONLY=false \
CLOUD_OPENAI_API_KEY="$OPENAI_API_KEY" \
CLOUD_OPENAI_MODEL="$OPENAI_MODEL" \
python ops/local-llm/healthcheck.py --check-cloud-fallback
```

The healthcheck does not execute cloud fallback. Cloud fallback is hard-disabled
while `LOCAL_ONLY=true`.

## Fallback Rules

Fallback to cloud is allowed only when `LOCAL_ONLY=false` and a cloud key/model
are present in environment variables. Keys must never be committed. The
healthcheck records fallback eligibility but does not call cloud, so it does not
create quality, latency, or cost comparisons.

Recommended fallback triggers for calling agents:

- local server unavailable or returns 5xx.
- local request timeout.
- any new OOM observed in the service log.
- latency policy only when an agent has comparable local/cloud manifests.

Recommended local degradation before cloud:

1. Lower `MAX_MODEL_LEN` from 24576 to 16384.
2. Lower `GPU_MEMORY_UTILIZATION` to 0.78.
3. Switch `QWEN_MODEL` to `Qwen/Qwen3-8B-AWQ`.
4. Use SGLang or Ollama if vLLM compatibility is blocked.

## JasperLoop-DV Integration

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

## Agent Handoff Messages

For Orchestrator:

```text
ARTIFACT_READY: localhost:8000 provides a Qwen OpenAI-compatible endpoint; default profile is safe_profile.
```

For Research/Eval:

```text
ARTIFACT_READY: local Qwen health manifest generated without cloud comparison.
```
