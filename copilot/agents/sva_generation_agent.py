#!/usr/bin/env python3
"""Prompt assembly scaffold for SVA generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_prompt(packet: dict[str, object]) -> str:
    return (
        "Generate SystemVerilog Assertions from this structured evidence packet.\n\n"
        + json.dumps(packet, indent=2)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text())
    print(build_prompt(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
