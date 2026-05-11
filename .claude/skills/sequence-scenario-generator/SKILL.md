---
name: sequence-scenario-generator
description: Create directed and constrained-random UVM sequences for coverage-driven scenarios.
---

# Sequence and Scenario Generator Skill

## Description

Generate directed and constrained-random UVM sequences and test scenarios targeting specific design behaviors, corner cases, stress conditions, and error recovery paths. Covers sequence libraries, virtual sequences, scenario composition, back-pressure injection, and reset-in-the-middle scenarios.

- **Requires:** UVM 1.2 / IEEE 1800.2, SystemVerilog simulator
- **Supported Contexts:** UVM sequence items, sequences, virtual sequences, test classes

> **Expertise:**
> You are an expert in coverage-driven verification scenario planning. You design layered sequence libraries that systematically exercise functional requirements, corner cases, error paths, and stress conditions, mapping each scenario to coverage goals.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: Generated sequences are starting points. Verify each sequence hits its intended coverage targets before regression integration. Sequence behavior may need adjustment based on DUT timing and protocol-specific requirements.`

---

## When to Use This Skill

Trigger this skill when users:
- Ask to write UVM sequences, virtual sequences, or directed tests
- Need corner-case scenarios for specific protocol features
- Want to target uncovered bins or coverage holes with new sequences
- Ask about back-pressure, reset injection, or interleaved transaction scenarios
- Mention terms like: "sequence", "scenario", "directed test", "corner case", "stress", "back pressure", "virtual sequence"

---

## Core Workflow

### Step 1 -Gather Context

- **Target Feature:** What design feature or requirement does this scenario verify?
- **Coverage Target:** Which coverpoints/bins should this sequence hit?
- **Protocol:** What bus interface does the sequence drive?
- **Scenario Type:** Functional, corner case, error injection, stress, or reset-in-middle
- **Sequence Depth:** Single sequence item, multi-step sequence, or virtual sequence across multiple agents

---

### Step 2 -Scenario Classification

| Type | Description | Example |
|------|-------------|---------|
| Directed functional | Specific legal transaction targeting one requirement | Write then read to same address |
| Corner case | Boundary conditions and limit values | Max burst length, min address, zero-length transfer |
| Error injection | Protocol violations, illegal transactions | Invalid burst type, unaligned address |
| Stress | High-throughput, back-to-back, no idle | 1000 back-to-back max-length bursts |
| Concurrent | Multiple agents active simultaneously | Read and write channels active in parallel |
| Reset-in-middle | Reset asserted mid-transaction | Assert reset during active AXI burst |
| Power state | Transitions during active traffic | Enter/exit power-gated state under load |

---

### Step 3 -Generate Sequences

#### 3.1 Basic Directed Sequence

```systemverilog
// Directed write-then-read sequence for data integrity check
class apb_write_read_seq extends uvm_sequence #(apb_seq_item);
  `uvm_object_utils(apb_write_read_seq)

  rand logic [31:0] target_addr;
  rand logic [31:0] write_data;

  constraint c_addr { target_addr[1:0] == 2'b00; }

  task body();
    apb_seq_item wr_txn, rd_txn;
    // Write phase
    `uvm_do_with(wr_txn, {
      addr   == target_addr;
      pwrite == 1'b1;
      data   == write_data;
      pstrb  == 4'hF;
    })
    // Read back and verify via scoreboard
    `uvm_do_with(rd_txn, {
      addr   == target_addr;
      pwrite == 1'b0;
    })
    `uvm_info("SEQ", $sformatf("Write 0x%0h -Read back at 0x%0h", write_data, target_addr), UVM_MEDIUM)
  endtask
endclass
```

---

#### 3.2 Corner Case Sequence Library

```systemverilog
// Max burst length corner case
class axi_max_burst_seq extends uvm_sequence #(axi_seq_item);
  `uvm_object_utils(axi_max_burst_seq)
  task body();
    `uvm_do_with(req, {
      burst == 2'b01;   // INCR
      len   == 8'd255;  // 256 beats
      size  == 3'b011;  // 8 bytes per beat
      addr[5:0] == 6'b0; // 64B aligned
    })
  endtask
endclass

// 4KB boundary crossing test
class axi_4k_boundary_seq extends uvm_sequence #(axi_seq_item);
  `uvm_object_utils(axi_4k_boundary_seq)
  task body();
    // Start near 4KB boundary -tests if DUT splits correctly
    `uvm_do_with(req, {
      addr[11:0] inside {[12'hFF0 : 12'hFF8]};
      burst == 2'b01;
      len   == 8'd15;
      size  == 3'b010;  // 4 bytes
    })
  endtask
