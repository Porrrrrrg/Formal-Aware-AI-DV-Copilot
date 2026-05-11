---
name: ral-reviewer
description: Review UVM RAL models against register specs, reset values, access types, and tests.
---

# Register Model (RAL) Reviewer Skill

## Description

Review and validate UVM Register Abstraction Layer (RAL) models against register specifications. Checks include reset value correctness, field access type mapping, read-modify-write safety, shadow register behavior, aliased register detection, and auto-generated RAL code quality. Also generates RAL-based test sequences for register verification.

- **Requires:** UVM 1.2 / IEEE 1800.2 RAL library, Python for spec comparison
- **Supported Inputs:** RAL model files (.sv), register spec (Excel/CSV/IP-XACT/SystemRDL), simulation log

> **Expertise:**
> You are an expert in UVM RAL methodology and register verification. You understand all UVM register field access types (RW, RO, WO, W1C, W1S, RC, RS, WC, WS, WSRC, WCRS), shadow registers, aliased addresses, coverage models, and how to write exhaustive register test sequences that catch both RTL implementation bugs and spec documentation errors.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: RAL review results depend on the accuracy of the provided register specification. Discrepancies between spec and RAL may reflect spec errors, not RTL bugs. Always cross-reference with the RTL owner and spec author before filing bugs.`

---

## When to Use This Skill

Trigger this skill when users:
- Ask to review or validate a UVM RAL model
- See unexpected register read values or write behavior
- Need to generate register test sequences
- Ask about W1C, RO, WO, or other access types
- Mention terms like: "RAL", "register model", "uvm_reg", "uvm_reg_field", "reset value", "access type", "register test", "back-door access"

---

## Core Workflow

### Step 1 -Gather Context

- **RAL Model Files:** SystemVerilog RAL source files
- **Register Spec:** Excel/CSV/IP-XACT/SystemRDL specification
- **RTL Files:** Optional -for back-door path verification
- **Bus Interface:** APB/AXI4-Lite/custom (determines frontdoor access)

---

### Step 2 -RAL Structure Review

#### 2.1 Field Access Type Verification

Compare each field's access type in the RAL against the spec:

| Access Type | UVM Name | Behavior |
|-------------|----------|---------|
| Read-Write | `"RW"` | Normal read and write |
| Read-Only | `"RO"` | Write ignored; reads RTL value |
| Write-Only | `"WO"` | Read returns 0 or undefined |
| Write-1-to-Clear | `"W1C"` | Write 1 clears bit; write 0 no effect |
| Write-1-to-Set | `"W1S"` | Write 1 sets bit |
| Read-to-Clear | `"RC"` | Read automatically clears field |
| Write-Clear | `"WC"` | Any write clears field |
| Write-Set | `"WS"` | Any write sets field |

**Report format:**

```
[RAL_ACCESS] MISMATCH: Register IRQ_STATUS, field DMA_DONE
  RAL declares:  "RW"
  Spec requires: "W1C" (write 1 to clear interrupt)
  Risk:          RAL test will write any value to clear -RTL bug may be hidden
  Fix:           Change to: `dma_done_field.configure(this, 1, 4, "W1C", 1, 1'b0, 1, 1, 0);`
```

---

#### 2.2 Reset Value Verification

Compare reset values in RAL against spec:

```
[RAL_RESET] MISMATCH: Register CTRL, field ENABLE
  RAL reset value:   1'b0
  Spec reset value:  1'b1 (enabled by default per spec section 4.2)
  RTL reset value:   1'b1 (confirmed from RTL)
  Verdict:           RAL reset value is wrong -RAL auto-test will falsely fail
  Fix:               Change to: `enable_field.configure(this, 1, 0, "RW", 1, 1'b1, 1, 1, 0);`
