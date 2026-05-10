# local_dv Benchmark Overlay

This directory is a repo-local benchmark registry for the checked-in RTL/SVA DV
cases under `benchmarks/arbiter_rr2`, `benchmarks/rv_buffer`, and
`benchmarks/apb_regblock`.

Split policy:

- `train`: `arbiter_rr2`
- `dev`: `rv_buffer`
- `test`: `apb_regblock`

The split is by design family, so case IDs and design IDs do not overlap across
train/dev/test. The retrieval corpus excludes `cases/*.json` and top-level
`*_cases.json` answer-bearing files by default. Public benchmark sources such as
miniF2F, ProofNet, SMT-LIB, and traced repos are recorded as absent unless a
checked-in source directory is later added.
