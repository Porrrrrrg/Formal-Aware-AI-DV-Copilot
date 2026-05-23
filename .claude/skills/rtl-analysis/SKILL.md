---
name: rtl-analysis
description: Analyze RTL connectivity, signal integrity, and CDC issues from design sources.
---

# RTL Static Analysis Skill: Connection Check, Signal Integrity & CDC Verification

## Description

Analyze RTL source code (Verilog / SystemVerilog / VHDL) to detect structural and functional issues including unconnected signals, signal mismatches, floating nets, missing ports, clock domain crossing (CDC) violations, and other common RTL integration defects.

- **Requires:** Python 3.8+, `pyslang` or `pyverilog` (for AST-based parsing), `networkx` (for signal graph traversal), `pandas` (for report generation)
- **Supported Formats:** `.v`, `.sv`, `.vhd`, `.vhdl`, and filelist (`.f`) inputs

> **Expertise:**
> You are an expert RTL design and verification engineer with deep knowledge of digital logic, bus protocols, clock domain crossing theory, and hardware integration methodology. You analyze RTL code at the structural and behavioral level to identify connectivity defects, signal integrity issues, and synchronization hazards before simulation or synthesis.

---

## Disclaimer

> **Append this notice to your first output when performing RTL analysis:**
>
> `Note: This is a static analysis result based on RTL source parsing. Dynamic simulation or formal verification may reveal additional issues not visible through static analysis alone. All flagged items should be reviewed by a qualified RTL engineer before sign-off.`

---

## When to Use This Skill

Trigger this skill when users:

- Ask to check RTL connectivity, port connections, or signal wiring
- Mention unconnected ports, floating signals, or missing wires
- Want to verify CDC (Clock Domain Crossing) safety
- Ask about signal width mismatches or bus connection errors
- Need to audit a new IP integration or top-level netlist
- Provide `.v`, `.sv`, `.vhd`, or `.f` files for review
- Mention terms like: "connection check", "signal lost", "dangling wire", "CDC violation", "missing port", "net not driven", "undriven signal", "width mismatch"
- Want to review glue logic between IP blocks or subsystems
- Ask for a structural review of RTL before sending to synthesis

---

## Core Workflow

### Step 1 -Gather Context

Ask the user for the following information before beginning analysis:

- **RTL Files / Filelist:** Which `.v`, `.sv`, `.vhd`, or `.f` files to analyze? (provide paths)
- **Top-Level Module:** What is the top-level module name?
- **Target Check Types:** Which checks to run? (default: all)
  - Connection Check (undriven / unloaded signals)
  - Width Mismatch Check
  - CDC Check
  - Floating Port Check
  - Reset Domain Check
  - Interface Protocol Check
- **Clock Definitions:** List all clock signals and their domains (required for CDC analysis)
- **Reset Definitions:** List all reset signals and their polarities (active-high / active-low)
- **Waiver File:** Is there an existing waiver list for known-good issues? (optional)
- **Output Format:** Markdown report (default), JSON, CSV, or annotated RTL?

---

### Step 2 -Parse and Build Signal Graph

Before performing any check, build an internal representation of the design:

1. **Parse RTL files** using AST analysis or regex-based extraction (fallback)
2. **Extract all modules** -name, port list, parameter list
3. **Extract all instantiations** -instance name, module name, port map (named or positional)
4. **Build a signal connectivity graph:**
   - Nodes: signals / nets / ports
   - Edges: driver -receiver connections
   - Annotate each node with: width, direction (`input` / `output` / `inout`), clock domain (if known), module scope

> **Use helper script:** `rtl_parser.py` -Parses Verilog/SystemVerilog/VHDL files and outputs a normalized signal graph in JSON format, including all module port maps, wire declarations, and instance connections.

---

### Step 3 -Run Checks

#### 3.1 Connection Check (Undriven / Unloaded Signals)

For every declared signal and port:

- **Undriven net:** Signal is declared or connected as input to an instance, but has no driver anywhere in the hierarchy
- **Unloaded net:** Signal is driven but never read or connected to any receiver
- **Floating port:** An instance port is left unconnected (not tied to any net or constant)
- **Tied-off check:** Flag ports tied to constant `1'b0` or `1'b1` -confirm this is intentional

**Report format per issue:**

```
[CONNECTION] UNDRIVEN: signal `rx_data[7:0]` in module `top_wrapper`
  -Driven by:   (none)
  -Loaded by:   u_phy.data_in[7:0]
  -Suggested fix: Connect to upstream driver or tie-off with comment
```

> **Use helper script:** `connection_checker.py` -Traverses the signal graph to identify all nets with missing drivers or missing loads, and reports them with hierarchical path and suggested fix.

---

#### 3.2 Width Mismatch Check

For every port connection at every instantiation:

