---
name: regression-result-analyzer
description: Analyze regression pass/fail trends, flaky tests, coverage progress, and health.
---

# Regression Result Analyzer Skill

## Description

Analyze regression run results to identify pass/fail trends, detect flaky tests, track coverage progression, prioritize failures by frequency and impact, and generate actionable regression health reports. Supports multi-seed, multi-configuration, and multi-day regression tracking.

- **Requires:** Python 3.8+, `pandas`, `matplotlib` (optional for trend plots), regression result CSV or JSON exports
- **Supported Inputs:** VCS/Xcelium/Questa regression result files, LSF/GridEngine job logs, custom result DBs

> **Expertise:**
> You are an expert in regression management and test infrastructure for large-scale chip verification. You understand how to distinguish real failures from infrastructure issues, identify flaky tests that waste debug effort, track coverage closure over time, and present regression health metrics to project management.

---

## When to Use This Skill

Trigger this skill when users:
- Ask to analyze or summarize regression results
- Need to identify flaky tests or intermittent failures
- Want to track coverage trends across multiple regression runs
- Ask about regression pass rate, failure rate, or health
- Mention terms like: "regression", "pass rate", "flaky test", "seed reproducibility", "regression health", "failing tests", "coverage trend"

---

## Core Workflow

### Step 1 -Gather Context

- **Regression Results:** CSV/JSON/log with test name, seed, pass/fail, runtime
- **Coverage Data:** Per-run coverage snapshots (optional)
- **Time Range:** Single run or multi-day trend?
- **Target Pass Rate:** Project sign-off threshold (default: 95%)

---

### Step 2 -Regression Summary

```
Regression Summary: 2025-03-29 nightly
  Total tests run:    2,400
  PASS:               2,284  (95.2%)
  FAIL:               116    (4.8%)
  TIMEOUT:              8    (0.3%)
  Infrastructure err:   4    (0.2%)

Coverage (this run):
  Functional:  87.3%  (+1.2% vs. previous run)
  Code line:   93.1%  (+0.4%)
  Toggle:      81.6%  (+0.2%)

Sign-off status: -FAILING -pass rate below 95% target for 2 of 5 test groups
```

---

### Step 3 -Failure Analysis

#### 3.1 Failure Frequency Table

```
Top Failing Tests (by frequency in last 5 regressions):
  Rank | Test Name                | Fail% | Seeds | Classification
  ----------------------------------------------------------------------------------------------------------------------------------
  1    | axi_stress_test          | 45%   | vary  | FLAKY -seed-dependent
  2    | apb_error_inj_test       | 100%  | fixed | CONSISTENT -RTL bug suspected
  3    | dma_burst_max_test       | 20%   | vary  | FLAKY -timing-sensitive
  4    | irq_concurrent_test      | 8%    | vary  | LOW-FREQUENCY -investigate
  5    | reset_mid_burst_test     | 2%    | vary  | RARE -acceptable or infrastructure
```

#### 3.2 Flaky Test Detection

A test is flaky if it passes on some seeds and fails on others for the same configuration:

```
[FLAKY] axi_stress_test
  Runs:   50 total across last week
  PASS:   27 (54%)   FAIL: 23 (46%)
  Failing seeds:    0x3A2F, 0x819C, 0xA1B4 ... (23 seeds)
  Passing seeds:    0x0001, 0x0842 ... (27 seeds)
  Root cause hint:  Failure time varies -likely race condition or constraint sensitivity
  Action:           Debug with +UVM_TESTNAME=axi_stress_test +ntb_random_seed=0x3A2F
                    Enable waveform dump for first 3 failing seeds
```

---

### Step 4 -Coverage Trend Analysis

```
Coverage Trend (last 14 days):
  Date        Func%   Line%   Toggle%  New Tests Added
  ----------------------------------------------------------------------------------------------------------
  Mar 15      71.2    87.4    74.1     -  Mar 17      74.8    88.9    75.3     +axi_wrap_seq
  Mar 19      78.1    90.2    77.8     +error_inj_seq
  Mar 22      82.4    91.8    79.2     +concurrent_irq_seq
  Mar 25      85.6    92.5    80.8     +reset_mid_burst_seq
  Mar 29      87.3    93.1    81.6     (nightly random)

Coverage velocity: +2.3% functional/week
Projected sign-off date (100%): 6.2 weeks at current velocity
```

---

### Step 5 -Infrastructure vs. RTL Failure Separation

```
Failure Root Cause Breakdown:
  RTL bugs (confirmed):            34 failures  (29%)
  Testbench/sequence bugs:         28 failures  (24%)
  Infrastructure (LSF/memory):     12 failures  (10%)
  Flaky/race conditions:           38 failures  (33%)
  Unknown (needs debug):            4 failures   (3%)
```

---

### Step 6 -Regression Health Report

```
Regression Health Score: 73/100

Breakdown:
  Pass rate (target 95%):      78/100   [current: 95.2% --
  Flaky test rate (<5%):       55/100   [current: 11% -too many flaky]
  Coverage velocity:           80/100   [on track for milestone]
  Time to triage (< 24hr):     65/100   [avg: 31hr -needs improvement]
  Infrastructure reliability:  90/100   [4 infra failures -acceptable]

Recommendations:
  1. Prioritize fixing top 3 flaky tests -consuming 40% of debug bandwidth
  2. Add 5 targeted sequences for functional coverage holes at 0%
  3. Set up automatic seed bisection for race condition failures
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `regression_parser.py` | Parses regression result files (CSV/JSON/log) into unified result database |
| `flaky_detector.py` | Identifies tests with seed-dependent pass/fail behavior; computes flakiness score |
| `coverage_trend_tracker.py` | Tracks coverage metrics across regression runs; plots trend and projects closure date |
| `failure_classifier.py` | Classifies failures as RTL bug, TB bug, infrastructure, or unknown based on log patterns |
| `regression_health_scorer.py` | Computes weighted regression health score from pass rate, flakiness, coverage, and triage metrics |

---

## Validation Checklist

- [ ] All test results parsed and deduplicated
- [ ] Flaky tests identified and separated from consistent failures
- [ ] Infrastructure failures excluded from RTL bug count
- [ ] Coverage trend shows positive velocity toward sign-off target
- [ ] Top-N failing tests have assigned debug owners
- [ ] Regression health report shared with project lead
