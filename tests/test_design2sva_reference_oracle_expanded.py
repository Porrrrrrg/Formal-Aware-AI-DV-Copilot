from __future__ import annotations

import json

from evaluation.run_design2sva_native_oracle import main


def test_expanded_reference_oracle_local_dry_run(tmp_path, monkeypatch) -> None:
    out = tmp_path / "expanded_reference_oracle.json"
    jasper_out_root = tmp_path / "wrapper_artifacts"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_native_oracle.py",
            "--expanded-local",
            "--limit",
            "4",
            "--out",
            str(out),
            "--jasper-out-root",
            str(jasper_out_root),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["mode"] == "design2sva_reference_oracle_expanded"
    assert payload["dry_run"] is True
    assert payload["llm_prompts_sent"] is False
    assert summary["num_cases"] == 4
    assert summary["native_mapped_cases"] == 4
    assert summary["native_all_cases_mapped"] is True
    assert summary["wrapper_cases"] == 4
    assert summary["clock_reset_metadata_checked"] == 4
    assert summary["reset_clock_mismatch_count"] == 0
    assert summary["invariant_reference_count"] >= 1
    assert summary["cover_generated_count"] == summary["cover_required_count"]
    assert summary["root_cause_summaries"] == []
    assert payload["result_artifact_paths"]["local"].endswith(
        "design2sva_reference_oracle_expanded_local.json"
    )
    assert payload["result_artifact_paths"]["jasper"].endswith(
        "design2sva_reference_oracle_expanded_jasper.json"
    )

    for result in payload["results"]:
        assert result["native"]["mapping_status"] == "mapped"
        wrapper = result["wrapper_reference"]
        assert wrapper["clock_reset_metadata"]["clock"]
        antecedent = wrapper["antecedent_metadata"]
        if antecedent["trigger_kind"] == "invariant":
            assert antecedent["cover_sva"] == ""
        else:
            assert antecedent["cover_sva"]