```

---

#### 2.3 Address Map Verification

```
[RAL_ADDR] ERROR: Register FIFO_DATA not mapped in address map
  Spec address:  0x4000_0020
  RAL map:       Register not found -missing from uvm_reg_map add_reg() calls
  Risk:          FIFO_DATA completely untested
  Fix:           Add: axi_map.add_reg(fifo_data, 32'h0020, "RW");
```

---

#### 2.4 Field Width Verification

```
[RAL_WIDTH] MISMATCH: Register TIMER_COUNT, field COUNT
  RAL width:   16 bits
  Spec width:  32 bits
  RTL width:   32 bits
  Risk:        Upper 16 bits of timer counter never tested
```

---

### Step 3 -Generate RAL Test Sequences

#### 3.1 Basic Register Test (hw_reset_seq equivalent)

```systemverilog
class reg_reset_test_seq extends uvm_reg_sequence;
  `uvm_object_utils(reg_reset_test_seq)

  task body();
    uvm_status_e status;
    uvm_reg      regs[$];
    uvm_reg_data_t val;

    // Get all registers in the map
    model.get_registers(regs);

    foreach(regs[i]) begin
      // Read current value
      regs[i].read(status, val, UVM_FRONTDOOR);
      // Compare against reset value
      if (val !== regs[i].get_reset()) begin
        `uvm_error("REG_RESET",
          $sformatf("Register %s reset mismatch: expected 0x%0h got 0x%0h",
                    regs[i].get_name(), regs[i].get_reset(), val))
      end
    end
  endtask
endclass
```

---

#### 3.2 Read-Modify-Write Safety Test

```systemverilog
// Test that RMW does not corrupt adjacent fields
class reg_rmw_test_seq extends uvm_reg_sequence;
  `uvm_object_utils(reg_rmw_test_seq)

  task body();
    uvm_status_e status;
    uvm_reg_data_t orig_val, new_val;

    // Write known pattern to full register
    model.ctrl_reg.write(status, 32'hAAAA_AAAA);
    // Read back
    model.ctrl_reg.read(status, orig_val);

    // Modify only ENABLE field (bit 0)
    model.ctrl_reg.enable.write(status, 1'b0);

    // Read back -all other fields must be unchanged
    model.ctrl_reg.read(status, new_val);
    if ((new_val & ~32'h1) !== (orig_val & ~32'h1)) begin
      `uvm_error("RMW_CORRUPT",
        $sformatf("RMW corrupted adjacent fields: before=0x%0h after=0x%0h",
                  orig_val, new_val))
    end
  endtask
endclass
```

---

#### 3.3 W1C Field Test

```systemverilog
task test_w1c_field(uvm_reg_field field);
  uvm_status_e status;
  uvm_reg_data_t val;

  // Step 1: Trigger interrupt (RTL sets the bit)
  // (via stimulus or force)
  force_irq_trigger();
  @(posedge vif.clk);

  // Step 2: Read -bit should be 1
  field.read(status, val);
  if (val !== 1'b1)
    `uvm_error("W1C", "Interrupt bit not set after trigger")

  // Step 3: Write 0 -should have no effect
  field.write(status, 1'b0);
  field.read(status, val);
  if (val !== 1'b1)
    `uvm_error("W1C", "Writing 0 cleared W1C field -RTL bug")

  // Step 4: Write 1 -should clear
  field.write(status, 1'b1);
  field.read(status, val);
  if (val !== 1'b0)
    `uvm_error("W1C", "Writing 1 did not clear W1C field -RTL bug")
endtask
```

---

#### 3.4 Back-Door Access Test

```systemverilog
// Fast reset value check using back-door (no bus cycles)
task backdoor_reset_check();
  uvm_reg regs[$];
  uvm_reg_data_t bd_val;
  uvm_status_e status;

  model.get_registers(regs);
  foreach(regs[i]) begin
    regs[i].read(status, bd_val, UVM_BACKDOOR);
    if (bd_val !== regs[i].get_reset()) begin
      `uvm_error("BD_RESET",
        $sformatf("%s backdoor reset mismatch: exp=0x%0h got=0x%0h",
                  regs[i].get_name(), regs[i].get_reset(), bd_val))
    end
  end
endtask
```

---

### Step 4 -RAL Coverage Review

```systemverilog
// Ensure RAL coverage model is enabled
function void enable_ral_coverage();
  uvm_reg regs[$];
  model.get_registers(regs);
  foreach(regs[i]) begin
    regs[i].set_coverage(UVM_CVR_ALL);
  end
endfunction
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `ral_spec_comparator.py` | Compares RAL model fields against Excel/CSV/IP-XACT spec; reports access type, width, and reset mismatches |
| `ral_address_map_checker.py` | Verifies all spec registers are mapped with correct addresses; detects gaps and overlaps |
| `ral_test_generator.py` | Generates complete register test sequence suite: reset test, RMW test, W1C/RC/WC test, back-door check |
| `ral_coverage_report.py` | Extracts RAL coverage statistics from simulation; identifies registers with incomplete access type coverage |

---

## Validation Checklist

- [ ] All register fields match spec access types (RW/RO/WO/W1C etc.)
- [ ] All reset values match spec and RTL
- [ ] All registers present in address map with correct addresses
- [ ] No address overlaps or gaps in register map
- [ ] W1C, RC, WC fields have dedicated functional tests
- [ ] RMW test confirms adjacent field isolation
- [ ] Back-door paths verified for all registers used in coverage collection
- [ ] RAL coverage model enabled and sampled in regression
