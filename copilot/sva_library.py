"""Shared SVA templates and lightweight syntax utilities."""

from __future__ import annotations

import re

SVA_TEMPLATES = {
    "p_mutex": "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));",
    "p_no_spurious_gnt0": "p_no_spurious_gnt0: assert property (@(posedge clk) disable iff (rst) gnt0 |-> req0);",
    "p_no_spurious_gnt1": "p_no_spurious_gnt1: assert property (@(posedge clk) disable iff (rst) gnt1 |-> req1);",
    "p_single_req0_grant": "p_single_req0_grant: assert property (@(posedge clk) disable iff (rst) req0 && !req1 |-> gnt0 && !gnt1);",
    "p_single_req1_grant": "p_single_req1_grant: assert property (@(posedge clk) disable iff (rst) !req0 && req1 |-> !gnt0 && gnt1);",
    "p_both_req_priority_turn0": "p_both_req_priority_turn0: assert property (@(posedge clk) disable iff (rst) req0 && req1 && !turn |-> gnt0 && !gnt1);",
    "p_both_req_priority_turn1": "p_both_req_priority_turn1: assert property (@(posedge clk) disable iff (rst) req0 && req1 && turn |-> !gnt0 && gnt1);",
    "p_turn_updates_on_contested_grant0": "p_turn_updates_on_contested_grant0: assert property (@(posedge clk) disable iff (rst) req0 && req1 && gnt0 |=> turn);",
    "p_turn_updates_on_contested_grant1": "p_turn_updates_on_contested_grant1: assert property (@(posedge clk) disable iff (rst) req0 && req1 && gnt1 |=> !turn);",
    "p_reset_initial_priority": "p_reset_initial_priority: assert property (@(posedge clk) rst |=> !turn);",
    "p_persistent_fairness0": "p_persistent_fairness0: assert property (@(posedge clk) disable iff (rst) req0 && req1 && !gnt0 |=> (!req0 || !req1 || gnt0));",
    "p_persistent_fairness1": "p_persistent_fairness1: assert property (@(posedge clk) disable iff (rst) req0 && req1 && !gnt1 |=> (!req0 || !req1 || gnt1));",
    "p_reset_empty": "p_reset_empty: assert property (@(posedge clk) rst |=> !full && !out_valid);",
    "p_out_valid_equals_full": "p_out_valid_equals_full: assert property (@(posedge clk) disable iff (rst) out_valid == full);",
    "p_in_ready_when_empty": "p_in_ready_when_empty: assert property (@(posedge clk) disable iff (rst) !full |-> in_ready);",
    "p_in_ready_when_full_and_out_ready": "p_in_ready_when_full_and_out_ready: assert property (@(posedge clk) disable iff (rst) full && out_ready |-> in_ready);",
    "p_data_stable_while_stalled": "p_data_stable_while_stalled: assert property (@(posedge clk) disable iff (rst) out_valid && !out_ready |=> out_valid && $stable(out_data));",
    "p_capture_on_input_fire": "p_capture_on_input_fire: assert property (@(posedge clk) disable iff (rst) in_valid && in_ready |=> full && out_data == $past(in_data));",
    "p_full_set_on_enqueue": "p_full_set_on_enqueue: assert property (@(posedge clk) disable iff (rst) in_valid && in_ready && !out_ready |=> full);",
    "p_full_clear_on_dequeue": "p_full_clear_on_dequeue: assert property (@(posedge clk) disable iff (rst) out_valid && out_ready && !in_valid |=> !full);",
    "p_simultaneous_enqueue_dequeue_semantics": "p_simultaneous_enqueue_dequeue_semantics: assert property (@(posedge clk) disable iff (rst) full && in_valid && in_ready && out_ready |=> full && out_data == $past(in_data));",
    "p_setup_then_enable": "p_setup_then_enable: assert property (@(posedge pclk) disable iff (!presetn) psel && !penable |=> psel && penable);",
    "p_write_updates_reg0": "p_write_updates_reg0: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && pwrite && pready && paddr == 8'h00 |=> reg0 == $past(pwdata));",
    "p_write_updates_reg1": "p_write_updates_reg1: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && pwrite && pready && paddr == 8'h04 |=> reg1 == $past(pwdata));",
    "p_read_returns_reg0": "p_read_returns_reg0: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && !pwrite && paddr == 8'h00 |-> prdata == reg0);",
    "p_read_returns_reg1": "p_read_returns_reg1: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && !pwrite && paddr == 8'h04 |-> prdata == reg1);",
    "p_no_write_without_access": "p_no_write_without_access: assert property (@(posedge pclk) disable iff (!presetn) !(psel && penable && pwrite) |=> reg0 == $past(reg0) && reg1 == $past(reg1));",
    "p_pready_response_valid": "p_pready_response_valid: assert property (@(posedge pclk) disable iff (!presetn) psel && penable |-> pready);",
    "p_reset_clears_registers": "p_reset_clears_registers: assert property (@(posedge pclk) !presetn |=> reg0 == 32'h0 && reg1 == 32'h0);",
    "p_invalid_address_behavior": "p_invalid_address_behavior: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && !(paddr inside {8'h00, 8'h04}) |-> pslverr);",
}

SVA_KEYWORDS = {
    "assert",
    "property",
    "cover",
    "posedge",
    "negedge",
    "disable",
    "iff",
    "inside",
    "stable",
    "past",
    "rose",
    "fell",
    "throughout",
    "until",
    "and",
    "or",
    "not",
    "h",
}


def normalize_sva(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def syntax_scaffold_ok(sva: str) -> bool:
    normalized = normalize_sva(sva)
    return (
        "assert property" in normalized
        and "@(posedge" in normalized
        and normalized.endswith(";")
        and normalized.count("(") == normalized.count(")")
    )


def extract_identifiers(sva: str) -> set[str]:
    identifiers = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_$]*\b", sva))
    return {
        identifier
        for identifier in identifiers
        if identifier not in SVA_KEYWORDS
        and not re.fullmatch(r"h[0-9A-Fa-f]+", identifier)
        and not re.fullmatch(r"b[01xXzZ]+", identifier)
    }


def hallucinated_identifiers(sva: str, allowed_identifiers: list[str]) -> list[str]:
    allowed = set(allowed_identifiers)
    return sorted(identifier for identifier in extract_identifiers(sva) if identifier not in allowed)
