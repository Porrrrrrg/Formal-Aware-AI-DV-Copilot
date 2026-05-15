# Design2SVA Stage 16 Error Analysis

## Scope

This note analyzes the expanded 12-case Codex Design2SVA Stage 16 artifacts:

- `evaluation/results/design2sva_eval_codex_expanded_subset.json`
- `evaluation/results/design2sva_eval_codex_expanded_jasper.json`
- `evaluation/results/design2sva_results.md`
- `evaluation/prompt_previews/design2sva_expanded_prompt_audit.md`
- Stage 15 oracle controls in `evaluation/results/design2sva_reference_oracle_expanded_jasper.json`
  and `evaluation/results/design2sva_native_oracle_expanded_jasper.json`

The important boundary is provenance:

- Stage 15 is the oracle gate. Native references prove 12/12, and the repaired
  Design2SVA wrapper proves the 12/12 reference assertions non-vacuously.
- `design2sva_eval_codex_expanded_subset.json` is real Codex generation only:
  36 LLM candidates, k=3 for 12 cases, formal checks not run.
- `design2sva_eval_codex_expanded_jasper.json` is a replay of those exact saved
  real LLM candidates through JasperGold. It is a replay artifact by mode, but
  its proof outcomes are JasperGold-measured outcomes.
- Deterministic scaffold and dry-run replay rows in the result ledger validate
  plumbing only. They should not be cited as LLM quality or formal proof
  evidence.

## Headline Metrics

For the real Codex generation artifact:

| Metric | Value | Meaning |
| --- | ---: | --- |
| Cases | 12 | Expanded fixture set |
| k | 3 | Three candidates per case |
| Real LLM rows | 36 | `source_counts.llm = 36` |
| Valid JSON | 1.000 | Schema-valid outputs |
| Fallback | 0.000 | No structured fallback outputs |
| Syntax@1 / syntax@k | 1.000 / 1.000 | Syntax-clean before Jasper |
| Formal status | `not_run` | No proof claim from this artifact |

For the JasperGold replay artifact:

| Metric | Value | Meaning |
| --- | ---: | --- |
| `proven@1` | 0.750 | 9/12 first candidates proved in first round |
| `proven@k` | 1.000 | Every case had at least one initially proving candidate among k=3 |
| `non_vacuous@k` | 1.000 | k=3 yielded a non-vacuous proof for every case |
| `proven_non_vacuous@k` | 1.000 | Final candidate paths all reached proven non-vacuous |
| Initial failed rows | 7/36 | All were `unreachable_cover_goal` diagnostics |
| Final proven rows | 36/36 | Every candidate path eventually reached `proven_non_vacuous` |

The JSON summary field `formal_metrics_status` is `replayed` in the Jasper file
because saved candidates were replayed, not newly generated. The proof metadata
inside the rows is still JasperGold backend evidence.

## Case Split

The pass@k split below uses first-round candidate rows, matching the summary
calculation for `proven@1` and `proven@k`. Feedback repair rounds are discussed
separately.

| Case | Design | Property | First proving initial candidate | Class |
| --- | --- | --- | ---: | --- |
| `design2sva_arbiter_mutex` | `arbiter_rr2` | `p_mutex` | 0 | Solved at k=1 |
| `design2sva_fifo_no_underflow` | `fifo_1r1w` | `p_no_underflow` | 0 | Solved at k=1 |
| `design2sva_arbiter_no_spurious_gnt0` | `arbiter_rr2` | `p_no_spurious_gnt0` | 0 | Solved at k=1 |
| `design2sva_arbiter_single_req0_grant` | `arbiter_rr2` | `p_single_req0_grant` | 0 | Solved at k=1 |
| `design2sva_rv_buffer_out_valid_equals_full` | `rv_buffer` | `p_out_valid_equals_full` | 0 | Solved at k=1 |
| `design2sva_rv_buffer_stable_while_stalled` | `rv_buffer` | `p_data_stable_while_stalled` | 0 | Solved at k=1 |
| `design2sva_apb_pready_response_valid` | `apb_regblock` | `p_pready_response_valid` | 0 | Solved at k=1 |
| `design2sva_fifo_no_overflow` | `fifo_1r1w` | `p_no_overflow` | 0 | Solved at k=1 |
| `design2sva_fifo_pop_data_stable` | `fifo_1r1w` | `p_pop_data_stable_when_stalled` | 0 | Solved at k=1 |
| `design2sva_rv_buffer_ready_full` | `rv_buffer` | `p_in_ready_when_full_and_out_ready` | 1 | Required k>1 |
| `design2sva_apb_setup_enable` | `apb_regblock` | `p_setup_then_enable` | 2 | Required k>1 |
| `design2sva_apb_invalid_address_behavior` | `apb_regblock` | `p_invalid_address_behavior` | 1 | Required k>1 |

So the measured first-round split is 9 solved at k=1 and 3 requiring k>1.

## Failed First Candidates

The failed first candidates are exactly the three cases that make `proven@1`
fall below `proven@k`.

| Case | c0 first-round status | First-round category | Later initial candidate | Feedback repair |
| --- | --- | --- | ---: | --- |
| `design2sva_rv_buffer_ready_full` | `failed`, proof `unreachable` | `unreachable_cover_goal` | c1 | c0 round 1 proved |
| `design2sva_apb_setup_enable` | `unknown`, proof `unreachable` | `unreachable_cover_goal` | c2 | c0 round 1 proved |
| `design2sva_apb_invalid_address_behavior` | `unknown`, proof `unreachable` | `unreachable_cover_goal` | c1 | c0 round 1 proved |

