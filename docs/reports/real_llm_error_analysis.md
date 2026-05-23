# Real LLM Error Analysis

Date: 2026-05-22

Scope: local Qwen backend healthcheck and 3+3+3 subset gate after the Codex CLI subprocess route failed.

## Summary

The Codex CLI route did not reach model execution. The Windows app package `codex.exe` still fails from Python subprocess with:

```text
permission_denied: cannot execute Codex executable from subprocess: [WinError 5] Access is denied
```

The generic backend route did reach a real local model. `JASPERLOOP_LLM_CMD` pointed to `python D:\AI-DV\qwen_json_backend.py`, which called a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ` at `http://127.0.0.1:8000/v1`. The backend doctor and contract test passed.

The 3+3+3 subset was run through the LLM-enabled evaluator paths. Full benchmark execution was stopped by policy because the failure-triage subset had JSON validity 0.667, fallback rate 0.333, and hallucinated signal rate 0.333.

This is a real local Qwen subset result. It is not Codex CLI performance and it is not JasperGold-backed performance.

## Subset Metrics

| Task | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | final exact match 0.667 |
| Failure triage | 3 | 0.667 | 0.667 | 0.333 | 0.333 | 0.333 | issue/action 0.667/0.667 |
| Coverage closure | 3 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

## Error Categories

1. JSON/schema failures: one failure-triage case (`apb_C5`) returned JSON-like content followed by additional prompt/evidence text, so the adapter rejected it as invalid JSON and the evaluator used structured fallback.
2. Hallucinated signals: one failure-triage case (`apb_C6`) named `access` and `valid_addr`, which are not in the allowed signal list for the case.
3. Wrong issue type: `apb_C6` was classified as `rtl_design_bug`; the gold label is `assertion_property_bug`.
4. Wrong recommended action: `apb_C6` recommended `fix_rtl`; the gold action is `fix_assertion_property`.
5. Syntactically valid but intent-wrong SVA: SVA repair produced valid JSON and no hallucinated signals, but one semantic repair did not reach exact template match under the scaffold check.
6. Property proves but is too weak: not evaluated because JasperGold re-check did not run.
7. Vacuity or overconstraint cases: one triage case (`apb_C11`) correctly identified an assumption-constraint issue, but no JasperGold vacuity re-check ran in this environment.
8. Coverage goal incorrectly treated as reachable: not observed in the three-case coverage subset; gap/action accuracy was 3/3.
9. Raw-log vs structured LLM comparison: not run; only structured subset paths were evaluated.
10. JasperGold feedback helped repair: not evaluated with real JasperGold feedback in this environment. The SVA repair loop used scaffold feedback only.

## Environment Findings

- `codex`/`codex.exe` resolves to the Codex Windows app package, but cannot be launched from this subprocess environment.
- `python scripts/doctor_llm_backend.py --json` confirms the executable exists and its parent directory can be listed, but both `codex.exe --version` and the JSON backend contract classify as `permission_denied`.
- `python scripts/test_llm_backend_contract.py` passed after switching to `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`.
- Local Qwen healthcheck at `http://127.0.0.1:8000/v1` passed through the generic command backend.
- `JASPER_BIN` and `JASPER_ENV` were unset, and no `jg` executable was found.

## Next Fix

Do not run the full benchmark from this result. Fix the triage backend behavior first, then rerun only the subset gate.

Candidate fixes:

- Make the generic backend reject or trim any response that includes prompt/evidence text outside the first JSON object.
- Lower `LOCAL_MAX_TOKENS` for triage or apply task-specific stop/format controls if the backend supports them.
- Strengthen output validation around allowed signals before accepting `source=llm`.
- Try a stronger subprocess-callable local/backend model after the Qwen 14B route is stable.
- If Codex CLI is required, set `CODEX_BIN` to a real subprocess-callable CLI binary rather than the Windows app package alias.

Only after the subset gate reaches JSON validity >= 0.90 and fallback rate <= 0.25 should the full Codex/LLM benchmark be run.
