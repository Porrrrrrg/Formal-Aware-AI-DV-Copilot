# JasperLoop-DV Replay Demo Script

This script demonstrates the JasperLoop-DV workflow contract with the existing
offline SVA repair replay fixture. It is for a local repository checkout and
does not require Codex, Qwen, JasperGold, Moore, network access, or a live model
run.

The demo uses:

- `examples/workflows/sva_repair_demo/demo_case.json`
- `examples/workflows/sva_repair_demo/replay_candidate.json`
- `examples/workflows/sva_repair_demo/verifier_outcome_sample.json`
- `jasperloop workflow repair` through the equivalent source-checkout command
  `python -m app.cli workflow repair`
- `scripts/run_e2e_demo.py` for bounded summary/report copies

## Setup

Run from the repository root. Use a clean output directory so the audience can
see only artifacts produced by this demo.

```powershell
Remove-Item -Recurse -Force artifacts/workflow-demo -ErrorAction SilentlyContinue
```

If the installed console entry point is available, the primary workflow command
is:

```powershell
jasperloop workflow repair `
  --case examples/workflows/sva_repair_demo/demo_case.json `
  --backend replay `
  --run-intent-alignment `
  --prepare-moore-handoff `
  --out-dir artifacts/workflow-demo `
  --dry-run
```

For an uninstalled source checkout, run the same CLI through Python:

```powershell
python -m app.cli workflow repair `
  --case examples/workflows/sva_repair_demo/demo_case.json `
  --backend replay `
  --run-intent-alignment `
  --prepare-moore-handoff `
  --out-dir artifacts/workflow-demo `
  --dry-run
```

Expected terminal output shape:

```json
{
  "manifest": ".../artifacts/workflow-demo/workflow_manifest.json",
  "report": ".../artifacts/workflow-demo/workflow_report.md",
  "dry_run": true,
  "blocked": false
}
```

Expected files:

```text
artifacts/workflow-demo/problem_spec_stub.json
artifacts/workflow-demo/repair_candidate.json
artifacts/workflow-demo/candidate_stub.json
artifacts/workflow-demo/moore_handoff_manifest.json
artifacts/workflow-demo/imported_verifier_outcome.json
artifacts/workflow-demo/intent_alignment_result.json
artifacts/workflow-demo/workflow_manifest.json
artifacts/workflow-demo/workflow_report.md
```

Expected key manifest fields:

```json
{
  "manifest_type": "WorkflowManifest",
  "workflow_type": "repair",
  "case_id": "demo_repair_arbiter_mutex_syntax",
  "backend": "replay",
  "status": "dry_run",
  "external_send_allowed": false,
  "cloud_fallback_called": false,
  "verifier_required": true
}
```

## 3-Minute Demo

Goal: show that JasperLoop-DV can execute the local repair workflow boundary
end to end with deterministic replay artifacts.

1. Open the fixture directory.

   ```powershell
   Get-ChildItem examples/workflows/sva_repair_demo
   ```

   Expected talking point: "This is a sanitized replay fixture. The candidate
   and verifier outcome are local JSON files, not live model or JasperGold
   output."

2. Show the problem and replay candidate.

   ```powershell
   Get-Content examples/workflows/sva_repair_demo/demo_case.json
   Get-Content examples/workflows/sva_repair_demo/replay_candidate.json
   ```

   Presenter says: "The broken assertion is missing the terminator. The replay
   candidate preserves the mutex intent and adds the missing semicolon."

3. Run the workflow.

   ```powershell
   python -m app.cli workflow repair `
     --case examples/workflows/sva_repair_demo/demo_case.json `
     --backend replay `
     --run-intent-alignment `
     --prepare-moore-handoff `
     --out-dir artifacts/workflow-demo `
     --dry-run
   ```

   Presenter says: "The workflow loads the case, selects the replay candidate,
   prepares a Moore handoff manifest, imports a sanitized verifier sample, runs
   static intent alignment, and emits a human-reviewable report."

4. Show the final report and manifest.

   ```powershell
   Get-Content artifacts/workflow-demo/workflow_report.md
   Get-Content artifacts/workflow-demo/workflow_manifest.json
   ```

   Expected talking point: "The important evidence is not a score. It is the
   manifest: backend `replay`, dry-run `true`, external send disabled, cloud
   fallback not called, and a final report path for review."

5. Close with the boundary.

   Presenter says: "This demo proves the offline workflow wiring and artifact
   boundaries. It does not prove real model performance, production readiness,
   or a new formal proof."

