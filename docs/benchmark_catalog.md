# Benchmark Catalog

## Local DV Benchmarks

| Benchmark | Scope | Collateral |
| --- | --- | --- |
| `arbiter_rr2` | Two-client round-robin arbiter | correct RTL, RTL bugs, assumptions, properties, coverage plan, signal-role map, labeled triage/coverage cases |
| `rv_buffer` | Single-entry ready/valid buffer | correct RTL, overwrite/ready bugs, assumptions, properties, coverage plan, labeled cases |
| `apb_regblock` | Small APB-lite register block | correct RTL, address/read/write bugs, assumptions, properties, coverage plan, labeled cases |
| `fifo_1r1w` | Optional one-read/one-write FIFO | correct RTL, reset/overflow/ordering/simultaneous bugs, assumptions, properties, coverage plan, labeled cases |

The original primary set was 30 cases across arbiter, ready/valid buffer, and APB. The expanded optional set adds FIFO and extra assumption/vacuity/assertion cases. Keep result tables explicit about which case roots were evaluated.

## FVEval Subset

`benchmarks/external/fveval_subset/` is reserved for local FVEval-compatible data. If a local FVEval checkout or imported subset is available, use `tools/import_fveval_subset.py` to normalize a bounded subset.

The intended 30-case subset is:

- 10 `NL2SVA-Human`
- 10 `NL2SVA-Machine`
- 10 `Design2SVA`

Do not claim official FVEval reproduction unless the exact dataset, reference flow, and functional-equivalence evaluation are imported and run. Without that flow, report only local proxy metrics such as JSON validity, syntax scaffold status, proof/vacuity where applicable, fallback rate, and hallucinated signal rate.

## Case Provenance

All benchmark cases should carry author/source metadata. Benchmark source RTL, properties, schemas, prompts, manifests, and curated summaries are tracked. Raw reports, traces, and full run logs are local artifacts.
