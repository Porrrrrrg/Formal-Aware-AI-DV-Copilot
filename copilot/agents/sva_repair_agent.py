#!/usr/bin/env python3
"""Prompt assembly scaffold for SVA repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_prompt(packet: dict[str, object], failed_sva: str) -> str:
    return (
        "Repair the following SVA using JasperGold feedback and structured context.\n\n"
        f"FAILED_SVA:\n{failed_sva}\n\n"
        "EVIDENCE_PACKET:\n"
        + json.dumps(packet, indent=2)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--failed-sva", required=True)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text())
    print(build_prompt(packet, args.failed_sva))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
