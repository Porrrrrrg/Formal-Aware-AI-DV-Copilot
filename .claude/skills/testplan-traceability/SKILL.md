---
name: testplan-traceability
description: Map requirements, testplans, and functional coverage into traceability matrices.
---

# Testplan -Coverage Traceability Skill

## Description

Build and maintain bidirectional traceability between design specification requirements and functional coverage points. Identifies untraced requirements (no coverage), uncovered coverpoints (no requirement), and generates traceability matrices for sign-off documentation.

- **Requires:** Python 3.8+, `pandas`, `openpyxl`; testplan in Excel/CSV/YAML; coverage report
- **Supported Formats:** Excel testplan, JAMA export, YAML testplan, SystemVerilog covergroup annotations

> **Expertise:**
> You are an expert in verification requirements traceability methodology. You ensure that every functional requirement has measurable coverage, every coverpoint is motivated by a requirement, and the sign-off package has complete and auditable requirement-to-coverage mapping.

---

## When to Use This Skill

Trigger this skill when users:
- Ask to trace requirements to coverage or tests
- Need to generate a traceability matrix for sign-off
- Ask which requirements have no coverage defined
- Ask which coverpoints have no corresponding requirement
- Mention terms like: "traceability", "requirements coverage", "testplan", "coverage mapping", "traced", "untraced requirement"

---

## Core Workflow

### Step 1 -Gather Context

- **Requirements Source:** Spec section, JAMA export, Excel testplan
- **Coverage Source:** Covergroup definitions in SV or coverage report
- **Traceability Link Format:** How are requirements linked to coverage? (comments, IDs, tags)
- **Output:** Traceability matrix (Excel), gap report (Markdown), or both

---

### Step 2 -Extract Requirements

From testplan or spec:

```
Requirements extracted: 48 total
  REQ-AXI-001: All AXI burst types (FIXED, INCR, WRAP) must be supported
  REQ-AXI-002: All transfer sizes (1B to 64B) must be supported
  REQ-AXI-003: Burst lengths 1 to 256 beats must be supported
  REQ-AXI-010: Slave must respond with SLVERR on access to reserved region
  REQ-IRQ-001: All interrupt sources must be individually maskable
  REQ-IRQ-002: Simultaneous interrupts must be arbitrated by priority
  ...
```

---

### Step 3 -Extract Coverage Points

From SV covergroup definitions:

```
Coverpoints extracted: 62 total
  axi4_write_cg::cp_burst       -bins: FIXED, INCR, WRAP
  axi4_write_cg::cp_size        -bins: 1B through 64B
  axi4_write_cg::cp_len         -bins: single, short, medium, long, max
  axi4_write_cg::cp_bresp       -bins: OKAY, SLVERR, DECERR
  irq_cg::cp_irq_src            -bins: TIMER, DMA, UART, GPIO, ERROR
  irq_cg::cp_concurrent         -bins: single, two, three+
  ...
```

---

### Step 4 -Build Traceability Matrix

```
Traceability Matrix (excerpt):
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Req ID       -Requirement                    -Coverpoint                    -Status ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------REQ-AXI-001  -All burst types supported      -axi4_write_cg::cp_burst       --     --REQ-AXI-002  -All transfer sizes             -axi4_write_cg::cp_size        --     --REQ-AXI-003  -Burst lengths 1-56            -axi4_write_cg::cp_len         --     --REQ-AXI-010  -SLVERR on reserved access      -axi4_write_cg::cp_bresp[slverr]--    --REQ-IRQ-001  -All IRQs individually maskable -(NO COVERAGE DEFINED)         --GAP --REQ-IRQ-002  -Priority arbitration           -irq_cg::cp_concurrent         --     --REQ-DMA-005  -DMA abort on bus error         -(NO COVERAGE DEFINED)         --GAP --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------```

---

### Step 5 -Gap Report

```
Traceability Gap Report:
  Total requirements:    48
  Fully traced:          41  (85.4%)
  Partially traced:       3  (6.3%)
  UNTRACED (no coverage): 4  (8.3%)  -ACTION REQUIRED

Untraced Requirements:
  REQ-IRQ-001: IRQ individual masking
    -No coverpoint for per-source mask register behavior
    -Action: Add cp_irq_mask coverpoint in irq_cg

  REQ-DMA-005: DMA abort on bus error
    -No error injection scenario covers DMA mid-transfer abort
    -Action: Add dma_error_abort_seq + cp_dma_abort coverpoint

  REQ-FIFO-003: FIFO almost-full threshold
    -No coverpoint for almost_full assertion at 75% depth
    -Action: Add cp_fifo_almost_full to fifo_cg

  REQ-PWR-002: Register retention across power cycles
    -Out of scope for current verification phase -defer to full-chip
    -Action: Document as deferred + add waiver

Orphan Coverpoints (no requirement):
  fsm_cg::cp_state::INIT_state
    -No requirement references INIT state behavior
    -Action: Add requirement or confirm as don't-care
```

---

### Step 6 -Annotating Coverage with Requirement Tags

Convention for in-code traceability comments:

```systemverilog
covergroup axi4_write_cg @(posedge aclk);
  // REQ-AXI-001: All burst types must be supported
  cp_burst: coverpoint awburst iff (awvalid && awready) {
    bins fixed = {2'b00};
    bins incr  = {2'b01};
    bins wrap  = {2'b10};
  }

  // REQ-AXI-010: Slave must return SLVERR on reserved address access
  // REQ-AXI-011: Slave must return DECERR on decode error
  cp_bresp: coverpoint bresp iff (bvalid && bready) {
    bins okay   = {2'b00};
    bins slverr = {2'b10};
    bins decerr = {2'b11};
  }
endgroup
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `req_extractor.py` | Parses testplan (Excel/YAML/JAMA) and extracts requirement IDs and descriptions |
| `coverpoint_extractor.py` | Parses SV covergroup files and extracts coverpoint names, bins, and requirement tags from comments |
| `traceability_mapper.py` | Builds bidirectional requirement -coverpoint map; identifies gaps in both directions |
| `matrix_exporter.py` | Exports traceability matrix as formatted Excel with color-coded status and filter support |

---

## Validation Checklist

- [ ] All requirements extracted from latest spec version
- [ ] All coverpoints extracted from current testbench
- [ ] Zero untraced requirements (or documented deferred/out-of-scope)
- [ ] Zero orphan coverpoints without corresponding requirement
- [ ] Traceability matrix reviewed by RTL owner and DV lead
- [ ] Matrix archived as part of sign-off package
- [ ] Deferred requirements have milestone planned for coverage
