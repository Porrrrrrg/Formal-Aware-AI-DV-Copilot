# Output Quality Results

The evaluation runners track output provenance and hallucinated suspect signals. These metrics are intended for Codex-backed runs, where a failed LLM call can fall back to a deterministic path.

## Triage, Local Packets

| System | Cases | Source | LLM Success | Fallback | LLM Error | Hallucinated Signal |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Heuristic | 53 | heuristic=53 | 0.000 | 0.000 | 0.000 | 0.000 |
| Raw-log fallback | 53 | raw_log_fallback=53 | 0.000 | 1.000 | 0.000 | 0.000 |
| Structured fallback | 53 | structured_fallback=53 | 0.000 | 1.000 | 0.000 | 0.000 |

## Coverage Closure, Local Packets

| System | Cases | Source | LLM Success | Fallback | LLM Error |
| --- | ---: | --- | ---: | ---: | ---: |
| Raw-log fallback | 14 | raw_log_fallback=14 | 0.000 | 1.000 | 0.000 |
| Structured fallback | 14 | structured_fallback=14 | 0.000 | 1.000 | 0.000 |

Codex-backed experiments should report `source_counts`, `llm_success_rate`, `fallback_rate`, `llm_error_rate`, and `hallucinated_signal_rate` alongside accuracy. A healthy Codex run should have high `llm_success_rate`, low `fallback_rate`, and zero hallucinated suspect signals.
