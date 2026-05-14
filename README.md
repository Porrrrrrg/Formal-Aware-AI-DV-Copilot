# JasperLoop-DV

JasperLoop-DV is a JasperGold-in-the-loop AI design-verification copilot prototype for SVA generation, SVA repair, failure triage, and coverage-closure recommendations.

**Core principle:** the LLM is not the verification oracle. JasperGold is the formal oracle for syntax, proof, counterexamples, cover reachability, and vacuity when those checks are actually run. LLM outputs are candidate explanations, repairs, rankings, and next actions for DV engineer review.

## Why This Matters

Modern DV work is evidence-heavy: engineers move between RTL, specs, assertions, assumptions, counterexamples, coverage goals, tool logs, and review checklists. LLMs can help summarize and propose fixes, but fluent text and plausible SVA are not proof. JasperLoop-DV keeps the formal tool in the loop by packaging verifier evidence into structured artifacts before asking an LLM or workflow layer to act.

The project is aimed at a practical research question: how can an AI assistant help a DV engineer decide whether a problem belongs in RTL, an assertion, an assumption, stimulus, or a coverage plan, while keeping correctness claims tied to formal evidence and human review?

## Architecture

```text
RTL + spec + SVA + assumptions + coverage goals
        |
        v
JasperGold runner on Moore or another configured environment
        |
        v
Parsers and formal evidence extractors
        |
        v
Schema-validated evidence packets
        |
        +--> SVA generation agent
        +--> SVA repair agent
        +--> DV failure triage agent
        +--> Coverage closure agent
        |
        v
Workflow CLI, replay/local/model backends, handoff manifests
        |
        v
JasperGold re-check where configured, static intent review, and DV engineer review
```

The evidence packet is the central boundary. It records design identity, task type, property or coverage intent, assumptions, JasperGold proof or counterexample context, role-aware signal summaries, and allowed issue/action labels. The model layer consumes this evidence; it does not replace the verifier.

## Agentic Refactor

The current architecture now separates formal-tool evidence, retrieval context,
agent prompts, and evaluation reporting:

- `app/models/agent.py` defines typed `Task`, `EvidencePacket`,
  `BackendResult`, `RepairAttempt`, `AgentRunManifest`, and
  `EvaluationResult` companions for the committed JSON schemas.
- `copilot/backends` defines the pluggable backend boundary; JasperGold is the
  first-class backend facade.
- `copilot/retrieval` adds lightweight RTL indexing for module interfaces,
  assigns, always blocks, hierarchy, signal logic, and clock/reset candidates.
- Evaluation outputs report `source_counts`, fallback/error rates,
  hallucinated-signal rates, and `output_family_counts` so deterministic
  scaffold rows stay separate from real LLM rows.

See [docs/architecture_agentic_refactor.md](docs/architecture_agentic_refactor.md).

## Implemented Capabilities

- Local DV benchmark structure for `apb_regblock`, `arbiter_rr2`, `fifo_1r1w`, and `rv_buffer`.
- JasperGold runner scripts, TCL flows, report parsers, trace summarization, and evidence-packet builders.
- Strict JSON schemas for evidence packets, repair candidates, diagnosis outputs, coverage outputs, and SVA generation outputs.
- Agent modes for SVA generation, SVA repair, failure triage, and coverage closure.
- Unified CLI and workflow wrapper with dry-run defaults, manifest outputs, and explicit external-call boundaries.
- Moore/JasperGold handoff preparation and sanitized verifier-outcome import.
- Offline replay demo for the repair workflow.
- Static/offline intent-alignment evaluator for SVA review support.
- Local Qwen endpoint plumbing for a bounded 3+3+3 workflow subset.
- FVEval-compatible local subset runner, kept separate from official FVEval reproduction claims.
- DV playbooks and YAML rule libraries for repair, counterexample debugging, assumptions/vacuity, triage, and coverage closure guidance.

## Key Results

These results are copied from the committed Stage 6A reports and retain their original boundaries.

| Evidence area | Recorded result | Boundary |
| --- | --- | --- |
| Expanded local-DV evidence | 53/53 schema-valid prove-backed evidence packets | Packet-level Jasper/Moore evidence for the local benchmark; expected labels are author-provided metadata |
| Codex full benchmark | 57 cases, 71/71 valid JSON, 0 fallback, 0 LLM errors | 11/18 SVA repair scaffold success, 28/30 triage issue/action accuracy, 9/9 coverage gap/action accuracy; not production readiness |
| Restored Codex repair final proof | 34/34 syntax pass and 34/34 proven on Moore/JasperGold | Proof is scoped to checked candidates, harnesses, and assumptions; proof pass does not imply intent alignment |
| SVA repair ablation handoff | 126/126 syntax pass and 126/126 proven across seven variants | Handoff artifact proof only; `not_flagged_vacuous` is not an independent explicit non-vacuity certificate |
| FVEval-compatible subset | 30/30 local subset cases completed with deterministic fallback and no answer leakage | Not an official FVEval reproduction; no JasperGold, Codex, Qwen, or commercial equivalence flow |
| Local Qwen 3+3+3 subset | 9 workflow cases completed through local vLLM with valid JSON, no fallback, and no cloud fallback | Readiness evidence only; not a full Qwen benchmark and not a Qwen-vs-Codex comparison |
| Replay workflow demo | Local repair workflow emits problem, candidate, handoff, verifier import, intent alignment, manifest, and report artifacts | Offline replay evidence only; not live model performance and not a new JasperGold run |

For the full tables, see [reports/final/jasperloop_dv_result_tables.md](reports/final/jasperloop_dv_result_tables.md).

## Quickstart

