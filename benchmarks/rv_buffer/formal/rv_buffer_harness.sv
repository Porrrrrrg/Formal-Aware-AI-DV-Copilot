module rv_buffer_harness;
  localparam int WIDTH = 8;

  logic clk;
  logic rst;
  logic in_valid;
  logic in_ready;
  logic [WIDTH-1:0] in_data;
  logic out_valid;
  logic out_ready;
  logic [WIDTH-1:0] out_data;
  logic full;

  rv_buffer #(.WIDTH(WIDTH)) dut (.*);

  rv_buffer_assumptions #(.WIDTH(WIDTH)) assumptions_i (.*);
  rv_buffer_properties #(.WIDTH(WIDTH)) properties_i (.*);
endmodule