endclass

// Zero-length transfer (len=0, single beat)
class axi_single_beat_seq extends uvm_sequence #(axi_seq_item);
  `uvm_object_utils(axi_single_beat_seq)
  task body();
    `uvm_do_with(req, { len == 8'd0; })
  endtask
endclass
```

---

#### 3.3 Stress Sequence -Back-to-Back with No Idle

```systemverilog
class axi_stress_seq extends uvm_sequence #(axi_seq_item);
  `uvm_object_utils(axi_stress_seq)

  int unsigned num_txns = 1000;

  task body();
    repeat(num_txns) begin
      `uvm_do_with(req, {
        burst == 2'b01;
        len   inside {[8'd15 : 8'd63]};   // Medium-to-long bursts
        size  == 3'b011;
      })
    end
  endtask
endclass
```

---

#### 3.4 Back-Pressure Injection Sequence

```systemverilog
class axi_backpressure_seq extends uvm_sequence #(axi_seq_item);
  `uvm_object_utils(axi_backpressure_seq)

  // Interleave normal transactions with back-pressure delays
  task body();
    fork
      // Stimulus thread: send transactions
      repeat(100) `uvm_do(req)
      // Back-pressure thread: de-assert RREADY/WREADY randomly
      begin
        repeat(50) begin
          int delay;
          std::randomize(delay) with { delay inside {[1:8]}; };
          p_sequencer.set_bp_delay(delay);   // Custom sequencer method
          #(delay * 10ns);
          p_sequencer.clear_bp();
        end
      end
    join
  endtask
endclass
```

---

#### 3.5 Virtual Sequence -Multi-Agent Coordination

```systemverilog
class soc_traffic_vseq extends uvm_sequence;
  `uvm_object_utils(soc_traffic_vseq)
  `uvm_declare_p_sequencer(soc_vsqr)

  task body();
    axi_stress_seq  axi_seq;
    apb_write_read_seq apb_seq;

    fork
      // AXI traffic on data path
      begin
        axi_seq = axi_stress_seq::type_id::create("axi_seq");
        axi_seq.num_txns = 500;
        axi_seq.start(p_sequencer.axi_sqr);
      end
      // APB configuration traffic
      begin
        repeat(50) begin
          apb_seq = apb_write_read_seq::type_id::create("apb_seq");
          apb_seq.start(p_sequencer.apb_sqr);
        end
      end
    join
  endtask
endclass
```

---

#### 3.6 Reset-in-Middle Scenario

```systemverilog
class reset_mid_burst_seq extends uvm_sequence #(axi_seq_item);
  `uvm_object_utils(reset_mid_burst_seq)

  task body();
    // Start a long burst
    fork
      `uvm_do_with(req, { burst == 2'b01; len == 8'd255; })
      begin
        // Assert reset after a random number of beats
        int unsigned beats_before_reset;
        std::randomize(beats_before_reset) with {
          beats_before_reset inside {[10:50]};
        };
        repeat(beats_before_reset) @(posedge p_sequencer.vif.aclk);
        p_sequencer.assert_reset();
        repeat(10) @(posedge p_sequencer.vif.aclk);
        p_sequencer.deassert_reset();
      end
    join_any
    disable fork;
    // Verify DUT recovered cleanly
    repeat(10) @(posedge p_sequencer.vif.aclk);
    `uvm_do_with(req, { burst == 2'b01; len == 8'd0; })   // Simple transaction post-reset
  endtask
endclass
```

---

### Step 4 -Scenario-to-Coverage Mapping

For each scenario, document which coverpoints it targets:

```
Scenario: axi_4k_boundary_seq
  Targets:
    - cp_burst_type      : INCR bin
    - cp_addr_boundary   : near_4k bin
    - cross_burst_x_len  : (INCR, medium) cross bin
  Expected hits per run: 1
  Recommended weight in regression: 5%
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `scenario_matrix_gen.py` | Generates a scenario-to-coverage mapping matrix from coverplan and sequence library |
| `sequence_weight_optimizer.py` | Analyzes regression coverage and recommends per-sequence run counts |
| `reset_scenario_injector.py` | Inserts reset assertions at random points during active simulation |

---

## Validation Checklist

- [ ] Each sequence verified to solve randomize() 100 times without failure
- [ ] Virtual sequence tested with all agent sequencers connected
- [ ] Reset-in-middle scenarios verified to leave DUT in clean state post-reset
- [ ] Scenario-to-coverage mapping documented for each new sequence
- [ ] Stress sequences profiled for simulation performance impact
