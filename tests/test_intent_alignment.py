from __future__ import annotations

import json
from pathlib import Path

from app.alignment import AlignmentLabel, IntentAlignmentCase, evaluate_intent_alignment
from app.alignment.sva_features import extract_sva_features
from app.cli import main


REFERENCE = (
    "p_capture: assert property (@(posedge clk) disable iff (rst) "
    "in_valid && in_ready |=> full && out_data == $past(in_data));"
)


def case(candidate: str, *, proof_status_context: dict[str, object] | None = None) -> IntentAlignmentCase:
    return IntentAlignmentCase(
        case_id="c1",
        property_id="p_capture",
        intent_summary="On an input handshake, the buffer stores the input data and becomes full.",
        candidate_sva=candidate,
        reference_sva=REFERENCE,
        allowed_signals=["clk", "rst", "in_valid", "in_ready", "full", "out_data", "in_data"],
        required_signals=["clk", "rst", "in_valid", "in_ready", "full", "out_data", "in_data"],
        proof_status_context=proof_status_context,
    )


def test_aligned_reference_vs_reference() -> None:
    result = evaluate_intent_alignment(case(REFERENCE))

    assert result.alignment_label == AlignmentLabel.ALIGNED
    assert result.alignment_score == 1.0
    assert result.manual_review_required is False


def test_missing_antecedent_is_not_aligned() -> None:
    candidate = (
        "p_capture: assert property (@(posedge clk) disable iff (rst) "
        "full && out_data == $past(in_data));"
    )

    result = evaluate_intent_alignment(case(candidate))

    assert result.alignment_label in {
        AlignmentLabel.PARTIALLY_ALIGNED,
        AlignmentLabel.LIKELY_MISALIGNED,
    }
    assert "antecedent_missing" in result.weak_property_flags
    assert result.manual_review_required is True


def test_missing_consequent_is_likely_misaligned() -> None:
    candidate = "p_capture: assert property (@(posedge clk) disable iff (rst) in_valid && in_ready |=> 1'b1);"

    result = evaluate_intent_alignment(case(candidate))

    assert result.alignment_label == AlignmentLabel.LIKELY_MISALIGNED
    assert "consequent_signal_missing" in result.weak_property_flags
    assert result.manual_review_required is True


def test_wrong_delay_is_partially_aligned_or_likely_misaligned() -> None:
    candidate = (
        "p_capture: assert property (@(posedge clk) disable iff (rst) "
        "in_valid && in_ready |-> full && out_data == $past(in_data));"
    )

    result = evaluate_intent_alignment(case(candidate))

    assert result.alignment_label in {
        AlignmentLabel.PARTIALLY_ALIGNED,
        AlignmentLabel.LIKELY_MISALIGNED,
    }
    assert "delay_missing_or_changed" in result.weak_property_flags
    assert result.delay_match.value in {"partial", "mismatch"}


def test_hallucinated_signal_requires_manual_review() -> None:
    candidate = (
        "p_capture: assert property (@(posedge clk) disable iff (rst) "
        "in_valid && fire |=> full && out_data == $past(in_data));"
    )

    result = evaluate_intent_alignment(case(candidate))

    assert result.forbidden_or_unknown_signal_count == 1
    assert result.alignment_label == AlignmentLabel.LIKELY_MISALIGNED
    assert result.manual_review_required is True


def test_proof_pass_context_alone_does_not_force_aligned() -> None:
    candidate = "p_capture: assert property (@(posedge clk) disable iff (rst) in_valid |=> full);"

    result = evaluate_intent_alignment(case(candidate, proof_status_context={"proof_status": "passed"}))

    assert result.alignment_label != AlignmentLabel.ALIGNED
    assert result.proof_status_context == {"proof_status": "passed"}
    assert any("does not imply intent alignment" in item for item in result.rationale)


def test_partial_structural_match_requires_manual_review() -> None:
    candidate = (
        "p_capture: assert property (@(posedge clk) disable iff (rst) "
        "in_valid && in_ready |=> out_data == $past(in_data) && full);"
    )

    result = evaluate_intent_alignment(case(candidate))

    assert result.alignment_label == AlignmentLabel.LIKELY_ALIGNED
    assert result.consequent_match.value == "partial"
    assert result.manual_review_required is True


def test_unknown_structural_match_requires_manual_review() -> None:
    no_trigger_reference = "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));"

    result = evaluate_intent_alignment(
        IntentAlignmentCase(
            case_id="mutex",
            property_id="p_mutex",
            intent_summary="The arbiter must never grant both clients in the same cycle.",
            candidate_sva=no_trigger_reference,
            reference_sva=no_trigger_reference,
            allowed_signals=["clk", "rst", "gnt0", "gnt1"],
            required_signals=["clk", "rst", "gnt0", "gnt1"],
        )
    )

    assert result.trigger_match.value == "unknown"
    assert result.manual_review_required is True


def test_weak_property_flag_triggers_for_simple_check() -> None:
    features = extract_sva_features("p: assert property (@(posedge clk) disable iff (rst) full);")
    result = evaluate_intent_alignment(
        IntentAlignmentCase(
            case_id="c2",
            property_id="p",
            intent_summary="Full should follow a valid input transfer.",
            candidate_sva=features.raw_sva,
            reference_sva="p: assert property (@(posedge clk) disable iff (rst) in_valid |=> full);",
            allowed_signals=["clk", "rst", "in_valid", "full"],
            required_signals=["clk", "rst", "in_valid", "full"],
        )
    )

    assert "simple_signal_check_without_trigger" in result.weak_property_flags


def test_cli_dry_run_emits_manifest_and_report(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    candidates = tmp_path / "candidates.jsonl"
    cases.write_text(
        json.dumps(
            [
                {
                    "case_id": "c1",
                    "property_id": "p_capture",
                    "intent": "On an input handshake, the buffer stores the input data and becomes full.",
                    "signals": ["clk", "rst", "in_valid", "in_ready", "full", "out_data", "in_data"],
                    "reference_sva": REFERENCE,
                }
            ]
        ),
        encoding="utf-8",
    )
    candidates.write_text(
        json.dumps(
            {
                "case_id": "c1",
                "property_id": "p_capture",
                "codex_repaired_sva": REFERENCE,
                "candidate_status": "proof_pass",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "align-intent",
            "--cases",
            str(cases),
            "--candidates",
            str(candidates),
            "--out-dir",
            str(tmp_path),
            "--dry-run",
        ]
    )

    manifests = sorted(tmp_path.glob("intent_alignment_smoke_manifest_*.json"))
    reports = sorted(tmp_path.glob("intent_alignment_smoke_summary_*.md"))
    assert exit_code == 0
    assert manifests
    assert reports
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["external_calls_allowed"] is False
    assert manifest["result_count"] == 1
