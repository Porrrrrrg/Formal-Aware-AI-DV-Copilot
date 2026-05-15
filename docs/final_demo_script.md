# Final CLI Demo Script

This demo is CLI-only and uses checked-in artifacts by default. The quick path
does not send external LLM prompts and does not require JasperGold or Moore.
Optional Moore/JasperGold commands are listed separately.

## Preconditions

- Run from the repository root.
- Use Python 3.10 or newer.
- Keep default commands local and prompt-free.
- Do not run commands with `--acknowledge-external-send`, `--llm`, or
  `--llm-command` during the quick demo.

## 0. Preflight

```powershell
git status --short
python --version
```

Expected point: the demo starts from a known worktree and uses committed
artifacts.

## 1. Show The Result Table

```powershell
Get-Content evaluation/results/design2sva_results.md
Get-Content evaluation/results/design2sva_ablation_results.md
```

Presenter line:

The Stage 16 row is the strongest measured result: local 12-case Design2SVA,
real Codex candidates, JasperGold replay, `proven@1 = 0.75`,
`proven@k = 1.0`, `non_vacuous@k = 1.0`, and
`proven_non_vacuous@k = 1.0`.

## 2. Show Prompt Audit

This command regenerates the prompt audit locally. It exports prompt previews
and checks that gold labels and reference answers are absent. It does not call
an external LLM.

```powershell
python scripts/export_codex_prompts.py --task design2sva --design2sva-cases benchmarks/design2sva_cases.json --limit 12 --design2sva-context-budget 24 --out-dir evaluation/prompt_previews/design2sva_expanded --audit-markdown evaluation/prompt_previews/design2sva_expanded_prompt_audit.md --require-no-gold-labels
Get-Content evaluation/prompt_previews/design2sva_expanded_prompt_audit.md
```

Expected point: the audit reports 12 prompts, no `reference_sva`, no
`expected_proof_status`, no exact reference SVA text, and no Jasper evidence in
the prompts.

## 3. Run Local Design2SVA Replay/Reference Command

This local replay command replays the checked-in Codex artifact without
JasperGold. It is useful for a quick reproducibility smoke but is not a new
formal result.

```powershell
python evaluation/run_design2sva_eval.py --limit 12 --k 3 --replay evaluation/results/design2sva_eval_codex_expanded_subset.json --out evaluation/results/design2sva_codex_replay_expanded_local.json
```

Optional local reference-oracle dry run, also prompt-free and Jasper-free:

```powershell
python evaluation/run_design2sva_native_oracle.py --native-expanded-local --out evaluation/results/design2sva_native_oracle_expanded_local.json
python evaluation/run_design2sva_native_oracle.py --expanded-local --out evaluation/results/design2sva_reference_oracle_expanded_local.json
```

Presenter line:

These commands refresh local scaffold/replay artifacts only. Formal metrics
remain `not_run` unless JasperGold is explicitly enabled.

## 4. Show JasperGold-Measured Artifact

Inspect the committed JasperGold-measured replay artifact:

```powershell
python -c "import json; p='evaluation/results/design2sva_eval_codex_expanded_jasper.json'; s=json.load(open(p))['summary']; print('cases=', s['num_cases'], 'k=', s['k'], 'syntax@k=', s['syntax@k'], 'proven@1=', s['proven@1'], 'proven@k=', s['proven@k'], 'non_vacuous@k=', s['non_vacuous@k'], 'proven_non_vacuous@k=', s['proven_non_vacuous@k'], 'valid_json=', s['valid_json_rate'], 'fallback=', s['fallback_rate'], 'formal=', s['formal_metrics_status'])"
```

Expected output values:

- `cases = 12`
- `k = 3`
- `syntax@k = 1.0`
- `proven@1 = 0.75`
- `proven@k = 1.0`
- `non_vacuous@k = 1.0`
- `proven_non_vacuous@k = 1.0`
- `valid_json = 1.0`
- `fallback = 0.0`
- `formal = replayed`

## 5. Show Claim Boundary

```powershell
Get-Content docs/final_claim_boundary.md
Get-Content reports/final/result_index.md
```

Closing line:

The supported claim is narrow: on the local 12-case Design2SVA benchmark, after
native and wrapper oracle validation, JasperGold replay of exact real Codex
candidates reached `proven_non_vacuous@k = 1.0` for `k = 3`. Do not claim
production signoff, arbitrary RTL generalization, or official FVEval
reproduction.

## Optional Moore/JasperGold Commands

Only run these on Moore or another configured host with Cadence/JasperGold
available. They are prompt-free but not part of the local quick demo.

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

Moore/JasperGold outputs must follow [artifact policy](artifact_policy.md).
Raw logs, waveforms, trace directories, generated harness dumps, and license
output stay out of git.
