# Output Quality Results

The evaluation runners track output provenance and hallucinated suspect signals. These metrics are intended for Codex-backed runs, where a failed LLM call can fall back to a deterministic path.

## Triage, Actual Packets

| System | Cases | Source | LLM Success | Fallback | LLM Error | Hallucinated Signal |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Heuristic | 30 | heuristic=30 | 0.000 | 0.000 | 0.000 | 0.000 |
| Raw-log fallback | 30 | raw_log_fallback=30 | 0.000 | 1.000 | 0.000 | 0.000 |
| Structured fallback | 30 | structured_fallback=30 | 0.000 | 1.000 | 0.000 | 0.000 |

## Coverage Closure, Actual Packets

| System | Cases | Source | LLM Success | Fallback | LLM Error |
| --- | ---: | --- | ---: | ---: | ---: |
| Raw-log fallback | 9 | raw_log_fallback=9 | 0.000 | 1.000 | 0.000 |
| Structured fallback | 9 | structured_fallback=9 | 0.000 | 1.000 | 0.000 |

Codex-backed experiments should report `source_counts`, `llm_success_rate`, `fallback_rate`, `llm_error_rate`, and `hallucinated_signal_rate` alongside accuracy. A healthy Codex run should have high `llm_success_rate`, low `fallback_rate`, and zero hallucinated suspect signals.
