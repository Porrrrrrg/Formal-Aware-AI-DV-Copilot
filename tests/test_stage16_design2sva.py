from __future__ import annotations

import json
from pathlib import Path

from evaluation.run_design2sva_eval import main as run_design2sva_main
from scripts.export_codex_prompts import main as export_prompts_main
from scripts.run_codex_llm_eval import main as run_codex_main


def test_stage16_design2sva_prompt_audit_exports_without_gold(
    tmp_path: Path,
    monkeypatch,
) -> None:
    out_dir = tmp_path / "prompts"
    audit_md = tmp_path / "design2sva_expanded_prompt_audit.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "export_codex_prompts.py",
            "--task",
            "design2sva",
            "--design2sva-cases",
            "benchmarks/design2sva_cases.json",
            "--limit",
            "12",
            "--design2sva-context-budget",
            "24",
            "--out-dir",
            str(out_dir),
            "--audit-markdown",
            str(audit_md),
            "--require-no-gold-labels",
        ],
    )

    assert export_prompts_main() == 0
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))

    assert summary["num_prompts"] == 12
    assert summary["num_cases"] == 12
    assert summary["num_with_gold_label"] == 0
    assert summary["num_with_reference_sva_key"] == 0
    assert summary["num_with_reference_sva_value"] == 0
    assert summary["num_with_expected_proof_status"] == 0
    assert summary["num_with_jasper_evidence"] == 0
    assert audit_md.exists()
    assert "Gold labels absent | True" in audit_md.read_text(encoding="utf-8")
    assert len(list(out_dir.glob("design2sva_*.txt"))) == 12
    assert all(
        int(row["visible_signal_set_size"]) > 0
        for row in summary["prompts"]
        if row["task"] == "design2sva"
    )

    cases = json.loads(Path("benchmarks/design2sva_cases.json").read_text(encoding="utf-8"))
    prompts = {path.name: path.read_text(encoding="utf-8") for path in out_dir.glob("*.txt")}
    for index, case in enumerate(cases, start=1):
        prompt_id = f"design2sva_{index:03d}_{case['case_id']}.txt"
        prompt = prompts[prompt_id]
        assert "reference_sva" not in prompt
        assert "expected_proof_status" not in prompt
        assert case["evaluation_metadata"]["reference_sva"] not in prompt


def test_stage16_codex_design2sva_dry_run_documents_schema_command(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_codex_llm_eval.py",
            "--task",
            "design2sva",
            "--k",
            "3",
            "--dry-run",
            "--out",
            "evaluation/results/design2sva_eval_codex_expanded_subset.json",
        ],
    )

    assert run_codex_main() == 0
    stdout = capsys.readouterr().out

    assert "design2sva_candidate.schema.json" in stdout
    assert "run_design2sva_eval.py" in stdout
    assert "--llm" in stdout
    assert "--k 3" in stdout
    assert "--max-repair-rounds 0" in stdout
    assert "design2sva_eval_codex_expanded_subset.json" in stdout


def test_stage16_codex_design2sva_external_run_requires_ack(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["run_codex_llm_eval.py", "--task", "design2sva"],
    )

    assert run_codex_main() == 2
    assert "Design2SVA" in capsys.readouterr().err


def test_stage16_design2sva_summary_reports_real_llm_accounting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    out = tmp_path / "design2sva_replay.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_eval.py",
            "--limit",
            "1",
            "--k",
            "3",
            "--max-repair-rounds",
            "0",
            "--replay",
            "evaluation/results/design2sva_eval_codex_subset.json",
            "--out",
            str(out),
            "--markdown",
            str(tmp_path / "design2sva_replay.md"),
        ],
    )

    assert run_design2sva_main() == 0
    summary = json.loads(out.read_text(encoding="utf-8"))["summary"]

    assert summary["source_counts"] == {"llm": 3}
    assert summary["real_llm_count"] == 3
    assert summary["candidate_count_by_case"] == {"design2sva_arbiter_mutex": 3}
    assert summary["failure_by_design_counts"] == {"arbiter_rr2": {"temporal_mismatch": 3}}
    assert summary["failure_by_property_type_counts"] == {
        "invariant": {"temporal_mismatch": 3}
    }
