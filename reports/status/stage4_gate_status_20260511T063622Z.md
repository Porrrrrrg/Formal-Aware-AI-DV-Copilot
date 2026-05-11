# Stage 4 Gate Status

Created UTC: `20260511T063622Z`

Branch: `stage/stage4-gate`

Base commit: `b9acdb4b768845780b777813714a89bc1b5b2353`

Stage 3 checkpoint tag: `stage3-checkpoint-a13eeec`

Stage 3 baseline commit: `a13eeeca64817f8257c22c7c4aaacb21527241f6`

## Scope

This report starts the Stage 4 gate from the Stage 3 release checkpoint. It is a
status-only artifact and does not implement feature changes, run benchmarks, call
models, rerun JasperGold, or modify schemas.

Stage 4 PRs must state what evidence they add relative to the Stage 3 checkpoint
and must keep scaffold results, real LLM outputs, and Jasper/Qwen evidence
separate.

## Current Queue Snapshot

At report creation time:

- Remote `origin/main` is `b9acdb4b768845780b777813714a89bc1b5b2353`.
- Remote tag `stage3-checkpoint-a13eeec` is available.
- No open GitHub PRs were observed.
- No remote `stage/*` branches were observed before this gate branch is pushed.

## Active First-Wave Branches

| Branch | Owner lane | Observed status | Evidence type | Gate expectation |
| --- | --- | --- | --- | --- |
| `stage/stage4-gate` | Gate | Active local branch | Gate/status report only | No feature/code changes; this report is the only intended write |
| `stage/sva-repair-ablation` | Stage 4A SVA repair ablation | Not observed yet | Planned real LLM / repair ablation report | Must separate scaffold success, selected-output Jasper proof, and best-of-k proof |
| `stage/expanded-benchmark-moore-evidence` | Stage 4B expanded benchmark evidence | Not observed yet | Planned Moore/JasperGold evidence for expanded FIFO/vacuity cases | Must separate expected metadata from observed Jasper evidence and avoid raw logs |

## Planned Later Branches

| Branch | Owner lane | Status | Evidence type | Gate expectation |
| --- | --- | --- | --- | --- |
| `stage/fveval-subset-eval` | Stage 4C FVEval-compatible subset evaluation | Planned later unless already opened by another agent | External-anchor subset evaluation | Must not claim official FVEval reproduction or commercial equivalence scoring |
| `stage/qwen-local-bringup` | Stage 4D local Qwen bring-up | Planned later unless local endpoint is available | Local-only readiness/subset evidence | Must enforce `LOCAL_ONLY=true`, no cloud fallback, and no Qwen-vs-Codex comparison |

## Mandatory PR Fields

Every Stage 4 PR should include:

| Field | Required content |
| --- | --- |
| Evidence type | One of gate/status, deterministic scaffold, real LLM, Moore/JasperGold, local Qwen, or mixed with components separated |
| Commands run | Exact commands, including whether they were local, Moore, or local-LLM commands |
| Model route | Codex, Qwen local, deterministic scaffold, or none |
| Jasper/Qwen/Codex usage | Whether JasperGold, Qwen, or Codex was used, and whether any run was unavailable or blocked |
| CI status | Local checks and GitHub Actions result when available |
| Claim boundary | What the PR supports and what it explicitly does not support |

## Gate Rules

- Do not commit raw Jasper logs, trace directories, generated harness dumps,
  license output, or large tool artifacts.
- Do not leak prompt payloads containing reference answers or full raw prompts
  when reports only need sanitized summaries.
- Do not compare Qwen and Codex unless both manifests have comparable model,
  backend, prompt, task, latency, token, fallback, and hardware fields.
- Do not report best-of-k as single-output repair success. Best-of-candidates
  pass@k is an upper-bound search result unless the selected output is proven.
- Do not claim official FVEval reproduction without matching the official metric
  and commercial-equivalence flow.
- Keep expected benchmark metadata separate from observed Jasper evidence.
- Keep `non_vacuous_proven` wording bounded unless an explicit independent
  vacuity certificate is generated.

## Stage 4 Acceptance Frame

Stage 4 should answer evidence questions, not just add artifacts:

1. Whether CEX-aware, structural, signal whitelist, temporal hint, multi-round,
   or self-check components improve SVA repair.
2. Whether expanded FIFO/vacuity benchmark cases have schema-valid Moore
   evidence packets.
3. Whether the FVEval-compatible subset runner works without answer leakage and
   with bounded comparability claims.
4. Whether local Qwen can complete a local-only 3+3+3 subset, or whether the
   blocker remains explicit.

## Initial Gate Decision

The Stage 4 queue is clean at this snapshot. The preferred first wave is:

1. `stage/sva-repair-ablation`
2. `stage/expanded-benchmark-moore-evidence`
3. `stage/stage4-gate`

`stage/fveval-subset-eval` and `stage/qwen-local-bringup` should remain later
lanes unless they already exist and can satisfy the mandatory PR fields without
expanding scope.

## Validation

Validation for this report branch should include:

| Command | Expected result |
| --- | --- |
| `python -m pytest -q` | Pass |
| `python -m ruff check .` | Pass |
| `git diff --check` | Pass |

