# Skill Index

Project-level Claude skills imported from the sanitized DV skill source folder. Descriptions are intentionally concise to keep model routing focused.

| Skill | Description | Source |
| --- | --- | --- |
| [rtl-analysis](../../.claude/skills/rtl-analysis/SKILL.md) | Analyze RTL connectivity, signal integrity, and CDC issues from design sources. | 01_RTL_ANALYSIS_SKILL.md |
| [rtl-lint](../../.claude/skills/rtl-lint/SKILL.md) | Review RTL for synthesizability, style, portability, and common lint issues. | 02_RTL_LINT_SKILL.md |
| [reset-sequence-verifier](../../.claude/skills/reset-sequence-verifier/SKILL.md) | Check reset sequencing, polarity, connectivity, and asynchronous deassertion safety. | 03_RESET_SEQUENCE_VERIFIER_SKILL.md |
| [parameterization-auditor](../../.claude/skills/parameterization-auditor/SKILL.md) | Audit RTL parameter propagation, overrides, ranges, defaults, and hard-coded values. | 04_PARAMETERIZATION_AUDITOR_SKILL.md |
| [constraint-writing](../../.claude/skills/constraint-writing/SKILL.md) | Generate and review SystemVerilog randomization constraints for DV testbenches. | 05_CONSTRAINT_WRITING_SKILL.md |
| [uvm-component-builder](../../.claude/skills/uvm-component-builder/SKILL.md) | Build and review UVM component scaffolding, TLM wiring, phases, and configuration. | 06_UVM_COMPONENT_BUILDER_SKILL.md |
| [sequence-scenario-generator](../../.claude/skills/sequence-scenario-generator/SKILL.md) | Create directed and constrained-random UVM sequences for coverage-driven scenarios. | 07_SEQUENCE_SCENARIO_GENERATOR_SKILL.md |
| [protocol-vip-checker](../../.claude/skills/protocol-vip-checker/SKILL.md) | Review bus protocol compliance checks and assertions for standard DUT interfaces. | 08_PROTOCOL_VIP_CHECKER_SKILL.md |
| [coverage-plan-writer](../../.claude/skills/coverage-plan-writer/SKILL.md) | Draft functional coverage plans, covergroups, coverpoints, crosses, and traceability. | 09_COVERAGE_PLAN_WRITER_SKILL.md |
| [coverage-hole-analyzer](../../.claude/skills/coverage-hole-analyzer/SKILL.md) | Analyze coverage gaps and recommend targeted tests, constraints, and sequence changes. | 10_COVERAGE_HOLE_ANALYZER_SKILL.md |
| [coverage-mapper](../../.claude/skills/coverage-mapper/SKILL.md) | Map code coverage to functional coverage to identify redundant tests and missing goals. | 11_COVERAGE_MAPPER_SKILL.md |
| [sva-assertion-writer](../../.claude/skills/sva-assertion-writer/SKILL.md) | Write and review SystemVerilog Assertions for requirements, protocols, and coverage. | 12_SVA_ASSERTION_WRITER_SKILL.md |
| [formal-property-checker](../../.claude/skills/formal-property-checker/SKILL.md) | Set up and debug formal property checks, assumptions, vacuity, and convergence. | 13_FORMAL_PROPERTY_CHECKER_SKILL.md |
| [assertion-coverage-reviewer](../../.claude/skills/assertion-coverage-reviewer/SKILL.md) | Review assertion sets for completeness, redundancy, vacuity, and requirement coverage. | 14_ASSERTION_COVERAGE_REVIEWER_SKILL.md |
| [simulation-failure-triage](../../.claude/skills/simulation-failure-triage/SKILL.md) | Triage simulation failures, assertion violations, mismatches, timeouts, and debug probes. | 15_SIMULATION_FAILURE_TRIAGE_SKILL.md |
| [regression-result-analyzer](../../.claude/skills/regression-result-analyzer/SKILL.md) | Analyze regression pass/fail trends, flaky tests, coverage progress, and health. | 16_REGRESSION_RESULT_ANALYZER_SKILL.md |
| [ral-reviewer](../../.claude/skills/ral-reviewer/SKILL.md) | Review UVM RAL models against register specs, reset values, access types, and tests. | 17_RAL_REVIEWER_SKILL.md |
| [signoff-readiness](../../.claude/skills/signoff-readiness/SKILL.md) | Assess DV signoff readiness from coverage, regressions, bugs, waivers, and risk. | 18_SIGNOFF_READINESS_SKILL.md |
| [testplan-traceability](../../.claude/skills/testplan-traceability/SKILL.md) | Map requirements, testplans, and functional coverage into traceability matrices. | 19_TESTPLAN_TRACEABILITY_SKILL.md |

## Omitted Sources

| Source | Reason |
| --- | --- |
| Feed _ LinkedIn.webloc | Non-Markdown web shortcut; explicitly excluded from import. |
| 20_JIRA_BUG_TRIAGE_SKILL.md | Omitted because it contains direct external Jira/API submission workflow and executable JavaScript network-call example. |