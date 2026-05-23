# Local Qwen Workflow Backend

Stage 5E wires a LOCAL_ONLY OpenAI-compatible local Qwen endpoint into the
`jasperloop workflow` commands. This path is for workflow readiness only. It
does not run full benchmarks, does not call JasperGold or Moore, does not use
cloud fallback, and does not compare Qwen with Codex.

## Start a Local Backend

Use one of the documented local serving profiles:

- vLLM: `bash ops/local-llm/run_vllm.sh`
- SGLang: `bash ops/local-llm/run_sglang.sh`
- Ollama OpenAI-compatible endpoint: see `ops/local-llm/run_ollama.md`

Set the local-only environment before any executable workflow run:

```bash
export LOCAL_ONLY=true
export LOCAL_BASE_URL=http://127.0.0.1:8000/v1
export SERVED_MODEL_NAME=Qwen/Qwen3-14B-AWQ
export SERVING_BACKEND=vllm
```

The workflow adapter also accepts CLI overrides:

```bash
python -m app.cli workflow repair \
  --backend local \
  --local-only \
  --local-base-url http://127.0.0.1:8000/v1 \
  --local-model Qwen/Qwen3-14B-AWQ \
  --local-backend-type vllm \
  --dry-run
```

## Readiness Check

First run the existing local healthcheck. It writes a local manifest and never
executes cloud fallback:

```bash
python ops/local-llm/healthcheck.py --strict-exit
```

If the endpoint is unavailable, the workflow path records a structured
`WorkflowManifest` with `status=local_unavailable` and writes a blocker report
under `reports/local_llm/`.

## Dry-Run Workflow

Dry-runs do not call the endpoint. They only resolve metadata, emit local
artifacts, and record the local backend route:

```bash
python -m app.cli workflow repair --backend local --dry-run --out-dir artifacts/local-workflow-smoke
python -m app.cli workflow triage --backend local --dry-run --out-dir artifacts/local-triage-smoke
python -m app.cli workflow coverage --backend local --dry-run --out-dir artifacts/local-coverage-smoke
python -m app.cli workflow demo --backend local --local-only --out-dir artifacts/qwen-demo --dry-run
```

The manifest includes the backend route, model id, endpoint URL, backend type,
`LOCAL_ONLY`, `cloud_fallback_allowed=false`, `cloud_fallback_called=false`,
task type, case count, JSON validity fields, error counts, latency when
available, GPU metadata when `nvidia-smi` is available, and the claim boundary.

## 3+3+3 Local Subset

Run this only after the healthcheck is healthy and only when a local endpoint is
intentionally allowed:

```bash
export LOCAL_ONLY=true

python -m app.cli workflow demo \
  --backend local \
  --run-local-subset \
  --local-only \
  --acknowledge-local-model-run \
  --out-dir artifacts/qwen-demo
```

This executes only:

- 3 SVA repair cases from `benchmarks/sva_repair_cases.json`
- 3 triage packets from checked-in benchmark cases
- 3 coverage packets from checked-in benchmark cases

It is not a benchmark result. It is a readiness subset for endpoint wiring,
strict JSON parsing, schema validation, and manifest capture.

## LOCAL_ONLY and Cloud Fallback

Executable local runs require both `LOCAL_ONLY=true` in the environment and the
CLI flags `--local-only --acknowledge-local-model-run`. The adapter never reads
cloud API keys and never calls a cloud endpoint. Even if cloud environment
variables are present, local workflow manifests record:

```json
{
  "cloud_fallback_allowed": false,
  "cloud_fallback_called": false
}
```

If the local endpoint is down, the workflow stops with `status=local_unavailable`
instead of silently switching to Codex or another provider.

## Claim Boundary

No Qwen-vs-Codex comparison is claimed from this workflow path. A dry-run proves
only that manifest and artifact plumbing is safe. A successful 3+3+3 subset
proves only that the configured local endpoint returned parseable, schema-valid
JSON for those nine explicit cases.
