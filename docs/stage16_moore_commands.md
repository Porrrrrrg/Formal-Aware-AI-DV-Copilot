# Stage 16 Moore/JasperGold Commands

These commands replay exact expanded Codex Design2SVA candidates through the
repaired wrapper path. They do not send new LLM prompts. Run them only after
`evaluation/results/design2sva_eval_codex_expanded_subset.json` contains the
approved 12-case, k=3 real Codex generation result.

```bash
source /vol/eecs391/cadence.env
export JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg

python3.11 evaluation/run_design2sva_eval.py \
  --limit 12 \
  --k 3 \
  --replay evaluation/results/design2sva_eval_codex_expanded_subset.json \
  --jasper-check \
  --debug-artifacts \
  --out evaluation/results/design2sva_eval_codex_expanded_jasper.json

python3.11 scripts/refresh_eval_results.py --allow-rebuild-packets
pytest -q
ruff check .
```

Measured output:

- `evaluation/results/design2sva_eval_codex_expanded_jasper.json`
- `formal_check_mode = "jasper"`
- `summary.formal_metrics_status = "measured"`
- `summary.proven@1 = 0.75`
- `summary.proven@k = 1.0`
- `summary.non_vacuous@k = 1.0`
- `summary.proven_non_vacuous@k = 1.0`
- `summary.syntax@k = 1.0`
- `summary.valid_json_rate = 1.0`
- `summary.fallback_rate = 0.0`
- `summary.hallucinated_signal_rate = 0.0`

The raw JasperGold report tree is not tracked because `jasper/reports/**` is
ignored. The tracked JSON is compacted; it keeps summary metrics, candidate SVA,
proof statuses, and artifact path pointers without embedding raw reports.
