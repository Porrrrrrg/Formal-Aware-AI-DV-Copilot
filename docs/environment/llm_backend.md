# LLM Backend Routes

JasperLoop-DV uses a command backend contract for real LLM experiments:

```text
read prompt from stdin, write exactly one JSON object to stdout
```

Fallback-only runs are failed environment gates, not model performance. A real LLM result requires a row source equivalent to `llm`; deterministic scaffold and real LLM tables must remain separate.

## Route A: Codex CLI

Use this route when a noninteractive Codex CLI binary is callable from the shell.

```bash
export CODEX_BIN=/path/to/codex
python scripts/doctor_llm_backend.py
python scripts/test_llm_backend_contract.py
bash scripts/run_real_llm_subset_gate.sh
```

On Windows PowerShell:

```powershell
$env:CODEX_BIN = "C:\path\to\codex.exe"
python scripts/doctor_llm_backend.py
python scripts/test_llm_backend_contract.py
.\scripts\run_real_llm_subset_gate.ps1
```

If the doctor reports `permission_denied`, the current shell cannot execute the selected binary from subprocess. Point `CODEX_BIN` at a real executable, run from a shell with execution permission, or use Route B.

## Route B: Generic Command Backend

Use this route for any local or hosted wrapper that reads stdin and writes JSON stdout.

```bash
export JASPERLOOP_LLM_CMD="python path/to/json_backend.py"
python scripts/doctor_llm_backend.py
python scripts/test_llm_backend_contract.py
bash scripts/run_real_llm_subset_gate.sh
```

This route can be backed by local vLLM/Qwen, an OpenAI-compatible wrapper, or another controlled backend. Record provider, model, command, prompt/schema versions, and failure policy in the run notes.

## Route C: Offline Replay

Replay is only for adapter regression and offline scoring of previously approved outputs.

```bash
export JASPERLOOP_LLM_CMD="python copilot/llm_adapters/replay_json.py --responses evaluation/fixtures/replay_sample_outputs.jsonl"
python scripts/test_llm_backend_contract.py
```

Replay output is not real LLM performance. It may be used to confirm evaluator plumbing, schema parsing, and source/fallback metrics.

## Gate Policy

Run only the 3+3+3 subset until the backend is healthy:

```bash
bash scripts/run_real_llm_subset_gate.sh
```

The script runs:

1. `python scripts/doctor_llm_backend.py`
2. `python scripts/test_llm_backend_contract.py`
3. SVA repair, triage, and coverage subset evaluation only if both checks pass
4. `python scripts/update_codex_subset_quality.py`

Do not run the full benchmark until the subset has JSON validity >= 0.90, fallback rate <= 0.25, and hallucinated signal rate <= 0.10.