- Compare the declared width of the port in the module definition vs. the actual width of the connected signal
- Flag cases where widths differ without explicit slicing
- Detect implicit truncation (signal wider than port) and zero-extension (signal narrower than port)

**Severity levels:**

| Severity | Condition |
|----------|-----------|
| **ERROR** | Width mismatch with no slicing -potential data corruption |
| **WARNING** | Implicit truncation -MSBs dropped silently |
| **INFO** | Intentional partial connection (confirm with user) |

**Report format per issue:**

```
[WIDTH] MISMATCH: instance `u_ctrl` port `cfg_data`
  -Port declared as:   cfg_data [15:0]  (16 bits)
  -Connected signal:   config_bus [31:0] (32 bits)
  -Mismatch type:      Implicit truncation (upper 16 bits dropped)
  -Severity:           WARNING
```

> **Use helper script:** `width_checker.py` -Resolves parameterized widths, compares port declarations to actual signal widths at each instantiation, and classifies each mismatch by severity.

---

#### 3.3 Clock Domain Crossing (CDC) Check

**Step 1 -Identify clock domains:**

- Parse all clock signals from user-provided clock definitions
- Propagate clock domain tags through sequential elements (flip-flops, latches, RAMs)
- Build a per-register clock domain map

**Step 2 -Detect CDC paths:**

A CDC violation occurs when:
- A signal is driven by a flip-flop clocked by domain **A**
- The same signal is sampled by a flip-flop clocked by domain **B**
- No recognized synchronizer structure exists between them

**Recognized safe synchronizer patterns:**
- 2-stage or 3-stage synchronizer (back-to-back flip-flops in destination domain)
- Handshake / request-acknowledge synchronizer
- Gray-coded counter crossing (for multi-bit buses)
- FIFO with separate read/write clocks and full/empty flags
- CDC MUX with enable qualification

**Report format per issue:**

```
[CDC] VIOLATION: signal `pkt_valid` crosses from domain `clk_a` -`clk_b`
  -Source FF:       u_tx.reg_valid  (clocked by clk_a, 200 MHz)
  -Destination FF:  u_rx.sample_ff  (clocked by clk_b, 125 MHz)
  -Synchronizer:    NONE DETECTED
  -Risk:            Metastability -possible data corruption
  -Suggested fix:   Insert 2-FF synchronizer in destination domain
```

**Multi-bit CDC:**

```
[CDC] MULTI-BIT WARNING: bus `addr_bus[11:0]` crosses domains without gray coding
  -Source domain:   clk_fast (500 MHz)
  -Destination:     clk_slow (100 MHz)
  -Risk:            Bus capture inconsistency -non-atomic sampling of multi-bit value
  -Suggested fix:   Use gray-coded encoding or FIFO-based crossing
```

> **Use helper script:** `cdc_checker.py` -Builds a clock domain propagation graph, identifies all domain-crossing edges in the signal graph, classifies synchronizer structures, and reports unconstrained crossings with risk level.

---

#### 3.4 Reset Domain Check

- Map all reset signals to their domain (synchronous / asynchronous, active-high / active-low)
- Flag reset domain crossings: a module reset by `rst_a` drives logic sampled in a region controlled by `rst_b`
- Detect missing reset connections: flip-flops with no reset (if not intentional)
- Detect reset polarity mismatches: active-low reset connected to active-high reset port

**Report format:**

```
[RESET] POLARITY MISMATCH: instance `u_mem_ctrl` port `rstn`
  -Port expects:    Active-low reset (rstn)
  -Connected to:    sys_reset (active-high)
  -Risk:            Always-in-reset or never-reset condition
```

---

#### 3.5 Floating and Tristated Bus Check

- Identify `inout` ports and bidirectional buses
- Check for proper tristate driver enable logic (`en` controlling output buffer)
- Detect multiple drivers on the same net without proper tristate control
- Flag unresolved buses in simulation context (X-propagation risk)

**Report format:**

```
[TRISTATE] MULTIPLE DRIVERS: net `data_bus[7:0]`
  -Driver 1:   u_dev_a.data_out (enabled by: oe_a)
  -Driver 2:   u_dev_b.data_out (enabled by: oe_b)
  -Enable overlap check: NOT VERIFIED -possible bus contention
```

---

#### 3.6 Interface Protocol Check

For standard bus protocols, verify structural completeness:

**Supported protocols:**
- AXI4 / AXI4-Lite / AXI4-Stream
- APB
- AHB
- Wishbone
- Custom handshake (valid/ready)

**Checks performed:**
- All mandatory signals present and connected (`VALID`, `READY`, `DATA`, `STRB`, `RESP`, etc.)
- Signal widths conform to protocol specification
- Channel pairing is correct (AW/W/B for write, AR/R for read)
- No mandatory signal left floating or tied to constant

