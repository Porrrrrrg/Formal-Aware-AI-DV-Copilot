module fifo_1r1w #(
  parameter int WIDTH = 8,
  parameter int DEPTH = 4,
  parameter int ADDR_W = $clog2(DEPTH),
  parameter int COUNT_W = $clog2(DEPTH + 1)
) (
  input  logic                 clk,
  input  logic                 rst,
  input  logic                 push_valid,
  output logic                 push_ready,
  input  logic [WIDTH-1:0]     push_data,
  output logic                 pop_valid,
  input  logic                 pop_ready,
  output logic [WIDTH-1:0]     pop_data,
  output logic                 full,
  output logic                 empty,
  output logic [COUNT_W-1:0]   level,
  output logic                 push_fire,
  output logic                 pop_fire
);

  logic [WIDTH-1:0] mem_q [DEPTH];
  logic [ADDR_W-1:0] wr_ptr_q;
  logic [ADDR_W-1:0] rd_ptr_q;
  logic [COUNT_W-1:0] count_q;

  function automatic logic [ADDR_W-1:0] next_ptr(input logic [ADDR_W-1:0] ptr);
    next_ptr = (ptr == DEPTH[ADDR_W-1:0] - 1'b1) ? '0 : ptr + 1'b1;
  endfunction

  assign level = count_q;
  assign full = count_q == DEPTH[COUNT_W-1:0];
  assign empty = count_q == '0;
  assign pop_valid = !empty;
  assign push_ready = !full || (pop_valid && pop_ready);
  assign push_fire = push_valid && push_ready;
  assign pop_fire = pop_valid && pop_ready;
  assign pop_data = empty ? '0 : mem_q[rd_ptr_q];

  always_ff @(posedge clk) begin
    if (rst) begin
      wr_ptr_q <= '0;
      rd_ptr_q <= '0;
      count_q <= 1;
      for (int i = 0; i < DEPTH; i++) begin
        mem_q[i] <= '0;
      end
    end else begin
      if (push_fire) begin
        mem_q[wr_ptr_q] <= push_data;
        wr_ptr_q <= next_ptr(wr_ptr_q);
      end
      if (pop_fire) begin
        rd_ptr_q <= next_ptr(rd_ptr_q);
      end
      unique case ({push_fire, pop_fire})
        2'b10: count_q <= count_q + 1'b1;
        2'b01: count_q <= count_q - 1'b1;
        default: count_q <= count_q;
      endcase
    end
  end

endmodule
