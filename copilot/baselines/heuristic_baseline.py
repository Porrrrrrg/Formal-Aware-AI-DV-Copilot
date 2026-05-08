#!/usr/bin/env python3
"""Simple heuristic baseline for diagnosis cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ACTION_BY_ISSUE = {
    "rtl_design_bug": "fix_rtl",
    "assertion_property_bug": "fix_assertion_property",
    "assumption_constraint_bug": "fix_assumption_constraint",
    "testbench_stimulus_bug": "fix_testbench_or_stimulus",
    "reachable_coverage_gap": "add_directed_test_or_sequence",
    "unreachable_or_invalid_coverage_goal": "prove_unreachable_or_waive_coverage_goal",
}


def predict(case: dict[str, object]) -> dict[str, str]:
    text = json.dumps(case).lower()
    if "vacuous" in text or "overconstraint" in text:
        issue = "assumption_constraint_bug"
    elif "coverage" in text and "unreachable" in text:
        issue = "unreachable_or_invalid_coverage_goal"
    elif "coverage" in text:
        issue = "reachable_coverage_gap"
    elif "property" in text and "persistence" in text:
        issue = "assertion_property_bug"
    else:
        issue = "rtl_design_bug"
    return {"predicted_issue_type": issue, "recommended_next_action": ACTION_BY_ISSUE[issue]}


def main() -> int:
    path = Path(sys.argv[1])
    print(json.dumps(predict(json.loads(path.read_text())), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
