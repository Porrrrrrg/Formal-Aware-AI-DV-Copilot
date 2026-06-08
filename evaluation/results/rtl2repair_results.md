# RTL2Repair Results

This file is a curated summary only. It intentionally excludes raw JSON, JasperGold reports, traces, waves, logs, and generated local artifacts.

| Evidence row | Status | Scope | Claim boundary |
| --- | --- | --- | --- |
| Dry-run smoke | Passed locally | RTL intake, candidate SVA generation, quality gate, debug bundle construction, report emission | Local plumbing only; no formal result |
| Replay patch scratch apply | Passed locally | Deterministic replay diff applies to scratch RTL and patched manifest points at the scratch copy | Patch plumbing only; not an RTL correctness claim |
| JasperGold replay closure | Passed on Moore | `arbiter_rr2_bug_double_grant` target recheck with deterministic mutual-exclusion SVA provider, `--rtl-repair-replay`, and `--jasper-check` | One scoped replay-patch closure only; not production signoff or real LLM patch performance |
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

JasperGold closure evidence:

```text
host: moore.wot.ece.northwestern.edu
baseline: v1.3.0-rtl2repair-infra / 4f282b697289ecf173673a2d65bd8f8946b99edd
formal_metrics_status: ran
patch_recheck.status: accepted
patch_recheck.accepted: true
target_before: p_rtl2repair_01 falsified
target_after: p_rtl2repair_01 proven
regression_total: 0
curated report: docs/reports/rtl2repair_closure_report.md
```

Do not move a row into `final_results.md` unless it is backed by curated formal evidence with the run environment, git SHA, command, and claim boundary documented.
