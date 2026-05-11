---
name: coverage-mapper
description: Map code coverage to functional coverage to identify redundant tests and missing goals.
---

# Code-to-Functional Coverage Mapper Skill

## Description

Correlate code coverage metrics (line, branch, toggle, FSM) with functional coverage results to identify redundant tests, code never exercised by the functional plan, and functional goals not backed by code activity. Provides a unified view of verification completeness.

- **Requires:** Coverage database with both code and functional coverage (UCDB/VCDDB), Python post-processing scripts
- **Supported Metrics:** Line coverage, branch coverage, toggle coverage, FSM state/arc coverage, expression coverage

> **Expertise:**
> You are an expert in verification completeness analysis. You understand the relationship between code coverage (what was executed) and functional coverage (what was intended), and you use the combination to identify gaps that neither metric alone would reveal.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: Coverage correlation is a heuristic guide -a line being executed does not prove it was exercised in all meaningful contexts. Low code coverage on a functionally-covered feature may indicate a coverage plan gap. High code coverage without functional coverage may indicate untargeted random exploration.`

---

## When to Use This Skill

Trigger this skill when users:
- Have high code coverage but low functional coverage (or vice versa)
- Ask whether code coverage alone is sufficient for sign-off
- Want to understand which RTL lines are never exercised
- Ask about toggle coverage, FSM arc coverage, or expression coverage
- Need to justify a coverage sign-off decision to management
- Mention terms like: "code coverage", "line coverage", "toggle", "FSM coverage", "branch coverage", "correlated coverage"

---

## Core Workflow

### Step 1 -Gather Context

- **Code Coverage Report:** Line, branch, toggle, FSM, expression metrics
- **Functional Coverage Report:** Covergroup hit rates
- **RTL Module of Interest:** Which module or block to correlate?
- **Threshold:** Minimum acceptable code coverage for sign-off (default: 90% line, 85% branch, 80% toggle)

---

### Step 2 -Correlation Analysis

#### 2.1 Code Coverage Baseline

```
Module: u_axi_slave
  Line coverage:    94.2%  (847 / 899 lines)
  Branch coverage:  88.7%  (214 / 241 branches)
  Toggle coverage:  82.1%  (532 / 648 signals toggled)
  FSM coverage:     75.0%  (9 / 12 arcs covered)
  Expression:       79.3%  (184 / 232 expressions)
```

#### 2.2 Uncovered Code Regions

```
Uncovered lines (52 lines):
  axi_slave.sv:142-148   Error recovery path -SLVERR response handler
  axi_slave.sv:201-207   WRAP burst address calculation -edge case
  axi_slave.sv:315       Timeout counter reset -rarely triggered

Uncovered branches (27 branches):
  axi_slave.sv:98        else branch: awburst == 2'b10 not taken
  axi_slave.sv:142       if (slverr_condition) -condition never true
  axi_slave.sv:315       if (timeout_cnt == MAX_TIMEOUT) -never reached
```

#### 2.3 Functional vs Code Gap Table

| Gap Type | Description | Action |
|----------|-------------|--------|
| Code covered, no functional hit | Code executed by random but no coverpoint defined | Add coverpoint or verify it's don't-care |
| Functional hit, code not covered | Coverpoint hit but RTL lines not exercised | Investigate -possible dead code or wrong sampling |
| Both uncovered | Neither code nor functional coverage | Missing test scenario -highest risk |
| Both covered | Fully verified | Sign-off candidate |

---

#### 2.4 FSM Arc Correlation

```
FSM: u_arb_fsm (current_state)
  Covered arcs:
    IDLE -ACTIVE       (functional: cp_transition::idle_to_active -
    ACTIVE -DONE       (functional: cp_transition::active_to_done -
    DONE -IDLE         (functional: cp_transition::done_to_idle -

  Uncovered arcs:
    ACTIVE -ERROR      (functional: cp_transition::active_to_error --0 hits)
    ERROR -IDLE        (functional: cp_transition::error_to_idle --0 hits)

  Verdict: Both code and functional coverage confirm error path untested.
           Action: Add error injection sequence (see Coverage Hole Analyzer skill)
```

---

#### 2.5 Toggle Coverage Deep Dive

Signals with 0% toggle (never toggled both 0- and 1-):

```
Never toggled signals (10 signals):
  u_axi_slave.error_state         -always 0 (error path never exercised)
  u_axi_slave.timeout_active      -always 0 (timeout never triggered)
  u_axi_slave.wrap_addr_boundary  -always 0 (WRAP boundary never hit)
  u_dma.priority_override         -always 0 (feature never enabled via register)
```

---

### Step 3 -Generate Unified Report

```
===================================================
  Unified Coverage Correlation Report
  Module:  u_axi_slave
  Date:    2025-03-29
===================================================

Code Coverage Summary:
  Line:    94.2%  Branch: 88.7%  Toggle: 82.1%  FSM: 75.0%

Functional Coverage Summary:
  Overall: 82.4%   Uncovered bins: 18

Correlation Findings:
  HIGH RISK (both code and functional uncovered):
    -Error recovery path (lines 142-148) + cp_bresp::decerr bin
    -FSM ERROR state arcs + cp_transition::active_to_error

  MEDIUM RISK (code uncovered, no functional coverpoint):
    -Timeout handler (line 315) -no timeout coverpoint defined
    -Action: Add cp_timeout coverpoint or waive as don't-care

  LOW RISK (functional covered, code covered):
    -91 bins hit with corresponding code activity -sign-off ready

Sign-off Readiness: NOT READY -2 HIGH RISK items unresolved
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `coverage_correlator.py` | Merges code coverage and functional coverage databases; produces per-signal and per-line correlation table |
| `dead_code_detector.py` | Identifies RTL lines covered by neither code nor functional metrics -flags for RTL owner review |
| `fsm_arc_correlator.py` | Maps FSM arc coverage to functional coverpoint transitions; highlights unmatched arcs |
| `toggle_gap_reporter.py` | Lists signals with incomplete toggle coverage and suggests the stimulus needed to exercise them |

---

## Validation Checklist

- [ ] Code and functional coverage databases from same regression run
- [ ] All HIGH RISK items (both metrics uncovered) addressed before sign-off
- [ ] Uncovered code with no functional goal classified (dead code vs. missing test)
- [ ] FSM arc coverage correlated with FSM transition coverpoints
- [ ] Toggle coverage reviewed -always-0 signals explained and waived or tested
- [ ] Unified report archived as part of sign-off package
