---
name: parameterization-auditor
description: Audit RTL parameter propagation, overrides, ranges, defaults, and hard-coded values.
---

# Parameterization Auditor Skill

## Description

Audit RTL designs for parameterization completeness, correctness, and safe defaults. Checks include parameter propagation through module hierarchies, override consistency, hard-coded values that should be parameterized, parameter range safety, and cross-instance parameter conflicts.

- **Requires:** Python 3.8+, `pyslang` or `pyverilog` (AST parsing), `networkx` (hierarchy traversal), `pandas` (report generation)
- **Supported Formats:** `.v`, `.sv`, `.vhd`, `.vhdl`, filelist `.f`

> **Expertise:**
> You are an expert RTL design engineer specializing in parameterized IP design, design reuse methodology, and hardware configuration management. You understand how parameters propagate through module hierarchies, the risks of parameter defaults being silently accepted, and the importance of defensive parameter range checking.

---

## Disclaimer

> **Append this notice to your first output when performing parameterization audit:**
>
> `Note: Parameterization analysis is based on static RTL parsing. Runtime configuration and elaboration-time parameter resolution may differ across synthesis tools. Verify critical parameter values in your target tool's elaboration log. All flagged items should be reviewed by a qualified RTL engineer.`

---

## When to Use This Skill

Trigger this skill when users:

- Ask about parameter propagation, parameter override, or parameterized RTL
- Mention hard-coded width, hard-coded depth, or magic numbers in RTL
- Want to audit IP reuse readiness or portability
- Ask about `localparam`, `parameter`, `defparam`, or `generate` correctness
- Need to verify that all instances use consistent parameter sets
- Mention tool elaboration errors related to parameters
- Mention terms like: "parameter mismatch", "width mismatch from parameter", "localparam", "generate if", "design reuse", "configurable IP"

---

## Core Workflow

### Step 1 -Gather Context

Ask the user for:

- **RTL Files / Filelist:** Paths to source files
- **Top-Level Module:** Design root for hierarchy traversal
- **Expected Parameter Values:** Optional golden reference (YAML/JSON) mapping module -parameter -expected value
- **Hard-coded Value Threshold:** Flag numeric literals above this bit-width (default: 4 bits)
- **Waiver File:** Known-good exceptions (optional)
- **Output Format:** Markdown (default), JSON, CSV

---

### Step 2 -Build Parameter Hierarchy

1. Parse all modules and extract: parameter declarations, default values, localparams derived from parameters
2. For each instantiation: extract the parameter override map (named or positional)
3. Build a **parameter propagation tree**: top module -child instances -grandchild instances
4. For each parameter at each level: record declared value, overridden value, and effective resolved value
5. Flag parameters that are never overridden (always use default) and those overridden inconsistently

> **Helper script:** `param_extractor.py` -Parses RTL, extracts all parameter declarations and instance-level overrides, and builds a parameter resolution tree in JSON.

---

### Step 3 -Run Parameter Checks

#### 3.1 Parameter Propagation Check

Verify that parameters flow correctly from top to bottom without being silently dropped or reset to defaults.

| Issue | Severity | Description |
|-------|----------|-------------|
| Default accepted silently | WARNING | Instance uses parameter default instead of explicit override -may be unintentional |
| Propagation break | ERROR | Parent passes parameter A, child module has no matching port -parameter silently ignored |
| Positional override | WARNING | Parameter overridden positionally -order-dependent, fragile |
| Inconsistent override | ERROR | Same module instantiated multiple times with conflicting parameter values without clear reason |

**Report format:**

```
[PARAM_PROP] WARNING: Instance `u_fifo_cmd` uses default DATA_WIDTH=8
  Module:      sync_fifo
  Parameter:   DATA_WIDTH (default: 8)
  Override:    (none -using default)
  Context:     All other FIFO instances override DATA_WIDTH to 32
  Risk:        Silent narrowing -possible data truncation
  Fix:         Add explicit override: .DATA_WIDTH(32)
```

---

#### 3.2 Hard-coded Value Detection

Flag numeric literals that should be parameters for reusability and maintainability.

**Flagged patterns:**

