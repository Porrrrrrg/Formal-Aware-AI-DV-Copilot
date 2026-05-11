# Stage 4 Second-Wave Gate

Created UTC: `20260511T141346Z`

Branch: `stage/stage4-second-wave-gate`

Base commit: `58b1ec13b5ebc26272826b6dcf98c7326e746e8a`

Stage 3 checkpoint tag: `stage3-checkpoint-a13eeec`

## Scope

This is a gate/status report only. It does not implement feature changes, run
benchmarks, call models, rerun JasperGold, modify schemas, or modify benchmark
labels.

The second wave should convert Stage 4 first-wave artifacts into bounded
evidence. In particular, SVA repair ablation candidates need Moore/JasperGold
final-proof validation before any formal repair-quality claim is made.

## Current Repository Snapshot

At report creation time:

- `origin/main` is `58b1ec13b5ebc26272826b6dcf98c7326e746e8a`.
- GitHub open PR search returned no open PRs.
- Remote branch scan returned only `main`.
- A local worktree for `stage/fveval-subset-eval` was observed, but no remote
  branch or PR was observed for it.
- No remote `stage/sva-repair-ablation-moore-proof`,
  `stage/qwen-local-bringup`, or `stage/stage4-second-wave-gate` branch was
  observed before this report branch is pushed.

## First-Wave Baseline Now On Main

The second wave starts after these Stage 4 first-wave results were merged:

| Lane | Evidence now on `main` | Claim boundary |
| --- | --- | --- |
| Stage 4 gate | Initial Stage 4 gate report | Status-only; no experiment evidence |
| Expanded benchmark evidence | 53/53 packet-level Moore/JasperGold evidence packets schema-valid | Prove-backed packet evidence; auxiliary cover/vacuity blockers remain bounded |
| SVA repair ablation | Seven Codex-backed variants with local scaffold metrics and a sanitized Moore handoff artifact | No new Jasper proof for ablation outputs yet; no formal-success claim |

## Second-Wave Lanes

| Lane | Branch | Observed status | Evidence type | Gate decision |
| --- | --- | --- | --- | --- |
| SVA repair ablation Moore proof | `stage/sva-repair-ablation-moore-proof` or equivalent | Not observed remotely | Moore/JasperGold final-proof evidence for #37 ablation candidates | P0. Should be reviewed before any formal ablation conclusion |
| FVEval-compatible subset evaluation | `stage/fveval-subset-eval` | Local worktree observed; no remote PR observed | External-anchor subset evaluation | P1. Allowed if no reference-answer leakage and no official FVEval reproduction claim |
| Qwen local bring-up | `stage/qwen-local-bringup` | Not observed | Local-only Qwen 3+3+3 subset or explicit readiness blocker | P1/P2. Allowed only with `LOCAL_ONLY=true`, no cloud fallback, and no Qwen-vs-Codex conclusion |
| Second-wave gate | `stage/stage4-second-wave-gate` | Active local branch | Gate/status report only | This PR should remain report-only |

## Required PR Fields

Every second-wave PR must state:

| Field | Required content |
| --- | --- |
| Evidence type | Gate/status, Moore/JasperGold, FVEval-compatible local evaluation, local Qwen, or mixed with components separated |
| Commands run | Exact commands, including local, Moore, or local-LLM context |
| Model route | Codex, Qwen local, deterministic scaffold, none, or not applicable |
| Jasper/Qwen/Codex usage | Whether JasperGold, Qwen, or Codex was used; blocked or unavailable runs must be explicit |
| CI status | Local checks and GitHub Actions status when available |
| Claim boundary | What the PR supports and what it explicitly does not support |

## Gate Rules

- Do not commit raw Jasper logs, trace directories, generated harness dumps,
  license output, or large generated artifacts.
- Do not leak prompt payloads containing reference answers.
- Do not compare Qwen and Codex unless both manifests have comparable model,
  backend, prompt, task, latency, token, fallback, and hardware fields.
- Do not report best-of-k as single-output repair success. Best-of-candidates
  pass@k is an upper-bound search result unless the selected output is the one
  being claimed and it is independently proven.
- Do not claim official FVEval reproduction unless the official metric and
  commercial equivalence flow are reproduced.
- Keep expected benchmark metadata separate from observed Jasper evidence.
- Keep `not_flagged_vacuous` or `non_vacuous_proven` wording bounded unless an
  explicit independent vacuity certificate is generated.

## Lane-Specific Merge Criteria

### SVA Repair Ablation Moore Proof

Before merge, the PR should include:

- The exact handoff artifact path and sha256.
- Variant-level candidate counts and proof outcomes.
- Candidate-level syntax/proof/vacuity outcomes.
- Case-level pass@1 and case-level best-of-candidates pass@k, reported
  separately.
- A clear distinction between local scaffold success, selected-output Jasper
  proof, and best-of-candidates Jasper proof.
- A vacuity caveat if Jasper 2018.09 cannot provide an explicit independent
  vacuity certificate.

### FVEval-Compatible Subset Evaluation

Before merge, the PR should include:

- Metrics separated across `NL2SVA-Human`, `NL2SVA-Machine`, and `Design2SVA`.
- Confirmation that reference answers remain evaluation metadata only and are
  not included in prompt payloads.
- A limitation statement that this is not official FVEval reproduction.
- A limitation statement that no commercial property-equivalence flow is
  reproduced unless one is actually implemented.
- A limitation statement that Design2SVA exact/reference match is not functional
  equivalence.

### Qwen Local Bring-Up

Before merge, the PR should include:

- `LOCAL_ONLY=true`.
- Cloud fallback disabled and not called.
- Backend/model/quantization/GPU/VRAM/context/latency manifest fields.
- 3+3+3 subset metrics if the local endpoint is healthy.
- An explicit readiness blocker report if the endpoint remains unavailable.
- No Qwen-vs-Codex quality or cost conclusion.

## Current Gate Decision

The second-wave queue is clean. The next preferred merge order is:

1. SVA repair ablation Moore proof.
2. FVEval-compatible subset evaluation.
3. Qwen local bring-up, or a Qwen readiness blocker report if local serving is
   still unavailable.
4. A fresh Stage 4 second-wave closeout report after the above lanes finish.

This gate PR itself can merge once local checks and CI pass, because it is
report-only and does not change code behavior.

## Validation Plan

This branch should pass:

| Command | Expected result |
| --- | --- |
| `python -m pytest -q` | Pass |
| `python -m ruff check .` | Pass |
| `git diff --check` | Pass |

