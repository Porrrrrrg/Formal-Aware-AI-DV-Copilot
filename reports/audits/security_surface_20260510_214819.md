# Security Surface

- Repository: `Porrrrrrg/Formal-Aware-AI-DV-Copilot`
- HEAD: `3bb6821e687db39d384abd7f6fcb00cee6f7c6c1`
- UTC: `2026-05-10 21:48:19`
- Scope: secrets/tokens/endpoints, external prompt export, command execution, signing/attestation evidence, ignored artifacts.
- Scope note: base security surface is tracked HEAD. A modified/untracked worktree overlay appeared during verification and is recorded separately.

## Summary

No committed secret values were found by keyword scan. The main tracked HEAD security surface is intentional local command execution through `JASPERLOOP_LLM_CMD`, optional external prompt export to Codex/OpenAI, and untracked generated formal artifacts under `jasper/reports/`.

Current worktree overlay adds CI/security controls that are not part of audited HEAD unless committed: `.github/workflows/ci.yml`, `.github/workflows/nightly-bench.yml`, `.github/workflows/release-attest.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `docs/security/ci_security.md`, and `.gitignore` additions for `*.egg-info/`, `artifacts/`, and `dist/`.

## Secrets and Tokens

| Evidence | Finding |
| --- | --- |
| `rg -n -i "secret|token|api[_-]?key|password|bearer|authorization|endpoint|OPENAI|ANTHROPIC|GITHUB"` | No committed credential value found. Matches are documentation or code strings about OpenAI/Codex and prompt export. |
| `.gitignore` | Ignores `.env`, `*.local.json`, `*.local.yaml`, logs, reports, VCD/FSDB/WLF, `jasper/reports/*`, and prompt previews. |

Risk: P2 - secret scanning is ad hoc in tracked HEAD. Evidence: no tracked `.github/workflows` or dedicated secret scanning config found. Worktree overlay `ci.yml` adds a custom scan plus CodeQL, but it remains uncommitted relative to audited HEAD.

## Command Execution

| Path | Surface | Finding |
| --- | --- | --- |
| `copilot/llm_client.py` | `subprocess.run(command, shell=True)` with `JASPERLOOP_LLM_CMD` | User/environment supplied command is executed via shell. This is flexible but must be treated as trusted local config only. |
| `copilot/llm_adapters/codex_json.py` | `subprocess.run([... "codex", "exec", ...])` | Uses argument-vector invocation, read-only sandbox, and output schema path when supplied. |
| `tools/run_jasper.py` | invokes `JASPER_BIN` or `jg` with `-batch` | Uses argv list and checks `shutil.which`. Writes run command and logs under `jasper/reports/...`. |
| `tools/check_generated_sva.py` | invokes `JASPER_BIN` or `jg` with generated SVA/harness | Uses argv list and writes generated properties/harness plus logs under `jasper/reports/...`. |

Risks:

- P1: Shell execution boundary for LLM backends is powerful enough for command injection if untrusted config reaches `JASPERLOOP_LLM_CMD` or `--llm-command`. Evidence: `copilot/llm_client.py`.
- P2: `JASPER_BIN` can point to arbitrary executable. Evidence: `tools/run_jasper.py`, `tools/check_generated_sva.py`. This is expected for local EDA environments but should remain outside untrusted CI.

## External Data Export

| Path | Evidence |
| --- | --- |
| `scripts/run_codex_llm_eval.py` | Requires `--acknowledge-external-send` for benchmark tasks and prints a warning describing exported benchmark content. |
| `docs/codex_cli_usage.md` | Documents benchmark prompt export and recommends prompt audit before sending externally. |
| `scripts/export_codex_prompts.py` | Exports or summarizes prompts locally; supports `--redact-evidence`; writes previews to `evaluation/prompt_previews/`, which is ignored. |
| `copilot/llm_adapters/replay_json.py`, `evaluation/fixtures/replay_sample_outputs.jsonl` | Provides offline replay path to avoid repeated network calls. |

Risks:

- P1: Benchmark content, RTL excerpts, manifests, Jasper summaries, traces, and SVA snippets may leave the local environment when Codex-backed tasks are acknowledged. Evidence: `scripts/run_codex_llm_eval.py`, `docs/codex_cli_usage.md`.
- P2: Prompt preview files can contain benchmark/formal evidence if generated without redaction. Evidence: `scripts/export_codex_prompts.py`; `.gitignore` covers `evaluation/prompt_previews/`.

Worktree overlay note: `.github/PULL_REQUEST_TEMPLATE.md` explicitly asks reviewers to confirm no default workflow sends benchmark content to external LLMs or unapproved endpoints.

## Network and Endpoints

- No application HTTP client implementation was found.
- External service references are documentation/CLI oriented: GitHub repo URL, Codex/OpenAI prompt export docs, and Codex CLI adapter.
- No hard-coded API endpoint with credential material was found.

Risk: P2 - no explicit network allowlist or outbound policy exists for LLM/Codex usage. Evidence: no workflow/policy file found; `JASPERLOOP_LLM_CMD` can call arbitrary command.

## Signing, Attestation, and Provenance

- Tracked HEAD: no `cosign`, `sigstore`, SLSA, provenance, signing, or attestation config was found.
- Tracked HEAD: no `.github/workflows` directory was found, so no CI artifact attestation evidence was found.
- Worktree overlay: GitHub artifact attestation workflows exist in `.github/workflows/ci.yml`, `nightly-bench.yml`, and `release-attest.yml`.
- Generated Jasper reports are intentionally ignored except `jasper/reports/.gitkeep`.

Risk: P2 - generated formal evidence packets and reports have no repository-level provenance or reproducibility attestation. Evidence: `.gitignore`, missing `.github/workflows`.

## Priority Findings

- P0: None found.
- P1: `JASPERLOOP_LLM_CMD` command execution uses shell=True. Path: `copilot/llm_client.py`.
- P1: External prompt export is possible after acknowledgement and can include local benchmark/formal content. Paths: `scripts/run_codex_llm_eval.py`, `docs/codex_cli_usage.md`.
- P1: No tracked HEAD CI guardrail for tests, lint, schema validation, secret scan, or prompt-export policy. Evidence: `.github/` absent from `git ls-files`; worktree overlay contains candidate workflows.
- P2: Secret scanning and provenance controls are unspecified in tracked HEAD. Evidence: no tracked workflows, no tracked signing/attestation config found.
- P2: Worktree overlay workflows need review before merge because they introduce security-sensitive CI permissions and attestation behavior. Evidence: `.github/workflows/*.yml`.
- P2: Prompt previews and Jasper artifacts are ignored, which protects accidental commit but leaves reproducibility/provenance to local procedure. Paths: `.gitignore`, `scripts/export_codex_prompts.py`, `jasper/reports/.gitkeep`.
