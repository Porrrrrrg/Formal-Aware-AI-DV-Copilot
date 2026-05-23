---
name: uvm-component-builder
description: Build and review UVM component scaffolding, TLM wiring, phases, and configuration.
---

# UVM Component Builder Skill

## Description

Generate, review, and debug Universal Verification Methodology (UVM) component scaffolding including agents, drivers, monitors, sequencers, scoreboards, environments, and tests. Covers component construction, TLM port/export wiring, phase scheduling, configuration database usage, factory override patterns, and UVM messaging best practices.

- **Requires:** SystemVerilog simulator with UVM library (UVM 1.2 or IEEE 1800.2), compatible with VCS, Xcelium, Questa
- **Supported Output:** `.sv` component files, package files, Makefile snippet

> **Expertise:**
> You are an expert UVM verification architect with deep knowledge of the UVM class hierarchy, TLM communication, phase scheduling, factory pattern, and configuration database. You design modular, reusable verification components that integrate cleanly into a layered UVM environment.

---

## Disclaimer

> **Append this notice to your first output when generating UVM components:**
>
> `Note: Generated UVM scaffolding follows IEEE 1800.2 / UVM 1.2 conventions. Adapt port names, data types, and phase logic to your specific DUT and project coding guidelines. Verify component connectivity by running a basic sanity test before integrating into the full regression suite.`

---

## When to Use This Skill

Trigger this skill when users:

- Ask to build or review a UVM agent, driver, monitor, scoreboard, or environment
- Mention TLM connections, analysis ports, or put/get exports
- Ask about UVM phases (build, connect, run, check, report)
- Need to add a new interface or protocol to an existing UVM environment
- Ask about factory overrides, `uvm_component_utils`, or `uvm_config_db`
- Mention terms like: "UVM", "agent", "sequencer", "driver", "monitor", "scoreboard", "environment", "virtual interface", "TLM"

---

## Core Workflow

### Step 1 -Gather Context

Ask the user for:

- **Protocol / Interface:** What bus or interface does this agent drive/monitor? (AXI, APB, custom)
- **Transaction Class:** Name and key fields of the sequence item
- **Agent Mode:** Active (drives DUT), passive (monitors only), or dual-mode
- **Components Needed:** Which components to generate (agent, driver, monitor, scoreboard, env, test)
- **Number of Instances:** Single agent or parameterized multi-instance
- **Scoreboard Type:** In-order, out-of-order, or reference model comparison
- **Coverage Integration:** Should the monitor include functional coverage sampling?

---

### Step 2 -Generate Components

#### 2.1 Sequence Item

```systemverilog
class apb_seq_item extends uvm_sequence_item;
  `uvm_object_utils_begin(apb_seq_item)
    `uvm_field_int(addr,  UVM_ALL_ON)
    `uvm_field_int(data,  UVM_ALL_ON)
    `uvm_field_int(pwrite,UVM_ALL_ON)
    `uvm_field_int(pstrb, UVM_ALL_ON)
  `uvm_object_utils_end

  rand logic [31:0] addr;
  rand logic [31:0] data;
  rand logic        pwrite;
  rand logic [3:0]  pstrb;

  constraint c_strb_valid {
    if (!pwrite) pstrb == 4'b0000;
    if (pwrite)  pstrb != 4'b0000;
  }

  constraint c_addr_align { addr[1:0] == 2'b00; }

  function new(string name = "apb_seq_item");
    super.new(name);
  endfunction

  function string convert2string();
    return $sformatf("addr=0x%08h data=0x%08h write=%0b strb=0b%04b",
                     addr, data, pwrite, pstrb);
  endfunction
endclass
```

---

#### 2.2 Driver

```systemverilog
class apb_driver extends uvm_driver #(apb_seq_item);
  `uvm_component_utils(apb_driver)

  virtual apb_if vif;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual apb_if)::get(this, "", "vif", vif))
      `uvm_fatal("NO_VIF", "Virtual interface not found in config_db")
  endfunction

  task run_phase(uvm_phase phase);
    apb_seq_item txn;
    forever begin
      seq_item_port.get_next_item(txn);
      drive_txn(txn);
      seq_item_port.item_done();
    end
  endtask

  task drive_txn(apb_seq_item txn);
    // Setup phase
    @(posedge vif.pclk);
    vif.psel   <= 1'b1;
    vif.penable <= 1'b0;
    vif.paddr  <= txn.addr;
    vif.pwrite <= txn.pwrite;
    vif.pwdata <= txn.pwrite ? txn.data : '0;
    vif.pstrb  <= txn.pstrb;
    // Enable phase
    @(posedge vif.pclk);
    vif.penable <= 1'b1;
    // Wait for ready
    @(posedge vif.pclk iff vif.pready);
    vif.psel    <= 1'b0;
    vif.penable <= 1'b0;
    `uvm_info("APB_DRV", txn.convert2string(), UVM_HIGH)
  endtask
endclass
```

---

#### 2.3 Monitor

```systemverilog
class apb_monitor extends uvm_monitor;
  `uvm_component_utils(apb_monitor)

  virtual apb_if vif;
  uvm_analysis_port #(apb_seq_item) ap;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    ap = new("ap", this);
    if (!uvm_config_db #(virtual apb_if)::get(this, "", "vif", vif))
      `uvm_fatal("NO_VIF", "Virtual interface not found in config_db")
  endfunction

  task run_phase(uvm_phase phase);
    apb_seq_item txn;
    forever begin
      // Wait for valid transaction
      @(posedge vif.pclk iff (vif.psel && vif.penable && vif.pready));
      txn = apb_seq_item::type_id::create("txn");
      txn.addr   = vif.paddr;
      txn.pwrite = vif.pwrite;
      txn.data   = vif.pwrite ? vif.pwdata : vif.prdata;
      txn.pstrb  = vif.pstrb;
      ap.write(txn);
      `uvm_info("APB_MON", txn.convert2string(), UVM_HIGH)
    end
  endtask
endclass
```

