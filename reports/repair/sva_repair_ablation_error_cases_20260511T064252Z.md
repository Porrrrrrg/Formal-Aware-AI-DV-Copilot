# Stage 4A SVA Repair Ablation Error Cases

Created UTC: 2026-05-11T06:42:53Z

Rows below are cases that did not reach local scaffold success or had hallucinated identifiers. They are not Jasper proof failures unless Jasper was explicitly run.

| variant | case_id | design | bug_type | final_status | scaffold | exact | hallucinated | rounds |
| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: |
| baseline_prompt | repair_arbiter_turn0_missing_condition | arbiter_rr2 | overbroad_property | scaffold_fail | False | False |  | 1 |
| baseline_prompt | repair_arbiter_fairness_too_strong | arbiter_rr2 | temporal_or_semantic_error | scaffold_fail | False | False |  | 1 |
| baseline_prompt | repair_buffer_capture_missing_fire | rv_buffer | overbroad_property | scaffold_fail | False | False |  | 1 |
| baseline_prompt | repair_apb_setup_syntax | apb_regblock | syntax_error | scaffold_fail | False | False |  | 1 |
| baseline_prompt | repair_apb_pready_missing_access | apb_regblock | overbroad_property | scaffold_fail | False | False |  | 1 |
| cex_aware_prompt | repair_arbiter_turn0_missing_condition | arbiter_rr2 | overbroad_property | scaffold_fail | False | False |  | 1 |
| cex_aware_prompt | repair_arbiter_reset_wrong_polarity | arbiter_rr2 | reset_error | scaffold_fail | False | False |  | 1 |
| cex_aware_prompt | repair_buffer_capture_missing_fire | rv_buffer | overbroad_property | scaffold_fail | False | False |  | 1 |
| cex_aware_prompt | repair_apb_pready_missing_access | apb_regblock | overbroad_property | scaffold_fail | False | False |  | 1 |
| cex_aware_prompt | repair_apb_reset_wrong_polarity | apb_regblock | reset_error | scaffold_fail | False | False |  | 1 |
| signal_whitelist_only | repair_arbiter_turn0_missing_condition | arbiter_rr2 | overbroad_property | scaffold_fail | False | False |  | 1 |
| signal_whitelist_only | repair_buffer_reset_syntax | rv_buffer | syntax_error | scaffold_fail | False | False |  | 1 |
| signal_whitelist_only | repair_buffer_capture_missing_fire | rv_buffer | overbroad_property | scaffold_fail | False | False |  | 1 |
| signal_whitelist_only | repair_apb_setup_syntax | apb_regblock | syntax_error | scaffold_fail | False | False |  | 1 |
| signal_whitelist_only | repair_apb_pready_missing_access | apb_regblock | overbroad_property | scaffold_fail | False | False |  | 1 |
| temporal_hint_only | repair_arbiter_single_req1_wrong_grant | arbiter_rr2 | temporal_or_semantic_error | scaffold_fail | False | False |  | 1 |
| temporal_hint_only | repair_arbiter_turn0_missing_condition | arbiter_rr2 | overbroad_property | scaffold_fail | False | False |  | 1 |
| temporal_hint_only | repair_buffer_reset_syntax | rv_buffer | syntax_error | scaffold_fail | False | False |  | 1 |
| temporal_hint_only | repair_buffer_capture_missing_fire | rv_buffer | overbroad_property | scaffold_fail | False | False |  | 1 |
| temporal_hint_only | repair_apb_setup_syntax | apb_regblock | syntax_error | scaffold_fail | False | False |  | 1 |
| temporal_hint_only | repair_apb_pready_missing_access | apb_regblock | overbroad_property | scaffold_fail | False | False |  | 1 |
| one_round_repair | repair_arbiter_single_req1_wrong_grant | arbiter_rr2 | temporal_or_semantic_error | scaffold_fail | False | False |  | 1 |
| one_round_repair | repair_arbiter_turn0_missing_condition | arbiter_rr2 | overbroad_property | scaffold_fail | False | False |  | 1 |
| one_round_repair | repair_buffer_reset_syntax | rv_buffer | syntax_error | scaffold_fail | False | False |  | 1 |
| one_round_repair | repair_buffer_capture_missing_fire | rv_buffer | overbroad_property | scaffold_fail | False | False |  | 1 |
| one_round_repair | repair_apb_setup_syntax | apb_regblock | syntax_error | scaffold_fail | False | False |  | 1 |
| one_round_repair | repair_apb_pready_missing_access | apb_regblock | overbroad_property | scaffold_fail | False | False |  | 1 |
| multi_round_repair | repair_arbiter_turn0_missing_condition | arbiter_rr2 | overbroad_property | scaffold_fail | False | False |  | 3 |
| multi_round_repair | repair_buffer_reset_syntax | rv_buffer | syntax_error | scaffold_fail | False | False |  | 3 |
| multi_round_repair | repair_buffer_capture_missing_fire | rv_buffer | overbroad_property | scaffold_fail | False | False |  | 3 |
| multi_round_repair | repair_apb_pready_missing_access | apb_regblock | overbroad_property | scaffold_fail | False | False |  | 3 |
| multi_round_repair | repair_apb_reset_wrong_polarity | apb_regblock | reset_error | scaffold_fail | False | False |  | 3 |
| self_check_before_final | repair_arbiter_turn0_missing_condition | arbiter_rr2 | overbroad_property | scaffold_fail | False | False |  | 1 |
| self_check_before_final | repair_buffer_reset_syntax | rv_buffer | syntax_error | scaffold_fail | False | False |  | 1 |
| self_check_before_final | repair_buffer_capture_missing_fire | rv_buffer | overbroad_property | scaffold_fail | False | False |  | 1 |
| self_check_before_final | repair_apb_setup_syntax | apb_regblock | syntax_error | scaffold_fail | False | False |  | 1 |
| self_check_before_final | repair_apb_pready_missing_access | apb_regblock | overbroad_property | scaffold_fail | False | False |  | 1 |
| self_check_before_final | repair_apb_reset_wrong_polarity | apb_regblock | reset_error | scaffold_fail | False | False |  | 1 |
