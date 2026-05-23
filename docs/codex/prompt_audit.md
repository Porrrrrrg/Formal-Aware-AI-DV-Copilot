# Prompt Audit

Run prompt audit before any external LLM benchmark submission:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
```

Use preview files only for local review:

```bash
python scripts/export_codex_prompts.py --task sva_repair --limit 3 --out-dir artifacts/prompt_previews
```

For triage and coverage previews, use redaction unless full evidence is explicitly required:

```bash
python scripts/export_codex_prompts.py --task triage --limit 2 --redact-evidence --summary-only
```

Audit for local paths, raw logs, tool-license details, excessive trace size, and reference-answer leakage before approving external submission.
