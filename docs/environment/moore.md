# Moore Environment

Moore is one possible JasperGold host environment. It is not part of the project architecture, implementation identity, or repository structure.

Example:

```bash
ssh moore
cd /path/to/Formal-Aware-AI-DV-Copilot
source /vol/eecs391/cadence.env
export JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg
export PYTHON_BIN=python3.11
bash scripts/run_jasper_smoke.sh
```

After the environment is configured, use the generic `scripts/run_jasper_*.sh` scripts. Moore-specific paths should stay in this environment note or in local operator notes, not in the project architecture narrative.
