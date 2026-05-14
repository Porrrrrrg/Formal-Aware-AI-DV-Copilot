# Design2SVA Stage 12 Wrapper Parity Repair

Stage 11 isolated a wrapper problem before any LLM-generation claim could be
made. Native benchmark reference properties proved in the checked-in formal
flows, while the same fixture `reference_sva` values failed when embedded
through the Design2SVA wrapper. The Stage 11 subset result was:

- Native benchmark reference oracle: `3/3` proven in native flows.
- Design2SVA reference embedding: `0/3` proven through the wrapper.
- Root-cause candidate: `design2sva_embedding_bug=3`.

Stage 12 repairs that isolation failure by making the generated Design2SVA
wrapper match the native benchmark formal environment more closely.

## Repair

The generated checker still writes self-contained artifacts under the requested
report directory, so existing commands remain compatible. The artifact contents
now follow the native harness topology:

- The generated property module uses the native property module name
  (`*_properties`) instead of a parallel `generated_sva_properties` module.
- The generated harness artifact is a copy of the checked-in native harness,
  so DUT, assumptions, property instance name, parameters, and `.*`
  connections match native behavior.
- The Jasper top module, clock, and reset command match the native
  `formal/run_jg.tcl` flow.
- The wrapper audit records native flow metadata, wrapper flow metadata,
  parity checks, `root_cause_candidate`, and `root_cause_detail`.
- Cover checks now run in cover mode (`cover -all`) instead of using the prove
  flow for generated cover properties.

Invariant assertions such as `!(gnt0 && gnt1)` are treated as assertions with
no antecedent obligation. They are evaluated by proof and vacuity status; no
antecedent cover is required or generated. Antecedent covers are only produced
for implication properties with an extracted trigger.

## Local Artifacts

Dry-run wrapper audit smoke:

```bash
python evaluation/run_design2sva_eval.py \
  --reference-oracle \
  --jasper-check \
  --dry-run \
  --out evaluation/results/design2sva_eval_reference_oracle_parity_local.json \
  --markdown evaluation/results/design2sva_eval_reference_oracle_parity_local.md
```

Replay parity fixture validation:

```bash
python evaluation/run_design2sva_eval.py \
  --reference-oracle \
  --jasper-replay evaluation/fixtures/design2sva_reference_oracle_replay.jsonl \
  --native-oracle-results evaluation/results/design2sva_native_reference_oracle_jasper.json \
  --out evaluation/results/design2sva_eval_reference_oracle_parity_jasper.json \
  --markdown evaluation/results/design2sva_eval_reference_oracle_parity_jasper.md
```

The replay fixture path is a local regression check for the wrapper-parity
metrics and is not new JasperGold evidence. It covers all four local
Design2SVA fixtures and reports:

- `reference_proven@1 = 1.000`
- `reference_non_vacuous@1 = 1.000`
- `reference_antecedent_reachable@1 = 1.000`
- `wrapper_parity_pass_rate = 1.000`
- `root_cause_details = reference_oracle_matches_native_formal_behavior=4`

The local dry-run result is not proof evidence. It records wrapper audit
artifacts and confirms stale reports are ignored when `--dry-run` is used.
Per-case audit JSON and markdown files are written under each dry-run report
directory at `embedding_audit/embedding_audit.json` and
`embedding_audit/embedding_audit.md`.

The Moore/JasperGold parity command writes measured evidence to
`evaluation/results/design2sva_eval_reference_oracle_parity_jasper.json`.
That file should be interpreted separately from the local dry-run and replay
fixture paths.

## Claim Boundary

Supported only when proven or replayed from measured evidence:
Design2SVA wrapper embedding can reproduce native reference behavior for the
local reference-oracle fixtures.

Unsupported:
Successful LLM Design2SVA generation. Stage 12 does not generate additional
LLM candidates and does not run external LLM prompts.
