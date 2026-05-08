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

Before sending benchmark prompts externally, audit the exact prompts locally:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
```

To write local prompt preview files:

```bash
python scripts/export_codex_prompts.py --task sva_repair --limit 3
```

Use `--redact-evidence` for triage or coverage previews that remove RTL context and trace events from the preview packet.

The runner uses `copilot/llm_adapters/codex_json.py`, which asks Codex for schema-constrained JSON and returns that JSON to the existing evaluation scripts.
