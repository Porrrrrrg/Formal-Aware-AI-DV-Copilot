module arbiter_rr2_assumptions (
  input logic clk,
  input logic rst,
  input logic req0,
  input logic req1,
  input logic gnt0,
  input logic gnt1,
  input logic turn
);

  // Initial reset is supplied by the JasperGold `reset rst` command in run_jg.tcl.
  a_reset_deasserts: assume property (@(posedge clk) rst |=> !rst);
  a_no_x_inputs: assume property (@(posedge clk) !$isunknown({rst, req0, req1}));

endmodule
