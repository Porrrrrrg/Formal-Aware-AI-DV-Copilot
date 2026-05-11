# Stage 3C Benchmark Expansion Summary

Generated: 2026-05-11T03:18:51Z

## Scope

Added a new `fifo_1r1w` benchmark family and expanded assumption/vacuity labels across existing local DV designs without modifying existing case labels.

## New FIFO Assets

- `benchmarks/fifo_1r1w/spec.md`
- `benchmarks/fifo_1r1w/rtl/fifo_1r1w_correct.sv`
- `benchmarks/fifo_1r1w/rtl/fifo_1r1w_bug_overflow.sv`
- `benchmarks/fifo_1r1w/rtl/fifo_1r1w_bug_ordering.sv`
- `benchmarks/fifo_1r1w/rtl/fifo_1r1w_bug_simultaneous_level.sv`
- `benchmarks/fifo_1r1w/rtl/fifo_1r1w_bug_reset_level.sv`
- `benchmarks/fifo_1r1w/rtl/fifo_1r1w_bug_no_simultaneous_ready.sv`
- `benchmarks/fifo_1r1w/formal/fifo_1r1w_harness.sv`
- `benchmarks/fifo_1r1w/formal/fifo_1r1w_properties.sv`
- `benchmarks/fifo_1r1w/formal/fifo_1r1w_assumptions.sv`
- `benchmarks/fifo_1r1w/formal/run_jg.tcl`
- `benchmarks/fifo_1r1w/manifests/assertion_manifest.yaml`
- `benchmarks/fifo_1r1w/manifests/assumption_manifest.yaml`
- `benchmarks/fifo_1r1w/manifests/signal_role_map.yaml`
- `benchmarks/fifo_1r1w/coverage/coverage_plan.yaml`

## Case Counts

- Total local DV labeled cases after expansion: 53
- New FIFO labeled cases: 17
- New labeled cases across existing designs: 6
- Total new labeled cases: 23
- Total coverage-closure cases after expansion: 14
- SVA generation cases after expansion: 33, including 6 new FIFO generation cases
- SVA repair cases after expansion: 23, including 5 new FIFO repair cases
- Combined new SVA generation/repair cases: 11

Issue-type distribution after expansion:

- `rtl_design_bug`: 11
- `assertion_property_bug`: 12
- `assumption_constraint_bug`: 12
- `testbench_stimulus_bug`: 4
- `reachable_coverage_gap`: 9
- `unreachable_or_invalid_coverage_goal`: 5

## Coverage of Requested FIFO Types

- No underflow: `fifo_D6`, `sva_fifo_no_underflow`, `repair_fifo_no_underflow_wrong_guard`
- No overflow: `fifo_D1`, `fifo_D9`, `sva_fifo_no_overflow`
- Ordering: `fifo_D2`, `fifo_D7`
- Simultaneous push/pop: `fifo_D3`, `fifo_D5`, `fifo_D14`, `sva_fifo_simultaneous_full`
- Reset behavior: `fifo_D4`, `fifo_D16`, `sva_fifo_reset_empty`
- Data stability: `sva_fifo_pop_data_stable`, `repair_fifo_pop_data_unknown_signal`
- Liveness/eventual pop: `fifo_D8`, `fifo_D17`, `sva_fifo_eventual_pop`
- Invalid coverage goal: `fifo_D13`

## Existing-Design Vacuity/Assumption Additions

- `arbiter_A11`: overconstraint makes no-spurious-grant checking vacuous.
- `arbiter_A12`: valid reset assumption with an incorrect no-grants property.
- `rv_B11`: overconstraint makes input capture vacuous.
- `rv_B12`: too-strong liveness property for valid consumer behavior.
- `apb_C11`: no-access-phase assumption makes APB write assertions vacuous.
- `apb_C12`: invalid zero-wait-state coverage goal.

## Registry and Tests

Updated the local DV registry generator to include `fifo_1r1w` in the `test` split. Regenerated:

- `benchmarks/local_dv/registry.json`
- `benchmarks/local_dv/splits/train.json`
- `benchmarks/local_dv/splits/dev.json`
- `benchmarks/local_dv/splits/test.json`
- `benchmarks/local_dv/README.md`

Added tests to ensure:

- Expected benchmark label metadata is marked with `label_source: author_expected`.
- Expected reachability/cover fields may exist in case metadata, while observed or
  Jasper-result evidence fields require a `run_manifest` or `evidence_packet` reference.
- Evidence packets do not include `gold_label` by default.
- Every case has `expected_issue_type` and `expected_next_action`.
- Case coverage signals exist in the relevant signal role map.
- Assertion manifest signals exist in the relevant signal role map.
- Top-level SVA generation/repair signal lists exist in the relevant signal role map.

## Validation

- JSON validation for all benchmark case files and top-level SVA case files: pass.
- YAML load validation for manifests and coverage plans: pass.
- Evidence packet build for all 53 cases: pass, with `num_with_reports=0` and
  `num_with_trace_dirs=0`.
- `python -m pytest -q`: 258 passed.
- `python -m ruff check .`: pass.

## Evidence Boundary

- Evidence type: benchmark metadata only, no live Jasper evidence.
- No Moore or JasperGold run was executed for this benchmark expansion.
- Evidence packets were locally built from checked-in benchmark metadata; all packet-build
  rows reported `report_found=false` / `report_found=0` and `trace_dir_found=false`.
- Live Jasper/Moore validation is future work and is not claimed by this report.

## Limitations

No Codex, Qwen, full benchmark, JasperGold, or Moore runs were executed. The expected
coverage and reachability fields are author-provided benchmark labels, not observed
tool results.
