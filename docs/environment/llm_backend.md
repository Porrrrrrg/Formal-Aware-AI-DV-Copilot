# LLM Backend

JasperLoop-DV uses a model-agnostic backend contract:

```text
read prompt from stdin
write exactly one JSON object to stdout
exit nonzero on failure
```

Configure:

```bash
export JASPERLOOP_LLM_CMD='python path/to/backend.py'
```

Preflight:

```bash
python scripts/doctor_llm_backend.py --json
python scripts/test_llm_backend_contract.py
```

## Routes

### Generic Command Backend

Use any noninteractive wrapper for a local or hosted model, including vLLM, Ollama, or an API-backed script, as long as it follows the stdin/stdout JSON contract.

### Codex CLI Adapter

`copilot/llm_adapters/codex_json.py` remains an optional adapter. On Windows, app-package aliases may fail from subprocess with `permission_denied`; that is an environment gate failure, not model performance.

### Offline Replay

`copilot/llm_adapters/replay_json.py` is for adapter regression and fixture replay only. Replay results are not real LLM performance.

## Reporting Rules

- Fallback-only outputs are failed environment gates.
- A real LLM result requires model output with `source=llm` or equivalent accounting.
- Deterministic scaffold, real LLM, replay, and JasperGold-backed rows must stay separate.
