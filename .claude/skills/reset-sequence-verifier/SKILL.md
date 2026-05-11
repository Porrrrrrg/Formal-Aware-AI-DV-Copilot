---
name: reset-sequence-verifier
description: Check reset sequencing, polarity, connectivity, and asynchronous deassertion safety.
---

# Reset Sequence Verifier Skill

## Description

Analyze RTL source code and simulation environments to verify reset correctness across the full chip or subsystem. Checks include reset ordering dependencies, sequencing timing, glitch detection, polarity consistency, missing reset connections, asynchronous reset removal (de-assertion) safety, and reset domain isolation.

- **Requires:** Python 3.8+, `pyslang` or `pyverilog` (AST parsing), `networkx` (reset dependency graph), `pandas` (report generation)
- **Supported Formats:** `.v`, `.sv`, `.vhd`, `.vhdl`, filelist `.f`, UPF/CPF (for power-aware reset domains)

> **Expertise:**
> You are an expert in digital reset architecture, reset sequencing methodology, and chip-level bring-up. You understand the risks of improper reset ordering, glitchy resets, asynchronous deassertion without synchronization, and the interaction between multiple reset domains in complex SoC designs.

---

## Disclaimer

> **Append this notice to your first output when performing reset analysis:**
>
> `Note: Reset analysis is based on static RTL parsing and user-provided reset definitions. Dynamic glitch behavior and board-level reset timing cannot be fully captured statically. Simulation and silicon bring-up validation are still required. All flagged items should be reviewed by a qualified RTL or DV engineer.`

---

## When to Use This Skill

Trigger this skill when users:

- Ask about reset correctness, reset sequencing, or reset ordering
- Mention glitchy reset, reset glitch, or metastability on reset
- Ask about asynchronous vs. synchronous reset, reset synchronizer
- Need to verify reset domain isolation or cross-reset-domain safety
- Mention chip bring-up failures suspected to be reset-related
- Provide RTL with multiple reset signals and want ordering checked
- Mention terms like: "reset tree", "reset controller", "power-on reset", "POR", "cold reset", "warm reset", "reset fan-out", "deassert", "reset release"

---

## Core Workflow

### Step 1 -Gather Context

Ask the user for:

- **RTL Files / Filelist:** Paths to source files
- **Top-Level Module:** Design root
- **Reset Signal Definitions:** For each reset signal:
  - Name
  - Polarity (active-high / active-low)
  - Type (synchronous / asynchronous)
  - Source (POR, software, watchdog, external pin, etc.)
  - Expected assertion duration (minimum pulse width)
- **Reset Ordering Spec:** Which resets must assert/deassert before others (if known)
- **Clock Definitions:** Clock signals and frequencies (for synchronizer analysis)
- **Waiver File:** Known-good exceptions (optional)
- **Output Format:** Markdown (default), JSON, CSV

---

### Step 2 -Build Reset Domain Map

1. Parse RTL and identify all reset signals by name pattern and usage
2. For each flip-flop, latch, and RAM: record which reset signal controls it
3. Build a **reset fan-out tree**: root reset sources -intermediate reset controllers -leaf flip-flops
4. Annotate each node with: polarity, type (sync/async), clock domain affiliation
5. Identify reset domain boundaries: sets of flip-flops sharing the same reset signal

> **Helper script:** `reset_mapper.py` -Parses RTL, identifies all reset-controlled sequential elements, and builds a reset fan-out graph in JSON format with polarity, type, and domain annotations.

---

### Step 3 -Run Reset Checks

#### 3.1 Reset Ordering and Sequencing Check

For designs with multiple reset signals, verify that ordering constraints are structurally enforced:

- **Dependency check:** If block B depends on block A being initialized first, then `reset_B` should deassert only after `reset_A` has deasserted and A has completed initialization
- **Controller check:** Is there an explicit reset sequencer/controller? Does it implement the correct ordering?
- **Hold time check:** Does each reset signal stay asserted long enough for all downstream flip-flops to reliably capture the reset state?

**Report format:**

```
[RESET_SEQ] WARNING: No ordering constraint detected between `rst_cpu` and `rst_mem`
  rst_cpu domain:   u_cpu_core (512 FFs)
  rst_mem domain:   u_ddr_ctrl (128 FFs)
  Risk:             CPU may begin memory access before DDR controller is out of reset
  Suggested fix:    Assert rst_cpu until rst_mem has deasserted and DDR init is complete
```

---

#### 3.2 Reset Glitch Detection

A reset glitch is a spurious pulse on the reset net -too short to reliably reset all flip-flops but long enough to partially disturb state.