```bash
git clone https://github.com/Porrrrrrg/Formal-Aware-AI-DV-Copilot.git
cd Formal-Aware-AI-DV-Copilot
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Inspect the workflow CLI:

```bash
python -m app.cli workflow --help
python -m app.cli workflow repair --dry-run --out-dir artifacts/workflow-smoke
```

Dry-run workflow commands write local manifests and reports. They do not call Codex, Qwen, JasperGold, Moore, network services, or cloud models.

Local evaluation refresh:

```bash
python scripts/build_all_evidence_packets.py
python evaluation/run_agent_eval.py --all-systems --out evaluation/results/agent_eval_all_local.json
python evaluation/run_sva_eval.py --out evaluation/results/sva_eval_local.json
python evaluation/run_sva_repair_eval.py --out evaluation/results/sva_repair_local.json
python evaluation/run_coverage_eval.py --all-systems --out evaluation/results/coverage_eval_local.json
python scripts/refresh_eval_results.py
python scripts/run_codex_llm_eval.py --task healthcheck
```

Prompt audit before any external benchmark submission:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
python scripts/export_codex_prompts.py --task triage --limit 2 --redact-evidence --summary-only
```

Do not run benchmark tasks with `--acknowledge-external-send` unless the
benchmark content export has been explicitly approved.

## Demo Command

Run the offline replay demo from the repository root:

```bash
python -m app.cli workflow repair --case examples/workflows/sva_repair_demo/demo_case.json --backend replay --run-intent-alignment --prepare-moore-handoff --out-dir artifacts/workflow-demo --dry-run
```

This demo uses committed fixture files under `examples/workflows/sva_repair_demo/` and writes local artifacts under `artifacts/workflow-demo/`. It is designed to demonstrate the workflow contract and artifact boundaries without live model calls, JasperGold, Moore, network access, or cloud fallback. See [docs/demo_script.md](docs/demo_script.md) for the 3-minute and 8-minute presenter scripts.

## Repository Structure

```text
app/                 CLI, workflow orchestration, local backend, intent alignment
copilot/             agents, prompts, schemas, playbooks, rules, LLM adapters
tools/               Jasper runners, parsers, trace summaries, evidence builders
jasper/              common JasperGold TCL flows and tracked sanitized report anchor
benchmarks/          local DV designs, cases, formal harnesses, manifests, coverage plans
evaluation/          benchmark runners, metrics, result-table refresh helpers
examples/            replay workflow fixture used by the demo
docs/                workflow docs, demo script, artifact policy, design notes
reports/final/       final Stage 6A report and consolidated result tables
reports/release/     stage checkpoints, release ledgers, artifact inventories
reports/*/           sanitized supporting evidence summaries and manifests
scripts/             convenience scripts for demos, evaluation, Moore handoff, cleanup
schemas/             canonical typed-IR schema definitions
tests/               unit, workflow, schema, hygiene, and integration tests
```

Raw JasperGold logs, generated trace trees, local scratch artifacts, and license/tool output are intentionally kept out of git. See [docs/artifact_policy.md](docs/artifact_policy.md).

## Stage History

| Stage | What changed | Boundary |
| --- | --- | --- |
| Stage 2 | Initial Moore/JasperGold evidence packets, Codex benchmark infrastructure, schema hardening, Qwen readiness checks | Early evidence and readiness reports, not production readiness |
| Stage 3 | Baseline release ledger, restored Codex repair outputs, final proof handoff, benchmark expansion metadata, FVEval-compatible import | Best-of-k and external subset boundaries preserved |
| Stage 4 | Expanded 53-case prove-backed evidence, FVEval-compatible local subset evaluation, SVA repair ablation, ablation final proof | Auxiliary cover/vacuity modes were blocked under the available Jasper 2018.09 command path |
| Stage 5 | Unified CLI/workflow, Moore handoff, replay demo, static intent alignment, local Qwen backend, repo hygiene | Workflow and demo evidence are integration evidence, not new benchmark proof |
| Stage 5.5 | Sanitized DV skill import, playbooks, rules, prompt/workflow guidance | Guidance assets only, not correctness evidence |
| Stage 6A | Final report and consolidated result tables | Documentation packaging from committed evidence only |
| Stage 6B | Replay demo script | Demo guidance only; no new model or JasperGold run |
| Stage 6C | Public README rewrite | This entry point summarizes existing claims without changing evidence |

Primary ledgers are under `reports/release/`. The Stage 6 final report is [reports/final/jasperloop_dv_final_report.md](reports/final/jasperloop_dv_final_report.md).

## Claim Boundaries

- JasperLoop-DV is a research prototype and workflow scaffold, not production-ready signoff automation.
- JasperGold is the formal oracle where JasperGold checks are run; LLMs propose, repair, summarize, and triage for review.
- A JasperGold proof pass is scoped to the checked harness, assumptions, and property. It does not prove semantic intent alignment.
- `not_flagged_vacuous` and similar manifest fields are not independent explicit non-vacuity certificates when explicit vacuity status is unavailable.
- Best-of-k is an upper-bound search result over available candidates, not single-output repair success.
- The FVEval-compatible subset is not an official FVEval reproduction and does not reproduce commercial equivalence evaluation.
- The Qwen 3+3+3 subset is local-only readiness evidence, not a full Qwen benchmark and not a Qwen-vs-Codex comparison.
- Replay and dry-run workflow artifacts are not real model performance and not new JasperGold/Moore results.
- Benchmark expected labels are authored metadata, not automatically discovered truth.

## Reference Links

- [Final report](reports/final/jasperloop_dv_final_report.md)
- [Result tables](reports/final/jasperloop_dv_result_tables.md)
- [Demo script](docs/demo_script.md)
- [Workflow usage](docs/workflow_usage.md)
- [Artifact policy](docs/artifact_policy.md)
