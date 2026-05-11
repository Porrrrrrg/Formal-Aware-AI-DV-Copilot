---
name: assertion-coverage-reviewer
description: Review assertion sets for completeness, redundancy, vacuity, and requirement coverage.
---

# Assertion Coverage Reviewer Skill

## Description

Review an RTL design's assertion set for completeness, redundancy, vacuity, and quality. Identifies missing assertions for uncovered design rules, detects duplicate or conflicting assertions, flags vacuous assertions that never fire, and ensures assertion coverage maps to verification requirements.

- **Requires:** SVA-capable simulator, assertion coverage database
- **Supported Inputs:** RTL files with inline assertions, bind files, assertion module list, simulation log with assertion statistics

> **Expertise:**
> You are an expert in assertion-based verification methodology and assertion quality assessment. You understand the difference between safety and liveness properties, how to detect vacuous assertions, and how to build a complete assertion set that guards all critical design rules without redundancy.

---

## When to Use This Skill

Trigger this skill when users:
- Ask whether their assertion set is complete or sufficient
- Suspect assertions are vacuous or never firing
- Need to audit assertions before formal verification or sign-off
- Ask about assertion redundancy or conflicting assertions
- Mention terms like: "assertion audit", "vacuous assertion", "assertion coverage", "missing assertion", "redundant assertion"

---

## Core Workflow

### Step 1 -Gather Context

- **Assertion Source Files:** RTL or bind files containing assertions
- **Simulation Log:** Assertion pass/fail/vacuous statistics from regression
- **Design Spec or Requirements:** What rules must be asserted?
- **Assertion Coverage DB:** Tool-generated assertion coverage report

---

### Step 2 -Assertion Inventory and Classification

Build a complete inventory of all assertions:

```
Assertion Inventory: u_axi_slave
  Total assertions:    24
  Safety properties:   18
  Liveness properties:  4
  Cover properties:     2

Simulation Statistics (1000-test regression):
  Assertions that fired at least once (antecedent triggered): 19
  Assertions that NEVER fired (potentially vacuous):           5
  Assertions that failed at least once:                        2
  Assertions with 0 antecedent hits (vacuous):                 3
```

---

### Step 3 -Vacuity Analysis

For each assertion that never fires its antecedent:

```
[VACUOUS] a_wrap_burst_addr_calc
  Property:     (awburst == 2'b10) |-> ##1 wrap_addr_correct
  Antecedent hits: 0 in 1000-test regression
  Root cause:   WRAP burst never generated -constraint too strict
  Action:       Add WRAP-targeted sequence OR add ignore_bins waiver if not required

[VACUOUS] a_error_recovery
  Property:     (state == ERROR) |-> ##[1:10] (state == IDLE)
  Antecedent hits: 0
  Root cause:   ERROR state never reached -no error injection in regression
  Action:       Add error injection sequence; this is a critical uncovered path
```

---

### Step 4 -Missing Assertion Detection

Compare assertion set against design spec requirements:

```
Requirements with no assertion coverage:
  REQ-004: FIFO must signal almost-full when depth > 75%
    -No assertion on almost_full signal behavior
    -Action: Add: (fifo_depth > DEPTH*3/4) |-> ##1 almost_full

  REQ-012: DMA transfer count must decrement monotonically
    -No assertion on xfer_count behavior
    -Action: Add: $stable(dma_en) && dma_en |-> (xfer_count <= $past(xfer_count))

  REQ-019: Bus grant must be mutually exclusive
    -No mutex assertion on grant signals
    -Action: Add: $onehot0({grant_a, grant_b, grant_c})
```

---

### Step 5 -Redundancy Detection

Identify assertions that check the same condition:

```
[REDUNDANT] a_valid_stable_aw and a_aw_valid_hold
  Both assert: awvalid stable until awready
  Action: Remove one; keep the more descriptive name
```

---

### Step 6 -Quality Scoring

Score each assertion on quality criteria:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Fires antecedent | 30% | Assertion actually triggers in regression |
| Catches a real bug | 25% | Proven to detect a DV or RTL bug |
| Maps to requirement | 20% | Traceable to spec requirement |
| Has cover companion | 15% | Paired with cover property |
| Disable condition correct | 10% | Reset/test_mode disable is accurate |

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `assertion_inventory.py` | Parses RTL/bind files and builds complete assertion inventory with type and location |
| `vacuity_detector.py` | Parses simulation log for assertions with zero antecedent hits |
| `assertion_gap_finder.py` | Compares assertion set against requirements list; flags uncovered requirements |
| `redundancy_checker.py` | Detects structurally similar assertion pairs that check the same condition |

---

## Validation Checklist

- [ ] All assertions fire their antecedent at least once in regression
- [ ] Zero vacuous assertions (or documented with justification)
- [ ] All design requirements have at least one covering assertion
- [ ] No structurally redundant assertions
- [ ] All assertions have correct disable conditions
- [ ] Every safety assertion has a companion cover property
