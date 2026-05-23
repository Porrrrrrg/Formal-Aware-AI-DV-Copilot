---
name: rtl-lint
description: Review RTL for synthesizability, style, portability, and common lint issues.
---

# RTL Lint Rule Enforcement Skill

## Description

Analyze RTL source code (Verilog / SystemVerilog / VHDL) against a comprehensive set of lint rules covering coding style, synthesizability, naming conventions, portability, and common design pitfalls. Generate structured lint reports with per-rule severity, fix suggestions, and waiver support.

- **Requires:** Python 3.8+, `pyslang` or `pyverilog` (AST parsing), `pyyaml` (rule configuration), `pandas` (report generation)
- **Supported Formats:** `.v`, `.sv`, `.vhd`, `.vhdl`, filelist `.f`

> **Expertise:**
> You are an expert RTL design and methodology engineer with deep knowledge of synthesizable RTL coding standards, tool-specific lint rules, and hardware design best practices across ASIC and FPGA flows. You enforce coding guidelines that prevent simulation/synthesis mismatches, improve readability, and reduce verification effort.

---

## Disclaimer

> **Append this notice to your first output when performing lint analysis:**
>
> `Note: Lint results are based on static rule matching and AST analysis. Some rules may produce false positives depending on tool flow or project-specific exceptions. All flagged items should be reviewed by a qualified RTL engineer. Use waiver files for intentional deviations.`

---

## When to Use This Skill

Trigger this skill when users:

- Ask to lint, style-check, or review RTL code quality
- Mention synthesizability issues, tool warnings, or coding guideline violations
- Want to enforce a naming convention or coding standard across a project
- Ask about simulation vs. synthesis mismatches
- Need to clean up RTL before handoff, review, or tapeout
- Provide `.v`, `.sv`, `.vhd`, or `.f` files for quality review
- Mention terms like: "lint", "coding style", "naming convention", "synthesizable", "latch inferred", "blocking vs non-blocking", "always block", "sensitivity list"

---

## Core Workflow

### Step 1 -Gather Context

Ask the user for:

- **RTL Files / Filelist:** Paths to source files
- **Top-Level Module:** Design root (for hierarchy-aware checks)
- **Rule Set:** Which rule categories to enable (default: all)
- **Severity Filter:** Minimum severity to report (ERROR / WARNING / INFO)
- **Project Style Guide:** Any project-specific naming convention or coding standard file (YAML/JSON)
- **Waiver File:** Known-good exceptions (optional)
- **Output Format:** Markdown (default), JSON, CSV, or inline-annotated RTL

---

### Step 2 -Parse and Index RTL

1. Parse all RTL files into AST representations
2. Build a module index: module name -file path, line range, port list
3. Index all: always blocks, assign statements, signal declarations, generate blocks, function/task definitions
4. Detect tool directives and pragmas (`// synthesis translate_off`, `/* verilint */`, etc.)

> **Helper script:** `rtl_parser.py` -shared with RTL connection check skill; outputs normalized AST JSON

---

### Step 3 -Run Lint Rule Checks

#### Category A -Synthesizability Rules

These rules flag constructs that may be accepted by simulators but rejected or mishandled by synthesis tools.

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `SYNTH_001` | ERROR | `initial` block outside of testbench context |
| `SYNTH_002` | ERROR | `#delay` in synthesizable RTL |
| `SYNTH_003` | ERROR | `fork...join` in synthesizable context |
| `SYNTH_004` | ERROR | System task `$display`, `$monitor`, `$finish` in non-testbench module |
| `SYNTH_005` | WARNING | `casex` / `casez` with potential X/Z masking -prefer `unique case` |
| `SYNTH_006` | WARNING | Combinational loop detected (signal feeds itself without a register) |
| `SYNTH_007` | WARNING | Latch inferred: incomplete sensitivity list or missing else/default in combinational `always` block |
| `SYNTH_008` | WARNING | `integer` or `real` type used in synthesizable logic |
| `SYNTH_009` | INFO | `for` loop with non-constant bounds -may cause unrollability issues |
| `SYNTH_010` | INFO | Multi-driven net via `assign` and `always` simultaneously |

**Report format:**

```
[SYNTH_007] WARNING: Latch inferred in module `ctrl_fsm`, always block at line 42
  Signal:   `next_state`
  Cause:    Missing else branch in combinational always block
  Fix:      Add `else next_state = IDLE;` or use a default assignment at top of block
```

---

#### Category B -Coding Style Rules

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `STYLE_001` | WARNING | Blocking assignment (`=`) used in clocked `always_ff` block |
| `STYLE_002` | WARNING | Non-blocking assignment (`<=`) used in combinational `always_comb` block |
| `STYLE_003` | WARNING | Mixed blocking and non-blocking assignments in same `always` block |
| `STYLE_004` | WARNING | Implicit net declaration (undeclared signal used in port connection) |
| `STYLE_005` | WARNING | `always @(*)` used instead of `always_comb` (SystemVerilog preferred) |
| `STYLE_006` | INFO | Magic numbers: numeric literal without a named parameter or localParam |
| `STYLE_007` | INFO | `begin...end` missing on multi-statement `if/else` body |
| `STYLE_008` | INFO | Sensitivity list is not `always @(*)` or `always_comb` -explicit list may be incomplete |
| `STYLE_009` | INFO | Line length exceeds 120 characters |
| `STYLE_010` | INFO | Trailing whitespace or tab/space mixing detected |

