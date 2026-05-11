# Stage 2E Local Qwen Readiness

- UTC timestamp: 2026-05-11T01:38:53Z
- Git SHA: dec371bd7d4eb9aacf80a28ffc300914a7b45540
- Readiness status: blocked
- Active backend: unavailable
- Configured backend: vLLM
- Subset status: not run

## Healthcheck

Command:

```powershell
$env:LOCAL_ONLY='true'; $env:CLOUD_OPENAI_API_KEY='dummy-not-used'; $env:CLOUD_OPENAI_MODEL='dummy-not-used'; $env:HEALTHCHECK_LOG='reports/local_llm/qwen_health.jsonl'; $env:QWEN_HEALTH_REPORTS_DIR='reports/local_llm'; .\.venv\Scripts\python.exe ops\local-llm\healthcheck.py --requests 1 --check-cloud-fallback
```

Result:

- Local status: local_unavailable
- Local base URL: http://127.0.0.1:8000/v1
- HTTP status: 0
- Error: connection refused
- JSON valid: false
- Schema errors: missing_model_json
- Cloud fallback called: false

## Backend Probes

| Backend | Endpoint | Result |
| --- | --- | --- |
| vLLM | http://127.0.0.1:8000/v1/models | connection refused |
| SGLang | http://127.0.0.1:30000/v1/models | connection refused |
| Ollama | http://127.0.0.1:11434/v1/models | connection refused |

## Runtime Fields

| Field | Value |
| --- | --- |
| model ID | Qwen/Qwen3-14B-AWQ |
| quantization | AWQ |
| backend | unavailable |
| configured backend | vllm |
| GPU | NVIDIA GeForce RTX 3090 Ti |
| VRAM | 24564 MiB |
| max_model_len | 24576 |
| gpu_memory_utilization | 0.82 |
| max_num_seqs | 1 |
| LOCAL_ONLY | true |
| cloud fallback allowed | false |
| git SHA | dec371bd7d4eb9aacf80a28ffc300914a7b45540 |

## LOCAL_ONLY Verification

`LOCAL_ONLY=true` was tested with dummy cloud variables present. The healthcheck reported `cloud_fallback_allowed=false`, `fallback_policy.cloud_not_called=true`, and an empty `fallback_policy.fallback_reasons` list. No cloud fallback was executed.

## Subset Decision

The SVA repair, triage, and coverage 3-case subsets were not run because no local Qwen server was available. Running them would have required a non-local or deterministic fallback path, which is disallowed for this stage.

## Blocker

Start one local Qwen OpenAI-compatible backend before rerunning the subset:

- vLLM on http://127.0.0.1:8000/v1, or
- SGLang on http://127.0.0.1:30000/v1, or
- Ollama on http://127.0.0.1:11434/v1.
