from __future__ import annotations

from evaluation.output_quality import classify_output_family, source_summary


def test_output_family_classification() -> None:
    rows = [
        {"system": "raw_log", "source": "raw_log_fallback"},
        {"system": "raw_log", "source": "llm"},
        {"system": "structured", "source": "llm"},
        {"system": "sva_repair", "source": "structured_fallback", "feedback_mode": "jasper"},
    ]

    assert [classify_output_family(row) for row in rows] == [
        "deterministic_fallback",
        "raw_log_llm",
        "structured_llm",
        "jasper_feedback_repair_loop",
    ]
    summary = source_summary(rows)
    assert summary["output_family_counts"]["deterministic_fallback"] == 1
    assert summary["output_family_counts"]["raw_log_llm"] == 1
    assert summary["output_family_counts"]["structured_llm"] == 1
    assert summary["output_family_counts"]["jasper_feedback_repair_loop"] == 1
