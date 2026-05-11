---
name: formal-property-checker
description: Set up and debug formal property checks, assumptions, vacuity, and convergence.
---

# Formal Property Checker Skill

## Description

Set up, run, and debug formal property verification (FPV) sessions using assume/guarantee methodology. Covers environment setup, assume constraint writing, property classification, cone-of-influence analysis, vacuity detection, proof convergence strategies, and counterexample analysis.

- **Requires:** Formal verification tool (JasperGold, VC Formal, OneSpin, Yosys+sby)
- **Supported Property Types:** Safety, liveness, reachability, cover, assume-guarantee

> **Expertise:**
> You are an expert in formal property verification methodology. You understand how to set up sound assume environments, avoid over-constraining, classify properties by proof complexity, and interpret counterexamples to find real bugs. You know when to use bounded model checking vs. unbounded proof and how to handle proof convergence issues.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: Formal verification results depend critically on the correctness of assume constraints. Over-constraining (too many assumes) can make the proof unsound -bugs may be hidden. Under-constraining (too few assumes) produces spurious counterexamples. Always review assume constraints with the RTL owner before claiming a proof is sound.`

---

## When to Use This Skill

Trigger this skill when users:
- Ask to set up a formal verification session or FPV environment
- Need to write assume constraints for a formal tool
- Ask about proof convergence, bounded model checking, or k-induction
- Get spurious counterexamples they believe are impossible
- Ask about vacuity checking or proof debugging
- Mention terms like: "formal", "FPV", "JasperGold", "VC Formal", "assume", "guarantee", "counterexample", "proof", "BMC", "k-induction"

---

## Core Workflow

### Step 1 -Gather Context

- **Target Module:** What RTL block to formally verify?
- **Properties to Prove:** Which assertions or properties?
- **Interface Protocols:** What protocols constrain the inputs? (drives assume generation)
- **Known Unreachable States:** Any known impossible states to assume away?
- **Proof Strategy:** Full proof, bounded (how many cycles?), or cover reachability?
- **Tool:** JasperGold / VC Formal / OneSpin?

---

### Step 2 -Environment Setup

#### 2.1 Formal Environment File Structure

```
fpv/
----- tb/
-  ----- fpv_env.sv          # Assume + clock + reset environment
-  ----- fpv_props.sv        # Properties to prove (guarantees)
-  ----- fpv_covers.sv       # Cover properties for reachability
----- scripts/
-  ----- run.tcl             # Tool run script
-  ----- analyze.tcl         # Results analysis script
----- reports/
    ----- (generated)
