from __future__ import annotations

from pathlib import Path

from copilot.retrieval import (
    build_rtl_index,
    get_clock_reset_candidates,
    get_module_interface,
    get_signal_logic,
)

ROOT = Path(__file__).resolve().parents[2]


def test_rv_buffer_interface_and_assign_logic() -> None:
    rtl = ROOT / "benchmarks/rv_buffer/rtl/rv_buffer_correct.sv"
    index = build_rtl_index([rtl])

    interface = get_module_interface(index, "rv_buffer")
    port_names = {port["name"] for port in interface["ports"]}
    assert {"clk", "rst", "in_valid", "in_ready", "out_ready", "full"} <= port_names

    logic = get_signal_logic(index, "in_ready", module_name="rv_buffer")
    assert logic["drivers"]
    assert {"full", "out_ready"} <= set(logic["drivers"][0]["dependencies"])


def test_arbiter_turn_logic_and_clock_reset_candidates() -> None:
    rtl = ROOT / "benchmarks/arbiter_rr2/rtl/arbiter_rr2_correct.sv"
    index = build_rtl_index([rtl])

    logic = get_signal_logic(index, "turn", module_name="arbiter_rr2")
    assert logic["drivers"]

    candidates = get_clock_reset_candidates(index)
    assert "clk" in candidates["clocks"]
    assert "rst" in candidates["resets"]
