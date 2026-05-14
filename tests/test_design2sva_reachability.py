from __future__ import annotations

from copilot.agents.design2sva_reachability import (
    NO_ANTECEDENT,
    UNKNOWN,
    antecedent_reachable,
    antecedent_unreachable,
    apply_cover_status,
    build_antecedent_metadata,
    cover_before_assert_metadata,
    extract_assertion_trigger,
    generate_antecedent_cover,
)


INVARIANT_SVA = "assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));"
IMPLICATION_SVA = "assert property (@(posedge clk) disable iff (rst) req0 |-> ##1 gnt0);"


def test_invariant_assertion_has_no_antecedent_cover() -> None:
    extraction = extract_assertion_trigger(INVARIANT_SVA)

    assert extraction["ok"] is True
    assert extraction["status"] == NO_ANTECEDENT
    assert extraction["condition"] is None
    assert extraction["condition_kind"] == "invariant"
    assert extraction["trigger_kind"] == "invariant"
    assert extraction["trigger_status"] == NO_ANTECEDENT
    assert extraction["has_antecedent"] is False
    assert extraction["requires_antecedent_cover"] is False

    cover = generate_antecedent_cover(INVARIANT_SVA, source_property_id="p_mutex")

    assert cover["ok"] is False
    assert cover["status"] == NO_ANTECEDENT
    assert cover["condition"] is None
    assert cover["cover_sva"] is None
    assert cover["has_antecedent"] is False
    assert cover["requires_antecedent_cover"] is False

    metadata = build_antecedent_metadata(INVARIANT_SVA, "p_mutex")

    assert metadata["extraction_status"] == NO_ANTECEDENT
    assert metadata["antecedent"] is None
    assert metadata["antecedent_kind"] == "invariant"
    assert metadata["trigger_kind"] == "invariant"
    assert metadata["trigger_status"] == NO_ANTECEDENT
    assert metadata["cover_property_id"] == ""
    assert metadata["cover_sva"] == ""
    assert metadata["cover_status"] == "not_run"
    assert metadata["antecedent_reachability"] == NO_ANTECEDENT
    assert antecedent_reachable(metadata) is True
    assert antecedent_unreachable(metadata) is False

    updated = apply_cover_status(
        metadata,
        {"status": "unreachable", "proof_status": "unreachable"},
    )

    assert updated["cover_status"] == "not_run"
    assert updated["cover_status_ignored_reason"] == NO_ANTECEDENT
    assert updated["antecedent_reachability"] == NO_ANTECEDENT
    assert antecedent_unreachable(updated) is False

    combined = cover_before_assert_metadata(INVARIANT_SVA, cover_status="unreachable")

    assert combined["ok"] is True
    assert combined["status"] == NO_ANTECEDENT
    assert combined["has_antecedent"] is False
    assert combined["requires_antecedent_cover"] is False
    assert combined["reachability"]["reachability_status"] == NO_ANTECEDENT


def test_implication_assertion_generates_cover_from_antecedent() -> None:
    extraction = extract_assertion_trigger(IMPLICATION_SVA)

    assert extraction["ok"] is True
    assert extraction["status"] == "extracted"
    assert extraction["condition"] == "req0"
    assert extraction["condition_kind"] == "antecedent"
    assert extraction["trigger_kind"] == "antecedent"
    assert extraction["trigger_status"] == "extracted"
    assert extraction["operator"] == "|->"
    assert extraction["has_antecedent"] is True
    assert extraction["requires_antecedent_cover"] is True

    cover = generate_antecedent_cover(IMPLICATION_SVA, source_property_id="p_req0")

    assert cover["ok"] is True
    assert cover["condition"] == "req0"
    assert cover["condition_kind"] == "antecedent"
    assert cover["cover_sva"] == (
        "cov_p_req0_antecedent: cover property "
        "(@(posedge clk) disable iff (rst) (req0));"
    )

    metadata = build_antecedent_metadata(IMPLICATION_SVA, "p_req0")

    assert metadata["extraction_status"] == "extracted"
    assert metadata["antecedent"] == "req0"
    assert metadata["antecedent_kind"] == "antecedent"
    assert metadata["cover_property_id"] == "cov_p_req0_antecedent"
    assert metadata["cover_sva"] == cover["cover_sva"]
    assert metadata["antecedent_reachability"] == UNKNOWN

    updated = apply_cover_status(
        metadata,
        {"status": "unreachable", "proof_status": "unreachable"},
    )

    assert updated["antecedent_reachability"] == "unreachable"
    assert antecedent_unreachable(updated) is True
