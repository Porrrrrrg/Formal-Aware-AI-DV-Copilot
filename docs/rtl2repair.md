# RTL2Repair

RTL2Repair extends the Design2SVA flow into a local evidence loop:

```text
RTL intake -> candidate SVA generation -> dynamic SVA check -> FormalDebugBundle
-> SVA repair triage -> optional RTL patch proposal -> recheck gate
```

Local dry-run:

```bash
python evaluation/run_rtl2repair_eval.py \
  --rtl benchmarks/arbiter_rr2/rtl/arbiter_rr2_correct.sv \
  --top arbiter_rr2 \
  --clock clk \
  --reset rst \
  --reset-polarity active_high \
  --intent "The arbiter must never grant both clients in the same cycle." \
  --k 2 \
  --max-sva-rounds 1 \
  --max-rtl-rounds 0 \
  --dry-run \
  --out artifacts/rtl2repair/arbiter_dry_run/rtl2repair_eval.json
```

With JasperGold configured, remove `--dry-run` and add `--jasper-check`. If the
Jasper executable is unavailable, the runner reports `formal_metrics_status` as
`blocked` instead of fabricating measured formal metrics.

Claim boundaries:

- RTL2Repair drafts and debugs candidate assertions and proposes RTL patches.
- It does not sign off RTL.
- Formal proof is necessary but not sufficient for full intent equivalence.
- Arbitrary RTL auto-intents are coverage aids, not complete specifications.
