from __future__ import annotations

import json

from copilot.agents.sva_repair_agent import build_prompt, cex_fields_present


CASE = {
    "case_id": "repair_example",
    "design_id": "demo",
    "property_id": "p_demo",
    "bug_type": "overbroad_property",
    "clock": "clk",
    "reset": "rst",
    "signals": ["clk", "rst", "valid", "ready", "done"],
    "intent": "A completed transfer requires valid and ready.",
    "broken_sva": "p_demo: assert property (@(posedge clk) disable iff (rst) valid |=> done);",
    "reference_sva": "p_demo: assert property (@(posedge clk) disable iff (rst) valid && ready |=> done);",
    "counterexample_summary": {
        "failing_cycle": 4,
        "expected_behavior": "No completion without a ready handshake.",
        "observed_behavior": "done rose after valid without ready.",
        "signal_values": {"valid": 1, "ready": 0, "done": 1},
    },
}


def test_baseline_prompt_keeps_legacy_shape() -> None:
    prompt = build_prompt(CASE, str(CASE["broken_sva"]), "feedback", 1)

    assert prompt.startswith("You are JasperLoop-DV in SVA repair mode.")
    assert "CEX_AWARE_REPAIR_CONTEXT" not in prompt
    assert "reference_sva" not in prompt


def test_cex_prompt_exposes_structured_counterexample_context() -> None:
    prompt = build_prompt(
        CASE,
        str(CASE["broken_sva"]),
        "feedback",
        2,
        prompt_version="cex_aware",
        feedback_context={"jasper_proof_status": "cex", "jasper_vacuity_status": "non_vacuous"},
    )

    _, context_blob = prompt.split("CEX_AWARE_REPAIR_CONTEXT:\n", 1)
    context_text, _ = context_blob.split("\n\nJASPER_FEEDBACK:", 1)
    context = json.loads(context_text)

    assert context["failing_property_intent"] == CASE["intent"]
    assert context["broken_sva"] == CASE["broken_sva"]
    assert context["jasper_status"]["proof_status"] == "cex"
    assert context["failing_cycle"] == 4
    assert context["expected_behavior"] == "No completion without a ready handshake."
    assert context["observed_behavior"] == "done rose after valid without ready."
    assert context["relevant_signal_values"] == {"valid": 1, "ready": 0, "done": 1}
    assert context["allowed_signal_whitelist"] == ["clk", "rst", "valid", "ready", "done", "p_demo"]
    assert context["reset_clock_semantics"]["clock"] == "clk"
    assert context["vacuity_hint"] == "non_vacuous"
    assert "reference_sva" not in prompt


def test_cex_fields_present_reports_available_fields() -> None:
    fields = cex_fields_present(CASE, str(CASE["broken_sva"]))

    assert fields["failing_property_intent"] is True
    assert fields["broken_sva"] is True
    assert fields["failing_cycle"] is True
    assert fields["allowed_signal_whitelist"] is True
    assert fields["assumption_risks"] is False
