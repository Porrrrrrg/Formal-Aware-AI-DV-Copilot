# Expected Workflow Manifest Notes

The demo command emits `workflow_manifest.json` with:

- `manifest_type`: `WorkflowManifest`
- `workflow_type`: `repair`
- `backend`: `replay`
- `external_send_allowed`: `false`
- `cloud_fallback_called`: `false`
- `verifier_required`: `true` when `--prepare-moore-handoff` is used
- `verifier_outcome_ref`: populated from `verifier_outcome_sample.json`
- `intent_alignment_ref`: populated when `--run-intent-alignment` is used
- `artifact_refs`: includes problem context, replay candidate, Moore handoff
  manifest, imported verifier outcome, intent alignment output, and final report

The manifest is a workflow evidence record. It is not a production readiness
claim and it is not a formal proof certificate.
