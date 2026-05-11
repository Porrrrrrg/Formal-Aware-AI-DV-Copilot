# Intent Alignment Smoke Summary

Created UTC: 2026-05-11T18:04:23.428527Z

Evidence type: static/offline heuristic evaluator.

This smoke report does not claim new benchmark results, formal equivalence, or production readiness. Jasper proof status, when present, remains separate from intent alignment.

## Summary

- Results: 18
- Manual review required: 10
- Label counts: {"likely_aligned": 15, "likely_misaligned": 2, "partially_aligned": 1}

## Cases

- `repair_arbiter_mutex_syntax` / `p_mutex`: likely_aligned (0.837); manual_review_required=true
- `repair_arbiter_spurious_unknown_signal` / `p_no_spurious_gnt0`: likely_aligned (1.000); manual_review_required=false
- `repair_arbiter_single_req1_wrong_grant` / `p_single_req1_grant`: likely_aligned (0.865); manual_review_required=true
- `repair_arbiter_turn0_missing_condition` / `p_both_req_priority_turn0`: likely_aligned (0.827); manual_review_required=true
- `repair_arbiter_reset_wrong_polarity` / `p_reset_initial_priority`: likely_aligned (1.000); manual_review_required=false
- `repair_arbiter_fairness_too_strong` / `p_persistent_fairness0`: likely_misaligned (0.785); manual_review_required=true
- `repair_buffer_reset_syntax` / `p_reset_empty`: likely_aligned (0.865); manual_review_required=true
- `repair_buffer_unknown_data_signal` / `p_data_stable_while_stalled`: likely_aligned (1.000); manual_review_required=false
- `repair_buffer_capture_missing_fire` / `p_capture_on_input_fire`: partially_aligned (0.752); manual_review_required=true
- `repair_buffer_full_clear_wrong_guard` / `p_full_clear_on_dequeue`: likely_aligned (1.000); manual_review_required=false
- `repair_buffer_simul_unknown_signal` / `p_simultaneous_enqueue_dequeue_semantics`: likely_aligned (1.000); manual_review_required=false
- `repair_buffer_out_valid_wrong_relation` / `p_out_valid_equals_full`: likely_aligned (0.837); manual_review_required=true
- `repair_apb_setup_syntax` / `p_setup_then_enable`: likely_misaligned (0.672); manual_review_required=true
- `repair_apb_write_wrong_addr` / `p_write_updates_reg0`: likely_aligned (1.000); manual_review_required=false
- `repair_apb_read_unknown_signal` / `p_read_returns_reg0`: likely_aligned (1.000); manual_review_required=false
- `repair_apb_pready_missing_access` / `p_pready_response_valid`: likely_aligned (0.887); manual_review_required=true
- `repair_apb_reset_wrong_polarity` / `p_reset_clears_registers`: likely_aligned (0.865); manual_review_required=true
- `repair_apb_invalid_missing_inside` / `p_invalid_address_behavior`: likely_aligned (1.000); manual_review_required=false
