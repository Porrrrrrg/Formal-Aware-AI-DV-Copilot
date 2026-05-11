---
name: coverage-plan-writer
description: Draft functional coverage plans, covergroups, coverpoints, crosses, and traceability.
---

# Coverage Plan Writer Skill

## Description

Generate comprehensive functional coverage plans from design specifications, including covergroups, coverpoints, cross coverage, bins definitions, and coverage-to-requirement traceability. Covers all major coverage dimensions: functional, protocol, configuration, error, and cross-feature interactions.

- **Requires:** SystemVerilog simulator with functional coverage (VCS, Xcelium, Questa)
- **Supported Inputs:** Natural language spec, RTL, UVM testplan, Excel/CSV feature lists

> **Expertise:**
> You are an expert in functional verification coverage methodology. You translate design specifications into measurable coverage metrics, ensure every requirement maps to at least one coverpoint, and design cross-coverage to catch interaction bugs that individual coverpoints miss.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: Coverage plans are derived from provided specifications. Coverage holes may exist for behaviors not described in the spec. Review the plan with the RTL owner and DV lead before integration. Coverage closure does not guarantee bug-free design -use in combination with assertion-based verification.`

---

## When to Use This Skill

Trigger this skill when users:
- Ask to write covergroups, coverpoints, or cross coverage
- Need to translate a spec feature into measurable coverage
- Ask about coverage plan, coverage model, or coverage closure strategy
- Want to add coverage to an existing UVM monitor or scoreboard
- Mention terms like: "coverage plan", "covergroup", "coverpoint", "cross coverage", "bins", "coverage closure", "hit count", "coverage hole"

---

## Core Workflow

### Step 1 -Gather Context

- **Design Feature / Spec Section:** What is being verified?
- **Key Fields and Enumerations:** What signals/variables have meaningful value ranges?
- **Required Interactions:** Which field combinations matter?
- **Error Scenarios:** What illegal or boundary conditions must be covered?
- **Target Coverage:** Minimum coverage percentage for sign-off (default: 100% with waivers)
- **Sampling Event:** When should coverage be sampled (posedge clk, transaction complete, etc.)?

---

### Step 2 -Coverage Dimensions

For each feature, cover all relevant dimensions:

| Dimension | Coverage Type | Example |
|-----------|--------------|---------|
| Value range | Bins covering all legal values | All burst types: FIXED, INCR, WRAP |
| Boundary conditions | Min, max, near-boundary bins | len=0, len=255, addr at 4KB boundary |
| Error conditions | Illegal values and error responses | SLVERR response, unaligned address |
| Transitions | State transitions, value sequences | Idle--ctive, Read--rite back-to-back |
| Interactions | Cross coverage between fields | burst_type - transfer_size |
| Configuration | Register settings affecting behavior | Cache policy - burst type |
| Timing | Back-pressure, pipeline fill, drain | All channels active simultaneously |

---

### Step 3 -Generate Covergroups

#### 3.1 AXI4 Write Channel Coverage

```systemverilog
covergroup axi4_write_cg (string name) with function sample(
  logic [1:0]  burst, logic [2:0] size, logic [7:0] len,
  logic [39:0] addr,  logic [1:0] bresp);

  option.name        = name;
  option.per_instance= 1;
  option.goal        = 100;
  option.comment     = "AXI4 Write channel functional coverage";

  // Burst type coverage -all three legal types
  cp_burst: coverpoint burst {
    bins fixed = {2'b00};
    bins incr  = {2'b01};
    bins wrap  = {2'b10};
    illegal_bins reserved = {2'b11};
  }

  // Transfer size -1B to 128B
  cp_size: coverpoint size {
    bins b1   = {3'b000};
    bins b2   = {3'b001};
    bins b4   = {3'b010};
    bins b8   = {3'b011};
    bins b16  = {3'b100};
    bins b32  = {3'b101};
    bins b64  = {3'b110};
    illegal_bins b128_reserved = {3'b111};
  }

  // Burst length -cover single, short, medium, long
  cp_len: coverpoint len {
    bins single  = {8'd0};
    bins short   = {[8'd1:8'd15]};
    bins medium  = {[8'd16:8'd63]};
    bins long    = {[8'd64:8'd254]};
    bins max     = {8'd255};
  }

  // Write response
  cp_bresp: coverpoint bresp {
    bins okay   = {2'b00};
    bins slverr = {2'b10};
    bins decerr = {2'b11};
  }

  // Address alignment relative to size
  cp_addr_align: coverpoint addr[5:0] {
    bins aligned_1b  = {[6'b000000:6'b111111]};  // Always aligned for 1B
    bins aligned_4b  = {6'b000000, 6'b000100, 6'b001000};  // 4B aligned
    bins unaligned   = {6'b000001, 6'b000010, 6'b000011};  // Unaligned
  }

  // 4KB boundary proximity
  cp_4k_boundary: coverpoint addr[11:0] {
    bins far_from_boundary  = {[12'h000:12'hEFF]};
    bins near_boundary      = {[12'hF00:12'hFF0]};
    bins at_boundary        = {12'hFF0, 12'hFF4, 12'hFF8, 12'hFFC};
  }

  // Key cross: burst type - transfer size
  cx_burst_x_size: cross cp_burst, cp_size {
    // WRAP only legal with specific sizes
    ignore_bins wrap_b1  = binsof(cp_burst.wrap) && binsof(cp_size.b1);
  }

  // Key cross: burst type - response
  cx_burst_x_resp: cross cp_burst, cp_bresp;

  // Key cross: length - size (bandwidth)
  cx_len_x_size: cross cp_len, cp_size;

endgroup
```

---

#### 3.2 FSM State Coverage

```systemverilog
covergroup fsm_cg @(posedge clk);
  option.per_instance = 1;

  // All states visited
  cp_state: coverpoint dut.current_state {
    bins idle    = {IDLE};
    bins active  = {ACTIVE};
    bins wait_st = {WAIT};
    bins error   = {ERROR};
    bins done    = {DONE};
  }

  // All state transitions
  cp_transition: coverpoint dut.current_state {
    bins idle_to_active  = (IDLE    => ACTIVE);
    bins active_to_wait  = (ACTIVE  => WAIT);
    bins wait_to_done    = (WAIT    => DONE);
    bins done_to_idle    = (DONE    => IDLE);
    bins active_to_error = (ACTIVE  => ERROR);
    bins error_to_idle   = (ERROR   => IDLE);
    bins any_to_idle     = (ACTIVE, WAIT, ERROR, DONE => IDLE);
  }

endgroup
```

---

#### 3.3 Interrupt Coverage

```systemverilog
covergroup irq_cg @(posedge clk);
  // All interrupt sources
  cp_irq_src: coverpoint irq_source {
    bins timer   = {IRQ_TIMER};
    bins dma     = {IRQ_DMA};
    bins uart    = {IRQ_UART};
    bins gpio    = {IRQ_GPIO};
    bins error   = {IRQ_ERROR};
  }

  // Priority levels
  cp_priority: coverpoint irq_priority;

  // Single vs. simultaneous interrupts
  cp_concurrent: coverpoint $countones(irq_vec) {
    bins single      = {1};
    bins two         = {2};
    bins three_plus  = {[3:16]};
  }

  // Interrupt acknowledged within deadline
  cp_latency: coverpoint irq_latency_cycles {
    bins fast    = {[0:4]};
    bins nominal = {[5:20]};
    bins slow    = {[21:100]};
    bins timeout = {[101:$]};
  }

  cx_src_x_priority: cross cp_irq_src, cp_priority;
endgroup
```

---

### Step 4 -Coverage Waiver Format

```systemverilog
// Unreachable bin -document reason
// WAIVER: cp_burst.fixed - cp_size.b128_reserved -b128 is illegal_bins, never hit by definition
// WAIVER: cx_burst_x_size.wrap_b1 -WRAP with 1B size is a protocol violation, excluded by constraint
```

---

### Step 5 -Coverage Plan Document

Generate a structured coverage plan table:

```
Coverage Plan: AXI4 Write Channel
Spec Section: AXI4 Spec -A3.4
Sign-off Target: 100% (with documented waivers)

----------------------------------------------------------------------------------------------------------------------------------------------------------------Coverpoint          -Bins              -Req. Traces  -Notes                 -----------------------------------------------------------------------------------------------------------------------------------------------------------------cp_burst            -FIXED,INCR,WRAP   -REQ-AXI-001  -All burst types       --cp_size             -1B through 64B    -REQ-AXI-002  -7 transfer sizes      --cp_len              -0,1-15,16-63,max  -REQ-AXI-003  -Burst lengths         --cp_bresp            -OKAY,SLVERR,DECERR-REQ-AXI-010  -All legal responses   --cx_burst_x_size     -3-7 = 21 bins     -REQ-AXI-001  -Burst/size matrix     --cx_len_x_size       -5-7 = 35 bins     -REQ-AXI-004  -Bandwidth scenarios   ----------------------------------------------------------------------------------------------------------------------------------------------------------------```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `coverplan_gen.py` | Generates SystemVerilog covergroup skeletons from a feature description or signal list |
| `bin_range_optimizer.py` | Suggests bin boundaries based on value distribution observed in previous regressions |
| `coverage_traceability_mapper.py` | Maps each coverpoint to one or more spec requirements |
| `waiver_generator.py` | Generates coverage exclusion waivers for unreachable bins with reason documentation |

---

## Validation Checklist

- [ ] Every spec requirement maps to at least one coverpoint
- [ ] All legal enum values have explicit bins
- [ ] Key field interactions covered by cross coverage
- [ ] Error and boundary conditions have dedicated bins
- [ ] Unreachable bins documented with `ignore_bins` and waiver reason
- [ ] Coverage groups instantiated in UVM monitor or subscriber
- [ ] Sign-off target percentage agreed with project lead
