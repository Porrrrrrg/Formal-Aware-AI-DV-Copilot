from __future__ import annotations

import json

from scripts import refresh_eval_results
from tools.import_fveval_subset import load_fixture_rows, main as import_main, normalize_case


def test_fveval_importer_supports_subset_folder_layout(tmp_path, monkeypatch) -> None:
    human = tmp_path / "NL2SVA-Human"
    machine = tmp_path / "NL2SVA-Machine"
    design = tmp_path / "Design2SVA"
    human.mkdir()
    machine.mkdir()
    design.mkdir()
    (human / "human.json").write_text(
        json.dumps({"task_id": "h1", "instruction": "assert req implies grant", "signals": "clk,req,gnt"}),
        encoding="utf-8",
    )
    (machine / "machine.jsonl").write_text(
        json.dumps({"task_id": "m1", "prompt": "assert valid handshake", "allowed_signals": ["clk", "valid"]})
        + "\n",
        encoding="utf-8",
    )
    (design / "design.csv").write_text(
        "task_id,design_id,intent,allowed_signals\n"
        "d1,arbiter_rr2,generate mutex assertion,\"clk;rst;gnt0;gnt1\"\n",
        encoding="utf-8",
    )

    rows = load_fixture_rows(tmp_path)
    assert [row["subset"] for row in rows] == ["Design2SVA", "NL2SVA-Human", "NL2SVA-Machine"]
    normalized = [normalize_case(row, index, tmp_path) for index, row in enumerate(rows)]
    assert {case["task_family"] for case in normalized} == {"design2sva", "nl2sva"}

    out = tmp_path / "imported.json"
    monkeypatch.setattr(
        "sys.argv",
        ["import_fveval_subset.py", "--source-dir", str(tmp_path), "--out", str(out)],
    )
    assert import_main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload) == 3
    assert {case["subset"] for case in payload} == {"NL2SVA-Human", "NL2SVA-Machine", "Design2SVA"}


def test_refresh_eval_results_writes_design2sva_markdown_when_json_exists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(refresh_eval_results, "RESULTS", tmp_path)
    (tmp_path / "design2sva_eval_local.json").write_text(
        json.dumps(
            {
                "mode": "deterministic_scaffold",
                "summary": {
                    "num_cases": 3,
                    "k": 3,
                    "syntax@1": 1.0,
                    "syntax@k": 1.0,
                    "proven@1": 0.0,
                    "proven@k": 0.0,
                    "non_vacuous@k": 0.0,
                    "hallucinated_signal_rate": 0.0,
                    "fallback_rate": 1.0,
                    "valid_json_rate": 1.0,
                    "average_rounds": 0.0,
                    "repair_success_after_feedback": 0.0,
                    "source_counts": {"structured_fallback": 9},
                    "failure_categories": {"passed": 9},
                    "formal_metrics_status": "not_run",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "design2sva_eval_codex_subset.json").write_text(
        json.dumps(
            {
                "mode": "llm",
                "summary": {
                    "num_cases": 3,
                    "k": 3,
                    "syntax@1": 1.0,
                    "syntax@k": 1.0,
                    "proven@1": 0.0,
                    "proven@k": 0.0,
                    "non_vacuous@k": 0.0,
                    "hallucinated_signal_rate": 0.0,
                    "fallback_rate": 0.0,
                    "valid_json_rate": 1.0,
                    "average_rounds": 1.0,
                    "repair_success_after_feedback": 1.0,
                    "source_counts": {"llm": 9},
                    "failure_categories": {"passed": 9, "temporal_mismatch": 9},
                    "formal_metrics_status": "not_run",
                },
            }
        ),
        encoding="utf-8",
    )

    refresh_eval_results.write_design2sva_results_if_present()

    markdown = (tmp_path / "design2sva_results.md").read_text(encoding="utf-8")
    assert "Design2SVA Results" in markdown
    assert "syntax@k" in markdown
    assert "structured_fallback=9" in markdown
    assert "design2sva_eval_codex_subset.json" in markdown
    assert "llm=9" in markdown
    assert "production signoff" in markdown
