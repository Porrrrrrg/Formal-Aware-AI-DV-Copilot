# SVA Repair End-to-End Demo Fixture

This directory contains a small sanitized replay fixture for the Stage 5F
JasperLoop workflow demo. It is designed to run without Codex, Qwen,
JasperGold, Moore, network access, or benchmark label changes.

Run from the repository root:

```bash
python -m app.cli workflow repair \
  --case examples/workflows/sva_repair_demo/demo_case.json \
  --backend replay \
  --run-intent-alignment \
  --prepare-moore-handoff \
  --out-dir artifacts/workflow-demo \
  --dry-run
```

The demo case references:

- `demo_case.json`: one representative SVA repair case with structured context.
- `replay_candidate.json`: a deterministic replay repair candidate.
- `verifier_outcome_sample.json`: a sanitized mocked verifier outcome import.
- `expected_workflow_manifest.schema-note.md`: field expectations for reviewers.

The verifier sample is not a new JasperGold run. It is a local artifact used to
exercise the import and review path.
