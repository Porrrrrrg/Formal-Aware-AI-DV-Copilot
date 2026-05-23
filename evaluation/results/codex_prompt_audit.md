# Codex Prompt Audit

Use this local-only command before any benchmark prompt is sent to Codex:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
```

The audit reports prompt count, character length, approximate token count, and whether the prompt includes gold labels, RTL context, or JasperGold evidence. Benchmark prompts should have `contains_gold_label=false`; triage and coverage prompts are expected to include JasperGold evidence, while SVA repair prompts include the broken assertion, allowed signals, and property intent.

## Local Audit Snapshot

Command:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
```

| Metric | Value |
| --- | ---: |
| Prompts | 9 |
| Max chars | 7088 |
| Approx total tokens | 10934 |
| Prompts with gold labels | 0 |
| Prompts with RTL context | 0 |
| Prompts with Jasper evidence | 9 |

With actual JasperGold report and trace packet fields present, packet previews are much larger. A 2-case-per-task preview had max prompt size around 66k characters. Codex subset runs should therefore use the wrapper default `--packet-source minimal` unless the experiment explicitly needs full report/trace evidence.

Redacted triage preview:

```bash
python scripts/export_codex_prompts.py --task triage --limit 2 --redact-evidence --summary-only
```

| Metric | Value |
| --- | ---: |
| Prompts | 2 |
| Max chars | 2055 |
| Approx total tokens | 1016 |
| Prompts with gold labels | 0 |
