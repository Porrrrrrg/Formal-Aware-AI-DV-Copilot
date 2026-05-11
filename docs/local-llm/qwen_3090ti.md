# Qwen on a single RTX 3090 Ti

## Scope

This runbook targets a local Qwen inference service for JasperLoop-DV on one
NVIDIA RTX 3090 Ti. The service exposes a localhost OpenAI-compatible API for
Codex-style agent experiments, while retaining an explicit cloud API fallback
for cases where local inference is unavailable or unsafe.

Unknowns are intentionally probed at runtime rather than hard-coded:

- OS version: unspecified.
- NVIDIA driver version: unspecified.
- CUDA/cuDNN versions: unspecified.
- model weight filenames: unspecified.

## Official guidance used

Qwen's deployment docs recommend vLLM for Qwen serving and show that it exposes
an OpenAI-compatible API at `http://localhost:8000` by default. The same docs
note that prebuilt vLLM has strict Torch/CUDA dependencies, so this project
does environment probing before launch instead of pinning an unverified CUDA
stack. Qwen's SGLang docs show the same OpenAI-compatible route on port 30000.
Qwen's Qwen3 release notes recommend SGLang and vLLM for deployment and Ollama,
LM Studio, llama.cpp, and related tools for local use.

Qwen's model card for `Qwen/Qwen3-14B-AWQ` identifies it as a 14.8B parameter
Qwen3 model with native 32768-token context, 131072-token YaRN extension, and
AWQ 4-bit quantization. The Qwen speed benchmark reports Qwen3-14B AWQ memory
usage under Transformers of about 9962 MB at short input and about 15323 MB at
30720-token input plus 2048 generated tokens. vLLM and SGLang allocate memory
differently, so this runbook uses conservative 3090 Ti thresholds.

Sources:

- https://github.com/QwenLM/Qwen3/blob/main/docs/source/deployment/vllm.md
- https://github.com/QwenLM/Qwen3/blob/main/docs/source/deployment/sglang.md
- https://qwenlm.github.io/blog/qwen3/
- https://huggingface.co/Qwen/Qwen3-14B-AWQ
- https://qwen.readthedocs.io/en/v3.0/getting_started/speed_benchmark.html

## Model choice

Default:

- `Qwen/Qwen3-14B-AWQ`
- Reason: best balance of coding/formal-DV usefulness, 4-bit VRAM footprint,
  and 24 GB single-GPU viability.

Fast development fallback:

- `Qwen/Qwen3-8B-AWQ`
- Use for CI smoke tests, lower latency local repair loops, or OOM recovery.

Experimental only:

- Qwen3 30B-A3B or 32B quantized variants.
- These can be useful experiments, but they should not be defaults on one
  3090 Ti because context length, KV cache, and serving overhead leave less
  operational headroom.

## Serving route order

1. vLLM
   - Preferred route.
   - Best fit for OpenAI-compatible API, batching, structured output support,
     and agent-serving ergonomics.
2. SGLang
   - First backend fallback when vLLM is blocked by compatibility or runtime
     behavior.
   - Strong Qwen3 support and OpenAI-compatible API.
3. Ollama
   - Local developer fallback.
   - Good for quick smoke tests or GGUF workflows, not the primary production
     route for this repository.

## Safe thresholds for RTX 3090 Ti

Start with:

- `MAX_MODEL_LEN=24576`
- `GPU_MEMORY_UTILIZATION=0.82`
- warning at `VRAM_WARN_FRACTION=0.92`
- batch/concurrency: one request at a time until measured.
- generation cap for agent repair tasks: 256-2048 tokens unless a task needs
  more.

Escalate only after benchmark evidence:

- Move to `MAX_MODEL_LEN=32768` when p95 latency and OOM count are stable.
- Raise `GPU_MEMORY_UTILIZATION` toward 0.88 only if the desktop/session has
  enough free VRAM and no other CUDA workloads.
- Avoid YaRN on 3090 Ti by default. Use it only for explicit long-context
  experiments; Qwen docs warn that static YaRN can affect shorter inputs.

Degrade on instability:

- OOM once: lower context to 16384 and restart.
- Repeated OOM: switch to `Qwen/Qwen3-8B-AWQ`.
- p95 latency above 60 s on normal prompts: lower context, lower max output, or
  use fast model.
- Local server 5xx or timeout with `LOCAL_ONLY=false`: allow cloud fallback.

## Runtime layout

Keep model weights and logs separate:

```text
/srv/local-llm/models      model cache or local snapshots
/var/log/local-llm         vLLM/SGLang/healthcheck logs
/var/run/local-llm         pid/runtime state
```

The service scripts refuse root execution. Use a normal Linux service account
with read access to model weights and write access to logs.

## Environment probe

The startup scripts probe:

- `nvidia-smi` availability.
- GPU name, driver version, CUDA version reported by the driver, and total VRAM.
- Python version.
- Torch version, CUDA availability, Torch CUDA version, and visible GPU count.
- vLLM or SGLang import/command availability.

This keeps the deployment portable across WSL/Ubuntu systems whose exact driver
and CUDA stack are not yet known.

## Offline service policy

Downloading dependencies and model files may use the network during install or
model acquisition. Normal service startup defaults to offline:

- `ALLOW_MODEL_DOWNLOAD=false`
- `HF_HUB_OFFLINE=1`
- `TRANSFORMERS_OFFLINE=1`

If `QWEN_MODEL` is not a local directory and downloads are not allowed, the
scripts exit rather than silently reaching the network.

## Cloud fallback

Fallback must be opt-in:

- `LOCAL_ONLY=true` disables fallback.
- `LOCAL_ONLY=false` permits fallback only when environment variables provide
  the key and model.
- API keys are read only from environment variables.

Required cloud variables:

```bash
export LOCAL_ONLY=false
export CLOUD_OPENAI_BASE_URL=https://api.openai.com/v1
export CLOUD_OPENAI_API_KEY=...
export CLOUD_OPENAI_MODEL=...
```

Fallback conditions:

- local OpenAI-compatible endpoint returns 5xx.
- local OpenAI-compatible endpoint is unavailable.
- local request times out.
- healthcheck observes a new OOM in the service log.
- p95 latency exceeds `LATENCY_WARN_MS` only if explicitly enabled.

Every fallback event should be recorded by the calling agent in the run
manifest with provider, model, reason, and timestamp.

## Monitoring

Run:

```bash
source ops/local-llm/.env
python ops/local-llm/healthcheck.py --requests 5
```

Recorded fields:

- GPU utilization.
- VRAM used and total VRAM.
- request latency min/mean/p95/max.
- tokens/s when available.
- OOM count from service logs.
- fallback eligibility and reason.

The JSONL output is suitable for Research/Eval ingestion.

## OpenAI-compatible smoke request

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-14B-AWQ",
    "messages": [
      {"role": "user", "content": "Write one concise SystemVerilog assertion for a ready/valid buffer."}
    ],
    "temperature": 0.2,
    "max_tokens": 256
  }'
```

## Cross-agent messages

To Orchestrator:

```text
ARTIFACT_READY: localhost:8000 已提供 Qwen OpenAI-compatible endpoint；默认模型为 Qwen/Qwen3-14B-AWQ。
```

To Research/Eval:

```text
ARTIFACT_READY: local Qwen healthcheck manifest scaffold 已生成；未运行真实 Qwen benchmark。
```
