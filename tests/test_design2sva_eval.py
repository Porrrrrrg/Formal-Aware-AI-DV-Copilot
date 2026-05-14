from __future__ import annotations

import json
from pathlib import Path

from copilot.agents.design2sva_agent import build_prompt
from evaluation.run_design2sva_eval import classify_failure, load_cases, main, row_success


ANTI_VACUITY_REPLAY = "evaluation/fixtures/design2sva_anti_vacuity_replay.jsonl"
REFERENCE_ORACLE_REPLAY = "evaluation/fixtures/design2sva_reference_oracle_replay.jsonl"


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
    assert summary["proven_non_vacuous@k"] == 0.0
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
    payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]
    assert payload["mode"] == "replay"
    assert summary["source_counts"] == {"replay": 6}
    assert summary["fallback_rate"] == 0.0


def test_design2sva_reference_oracle_dry_run_audits_reference(tmp_path, monkeypatch) -> None:
    out = tmp_path / "design2sva_reference_oracle.json"

    def fail_generate_candidates(*_args, **_kwargs):  # pragma: no cover - failure path only
        raise AssertionError("reference oracle mode must not invoke candidate generation")

    monkeypatch.setattr(
        "evaluation.run_design2sva_eval.generate_candidates",
        fail_generate_candidates,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_eval.py",
            "--limit",
            "3",
            "--k",
            "1",
            "--reference-oracle",
            "--llm",
            "--jasper-check",
            "--dry-run",
            "--out",
            str(out),
            "--markdown",
            str(tmp_path / "design2sva_reference_oracle.md"),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["mode"] == "reference_oracle"
    assert payload["formal_check_mode"] == "jasper"
    assert summary["source_counts"] == {"reference_oracle": 3}
    assert summary["fallback_rate"] == 0.0
    assert summary["reference_proven@1"] == 0.0
    assert summary["reference_non_vacuous@1"] == 0.0
    assert summary["reference_antecedent_reachable@1"] == 0.0
    assert summary["wrapper_parity_pass_rate"] == 0.0
    assert summary["harness_reachability_status"] == "not_run"
    assert summary["root_cause_details"] == {"formal_check_not_run": 3}

    for result in payload["results"]:
        audit = result["harness_reachability_audit"]
        first_round = result["candidate_paths"][0]["rounds"][0]
        candidate = first_round["candidate"]
        metrics = first_round["metrics"]
        assert audit["reference_sva"] == candidate["sva"]
        assert audit["clock_reset_metadata"]["clock"]
        if audit["reference_antecedent_metadata"]["trigger_kind"] == "invariant":
            assert audit["cover_sva"] == ""
        else:
            assert audit["cover_sva"]
        assert audit["harness_reachability_status"] == "not_run"
        assert metrics["root_cause_candidate"] == "unknown"
        assert metrics["root_cause_detail"] == "formal_check_not_run"
        assert metrics["wrapper_parity_pass"] is False
        assert metrics["reset_release_reachable"] in {"unknown", "not_run"}
        assert "embedding_audit" in metrics
        assert candidate["source"] == "reference_oracle"


def test_design2sva_reference_oracle_replay_metrics(tmp_path, monkeypatch) -> None:
    out = tmp_path / "design2sva_reference_oracle_replay.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_eval.py",
            "--limit",
            "3",
            "--k",
            "1",
            "--reference-oracle",
            "--jasper-replay",
            REFERENCE_ORACLE_REPLAY,
            "--out",
            str(out),
            "--markdown",
            str(tmp_path / "design2sva_reference_oracle_replay.md"),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["mode"] == "reference_oracle"
    assert payload["formal_check_mode"] == "replay"
    assert summary["formal_metrics_status"] == "replayed"
    assert summary["reference_proven@1"] == 1.0
    assert summary["reference_non_vacuous@1"] == 1.0
    assert summary["reference_antecedent_reachable@1"] == 1.0
    assert summary["wrapper_parity_pass_rate"] == 1.0
    assert summary["harness_reachability_status"] == "mixed"
    assert summary["harness_reachability_status_counts"] == {"not_run": 1, "reachable": 2}
    assert summary["proven@1"] == 1.0
    assert summary["source_counts"] == {"reference_oracle": 3}
    assert summary["root_cause_details"] == {
        "reference_oracle_matches_native_formal_behavior": 3
    }
    for result in payload["results"]:
        audit = result["harness_reachability_audit"]
        metrics = result["candidate_paths"][0]["rounds"][0]["metrics"]
        assert audit["reference_proven"] is True
        assert audit["reference_non_vacuous"] is True
        assert audit["reference_antecedent_reachable"] is True
        assert metrics["wrapper_parity_pass"] is True
        assert metrics["root_cause_detail"] == "reference_oracle_matches_native_formal_behavior"
        if audit["reference_antecedent_metadata"]["trigger_kind"] == "invariant":
            assert audit["cover_status"] == "not_run"
        else:
            assert audit["cover_status"] == "covered"


def test_design2sva_reference_oracle_replay_covers_all_fixtures(
    tmp_path,
    monkeypatch,
) -> None:
    out = tmp_path / "design2sva_reference_oracle_replay_all.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_eval.py",
            "--k",
            "1",
            "--reference-oracle",
            "--jasper-replay",
            REFERENCE_ORACLE_REPLAY,
            "--out",
            str(out),
            "--markdown",
            str(tmp_path / "design2sva_reference_oracle_replay_all.md"),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert summary["num_cases"] == 4
    assert summary["reference_proven@1"] == 1.0
    assert summary["reference_non_vacuous@1"] == 1.0
    assert summary["wrapper_parity_pass_rate"] == 1.0
    assert summary["root_cause_details"] == {
        "reference_oracle_matches_native_formal_behavior": 4
    }


def test_unreachable_formal_result_is_not_counted_as_passed() -> None:
    metrics = {
        "valid_json": True,
        "unsupported_helper_code_issue": False,
        "has_hallucinated_signal": False,
        "syntax_ok": True,
        "reset_clock_mismatch": False,
        "exact_match": True,
        "proof_metadata": {
            "status": "passed",
            "syntax_status": "passed",
            "proof_status": "unreachable",
            "vacuity_status": "not_flagged_vacuous",
        },
    }

    metrics["failure_category"] = classify_failure(metrics)

    assert metrics["failure_category"] == "unreachable_cover_goal"
    assert row_success(metrics, formal_mode=True) is False


def test_design2sva_anti_vacuity_replay_repairs_nonvacuously(tmp_path, monkeypatch) -> None:
    rv_case = [
        case
        for case in load_cases(Path("benchmarks/design2sva_cases.json"))
        if case["case_id"] == "design2sva_rv_buffer_ready_full"
    ]
    cases_path = tmp_path / "rv_case.json"
    cases_path.write_text(json.dumps(rv_case), encoding="utf-8")
    out = tmp_path / "anti_vacuity.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_eval.py",
            "--cases",
            str(cases_path),
            "--k",
            "1",
            "--max-repair-rounds",
            "1",
            "--replay",
            ANTI_VACUITY_REPLAY,
            "--jasper-replay",
            ANTI_VACUITY_REPLAY,
            "--out",
            str(out),
            "--markdown",
            str(tmp_path / "anti_vacuity.md"),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]
    rows = [
        round_record["metrics"]
        for result in payload["results"]
        for path in result["candidate_paths"]
        for round_record in path["rounds"]
    ]

    assert payload["mode"] == "replay"
    assert payload["formal_check_mode"] == "replay"
    assert "rows" not in summary
    assert summary["formal_metrics_status"] == "replayed"
    assert summary["syntax@1"] == 1.0
    assert summary["proven@1"] == 0.0
    assert summary["proven@k"] == 0.0
    assert summary["non_vacuous@k"] == 0.0
    assert summary["antecedent_reachable@1"] == 0.0
    assert summary["cover_reachable@k"] == 0.0
    assert summary["proven_non_vacuous@k"] == 1.0
    assert summary["repair_success_after_feedback"] == 1.0
    assert summary["repaired_non_vacuous_success_after_feedback"] == 1.0
    assert summary["source_counts"] == {"replay": 1}
    assert summary["failure_categories"] == {
        "proven_non_vacuous": 1,
        "unreachable_antecedent": 1,
    }
    assert rows[0]["failure_category"] == "unreachable_antecedent"
    assert rows[0]["proof_metadata"]["proof_status"] == "unreachable"
    assert rows[0]["antecedent_metadata"]["antecedent_reachability"] == "unreachable"
    assert row_success(rows[0], formal_mode=True) is False
    assert rows[1]["failure_category"] == "proven_non_vacuous"
    assert rows[1]["source"] == "repair"
    assert rows[1]["antecedent_metadata"]["antecedent_reachability"] == "reachable"
    assert row_success(rows[1], formal_mode=True) is True


def test_replay_takes_precedence_over_llm_mode(tmp_path, monkeypatch) -> None:
    out = tmp_path / "design2sva_replay_llm_flag.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_eval.py",
            "--limit",
            "1",
            "--k",
            "1",
            "--llm",
            "--replay",
            "--out",
            str(out),
            "--markdown",
            str(tmp_path / "design2sva_replay_llm_flag.md"),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "replay"
    assert payload["summary"]["source_counts"] == {"replay": 1}
