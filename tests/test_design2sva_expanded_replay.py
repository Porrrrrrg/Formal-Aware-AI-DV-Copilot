from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.run_design2sva_fixed_wrapper_rerun import (
    DEFAULT_ORIGINAL_SOURCE,
    main,
    missing_replay_cases,
)
from evaluation.run_design2sva_eval import load_cases
from copilot.agents.design2sva_agent import load_replay_records


def test_expanded_replay_reports_missing_candidates_without_fallback(tmp_path, monkeypatch) -> None:
    out = tmp_path / "expanded_replay.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_fixed_wrapper_rerun.py",
            "--only",
            "expanded-local",
            "--expanded-local-out",
            str(out),
            "--jasper-out-root",
            str(tmp_path / "jasper"),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    coverage = payload["replay_coverage"]
    summary = payload["summary"]

    assert payload["stage"] == "stage14_expanded_codex_replay"
    assert payload["mode"] == "committed_codex_expanded_replay"
    assert payload["llm_prompts_sent"] is False
    assert coverage["expanded_case_count"] >= 10
    assert coverage["evaluated_case_count"] == 3
    assert coverage["missing_case_count"] == coverage["expanded_case_count"] - 3
    assert coverage["fallback_used_for_missing_cases"] is False
    assert summary["source_counts"] == {"llm": 9}
    assert summary["fallback_rate"] == 0.0
    assert payload["result_artifact_paths"]["local"].endswith(
        "design2sva_codex_replay_expanded_local.json"
    )
    assert payload["result_artifact_paths"]["jasper"].endswith(
        "design2sva_codex_replay_expanded_jasper.json"
    )


def test_expanded_replay_strict_mode_lists_missing_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_fixed_wrapper_rerun.py",
            "--only",
            "expanded-local",
            "--require-expanded-candidates",
        ],
    )

    with pytest.raises(ValueError, match="missing candidates for expanded Design2SVA"):
        main()


def test_missing_replay_case_helper_uses_case_and_property() -> None:
    cases = load_cases(Path("benchmarks/design2sva_cases.json"))
    records = load_replay_records(Path(DEFAULT_ORIGINAL_SOURCE))
    assert records is not None

    missing = missing_replay_cases(cases, records)

    assert len(missing) == len(cases) - 3
    assert {"case_id", "property_id", "design_id"} <= set(missing[0])