**Report format:**

```
[STYLE_001] WARNING: Blocking assignment in clocked always block -module `mac_core`, line 88
  Signal:   `acc_reg`
  Found:    acc_reg = acc_reg + data_in;
  Expected: acc_reg <= acc_reg + data_in;
  Fix:      Replace `=` with `<=` for all register assignments in always_ff blocks
```

---

#### Category C -Naming Convention Rules

Default naming conventions (customizable via style guide YAML):

| Element | Convention | Example |
|---------|-----------|---------|
| Module name | `snake_case` | `axi_slave_ctrl` |
| Port -clock | prefix `clk_` | `clk_core`, `clk_periph` |
| Port -reset | prefix `rst_` or `rstn_` | `rst_n`, `rstn_sys` |
| Port -active-low | suffix `_n` | `cs_n`, `oe_n` |
| Port -input | no required suffix | -|
| Port -output registered | suffix `_r` or `_q` | `data_out_r` |
| Parameter / localParam | `UPPER_SNAKE_CASE` | `DATA_WIDTH`, `FIFO_DEPTH` |
| Generate block | prefix `gen_` | `gen_lane` |
| Function / task | `snake_case` | `compute_parity` |

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `NAME_001` | WARNING | Module name does not follow `snake_case` convention |
| `NAME_002` | WARNING | Clock port does not use `clk_` prefix |
| `NAME_003` | WARNING | Reset port does not use `rst_` / `rstn_` prefix |
| `NAME_004` | WARNING | Active-low signal missing `_n` suffix |
| `NAME_005` | WARNING | Parameter name not in `UPPER_SNAKE_CASE` |
| `NAME_006` | INFO | Generate block label missing or does not use `gen_` prefix |
| `NAME_007` | INFO | Single-character signal name (except loop variables `i`, `j`, `k`) |

---

#### Category D -Portability and Reuse Rules

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `PORT_001` | WARNING | Hard-coded width in port declaration -use parameter instead |
| `PORT_002` | WARNING | Hard-coded address or data in RTL -define as localParam |
| `PORT_003` | WARNING | Tool-specific pragma without guarding `ifdef -may break portability |
| `PORT_004` | INFO | Module has no parameter declaration -consider adding for reuse |
| `PORT_005` | INFO | `defparam` used -deprecated; use `#(.PARAM(value))` instantiation style |
| `PORT_006` | INFO | Positional port connection at instantiation -use named connections |

---

#### Category E -Complexity and Maintainability Rules

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `CMPLX_001` | WARNING | Module has more than 64 ports -consider splitting |
| `CMPLX_002` | WARNING | Always block exceeds 100 lines -consider refactoring |
| `CMPLX_003` | WARNING | Deeply nested `if/else` (depth > 4) -consider `case` or function |
| `CMPLX_004` | INFO | Module has no comment header (author, description, date) |
| `CMPLX_005` | INFO | Signal declared but never used (dead code) |
| `CMPLX_006` | INFO | Duplicate `localparam` value defined more than once |
| `CMPLX_007` | INFO | FSM state encoding not explicitly defined -may vary by synthesis tool |

---

### Step 4 -Custom Rule Configuration

Users may provide a YAML style guide to override or extend default rules:

```yaml
naming:
  module:    snake_case
  clock_prefix:  clk_
  reset_prefix:  [rst_, rstn_]
  active_low_suffix: _n
  parameter: UPPER_SNAKE_CASE

thresholds:
  max_port_count:   48
  max_always_lines: 80
  max_if_depth:     3
  max_line_length:  100

disabled_rules:
  - STYLE_009
  - CMPLX_004

custom_rules:
  - id: PROJ_001
    description: "All output ports must be registered"
    severity: WARNING
    pattern: "output wire"   # flag unregistered outputs
```

> **Helper script:** `rule_config_loader.py` -Loads and validates the style guide YAML, merges with default rule set, resolves conflicts and disabled rules.

---

### Step 5 -Waiver Processing

Same waiver format as RTL connection check skill. Match by `rule_id`, `module`, `signal`, and `line_range`.

```json
[
  {
    "rule_id": "SYNTH_004",
    "module": "debug_monitor",
    "reason": "This module is excluded from synthesis -testbench-only",
    "owner": "dv-team",
    "expires": "2025-12-31"
  }
]
```

> **Helper script:** `waiver_manager.py` -shared across all DV skills; loads, matches, and flags expired waivers.

---

### Step 6 -Generate Report

#### Summary Header

