# RTL2Repair Results

This file is a curated summary only. It intentionally excludes raw JSON, JasperGold reports, traces, waves, logs, and generated local artifacts.

| Evidence row | Status | Scope | Claim boundary |
| --- | --- | --- | --- |
| Dry-run smoke | Passed locally | RTL intake, candidate SVA generation, quality gate, debug bundle construction, report emission | Local plumbing only; no formal result |
| Replay patch scratch apply | Passed locally | Deterministic replay diff applies to scratch RTL and patched manifest points at the scratch copy | Patch plumbing only; not an RTL correctness claim |
| JasperGold replay closure | Pending | `arbiter_rr2_bug_double_grant` target/regression recheck with `--rtl-repair-replay --jasper-check` | Measured only after a real `JASPER_BIN` run |
| Real LLM patch proposal | Pending | LLM-generated RTL patch validity/apply/closure metrics | No LLM patch performance claimed |

Current local validation:

```text
python -m compileall copilot tools evaluation scripts app
python -m pytest
python scripts/secret_scan.py

compileall: passed
pytest: 459 passed, 2 skipped
secret_scan: passed
```

Do not move a row into `final_results.md` unless it is backed by curated formal evidence with the run environment, git SHA, command, and claim boundary documented.
