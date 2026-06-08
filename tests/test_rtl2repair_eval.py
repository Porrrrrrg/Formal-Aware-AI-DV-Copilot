from __future__ import annotations

import json
from pathlib import Path

from evaluation.run_rtl2repair_eval import main


def write_rtl(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
module tiny_arb(
  input logic clk,
  input logic rst,
  input logic req0,
  input logic req1,
  output logic gnt0,
  output logic gnt1
);
  assign gnt0 = req0;
  assign gnt1 = req1;
endmodule
""",
        encoding="utf-8",
    )
    return path


def test_rtl2repair_dry_run_emits_json_and_markdown(tmp_path: Path) -> None:
    rtl = write_rtl(tmp_path / "rtl" / "tiny_arb.sv")
    out = tmp_path / "run" / "rtl2repair_eval.json"

    assert main(
        [
            "--rtl",
            str(rtl),
            "--top",
            "tiny_arb",
            "--clock",
            "clk",
            "--reset",
            "rst",
            "--reset-polarity",
            "active_high",
            "--intent",
            "The arbiter must never grant both clients in the same cycle.",
            "--k",
            "2",
            "--max-sva-rounds",
            "1",
            "--max-rtl-rounds",
            "0",
            "--dry-run",
            "--out",
            str(out),
        ]
    ) == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "rtl2repair_eval_v1"
    assert payload["formal_metrics_status"] == "not_run"
    assert len(payload["generated_sva_candidates"]) == 2
    assert Path(payload["markdown_report"]).is_file()
    assert payload["metrics"]["formal_metrics_status"] == "not_run"


def test_rtl2repair_missing_jasper_reports_blocked(tmp_path: Path, monkeypatch) -> None:
    rtl = write_rtl(tmp_path / "rtl" / "tiny_arb.sv")
    out = tmp_path / "run" / "rtl2repair_eval.json"
    monkeypatch.setenv("JASPER_BIN", "definitely_missing_jasper_binary")

    assert main(
        [
            "--rtl",
            str(rtl),
            "--top",
            "tiny_arb",
            "--clock",
            "clk",
            "--reset",
            "rst",
            "--reset-polarity",
            "active_high",
            "--intent",
            "The arbiter must never grant both clients in the same cycle.",
            "--k",
            "1",
            "--max-sva-rounds",
            "0",
            "--max-rtl-rounds",
            "0",
            "--jasper-check",
            "--out",
            str(out),
        ]
    ) == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["formal_metrics_status"] == "blocked"
    first_round = payload["generated_sva_candidates"][0]["rounds"][0]
    assert "Cannot find JasperGold executable" in first_round["check_result"]["feedback"]
