# Qwen On A Single RTX 3090 Ti

## Scope

This runbook targets a local Qwen inference service for JasperLoop-DV on one
NVIDIA RTX 3090 Ti. The service exposes a localhost OpenAI-compatible API for
Codex-style agent experiments. Cloud API fallback remains explicit and
hard-disabled whenever `LOCAL_ONLY=true`.

Unknowns are intentionally probed at runtime rather than hard-coded:

- OS version: unspecified.
- NVIDIA driver version: unspecified.
- CUDA/cuDNN versions: unspecified.
- model weight filenames: unspecified.

## Sources

- https://github.com/QwenLM/Qwen3/blob/main/docs/source/deployment/vllm.md
- https://github.com/QwenLM/Qwen3/blob/main/docs/source/deployment/sglang.md
- https://qwenlm.github.io/blog/qwen3/
- https://huggingface.co/Qwen/Qwen3-14B-AWQ
- https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507
- https://huggingface.co/Qwen/Qwen3-32B-AWQ

## Profile Choice

Safe profile:

- `safe_profile`: `Qwen/Qwen3-14B-AWQ`
- Quantization: `AWQ`
- Purpose: default local RTX 3090 Ti serving profile.

Larger MoE candidate:

- `big_profile`: `Qwen/Qwen3-30B-A3B-Instruct-2507`
- Quantization: `native_or_local_quantized` by default.
- A local quantized 30B-A3B snapshot can replace this with
  `QWEN_BIG_PROFILE_MODEL`, and the exact value is recorded in the manifest.

Fast development local fallback:

- `Qwen/Qwen3-8B-AWQ`
- Purpose: CI smoke tests, lower latency local repair loops, or OOM recovery.

Experimental dense profile only:

- `experimental_dense_profile`: `Qwen/Qwen3-32B-AWQ`
- The startup scripts and healthcheck reject `Qwen/Qwen3-32B-AWQ` unless this
  profile is selected.

## Serving Route Order

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
   - Useful for quick smoke tests or GGUF workflows, not the primary production
     route for this repository.

## Safe Thresholds For RTX 3090 Ti

Start with:

- `MAX_MODEL_LEN=24576`
- `GPU_MEMORY_UTILIZATION=0.82`
- `MAX_NUM_SEQS=1`
- warning at `VRAM_WARN_FRACTION=0.92`
- batch/concurrency: one request at a time until measured.
- generation cap for agent repair tasks: 256-2048 tokens unless a task needs
  more.

Escalate only after local manifests show stable behavior:

- Move to `MAX_MODEL_LEN=32768` only after OOM count stays flat on real prompts.
- Raise `GPU_MEMORY_UTILIZATION` toward 0.88 only if the desktop/session has
  enough free VRAM and no other CUDA workloads.
- Avoid YaRN on 3090 Ti by default. Use it only for explicit long-context
  experiments.

Degrade on instability:

- OOM once: lower context to 16384 and restart.
- Repeated OOM: switch to `Qwen/Qwen3-8B-AWQ`.
- Slow normal prompts: lower context, lower max output, or use the fast local
  model.
- Local server 5xx or timeout with `LOCAL_ONLY=false`: record fallback
  eligibility. Do not compare cloud quality, latency, or cost until comparable
  manifests exist.

## Runtime Layout

Keep model weights and logs separate:

```text
/srv/local-llm/models      model cache or local snapshots
/var/log/local-llm         vLLM/SGLang/healthcheck logs
/var/run/local-llm         pid/runtime state
```

The service scripts refuse root execution. Use a normal Linux service account
with read access to model weights and write access to logs.

## Environment Probe

The startup scripts probe:

- `nvidia-smi` availability.
- GPU name, driver version, CUDA version reported by the driver, and total VRAM.
- Python version.
- Torch version, CUDA availability, Torch CUDA version, and visible GPU count.
- vLLM or SGLang import/command availability.

This keeps the deployment portable across WSL/Ubuntu systems whose exact driver
and CUDA stack are not yet known.

## Offline Service Policy

Downloading dependencies and model files may use the network during install or
model acquisition. Normal service startup defaults to offline:

- `ALLOW_MODEL_DOWNLOAD=false`
- `HF_HUB_OFFLINE=1`
- `TRANSFORMERS_OFFLINE=1`

If `QWEN_MODEL` is not a local directory and downloads are not allowed, the
scripts exit rather than silently reaching the network.

## Cloud Fallback

Fallback must be opt-in:

- `LOCAL_ONLY=true` hard-disables fallback.
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

Fallback conditions for calling agents:

- local OpenAI-compatible endpoint returns 5xx.
- local OpenAI-compatible endpoint is unavailable.
- local request times out.
- a new OOM is observed in the service log.

Every fallback event should be recorded by the calling agent in the run
manifest with provider, model, reason, and timestamp. The local healthcheck does
not call cloud; it records only local availability and fallback policy.

## JSON-Only Healthcheck

Run:

```bash
source ops/local-llm/.env
python ops/local-llm/healthcheck.py
```

Recorded manifest fields:

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
- local request status, including `local_unavailable` when the server is down.

The healthcheck writes `reports/local_llm/qwen_health_<UTC>.json` and
`reports/local_llm/run_manifest.json`. The JSONL output remains available for
append-only ingestion.

## OpenAI-Compatible Smoke Request

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-14B-AWQ",
    "messages": [
      {"role": "user", "content": "Return {\"status\":\"ok\"} as JSON."}
    ],
    "temperature": 0.0,
    "max_tokens": 64
  }'
```

## Cross-Agent Messages

To Orchestrator:

```text
ARTIFACT_READY: localhost:8000 provides a Qwen OpenAI-compatible endpoint; default profile is safe_profile.
```

To Research/Eval:

```text
ARTIFACT_READY: local Qwen health manifest generated without cloud comparison.
```
