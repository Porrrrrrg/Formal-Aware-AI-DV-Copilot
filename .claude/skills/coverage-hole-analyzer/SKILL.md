---
name: coverage-hole-analyzer
description: Analyze coverage gaps and recommend targeted tests, constraints, and sequence changes.
---

# Coverage Hole Analyzer Skill

## Description

Analyze functional coverage databases to identify uncovered bins, hard-to-hit scenarios, and coverage holes. Generate targeted test recommendations, constraint modifications, and sequence additions to efficiently close remaining coverage gaps before sign-off.

- **Requires:** Coverage database in UCDB (Questa), VCDDB (VCS), or RCDB (Xcelium) format; Python coverage export scripts
- **Supported Inputs:** Coverage reports (HTML/text), UCDB/VCDDB exports, per-test coverage CSV

> **Expertise:**
> You are an expert in coverage closure methodology. You analyze coverage gaps systematically, distinguish between reachable and unreachable bins, prioritize gaps by functional risk, and prescribe the minimum set of additional tests needed to reach sign-off targets efficiently.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: Coverage hole analysis depends on the accuracy of the coverage plan. Bins that are 0% hit may be unreachable by design -always verify with the RTL owner before escalating. Coverage closure does not guarantee absence of bugs not modeled by the coverage plan.`

---

## When to Use This Skill

Trigger this skill when users:
- Ask why a coverpoint or cross bin is never hit
- Need to close coverage before tapeout or milestone
- Want to know which tests to add for maximum coverage gain
- Ask about hard-to-hit bins or unreachable coverage
- Mention terms like: "coverage hole", "unhit bin", "0% coverage", "coverage closure", "coverage gap", "missing coverage"

---

## Core Workflow

### Step 1 -Gather Context

- **Coverage Database / Report:** Path to coverage export or HTML report
- **Current Coverage Level:** Overall and per-group percentages
- **Sign-off Target:** Required coverage threshold (e.g., 100% with documented waivers)
- **Existing Test Count:** How many tests in the regression?
- **Priority Groups:** Which covergroups are highest priority for closure?

---

### Step 2 -Identify and Classify Holes

#### 2.1 Parse Coverage Report

Extract all unhit bins (0% hit count) and partially hit bins:

```
Coverage Gap Analysis:
  Total coverpoints:   148
  Fully covered:       112  (75.7%)
  Partially covered:    24  (16.2%)
  Not hit at all:       12  (8.1%)

Top uncovered bins:
  axi4_write_cg::cx_burst_x_size[wrap - b64]   0 / 1 hits
  axi4_write_cg::cp_bresp[decerr]               0 / 1 hits
  irq_cg::cx_src_x_priority[error - high]       0 / 1 hits
  fsm_cg::cp_transition[active_to_error]        0 / 1 hits
```

---

#### 2.2 Classify Each Hole

| Classification | Definition | Action |
|----------------|-----------|--------|
| **Reachable** | Design can reach this state; test hasn't triggered it | Add targeted test or constraint |
| **Hard-to-hit** | Reachable but requires specific multi-field combination | Add directed sequence |
| **Unreachable by design** | RTL cannot reach this state by architectural definition | Add `ignore_bins` + waiver |
| **Unreachable by constraint** | Legal in protocol but excluded by current constraints | Relax constraint or add error class |
| **Needs RTL force** | Only reachable by forcing internal signal | Use `$deposit` or add DFT hook |

---

#### 2.3 Root Cause Analysis Per Hole

For each unhit bin:

```
[HOLE] axi4_write_cg::cp_bresp[decerr]
  Root cause:    DECERR response requires accessing an unmapped address region.
                 Current address constraints restrict to valid memory map only.
  Classification: Unreachable by constraint -valid test scenario not exercised
  Recommended fix: Add error injection sequence with out-of-range address
  Estimated tests to close: 1 directed test
  Risk if not covered: Address decode error path untested -potential silicon escape
```

```
[HOLE] fsm_cg::cp_transition[active_to_error]
  Root cause:    Error transition requires a protocol violation during active state.
                 No error injection sequences exist in current regression.
  Classification: Reachable -missing test scenario
  Recommended fix: Add axi_error_seq with illegal burst type during active transfer
  Estimated tests to close: 1 sequence addition
```

```
[HOLE] axi4_write_cg::cx_burst_x_size[wrap - b64]
  Root cause:    WRAP burst with 64-byte size is a legal but rare combination.
                 Current weight distribution rarely generates this.
  Classification: Hard-to-hit -low probability in random
  Recommended fix: Add directed constraint targeting burst=WRAP && size=3'b110
  Estimated tests to close: 1 directed constraint + 10 runs
```

---

### Step 3 -Generate Targeted Tests

For each identified hole, generate the targeted fix:

#### Targeted constraint for hard-to-hit bin:

```systemverilog
class axi_wrap_64b_seq extends uvm_sequence #(axi_seq_item);
  `uvm_object_utils(axi_wrap_64b_seq)
  task body();
    `uvm_do_with(req, {
      burst == 2'b10;    // WRAP
      size  == 3'b110;   // 64 bytes
      len   inside {8'd1, 8'd3, 8'd7, 8'd15};  // WRAP legal lengths
      addr[5:0] == 6'b0; // 64B aligned
    })
  endtask
endclass
```

#### Adjusted distribution weight to boost rare bin:

```systemverilog
// Before: wrap probability too low
constraint c_burst_dist {
  burst dist { 2'b00 := 10, 2'b01 := 80, 2'b10 := 10 };
}

// After: increase WRAP weight until bin is hit
constraint c_burst_dist {
  burst dist { 2'b00 := 10, 2'b01 := 60, 2'b10 := 30 };
}
```

---

### Step 4 -Coverage Closure Priority Matrix

```
Priority | Covergroup              | Gap %  | Risk  | Action
----------------------------------------------------------------------------------------------------------------------------------
HIGH     | fsm_cg::transition      | 30%    | HIGH  | Add error injection sequence
HIGH     | cp_bresp::decerr        | 0%     | HIGH  | Add address decode error test
MEDIUM   | cx_burst_x_size wrap-*  | 45%    | MED   | Boost WRAP constraint weight
MEDIUM   | irq_cg::concurrent      | 60%    | MED   | Add multi-IRQ stress sequence
LOW      | cp_len::max             | 0%     | LOW   | Add max burst directed test
WAIVER   | illegal_bins            | 0%     | N/A   | By definition -waive
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `coverage_db_parser.py` | Parses UCDB/VCDDB/HTML coverage reports and extracts unhit and partially-hit bins |
| `hole_classifier.py` | Classifies each coverage hole as reachable, hard-to-hit, unreachable-by-design, or constraint-blocked |
| `targeted_test_recommender.py` | For each hole, suggests a specific constraint change, sequence, or waiver |
| `closure_priority_ranker.py` | Ranks coverage gaps by functional risk and estimated closure effort |

---

## Validation Checklist

- [ ] All 0%-hit bins classified (reachable / unreachable / constraint-blocked)
- [ ] Unreachable bins have `ignore_bins` and waiver with RTL owner sign-off
- [ ] Targeted tests generated for all reachable holes
- [ ] Priority matrix reviewed with DV lead and RTL owner
- [ ] After adding targeted tests, re-run regression to confirm closure
- [ ] Final coverage report archived for sign-off record
