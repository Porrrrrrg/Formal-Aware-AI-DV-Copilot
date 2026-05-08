module rv_buffer_assumptions #(
  parameter int WIDTH = 8
) (
  input logic             clk,
  input logic             rst,
  input logic             in_valid,
  input logic             in_ready,
  input logic [WIDTH-1:0] in_data,
  input logic             out_valid,
  input logic             out_ready,
  input logic [WIDTH-1:0] out_data,
  input logic             full
);

  a_reset_initial: assume property (@(posedge clk) $initstate |-> rst);
  a_reset_deasserts: assume property (@(posedge clk) rst |=> !rst);
  a_no_x_controls: assume property (@(posedge clk) !$isunknown({rst, in_valid, out_ready}));

endmodule
