module fifo_1r1w_assumptions #(
  parameter int WIDTH = 8,
  parameter int DEPTH = 4,
  parameter int COUNT_W = $clog2(DEPTH + 1)
) (
  input logic               clk,
  input logic               rst,
  input logic               push_valid,
  input logic               push_ready,
  input logic [WIDTH-1:0]   push_data,
  input logic               pop_valid,
  input logic               pop_ready,
  input logic [WIDTH-1:0]   pop_data,
  input logic               full,
  input logic               empty,
  input logic [COUNT_W-1:0] level,
  input logic               push_fire,
  input logic               pop_fire
);

  a_reset_deasserts: assume property (@(posedge clk) rst |=> !rst);
  a_push_data_stable_when_blocked: assume property (
    @(posedge clk) disable iff (rst)
      push_valid && !push_ready |=> push_valid && $stable(push_data)
  );
  a_pop_ready_eventually: assume property (
    @(posedge clk) disable iff (rst)
      pop_valid |-> ##[0:4] pop_ready
  );

endmodule
