# Real Jasper Evidence Blocker - 2026-05-11T00:27:48Z

## Scope

Requested worktree: `D:\AI-DV\jl-real-jasper-evidence`

Requested branch: `stage/real-jasper-evidence`

Expected base: `origin/main` at `a8b476665337829d1a952385c5b9dca989843115`

## Verified

- `git rev-parse HEAD`
  - Result: `a8b476665337829d1a952385c5b9dca989843115`
- `git status --short --branch`
  - Result: `## stage/real-jasper-evidence...origin/main`
- `python -m pytest -q`
  - Result: `65 passed in 3.54s`
- `python -m ruff check .`
  - Result: `All checks passed!`
- `python --version`
  - Result: `Python 3.11.9`

## Blocker

The requested Jasper commands require a Unix/Moore environment with Cadence/JasperGold available through `/vol/eecs391/cadence.env`. This environment is Windows and does not expose that file or the JasperGold binaries.

Commands checked:

- `Test-Path -LiteralPath '/vol/eecs391/cadence.env'`
  - Result: `False`
- `Get-Command jaspergold -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source`
  - Result: no command found
- `Get-Command jg -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source`
  - Result: no command found
- `wsl.exe -e sh -lc "test -f /vol/eecs391/cadence.env && echo FOUND || echo MISSING"`
  - Result: `MISSING`
- `wsl.exe -e sh -lc "command -v jaspergold || command -v jg || true"`
  - Result: no command found
- `wsl.exe -e sh -lc "uname -a"`
  - Result: `Linux Cyporg 6.6.114.1-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Mon Dec  1 20:46:23 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux`
- `$env:OS; [System.Environment]::OSVersion.VersionString`
  - Result: `Windows_NT`, `Microsoft Windows NT 10.0.26200.0`

## Commands Not Run

The following requested commands were not run because the required Cadence/JasperGold environment is unavailable:

- `source /vol/eecs391/cadence.env`
- `python3.11 scripts/build_all_evidence_packets.py`
- `bash scripts/run_moore_sva_eval.sh`
- `bash scripts/run_moore_sva_repair_eval.sh`

## Required Next Environment

Run the Jasper evidence workflow on Moore, or another Unix environment where `/vol/eecs391/cadence.env` exists and provides Cadence/JasperGold on PATH. After sourcing that environment, rerun the requested evidence packet and SVA evaluation commands and validate generated packets against `copilot/schemas/evidence_packet.schema.json`.

No Jasper evidence packets, Jasper summaries, model outputs, raw Jasper logs, trace directories, or tool/license outputs were generated in this blocked run.
