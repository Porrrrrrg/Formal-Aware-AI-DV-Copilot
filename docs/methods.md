# Methods

JasperLoop-DV evaluates whether structured formal evidence helps an AI DV assistant produce more useful, bounded recommendations than raw logs or prompt-only approaches.

## Evidence Packet Method

Each benchmark case has a case JSON file with design id, task type, target property or coverage goal, active assumptions, expected issue class, expected next action, and label provenance. The evidence builder optionally adds:

- JasperGold property, cover, syntax, and vacuity status rows
- counterexample or witness trace summaries
- signal role maps
- coverage-plan metadata
- RTL source context
- parser warnings or structured parser errors

Gold labels are excluded from normal packet construction unless `--include-gold` is explicitly requested.

## SVA Generation

The SVA generation runner compares direct and structured systems on local property-intent cases. Metrics include syntax scaffold pass rate, exact template match, hallucinated signal rate, and optional JasperGold syntax/proof/vacuity status.

Exact match is a scaffold metric. It is not a substitute for functional equivalence or intent alignment.

## SVA Repair

The repair runner starts from intentionally broken SVA. It checks a candidate, converts tool feedback into repair context, and retries up to a bounded number of rounds. Metrics include round-0 status, final exact match, repair success, average rounds, hallucinated signal rate, and optional JasperGold status.

## Failure Triage

The triage runner compares heuristic, raw-log, and structured systems. Metrics include issue-type accuracy, next-action accuracy, source counts, fallback rate, LLM error rate, and hallucinated signal rate.

## Coverage Closure

Coverage closure uses coverage-plan intent, formal cover status, assumptions, and witness events when present. If `witness_events` are available, prompts and agents should prefer them over inferred sequences.

## External LLM Runs

Hosted or CLI LLM runs require explicit `--llm`/`--llm-command` or the guarded Codex wrapper. Prompt audit should run before sending benchmark content outside the repository. Replay mode can score previously approved outputs without another network call.
