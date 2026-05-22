# JasperGold Environment

JasperLoop-DV expects JasperGold to be provided by the runtime environment. The repository does not require a host-specific path.

Set these variables when needed:

```bash
export JASPER_BIN=/path/to/jg
export PYTHON_BIN=python3.11
```

If the Cadence installation requires an environment script, either source it before running commands or set:

```bash
export JASPER_ENV=/path/to/cadence.env
```

Generic wrappers:

```bash
bash scripts/run_jasper_smoke.sh
bash scripts/run_jasper_sva_eval.sh
bash scripts/run_jasper_sva_repair_eval.sh
```

The wrappers keep raw reports under `jasper/reports/`, which is local-only by default.
