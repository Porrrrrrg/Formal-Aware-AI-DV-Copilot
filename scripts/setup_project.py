#!/usr/bin/env python3
"""Print setup instructions for local and moore environments."""

from __future__ import annotations


def main() -> int:
    print("Local scaffold is ready.")
    print("On moore:")
    print("  source /vol/eecs391/cadence.env")
    print("  JASPER_BIN=/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg \\")
    print("    python3.11 tools/run_jasper.py --design arbiter_rr2 --variant correct --mode prove")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