- Hard-coded port widths: `input [31:0] data_in` instead of `input [DATA_WIDTH-1:0]`
- Hard-coded address ranges: `if (addr == 32'hDEAD_0000)` instead of named localParam
- Hard-coded FIFO depths, counter limits, timeout values
- Hard-coded bit positions: `data[7:4]` instead of `data[FIELD_HIGH:FIELD_LOW]`

**Report format:**

```
[PARAM_HARDCODE] WARNING: Hard-coded width in module `axi_bridge`, line 23
  Found:    input [63:0] wdata
  Risk:     Width cannot be changed without RTL edit -breaks reuse
  Fix:      Replace with parameter: parameter DATA_WIDTH = 64;
            then: input [DATA_WIDTH-1:0] wdata
```

---

#### 3.3 Parameter Range Safety Check

Verify that parameter values are within safe bounds, either through explicit `generate` checks or documented constraints.

**Checks performed:**

- Is there a `generate if` or `initial` block asserting valid parameter ranges?
- Does the parameter have a documented min/max constraint?
- Are derived localparams computed correctly from base parameters (e.g., `localparam ADDR_BITS = $clog2(DEPTH)` -what if DEPTH=0 or DEPTH=1)?
- Flag parameters that, if set to 0 or 1, would cause divide-by-zero, negative index, or zero-width port

**Recognized safe range check pattern:**

```systemverilog
// Correct parameter range assertion
generate
  if (DATA_WIDTH < 8 || DATA_WIDTH > 512)
    $error("DATA_WIDTH must be between 8 and 512");
  if ((DATA_WIDTH & (DATA_WIDTH - 1)) != 0)
    $error("DATA_WIDTH must be a power of 2");
endgenerate
```

**Report format:**

```
[PARAM_RANGE] WARNING: Parameter `DEPTH` in module `sync_fifo` has no range check
  Default value:  16
  Derived usage:  localparam ADDR_BITS = $clog2(DEPTH)
  Risk:           If DEPTH=0, $clog2(0) = 0 -zero-width address bus; synthesis behavior undefined
  Fix:            Add: if (DEPTH < 2) $error("DEPTH must be >= 2");
```

---

#### 3.4 `defparam` Usage Check

`defparam` is deprecated in SystemVerilog and unsupported in many modern flows. Flag all usages.

**Report format:**

```
[PARAM_DEFPARAM] WARNING: `defparam` used in module `top_tb`, line 112
  Found:    defparam u_dut.DATA_WIDTH = 32;
  Risk:     Deprecated construct -may be rejected by synthesis or formal tools
  Fix:      Use named parameter override at instantiation:
            u_dut #(.DATA_WIDTH(32)) u_dut_inst (...)
```

---

#### 3.5 Localparam Derivation Check

Verify that localparams derived from parameters are computed correctly and handle edge cases.

**Common error patterns:**

- `localparam ADDR_BITS = $clog2(DEPTH)` -fails when DEPTH is not a power of 2 (rounds down)
- `localparam HALF_WIDTH = DATA_WIDTH / 2` -fails when DATA_WIDTH is odd
- `localparam MAX_VAL = (1 << WIDTH) - 1` -overflows when WIDTH = 32 in 32-bit context
- Localparam used in port width before parameter is fully resolved

**Report format:**

```
[PARAM_DERIVED] WARNING: localparam `HALF_DATA` = DATA_WIDTH/2 in module `split_bus`
  Expression:   localparam HALF_DATA = DATA_WIDTH / 2;
  Risk:         Integer division truncates -if DATA_WIDTH=9, HALF_DATA=4 (1 bit lost silently)
  Fix:          Add assertion: if (DATA_WIDTH % 2 != 0) $error("DATA_WIDTH must be even");
```

---

#### 3.6 Cross-Instance Parameter Consistency Check

When the same module is instantiated multiple times, verify that parameter choices are consistent with design intent.

**Report format:**

```
[PARAM_CONFLICT] INFO: Module `sync_fifo` instantiated 4 times with different DEPTH values
  u_cmd_fifo:   DEPTH = 16
  u_data_fifo:  DEPTH = 256
  u_resp_fifo:  DEPTH = 16
  u_dbg_fifo:   DEPTH = 4
  Action:       Confirm all DEPTH choices are intentional and documented
```

---

