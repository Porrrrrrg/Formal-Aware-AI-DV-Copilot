# Stage 5.5 To Stage 6 Entry Plan

Created UTC: `20260511T224417Z`

Base commit: `775e0a0aeee67c729d10bf19d8af5ef94127d96a`

## Decision

Stage 5.5 is ready to freeze as the skill-assimilated JasperLoop baseline.
Stage 6 should begin only after this checkpoint is merged and tagged as
`stage55-checkpoint-775e0a0`.

Stage 6 is a documentation, packaging, and public-facing presentation phase.
It should not re-open Stage 4 evidence, re-run benchmarks, or make new model,
Qwen, JasperGold, or Moore calls.

## What Stage 5.5 Added

Stage 5.5 integrated sanitized DV engineer skills into the project at three
levels:

1. Project-level skills in `.claude/skills/` with normalized `SKILL.md`
   frontmatter and index documentation.
2. Model-agnostic JasperLoop playbooks and YAML rule libraries under
   `copilot/playbooks/` and `copilot/rules/`.
3. Prompt and workflow dry-run guidance that references playbook sections
   without making external calls or changing benchmark labels.

The sequence was closed by a skill integration gate and risk register.

## Stage 6 Entry Conditions

| Condition | Status |
| --- | --- |
| Stage 3 checkpoint tag exists | Met: `stage3-checkpoint-a13eeec` |
| Stage 4 checkpoint tag exists | Met: `stage4-checkpoint-581102f` |
| Stage 5 pre-skills checkpoint tag exists | Met: `stage5-pre-skills-checkpoint-6e77134` |
| Stage 5.5 skill import completed | Met |
| Playbooks/rules extracted | Met |
| Prompt/workflow guidance integrated | Met |
| Skill integration gate completed | Met |
| Tests and ruff pass | Met: 335 tests passed, ruff passed |
| Open PR queue clear before Stage 6 | To verify after checkpoint merge |

## Recommended Stage 6 PR Sequence

### Stage 6A: Final Report And Result Tables

Outputs:

- `reports/final/jasperloop_dv_final_report.md`
- `reports/final/jasperloop_dv_result_tables.md`

Scope:

- Use existing reports only.
- Consolidate deterministic scaffold results, JasperGold evidence, Codex
  benchmark results, SVA repair proof validation, repair ablation proof,
  expanded benchmark evidence, FVEval-compatible subset, Qwen local subset,
  replay demo, and skill assimilation.
- Include source report filenames for every result table.

Do not:

- Invent new numbers.
- Run new experiments.
- Treat FVEval-compatible subset as official FVEval reproduction.
- Treat Qwen 3+3+3 as a full Qwen benchmark.

### Stage 6B: Demo Script

Output:

- `docs/demo_script.md`

Scope:

- Provide a 3-minute demo, 8-minute demo, and full technical walkthrough.
- Use replay/sample artifacts only.
- Explain what the demo proves and what it does not prove.
- Include commands and expected artifacts for the existing workflow demo.

Do not:

- Require Codex, Qwen, JasperGold, Moore, or network access.
- Describe replay as real model performance.

### Stage 6C: README Rewrite

Output:

- `README.md`

Scope:

- Present JasperLoop-DV clearly for a public repository.
- Explain the core principle: LLMs are assistants; JasperGold is the formal
  oracle.
- Link to the final report and demo script.
- Include architecture, implemented capabilities, key results, quickstart,
  repository map, stage history, and claim boundaries.

Do not:

- Claim production readiness.
- Claim signoff automation.
- Claim Qwen-vs-Codex comparison.
- Claim official FVEval reproduction.
- Describe best-of-k as single-output success.

### Stage 6D: Final Documentation Checkpoint

Output:

- `reports/release/stage6_final_documentation_checkpoint_<UTC>.md`

Recommended tag:

- `stage6-docs-final-<shortsha>`

Scope:

- Verify Stage 6 docs are merged, links are stable, and claim boundaries remain
  explicit.

## Stage 6 Claim Boundary

Stage 6 should preserve these statements:

- JasperLoop-DV is a research prototype, not production signoff automation.
- JasperGold is the formal oracle; LLMs propose, summarize, repair, and
  organize evidence.
- Proof pass does not imply intent alignment.
- `not_flagged_vacuous` is not an independent explicit non-vacuity certificate.
- Best-of-candidates pass@k is an upper-bound search result, not single-output
  repair success.
- Qwen 3+3+3 is local-only subset evidence, not a full Qwen benchmark.
- Qwen-vs-Codex comparison is unsupported without manifest parity.
- FVEval-compatible subset is not official FVEval reproduction.
- Skill-derived playbooks are guidance assets, not standalone research claims.

## CodeQL Follow-Up

CodeQL currently runs analysis with `upload: never` because GitHub code scanning
is not enabled for this repository. This is acceptable for the checkpoint and
keeps CI green. After repository code scanning is enabled, remove `upload:
never` from the CodeQL analyze step so SARIF upload is restored.
