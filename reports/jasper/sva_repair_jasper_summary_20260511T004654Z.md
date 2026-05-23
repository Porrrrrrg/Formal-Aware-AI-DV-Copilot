# Jasper-Backed SVA Repair Summary

UTC timestamp: 20260511T004654Z

Scope: deterministic SVA repair checks executed with JasperGold feedback on Moore. This is not a Codex/Qwen/cloud LLM benchmark.

- Cases: 18
- Cases by design: {"apb_regblock": 6, "arbiter_rr2": 6, "rv_buffer": 6}
- Cases by bug type: {"overbroad_property": 3, "reset_error": 2, "syntax_error": 3, "temporal_or_semantic_error": 6, "unknown_signal": 4}
- Feedback modes: {"jasper": 18}
- Syntax pass round 0: 0.611
- Repair success rate: 1.000
- Exact match final: 1.000
- Hallucinated signal rate: 0.000
- Jasper syntax pass final: 1.000
- Proven final: 1.000
- Vacuous final: 0.000
- Source counts: {"structured_fallback": 18}
- Fallback rate: 1.000

Source result: `evaluation/results/sva_repair_jasper_moore.json` on Moore; raw result file not committed.