All three first candidates were syntactically valid and used known signals. The
common pattern is a multi-line `property ... endproperty` declaration followed
by `assert property (name);`. The feedback repair canonicalized these into
labeled inline assertions, after which JasperGold proved them non-vacuously.

There were four additional first-round failures that were not c0 failures:

| Case | Candidate | Category | Feedback repair |
| --- | ---: | --- | --- |
| `design2sva_apb_setup_enable` | c1 | `unreachable_cover_goal` | Proved in round 1 |
| `design2sva_arbiter_single_req0_grant` | c1 | `unreachable_cover_goal` | Proved in round 1 |
| `design2sva_apb_invalid_address_behavior` | c2 | `unreachable_cover_goal` | Proved in round 1 |
| `design2sva_fifo_no_overflow` | c1 | `unreachable_cover_goal` | Proved in round 1 |

These seven rows explain the artifact's `backend_status_counts` of 36 passed
rows plus 7 intermediate failed or unknown rows. They are not seven failed
cases.

## Syntax-Only Success

There are two syntax-only interpretations to keep separate:

- In the real Codex generation artifact, all 36 rows are valid JSON and syntax
  clean, but formal status is `not_run`. That is schema and parser quality, not
  proof quality.
- In the JasperGold replay artifact, all 36 first-round candidates are still
  syntax clean, but 7/36 first-round rows fail the formal/reachability gate with
  `unreachable_cover_goal`. These rows show why syntax@k alone overstates
  usefulness.

No Stage 16 formal claim should be made from syntax metrics alone. The formal
claim comes only from the JasperGold replay rows.

## Vacuity And Reachability Risks

The measured Jasper replay is strong on final non-vacuity:

- All 36 final candidate paths have `proof_status = proven`.
- All 36 final candidate paths have `vacuity_status = not_flagged_vacuous`.
- `proven_non_vacuous@k = 1.0`.
- `antecedent_reachable@k = 1.0`.

The remaining vacuity risk is not an observed final vacuous proof. It is the
diagnostic fragility exposed by the seven `unreachable_cover_goal` intermediate
rows. Those rows were classified with root cause `cover_generation_bug` and
detail `invariant_assertion_reported_unreachable_without_antecedent_cover_obligation`.
The repaired inline assertions proved, but the first-round failures show that
surface SVA form and cover extraction can still perturb reachability diagnostics.

Also keep native and wrapper evidence separate: the native Stage 15 oracle proves
12/12 references, while the wrapper reference oracle proves 12/12 references
non-vacuously. Native vacuity is not the same measurement as wrapper
non-vacuity.

## Hallucination Risks

The compact Stage 16 JSON artifacts report no unknown-signal hallucinations:

- Real Codex generation JSON: `hallucinated_signal_rate = 0.0`.
- Jasper replay JSON: `hallucinated_signal_rate = 0.0`.
- All initial rows have `has_hallucinated_signal = false`.

The prompt audit also reports no gold leakage: no `reference_sva`, no exact
reference SVA value, no `expected_proof_status`, and no Jasper evidence in the
prompts.

There is still a reporting caveat. The generated Markdown file
`evaluation/results/design2sva_eval_codex_expanded_subset.md` contains an older
hallucination/root-cause summary that conflicts with the compact JSON and result
ledger after the SystemVerilog keyword filtering fix. For Stage 16 accounting,
use the JSON artifacts and `design2sva_results.md` rollup, which report 0.0
hallucinated signal rate.

Signal hallucination is not the only hallucination mode. A candidate can use
valid signals but encode the wrong temporal relation. Stage 16 does not show
final failures of that kind on this 12-case set, but the benchmark is too small
to rule it out generally.

## Why pass@k Matters

Stage 16 would look materially worse if only one candidate were sampled:

- k=1: 9/12 first candidates prove in the first round.
- k=3: 12/12 cases have at least one first-round proving candidate.

The three k>1 cases are not invalid tasks and not Jasper-only flukes. Their
oracle controls passed in Stage 15, and alternate Codex candidates for the same
prompts proved non-vacuously under JasperGold. This is exactly the reason to
report pass@k for LLM-generated SVA: the model often has the right intent but
varies in surface form and temporal encoding. Sampling multiple candidates lets
the verifier select a proving, non-vacuous candidate instead of treating the
first syntactically valid candidate as the whole model result.

Pass@k should not be confused with repair:

- `proven@1` and `proven@k` are computed from first-round candidate rows.
- Feedback repair later fixes the seven intermediate `unreachable_cover_goal`
  rows.
- `proven_non_vacuous@k` is computed from final candidate paths after repair.

Reporting only final repaired success would hide first-candidate brittleness.
Reporting only syntax@k would hide formal failures. The useful Stage 16 result
is the combination: real LLM outputs, JasperGold-measured replay, pass@1 below
pass@k, and final non-vacuous proof after the repaired wrapper/feedback path.

## Bottom Line

Supported by Stage 16:

- 12/12 expanded cases are valid evaluation targets under the Stage 15 oracle
  gate.
- Real Codex produced 36/36 valid JSON, syntax-clean, non-fallback candidates.
- JasperGold replay of those exact candidates measured 9/12 pass@1 and 12/12
  pass@3.
- Final repaired candidate paths reached 36/36 proven non-vacuous outcomes.

Not supported:

- Production signoff.
- Generalization beyond this local 12-case fixture set.
- A claim that one Codex sample is sufficient.
- A claim that syntax-valid SVA is equivalent to formally useful SVA.
- Attribution of the gain to one component without Stage 17 ablations.
