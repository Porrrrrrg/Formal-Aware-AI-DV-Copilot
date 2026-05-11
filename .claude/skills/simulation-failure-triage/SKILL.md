---
name: simulation-failure-triage
description: Triage simulation failures, assertion violations, mismatches, timeouts, and debug probes.
---

# Simulation Failure Triage Skill

## Description

Analyze simulation failure logs, assertion violations, scoreboard mismatches, and timeout errors to identify root cause, classify failure type, and recommend targeted waveform probes and debug strategies. Covers first-failure identification, X-propagation analysis, race condition detection, and UVM phase/objection issues.

- **Requires:** Simulation log files (.log), waveform files (.vcd, .fsdb, .shm), UVM report summary
- **Supported Simulators:** VCS, Xcelium, Questa

> **Expertise:**
> You are an expert in simulation debug methodology for complex SoC designs. You systematically narrow the root cause of failures from high-level symptoms to specific RTL lines, signal values, or testbench logic issues, using logs, waveforms, and structural knowledge.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: Failure triage is based on log analysis and static reasoning. Waveform inspection and seed-reproducible simulation runs may be required to confirm root cause. Some failures are seed-dependent (race conditions) and may not reproduce deterministically.`

---

## When to Use This Skill

Trigger this skill when users:
- Share a simulation failure log and ask for help
- See UVM_ERROR, UVM_FATAL, or assertion failures they cannot explain
- Get scoreboard mismatches or timeout failures
- Ask about X-propagation or Z values in simulation
- Mention terms like: "sim failure", "assertion fired", "scoreboard mismatch", "UVM_FATAL", "timeout", "X propagation", "phase hang"

---

## Core Workflow

### Step 1 -Gather Context

- **Log File:** Simulation output log (paste or path)
- **Failure Type:** UVM error, assertion, timeout, scoreboard, X/Z value
- **Test Name and Seed:** For reproducibility
- **Recent Changes:** Any RTL or testbench changes before this failure appeared?

---

### Step 2 -Failure Classification

| Failure Type | Typical Symptoms | First Look |
|-------------|-----------------|-----------|
| Assertion violation | `Assertion FAILED at time X` | Find which property; check antecedent timing |
| Scoreboard mismatch | `EXPECTED: X GOT: Y` | Identify transaction; trace signal back |
| UVM_FATAL -no VIF | `Virtual interface not found` | Config_db path mismatch |
| UVM_FATAL -phase hang | Simulation never ends | Check raise_objection/drop_objection |
| X propagation | `Z/X on output`, `X in comparison` | Find X source; check reset, initialization |
| Timeout | `MAX CYCLES REACHED` | Check for deadlock, missing handshake |
| Race condition | Fails on some seeds | Look for non-blocking vs blocking mix |

---

### Step 3 -Log Analysis Patterns

#### 3.1 Assertion Failure

```
# Log pattern:
# "axi_slave_sva.a_valid_stable: started at 1250ns, failed at 1270ns"

Analysis steps:
  1. Note failure time: 1270ns
  2. Find what triggered awvalid at ~1250ns
  3. Check if awready was asserted at 1270ns
  4. If not: DUT dropped awvalid before ready -protocol violation
  5. Waveform probes: awvalid, awready, awaddr, aclk
  6. Trace: which master sequence drove the transaction that failed?
```

#### 3.2 Scoreboard Mismatch

```
# Log pattern:
# "[SB_MISMATCH] READ MISMATCH addr=0x4000_0008 exp=0x0000_00FF got=0x0000_00FE"

Analysis steps:
  1. Identify address: 0x4000_0008
  2. Find last write to this address in the log
  3. Check if write data matches expected (0xFF)
  4. If write was correct: read path issue -check bus, buffer, or read logic
  5. If write was wrong: check write path, byte enables, or memory model
  6. Common cause: PSTRB/WSTRB byte enable mismatch dropped one bit
  7. Waveform probes: paddr, pwdata, prdata, pstrb at transaction time
```

#### 3.3 Phase Hang (UVM Objection)

```
# Log pattern:
# "Simulation running... (last activity at 5000ns, now at 100000ns)"
# No UVM_INFO after test sequence completes

Analysis steps:
  1. Search log for last `drop_objection` call
  2. If never dropped: sequence did not complete -check sequence body for blocking call
  3. Common causes:
     - seq_item_port.get_next_item() blocking -driver never calls item_done()
     - wait(condition) that never becomes true -deadlock in monitor
     - Phase objection raised in build_phase, not dropped
  4. Add `set_drain_time` timeout to detect hung phases
  5. Waveform: check if DUT handshake signals are stuck
```

#### 3.4 X Propagation

```
# Log pattern:
# "WARNING: 4-state value on data_out includes X/Z at time 2000ns"
# Scoreboard comparison returns X

Analysis steps:
  1. Note first occurrence of X in the log
  2. Find X source: uninitialized register, undriven net, or reset not applied
  3. Most common causes:
     - FF without reset: X persists until first write
     - Bus with multiple drivers: contention produces X
     - Tri-state enable not driven: bus floats to Z
     - Glitch on reset: partial reset propagates X
  4. Use simulator X-pessimism reduction carefully -don't mask real Xs
  5. Waveform: trace X backwards from output to source FF or net
```

---

### Step 4 -Waveform Probe Recommendations

For each failure type, recommend the minimum signal set to probe:

```
For assertion failure (AXI handshake):
  Probes: aclk, aresetn, awvalid, awready, awaddr, awlen, awburst

For scoreboard mismatch (APB):
  Probes: pclk, presetn, psel, penable, pwrite, paddr, pwdata, prdata, pstrb, pready

For phase hang:
  Probes: clk + all handshake signals (valid/ready pairs)
  UVM: enable +UVM_PHASE_TRACE and +UVM_OBJECTION_TRACE

For X propagation:
  Probes: all outputs showing X + suspected source signals + reset signals
```

---

### Step 5 -Race Condition Detection

Signs of a race condition:
- Failure only on specific seeds
- Different fail time each run
- Passes with `+define+RACE_FREE` or with slower clock

```
Common race patterns:
  1. Blocking = in clocked always: use <= instead
  2. Fork-join_any with shared variable: use semaphore
  3. @(posedge clk) in task competing with forever loop: use event or mailbox
  4. Driver and monitor both reading vif signals without clock synchronization
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `log_parser.py` | Parses simulation log; extracts all UVM_ERROR/FATAL/WARNING with timestamps and context |
| `failure_classifier.py` | Classifies each failure by type (assertion, scoreboard, timeout, X-prop, race) |
| `probe_recommender.py` | Based on failure type and module, recommends minimum waveform signal set |
| `seed_reproducer.py` | Generates simulator command to re-run with specific seed and captured waveform |

---

## Validation Checklist

- [ ] Failure reproduced deterministically with same seed
- [ ] Root cause identified to specific RTL line or testbench function
- [ ] Waveform captured and annotated at failure point
- [ ] Bug report filed with: failure time, signal values, root cause, RTL location
- [ ] Fix verified by re-running the failing test to pass
- [ ] Regression run to confirm fix did not break other tests
