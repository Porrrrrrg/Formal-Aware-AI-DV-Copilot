# Stage 17 Final CLI Demo Script

This is the final CLI-only demo path for the local JasperLoop-DV repository.
It uses checked-in artifacts by default, separates provenance for oracle,
LLM-only, and JasperGold-measured rows, and does not require or describe any web
UI.

## Preconditions

- Run commands from the repository root.
- Use the checked-in artifacts for the default demo. They are sufficient to show
  the final evidence chain without sending new prompts or rerunning JasperGold.
- Only run JasperGold commands on Moore or another host with Cadence/JasperGold
  configured.
- Do not run commands containing `--acknowledge-external-send`, `--llm`, or
  `--llm-command` unless the explicit external-send gate in this document is
  deliberately opened.

## Demo Arc

| Step | CLI action | Evidence to cite | Claim boundary |
| --- | --- | --- | --- |
| 1 | Prove the reference oracle through native and wrapper paths | `evaluation/results/design2sva_native_oracle_expanded_jasper.json`, `evaluation/results/design2sva_reference_oracle_expanded_jasper.json` | Oracle and wrapper validity only; not generated-candidate quality |
| 2 | Show real Codex candidate generation | `evaluation/results/design2sva_eval_codex_expanded_subset.json` | Real LLM generation only; formal metrics intentionally `not_run` |
| 3 | Replay exact Codex candidates through JasperGold | `evaluation/results/design2sva_eval_codex_expanded_jasper.json` | Formal result for this 12-case local benchmark only |
| 4 | Read evidence/result markdown | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md`, `reports/final/jasperloop_dv_result_tables.md`, `evaluation/results/design2sva_results.md` | Markdown summarizes tracked artifacts; raw Jasper logs stay under ignored report trees |
| 5 | Close with claim boundary | `docs/stage16_claim_update.md`, `docs/design2sva_expanded_codex_stage16_error_analysis.md` | No production signoff, broad industrial generalization, or official FVEval reproduction |

## 0. Preflight

```powershell
git status --short
python --version
```

Expected presenter point:

- The demo is CLI-only.
- A dirty worktree should be explained before continuing.
- The default path reads or refreshes artifacts and does not send external LLM
  prompts.

## 1. Reference Oracle: Native And Wrapper Proofs

Default artifact inspection:

```powershell
python -c "import json; p='evaluation/results/design2sva_native_oracle_expanded_jasper.json'; s=json.load(open(p))['summary']; print('native_cases=', s['num_cases'], 'native_proven=', s['native_proof_status_counts'])"
python -c "import json; p='evaluation/results/design2sva_reference_oracle_expanded_jasper.json'; s=json.load(open(p))['summary']; print('wrapper_cases=', s['num_cases'], 'reference_proven@1=', s['reference_proven@1'], 'reference_non_vacuous@1=', s['reference_non_vacuous@1'], 'wrapper_parity=', s['wrapper_parity_pass_rate'], 'llm_prompts_sent=', json.load(open(p))['llm_prompts_sent'])"
```

Expected result:

- Native expanded oracle proves 12/12 references in the native benchmark flow.
- Wrapper expanded oracle proves 12/12 references non-vacuously through the
  repaired Design2SVA wrapper.
- `llm_prompts_sent = False`.

Optional local dry-run preparation, prompt-free:

```powershell
python evaluation/run_design2sva_native_oracle.py --native-expanded-local --out evaluation/results/design2sva_native_oracle_expanded_local.json
python evaluation/run_design2sva_native_oracle.py --expanded-local --out evaluation/results/design2sva_reference_oracle_expanded_local.json
```

Optional Moore/JasperGold rerun, prompt-free:

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
```

Presenter line:

The reference oracle is the gate. Native proof plus wrapper non-vacuous proof
means later candidate failures can be interpreted as candidate or repair
behavior instead of a known harness or wrapper invalidity.

## 2. Real Codex Candidate Generation

First run the prompt audit. This exports local prompt previews and does not send
new external LLM prompts:

```powershell
python scripts/export_codex_prompts.py `
  --task design2sva `
  --design2sva-cases benchmarks/design2sva_cases.json `
  --limit 12 `
  --design2sva-context-budget 24 `
  --out-dir evaluation/prompt_previews/design2sva_expanded `
  --audit-markdown evaluation/prompt_previews/design2sva_expanded_prompt_audit.md `
  --require-no-gold-labels
