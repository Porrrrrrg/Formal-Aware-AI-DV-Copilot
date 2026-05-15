# Expanded Design2SVA Prompt Audit

This audit is generated locally and does not send prompts to an external LLM.

Command: `python scripts/export_codex_prompts.py --task design2sva --design2sva-cases benchmarks/design2sva_cases.json --limit 12 --design2sva-context-budget 24 --out-dir evaluation/prompt_previews/design2sva_expanded --audit-markdown evaluation/prompt_previews/design2sva_expanded_prompt_audit.md --require-no-gold-labels`

| Field | Value |
| --- | ---: |
| Prompts | 12 |
| Cases | 12 |
| Gold labels absent | True |
| `reference_sva` key present | 0 |
| `reference_sva` value present | 0 |
| `expected_proof_status` present | 0 |
| Jasper evidence included | False |
| Visible signal set size | min=7, max=17, avg=12.50 |
| Total approximate tokens | 89998 |
| Max prompt characters | 39553 |

## Prompt Rows

| Prompt | Case | Design | Property | Chars | Approx tokens | Visible signals | Gold absent | Jasper evidence |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| design2sva_001_design2sva_arbiter_mutex | design2sva_arbiter_mutex | arbiter_rr2 | p_mutex | 21621 | 5405 | 7 | True | False |
| design2sva_002_design2sva_rv_buffer_ready_full | design2sva_rv_buffer_ready_full | rv_buffer | p_in_ready_when_full_and_out_ready | 28128 | 7032 | 12 | True | False |
| design2sva_003_design2sva_apb_setup_enable | design2sva_apb_setup_enable | apb_regblock | p_setup_then_enable | 30698 | 7674 | 14 | True | False |
| design2sva_004_design2sva_fifo_no_underflow | design2sva_fifo_no_underflow | fifo_1r1w | p_no_underflow | 39553 | 9888 | 17 | True | False |
| design2sva_005_design2sva_arbiter_no_spurious_gnt0 | design2sva_arbiter_no_spurious_gnt0 | arbiter_rr2 | p_no_spurious_gnt0 | 21639 | 5409 | 7 | True | False |
| design2sva_006_design2sva_arbiter_single_req0_grant | design2sva_arbiter_single_req0_grant | arbiter_rr2 | p_single_req0_grant | 21656 | 5414 | 7 | True | False |
| design2sva_007_design2sva_rv_buffer_out_valid_equals_full | design2sva_rv_buffer_out_valid_equals_full | rv_buffer | p_out_valid_equals_full | 28110 | 7027 | 12 | True | False |
| design2sva_008_design2sva_rv_buffer_stable_while_stalled | design2sva_rv_buffer_stable_while_stalled | rv_buffer | p_data_stable_while_stalled | 28119 | 7029 | 12 | True | False |
| design2sva_009_design2sva_apb_pready_response_valid | design2sva_apb_pready_response_valid | apb_regblock | p_pready_response_valid | 30658 | 7664 | 14 | True | False |
| design2sva_010_design2sva_apb_invalid_address_behavior | design2sva_apb_invalid_address_behavior | apb_regblock | p_invalid_address_behavior | 30759 | 7689 | 14 | True | False |
| design2sva_011_design2sva_fifo_no_overflow | design2sva_fifo_no_overflow | fifo_1r1w | p_no_overflow | 39535 | 9883 | 17 | True | False |
| design2sva_012_design2sva_fifo_pop_data_stable | design2sva_fifo_pop_data_stable | fifo_1r1w | p_pop_data_stable_when_stalled | 39539 | 9884 | 17 | True | False |

Gold-label checks treat `reference_sva`, `expected_proof_status`, `gold_label`, `expected_issue_type`, and exact reference SVA text as forbidden prompt content.
