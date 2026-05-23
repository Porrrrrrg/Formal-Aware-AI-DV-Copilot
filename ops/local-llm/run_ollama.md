# Ollama fallback route

Ollama is the low-friction fallback for local development, smoke tests, and
cases where vLLM/SGLang dependency compatibility is blocked. It is not the
preferred production route for this project because vLLM and SGLang expose the
Qwen3 deployment controls more directly.

## Suggested use

- Primary fallback: `qwen3:14b` or a local Qwen3 14B GGUF-derived Modelfile.
- Fast fallback: `qwen3:8b`.
- API base URL: `http://127.0.0.1:11434/v1`.
- Keep `LOCAL_ONLY=true` unless a cloud provider is explicitly allowed.

## Commands

Install Ollama from the official package for your OS, then run:

```bash
ollama pull qwen3:14b
ollama run qwen3:14b
```

For quick development:

```bash
ollama pull qwen3:8b
ollama run qwen3:8b
```

OpenAI-compatible smoke request:

```bash
curl http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:14b",
    "messages": [
      {"role": "user", "content": "Write one concise SVA assertion for a ready/valid buffer."}
    ],
    "temperature": 0.2,
    "max_tokens": 256
  }'
```

Healthcheck against Ollama:

```bash
LOCAL_BASE_URL=http://127.0.0.1:11434/v1 \
SERVED_MODEL_NAME=qwen3:14b \
python ops/local-llm/healthcheck.py --requests 3
```

## GGUF Modelfile option

If service startup must be fully offline, download GGUF weights during an
install phase and create a local `Modelfile`:

```text
FROM /srv/local-llm/models/qwen3-14b-q4_k_m.gguf
PARAMETER temperature 0.2
PARAMETER top_p 0.8
PARAMETER top_k 20
PARAMETER num_ctx 16384
```

Then register it:

```bash
ollama create jasperloop-qwen3-14b -f Modelfile
ollama run jasperloop-qwen3-14b
```

Use this path only after measuring quality on the repository prompts. GGUF
quantization choices can change repair quality and long-context behavior.