```

Default artifact inspection:

```powershell
python -c "import json; p='evaluation/results/design2sva_eval_codex_expanded_subset.json'; s=json.load(open(p))['summary']; print('mode=real_llm', 'cases=', s['num_cases'], 'k=', s['k'], 'llm=', s['source_counts']['llm'], 'valid_json=', s['valid_json_rate'], 'fallback=', s['fallback_rate'], 'formal=', s['formal_metrics_status'])"
```

Expected result:

- 12 cases, `k = 3`.
- 36/36 candidates from real Codex outputs.
- `valid_json_rate = 1.0`, `fallback_rate = 0.0`.
- Formal proof fields are not cited from this artifact because
  `formal_metrics_status = not_run`.

External-send gate for a new Codex generation run:

```powershell
if ($env:JASPERLOOP_STAGE17_EXTERNAL_LLM_OK -ne "I_APPROVE_NEW_EXTERNAL_CODEX_PROMPTS") {
  throw "Blocked: set JASPERLOOP_STAGE17_EXTERNAL_LLM_OK=I_APPROVE_NEW_EXTERNAL_CODEX_PROMPTS only after approving a new external Codex prompt send."
}

python scripts/run_codex_llm_eval.py `
  --task design2sva `
  --cases benchmarks/design2sva_cases.json `
  --k 3 `
  --max-repair-rounds 0 `
  --timeout 900 `
  --out evaluation/results/design2sva_eval_codex_expanded_subset.json `
  --prompt-audit evaluation/prompt_previews/design2sva_expanded_prompt_audit.md `
  --acknowledge-external-send
```

Presenter line:

This is the only demo command that can send new external LLM prompts. It is
blocked by default and should not be used for the normal final demo, because the
approved Stage 16 Codex generation artifact is already checked in.

## 3. JasperGold Proof Result For Exact Codex Candidates

Default artifact inspection:

```powershell
python -c "import json; p='evaluation/results/design2sva_eval_codex_expanded_jasper.json'; s=json.load(open(p))['summary']; print('cases=', s['num_cases'], 'k=', s['k'], 'syntax@k=', s['syntax@k'], 'proven@1=', s['proven@1'], 'proven@k=', s['proven@k'], 'non_vacuous@k=', s['non_vacuous@k'], 'proven_non_vacuous@k=', s['proven_non_vacuous@k'], 'valid_json=', s['valid_json_rate'], 'fallback=', s['fallback_rate'])"
```

Expected result:

- `syntax@k = 1.0`
- `proven@1 = 0.75`
- `proven@k = 1.0`
- `non_vacuous@k = 1.0`
- `proven_non_vacuous@k = 1.0`
- `valid_json_rate = 1.0`
- `fallback_rate = 0.0`

Optional Moore/JasperGold rerun, prompt-free because it replays the checked-in
LLM artifact:

```bash
source /vol/eecs391/cadence.env
export JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg

python3.11 evaluation/run_design2sva_eval.py \
  --limit 12 \
  --k 3 \
  --replay evaluation/results/design2sva_eval_codex_expanded_subset.json \
  --jasper-check \
  --debug-artifacts \
  --out evaluation/results/design2sva_eval_codex_expanded_jasper.json
```

Presenter line:

This step proves exact generated candidates, not fresh model outputs. It is the
formal measurement row for the 12-case local benchmark.

## 4. Evidence And Result Markdown

Read the evidence and result tables:

```powershell
Get-Content reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md
Get-Content reports/final/jasperloop_dv_result_tables.md
Get-Content evaluation/results/design2sva_results.md
Get-Content docs/stage16_claim_update.md
```

Optional result refresh from existing artifacts, prompt-free:

```powershell
python scripts/refresh_eval_results.py --allow-rebuild-packets
```

Preferred Moore refresh when actual packet evidence exists, prompt-free:

```bash
python3.11 scripts/refresh_eval_results.py \
  --packet-source actual \
  --packet-root jasper/reports/case_packets
```

Expected presenter point:

- The Jasper evidence markdown shows prove-backed packet evidence separately
  from the Design2SVA Stage 16 candidate benchmark.
- `evaluation/results/design2sva_results.md` keeps reference/native oracle,
  real LLM generation, and JasperGold-measured replay rows separate.
- The raw JasperGold report tree is not tracked; the tracked JSON and markdown
  preserve metrics, proof statuses, candidate provenance, and artifact path
  pointers.

## 5. Claim Boundary

Read the boundary docs:

```powershell
Get-Content docs/stage16_claim_update.md
Get-Content docs/design2sva_expanded_codex_stage16_error_analysis.md
```

Closing script:

The supported claim is narrow and evidence-backed: on the local 12-case
Design2SVA benchmark, after native and wrapper reference-oracle validation,
real Codex generated 36 schema-valid candidates with no fallback, and
JasperGold replay of those exact candidates reached `proven_non_vacuous@k =
1.0` for `k = 3`.

Do not claim production signoff, broad industrial generalization, official
FVEval reproduction, arbitrary-RTL correctness, or that a single Codex sample is
sufficient. The next evidence step is ablation to isolate the contribution of
retrieval context, reachability guidance, wrapper parity, feedback repair, and
candidate sampling.