```
========================================================
  RTL Lint Report
  Top Module  : soc_top
  Analysis Date : 2025-03-29
  Rule Set    : Full (Categories A--)
  Files Parsed: 22 files, 61 modules
========================================================

OVERALL STATUS: -ISSUES FOUND

Issue Summary:
  [ERROR]   Synthesizability    :  2
  [WARNING] Coding Style        :  9
  [WARNING] Naming Convention   : 14
  [WARNING] Portability         :  3
  [INFO]    Complexity          :  7
  [WAIVED]  Known Exceptions    :  5

Total Issues (excluding waived): 35
```

#### Per-Rule Sections

Each flagged rule entry includes: rule ID, severity, module, line number, offending code snippet, explanation, and suggested fix.

---

### Step 7 -Interactive Fix Guidance

After the report, offer to:

1. **Auto-fix safe issues** -generate corrected code for `STYLE_001/002/003`, `NAME_002/003/004/005`, `SYNTH_007` (add default assignments)
2. **Explain any rule** in depth -why it matters for synthesis, simulation, or tool compatibility
3. **Generate a waiver** for intentional deviations with a pre-filled JSON snippet
4. **Produce an annotated RTL file** -original file with lint comments inserted at flagged lines
5. **Generate a style guide YAML** based on observed patterns in the existing codebase

---

## Rule Severity Definitions

| Severity | Meaning |
|----------|---------|
| **ERROR** | Must fix -will cause synthesis failure, simulation mismatch, or functional bug |
| **WARNING** | Should fix -known risk of unexpected behavior or tool-specific issues |
| **INFO** | Best practice -improve maintainability, readability, or portability |
| **WAIVED** | Acknowledged exception -suppressed via waiver file |

---

## Lint Rule Quick Reference

| ID | Category | Severity | Short Description |
|----|----------|----------|-------------------|
| SYNTH_001 | Synthesizability | ERROR | `initial` block in synthesizable RTL |
| SYNTH_002 | Synthesizability | ERROR | `#delay` in synthesizable RTL |
| SYNTH_007 | Synthesizability | WARNING | Latch inferred |
| STYLE_001 | Coding Style | WARNING | Blocking assign in `always_ff` |
| STYLE_002 | Coding Style | WARNING | Non-blocking in `always_comb` |
| STYLE_003 | Coding Style | WARNING | Mixed blocking/non-blocking |
| NAME_002 | Naming | WARNING | Clock port missing `clk_` prefix |
| NAME_003 | Naming | WARNING | Reset port missing `rst_` prefix |
| NAME_004 | Naming | WARNING | Active-low signal missing `_n` suffix |
| NAME_005 | Naming | WARNING | Parameter not `UPPER_SNAKE_CASE` |
| PORT_001 | Portability | WARNING | Hard-coded width in port |
| PORT_006 | Portability | INFO | Positional port connection |
| CMPLX_001 | Complexity | WARNING | Module has >64 ports |
| CMPLX_005 | Complexity | INFO | Unused signal (dead code) |

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `rtl_parser.py` | Parses RTL source into AST JSON (shared with connection check skill) |
| `lint_engine.py` | Applies all enabled rule categories against the AST; returns per-rule match list with location and context |
| `rule_config_loader.py` | Loads and validates style guide YAML; merges with default rules; resolves disabled/custom rules |
| `naming_checker.py` | Dedicated checker for naming convention rules; supports configurable prefix/suffix/case patterns |
| `fix_generator.py` | Produces corrected RTL snippets for auto-fixable rules (STYLE_001/002/003, NAME series) |
| `annotated_rtl_writer.py` | Inserts lint comments at flagged lines in a copy of the source file |
| `waiver_manager.py` | Shared waiver processor (see RTL connection check skill) |
| `report_generator.py` | Assembles lint results into Markdown, JSON, or CSV report |

---

## Validation Checklist

Before closing lint analysis:

- [ ] All RTL files parsed without errors
- [ ] Rule configuration (YAML) loaded and validated if provided
- [ ] Waiver file applied and expired waivers flagged
- [ ] All ERROR-severity rules addressed (fixed or waived)
- [ ] Synthesizability rules (Category A) given highest priority
- [ ] Naming convention report reviewed -agree deviations are intentional
- [ ] Disclaimer notice included in first output

---

## Common Lint Pitfalls Reference

| Pitfall | Rule | Risk |
|---------|------|------|
| Blocking assign in `always_ff` | STYLE_001 | Race condition in simulation; synthesis may differ |
| Latch inferred | SYNTH_007 | Unintended state retention; tool-dependent behavior |
| `casex` with X masking | SYNTH_005 | X-optimism hides real mismatches |
| Hard-coded widths | PORT_001 | Breaks parameterization; prevents reuse |
| Positional port connections | PORT_006 | Silent misconnection if port order changes |
| Magic numbers | STYLE_006 | Unmaintainable; meaning unclear without context |
| Mixed blocking/non-blocking | STYLE_003 | Undefined simulation order; synthesis mismatch |