```

---

#### 2.2 Clock and Reset Environment

```systemverilog
module fpv_env (
  input logic clk,
  input logic rstn,
  // DUT ports ...
);

  // Clock constraint
  assume property (@(posedge clk) 1'b1);   // Free-running clock

  // Reset: assert for first 3 cycles, then release
  // (Use tool-native reset handling in practice)
  initial begin
    assume(rstn == 1'b0);
    repeat(3) @(posedge clk);
    assume(rstn == 1'b1);
  end

endmodule
```

---

#### 2.3 Input Assume Constraints

**Critical rule:** Assumes must reflect real-world input behavior. Over-constraining hides bugs. Under-constraining generates false counterexamples.

```systemverilog
// Assume AXI master drives legal AWBURST values only
property assume_awburst_legal;
  @(posedge aclk) disable iff (!aresetn)
  awvalid |-> awburst inside {2'b00, 2'b01, 2'b10};
endproperty
assume property (assume_awburst_legal);

// Assume AWVALID is stable until AWREADY (protocol rule)
property assume_awvalid_stable;
  @(posedge aclk) disable iff (!aresetn)
  (awvalid && !awready) |=> awvalid;
endproperty
assume property (assume_awvalid_stable);

// Assume address stays within valid range
property assume_addr_legal;
  @(posedge aclk) disable iff (!aresetn)
  awvalid |-> awaddr inside {[40'h0:40'hFFFF_FFFF]};
endproperty
assume property (assume_addr_legal);

// Assume no simultaneous multiple channel handshakes (if single-beat)
// CAREFUL: only assume this if your DUT truly cannot receive them simultaneously
```

---

#### 2.4 Properties to Prove (Guarantees)

```systemverilog
// Safety: no response before request
property g_no_resp_without_req;
  @(posedge aclk) disable iff (!aresetn)
  bvalid |-> pending_write_count > 0;
endproperty
g_resp_ordering: assert property (g_no_resp_without_req);

// Safety: FIFO never overflows
property g_fifo_no_overflow;
  @(posedge aclk) disable iff (!aresetn)
  !(fifo_full && push && !pop);
endproperty
g_fifo_overflow: assert property (g_fifo_no_overflow);

// Liveness: every write gets a response
property g_write_gets_response;
  @(posedge aclk) disable iff (!aresetn)
  (awvalid && awready) |-> ##[1:MAX_LATENCY] (bvalid && bready);
endproperty
g_liveness: assert property (g_write_gets_response);
```

---

### Step 3 -Proof Strategies

#### 3.1 Strategy Selection

| Property Type | Recommended Strategy | When to Use |
|---------------|---------------------|-------------|
| Simple safety (combinational) | One-step proof | No state dependencies |
| Bounded safety | BMC (k=50-00) | Known maximum pipeline depth |
| Unbounded safety | K-induction or IC3/PDR | Critical safety properties |
| Liveness | K-induction with fairness | Must-eventually-happen |
| Reachability | Cover + BMC | Check if state is reachable |

#### 3.2 JasperGold TCL Script

```tcl
# analyze and elaborate
analyze -sv09 -f filelist.f
elaborate -top axi_slave

# Set up clock and reset
clock clk
reset -expression {!rstn}

# Run assumes first -check for over-constraint
check_assumptions -show_all

# Prove properties
prove -init {assume_*} -property {g_*} -engine_mode Hp

# Check vacuity
check_vacuity -property {g_*}

# Report
report -type summary -file reports/summary.rpt
report -type detail  -file reports/detail.rpt
```

---

#### 3.3 Handling Non-Convergent Proofs

When a proof does not converge (bounded engine hits depth limit):

```
Strategy 1: Increase bound
  prove -depth 200  (from default 50)

Strategy 2: Split into sub-properties
  Break complex property into simpler lemmas
  Prove lemmas first, then use them as assumes for top property

Strategy 3: Abstract helper logic
  Add auxiliary state variables to help the engine track invariants
  Example: Add a counter tracking outstanding transactions

Strategy 4: Switch engine
  JasperGold: try -engine_mode Hpr (IC3/PDR based)
  VC Formal:  try sharpsat or abc engines

Strategy 5: Constrain state space
  Add additional assumes to reduce reachable state space
  (Carefully -risk of over-constraining)
```

---

### Step 4 -Counterexample Analysis

When a property fails, the tool provides a counterexample (CEX) trace. Follow this analysis flow:

```
CEX Analysis Steps:
  1. Load CEX waveform in tool's waveform viewer
  2. Identify the cycle where the property violation occurs
  3. Trace backwards: what inputs led to this state?
  4. Check: is this a real bug or a false CEX from under-constraining?
     - If false CEX: add assumption to block this impossible input
     - If real bug:  file bug report, fix RTL, re-run proof
  5. Minimize CEX: use tool's CEX minimization to find shortest failing trace
```

---

### Step 5 -Vacuity Check

A vacuous proof means the antecedent was never reachable -the property trivially passes because the trigger condition never fires.

```tcl
# Check for vacuity in JasperGold
check_vacuity -property {g_write_gets_response}

# If vacuous: verify the trigger fires
cover -property {awvalid && awready}  # Should be reachable
```

If the trigger is unreachable: either the assume environment is over-constrained, or the design truly cannot reach that state (potential design bug).

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `fpv_env_generator.py` | Generates formal assume environment from interface protocol definition |
| `assume_strength_checker.py` | Analyzes assume set for over-constraint (blocks reachable states) and under-constraint (allows impossible states) |
| `cex_analyzer.py` | Parses counterexample trace and generates a human-readable causal chain analysis |
| `proof_coverage_reporter.py` | Maps proven properties to design requirements for coverage traceability |

---

## Validation Checklist

- [ ] Clock and reset environment correctly defined
- [ ] All input assumes reviewed with RTL owner for soundness
- [ ] Vacuity check passed for all proved properties
- [ ] All CEX analyzed -real bugs filed, false CEX documented with assume rationale
- [ ] Liveness properties have bounded response window
- [ ] Proof coverage maps all properties to design requirements
- [ ] Reports archived as part of formal sign-off package
