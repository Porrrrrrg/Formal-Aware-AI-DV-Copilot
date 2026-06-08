from __future__ import annotations

import json
from pathlib import Path

from scripts import run_rtl2repair_llm_patch_subset as runner


ROOT = Path(__file__).resolve().parents[1]
SUBSET_MANIFEST = ROOT / "evaluation" / "fixtures" / "rtl2repair_llm_patch_subset.json"
RESULT_PLACEHOLDER = ROOT / "evaluation" / "results" / "rtl2repair_llm_patch_subset.md"


def test_subset_manifest_shape_and_regression_files_exist() -> None:
    manifest = runner.load_manifest(SUBSET_MANIFEST)

    assert manifest["schema_version"] == "rtl2repair_llm_patch_subset_v1"
    assert len(manifest["cases"]) == 3
    case_ids = {case["case_id"] for case in manifest["cases"]}
    assert case_ids == {
        "arbiter_rr2_bug_double_grant",
        "rv_buffer_bug_overwrite",
        "apb_regblock_bug_wrong_addr",
    }
    for case in manifest["cases"]:
        assert Path(ROOT / case["rtl_path"]).is_file()
        assert Path(ROOT / case["regression_candidates"]).is_file()
        stable_sva = case["stable_sva"]
        assert stable_sva["property_id"] == "p_rtl2repair_01"
        assert "assert property" in stable_sva["sva"]
        assert "real LLM" not in stable_sva.get("source", "")


def test_runner_dry_run_writes_planned_commands_without_external_llm(tmp_path: Path) -> None:
    out = tmp_path / "summary.json"

    assert runner.main(["--manifest", str(SUBSET_MANIFEST), "--dry-run", "--out", str(out)]) == 0

    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["dry_run"] is True
    assert summary["external_send_acknowledged"] is False
    assert len(summary["cases"]) == 3
    for case in summary["cases"]:
        assert case["status"] == "planned"
        assert case["patch_source"] == "real_llm_required_for_execution"
        command = case["command"]
        assert "--rtl-repair-llm" not in command
        assert "--regression-candidates" in command
        assert "--dry-run" in command


def test_runner_blocks_real_llm_without_acknowledgement(tmp_path: Path) -> None:
    out = tmp_path / "summary.json"

    try:
        runner.main(
            [
                "--manifest",
                str(SUBSET_MANIFEST),
                "--llm-command",
                "fake-json-backend",
                "--out",
                str(out),
            ]
        )
    except SystemExit as exc:
        assert "acknowledge" in str(exc).lower()
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("runner should block real LLM route without acknowledgement")


def test_llm_patch_subset_placeholder_does_not_fabricate_results() -> None:
    markdown = RESULT_PLACEHOLDER.read_text(encoding="utf-8")

    assert "Pending" in markdown
    assert "No real LLM RTL patch proposal run has been executed" in markdown
    assert "Passed on Moore" not in markdown
    assert "`true`" not in markdown
    assert "| Passed |" not in markdown
