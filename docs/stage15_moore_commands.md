# Stage 15 Moore/JasperGold Commands

Run these commands from the repository root on Moore. They assume the Cadence
environment is available and JasperGold is invoked through the fixed Moore path
below.

```bash
export JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg
```

These Stage 15 oracle commands do not send external LLM prompts. They evaluate
checked-in benchmark/reference artifacts and committed local fixture metadata;
do not add `--llm` or `--llm-command` to these runs.

## Expanded Native Oracle JasperGold

Runs the native benchmark JasperGold flows for every expanded Design2SVA case.
This maps each fixture to the checked-in benchmark RTL, assumptions, properties,
harness, and `formal/run_jg.tcl` flow.

```bash
export JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg
python3.11 evaluation/run_design2sva_native_oracle.py \
  --native-expanded-jasper \
  --cases benchmarks/design2sva_cases.json \
  --variant correct \
  --out evaluation/results/design2sva_native_oracle_expanded_jasper.json
```

Expected output paths:

- JSON summary: `evaluation/results/design2sva_native_oracle_expanded_jasper.json`
- Native JasperGold report directories:
  `jasper/reports/<design_id>_correct_prove/` and
  `jasper/reports/<design_id>_correct_vacuity/`
- Per-flow raw files under those report directories, including `jg.log`,
  `properties.rpt`, `cover.rpt`, `vacuity.rpt`, and `jgproject/` where emitted
  by JasperGold.

## Expanded Wrapper Reference Oracle JasperGold

Runs the expanded reference-oracle wrapper validation with JasperGold. This uses
the fixture `evaluation_metadata.reference_sva` assertions as the oracle
candidate, runs wrapper proof/cover/diagnostic checks, and also embeds the
native oracle mapping summary in the output.

```bash
export JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg
python3.11 evaluation/run_design2sva_native_oracle.py \
  --cases benchmarks/design2sva_cases.json \
  --expanded-jasper \
  --variant correct \
  --jasper-out-root jasper/reports/design2sva_reference_oracle_expanded_jasper \
  --out evaluation/results/design2sva_reference_oracle_expanded_jasper.json
```

Expected output paths:

- JSON summary: `evaluation/results/design2sva_reference_oracle_expanded_jasper.json`
- Wrapper JasperGold report root:
  `jasper/reports/design2sva_reference_oracle_expanded_jasper/`
- Per-case wrapper report directories:
  `jasper/reports/design2sva_reference_oracle_expanded_jasper/design2sva_c0_r0/<case_id>/`
- Per-case wrapper raw files, including `generated_properties.sv`,
  `generated_harness.sv`, `candidate_sva.json`, `run_command.txt`,
  `properties.rpt`, `cover.rpt`, `vacuity.rpt`, `jg.log`, and
  `embedding_audit/` artifacts when emitted.
- The JSON payload records `llm_prompts_sent: false`.

## Local/Dry-Run Preparation

Use these commands on a non-Moore machine, or on Moore when preparing artifacts
without invoking JasperGold:

```bash
python3.11 evaluation/run_design2sva_native_oracle.py \
  --native-expanded-local \
  --out evaluation/results/design2sva_native_oracle_expanded_local.json

python3.11 evaluation/run_design2sva_native_oracle.py \
  --native-expanded-jasper \
  --dry-run \
  --out evaluation/results/design2sva_native_oracle_expanded_jasper.json

python3.11 evaluation/run_design2sva_native_oracle.py \
  --expanded-local \
  --out evaluation/results/design2sva_reference_oracle_expanded_local.json

python3.11 evaluation/run_design2sva_native_oracle.py \
  --expanded-jasper \
  --dry-run \
  --out evaluation/results/design2sva_reference_oracle_expanded_jasper.json
```

Expected dry-run output paths:

- `evaluation/results/design2sva_native_oracle_expanded_local.json`
- `evaluation/results/design2sva_native_oracle_expanded_jasper.json`
- `evaluation/results/design2sva_reference_oracle_expanded_local.json`
- `evaluation/results/design2sva_reference_oracle_expanded_jasper.json`

## Result Refresh

Refresh markdown result tables after the two JasperGold runs finish. This
command consumes existing JSON result artifacts and actual packet evidence; it
does not send external LLM prompts.

```bash
python3.11 scripts/refresh_eval_results.py \
  --packet-source actual \
  --packet-root jasper/reports/case_packets
```

Expected output paths:

- `evaluation/results/main_results.md`
- `evaluation/results/coverage_closure_results.md`
- `evaluation/results/ablation_results.md`
- `evaluation/results/output_quality_results.md`
- `evaluation/results/design2sva_results.md`

If Moore does not have complete actual evidence packets under
`jasper/reports/case_packets`, this command is expected to stop with the
repository's packet-evidence guard rather than silently rebuilding local
scaffold packets.

## Validation

Run the focused Stage 15 validation checks after refreshing results.

```bash
python3.11 -m pytest \
  tests/test_design2sva_native_oracle.py \
  tests/test_design2sva_reference_oracle_expanded.py \
  tests/test_design2sva_expanded_fixtures.py \
  tests/test_stage5_import_and_refresh.py
```

Expected validation behavior:

- The native oracle tests confirm expanded Design2SVA cases map to checked-in
  benchmark JasperGold flows and that dry-run mode does not invoke JasperGold.
- The expanded reference-oracle tests confirm the expanded payload mode,
  expected artifact path fields, and `llm_prompts_sent: false`.
- The expanded fixture tests confirm Stage 15 fixture fields, valid paths,
  unique case/property pairs, and that reference SVA stays out of prompts.
- The refresh tests confirm Design2SVA JSON artifacts are rendered into
  `evaluation/results/design2sva_results.md`.