---

#### 2.4 Sequencer

```systemverilog
class apb_sequencer extends uvm_sequencer #(apb_seq_item);
  `uvm_component_utils(apb_sequencer)

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
endclass
```

---

#### 2.5 Agent

```systemverilog
class apb_agent extends uvm_agent;
  `uvm_component_utils(apb_agent)

  apb_driver    drv;
  apb_monitor   mon;
  apb_sequencer seqr;

  uvm_analysis_port #(apb_seq_item) ap;   // Forwarded from monitor

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    mon  = apb_monitor::type_id::create("mon", this);
    ap   = new("ap", this);
    if (get_is_active() == UVM_ACTIVE) begin
      drv  = apb_driver::type_id::create("drv", this);
      seqr = apb_sequencer::type_id::create("seqr", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    mon.ap.connect(ap);
    if (get_is_active() == UVM_ACTIVE)
      drv.seq_item_port.connect(seqr.seq_item_export);
  endfunction
endclass
```

---

#### 2.6 Scoreboard

```systemverilog
class apb_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(apb_scoreboard)

  uvm_analysis_imp #(apb_seq_item, apb_scoreboard) analysis_export;

  // Reference model: address -> expected data
  logic [31:0] ref_mem [logic [31:0]];

  int unsigned pass_cnt, fail_cnt;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    analysis_export = new("analysis_export", this);
  endfunction

  function void write(apb_seq_item txn);
    if (txn.pwrite) begin
      // Write: update reference model
      ref_mem[txn.addr] = txn.data;
      `uvm_info("SB", $sformatf("WRITE addr=0x%0h data=0x%0h", txn.addr, txn.data), UVM_MEDIUM)
    end else begin
      // Read: compare against reference
      if (ref_mem.exists(txn.addr)) begin
        if (txn.data !== ref_mem[txn.addr]) begin
          `uvm_error("SB_MISMATCH",
            $sformatf("READ MISMATCH addr=0x%0h exp=0x%0h got=0x%0h",
                      txn.addr, ref_mem[txn.addr], txn.data))
          fail_cnt++;
        end else begin
          pass_cnt++;
        end
      end
    end
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("SB_REPORT",
      $sformatf("Scoreboard: PASS=%0d FAIL=%0d", pass_cnt, fail_cnt), UVM_NONE)
    if (fail_cnt > 0)
      `uvm_error("SB_FAIL", "Scoreboard detected mismatches")
  endfunction
endclass
```

---

#### 2.7 Environment

```systemverilog
class apb_env extends uvm_env;
  `uvm_component_utils(apb_env)

  apb_agent     agent;
  apb_scoreboard sb;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agent = apb_agent::type_id::create("agent", this);
    sb    = apb_scoreboard::type_id::create("sb", this);
  endfunction

  function void connect_phase(uvm_phase phase);
    agent.ap.connect(sb.analysis_export);
  endfunction
endclass
```

---

### Step 3 -TLM Connection Patterns

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| Analysis port -export | Monitor -scoreboard | `mon.ap.connect(sb.export)` |
| Analysis port -fifo | Decoupled producer/consumer | `ap.connect(fifo.analysis_export)` |
| Get port -export | Driver pulls from sequencer | `drv.seq_item_port.connect(seqr.seq_item_export)` |
| Analysis port -subscriber | Monitor -coverage collector | `mon.ap.connect(cov.analysis_export)` |
| Analysis port -broadcast | One monitor -scoreboard + coverage | Use `uvm_analysis_port` (fan-out built in) |

---

### Step 4 -Configuration Database Patterns

```systemverilog
// Set in test (top of hierarchy)
uvm_config_db #(virtual apb_if)::set(this, "env.agent.*", "vif", apb_if_inst);
uvm_config_db #(int)::set(this, "env.agent", "is_active", UVM_ACTIVE);

// Get in component (driver, monitor)
if (!uvm_config_db #(virtual apb_if)::get(this, "", "vif", vif))
  `uvm_fatal("CFG", "vif not set")
```

---

### Step 5 -Factory Override Patterns

```systemverilog
// In test: override driver with error-injecting version
apb_error_driver::type_id::set_type_override(apb_driver::get_type());

// Or instance-specific override
apb_error_driver::type_id::set_inst_override(apb_driver::get_type(),
                                              "env.agent.drv");
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `uvm_scaffold_gen.py` | Generates full UVM component set (item, driver, monitor, seqr, agent, env) from a field list and interface description |
| `tlm_connection_checker.py` | Verifies that all analysis ports are connected in `connect_phase`; flags dangling ports |
| `uvm_phase_tracer.py` | Adds phase entry/exit debug messages to all components for bring-up debug |

---

## Validation Checklist

- [ ] All `uvm_*_utils` macros applied to every component and object
- [ ] `build_phase` creates all sub-components and retrieves config_db entries
- [ ] `connect_phase` wires all TLM ports and exports
- [ ] All `uvm_fatal` guards on mandatory config_db entries
- [ ] Scoreboard report_phase raises error if fail_cnt > 0
- [ ] Factory utils registered for all overridable components
- [ ] Virtual interface retrieved in driver and monitor build_phase
