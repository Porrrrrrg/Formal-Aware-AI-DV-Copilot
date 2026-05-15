# Design2SVA Stage 16 Expanded Codex Error Analysis

## Scope And Boundary

Stage 16 is the first expanded real Codex Design2SVA measurement on the
validated 12-case fixture set. Stage 15 established the oracle gate first:
native references prove 12/12, and the repaired Design2SVA wrapper proves the
same 12/12 references non-vacuously.

Stage 16 then sent the audited, gold-free Design2SVA prompts to Codex and replayed
the generated candidates through JasperGold on Moore. It does not claim
production signoff or broad industrial generalization.

Tracked result artifacts:

- `evaluation/results/design2sva_eval_codex_expanded_subset.json`
- `evaluation/results/design2sva_eval_codex_expanded_jasper.json`
- `evaluation/results/design2sva_results.md`

The tracked JSON files are compacted artifacts. Heavy RTL context, generated
wrappers, and raw Jasper logs are omitted from the tracked JSON, while summary
metrics, candidate SVA/helper code, referenced signals, proof statuses, root
cause fields, and artifact path pointers are retained.

## Oracle Baseline

Stage 15 is the sanity gate:

- Native expanded oracle: 12/12 references prove in the native benchmark flow.
- Wrapper reference oracle: 12/12 references prove non-vacuously through the
  repaired Design2SVA wrapper.
- The wrapper reference result reports `wrapper_parity_pass_rate = 1.0` and
  `reference_non_vacuous@1 = 1.0`.

This means Stage 16 candidate failures can be interpreted as candidate or
repair behavior, not as known fixture/wrapper invalidity.

## LLM-Only Generation

The local real Codex generation run produced 36 initial candidates:

- Cases: 12
- k: 3
- `source_counts.llm = 36`
- `real_llm_count = 36`
- `valid_json_rate = 1.0`
- `fallback_rate = 0.0`
- `syntax@1 = 1.0`
- `syntax@k = 1.0`
- `hallucinated_signal_rate = 0.0`

Before JasperGold, the candidates are only schema-clean and syntax-clean. The
LLM-only artifact reports `formal_metrics_status = not_run`, so its
`proven@*` fields are intentionally zero.

## JasperGold Measurement

Moore/JasperGold replay measured the exact generated candidates with the repaired
wrapper path:

- `formal_metrics_status = measured`
- `proven@1 = 0.75`
- `proven@k = 1.0`
- `non_vacuous@k = 1.0`
- `proven_non_vacuous@k = 1.0`
- `valid_json_rate = 1.0`
- `fallback_rate = 0.0`
- `hallucinated_signal_rate = 0.0`

Interpretation:

- k=1 succeeds on 9/12 cases.
- k=3 succeeds on 12/12 cases.
- All 36 candidates eventually have a `proven_non_vacuous` measured row after
  the wrapper/repair path.
- Seven initial rows were repaired from an invariant/cover diagnostic condition;
  those are tracked as `unreachable_cover_goal` intermediate rows, not final
  failed cases.

## Failure Mapping

The expanded run did not expose actual unknown-signal hallucinations after the
identifier checker was fixed to ignore SystemVerilog structural keywords such as
`endproperty`.

Observed diagnostic classes:

| Class | Count | Interpretation |
| --- | ---: | --- |
| `proven_non_vacuous` | 36 | Candidate path reached a non-vacuous proof under JasperGold. |
| `unreachable_cover_goal` | 7 | Intermediate invariant/cover diagnostic rows before repair; final candidates still prove non-vacuously. |

By design, the result table keeps these diagnostic counts separate from pass@k
metrics. The pass@k metrics are the main result: `proven@k = 1.0` and
`proven_non_vacuous@k = 1.0` on the 12-case benchmark.

## What Improved

The strongest improvement is the full evidence chain:

1. The fixture/reference oracle is valid on 12/12 cases.
2. Real Codex produces schema-valid and syntax-valid candidates with no fallback.
3. JasperGold proves at least one of three candidates per case non-vacuously.
4. The result is no longer confounded by the wrapper parity bug from earlier
   stages.

This is the first strong expanded Design2SVA result in the project.

## Remaining Limits

- The benchmark is still a local 12-case fixture set, not FVEval-scale evidence.
- k=1 is 0.75, so single-sample generation is not fully reliable.
- The measured success uses the repaired wrapper and bounded evaluation path;
  it is not production signoff.
- Stage 17 should run ablations before claiming which component caused the gain:
  retrieval context, reachability guidance, wrapper parity, or repair behavior.
