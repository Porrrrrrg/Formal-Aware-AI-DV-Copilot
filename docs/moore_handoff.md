# Moore Handoff Workflow

Stage 5B standardizes the local-to-Moore handoff path without running new
experiments locally. The `jasperloop moore-handoff` commands write sanitized
manifests, validate artifact boundaries, and import lightweight Moore summaries.
They do not call Codex, Qwen, JasperGold, or Moore.

## Local Prepare Workflow

Prepare a handoff manifest from a local checkout:

```bash
jasperloop moore-handoff prepare evidence-packets --dry-run --out-dir artifacts/moore_handoff/evidence
jasperloop moore-handoff prepare codex-repair-final-proof --dry-run --out-dir artifacts/moore_handoff/codex_final
jasperloop moore-handoff prepare sva-repair-ablation-proof --dry-run --out-dir artifacts/moore_handoff/ablation_final
```

Each command writes `handoff_manifest.json` with the current `git_sha`, branch,
task type, Moore command, expected lightweight outputs, forbidden raw outputs,
input artifact references, input artifact SHA-256 values, timestamp, and
generator name. Prompt text is not included.

## Moore Execution Workflow

Move or recreate the prepared manifest on Moore, check out the recorded commit,
and run only the `command_to_run_on_moore` recorded in the manifest. The command
is intended to produce lightweight JSON or Markdown summaries that can be
reviewed and imported later.

For Cadence setup on Moore, prefer a `tcsh` or `csh` shell invocation that
sources the environment before running JasperGold:

```bash
tcsh -fc 'source /vol/eecs391/cadence.env; setenv JASPER_BIN /vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg; bash scripts/run_moore_codex_repair_final_proof.sh --dry-run'
```

The local CLI does not run this command. It records the command so the Moore
operator can run it in the proper environment.

## Import Workflow

Validate a prepared handoff before import:

```bash
jasperloop moore-handoff validate --manifest artifacts/moore_handoff/codex_final/handoff_manifest.json --dry-run
```

Import a Moore-produced lightweight summary manifest:

```bash
jasperloop moore-handoff import-result --manifest reports/jasper/codex_repair_final_proof_manifest_moore.json --dry-run --out-dir reports/jasper
```

`import-result` parses the JSON, rejects forbidden raw artifact references, and
writes `moore_import_summary.json` plus `moore_import_artifact_manifest.json`.
The imported summary is intentionally narrow: it records source manifest hash,
git context, raw artifact policy, and selected lightweight summary fields.

## Raw Artifact Policy

Do not commit raw Jasper logs, trace directories, generated harness dumps,
license output, or large generated artifacts. Keep those under ignored Moore or
`jasper/reports/` run directories. Only import reviewed lightweight JSON
manifests and Markdown summaries into `reports/` or a chosen `--out-dir`.

Forbidden examples include:

- `*.log`
- `*.jou`
- `*.vcd`
- `*.fsdb`
- `*/trace/*`
- `*/traces/*`
- `*/jgproject/*`
- `*/generated_harness_dumps/*`
- `*/license*`

## Claim Boundary

Stage 5B is code and documentation only. It adds automation for sanitized
handoff manifests, validation, and import summaries. It does not add new
experimental results, modify benchmark labels, change Stage 2/3/4 reports, or
change prior result semantics.
