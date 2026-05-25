# JasperGold Environment

JasperGold checks require a shell where the Cadence/JasperGold environment is available.

Set either a direct executable:

```bash
export JASPER_BIN=/path/to/jg
```

or source the site-specific environment:

```bash
source /path/to/cadence_or_jasper_env.sh
```

Then run:

```bash
bash scripts/run_jasper_smoke.sh
bash scripts/run_jasper_sva_eval.sh
bash scripts/run_jasper_sva_repair_eval.sh
```

Raw outputs are written under ignored `jasper/reports/` paths. Commit only curated Markdown summaries when a real JasperGold run completed.
