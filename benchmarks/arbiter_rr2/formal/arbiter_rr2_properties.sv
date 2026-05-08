module arbiter_rr2_properties (
  input logic clk,
  input logic rst,
  input logic req0,
  input logic req1,
  input logic gnt0,
  input logic gnt1,
  input logic turn
);

  p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));
  p_no_spurious_gnt0: assert property (@(posedge clk) disable iff (rst) gnt0 |-> req0);
  p_no_spurious_gnt1: assert property (@(posedge clk) disable iff (rst) gnt1 |-> req1);
  p_single_req0_grant: assert property (@(posedge clk) disable iff (rst) req0 && !req1 |-> gnt0 && !gnt1);
  p_single_req1_grant: assert property (@(posedge clk) disable iff (rst) !req0 && req1 |-> !gnt0 && gnt1);
  p_both_req_priority_turn0: assert property (@(posedge clk) disable iff (rst) req0 && req1 && !turn |-> gnt0 && !gnt1);
  p_both_req_priority_turn1: assert property (@(posedge clk) disable iff (rst) req0 && req1 && turn |-> !gnt0 && gnt1);
  p_turn_updates_on_contested_grant0: assert property (@(posedge clk) disable iff (rst) req0 && req1 && gnt0 |=> turn);
  p_turn_updates_on_contested_grant1: assert property (@(posedge clk) disable iff (rst) req0 && req1 && gnt1 |=> !turn);
  p_reset_initial_priority: assert property (@(posedge clk) rst |=> !turn);
  p_persistent_fairness0: assert property (@(posedge clk) disable iff (rst) req0 && req1 ##1 req0 && req1 |-> ##[0:1] gnt0);
  p_persistent_fairness1: assert property (@(posedge clk) disable iff (rst) req0 && req1 ##1 req0 && req1 |-> ##[0:1] gnt1);

  cov_alternating_grants: cover property (@(posedge clk) disable iff (rst) req0 && req1 && gnt0 ##1 req0 && req1 && gnt1);
  cov_illegal_double_grant: cover property (@(posedge clk) disable iff (rst) gnt0 && gnt1);

endmodule
