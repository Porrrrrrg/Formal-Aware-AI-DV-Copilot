# JasperLoop CLI Usage

Stage 5A adds a unified user-facing CLI named `jasperloop`. It is a thin wrapper
around existing JasperLoop-DV scripts and runners. This stage records manifests
and planned internal commands only; it does not run new experiments or change
Stage 2, Stage 3, or Stage 4 reports.

## Commands

```bash
jasperloop --help
jasperloop build-packet --dry-run --out-dir artifacts/jasperloop_cli/build-packet
jasperloop repair --dry-run --out-dir artifacts/jasperloop_cli/repair
jasperloop triage --dry-run --out-dir artifacts/jasperloop_cli/triage
jasperloop coverage --dry-run --out-dir artifacts/jasperloop_cli/coverage
jasperloop eval --dry-run --out-dir artifacts/jasperloop_cli/eval
jasperloop moore-handoff --dry-run --out-dir artifacts/jasperloop_cli/moore-handoff
```

Each command supports `--dry-run` and `--out-dir`. The Stage 5A implementation
keeps external execution disabled by default and does not provide a flag to
enable model, JasperGold, or Moore execution.

## Dry-Run Safety

Dry-run mode writes manifests and planned runner metadata without invoking the
planned runner. The CLI never calls Codex, Qwen, JasperGold, Moore, or a cloud
model. The `external_calls_allowed` field is always `false`.

The planned internal runners are:

| CLI command | Planned internal runner |
| --- | --- |
| `build-packet` | `scripts/build_all_evidence_packets.py` |
| `repair` | `evaluation/run_sva_repair_eval.py --jasper-dry-run` |
| `triage` | `evaluation/run_agent_eval.py --systems structured` |
| `coverage` | `evaluation/run_coverage_eval.py --systems structured` |
| `eval` | `evaluation/run_fveval_subset.py` |
| `moore-handoff` | `scripts/run_moore_codex_repair_final_proof.sh --dry-run` |

## Output Manifests

Each command writes these JSON files under `--out-dir`:

- `jasperloop_run_manifest.json`: Stage 5A manifest with top-level CLI fields.
- `core_run_manifest.json`: canonical typed-IR `RunManifest`.
- `core_artifact_manifest.json`: canonical typed-IR `ArtifactManifest`.

The Stage 5A manifest includes `git_sha`, `command`, `subcommand`, `dry_run`,
`created_at_utc`, `out_dir`, `external_calls_allowed`, `evidence_type`,
`claim_boundary`, and the planned internal runner/command.

## Stage 4 Claim Boundary

The CLI is wrapper evidence only. It does not update benchmark labels, result
schemas, Stage 2/3/4 reports, or prior result semantics. Any future command that
enables external execution must add an explicit gate and tests covering that
gate before model, JasperGold, Moore, or cloud calls are allowed.
