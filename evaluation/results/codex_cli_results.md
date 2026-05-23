# Codex CLI Results

| Check | Status | Notes |
| --- | --- | --- |
| `python scripts/doctor_llm_backend.py --json` | Failed backend gate | Selected PATH `codex.exe`; executable exists and parent directory is visible, but short command and contract both classify as `permission_denied`. |
| `python scripts/test_llm_backend_contract.py` | Failed contract | Backend could not launch Codex from subprocess; no model JSON was returned. |
| Direct `codex exec` JSON healthcheck | Blocked | `codex`/`codex.exe` resolves to the Windows app package but cannot be launched from this subprocess environment: `Access is denied`. |
| `scripts/run_codex_llm_eval.py --task healthcheck` | Failed before model call | Adapter returned `permission_denied`; no fake JSON was returned. |
| Benchmark subset run | Gate failed | 3+3+3 subset ran through `--llm` paths, but all calls used structured fallback because Codex CLI invocation failed. |

The healthcheck prompt is synthetic and does not include benchmark RTL, properties, evidence packets, or JasperGold logs. SVA repair, triage, and coverage tasks do include benchmark content and should be run only after approving external prompt export.

The current subset files are evidence of a failed real-LLM gate, not Codex performance results.

Use `CODEX_BIN` to point at a subprocess-callable Codex executable, or use `JASPERLOOP_LLM_CMD` for a generic JSON backend, then rerun `scripts/run_real_llm_subset_gate.sh` or `scripts/run_real_llm_subset_gate.ps1`.
