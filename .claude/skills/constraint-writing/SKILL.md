---
name: constraint-writing
description: Generate and review SystemVerilog randomization constraints for DV testbenches.
---

# Constraint Writing Skill

## Description

Generate, review, and debug SystemVerilog randomization constraints for verification testbenches. Covers constraint construction for all data types, solve-order directives, soft/hard constraints, weight-based distributions, constraint inheritance in UVM sequences, constraint mode control, and debugging unsolvable constraint sets.

- **Requires:** SystemVerilog simulator with constraint solver (VCS, Xcelium, Questa, etc.)
- **Supported Contexts:** UVM sequence items, transaction objects, standalone randomizable classes, inline `randomize() with` calls

> **Expertise:**
> You are an expert in SystemVerilog constraint-driven random verification. You understand constraint solver behavior, solve-order semantics, distribution weights, constraint inheritance and override in UVM class hierarchies, and how to diagnose and fix unsolvable or poorly-directed constraint sets. You write constraints that maximize coverage closure efficiency.

---

## Disclaimer

> **Append this notice to your first output when generating constraints:**
>
> `Note: Generated constraints are starting points based on provided specifications. Constraint solver behavior may vary slightly across simulators. Always verify that generated transactions cover intended scenarios by checking functional coverage closure. Constraint debug may require simulator-specific tools (e.g., VCS constraint debug, Xcelium constraint analyzer).`

---

## When to Use This Skill

Trigger this skill when users:

- Ask to write or review `rand`, `randc`, or `constraint` blocks
- Mention `randomize()` failures, constraint solver errors, or unsolvable constraints
- Need to generate specific distributions, weighted random, or corner-case stimuli
- Ask about `solve...before`, `dist`, `inside`, `soft` constraints
- Need to constrain AXI, APB, or other bus protocol transaction fields
- Ask about constraint inheritance, `constraint_mode()`, or `rand_mode()`
- Mention terms like: "constraint", "randomization", "rand variable", "solve order", "distribution", "coverage driven", "directed random"

---

## Core Workflow

### Step 1 -Gather Context

Ask the user for:

- **Object Type:** UVM sequence item, transaction class, or standalone class
- **Fields to Constrain:** Signal names, widths, and semantic meaning
- **Protocol / Spec:** Bus protocol or spec driving the constraints (if applicable)
- **Constraint Goals:** What scenarios to target -normal operation, corner cases, error injection, stress
- **Distribution Preference:** Uniform, weighted, biased toward specific values/ranges
- **Solve Order Requirements:** Any fields that must be solved before others
- **Existing Constraints:** Any base class constraints to inherit or override
- **Coverage Goals:** Covergroups or coverpoints this constraint set should help hit

---

### Step 2 -Classify Constraint Types

Before writing, classify each field's constraint requirement:

| Type | Use Case | SV Construct |
|------|----------|-------------|
| Range bound | Limit value to valid protocol range | `inside {[min:max]}` |
| Enumerated set | Restrict to legal values | `inside {A, B, C}` |
| Weighted distribution | Bias random toward specific values | `dist {val := weight}` |
| Conditional | Field B depends on field A | `if (A == X) B == Y` |
| Relational | Relationship between fields | `B > A`, `B == A + 1` |
| Alignment | Address/data alignment | `addr % align == 0` |
| Exclusion | Illegal value ranges | `!(field inside {bad_vals})` |
| Solve order | Force solver sequence | `solve A before B` |
| Soft | Overridable default | `soft field == default_val` |

---

### Step 3 -Generate Constraints

#### 3.1 Basic Range and Set Constraints

```systemverilog
class axi_txn extends uvm_sequence_item;
  rand logic [39:0] addr;
  rand logic [2:0]  size;
  rand logic [7:0]  len;
  rand logic [1:0]  burst;
  rand logic        locked;

  // Address must be within valid memory map range
  constraint c_addr_range {
    addr inside {[40'h0000_0000 : 40'h00FF_FFFF],   // DDR region
                 [40'h4000_0000 : 40'h400F_FFFF]};   // MMIO region
  }

  // AXI4 burst size: 1B to 128B (3'b000 to 3'b110)
  constraint c_size_valid {
    size inside {[3'b000 : 3'b110]};
  }

  // AXI4 burst type: FIXED, INCR, WRAP only (2'b11 reserved)
  constraint c_burst_valid {
    burst inside {2'b00, 2'b01, 2'b10};
  }

  // WRAP burst requires power-of-2 length: 2,4,8,16 beats
  constraint c_wrap_len {
    if (burst == 2'b10)
      len inside {8'd1, 8'd3, 8'd7, 8'd15};
  }

endclass
```

---

#### 3.2 Weighted Distribution Constraints

