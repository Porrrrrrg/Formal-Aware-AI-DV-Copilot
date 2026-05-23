# Stage 5 to Stage 5.5 Skill Assimilation Plan

Created UTC: `20260511T205601Z`

Base commit: `a63af615567e3ebaaaba79e8f2ed90dcd5b577eb`

## Decision

Stage 6 is intentionally deferred.

The next phase is Stage 5.5: DV Engineer Skill Assimilation and Workflow
Refinement. This checkpoint is a system baseline before external Claude Skills
from real DV workflows are reviewed and incorporated.

## Rationale

Stage 5 now has a coherent system shell:

- CLI and workflow orchestration.
- Moore handoff automation.
- Verifier-result import path.
- Static intent-alignment evaluator.
- End-to-end replay demo.
- LOCAL_ONLY local Qwen backend with a successful 3+3+3 subset.
- Repo hygiene infrastructure and artifact policy.

However, external DV-engineer Claude Skills may change the way JasperLoop
should handle repair prompts, counterexample debugging, assumption and vacuity
diagnosis, coverage closure, formal review checklists, triage taxonomy, and
agent operating procedure. Entering Stage 6 now would freeze too early.

## Stage 5.5 Step 1: Skills Reading / Taxonomy

Classify incoming Claude Skills into these groups:

1. SVA writing / repair skills.
2. JasperGold debug skills.
3. Counterexample analysis skills.
4. Assumption / constraint debugging skills.
5. Vacuity diagnosis skills.
6. Coverage closure skills.
7. Formal signoff / review checklist skills.
8. DV engineer workflow / triage skills.
9. Prompt / agent operation skills.

Expected outputs:

- `reports/skills/dv_skill_taxonomy_<UTC>.md`
- `reports/skills/dv_skill_to_jasperloop_mapping_<UTC>.md`

## Stage 5.5 Step 2: Map Skills To JasperLoop

Map each skill to the existing system before implementation:

| Skill type | Candidate JasperLoop targets |
| --- | --- |
| CEX debug checklist | `copilot/prompts/`, SVA repair prompts, triage reports, `app/alignment/` |
| Vacuity diagnosis | evidence packet fields, intent-alignment `vacuity_risk_flags`, coverage workflow reports |
| Assumption debugging | evidence packet schema, triage taxonomy, workflow report sections |
| Coverage closure procedure | coverage closure prompt, workflow coverage command, report format |
| Formal review checklist | docs, workflow final report, gate reports |
| Agent operating procedure | CLI defaults, external-send gates, local-only gates, Moore handoff docs |

The mapping phase should not modify code. It should identify high-value
refinements, risks, and conflicts with existing evidence boundaries.

## Stage 5.5 Step 3: Scoped Refinement PRs

Only after taxonomy and mapping are reviewed, open scoped implementation PRs:

1. Prompt refinement.
2. Repair workflow refinement.
3. Triage checklist refinement.
4. Coverage closure refinement.
5. Documentation / workflow guide refinement.
6. Evaluation update.

Do not combine all refinements into one large PR. Each PR must state the skill
source, mapped JasperLoop module, expected behavior change, tests, and claim
boundary.

## Gate Rules

- No production-readiness claim.
- No final-paper claim.
- No Qwen-vs-Codex comparison unless matched manifests exist.
- No full Qwen benchmark without a separate gate.
- No replay-demo-as-model-performance claim.
- No proof-pass-as-intent-alignment claim.
- No `not_flagged_vacuous` as explicit non-vacuity certification.
- No signoff automation claim.

## Recommended Agents After Skills Are Provided

Start with three read-only or report-only agents:

| Agent | Role | Output |
| --- | --- | --- |
| Skill Taxonomy Agent | Categorize all Claude Skills by DV workflow function | `reports/skills/dv_skill_taxonomy_<UTC>.md` |
| Skill-to-JasperLoop Mapping Agent | Map skills to prompts, workflow commands, reports, schemas, and docs | `reports/skills/dv_skill_to_jasperloop_mapping_<UTC>.md` |
| Risk / Integration Gate Agent | Identify conflicts, unsafe claims, duplicate procedures, and implementation order | `reports/skills/dv_skill_integration_gate_<UTC>.md` |

Implementation agents should wait until those reports are reviewed.

## Stage 6 Entry Criteria

Stage 6 should begin only after:

- Stage 5 checkpoint is tagged.
- DV-engineer Claude Skills have been read and categorized.
- Skills have been mapped to JasperLoop modules.
- Stage 5.5 refinements that are accepted by the gate have landed.
- Remaining caveats are preserved in release notes.

Until then, Stage 6 paper/demo/release packaging remains deferred.
