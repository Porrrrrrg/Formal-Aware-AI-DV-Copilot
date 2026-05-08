# Progress Report

## Current State

- Empty GitHub repository cloned locally.
- Phase 0 scaffold created.
- Benchmark, JasperGold, parser, agent, schema, and evaluation directories created.
- Initial JasperGold smoke testing on `moore` completed for arbiter, ready/valid buffer, and APB-lite.
- Evidence packet generation and schema validation were exercised on `arbiter_rr2/bug_double_grant`.

## Next Milestones

1. Add trace dumping commands for falsified JasperGold properties.
2. Harden `parse_jg_trace.py` against actual JasperGold trace formats.
3. Add more labeled cases until the local benchmark reaches 30 diagnosis cases.
4. Replace placeholder agents with an actual model backend and JSON repair loop.
5. Add SVA generation/repair evaluation cases.
