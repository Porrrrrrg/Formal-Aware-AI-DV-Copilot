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

For Codex-backed triage and coverage runs, the wrapper defaults to `--packet-source minimal` to avoid sending large trace/report packets. Use `--packet-source actual` only when you intentionally want full JasperGold evidence in the prompt.

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

## Offline Replay

If benchmark prompts must be run in a separate approved environment, save each
LLM output as JSONL and replay it locally without another network call:

```jsonl
{"task":"sva_repair","case_id":"repair_arbiter_mutex_syntax","property_id":"p_mutex","round":1,"response":{"property_id":"p_mutex","sva":"p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));","explanation":"Adds the missing assertion terminator."}}
```

Then point `JASPERLOOP_LLM_CMD` at the replay adapter:

```bash
JASPERLOOP_LLM_CMD="python copilot/llm_adapters/replay_json.py --responses evaluation/fixtures/replay_sample_outputs.jsonl" \
  python evaluation/run_sva_repair_eval.py --llm --limit 1
```

The replay adapter matches by `case_id`, `property_id`, optional `round`, or
`prompt_sha256`. It exits nonzero when no response is available, so the existing
evaluation runner records `llm_error` and falls back in the same way it does for
a failed hosted LLM call.
