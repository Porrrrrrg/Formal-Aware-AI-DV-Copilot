module fifo_1r1w_harness;
  localparam int WIDTH = 8;
  localparam int DEPTH = 4;
  localparam int ADDR_W = $clog2(DEPTH);
  localparam int COUNT_W = $clog2(DEPTH + 1);

  logic clk;
  logic rst;
  logic push_valid;
  logic push_ready;
  logic [WIDTH-1:0] push_data;
  logic pop_valid;
  logic pop_ready;
  logic [WIDTH-1:0] pop_data;
  logic full;
  logic empty;
  logic [COUNT_W-1:0] level;
  logic push_fire;
  logic pop_fire;

  fifo_1r1w #(.WIDTH(WIDTH), .DEPTH(DEPTH)) dut (.*);

  fifo_1r1w_assumptions #(.WIDTH(WIDTH), .DEPTH(DEPTH)) assumptions_i (.*);
  fifo_1r1w_properties #(.WIDTH(WIDTH), .DEPTH(DEPTH)) properties_i (.*);
endmodule
