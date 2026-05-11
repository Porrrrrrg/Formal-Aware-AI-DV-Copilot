---
name: signoff-readiness
description: Assess DV signoff readiness from coverage, regressions, bugs, waivers, and risk.
---

# DV Sign-off Readiness Checker Skill

## Description

Evaluate verification completeness against project sign-off criteria. Aggregates coverage metrics, open bug counts, waiver status, escape analysis, regression health, and outstanding review items into a structured sign-off readiness report with a go/no-go recommendation.

- **Requires:** Coverage DB export, regression result summary, bug tracker data (Jira/CSV), waiver files
- **Supported Inputs:** Coverage reports, regression CSVs, Jira export, waiver JSON files

> **Expertise:**
> You are an expert in verification sign-off methodology for ASIC design. You understand how to evaluate coverage completeness with appropriate waivers, assess risk from open bugs and coverage gaps, and present a defensible sign-off recommendation to project management and silicon stakeholders.

---

## When to Use This Skill

Trigger this skill when users:
- Ask whether the design is ready for tapeout or milestone sign-off
- Need to generate a sign-off report or coverage sign-off package
- Ask about coverage waivers, open bugs, or escape risk
- Mention terms like: "sign-off", "tapeout readiness", "coverage gate", "DV complete", "milestone", "escape analysis", "go/no-go"

---

## Core Workflow

### Step 1 -Gather Sign-off Criteria

Confirm project sign-off thresholds:

| Metric | Typical Threshold | Project Threshold |
|--------|------------------|-------------------|
| Functional coverage | >=100% (with waivers) | TBD |
| Code line coverage | >=90% | TBD |
| Branch coverage | >=85% | TBD |
| Toggle coverage | >=80% | TBD |
| Regression pass rate | >=95% | TBD |
| Open P1 bugs | 0 | TBD |
| Open P2 bugs | <=3 with risk assessment | TBD |
| Unreviewed waivers | 0 | TBD |

---

### Step 2 -Coverage Gate Evaluation

```
Coverage Sign-off Status:
  Functional coverage:   98.7%  - (threshold: 100% with waivers)
    Uncovered bins:        3    -all reviewed and waived (unreachable by design)
    Waiver sign-off:       RTL owner + DV lead -
  Code coverage:
    Line:    93.4%  - (threshold: 90%)
    Branch:  87.2%  - (threshold: 85%)
    Toggle:  79.1%  - (threshold: 80%) -BLOCKING

  FSM coverage:  100%  -
  Toggle coverage gap detail:
    7 signals at 0% toggle -5 are power management signals active only in power-down mode
    2 signals need root cause: u_dma.priority_flag, u_ctrl.bypass_en
    Action required before sign-off
```

---

### Step 3 -Open Bug Assessment

```
Bug Status (from Jira export 2025-03-29):
  Priority 1 (must fix):     0  -  Priority 2 (should fix):   2  -    BUG-1042: DMA burst counter off-by-one at max length
              -Risk: medium -only occurs with len=255, workaround available
              -Owner: eng-team, Fix ETA: 2025-04-02
    BUG-1051: APB timeout not triggered on infinite PREADY hold
              -Risk: low -requires testbench to stall indefinitely
              -Owner: dv-team, Fix ETA: 2025-04-05
  Priority 3 (nice to fix):  8  (acceptable for tapeout)
  Wont-fix:                  3  (risk accepted, documented)

P2 Sign-off: CONDITIONAL -requires P2 bug fixes before final go
```

---

### Step 4 -Waiver Review Status

```
Waiver Summary:
  Total waivers:              27
  RTL owner reviewed:         27  -  DV lead reviewed:           27  -  Expired waivers:             0  -  Waiver reason categories:
    Unreachable by design:    14  (confirmed with RTL owner)
    Testbench limitation:      8  (simulation model does not support)
    Low risk don't-care:       5  (feature deprecated, not used in product)
```

---

### Step 5 -Escape Analysis

Assess risk of bugs escaping to silicon:

```
Escape Risk Assessment:
  Verification approach:    Constrained-random + directed + formal (property subset)
  Formal coverage:          12 properties proved unbounded for u_axi_slave
  Assertion count:          156 assertions, 0 vacuous
  Protocol checker:         AXI4 VIP enabled for all transactions

  High-risk areas reviewed:
    CDC paths:              All 8 crossing points have 2-FF synchronizers -    Reset sequencing:       4-domain reset order verified in simulation -    Error paths:            All SLVERR/DECERR response paths exercised -    Power states:           Not in scope for this block (handled by PMU team)

  Estimated escape risk:    LOW -primary risks are P2 bugs above
```

---

### Step 6 -Sign-off Readiness Summary

```
------------------------------------------------------------------------------------------
-         DV SIGN-OFF READINESS REPORT                    --         Block: axi_slave   Date: 2025-03-29            -------------------------------------------------------------------------------------------
-METRIC                      STATUS    THRESHOLD  ACTUAL --Functional coverage         -PASS    100%*      98.7%* --Code line coverage          -PASS    90%        93.4%  --Branch coverage             -PASS    85%        87.2%  --Toggle coverage             -FAIL    80%        79.1%  --Regression pass rate        -PASS    95%        96.8%  --Open P1 bugs                -PASS    0          0      --Open P2 bugs                -COND    -         2      --Waiver review complete      -PASS    100%       100%   -------------------------------------------------------------------------------------------
-RECOMMENDATION:  CONDITIONAL GO                         --Blocking items:                                         --  1. Resolve toggle coverage gap (2 signals)            --  2. Fix or accept P2 bugs BUG-1042, BUG-1051          --  3. Re-run nightly after fixes to confirm              -------------------------------------------------------------------------------------------
* Functional coverage: 3 bins waived, all approved
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `signoff_aggregator.py` | Aggregates coverage DB, regression results, bug tracker data, and waiver files into a unified sign-off input |
| `coverage_gate_evaluator.py` | Evaluates each coverage metric against configured thresholds; returns pass/fail per gate |
| `escape_risk_scorer.py` | Scores escape risk based on verification approach, assertion count, and uncovered areas |
| `signoff_report_generator.py` | Generates the structured sign-off report in Markdown or PDF format |

---

## Validation Checklist

- [ ] All coverage thresholds confirmed with project lead
- [ ] Every coverage waiver has RTL owner + DV lead sign-off
- [ ] Zero P1 open bugs
- [ ] P2 bugs have documented risk assessment and owner
- [ ] Escape analysis completed for all high-risk areas
- [ ] Regression pass rate stable over last 3 nights
- [ ] Sign-off report reviewed by verification manager
- [ ] Archive: coverage DB, waiver file, regression result, bug list -all versioned
