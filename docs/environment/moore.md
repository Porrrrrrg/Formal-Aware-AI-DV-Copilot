# Moore Environment

Moore is one possible JasperGold/Cadence host environment. It is not part of the project architecture, implementation identity, or repository structure.

Example setup on Moore:

```bash
ssh moore
cd /path/to/Formal-Aware-AI-DV-Copilot
source /vol/eecs391/cadence.env
export JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg
export PYTHON_BIN=python3.11
bash scripts/run_jasper_smoke.sh
```

Compatibility wrappers named `scripts/run_moore_*.sh` may remain for older notes, but they call the generic `run_jasper_*` scripts and print that Moore is only one possible JasperGold host.