Use `dist` to control the probability of specific values or ranges:

```systemverilog
// Bias toward short bursts (common case) with occasional long bursts
constraint c_len_dist {
  len dist {
    [8'd0  : 8'd3]  := 50,   // Short bursts: 50% probability
    [8'd4  : 8'd15] := 30,   // Medium bursts: 30%
    [8'd16 : 8'd63] := 15,   // Long bursts: 15%
    [8'd64 : 8'd255]:= 5     // Max length: 5%
  };
}

// Weighted burst type -INCR most common in real traffic
constraint c_burst_dist {
  burst dist {
    2'b00 := 10,   // FIXED:  10%
    2'b01 := 80,   // INCR:   80%
    2'b10 := 10    // WRAP:   10%
  };
}
```

---

#### 3.3 Alignment and Boundary Constraints

```systemverilog
// Address must be naturally aligned to transfer size
constraint c_addr_align {
  addr[2:0] == 3'b0;   // For size=3'b011 (8-byte), force 8B alignment
  // General form:
  // addr % (1 << size) == 0;
}

// Prevent 4KB boundary crossing for INCR bursts
constraint c_no_4k_cross {
  if (burst == 2'b01)  // INCR burst
    (addr[11:0] + ((len + 1) << size)) <= 12'hFFF;
}

// Address aligned to cache line (64 bytes)
constraint c_cacheline_align {
  addr[5:0] == 6'b0;
}
```

---

#### 3.4 Solve Order Directives

Use `solve...before` when a field's constraint depends on another field's value, and you want the solver to commit to the first field before constraining the second:

```systemverilog
// Solve burst type before len -len constraints depend on burst
constraint c_solve_order {
  solve burst before len;
  solve size  before addr;   // Align addr after size is known
}

// Without solve order, the solver may pick len first and fail to satisfy
// the WRAP-specific len constraints
```

---

#### 3.5 Soft Constraints

Soft constraints express preferred defaults that can be overridden by derived class constraints or inline `randomize() with` calls:

```systemverilog
// Default to INCR burst -can be overridden for specific tests
constraint c_burst_default_soft {
  soft burst == 2'b01;
}

// Default to small transfers -overridden in stress tests
constraint c_len_default_soft {
  soft len inside {[8'd0 : 8'd7]};
}
```

Usage in a derived test:

```systemverilog
// Override soft constraint inline for a stress scenario
assert(txn.randomize() with {
  len inside {[8'd64 : 8'd255]};  // Overrides soft c_len_default_soft
});
```

---

#### 3.6 Error Injection Constraints

```systemverilog
class axi_error_txn extends axi_txn;

  rand bit inject_addr_error;
  rand bit inject_prot_error;

  // 10% chance of injecting an out-of-range address
  constraint c_error_rate {
    inject_addr_error dist { 1'b1 := 10, 1'b0 := 90 };
    inject_prot_error dist { 1'b1 := 5,  1'b0 := 95 };
  }

  // If injecting address error, choose an illegal address
  constraint c_addr_error_val {
    if (inject_addr_error)
      !(addr inside {[40'h0000_0000 : 40'h00FF_FFFF],
                     [40'h4000_0000 : 40'h400F_FFFF]});
    else
      addr inside {[40'h0000_0000 : 40'h00FF_FFFF],
                   [40'h4000_0000 : 40'h400F_FFFF]};
  }

endclass
```

---

#### 3.7 Constraint Inheritance and Override in UVM

```systemverilog
// Base item -general constraints
class base_txn extends uvm_sequence_item;
  rand logic [31:0] data;
  rand logic [7:0]  len;

  constraint c_len_base { len inside {[8'd0 : 8'd15]}; }
endclass

// Extended item -stress test overrides len range
class stress_txn extends base_txn;

  // Turn off base constraint and apply new one
  constraint c_len_stress {
    len inside {[8'd64 : 8'd255]};
  }

  function new(string name = "stress_txn");
    super.new(name);
    c_len_base.constraint_mode(0);   // Disable base constraint
  endfunction

endclass
```

---

#### 3.8 Constraint for Coverage Closure

When a coverpoint is not being hit, write a targeted constraint to drive the specific scenario:

```systemverilog
// Coverage target: hit len == 255 (max burst)
constraint c_hit_max_burst {
  len == 8'd255;
  burst == 2'b01;   // INCR only for len=255
  size == 3'b011;   // 8-byte transfers
}

// Coverage target: hit all burst types with addr close to 4KB boundary
constraint c_boundary_cross_test {
  addr[11:0] inside {[12'hFF0 : 12'hFFF]};   // Near 4KB boundary
  burst == 2'b01;
  len inside {[8'd1 : 8'd15]};
}
```

---