## 8-Minute Demo

Goal: show each artifact in the replay workflow and why it exists.

1. Start with the fixture README.

   ```powershell
   Get-Content examples/workflows/sva_repair_demo/README.md
   ```

   Presenter says: "The fixture is intentionally small and sanitized. It is
   designed to run without Codex, Qwen, JasperGold, Moore, network access, or
   benchmark label changes."

2. Inspect the case.

   ```powershell
   Get-Content examples/workflows/sva_repair_demo/demo_case.json
   ```

   Talking points:

   - Case ID: `demo_repair_arbiter_mutex_syntax`
   - Intent: the arbiter must never grant both clients in the same cycle.
   - Broken SVA lacks the final semicolon.
   - `replay_candidate_path` and `verifier_outcome_path` point to local files.

3. Inspect the replay candidate.

   ```powershell
   Get-Content examples/workflows/sva_repair_demo/replay_candidate.json
   ```

   Presenter says: "This is deterministic replay input. Do not describe it as a
   model generation during the demo."

4. Inspect the verifier import sample.

   ```powershell
   Get-Content examples/workflows/sva_repair_demo/verifier_outcome_sample.json
   ```

   Expected fields to call out:

   - `manifest_type`: `VerifierOutcomeSample`
   - `status`: `proved_sample_imported`
   - `jaspergold_invoked`: `false`
   - `moore_invoked`: `false`
   - `raw_logs_included`: `false`
   - `claim_boundary`: mocked verifier import only

5. Run the workflow command.

   ```powershell
   python -m app.cli workflow repair `
     --case examples/workflows/sva_repair_demo/demo_case.json `
     --backend replay `
     --run-intent-alignment `
     --prepare-moore-handoff `
     --out-dir artifacts/workflow-demo `
     --dry-run
   ```

   Expected stdout:

   ```json
   {
     "manifest": ".../artifacts/workflow-demo/workflow_manifest.json",
     "report": ".../artifacts/workflow-demo/workflow_report.md",
     "dry_run": true,
     "blocked": false
   }
   ```

6. Show the artifact set.

   ```powershell
   Get-ChildItem artifacts/workflow-demo
   ```

   Expected artifact names:

   - `problem_spec_stub.json`
   - `repair_candidate.json`
   - `candidate_stub.json`
   - `moore_handoff_manifest.json`
   - `imported_verifier_outcome.json`
   - `intent_alignment_result.json`
   - `workflow_manifest.json`
   - `workflow_report.md`

7. Show the Moore handoff boundary.

   ```powershell
   Get-Content artifacts/workflow-demo/moore_handoff_manifest.json
   ```

   Presenter says: "This prepares the boundary for a future Moore-side
   verification. It does not run Moore, JasperGold, or any TCL script."

8. Show intent alignment.

   ```powershell
   Get-Content artifacts/workflow-demo/intent_alignment_result.json
   ```

   Expected fields:

   - `alignment_label`: usually `likely_aligned`
   - `manual_review_required`: `true`
   - `proof_status_context.status`: `proved_sample_imported`
   - Rationale includes that proof/status context does not imply intent
     alignment.

9. Show the human-reviewable report.

   ```powershell
   Get-Content artifacts/workflow-demo/workflow_report.md
   ```

   Presenter says: "This report is intentionally conservative. It records the
   claim boundary, imported verifier context, intent alignment path, and steps
   executed."

10. Optional: run the packaged E2E summary helper.

    ```powershell
    python scripts/run_e2e_demo.py
    ```

    Expected stdout shape:

    ```json
    {
      "summary": ".../reports/workflows/e2e_demo_summary_<timestamp>.md",
      "manifest": ".../reports/workflows/e2e_demo_manifest_<timestamp>.json"
    }
    ```

    Presenter says: "The helper runs the same replay workflow and writes a
    bounded summary manifest for reviewers. It still does not call external
    services."

## Full Technical Walkthrough

The repair workflow is a manifest-driven orchestration path. The demo command
executes these local steps:

1. Load `demo_case.json` as repair case metadata.
2. Write a typed `problem_spec_stub.json`.
3. Choose the `replay` backend route.
4. Load `replay_candidate.json` and write `repair_candidate.json`.
5. Write `candidate_stub.json` as a typed candidate record.
6. Write `moore_handoff_manifest.json` because `--prepare-moore-handoff` is set.
7. Import `verifier_outcome_sample.json` into `imported_verifier_outcome.json`.
8. Run static intent alignment because `--run-intent-alignment` is set and the
   case has intent, reference SVA, candidate SVA, property ID, and signal
   metadata.