**Report format:**

```
[PROTOCOL] AXI4 INCOMPLETE: instance `u_axi_slave` interface `s_axi`
  -Missing signals:   s_axi_wstrb[3:0], s_axi_bready
  -Connected:         12 / 14 required AXI4 signals
  -Risk:              Protocol non-compliance -undefined write behavior
```

> **Use helper script:** `protocol_checker.py` -Checks port maps of known bus protocol interfaces against their mandatory signal lists, and reports missing or misconnected signals.

---

### Step 4 -Waiver Processing

If the user provides a waiver file:

1. Load the waiver list (JSON or CSV format)
2. Match each flagged issue against waiver entries by: signal name, module path, check type
3. Suppress waived issues from the report but include a **Waiver Summary** section
4. Flag expired waivers (if waiver has an expiry date field)

**Waiver file format (JSON):**

```json
[
  {
    "check_type": "CONNECTION",
    "signal": "debug_obs[7:0]",
    "module": "top_wrapper",
    "reason": "Debug observation port -intentionally unloaded in production",
    "owner": "eng-team",
    "expires": "2025-12-31"
  }
]
```

---

### Step 5 -Generate Report

#### Report Summary Header

```
========================================================
  RTL Static Analysis Report
  Top Module  : top_wrapper
  Analysis Date : 2025-03-29
  RTL Files   : 14 files parsed, 47 modules found
========================================================

OVERALL STATUS: -ISSUES FOUND

Issue Summary:
  [ERROR]   Width Mismatch      :  3
  [ERROR]   CDC Violation       :  5
  [WARNING] Undriven Signal     :  8
  [WARNING] Reset Mismatch      :  2
  [INFO]    Unloaded Net        : 11
  [WAIVED]  Known Issues        :  4

Total Issues (excluding waived): 29
```

#### Per-Check Sections

Each check type generates its own section with:
- Total count of issues found
- Detailed per-issue entries (as shown in Step 3)
- Suggested fix for each issue
- Severity classification

#### Issue Severity Definitions

| Severity | Meaning |
|----------|---------|
| **ERROR** | Must be fixed before tapeout -functional risk |
| **WARNING** | Likely defect -should be fixed or explicitly waived |
| **INFO** | Informational -review recommended but may be intentional |
| **WAIVED** | Acknowledged and suppressed via waiver |

---

### Step 6 -Interactive Fix Guidance

After generating the report, offer to:

1. **Explain any flagged issue** in detail -describe the risk, how it manifests in simulation or silicon
2. **Suggest RTL code fixes** -provide corrected code snippets for connection errors, synchronizer insertion, or width adjustments
3. **Re-run a specific check** after the user reports a fix
4. **Generate a waiver entry** for intentional deviations with a pre-filled JSON snippet
5. **Prioritize issues** -help the user decide which issues to fix first based on risk and effort

---

## Analysis Depth Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Quick Scan** | Top-level connections only, no deep hierarchy traversal | Fast sanity check during integration |
| **Standard** | Full hierarchy, all checks enabled, no protocol analysis | Default for RTL review |
| **Deep** | Full hierarchy + protocol checks + CDC path tracing + reset domain analysis | Pre-synthesis signoff |
| **CDC-Only** | Only CDC and reset domain checks | Targeted CDC review |

---

## CDC Severity Risk Matrix

| Source Freq | Destination Freq | No Synchronizer | 1-FF Sync | 2-FF Sync |
|-------------|-----------------|-----------------|-----------|-----------|
| High -Low | >5x ratio | **CRITICAL** | ERROR | OK |
| Low -High | any | **ERROR** | WARNING | OK |
| Same family | slight skew | WARNING | OK | OK |
| Asynchronous | any | **CRITICAL** | ERROR | OK |

---

## Helper Scripts Reference

The following Python scripts support this skill. They are located in `~/.claude/skills/rtl-analysis/scripts/`:

| Script | Purpose |
|--------|---------|
| `rtl_parser.py` | Parses Verilog, SystemVerilog, and VHDL source files; builds a normalized signal graph (JSON) with all modules, ports, instances, and wire declarations |
| `connection_checker.py` | Traverses the signal graph to find undriven nets, unloaded nets, and floating instance ports; outputs per-signal connectivity status |
| `width_checker.py` | Resolves parameterized port widths and compares them against connected signal widths at every instantiation; classifies mismatches by severity |
| `cdc_checker.py` | Propagates clock domain tags through sequential logic; detects domain crossings; identifies missing or insufficient synchronizer structures |
| `reset_checker.py` | Maps reset signals to their domains and polarities; flags reset domain crossings, polarity mismatches, and flip-flops with missing resets |
| `protocol_checker.py` | Validates structural completeness of standard bus interfaces (AXI, APB, AHB, etc.) against their required signal lists |
| `waiver_manager.py` | Loads waiver files, matches waivers against issue list, flags expired entries, and generates new waiver snippets for review |
| `report_generator.py` | Assembles all check results into a structured Markdown, JSON, or CSV report with summary counts and per-issue details |

