# Stage 4B Expanded Benchmark Jasper Evidence

Created UTC: `20260511T064639Z`

## Scope

This report records live Moore/JasperGold evidence packet generation for the current local-DV benchmark after the Stage 3 checkpoint. It upgrades the Stage 3 FIFO/vacuity expansion from metadata-only to packet-level Jasper evidence validation for all current cases.

Raw Jasper logs, traces, `jgproject` directories, and generated case packets remain local-only and are not committed. Expected benchmark metadata remains separate from observed evidence: `expected_*` and author labels describe intended case metadata; observed evidence here means generated Jasper prove reports/traces referenced by schema-valid evidence packets.

## Run Metadata

- Branch: `stage/expanded-benchmark-moore-evidence`
- Git SHA: `b9acdb4b768845780b777813714a89bc1b5b2353`
- Stage 3 checkpoint tag: `stage3-checkpoint-a13eeec`
- Moore host: `moore.wot.ece.northwestern.edu`
- JasperGold binary: `/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg`
- JasperGold version: `2018.09p002 64 bits`
- Moore Python version: `3.11.13`

## Case Counts

- Total current benchmark cases attempted: 53
- Stage 2 old Jasper-evidence baseline cases: 30
- Current existing-design cases: 36
- New FIFO cases: 17
- New existing-design assumption/vacuity cases: 6

| Design | Cases |
| --- | ---: |
| `apb_regblock` | 12 |
| `arbiter_rr2` | 12 |
| `fifo_1r1w` | 17 |
| `rv_buffer` | 12 |

## Jasper Run Results

- Prove runs attempted: 15
- Prove runs succeeded: 15
- Prove runs failed: 0
- Auxiliary cover runs attempted: 4
- Auxiliary cover runs succeeded: 0
- Auxiliary cover runs failed: 4
- Auxiliary vacuity runs attempted: 4
- Auxiliary vacuity runs succeeded: 0
- Auxiliary vacuity runs failed: 4

The evidence packets for this PR are built from successful prove reports. Auxiliary cover/vacuity mode attempts are recorded separately because the current Jasper 2018.09 command path rejects `cover -all` and does not expose `check_vacuity` in the benchmark TCL scripts.

## Evidence Packet Validation

- Evidence packets generated: 53
- `report_found` count: 53
- `trace_dir_found` count: 53
- Trace file references in packets: 610
- Schema-valid packets: 53
- Schema-invalid packets: 0

## Failures / Blockers

| Blocker | Count | Meaning |
| --- | ---: | --- |
| `cover -all` unsupported by Jasper 2018.09 command path | 4 | Auxiliary cover reports were not generated. |
| `check_vacuity` command unavailable in current TCL command set | 4 | Auxiliary explicit vacuity reports were not generated. |

## Claim Boundary

- This PR does not commit raw Jasper logs, traces, generated harness dumps, `jgproject` directories, license output, or generated case packets.
- This PR does not rerun Codex or Qwen and makes no LLM quality claim.
- Expected metadata remains author-provided benchmark labels. It is not treated as observed Jasper evidence.
- Cover/vacuity auxiliary-mode failures are runner/tool compatibility blockers. They do not invalidate the 53 schema-valid prove-backed evidence packets, but they do mean this PR is not an explicit cover/vacuity certificate.
