from __future__ import annotations

from evaluation.run_sva_repair_ablation import VARIANTS, filter_cases


def test_stage4a_variants_cover_requested_ablation_axes() -> None:
    assert set(VARIANTS) == {
        "baseline_prompt",
        "cex_aware_prompt",
        "signal_whitelist_only",
        "temporal_hint_only",
        "one_round_repair",
        "multi_round_repair",
        "self_check_before_final",
    }


def test_default_case_filter_uses_stage3d_case_ids() -> None:
    cases = [
        {"case_id": "repair_a"},
        {"case_id": "repair_b"},
        {"case_id": "new_fifo_repair"},
    ]
    final_proof = {"case_ids": ["repair_a", "repair_b"]}

    filtered = filter_cases(cases, "stage3d_repair", final_proof)

    assert [case["case_id"] for case in filtered] == ["repair_a", "repair_b"]


def test_all_case_filter_keeps_expanded_cases() -> None:
    cases = [{"case_id": "repair_a"}, {"case_id": "new_fifo_repair"}]

    assert filter_cases(cases, "all", {"case_ids": ["repair_a"]}) == cases
