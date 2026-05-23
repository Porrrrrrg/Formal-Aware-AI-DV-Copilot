# Real LLM Error Analysis

Date: 2026-05-22

Scope: attempted Codex/LLM healthcheck and 3+3+3 subset gate.

## Summary

The real LLM pass did not reach model execution. The Codex CLI healthcheck failed with:

```text
permission_denied: cannot execute Codex executable from subprocess: [WinError 5] Access is denied
```

The subset gate was still run through the LLM-enabled evaluator paths. All nine attempted LLM calls failed with the same adapter-level error and fell back to structured deterministic outputs. Full Codex/LLM benchmark execution was stopped by policy.

## Error Categories

1. JSON/schema failures: no model JSON was returned, so model JSON validity was 0/9. Evaluator result JSON files were valid.
2. Hallucinated signals: not measurable on model output. Fallback outputs had 0 hallucinated signal rate.
3. Wrong issue type: not measurable on model output. Triage fallback scored 3/3 on the subset.
4. Wrong recommended action: not measurable on model output. Triage and coverage fallbacks scored 3/3 on the subset.
5. Syntactically valid but intent-wrong SVA: not measurable on model output. SVA repair fallback matched reference templates for the subset.
6. Property proves but is too weak: not evaluated because JasperGold re-check did not run.
7. Vacuity or overconstraint cases: present in benchmark collateral, but not evaluated with real LLM or JasperGold in this pass.
8. Coverage goal incorrectly treated as reachable: not observed in model output because no model output was produced.
9. Raw-log vs structured LLM comparison: not run; only structured subset path was attempted.
10. JasperGold feedback helped repair: not evaluated with real JasperGold feedback in this environment.

## Environment Findings

- `codex`/`codex.exe` resolves to the Codex Windows app package, but cannot be launched from this subprocess environment.
- `python scripts/doctor_llm_backend.py --json` confirms the executable exists and its parent directory can be listed, but both `codex.exe --version` and the JSON backend contract classify as `permission_denied`.
- `python scripts/test_llm_backend_contract.py` fails before receiving any model JSON.
- Local Qwen healthcheck at `http://127.0.0.1:8000/v1` reported `local_unavailable`; cloud fallback was not called.
- `JASPER_BIN` and `JASPER_ENV` were unset, and no `jg` executable was found.

## Next Fix

Run the same subset gate in an environment where one of these is true:

- `codex exec` is callable non-interactively from the shell, or
- `CODEX_BIN` points to an executable Codex CLI binary, or
- `JASPERLOOP_LLM_CMD` points to a working OpenAI-compatible/local model JSON adapter.

Only after the subset gate reaches JSON validity >= 0.90 and fallback rate <= 0.25 should the full Codex/LLM benchmark be run.
