# Codex CLI Usage

JasperLoop-DV can use Codex CLI as the `JASPERLOOP_LLM_CMD` backend. The safe smoke test sends only a synthetic prompt:

```bash
python scripts/run_codex_llm_eval.py --task healthcheck
```

Benchmark runs send local project content to Codex/OpenAI. Use the explicit acknowledgement flag only after you are comfortable exporting the relevant prompt content.

```bash
python scripts/run_codex_llm_eval.py \
  --task sva_repair \
  --limit 3 \
  --acknowledge-external-send
```

```bash
python scripts/run_codex_llm_eval.py \
  --task triage \
  --limit 3 \
  --acknowledge-external-send
```

```bash
python scripts/run_codex_llm_eval.py \
  --task coverage \
  --limit 3 \
  --acknowledge-external-send
```

Use `--dry-run` to print the exact command without calling Codex:

```bash
python scripts/run_codex_llm_eval.py --task sva_repair --limit 3 --dry-run
```

The runner uses `copilot/llm_adapters/codex_json.py`, which asks Codex for schema-constrained JSON and returns that JSON to the existing evaluation scripts.
