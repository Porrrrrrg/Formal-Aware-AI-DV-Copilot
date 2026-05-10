#!/usr/bin/env python3
"""CLI entry point for the cvc5 adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from adapters.smt.cvc5.adapter import CVC5Adapter  # noqa: E402
from core.schemas import Candidate, ProblemSpec  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, help="SMT2 file to verify. Reads stdin if omitted.")
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--expected", choices=["sat", "unsat", "unknown"])
    parser.add_argument("--problem-id", default="cvc5_cli_problem")
    parser.add_argument("--run-id", default="run_cvc5_cli")
    parser.add_argument("--attempt-id", default="attempt_0")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--strict-exit", action="store_true")
    args = parser.parse_args()

    content = args.candidate.read_text(encoding="utf-8") if args.candidate else sys.stdin.read()
    problem = ProblemSpec(
        problem_id=args.problem_id,
        tool="cvc5",
        language="smt2",
        statement="",
        metadata={"expect": args.expected} if args.expected else {},
    )
    candidate = Candidate(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        producer="cli",
        content=content,
    )
    outcome = CVC5Adapter(artifact_root=args.artifact_root, timeout_s=args.timeout).verify(
        problem,
        candidate,
    )
    print(json.dumps(outcome.to_dict(), indent=2))
    return 0 if outcome.ok or not args.strict_exit else 1


if __name__ == "__main__":
    raise SystemExit(main())
