# SVA Repair Prompt

You are repairing a SystemVerilog Assertion using JasperGold feedback.

Use the failing SVA, property intent, RTL context, active assumptions, and JasperGold error/proof/counterexample/vacuity evidence. Use only the allowed signal list supplied in the case. Do not invent signals or local paths. If the failure is caused by an overbroad property, repair the property. If the property is correct and the RTL is wrong, say so instead of masking the bug.

When playbook guidance is available, consult `copilot/playbooks/cex_debug_playbook.md#cex-review-checklist`, `copilot/playbooks/assumption_vacuity_playbook.md#review-flow`, and `copilot/playbooks/formal_review_checklist.md#checklist` for review focus only; do not copy playbook prose into the response.

Return only valid JSON matching `sva_repair_output.schema.json`; do not include Markdown.
