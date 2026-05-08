# Moore JasperGold Smoke Results

Date: 2026-05-08

Server:

```text
host: moore.wot.ece.northwestern.edu
user: esf2634
env: source /vol/eecs391/cadence.env
jasper: /vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg
python: python3.11
```

## Results

| Design | Variant | Mode | Assertion Result | Expected |
| --- | --- | --- | --- | --- |
| `arbiter_rr2` | `correct` | prove | 12 proven, 0 cex | pass |
| `arbiter_rr2` | `bug_double_grant` | prove | 8 proven, 4 cex | fail |
| `rv_buffer` | `correct` | prove | 9 proven, 0 cex | pass |
| `rv_buffer` | `bug_overwrite` | prove | 8 proven, 1 cex | fail |
| `apb_regblock` | `correct` | prove | 9 proven, 0 cex | pass |
| `apb_regblock` | `bug_wrong_addr` | prove | 5 proven, 4 cex | fail |

## Notes

- The course `cadence.env` is csh/tcsh style. Source it from `tcsh` or an interactive csh-compatible shell.
- The default `python3` on `moore` is too old for this repo; use `python3.11`.
- JasperGold 2018 uses `report -summary -results -detailed -file ... -force`; newer `report -property -all` style flags are not accepted.
- `$initstate` is not supported by this JasperGold frontend, so reset initialization is handled through JasperGold reset commands in each `run_jg.tcl`.
- `tools/run_jasper.py` uses a per-run `-proj` directory under the report directory, so multiple runs do not collide on a shared `jgproject`.

## Evidence Extraction Smoke

The following chain was validated on `arbiter_rr2/bug_double_grant`:

```text
JasperGold properties.rpt
-> JasperGold VCD traces from prove -dump_trace
-> tools/build_evidence_packet.py
-> copilot/schemas/evidence_packet.schema.json
-> copilot/agents/dv_triage_agent.py
```

The resulting scaffold diagnosis classified the case as `rtl_design_bug` with next action `fix_rtl`.

The counterexample summary now prioritizes the focused failing property trace. For `p_mutex`, the generated evidence reports:

```text
falsified_properties:
  p_mutex
  p_both_req_priority_turn0
  p_both_req_priority_turn1
  p_turn_updates_on_contested_grant1

first_trace_property: p_mutex
key event: req0=1, req1=1, gnt0=1, gnt1=1, rst=0
semantic observation: Multiple grant outputs are asserted while multiple requests are active.
```

JasperGold may emit compressed VCD data with either `.vcd` or `.vcd.gz` names. `tools/parse_jg_trace.py` detects gzip content by file magic bytes rather than extension.