#### 3.7 Generate Block Parameter Dependency Check

Verify that `generate if` and `generate for` constructs depend only on parameters (constants at elaboration time), not on runtime signals.

**Report format:**

```
[PARAM_GENERATE] ERROR: `generate if` condition depends on non-constant expression
  Module:     u_config_ctrl, line 88
  Found:      if (cfg_mode == 2'b01) begin  // cfg_mode is a runtime signal
  Risk:       Illegal generate usage -will fail elaboration
  Fix:        Use a parameter: parameter MODE = 1; then: if (MODE == 1)
```

---

### Step 4 -Golden Reference Comparison

If the user provides an expected parameter map (YAML), compare all resolved parameter values against the golden reference:

```yaml
# golden_params.yaml
sync_fifo:
  DATA_WIDTH: 32
  DEPTH: 256
axi_bridge:
  ADDR_WIDTH: 40
  DATA_WIDTH: 64
  ID_WIDTH: 8
```

**Report format:**

```
[PARAM_GOLDEN] ERROR: Parameter mismatch for module `axi_bridge`
  Parameter:   DATA_WIDTH
  Expected:    64  (from golden_params.yaml)
  Actual:      32  (resolved from instance u_axi_s0 override)
  Fix:         Update override to .DATA_WIDTH(64) or update golden reference
```

> **Helper script:** `golden_param_checker.py` -Loads the golden parameter YAML and compares resolved values against each instance in the hierarchy; reports deviations with location.

---

### Step 5 -Generate Report

```
========================================================
  Parameterization Audit Report
  Top Module  : soc_top
  Analysis Date : 2025-03-29
  Modules Parsed: 34
  Parameters Found: 127 declarations, 89 unique names
========================================================

OVERALL STATUS: -ISSUES FOUND

Summary:
  [ERROR]   Propagation break / generate error :  2
  [ERROR]   Golden reference mismatch          :  3
  [WARNING] Hard-coded value (should be param) : 18
  [WARNING] Default accepted silently          :  9
  [WARNING] No parameter range check           : 11
  [WARNING] defparam usage                     :  1
  [INFO]    Cross-instance value variation      :  5
  [WAIVED]  Known exceptions                   :  3

Total Issues (excluding waived): 49
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `rtl_parser.py` | Parses RTL source into AST JSON (shared) |
| `param_extractor.py` | Extracts all parameter declarations, defaults, and instance-level overrides; builds parameter resolution tree |
| `hardcode_detector.py` | Scans RTL for numeric literals above configured bit-width threshold that are candidates for parameterization |
| `range_checker.py` | Analyzes parameter usage in derived expressions and generates/initial checks; flags missing range guards |
| `golden_param_checker.py` | Compares resolved parameter values against a user-supplied golden YAML reference |
| `localparam_analyzer.py` | Validates localparam derivation expressions for edge cases (divide-by-zero, truncation, overflow) |
| `waiver_manager.py` | Shared waiver processor |
| `report_generator.py` | Assembles audit results into Markdown, JSON, or CSV |

---

## Validation Checklist

- [ ] All RTL files parsed and parameter hierarchy built
- [ ] Golden reference compared if provided
- [ ] All ERROR-severity issues addressed
- [ ] Hard-coded values reviewed -intentional ones waived with reason
- [ ] All `defparam` usages eliminated or waived
- [ ] Range checks added for all parameters used in derived width expressions
- [ ] Cross-instance parameter variations confirmed intentional
- [ ] Disclaimer notice included in first output

---

## Common Parameterization Pitfalls

| Pitfall | Check | Risk |
|---------|-------|------|
| Default silently accepted | PARAM_PROP | Wrong width or depth used without error |
| Hard-coded port width | PARAM_HARDCODE | IP cannot be reused at different widths |
| Missing range guard | PARAM_RANGE | Zero-width bus or divide-by-zero at elaboration |
| `$clog2` of non-power-of-2 | PARAM_DERIVED | Address bus one bit too narrow |
| `defparam` usage | PARAM_DEFPARAM | Tool rejection, elaboration failure |
| Positional override | PARAM_PROP | Silent wrong-parameter if order changes |
| Generate on runtime signal | PARAM_GENERATE | Elaboration error -generate requires constants |
