# Stage 14 Final Demo Plan

This plan demonstrates the final JasperLoop-DV research package without sending
external LLM prompts and without claiming a new JasperGold or Moore run. Use it
as a presenter script for a local checkout.

## Demo Goal

Show that JasperLoop-DV is an evidence-centered DV copilot prototype:

- formal evidence is packaged before model reasoning;
- model, replay, fallback, and formal provenance are kept separate;
- workflow artifacts are reviewable by a DV engineer;
- Design2SVA results are interpreted only after wrapper parity and reachability
  are understood.

## Preconditions

- Run from the repository root.
- Use a Python environment where the package dependencies are installed.
- Do not use `--llm`, `--acknowledge-external-send`, or any external backend
  during this demo.
- Treat all replay and dry-run outputs as workflow evidence only.

## Demo Track

| Segment | Time | Action | Evidence to show | Presenter point |
| --- | ---: | --- | --- | --- |
| 1. Problem framing | 1 min | Open `README.md` and `docs/design_doc.md` | Architecture diagram and claim boundary table | The LLM proposes; formal evidence and review bound the claims |
| 2. Evidence packet architecture | 2 min | Show packet schema and expanded evidence report | `copilot/schemas/evidence_packet.schema.json`, `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md` | The central artifact is structured evidence, not prose output |
| 3. Offline repair workflow | 4 min | Run the replay workflow command below | `artifacts/workflow-demo/workflow_manifest.json`, `workflow_report.md` | The workflow emits a candidate, Moore handoff, verifier import, static alignment, manifest, and report without external services |
| 4. Model/result provenance | 2 min | Show consolidated result tables | `reports/final/jasperloop_dv_result_tables.md`, `evaluation/results/design2sva_results.md` | Real LLM, replay, deterministic fallback, and measured formal rows are separated |
| 5. Design2SVA wrapper lesson | 3 min | Walk Stage 10-13 docs and fixed-wrapper results | `docs/design2sva_fixed_wrapper_rerun_stage13.md` | Earlier negative Design2SVA results were not interpretable until native reference and wrapper parity were isolated |
| 6. Closing boundaries | 1 min | Show claim table in `docs/paper_outline.md` | Supported, partial, unsupported, and next evidence rows | The package is a research artifact with explicit evidence gaps |

## Command: Offline Repair Workflow

Clean the previous demo output:

```powershell
Remove-Item -Recurse -Force artifacts/workflow-demo -ErrorAction SilentlyContinue
```

Run the bounded replay workflow:

```powershell
python -m app.cli workflow repair `
  --case examples/workflows/sva_repair_demo/demo_case.json `
  --backend replay `
  --run-intent-alignment `
  --prepare-moore-handoff `
  --out-dir artifacts/workflow-demo `
  --dry-run
```

Expected output shape:

```json
{
  "manifest": ".../artifacts/workflow-demo/workflow_manifest.json",
  "report": ".../artifacts/workflow-demo/workflow_report.md",
  "dry_run": true,
  "blocked": false
}
```

Expected artifacts:

```text
artifacts/workflow-demo/problem_spec_stub.json
artifacts/workflow-demo/repair_candidate.json
artifacts/workflow-demo/candidate_stub.json
artifacts/workflow-demo/moore_handoff_manifest.json
artifacts/workflow-demo/imported_verifier_outcome.json
artifacts/workflow-demo/intent_alignment_result.json
artifacts/workflow-demo/workflow_manifest.json
artifacts/workflow-demo/workflow_report.md
```

Inspect the key manifest boundary:

```powershell
python -c "import json; m=json.load(open('artifacts/workflow-demo/workflow_manifest.json')); print(m['backend'], m['dry_run'], m['external_send_allowed'], m['cloud_fallback_called'])"
```

Expected output:

```text
replay True False False
```

## Presenter Script

Opening:

"This demo is about the evidence contract. JasperLoop-DV does not ask the model
to be the verifier. It packages formal context, constrains the agent output, and
records the exact boundary of each result."

During the replay workflow:

"The candidate is a local replay fixture, so this command is reproducible and
offline. That is useful for demonstrating the artifact chain, but it is not a
model-quality measurement."

During the Moore handoff artifact:

"The handoff manifest records what a Moore-side proof job would consume. This
command does not run Moore or JasperGold."

During intent alignment:

"Intent alignment is a static review aid. It can flag semantic drift, but proof
status and static alignment are separate dimensions."

During Design2SVA:

"The Design2SVA history is the main lesson. The first Jasper subset looked like
a model failure, but reference-oracle checks showed the wrapper itself was not
preserving native formal behavior. After wrapper parity was fixed, prior
committed candidates could be rerun fairly without sending new prompts."

Closing:

"The supported result is an evidence-centered workflow and measured local
subsets. The next research step is broader measured evaluation with the same
provenance discipline."

## Design2SVA Evidence Walkthrough

Use these files rather than rerunning JasperGold during the demo:

| File | What to show |
| --- | --- |
| `docs/design2sva_jasper_subset_error_analysis.md` | Syntax-clean and hallucination-free candidates still produced unreachable formal results before wrapper diagnosis |
| `docs/design2sva_reference_oracle_stage10.md` | Reference-oracle mode made harness reachability visible |
| `docs/design2sva_harness_rootcause_stage11.md` | Native references proved while Design2SVA embedding failed, isolating wrapper behavior |
| `docs/design2sva_wrapper_parity_stage12.md` | Wrapper repair matched native harness topology and restored measured reference parity |
| `docs/design2sva_fixed_wrapper_rerun_stage13.md` | Prior committed Codex candidates proved non-vacuously on the measured three-case fixed-wrapper reruns |
| `evaluation/results/design2sva_results.md` | Provenance table separates local, replay, LLM, and measured Jasper rows |

## Evidence To Quote

- Expanded local-DV packets: 53/53 schema-valid prove-backed evidence packets.
- Codex full benchmark: 57 cases, 71/71 valid JSON, 0 fallback, 0 LLM errors.
- Codex task metrics: 11/18 SVA repair scaffold success, 28/30 triage
  issue/action accuracy, 9/9 coverage gap/action accuracy.
- Restored SVA repair proof: 34/34 syntax pass and 34/34 proven.
- SVA repair ablation proof: 126/126 syntax pass and 126/126 proven across
  seven variants.
- Stage 13 Design2SVA fixed-wrapper rerun: original Codex subset k=3 and
  anti-vacuity subset k=5 both record syntax@k, proven@k, and
  proven_non_vacuous@k as 1.000 on three measured cases.

## What Not To Say

- Do not say replay output is live model performance.
- Do not say dry-run output is formal proof.
- Do not say a JasperGold proof pass proves semantic intent alignment.
- Do not say `not_flagged_vacuous` is an independent explicit non-vacuity
  certificate outside the measured report context.
- Do not say the FVEval-compatible subset is an official FVEval reproduction.
- Do not say the Qwen 3+3+3 subset is a full Qwen benchmark or a Qwen-vs-Codex
  comparison.
- Do not say the three-case Design2SVA fixed-wrapper result generalizes to broad
  Design2SVA success.

## Backup Plan

If the workflow command cannot run in the presentation environment, open the
committed demo documentation instead:

- `docs/demo_script.md`
- `docs/e2e_demo.md`
- `reports/workflows/e2e_demo_summary_20260511T191259Z.md`
- `reports/workflows/e2e_demo_manifest_20260511T191259Z.json`

State clearly that the backup path is a documentation walkthrough, not a new
execution.
