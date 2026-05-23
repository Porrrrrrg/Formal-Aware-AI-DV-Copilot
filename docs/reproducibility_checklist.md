# Reproducibility Checklist

This checklist covers Stage 18 local validation and optional Moore/JasperGold
reruns. The default commands do not send external LLM prompts.

## Python Version Assumptions

- Project metadata requires Python `>=3.10`.
- Moore examples historically use `python3.11`.
- Windows PowerShell local checks can use the active `python` on PATH.

## Local Test Commands

```powershell
python -m pytest -q
```

Expected result: the repository test suite passes without requiring external
LLM calls, network access, Moore, or JasperGold.

## Ruff Command

```powershell
python -m ruff check .
```

Expected result: no lint violations.

## Prompt Audit Command

```powershell
python scripts/export_codex_prompts.py --task design2sva --design2sva-cases benchmarks/design2sva_cases.json --limit 12 --design2sva-context-budget 24 --out-dir evaluation/prompt_previews/design2sva_expanded --audit-markdown evaluation/prompt_previews/design2sva_expanded_prompt_audit.md --require-no-gold-labels
```

Expected result file:

- `evaluation/prompt_previews/design2sva_expanded_prompt_audit.md`

Expected guarantee:

- No `reference_sva` key.
- No exact reference SVA value.
- No `expected_proof_status`.
- No Jasper evidence in prompt previews.
- No gold labels in prompt-visible content.

## Local Replay Commands

Prompt-free Design2SVA replay from checked-in candidates:

```powershell
python evaluation/run_design2sva_eval.py --limit 12 --k 3 --replay evaluation/results/design2sva_eval_codex_expanded_subset.json --out evaluation/results/design2sva_codex_replay_expanded_local.json
```

Prompt-free local oracle dry runs:

```powershell
python evaluation/run_design2sva_native_oracle.py --native-expanded-local --out evaluation/results/design2sva_native_oracle_expanded_local.json
python evaluation/run_design2sva_native_oracle.py --expanded-local --out evaluation/results/design2sva_reference_oracle_expanded_local.json
```

Result refresh from local artifacts:

```powershell
python scripts/refresh_eval_results.py --allow-rebuild-packets
```

## Moore/JasperGold Commands

Run these only on a configured Moore/JasperGold host. They do not send external
LLM prompts, but they do run formal tools.

```bash
source /vol/eecs391/cadence.env
export JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg

python3.11 evaluation/run_design2sva_native_oracle.py \
  --native-expanded-jasper \
  --cases benchmarks/design2sva_cases.json \
  --variant correct \
  --out evaluation/results/design2sva_native_oracle_expanded_jasper.json

python3.11 evaluation/run_design2sva_native_oracle.py \
  --expanded-jasper \
  --cases benchmarks/design2sva_cases.json \
  --variant correct \
  --jasper-out-root jasper/reports/design2sva_reference_oracle_expanded_jasper \
  --out evaluation/results/design2sva_reference_oracle_expanded_jasper.json

python3.11 evaluation/run_design2sva_eval.py \
  --limit 12 \
  --k 3 \
  --replay evaluation/results/design2sva_eval_codex_expanded_subset.json \
  --jasper-check \
  --debug-artifacts \
  --out evaluation/results/design2sva_eval_codex_expanded_jasper.json
```

## Expected Result Files

- `evaluation/results/design2sva_results.md`
- `evaluation/results/design2sva_ablation_results.md`
- `evaluation/results/design2sva_eval_codex_expanded_subset.json`
- `evaluation/results/design2sva_eval_codex_expanded_jasper.json`
- `evaluation/results/design2sva_reference_oracle_expanded_jasper.json`
- `evaluation/results/design2sva_native_oracle_expanded_jasper.json`
- `evaluation/prompt_previews/design2sva_expanded_prompt_audit.md`
- `reports/final/jasperloop_dv_final_research_report.md`
- `reports/final/result_index.md`
- `docs/final_claim_boundary.md`
- `docs/final_demo_script.md`
- `docs/final_presentation_slides_outline.md`

## Artifact Policy

Commit source, docs, schemas, benchmark fixtures, sanitized JSON summaries, and
sanitized markdown reports.

Keep these out of git:

- Raw JasperGold logs and reports: `*.log`, `*.rpt`, `*.jou`.
- Waveforms and traces: `*.vcd`, `*.fsdb`, `*.wlf`, trace directories.
- Generated Jasper work directories and raw `jasper/reports/**` output.
- Local scratch directories under `artifacts/**`.
- Secrets, local model caches, raw LLM logs, and machine-local config.

See [artifact policy](artifact_policy.md).

## No-Gold-In-Prompt Guarantee

The Stage 16 prompt audit is the evidence for the default Design2SVA prompt
set. It reports 12 prompts, no prompt-visible reference SVA, no expected proof
status, no exact reference SVA text, and no Jasper evidence. Any future
external benchmark prompt export must rerun the audit with
`--require-no-gold-labels` before prompts are sent.
