"""Output-quality metrics shared by evaluation runners."""

from __future__ import annotations

import collections

from copilot.json_utils import coerce_string_list


def source_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    sources = [str(row.get("source") or "unknown") for row in rows]
    source_counts = dict(sorted(collections.Counter(sources).items()))
    total = len(rows)
    return {
        "source_counts": source_counts,
        "llm_success_rate": rate(rows, lambda row: row.get("source") == "llm"),
        "fallback_rate": rate(rows, lambda row: "fallback" in str(row.get("source", ""))),
        "llm_error_rate": rate(rows, lambda row: bool(row.get("llm_error"))),
        "llm_error_count": sum(1 for row in rows if row.get("llm_error")),
        "num_outputs": total,
    }


def hallucinated_signals(
    prediction: dict[str, object],
    packet: dict[str, object],
) -> list[str]:
    allowed = allowed_signal_names(packet)
    suspects = coerce_string_list(prediction.get("suspect_rtl_signals"))
    return sorted(signal for signal in suspects if signal and signal not in allowed)


def allowed_signal_names(packet: dict[str, object]) -> set[str]:
    allowed: set[str] = set()
    signal_role_map = packet.get("signal_role_map")
    if isinstance(signal_role_map, dict):
        allowed.update(str(signal) for signal in signal_role_map)

    cex = packet.get("counterexample_summary")
    if isinstance(cex, dict):
        allowed.update(coerce_string_list(cex.get("changed_signals")))

    coverage = packet.get("coverage_context")
    if isinstance(coverage, dict):
        allowed.update(coerce_string_list(coverage.get("related_signals")))

    coverage_evidence = packet.get("coverage_evidence")
    if isinstance(coverage_evidence, dict):
        allowed.update(coerce_string_list(coverage_evidence.get("related_signals")))
    return allowed


def rate(rows: list[dict[str, object]], predicate) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if predicate(row)) / len(rows)