**Checks performed:**

- Identify resets derived from combinational logic (AND/OR of multiple signals) without glitch filtering
- Flag resets that pass through asynchronous MUX paths
- Detect resets generated from software register bits without synchronization to the reset clock
- Check for resets that are AND-gated with data signals (functional logic driving reset)

**Report format:**

```
[RESET_GLITCH] ERROR: Reset signal `rst_periph_n` derived from combinational logic
  Expression:  rst_periph_n = por_n & sw_rst_n & wdt_rst_n
  Module:      u_rst_ctrl, line 44
  Risk:        Any glitch on sw_rst_n or wdt_rst_n propagates directly to rst_periph_n
  Fix:         Register the combined reset output in the destination clock domain;
               use a dedicated reset synchronizer cell
```

---

#### 3.3 Asynchronous Reset Deassertion Safety Check

Asynchronous resets are safe to assert at any time, but **deassertion must be synchronous** to avoid metastability. This is the most common reset-related silicon bug.

**Checks performed:**

- Identify all flip-flops using asynchronous reset (`always @(posedge clk or negedge rstn)`)
- For each async reset: verify that its deassertion path passes through a reset synchronizer (2-FF synchronizer clocked by the destination clock)
- Flag any async reset that deasserts without synchronization

**Recognized safe synchronizer pattern:**

```systemverilog
// Correct async reset synchronizer
always_ff @(posedge clk or negedge por_n) begin
    if (!por_n) begin
        sync_ff1 <= 1'b0;
        sync_ff2 <= 1'b0;
    end else begin
        sync_ff1 <= 1'b1;
        sync_ff2 <= sync_ff1;
    end
end
assign rstn_sync = sync_ff2;
```

**Report format:**

```
[RESET_ASYNC] ERROR: Asynchronous reset `rst_io_n` deasserts without synchronizer
  Used in:     u_gpio, u_uart, u_spi (38 flip-flops)
  Clock:       clk_io (50 MHz)
  Risk:        Metastability on reset release -FFs may capture unknown state
  Fix:         Insert a 2-FF reset synchronizer clocked by clk_io before rstn_io distribution
```

---

#### 3.4 Reset Polarity Mismatch Check

- Compare the polarity declared in user-provided reset definitions against the actual RTL usage
- Detect resets connected to ports that expect opposite polarity
- Flag inverted reset connections without explicit comment

**Report format:**

```
[RESET_POL] ERROR: Polarity mismatch -instance `u_sram` port `RESETn`
  Port expects:   Active-low (RESETn)
  Connected to:   sys_reset (active-high, no inversion)
  Risk:           SRAM always in reset or never reset
  Fix:            Invert: .RESETn(~sys_reset) or use correct reset signal
```

---

#### 3.5 Missing Reset Check

Identify flip-flops with no reset connection:

