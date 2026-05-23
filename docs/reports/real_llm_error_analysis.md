# Real LLM Error Analysis

Date: 2026-05-23

Scope: local Qwen backend healthcheck, 3+3+3 subset gate, and full local Qwen benchmark after the Codex CLI subprocess route failed.

## Summary

The Codex CLI route did not reach model execution. The Windows app package `codex.exe` still fails from Python subprocess with:

```text
permission_denied: cannot execute Codex executable from subprocess: [WinError 5] Access is denied
```

The generic backend route did reach a real local model. `JASPERLOOP_LLM_CMD` pointed to `python D:\AI-DV\qwen_json_backend.py`, which called a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ` at `http://127.0.0.1:8000/v1`. The backend doctor and contract test passed.

The first 3+3+3 subset run exposed failure-triage output-control problems: JSON validity 0.667, fallback rate 0.333, and hallucinated signal rate 0.333. The triage prompt, first-JSON extraction, and allowed-signal normalization were tightened, then the subset gate was rerun. The rerun passed the subset mechanics: triage JSON validity 1.000, fallback rate 0.000, and hallucinated signal rate 0.000.

The follow-up full local Qwen benchmark used the same backend route and completed SVA repair, structured failure triage, and structured coverage closure. It is not Codex CLI performance and not JasperGold-backed performance.

## Subset Metrics

| Task | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | final exact match 0.667 |
| Failure triage | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | issue/action 0.667/0.667 |
| Coverage closure | 3 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

## Full Local Qwen Metrics

| Task | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 23 | 1.000 | 1.000 | 0.000 | 0.000 | 0.043 | final exact match / repair success 0.913 |
| Failure triage | 53 | 0.981 | 0.981 | 0.019 | 0.019 | 0.000 | issue/action 0.811/0.811 |
| Coverage closure | 14 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

The full local Qwen run passed the output mechanics gate: JSON validity >= 0.90, fallback rate <= 0.25, and hallucinated signal rate <= 0.10 where measured. This is a gate result, not formal signoff.

## Error Categories

1. JSON/schema failures: fixed for the subset rerun. The initial `apb_C5` response included extra prompt/evidence text after JSON-like content; first-valid-JSON extraction now prevents this from becoming a fallback when a valid object is present.
2. Hallucinated signals: fixed for the subset rerun and controlled in full triage. Full SVA repair still reported one hallucinated signal, `out_valid`, in `repair_fifo_reset_wrong_polarity`.
3. Wrong issue type: still present. The full triage run systematically under-detected assumption/constraint bugs, often classifying them as `assertion_property_bug`.
4. Wrong recommended action: still present. The corresponding wrong action was usually `fix_assertion_property` instead of `fix_assumption_constraint`.
5. Syntactically valid but intent-wrong SVA: SVA repair produced valid JSON and no fallback, but `repair_arbiter_single_req1_wrong_grant` and `repair_fifo_reset_wrong_polarity` did not reach scaffold exact match after 3 rounds.
6. Property proves but is too weak: not evaluated because JasperGold re-check did not run.
7. Vacuity or overconstraint cases: still the main weakness. Full triage correctly classified only 3 of 12 gold assumption/constraint cases; examples include `apb_C11`, `apb_C7`, `arbiter_A11`, `fifo_D10`, and `rv_B6`.
8. Coverage goal incorrectly treated as reachable: not observed in the full coverage run. Gap/action accuracy was 14/14, including 5 unreachable or invalid coverage goals.
9. Raw-log vs structured LLM comparison: not run; only structured subset paths were evaluated.
10. JasperGold feedback helped repair: not evaluated with real JasperGold feedback in this environment. The SVA repair loop used scaffold feedback only.

## Environment Findings

- `codex`/`codex.exe` resolves to the Codex Windows app package, but cannot be launched from this subprocess environment.
- `python scripts/doctor_llm_backend.py --json` confirms the executable exists and its parent directory can be listed, but both `codex.exe --version` and the JSON backend contract classify as `permission_denied`.
- `python scripts/test_llm_backend_contract.py` passed after switching to `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`.
- Local Qwen healthcheck at `http://127.0.0.1:8000/v1` passed through the generic command backend.
- `JASPER_BIN` and `JASPER_ENV` were unset, and no `jg` executable was found.

## Next Step

The full local Qwen run clears the local output mechanics gate, but the results should not be treated as formal correctness. The next experiment should be a separate JasperGold-backed re-check PR in an environment where `JASPER_BIN`, `JASPER_ENV`, or `jg` is available.

Recommended next constraints:

- Keep reporting JSON validity, fallback rate, hallucinated signal rate, and task accuracy separately.
- Do not treat local LLM output mechanics as proof of intent correctness.
- Do not claim JasperGold-backed performance unless `JASPER_BIN`, `JASPER_ENV`, or `jg` is available and the generic JasperGold scripts run.
- If Codex CLI performance is required, set `CODEX_BIN` to a real subprocess-callable CLI binary rather than the Windows app package alias.

The main residual model error is assumption/vacuity triage, not backend invocation.
