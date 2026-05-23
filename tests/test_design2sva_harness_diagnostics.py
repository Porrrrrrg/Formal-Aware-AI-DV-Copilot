from __future__ import annotations

from copilot.agents.design2sva_harness_diagnostics import (
    NOT_RUN,
    UNKNOWN,
    build_harness_diagnostic_bundle,
    build_harness_diagnostic_predictions,
)


def _case(reset_polarity: str) -> dict[str, object]:
    if reset_polarity == "active_low":
        return {
            "case_id": "apb_case",
            "property_id": "p_setup_then_enable",
            "visible_signals": ["pclk", "presetn", "psel", "penable"],
            "clock_reset": {
                "clock": "pclk",
                "reset": "presetn",
                "clock_edge": "posedge",
                "reset_polarity": "active_low",
            },
        }
    return {
        "case_id": "arbiter_case",
        "property_id": "p_mutex",
        "visible_signals": ["clk", "rst", "req0", "gnt0"],
        "clock_reset": {
            "clock": "clk",
            "reset": "rst",
            "clock_edge": "posedge",
            "reset_polarity": "active_high",
        },
    }


def _first_prediction(predictions: list[dict[str, object]], kind: str) -> dict[str, object]:
    for prediction in predictions:
        if prediction["diagnostic_kind"] == kind:
            return prediction
    raise AssertionError(f"missing diagnostic kind {kind}")


def test_active_high_reset_diagnostics_render_disable_iff_and_metadata() -> None:
    predictions = build_harness_diagnostic_predictions(_case("active_high"))

    reset_release = _first_prediction(predictions, "reset_release")
    assert reset_release["sva"] == (
        "cov_p_mutex_reset_release: cover property (@(posedge clk) (rst ##1 !rst));"
    )
    assert reset_release["disable_iff_used"] is False
    assert reset_release["reset_polarity_used"] == "active_high"
    assert reset_release["reset_release_reachable"] == UNKNOWN
    assert reset_release["reachability_status"] == NOT_RUN
    assert reset_release["reachability_ok"] is False

    post_reset = _first_prediction(predictions, "post_reset_cycle")
    assert post_reset["sva"] == (
        "cov_p_mutex_post_reset_cycle: cover property "
        "(@(posedge clk) disable iff (rst) (1'b1));"
    )
    assert post_reset["disable_iff"] == "disable iff (rst)"
    assert post_reset["disable_iff_used"] is True
    assert post_reset["clock_event_assumed"] == "@(posedge clk)"
    assert post_reset["post_reset_reachable"] == UNKNOWN

    visible = [
        prediction
        for prediction in predictions
        if prediction["diagnostic_kind"] == "visible_signal_non_reset"
    ]
    assert [prediction["signal"] for prediction in visible] == ["req0", "gnt0"]
    assert "req0 != '0" in str(visible[0]["sva"])


def test_active_low_reset_diagnostics_render_negated_disable_iff_and_metadata() -> None:
    bundle = build_harness_diagnostic_bundle(_case("active_low"))
    predictions = bundle["predictions"]

    reset_release = _first_prediction(predictions, "reset_release")
    assert reset_release["sva"] == (
        "cov_p_setup_then_enable_reset_release: cover property "
        "(@(posedge pclk) (!presetn ##1 presetn));"
    )
    assert reset_release["disable_iff_used"] is False
    assert reset_release["reset_asserted"] == "!presetn"
    assert reset_release["reset_deasserted"] == "presetn"

    post_reset = _first_prediction(predictions, "post_reset_cycle")
    assert post_reset["sva"] == (
        "cov_p_setup_then_enable_post_reset_cycle: cover property "
        "(@(posedge pclk) disable iff (!presetn) (1'b1));"
    )
    assert post_reset["reset_polarity_used"] == "active_low"
    assert post_reset["disable_iff"] == "disable iff (!presetn)"
    assert post_reset["harness_diagnostic_metadata"]["disable_iff_used"] is True
    assert post_reset["post_reset_reachable"] == UNKNOWN
    assert post_reset["reachability_status"] == NOT_RUN

    clock_advance = _first_prediction(predictions, "clock_advance")
    assert "1'b1 ##1 1'b1" in str(clock_advance["sva"])
    assert clock_advance["clock_event_assumed"] == "@(posedge pclk)"
    assert bundle["reset_release_reachable"] == UNKNOWN
    assert bundle["reachability_status"] == NOT_RUN
    assert bundle["clock_event_assumed"] == "@(posedge pclk)"
    assert bundle["reset_polarity_used"] == "active_low"
    assert bundle["disable_iff_used"] is True
