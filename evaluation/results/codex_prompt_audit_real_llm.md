# Codex Prompt Audit for Real LLM Gate

Command:

```bash
python scripts/export_codex_prompts.py --task all --limit 3 --summary-only
```

The audit used summary-only mode. Raw prompts were not written to tracked files.

| Metric | Value |
| --- | ---: |
| Prompt samples | 9 |
| Approx tokens | 11341 |
| Max prompt chars | 7971 |
| Samples with gold labels | 0 |
| Samples with RTL context | 0 |
| Samples with JasperGold evidence | 9 |

Prompt checks:

- JSON-only output is required by the Codex adapter wrapper and reinforced in task prompts.
- Triage and coverage prompts now explicitly name allowed label/action sets through schema references and prompt text.
- Signal-use constraints are explicit: do not invent signals, and suspect signals must come from supplied signal maps, counterexample changed signals, coverage related signals, or allowed signal lists.
- No host-specific project-identity wording was found in prompt templates.
- No raw prompt files were promoted to git.

This audit approves only the small subset gate. It does not establish Codex benchmark performance.