- For every `always_ff` block: check whether a reset branch exists
- Classify as **intentional** (e.g., datapath registers that don't need reset) or **suspect** (control path, FSM state, valid/ready registers)
- Flag suspect un-reset registers

**Report format:**

```
[RESET_MISSING] WARNING: FSM state register `current_state` has no reset
  Module:   u_arb_fsm, line 77
  Type:     FSM state -control-critical
  Risk:     Unknown FSM state on power-up; possible deadlock
  Fix:      Add reset branch: if (!rstn) current_state <= IDLE;
```

---

#### 3.6 Reset Fan-out Check

Excessive reset fan-out can cause timing violations on the reset tree, leading to different flip-flops coming out of reset at different clock cycles.

**Checks performed:**

- Count fan-out of each reset signal
- Flag resets driving more than a configurable threshold (default: 512 flip-flops) without buffering
- Identify unbalanced reset trees where some branches have significantly more load than others

**Report format:**

```
[RESET_FANOUT] WARNING: Reset signal `rst_core_n` drives 2,847 flip-flops without buffering
  Module:      u_core_top
  Risk:        Reset timing violation -last FF may release reset 1- cycles after first FF
  Fix:         Insert reset buffer tree; use synthesis reset_tree or reset_buf cells
```

---

#### 3.7 Cross-Reset-Domain Check

A cross-reset-domain issue occurs when logic in one reset domain drives logic in another reset domain without proper isolation.

**Checks performed:**

- Identify signals that cross from a region controlled by `reset_A` to a region controlled by `reset_B`
- Verify isolation cells or handshake logic exists at the boundary
- Flag cases where `reset_A` deasserts while `reset_B` is still asserted, leaving driven values undefined

**Report format:**

```
[RESET_XD] WARNING: Signal `cfg_valid` crosses from domain `rst_cpu` to domain `rst_periph`
  Source:    u_cpu.cfg_out   (reset by rst_cpu)
  Dest:      u_uart.cfg_in   (reset by rst_periph)
  Risk:      If rst_periph releases before rst_cpu, cfg_in may sample garbage
  Fix:       Add isolation cell gated by rst_periph on the boundary;
             or ensure rst_periph always deasserts after rst_cpu
```

---

### Step 4 -Reset Sequence Timeline Generator

If the user provides an expected reset ordering specification, generate a visual ASCII timeline showing correct assertion/deassertion sequence:

```
Reset Sequence Timeline (time flows right -
--------------------------------------------------------------------------------------------------------------------------
por_n        -------------                             ---------------------
                   --------------------------------------------------------------rst_sys_n    ---------------------                   -----------------------------
                       ------------------------------------------rst_cpu_n    ---------------------------------       -----------------------------------------
                             ------------------rst_periph_n --------------------------------------------- -----------------------------------------
                                   --------------------------------------------------------------------------------------------------------------------------------
Phase:       [ POR ] [ SYS INIT ] [ CPU BOOT ] [ PERIPH UP ]
```

> **Helper script:** `reset_timeline_gen.py` -Generates an ASCII or SVG reset sequence diagram from a user-provided ordering spec or inferred ordering from the reset controller RTL.

---

### Step 5 -Waiver Processing

```json
[
  {
    "check_type": "RESET_MISSING",
    "signal": "rx_shift_reg",
    "module": "u_uart_rx",
    "reason": "Datapath shift register -reset not required; value is valid only after start bit detected",
    "owner": "rtl-team",
    "expires": "2025-12-31"
  }
]
```

---

### Step 6 -Generate Report

```
========================================================
  Reset Sequence Verification Report
  Top Module  : soc_top
  Analysis Date : 2025-03-29
  Reset Signals : 8 defined, 3 domains
========================================================

OVERALL STATUS: -ISSUES FOUND

Summary:
  [ERROR]   Async deassertion without sync :  3
  [ERROR]   Polarity mismatch              :  1
  [ERROR]   Reset glitch risk              :  2
  [WARNING] Missing reset on FSM register  :  4
  [WARNING] Cross-reset-domain path        :  6
  [WARNING] Reset fan-out exceeds limit    :  1
  [INFO]    Unordered reset pair           :  3
  [WAIVED]  Known exceptions               :  2

Total Issues (excluding waived): 20
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `rtl_parser.py` | Parses RTL and extracts sequential elements with reset connections (shared) |
| `reset_mapper.py` | Builds reset fan-out graph; annotates each FF with reset signal, polarity, type, and clock domain |
| `reset_seq_checker.py` | Analyzes reset ordering dependencies; flags unordered or incorrectly ordered reset pairs |
| `reset_glitch_checker.py` | Identifies combinationally-derived or MUX-sourced resets prone to glitching |
| `reset_sync_checker.py` | Detects async resets that deassert without a 2-FF synchronizer in the destination clock domain |
| `reset_fanout_checker.py` | Counts reset fan-out per signal; flags over-driven nets without buffering |
| `reset_timeline_gen.py` | Generates ASCII or SVG reset sequence diagrams from spec or RTL inference |
| `waiver_manager.py` | Shared waiver processor |
| `report_generator.py` | Assembles results into Markdown, JSON, or CSV |

---

## Validation Checklist

- [ ] All reset signals identified and polarity confirmed by user
- [ ] Clock definitions provided for synchronizer analysis
- [ ] All ERROR-severity issues addressed (fixed or waived)
- [ ] Async reset deassertion check passed for all clock domains
- [ ] FSM state registers all have reset connections
- [ ] Reset fan-out within limits or buffering confirmed
- [ ] Cross-reset-domain paths reviewed and isolation confirmed
- [ ] Disclaimer notice included in first output

---

## Common Reset Pitfalls Reference

| Pitfall | Check | Risk |
|---------|-------|------|
| Async reset without deassertion sync | RESET_ASYNC | Metastability on reset release |
| Combinational reset glitch | RESET_GLITCH | Partial reset of state machines |
| FSM register without reset | RESET_MISSING | Unknown state on power-up, deadlock |
| Polarity inversion error | RESET_POL | Always-in-reset or never-reset |
| Unordered multi-domain reset | RESET_SEQ | Block A accesses uninitialized Block B |
| Excessive fan-out | RESET_FANOUT | Reset skew across chip; cycle-accurate release not guaranteed |
| Cross-reset-domain data | RESET_XD | Undefined values sampled across domain boundary |
