# Codex CLI And Local Backend Results

| Check | Status | Notes |
| --- | --- | --- |
| Codex CLI route | Failed backend gate | Selected PATH `codex.exe`; executable exists and parent directory is visible, but short command and contract both classify as `permission_denied`. |
| Direct `codex exec` JSON healthcheck | Blocked | `codex`/`codex.exe` resolves to the Windows app package but cannot be launched from this subprocess environment: `Access is denied`. |
| `scripts/run_codex_llm_eval.py --task healthcheck` | Failed before model call | Adapter returned `permission_denied`; no fake JSON was returned. |
| Generic `JASPERLOOP_LLM_CMD` route | Passed backend gate | `python scripts/doctor_llm_backend.py --json` and `python scripts/test_llm_backend_contract.py` passed with `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`. |
| Local Qwen subset rerun | Gate passed; full benchmark not run | The 3+3+3 subset ran through a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ`. Triage JSON/fallback/hallucinated-signal controls passed after tightening output handling. |

The healthcheck prompt is synthetic and does not include benchmark RTL, properties, evidence packets, or JasperGold logs. SVA repair, triage, and coverage tasks do include benchmark content. This run used a local model endpoint rather than exporting benchmark prompts to a hosted service.

The current subset files are evidence of a passed 3+3+3 gate for a real local Qwen backend. They are not Codex CLI performance results, not deterministic scaffold results, not full benchmark results, and not JasperGold-backed results.

Subset metrics:

| Task | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | final exact match 0.667 |
| Failure triage | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | issue/action 0.667/0.667 |
| Coverage closure | 3 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

Full benchmark status: allowed next by subset gate policy, but not run in this PR. Triage issue/action accuracy remains 0.667/0.667 on the subset, so any next full run should still report task accuracy separately from gate mechanics.

Use `CODEX_BIN` to point at a subprocess-callable Codex executable if Codex CLI performance is needed. Otherwise keep using `JASPERLOOP_LLM_CMD` for local/backend LLM runs.
