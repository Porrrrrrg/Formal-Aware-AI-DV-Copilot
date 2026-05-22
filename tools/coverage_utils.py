"""Coverage-plan helpers for evidence packets and closure evaluation."""

from __future__ import annotations

from pathlib import Path


def infer_coverage_plan_path(case_path: Path) -> Path | None:
    """Infer benchmarks/<design>/coverage/coverage_plan.yaml from a case path."""
    parts = list(case_path.resolve().parts)
    if "benchmarks" not in parts:
        return None
    index = parts.index("benchmarks")
    if len(parts) <= index + 1:
        return None
    design_dir = Path(*parts[: index + 2])
    candidate = design_dir / "coverage" / "coverage_plan.yaml"
    return candidate if candidate.exists() else None


def load_coverage_plan(path: Path | None) -> list[dict[str, object]]:
    """Parse the small coverage_plan.yaml format used by the local benchmarks."""
    if not path or not path.exists():
        return []

    goals: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line == "coverage_goals:":
            continue
        if line.startswith("- "):
            if current:
                goals.append(current)
            current = {}
            line = line[2:].strip()
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.strip()] = parse_scalar(value.strip())
    if current:
        goals.append(current)
    return goals


def parse_scalar(value: str) -> object:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        return value[1:-1]
    return value


def lookup_coverage_goal(goals: list[dict[str, object]], goal_id: object) -> dict[str, object]:
    goal_id = str(goal_id or "")
    for goal in goals:
        if str(goal.get("id", "")) == goal_id:
            return goal
    return {}


def enrich_coverage_context(case_path: Path, case: dict[str, object]) -> dict[str, object]:
    """Merge case coverage fields with the design coverage plan."""
    context = case.get("coverage_context", {})
    if case.get("task_type") != "coverage_closure" and not context:
        return {}
    coverage = dict(context) if isinstance(context, dict) else {}
    goal_id = coverage.get("coverage_goal") or case.get("property_id")
    coverage.setdefault("coverage_goal", goal_id)

    plan_path = infer_coverage_plan_path(case_path)
    plan_goal = lookup_coverage_goal(load_coverage_plan(plan_path), goal_id)
    if plan_goal:
        coverage.setdefault("intent", plan_goal.get("intent"))
        coverage.setdefault("expression", plan_goal.get("expression"))
        coverage.setdefault("expected_reachable", plan_goal.get("expected_reachable"))
        coverage["coverage_plan"] = str(plan_path) if plan_path else None

    if case.get("task_type") == "coverage_closure":
        coverage.setdefault("expected_test_hits", 0)
    return coverage


def build_coverage_evidence(
    coverage_context: dict[str, object],
    trace_summaries: list[dict[str, object]],
    property_results: list[dict[str, object]] | None = None,
    result_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    if not coverage_context:
        return {}

    witness_events: list[str] = []
    witness_depth = coverage_context.get("witness_depth")
    goal_id = coverage_context.get("coverage_goal")
    observed = observed_status_for_goal(goal_id, property_results or [], result_summary or {})
    for trace in sorted(
        trace_summaries,
        key=lambda item: (
            0
            if isinstance(item, dict)
            and goal_id
            and str(item.get("property_id") or "").endswith(str(goal_id))
            else 1
        ),
    ):
        if not isinstance(trace, dict):
            continue
        trace_events = trace.get("witness_events")
        if isinstance(trace_events, list) and trace_events:
            witness_events = [str(event) for event in trace_events[:8]]
            break
        summary = trace.get("summary")
        if not isinstance(summary, dict):
            continue
        if witness_depth is None and summary.get("fail_cycle") is not None:
            witness_depth = summary.get("fail_cycle")
        events = summary.get("semantic_events") or summary.get("events")
        if isinstance(events, list) and events:
            witness_events = [str(event) for event in events[:8]]
            break

    cover_status = str(observed.get("observed_cover_status") or coverage_context.get("expected_cover_status", "") or "").lower()
    expected = coverage_context.get("expected_reachable")
    if cover_status == "covered":
        closure_class = "already_covered"
    elif cover_status in {"reachable", "uncovered"} and expected is not False:
        closure_class = "reachable_coverage_gap"
    elif expected is False or cover_status == "unreachable":
        closure_class = "unreachable_or_invalid_coverage_goal"
    elif cover_status in {"undetermined", "syntax_error"}:
        closure_class = "stale_or_mismatched_evidence"
    else:
        closure_class = "unknown_coverage_status"

    return {
        "coverage_goal": goal_id,
        "intent": coverage_context.get("intent"),
        "expression": coverage_context.get("expression"),
        "expected_test_hits": coverage_context.get("expected_test_hits"),
        "expected_reachable": expected,
        "expected_cover_status": coverage_context.get("expected_cover_status"),
        "observed_cover_status": observed.get("observed_cover_status"),
        "observed_property_status": observed.get("observed_property_status"),
        "status_source": observed.get("status_source"),
        "closure_class": closure_class,
        "witness_depth": witness_depth,
        "witness_events": witness_events,
        "suggested_sequence": coverage_context.get("suggested_sequence", []),
        "related_signals": coverage_context.get("related_signals", []),
    }


def observed_status_for_goal(
    goal_id: object,
    property_results: list[dict[str, object]],
    result_summary: dict[str, object],
) -> dict[str, object]:
    goal = str(goal_id or "")
    if not goal:
        return {}
    for row in property_results:
        property_id = str(row.get("property_id") or "")
        if property_id == goal or property_id.endswith("." + goal) or goal in property_id:
            status = str(row.get("status") or "").lower()
            return {
                "observed_cover_status": status if status in {"covered", "uncovered", "unreachable", "undetermined", "syntax_error"} else None,
                "observed_property_status": status or None,
                "status_source": f"{row.get('result_file')}:{row.get('line')}",
            }

    for status_key in [
        "covered_properties",
        "uncovered_properties",
        "unreachable_properties",
        "undetermined_properties",
        "syntax_error_properties",
    ]:
        values = result_summary.get(status_key, [])
        if isinstance(values, list) and any(goal in str(value) for value in values):
            return {
                "observed_cover_status": status_key.removesuffix("_properties"),
                "observed_property_status": status_key.removesuffix("_properties"),
                "status_source": "summary",
            }
    return {}
