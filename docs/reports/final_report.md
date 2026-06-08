# Final Report Draft

JasperLoop-DV studies how a formal-aware AI DV copilot can use structured JasperGold evidence to assist with SVA generation, SVA repair, failure triage, and coverage closure.

Key claim boundary:

- JasperGold is the formal oracle when checks are run.
- The LLM proposes and explains; it does not prove.
- Deterministic scaffold results validate local plumbing and should not be reported as hosted LLM performance.
- JasperGold proof is scoped to the checked harness, assumptions, property, and tool setup; it is not semantic intent equivalence.

The final report should draw from canonical docs:

- architecture: `docs/architecture.md`
- methods: `docs/methods.md`
- benchmark catalog: `docs/benchmark_catalog.md`
- evaluation: `docs/evaluation.md`
- claims and limitations: `docs/limitations_and_claims.md`
- artifact policy: `docs/artifact_policy.md`
