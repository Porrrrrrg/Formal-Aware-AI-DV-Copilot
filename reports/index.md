# Reports Index

This index makes report families discoverable without moving or deleting
evidence. It classifies current and historical material; it does not revise the
contents of existing reports.

| Report family | Status | Claim boundary | Notes |
| --- | --- | --- | --- |
| `reports/release/stage3_*` | historical | Stage 3 checkpoint, result ledger, and artifact inventory. | Preserve as release evidence. |
| `reports/release/stage4_*` | current | Stage 4 checkpoint, result ledger, and artifact inventory. | Preserve as release evidence for Stage 5 follow-up context. |
| `reports/status/stage5_gate_status_*` | current | Stage 5 gate closeout/status context. | Latest gate status on `origin/main` as of this cleanup branch. |
| `reports/status/repo_hygiene_audit_*` | current | Static repo hygiene audit inputs for this cleanup implementation. | Source for this PR. |
| `reports/status/repo_cleanup_plan_*` | current | Proposed cleanup sequencing and non-actions. | Source for this PR. |
| `reports/status/stage3_*` | historical | Historical Stage 3 gate reports. | Keep for audit trail; old branch/worktree references are historical. |
| `reports/status/stage4_*` | historical | Historical Stage 4 gate reports and second-wave status. | Keep for audit trail; do not treat as current operational instructions. |
| `reports/status/integration_*` | historical | Integration planning and gate status from earlier branches. | Preserve unless a future owner-approved archive move supersedes it. |
| `reports/status/real_jasper_evidence_blocker_*` | historical | Historical blocker context. | Preserve as claim-boundary evidence. |
| `reports/audits/*` | archive-candidate | Baseline repo, dependency, tree, and security audits. | Future move only after owner approval. |
| `reports/review/*` | archive-candidate | Pre-integration review snapshots. | Useful history but stale for current operations. |
| `reports/research/*.md` | historical | Research summaries, deltas, plans, and risk registers. | Preserve as research evidence. |
| `reports/research/runs/**` | archive-candidate | Generated research run payloads and stdout/stderr captures. | Do not delete; externalize only after durable indexing. |
| `reports/eval/local_dv/run_*/**` | archive-candidate | Generated local-DV evaluation snapshot. | Do not delete; compare against canonical benchmark assets before any future move. |
| `reports/jasper/*summary*.md` | current | Sanitized Jasper proof, generation, repair, and evidence summaries. | Preserve; raw Jasper outputs remain ignored. |
| `reports/jasper/*manifest*.json` | current | Sanitized Jasper manifests and final-proof records. | Preserve; raw logs/traces are not committed. |
| `reports/workflows/*` | current | Workflow smoke and end-to-end demo evidence. | Preserve as workflow evidence. |
| `reports/alignment/*summary*.md` | current | Intent-alignment smoke summary. | Preserve. |
| `reports/alignment/*manifest*.json` | current | Intent-alignment smoke manifest. | Preserve. |
| `reports/alignment/*.jsonl` | archive-candidate | Generated intent-alignment result stream. | Preserve until indexed/externalized by an owner-approved follow-up. |
| `reports/fveval/*` | current | FVEval subset import/evaluation summaries and manifests. | Preserve as benchmark/eval evidence. |
| `reports/benchmarks/*` | current | Benchmark expansion and FVEval subset import summaries. | Preserve. |
| `reports/repair/*summary*.md` | current | SVA repair and CEX-aware repair summaries. | Preserve. |
| `reports/repair/*manifest*.json` | current | Repair run manifests. | Preserve. |
| `reports/repair/*error_cases*.md` | historical | Repair error-case analysis. | Preserve as evidence. |
| `reports/local_llm/*` | owned-elsewhere | Qwen/local-LLM bring-up, readiness, and health evidence. | Do not edit in repo hygiene cleanup; owned by Qwen/local-LLM follow-up. |
| `reports/llm/*` | historical | Codex/LLM evaluation summaries, manifests, and error cases. | Preserve; raw local LLM logs remain ignored. |

## Index Rules

- Add a row when a new report family is committed.
- Prefer summaries and manifests over raw generated output.
- Mark stale coordination reports as `historical` instead of deleting them.
- Mark generated payload groups as `archive-candidate` before any future move.
- Keep Qwen/local-LLM report files under their owning workflow.