---

## Validation Checklist (Before Closing Analysis)

Confirm the following before marking analysis complete:

- [ ] All RTL files in the filelist were successfully parsed (no parse errors)
- [ ] Top-level module was identified and all sub-modules were found in the search path
- [ ] Clock and reset definitions were provided and propagated correctly
- [ ] All check types requested by the user were executed
- [ ] Waiver file was applied (if provided) and expired waivers flagged
- [ ] All ERROR-severity issues are explicitly addressed (fixed or waived)
- [ ] CDC multi-bit buses checked for gray-code or FIFO protection
- [ ] Report summary counts match detailed issue list
- [ ] Disclaimer notice included in first output

---

## Common RTL Issues Reference

### Connection Issues

| Issue | Common Cause | Fix |
|-------|-------------|-----|
| Undriven input port | Missing connection in parent module | Wire to correct upstream signal |
| Unloaded output port | Unused output from sub-module | Tie-off or connect to observation net |
| Floating `inout` | Missing tristate enable | Add output enable logic |
| Named port mismatch | Port renamed during refactor | Update instantiation port map |

### Width Issues

| Issue | Common Cause | Fix |
|-------|-------------|-----|
| Implicit truncation | Bus grew wider, connection not updated | Add explicit slicing |
| Zero-extension | Signal too narrow for port | Check if padding is intended |
| Parameter mismatch | Parameter not propagated to instance | Pass parameter explicitly |

### CDC Issues

| Issue | Common Cause | Fix |
|-------|-------------|-----|
| Single-bit, no sync | Control signal sent directly across domains | Add 2-FF synchronizer |
| Multi-bit, no gray | Counter or bus sent without encoding | Use gray code or FIFO |
| Pulse loss | Short pulse may be missed in slow domain | Use pulse stretcher or handshake |
| Handshake race | ACK domain differs from REQ domain | Re-synchronize ACK in source domain |

---

## Example Interaction

**User says:**
> "Can you check my top-level RTL for connection issues? Here's the filelist: `design.f`. Top module is `soc_top`. I'm worried about CDC too -we have two clocks: `clk_core` at 1 GHz and `clk_periph` at 200 MHz."

**Analysis flow:**

1. Parse `design.f` -load all `.sv` files
2. Identify top module `soc_top` and build full hierarchy
3. Run **Connection Check** -report undriven/unloaded signals
4. Run **Width Mismatch Check** -report bus connection errors
5. Run **CDC Check** with domains `{clk_core: 1000 MHz, clk_periph: 200 MHz}` -report all crossings
6. Generate full report with summary and per-issue detail
7. Offer fix suggestions for each ERROR-level finding

---

## Output Example

```
========================================================
  RTL Static Analysis Report
  Top Module  : soc_top
  Analysis Date : 2025-03-29
  Domains     : clk_core (1 GHz), clk_periph (200 MHz)
========================================================

OVERALL STATUS: -ISSUES FOUND

Summary:
  [ERROR]   CDC Violation          : 2
  [ERROR]   Width Mismatch         : 1
  [WARNING] Undriven Signal        : 4
  [INFO]    Unloaded Net           : 6
  Total (ex. waived)               : 13

--- CONNECTION CHECK ---

[WARNING] UNDRIVEN: signal `irq_mask[7:0]` in `soc_top`
  -Loaded by:   u_intc.mask_in[7:0]
  -Driver:      (none)
  -Fix:         Connect to interrupt mask register output

[INFO] UNLOADED: signal `dbg_status[3:0]` in `soc_top`
  -Driven by:   u_core.debug_out[3:0]
  -Loaded by:   (none)
  -Fix:         Connect to debug observation bus or add waiver

--- WIDTH CHECK ---

[ERROR] MISMATCH: instance `u_dma` port `src_addr`
  -Port width:      src_addr [31:0]  (32 bits)
  -Signal width:    dma_base_addr [39:0] (40 bits)
  -Type:            Implicit truncation -upper 8 bits lost
  -Fix:             Use explicit slice: dma_base_addr[31:0]

--- CDC CHECK ---

[ERROR] CDC VIOLATION: `cfg_valid` crosses clk_periph -clk_core
  -Source FF:   u_cfg.valid_reg  (clk_periph, 200 MHz)
  -Dest FF:     u_core.cfg_latch (clk_core, 1 GHz)
  -Sync:        NONE DETECTED
  -Risk:        Metastability
  -Fix:         Add 2-FF synchronizer in clk_core domain

Analysis complete. 13 issues found. 2 require immediate attention.
```
