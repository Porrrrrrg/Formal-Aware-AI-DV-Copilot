# FVEval Subset

This directory contains a 30-case local subset imported from the public
[NVlabs/FVEval](https://github.com/NVlabs/FVEval) repository at commit
`141afe7dcf03a0b86547b94657d9d610b6087724`.

## Contents

- `cases.json`: local benchmark cases.
- `source_manifest.json`: source commit, license, and deterministic selection rule.

## Selection

- 10 `NL2SVA-Human` cases: first 10 rows from
  `data_nl2sva/data/nl2sva_human.csv`.
- 10 `NL2SVA-Machine` cases: first 10 rows from
  `data_nl2sva/data/nl2sva_machine.csv`.
- 10 `Design2SVA` cases: first 5 pipeline rows and first 5 FSM rows from
  `data_design2sva/data/design2sva_*.csv`.

## Local Schema

Each case maps the source row into:

- `problem_spec`: natural-language instruction for NL2SVA, RTL for Design2SVA.
- `property_intent`: assertion intent used by local runners.
- `allowed_signals` / `signals`: identifiers allowed for hallucination checks.
- `expected_sva` / `reference_sva`: evaluation-only reference when available.
- `testbench_header` and `testbench`: source testbench context.

Reference assertions are present only for scoring and must not be included in
model prompts. The local runner emits sanitized prompt payloads that omit
`expected_sva` and `reference_sva`.

## Limitations

This import is FVEval-compatible data plumbing, not an apples-to-apples FVEval
official result. Local runners may report syntax scaffold checks,
exact/reference match where a reference exists, valid JSON, fallback use, and
hallucinated signal rate. External references are retained as evaluation
metadata only, and reference answers are omitted from prompt payloads. The
runner does not reproduce FVEval's commercial Jasper/property-equivalence
functional-equivalence flow. Design2SVA admits multiple valid assertions, so
exact matching is not a functional equivalence or correctness metric for that
subset. No JasperGold, Codex, or Qwen execution is performed by the local
runner.