9. Emit `workflow_report.md`.
10. Emit `workflow_manifest.json`.

Use this command to inspect the recorded steps:

```powershell
python -c "import json; m=json.load(open('artifacts/workflow-demo/workflow_manifest.json')); print('\n'.join(m['steps_executed']))"
```

Expected steps:

```text
load_repair_case_metadata
prepare_problem_spec_stub
choose_backend_route
prepare_candidate_stub_or_replay_candidate
prepare_moore_handoff_manifest_if_requested
import_verifier_outcome_if_available
run_intent_alignment_if_requested_and_available
emit_final_workflow_report
emit_workflow_manifest
```

Use this command to verify the external-call boundary:

```powershell
python -c "import json; m=json.load(open('artifacts/workflow-demo/workflow_manifest.json')); print(m['backend'], m['dry_run'], m['external_send_allowed'], m['cloud_fallback_called'])"
```

Expected output:

```text
replay True False False
```

Use this command to verify verifier and intent-alignment references:

```powershell
python -c "import json; m=json.load(open('artifacts/workflow-demo/workflow_manifest.json')); print(bool(m['verifier_outcome_ref']), bool(m['intent_alignment_ref']), bool(m['final_report_ref']))"
```

Expected output:

```text
True True True
```

Use this command to inspect the replayed candidate:

```powershell
Get-Content artifacts/workflow-demo/repair_candidate.json
```

Expected content:

```json
{
  "explanation": "Replays the known repair by preserving the mutex intent and adding the missing assertion terminator.",
  "property_id": "p_mutex",
  "sva": "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));"
}
```

Use this command to inspect the final report sections:

```powershell
Select-String -Path artifacts/workflow-demo/workflow_report.md -Pattern "Claim Boundary|Imported Verifier Context|Intent Alignment|Steps Executed"
```

Expected sections:

```text
## Claim Boundary
## Imported Verifier Context
## Intent Alignment
## Steps Executed
```

## Presenter Talking Points

- "JasperLoop-DV separates workflow orchestration from external execution."
- "This replay demo validates the local artifact chain: case, candidate,
  handoff manifest, verifier import, intent alignment, manifest, and report."
- "The replay backend is deterministic and offline. That makes the demo
  reproducible, but it also means it is not evidence of model quality."
- "The Moore handoff manifest is a boundary artifact. It records what a future
  Moore-side verification would consume, but it does not run Moore."
- "The verifier outcome is imported sample context. It is not a new JasperGold
  result."
- "Intent alignment is a static review aid. It can flag semantic risk, but it
  is not a formal proof and it does not replace human review."
- "The final workflow report is human-reviewable and includes the claim
  boundary by design."

## Troubleshooting

- `python: No module named app`: run the command from the repository root.
- `jasperloop: command not found`: use `python -m app.cli workflow repair ...`
  from the source checkout, or install the package in an environment where the
  console script is intended to be available.
- `case id not found` or file not found: check that
  `examples/workflows/sva_repair_demo/demo_case.json` exists and that the
  command is run from the repo root.
- No `intent_alignment_result.json`: confirm `--run-intent-alignment` is present
  and the case contains `intent`, `property_id`, `reference_sva`, `signals`, and
  a candidate SVA.
- No `moore_handoff_manifest.json`: confirm `--prepare-moore-handoff` is
  present.
- `blocked: true` with `backend=codex`: this demo should not use `backend=codex`.
  Use `--backend replay`.
- Output paths differ from the examples: that is expected when `--out-dir` uses
  an absolute path or a different directory. The artifact names and manifest
  fields should still match.
- Reports under `reports/workflows` change only when running
  `python scripts/run_e2e_demo.py`. The direct workflow command writes only to
  the selected `--out-dir`.

## What Not To Claim

- Do not claim this is real model performance.
- Do not claim Codex, Qwen, or any other model generated the replay candidate
  during the demo.
- Do not claim JasperGold or Moore ran live.
- Do not claim a new proof, new vacuity result, or production signoff.
- Do not claim intent alignment is formal equivalence.
- Do not claim proof status implies semantic intent alignment.
- Do not claim best-of-k results are single-output repair success.
- Do not claim benchmark labels, historical reports, schemas, or prior result
  semantics were changed by this demo.
- Do not claim the demo uses network access or cloud fallback.
