---
name: sva-assertion-writer
description: Write and review SystemVerilog Assertions for requirements, protocols, and coverage.
---

# SVA Assertion Writer Skill

## Description

Generate, review, and debug SystemVerilog Assertions (SVA) for design verification. Covers immediate assertions, concurrent assertions, sequence operators, property definitions, clocking blocks, disable conditions, liveness vs. safety properties, and assertion coverage. Maps assertions to design requirements and protocol rules.

- **Requires:** SystemVerilog simulator with SVA support (VCS, Xcelium, Questa) or formal tool (JasperGold, VC Formal)
- **Supported Contexts:** RTL bind files, inline module assertions, SVA packages, UVM scoreboard checkers

> **Expertise:**
> You are an expert in SystemVerilog Assertion writing for both simulation-based and formal verification. You understand temporal sequence operators, clocking semantics, disable conditions, liveness vs. safety property classification, and how to write assertions that catch real bugs without excessive false positives.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: Generated assertions are starting points based on provided specifications. Verify that each assertion fires correctly on a known-bad stimulus before regression integration. Assertions that never fire in simulation may be vacuous -check assertion coverage to confirm they are being exercised.`

---

## When to Use This Skill

Trigger this skill when users:
- Ask to write SVA assertions, properties, or sequences
- Need to formalize a protocol rule or design requirement as an assertion
- Ask about `|->`, `|=>`, sequence operators, `throughout`, `within`
- Need to debug a failing or vacuous assertion
- Ask about assertion coverage, `$rose`, `$fell`, `$stable`, `$past`
- Mention terms like: "SVA", "assertion", "property", "sequence", "checker", "|->", "|=>"

---

## Core Workflow

### Step 1 -Gather Context

- **Design Rule to Assert:** What property must always hold?
- **Signal Names:** Clock, reset, and relevant design signals
- **Assertion Type:** Safety (bad thing never happens) or liveness (good thing eventually happens)
- **Disable Condition:** When should the assertion be inactive? (reset, test mode, power-down)
- **Timing:** How many cycles between cause and effect?
- **Integration:** Inline, bind file, or formal environment?

---

### Step 2 -SVA Building Blocks

#### 2.1 Basic Concurrent Assertion Structure

```systemverilog
// Template: basic property + assertion
property p_name;
  @(posedge clk) disable iff (!rstn || test_mode)
  antecedent |-> consequent;
endproperty

a_name: assert property (p_name)
  else `uvm_error("ASSERT", "Property p_name failed")

// Also add cover to confirm it fires
c_name: cover property (p_name);
```

---

#### 2.2 Safety Properties (bad thing never happens)

```systemverilog
// Rule: VALID must not deassert before READY (AXI handshake stability)
property p_valid_stable;
  @(posedge aclk) disable iff (!aresetn)
  (awvalid && !awready) |=> awvalid;
endproperty
a_valid_stable: assert property (p_valid_stable)
  else `uvm_error("AXI_SVA", "AWVALID dropped before AWREADY")

// Rule: FIFO must never overflow
property p_fifo_no_overflow;
  @(posedge clk) disable iff (!rstn)
  !(fifo_full && push && !pop);
endproperty
a_fifo_overflow: assert property (p_fifo_no_overflow)
  else `uvm_error("FIFO_SVA", "FIFO overflow detected")

// Rule: Write strobe must be zero during read operations
property p_strb_zero_on_read;
  @(posedge clk) disable iff (!rstn)
  (psel && !pwrite) |-> (pstrb == '0);
endproperty
```

---

#### 2.3 Liveness Properties (good thing eventually happens)

```systemverilog
// Rule: Every request must eventually receive a response (within N cycles)
property p_req_gets_resp;
  @(posedge clk) disable iff (!rstn)
  $rose(req_valid) |-> ##[1:MAX_LATENCY] resp_valid;
endproperty
a_req_gets_resp: assert property (p_req_gets_resp)
  else `uvm_error("LIVE_SVA", "Request did not receive response within timeout")

// Rule: FIFO must eventually drain after write enable deasserts
property p_fifo_drains;
  @(posedge clk) disable iff (!rstn)
  $fell(push_en) |-> ##[1:MAX_DRAIN] fifo_empty;
endproperty
```

---

#### 2.4 Sequence Operators

```systemverilog
// ##N: exactly N cycles later
property p_ack_after_req;
  @(posedge clk) disable iff (!rstn)
  req |-> ##2 ack;   // ack must appear exactly 2 cycles after req
endproperty

// ##[m:n]: between m and n cycles
property p_ack_within_window;
  @(posedge clk) disable iff (!rstn)
  req |-> ##[1:8] ack;