### Step 4 -Constraint Debug

When `randomize()` fails or returns 0, follow this debug process:

#### Step 4.1 -Identify Conflicting Constraints

```systemverilog
// Enable constraint solver debug (VCS)
// +define+SV_RAND_DEBUG or simulator option

// Narrow down: disable constraints one by one
txn.c_wrap_len.constraint_mode(0);
if (txn.randomize()) begin
  $display("c_wrap_len was causing conflict");
end
```

#### Step 4.2 -Common Conflict Patterns

| Conflict Type | Symptom | Fix |
|---------------|---------|-----|
| Overlapping range exclusions | No value satisfies `inside` and `!inside` | Review coverage of both constraints |
| Conditional deadlock | `if (A==X) B==Y` but B is also constrained to non-Y | Relax or separate conditions |
| Solve order loop | A `solve before` B and B `solve before` A | Remove circular solve dependency |
| Too-tight distribution | `dist` weights don't cover all `inside` values | Ensure dist range covers constraint range |
| Derived field over-constrained | C is constrained by both A and B and they conflict | Use `solve before` or relax one side |

#### Step 4.3 -Debug Checklist

```
Constraint Debug Checklist:
  [ ] Run with single constraint enabled at a time to isolate conflict
  [ ] Check if all dist ranges are subsets of inside ranges
  [ ] Verify conditional constraints cover all enum/field value cases
  [ ] Check solve-before order does not create circular dependency
  [ ] Confirm randc variables are not exhausted (call rand_mode(0)/rand_mode(1) to reset)
  [ ] Verify no implicit 0-width or 1-value ranges remain after conditions applied
```

---

### Step 5 -Constraint Library Templates

#### AXI4 Write Transaction

```systemverilog
constraint c_axi4_write_legal {
  // Address aligned to size
  addr % (1 << size) == 0;
  // WRAP burst: len must be 1,3,7,15 (2,4,8,16 beats)
  if (burst == 2'b10) len inside {8'd1, 8'd3, 8'd7, 8'd15};
  // Size max 128B
  size inside {[3'b000 : 3'b110]};
  // No reserved burst type
  burst inside {2'b00, 2'b01, 2'b10};
  // No 4KB crossing for INCR
  if (burst == 2'b01)
    (addr[11:0] + ((len+1) << size)) <= 13'd4096;
}
```

#### APB Transaction

```systemverilog
constraint c_apb_legal {
  // PADDR must be word-aligned
  addr[1:0] == 2'b00;
  // PSTRB valid only during write
  if (!pwrite) pstrb == 4'b0000;
  // PSTRB must be non-zero for write
  if (pwrite)  pstrb != 4'b0000;
}
```

#### Interrupt Stress

```systemverilog
constraint c_irq_storm {
  // Multiple simultaneous interrupts -hit priority arbitration
  $countones(irq_vec) dist {
    [1:1]   := 40,   // Single IRQ
    [2:4]   := 40,   // Few simultaneous
    [5:16]  := 20    // Many simultaneous -stress arbitration
  };
}
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `constraint_template_gen.py` | Generates SV constraint class skeletons from a user-provided field list and protocol spec |
| `constraint_debugger.py` | Analyzes a constraint class and identifies potential conflicts, over-constrained variables, and solve-order issues |
| `coverage_gap_constrainer.py` | Reads a coverage database and generates targeted constraints to hit uncovered bins |
| `dist_weight_optimizer.py` | Analyzes coverage hit rates per bin and suggests adjusted `dist` weights to balance coverage closure |

---

## Validation Checklist

- [ ] All protocol-required fields constrained to legal ranges
- [ ] `solve...before` directives added where conditional constraints exist
- [ ] Soft constraints used for overridable defaults
- [ ] Error injection constraints have realistic probability weights
- [ ] Constraint set verified to solve (run 100 randomize() calls without failure)
- [ ] Coverage closure verified -targeted constraints hit intended coverpoints
- [ ] No circular solve dependencies
- [ ] Constraint inheritance in UVM hierarchy reviewed for conflicts

---

## Common Constraint Pitfalls

| Pitfall | Risk | Fix |
|---------|------|-----|
| Missing solve order on conditional | Solver commits B before knowing A -constraint fails | Add `solve A before B` |
| dist range not covered by inside | Some weighted values excluded by hard constraint | Ensure dist -inside range |
| Tight constraints in base class | Derived class cannot override easily | Use `soft` in base; override in derived |
| `randc` not reset between tests | Variables exhausted -randomize() fails | Call `rand_mode(0); rand_mode(1)` |
| No error scenario constraints | Design never sees illegal inputs | Add explicit error injection class |
| Overlapping conditional coverage | Some field combinations never generated | Use cross coverage to verify all combos |
