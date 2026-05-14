from __future__ import annotations

from pathlib import Path

from copilot.retrieval import Design2SVAContextOptions, build_design2sva_context

ROOT = Path(__file__).resolve().parents[2]


def test_design2sva_context_for_arbiter_is_structured_and_budgeted() -> None:
    context = build_design2sva_context(
        [ROOT / "benchmarks/arbiter_rr2/rtl/arbiter_rr2_correct.sv"],
        Design2SVAContextOptions(
            module_name="arbiter_rr2",
            focus_signals=("gnt0", "gnt1", "req0", "req1"),
            property_intent="gnt0 and gnt1 must never be high together",
            visible_signal_budget=5,
        ),
    )

    assert context["module"] == "arbiter_rr2"
    assert context["signal_budget"]["limit"] == 5
    assert len(context["visible_signals"]) <= 5
    assert {"gnt0", "gnt1"} <= set(context["visible_signals"])
    assert {port["name"] for port in context["interface"]["ports"]} >= {"clk", "rst", "gnt0", "gnt1"}
    assert context["signal_logic"]["gnt0"]["drivers"]


def test_design2sva_context_for_rv_buffer_prefers_signal_logic_over_raw_dump() -> None:
    context = build_design2sva_context(
        [ROOT / "benchmarks/rv_buffer/rtl/rv_buffer_correct.sv"],
        Design2SVAContextOptions(
            module_name="rv_buffer",
            focus_signals=("full", "out_ready", "in_ready"),
            property_intent="full buffer accepts input when output is ready",
            visible_signal_budget=8,
            max_always_blocks=2,
        ),
    )

    assert context["module"] == "rv_buffer"
    assert {"full", "out_ready", "in_ready"} <= set(context["visible_signals"])
    assert len(context["always_blocks"]) <= 2
    assert context["signal_logic"]["in_ready"]["drivers"]
    assert "full" in context["signal_logic"]["in_ready"]["drivers"][0]["dependencies"]
