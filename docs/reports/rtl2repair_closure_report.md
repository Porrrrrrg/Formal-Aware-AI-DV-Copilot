# RTL2Repair JasperGold Closure Report

## Scope

This report records one scoped JasperGold-backed RTL2Repair replay-patch closure run for:

- Design: `arbiter_rr2`
- Bug case: `benchmarks/arbiter_rr2/rtl/arbiter_rr2_bug_double_grant.sv`
- Intent: `The arbiter must never grant both clients in the same cycle.`
- Release baseline: `v1.3.0-rtl2repair-infra`
- Baseline commit: `4f282b697289ecf173673a2d65bd8f8946b99edd`
- Follow-up issue: `#96 Run JasperGold-backed RTL2Repair replay patch closure`

This is not a production RTL signoff claim and does not measure real LLM patch proposal quality.

## Environment

- Host: `moore.wot.ece.northwestern.edu`
- Cadence environment: `/vol/eecs391/cadence.env`
- JasperGold binary: `/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg`
- Python: `python3.11`

## Command

The accepted run used a deterministic SVA provider for the target mutual-exclusion assertion and the existing deterministic RTL patch replay fixture:

```csh
source /vol/eecs391/cadence.env
setenv JASPER_BIN /vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg

python3.11 evaluation/run_rtl2repair_eval.py \
  --rtl benchmarks/arbiter_rr2/rtl/arbiter_rr2_bug_double_grant.sv \
  --top arbiter_rr2 \
  --clock clk \
  --reset rst \
  --reset-polarity active_high \
  --intent "The arbiter must never grant both clients in the same cycle." \
  --k 3 \
  --max-sva-rounds 3 \
  --max-rtl-rounds 1 \
  --llm \
  --llm-command "python3.11 /home/esf2634/rtl2repair-closure-v1.3.0-20260607-210112/deterministic_sva_provider.py" \
  --rtl-repair-replay evaluation/fixtures/rtl_repair_replay_outputs.jsonl \
  --jasper-check \
  --out artifacts/rtl2repair/arbiter_double_grant_jasper_sva_replay/rtl2repair_eval.json
```

The deterministic SVA provider emitted:

```systemverilog
p_rtl2repair_01: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));
```

This keeps the result focused on JasperGold-backed patch closure plumbing. It is not a real LLM SVA-generation or real LLM RTL-patch benchmark result.

## Result

| Field | Value |
| --- | --- |
| `formal_metrics_status` | `ran` |
| `patch_recheck.status` | `accepted` |
| `patch_recheck.accepted` | `true` |
| `patch_recheck.attempted` | `true` |
| `target_before.proof_status` | `falsified` |
| `target_before.feedback` | `Property results: p_rtl2repair_01: falsified` |
| `target_after.proof_status` | `proven` |
| `target_after.feedback` | `Property results: p_rtl2repair_01: proven` |
| `target_after.pass` | `true` |
| `regression_total` | `0` |
| `regression_pass_rate` | `1.0` |

Patch recheck acceptance reason:

```text
Patch passed target and regression rechecks.
```

## Patch Under Recheck

The replay fixture patched the simultaneous-request double-grant case from unconditional dual grants to turn-based mutual exclusion:

```diff
-        gnt0 = 1'b1;
-        gnt1 = 1'b1;
+        gnt0 = (turn == 1'b0);
+        gnt1 = (turn == 1'b1);
```

It also nested the turn update under the simultaneous-request branch so the turn state advances after the selected grant.

## Important Boundary

An initial Moore run using the default structured fallback SVA did run JasperGold, but it was rejected because the fallback assertion was `assert ... turn`, which is not the target mutual-exclusion intent. The accepted result above uses the explicit mutual-exclusion SVA shown in this report.

No raw JSON, JasperGold reports, logs, waves, traces, or generated local artifacts are committed. This report is curated evidence only.

## Claim

This evidence supports the following bounded claim:

```text
One scoped RTL2Repair replay patch for arbiter_rr2_bug_double_grant was
checked with JasperGold: the target mutual-exclusion property was falsified
before the replay patch and proven after scratch apply plus patched-manifest
recheck.
```

It does not support claims of arbitrary RTL auto-repair, production RTL signoff, or measured real LLM RTL patch proposal performance.
