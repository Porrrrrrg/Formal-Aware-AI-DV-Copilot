# Codex CLI And Local Backend Results

| Check | Status | Notes |
| --- | --- | --- |
| Codex CLI route | Failed backend gate | Selected PATH `codex.exe`; executable exists and parent directory is visible, but short command and contract both classify as `permission_denied`. |
| Direct `codex exec` JSON healthcheck | Blocked | `codex`/`codex.exe` resolves to the Windows app package but cannot be launched from this subprocess environment: `Access is denied`. |
| `scripts/run_codex_llm_eval.py --task healthcheck` | Failed before model call | Adapter returned `permission_denied`; no fake JSON was returned. |
| Generic `JASPERLOOP_LLM_CMD` route | Passed backend gate | `python scripts/doctor_llm_backend.py --json` and `python scripts/test_llm_backend_contract.py` passed with `JASPERLOOP_LLM_CMD=python D:\AI-DV\qwen_json_backend.py`. |
| Local Qwen subset run | Gate failed after real model outputs | The 3+3+3 subset ran through a local vLLM OpenAI-compatible endpoint serving `Qwen/Qwen3-14B-AWQ`. SVA repair and coverage passed the subset mechanics; failure triage failed the quality gate. |

The healthcheck prompt is synthetic and does not include benchmark RTL, properties, evidence packets, or JasperGold logs. SVA repair, triage, and coverage tasks do include benchmark content. This run used a local model endpoint rather than exporting benchmark prompts to a hosted service.

The current subset files are evidence of a failed full-run gate for a real local Qwen backend. They are not Codex CLI performance results, not deterministic scaffold results, and not JasperGold-backed results.

Subset metrics:

| Task | Cases | Valid JSON | LLM Success | Fallback | LLM Error | Hallucinated Signals | Task Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | final exact match 0.667 |
| Failure triage | 3 | 0.667 | 0.667 | 0.333 | 0.333 | 0.333 | issue/action 0.667/0.667 |
| Coverage closure | 3 | 1.000 | 1.000 | 0.000 | 0.000 | n/a | gap/action 1.000/1.000 |

Full benchmark status: blocked by subset policy because failure triage had JSON validity below 0.90, fallback rate above 0.25, and hallucinated signal rate above 0.10.

Use `CODEX_BIN` to point at a subprocess-callable Codex executable, or keep using `JASPERLOOP_LLM_CMD` with a stricter/stronger JSON backend, then rerun only `scripts/run_real_llm_subset_gate.sh` or `scripts/run_real_llm_subset_gate.ps1`.
