from __future__ import annotations

import json
from pathlib import Path

from copilot.agents.design2sva_agent import build_prompt
from evaluation.run_design2sva_eval import load_cases, main

def test_design2sva_prompt_omits_reference_sva() -> None:
    case = load_cases(Path("benchmarks/design2sva_cases.json"))[0]
    context = {"visible_signals": case["visible_signals"], "interface": {"ports": []}}

    prompt = build_prompt(case, context)

    assert case["evaluation_metadata"]["reference_sva"] not in prompt
    assert "expected_proof_status" not in prompt
    assert "reference_sva" not in prompt


def test_design2sva_dry_run_pass_at_k(tmp_path, monkeypatch) -> None:
    out = tmp_path / "design2sva.json"
    markdown = tmp_path / "design2sva.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_eval.py",
            "--limit",
            "3",
            "--k",
            "3",
            "--dry-run",
            "--out",
            str(out),
            "--markdown",
            str(markdown),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]
    assert summary["num_cases"] == 3
    assert summary["k"] == 3
    assert summary["syntax@1"] == 1.0
    assert summary["syntax@k"] == 1.0
    assert summary["valid_json_rate"] == 1.0
    assert summary["fallback_rate"] == 1.0
    assert summary["hallucinated_signal_rate"] == 0.0
    assert summary["formal_metrics_status"] == "not_run"
    assert markdown.exists()


def test_design2sva_replay_source_counts(tmp_path, monkeypatch) -> None:
    out = tmp_path / "design2sva_replay.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_eval.py",
            "--limit",
            "3",
            "--k",
            "2",
            "--replay",
            "--out",
            str(out),
            "--markdown",
            str(tmp_path / "design2sva_replay.md"),
        ],
    )

    assert main() == 0
    summary = json.loads(out.read_text(encoding="utf-8"))["summary"]
    assert summary["source_counts"] == {"replay": 6}
    assert summary["fallback_rate"] == 0.0
