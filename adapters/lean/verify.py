#!/usr/bin/env python3
"""CLI entry point for the Lean adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.artifacts import make_attempt_id, make_candidate_id, make_problem_id, make_run_id  # noqa: E402
from app.models.core import Candidate, ProblemSpec, ToolName  # noqa: E402
from adapters.lean.adapter import LeanAdapter  # noqa: E402
from adapters.common import git_sha  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, help="Lean file to verify. Reads stdin if omitted.")
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--problem-id")
    parser.add_argument("--run-id")
    parser.add_argument("--attempt-id", default=make_attempt_id(1))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--strict-exit", action="store_true")
    args = parser.parse_args()

    content = args.candidate.read_text(encoding="utf-8") if args.candidate else sys.stdin.read()
    problem_id = args.problem_id or make_problem_id(ToolName.LEAN, content)
    run_id = args.run_id or make_run_id(git_sha())
    problem = ProblemSpec(
        problem_id=problem_id,
        tool=ToolName.LEAN,
        language="lean",
        statement=content,
    )
    candidate = Candidate(
        candidate_id=make_candidate_id(args.attempt_id, "cli", content),
        run_id=run_id,
        problem_id=problem_id,
        attempt_id=args.attempt_id,
        producer="cli",
        content=content,
    )
    outcome = LeanAdapter(artifact_root=args.artifact_root, timeout_s=args.timeout).verify(
        problem,
        candidate,
    )
    print(json.dumps(outcome.model_dump(mode="json"), indent=2))
    return 0 if outcome.ok or not args.strict_exit else 1


if __name__ == "__main__":
    raise SystemExit(main())
