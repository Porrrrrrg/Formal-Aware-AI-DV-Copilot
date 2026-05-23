# Real LLM Error Analysis

Date: 2026-05-23

Scope: local Qwen backend healthcheck and 3+3+3 subset gate after the Codex CLI subprocess route failed.

## Summary

The Codex CLI route did not reach model execution. The Windows app package `codex.exe` still fails from Python subprocess with:

```text
permission_denied: cannot execute Codex executable from subprocess: [WinError 5] Access is denied
```

The generic backend route did reach a real local model. `JASPERLOOP_LLM_CMD` pointed to `python D:\AI-DV\qwen_json_backend.py`, which called a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ` at `http://127.0.0.1:8000/v1`. The backend doctor and contract test passed.

The first 3+3+3 subset run exposed failure-triage output-control problems: JSON validity 0.667, fallback rate 0.333, and hallucinated signal rate 0.333. The triage prompt, first-JSON extraction, and allowed-signal normalization were tightened, then the subset gate was rerun. The rerun passed the subset mechanics: triage JSON validity 1.000, fallback rate 0.000, and hallucinated signal rate 0.000.

This is a real local Qwen subset result. It is not Codex CLI performance, not a full benchmark result, and not JasperGold-backed performance.

## Subset Metrics

| Task | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | final exact match 0.667 |
| Failure triage | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | issue/action 0.667/0.667 |
| Coverage closure | 3 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

## Error Categories

1. JSON/schema failures: fixed for the subset rerun. The initial `apb_C5` response included extra prompt/evidence text after JSON-like content; first-valid-JSON extraction now prevents this from becoming a fallback when a valid object is present.
2. Hallucinated signals: fixed for the subset rerun. The initial `apb_C6` response named `access` and `valid_addr`, which are not in the allowed signal list; triage normalization now drops unsupported suspect signals instead of accepting them.
3. Wrong issue type: still present in the subset. The rerun classified `apb_C11` as `assertion_property_bug`; the gold label is `assumption_constraint_bug`.
4. Wrong recommended action: still present in the subset. The rerun recommended `fix_assertion_property` for `apb_C11`; the gold action is `fix_assumption_constraint`.
5. Syntactically valid but intent-wrong SVA: SVA repair produced valid JSON and no hallucinated signals, but one semantic repair did not reach exact template match under the scaffold check.
6. Property proves but is too weak: not evaluated because JasperGold re-check did not run.
7. Vacuity or overconstraint cases: one triage case (`apb_C11`) remained wrong after the output-control fix, showing that output mechanics can pass even when task accuracy needs more model/prompt work.
8. Coverage goal incorrectly treated as reachable: not observed in the three-case coverage subset; gap/action accuracy was 3/3.
9. Raw-log vs structured LLM comparison: not run; only structured subset paths were evaluated.
10. JasperGold feedback helped repair: not evaluated with real JasperGold feedback in this environment. The SVA repair loop used scaffold feedback only.

## Environment Findings

- `codex`/`codex.exe` resolves to the Codex Windows app package, but cannot be launched from this subprocess environment.
- `python scripts/doctor_llm_backend.py --json` confirms the executable exists and its parent directory can be listed, but both `codex.exe --version` and the JSON backend contract classify as `permission_denied`.
- `python scripts/test_llm_backend_contract.py` passed after switching to `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`.
- Local Qwen healthcheck at `http://127.0.0.1:8000/v1` passed through the generic command backend.
- `JASPER_BIN` and `JASPER_ENV` were unset, and no `jg` executable was found.

## Next Step

The subset gate now allows a full local Qwen benchmark run as the next experiment, but it has not been run in this PR.

Recommended next constraints:

- Keep reporting JSON validity, fallback rate, hallucinated signal rate, and task accuracy separately.
- Do not treat subset gate pass as full benchmark success.
- Do not claim JasperGold-backed performance unless `JASPER_BIN`, `JASPER_ENV`, or `jg` is available and the generic JasperGold scripts run.
- If Codex CLI performance is required, set `CODEX_BIN` to a real subprocess-callable CLI binary rather than the Windows app package alias.

The main residual model error is assumption/vacuity triage (`apb_C11`), not backend invocation.
