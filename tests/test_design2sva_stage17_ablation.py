from __future__ import annotations

import json
from pathlib import Path

from evaluation.run_design2sva_ablation import METRIC_KEYS, main


def test_stage17_ablation_summary_uses_existing_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "summary.json"
    markdown = tmp_path / "summary.md"

    assert main(["--out", str(out), "--markdown", str(markdown)]) == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    rows = {row["row_id"]: row for row in payload["rows"]}

    assert payload["schema_version"] == "stage17_design2sva_ablation_v1"
    assert payload["llm_prompts_sent"] is False
    assert payload["metric_keys"] == METRIC_KEYS
    assert {
        "reference_oracle",
        "native_oracle",
        "codex_design2sva_current",
        "codex_fixed_wrapper_rerun",
        "codex_antivacuity_current",
        "deterministic_scaffold",
        "replay_baseline",
        "direct_prompt_placeholder",
        "no_retrieval_placeholder",
        "no_antivacuity_placeholder",
    } <= set(rows)

    current = rows["codex_design2sva_current"]
    assert current["status"] == "missing_artifact"
    assert current["metrics"]["cases"] == "not_run"
    assert current["metrics"]["proven@1"] == "not_run"
    assert current["metrics"]["proven_non_vacuous@k"] == "not_run"
    assert current["llm_prompts_sent"] is False

    placeholder = rows["direct_prompt_placeholder"]
    assert placeholder["status"] == "not_run"
    assert placeholder["metrics"]["proven@k"] == "not_run"
    assert placeholder["command_to_measure"]

    assert "No production signoff" in markdown.read_text(encoding="utf-8")


def test_stage17_ablation_variant_placeholder_is_not_zero(tmp_path: Path) -> None:
    out = tmp_path / "placeholder.json"
    markdown = tmp_path / "placeholder.md"

    assert (
        main(
            [
                "--variant",
                "no_retrieval_placeholder",
                "--out",
                str(out),
                "--markdown",
                str(markdown),
            ]
        )
        == 0
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert [row["row_id"] for row in payload["rows"]] == ["no_retrieval_placeholder"]
    row = payload["rows"][0]
    assert row["status"] == "not_run"
    assert set(row["metrics"]) == set(METRIC_KEYS)
    assert all(value == "not_run" for value in row["metrics"].values())
    assert payload["external_llm_commands"][0]["gated"] is True
