# Codex Repair Output Restore Summary

Run UTC: 2026-05-11T03:56:13Z
Run ID: `codex_repair_output_restore_20260511T035613Z`

## Outcome

Regenerated the SVA repair task only. Triage, coverage, JasperGold, and formal proof validation were not run.

## Artifacts

| Artifact | Rows/Cases | SHA256 | Bytes |
| --- | ---: | --- | ---: |
| `reports/repair/artifacts/codex_repair_outputs_20260511T035613Z.jsonl` | 34 rows / 18 cases | `DB469CDAAAECF06953260CFFB1BD6EAA24A7B76E66F2CD56A4CAE44F8DBDBD9B` | 27588 |
| `evaluation/results/sva_repair_codex_restore.json` (ignored, not committed) | raw runner JSON | `305C66B5FBD6AE7631EEAB0D4261DC5273D5068D6CE1CA8E1EFDAB052C6795CB` | 85808 |

## Rerun Metrics

- Repair cases represented: 18/18
- LLM repair outputs exported: 34
- Source counts: {"llm": 34}
- Scaffold repair success: 0.5555555555555556 (10/18 cases)
- Final exact match: 0.5555555555555556
- Fallback rate: 0.0
- LLM error count: 0
- Formal proof success: not claimed; no JasperGold final proof was run.

## Command

```powershell
python scripts/run_codex_llm_eval.py --task sva_repair --limit 999 --out evaluation/results/sva_repair_codex_restore.json --acknowledge-external-send
```

## Sanitization

The committed JSONL includes case identifiers, original broken SVA, Codex repaired SVA candidates, referenced allowed signals, routing metadata, attempt indices, and scaffold metrics. It omits raw prompt text, natural-language repair explanations, verbose CLI traces, and local tool/license output.
