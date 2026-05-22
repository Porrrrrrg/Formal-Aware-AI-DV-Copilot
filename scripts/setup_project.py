#!/usr/bin/env python3
"""Print setup instructions for local and JasperGold environments."""

from __future__ import annotations


def main() -> int:
    print("Local scaffold is ready.")
    print("With JasperGold available:")
    print("  export JASPER_BIN=/path/to/jg")
    print("  export PYTHON_BIN=python3.11")
    print("  bash scripts/run_jasper_smoke.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
