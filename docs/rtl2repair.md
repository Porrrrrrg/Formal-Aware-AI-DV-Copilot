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

Deterministic replay patch closure command:

```bash
python evaluation/run_rtl2repair_eval.py \
  --rtl benchmarks/arbiter_rr2/rtl/arbiter_rr2_bug_double_grant.sv \
  --top arbiter_rr2 \
  --clock clk \
  --reset rst \
  --reset-polarity active_high \
  --intent "The arbiter must never grant both clients in the same cycle." \
  --k 3 \
  --max-sva-rounds 3 \
  --max-rtl-rounds 1 \
  --rtl-repair-replay evaluation/fixtures/rtl_repair_replay_outputs.jsonl \
  --jasper-check \
  --out artifacts/rtl2repair/arbiter_double_grant_jasper/rtl2repair_eval.json
```

This result is JasperGold-backed only when `--jasper-check` runs with a real
`JASPER_BIN` in a configured Cadence/JasperGold environment. The replay fixture
removes LLM patch-generation variance; it does not bypass patch safety,
scratch apply, patched-manifest generation, or target/regression recheck.

Patch recheck behavior:

- Candidate SVA quality gates use schema validation, local syntax scaffolding,
  hallucinated-signal detection, helper-code policy checks, clock/reset checks,
  and antecedent cover metadata.
- RTL patch proposals are considered only when triage assigns the issue to
  `rtl_design_bug` and the candidate contains a non-empty unified diff.
- Patches apply to a scratch copy by default. The original RTL file is not
  modified by the evaluator.
- `tools/build_patched_manifest.py` emits a standard `rtl_project_manifest_v1`
  whose `rtl_files` point at the scratch-patched RTL, so existing SVA check
  plumbing can re-run without a special harness path.
- The recheck gate runs the target SVA on the patched manifest and then re-runs
  accepted regression SVAs from earlier rounds. Dry-run mode records
  `not_run`; it does not count the patch as accepted.
- Patch recheck output records `target_before`, `target_after`, and
  `acceptance_reason`. A patch is accepted only when the target was reachable
  falsified before patch, the patched target proves non-vacuous, and every
  regression recheck passes.

Claim boundaries:

- RTL2Repair drafts and debugs candidate assertions and proposes RTL patches.
- It does not sign off RTL.
- Formal proof is necessary but not sufficient for full intent equivalence.
- Arbitrary RTL auto-intents are coverage aids, not complete specifications.
