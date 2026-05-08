module arbiter_rr2_harness;
  logic clk;
  logic rst;
  logic req0;
  logic req1;
  logic gnt0;
  logic gnt1;
  logic turn;

  arbiter_rr2 dut (
    .clk(clk),
    .rst(rst),
    .req0(req0),
    .req1(req1),
    .gnt0(gnt0),
    .gnt1(gnt1),
    .turn(turn)
  );

  arbiter_rr2_assumptions assumptions_i (.*);
  arbiter_rr2_properties properties_i (.*);
endmodule