endproperty

// `throughout`: condition must hold throughout a sequence
property p_cs_stable_during_transfer;
  @(posedge clk) disable iff (!rstn)
  $rose(cs_n == 0) |-> (cs_n == 0) throughout (##[1:$] $rose(done));
endproperty

// `within`: sequence A must complete within sequence B
sequence s_burst_complete;
  @(posedge aclk) wvalid && wready && wlast;
endsequence

sequence s_write_channel_open;
  @(posedge aclk) awvalid && awready ##[1:$] s_burst_complete;
endsequence
```

---

#### 2.5 Multi-Cycle and Pipeline Assertions

```systemverilog
// Check that pipeline output matches input after fixed latency
property p_pipeline_correct;
  logic [31:0] captured_data;
  @(posedge clk) disable iff (!rstn)
  (valid_in, captured_data = data_in) |-> ##PIPE_LATENCY
    (valid_out && (data_out == captured_data));
endproperty

// Check back-pressure propagates correctly through pipeline
property p_backpressure_stalls_pipeline;
  @(posedge clk) disable iff (!rstn)
  (!ready_out && valid_in) |=> $stable(data_in);
endproperty
```

---

#### 2.6 FSM Assertion Pack

```systemverilog
// All valid state transitions only
property p_fsm_legal_transitions;
  @(posedge clk) disable iff (!rstn)
  (state == ACTIVE) |=>
    (state inside {ACTIVE, WAIT, ERROR, DONE});
endproperty

// No state skipping
property p_no_idle_skip;
  @(posedge clk) disable iff (!rstn)
  (state == ERROR) |=> ##[1:$] (state == IDLE);
endproperty

// State mutex -only one hot bit active
property p_state_onehot;
  @(posedge clk) disable iff (!rstn)
  $onehot(state);
endproperty
```

---

#### 2.7 Assertion Coverage

Always pair assertions with cover properties to verify they fire:

```systemverilog
// Cover: VALID goes high (antecedent fires)
c_valid_seen: cover property (@(posedge aclk) awvalid);

// Cover: full property executes (antecedent + consequent path)
c_valid_stable_fires: cover property (p_valid_stable);

// Cover: error path exercised
c_error_transition: cover property (
  @(posedge clk) (state == ACTIVE) ##1 (state == ERROR));
```

---

### Step 3 -Bind File Integration

```systemverilog
// Separate assertion module -non-intrusive binding
module axi_slave_sva #(
  parameter int TIMEOUT = 1000
)(
  input logic        aclk, aresetn,
  input logic        awvalid, awready,
  input logic [7:0]  awlen,
  input logic [1:0]  awburst,
  input logic [1:0]  bresp,
  input logic        bvalid, bready
);

  // Assertion properties
  property p_valid_stable;
    @(posedge aclk) disable iff (!aresetn)
    (awvalid && !awready) |=> awvalid;
  endproperty

  property p_aw_timeout;
    @(posedge aclk) disable iff (!aresetn)
    awvalid |-> ##[1:TIMEOUT] awready;
  endproperty

  a_valid_stable : assert property (p_valid_stable);
  a_aw_timeout   : assert property (p_aw_timeout);

endmodule

// Bind to DUT -zero RTL modification
bind u_axi_slave axi_slave_sva #(.TIMEOUT(500)) i_sva (.*);
```

---

### Step 4 -Assertion Debug

When an assertion fires unexpectedly:

```
Debug checklist:
  [ ] Check disable condition -is reset or test_mode causing false disable?
  [ ] Verify clocking event -is posedge vs negedge correct?
  [ ] Check $past() usage -off-by-one cycle errors are common
  [ ] Confirm signal naming -bound module may have different signal hierarchy
  [ ] Narrow the window -reduce ##[m:n] range to isolate timing
  [ ] Add $display in else clause to print signal values at failure point
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `sva_generator.py` | Generates SVA property and assertion pairs from a natural language rule description |
| `assertion_coverage_reporter.py` | Extracts assertion pass/fail/vacuous counts from simulation log |
| `bind_file_generator.py` | Generates bind file wrapper for a given DUT module and assertion module |
| `vacuity_checker.py` | Identifies assertions that never fire their antecedent (potentially vacuous) |

---

## Validation Checklist

- [ ] Every assertion has a matching `cover` property to verify it fires
- [ ] All assertions have correct `disable iff` for reset and test modes
- [ ] Assertions verified to fire on deliberate known-bad stimulus
- [ ] No vacuous assertions -all antecedents confirmed to trigger
- [ ] Bind files tested without DUT RTL modification
- [ ] Liveness assertions have bounded `##[1:N]` windows with N justified
