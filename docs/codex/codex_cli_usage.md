# Codex CLI Usage

JasperLoop-DV can use Codex CLI as the `JASPERLOOP_LLM_CMD` backend. The safe healthcheck sends only a synthetic prompt:

```bash
python scripts/run_codex_llm_eval.py --task healthcheck
```

Benchmark runs can send local project content to Codex/OpenAI. Use the acknowledgement flag only after prompt content is audited and export is approved:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
python scripts/run_codex_llm_eval.py --task sva_repair --limit 3 --acknowledge-external-send
```

For triage and coverage runs, prefer `--packet-source minimal` for pilot tests unless the experiment explicitly needs full report or trace evidence.

Offline replay can score approved JSONL outputs without another network call:

```bash
JASPERLOOP_LLM_CMD="python copilot/llm_adapters/replay_json.py --responses evaluation/fixtures/replay_sample_outputs.jsonl" \
  python evaluation/run_sva_repair_eval.py --llm --limit 1
```

Record JSON validity, fallback rate, LLM error rate, and hallucinated signal rate separately from deterministic scaffold metrics.
