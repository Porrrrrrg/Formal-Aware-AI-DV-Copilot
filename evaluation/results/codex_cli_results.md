# Codex CLI Results

| Check | Status | Notes |
| --- | --- | --- |
| Direct `codex exec` JSON healthcheck | Pass | Returned schema-compatible SVA repair JSON. |
| `scripts/run_codex_llm_eval.py --task healthcheck` | Pass | Verified the repository adapter path through `codex_json.py`. |
| Benchmark subset run | Pending explicit approval | Requires `--acknowledge-external-send` because prompts include local benchmark content. |

The healthcheck prompt is synthetic and does not include benchmark RTL, properties, evidence packets, or JasperGold logs. SVA repair, triage, and coverage tasks do include benchmark content and should be run only after approving external prompt export.
