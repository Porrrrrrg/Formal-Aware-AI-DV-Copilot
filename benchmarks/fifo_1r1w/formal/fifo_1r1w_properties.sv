module fifo_1r1w_properties #(
  parameter int WIDTH = 8,
  parameter int DEPTH = 4,
  parameter int ADDR_W = $clog2(DEPTH),
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

  logic [WIDTH-1:0] ref_mem [DEPTH];
  logic [ADDR_W-1:0] ref_wr_q;
  logic [ADDR_W-1:0] ref_rd_q;
  logic [COUNT_W-1:0] ref_count_q;

  function automatic logic [ADDR_W-1:0] next_ptr(input logic [ADDR_W-1:0] ptr);
    if (ptr == DEPTH[ADDR_W-1:0] - 1'b1) begin
      next_ptr = '0;
    end else begin
      next_ptr = ptr + 1'b1;
    end
  endfunction

  always_ff @(posedge clk) begin
    if (rst) begin
      ref_wr_q <= '0;
      ref_rd_q <= '0;
      ref_count_q <= '0;
      for (int i = 0; i < DEPTH; i++) begin
        ref_mem[i] <= '0;
      end
    end else begin
      if (push_fire && ref_count_q < DEPTH[COUNT_W-1:0]) begin
        ref_mem[ref_wr_q] <= push_data;
        ref_wr_q <= next_ptr(ref_wr_q);
      end
      if (pop_fire && ref_count_q != '0) begin
        ref_rd_q <= next_ptr(ref_rd_q);
      end
      unique case ({push_fire, pop_fire})
        2'b10: if (ref_count_q < DEPTH[COUNT_W-1:0]) ref_count_q <= ref_count_q + 1'b1;
        2'b01: if (ref_count_q != '0) ref_count_q <= ref_count_q - 1'b1;
        default: ref_count_q <= ref_count_q;
      endcase
    end
  end

  p_reset_empty: assert property (@(posedge clk) rst |=> empty && !full && level == '0 && !pop_valid);
  p_level_bounds: assert property (@(posedge clk) disable iff (rst) level <= DEPTH[COUNT_W-1:0]);
  p_flags_match_level: assert property (
    @(posedge clk) disable iff (rst)
      (empty == (level == '0)) && (full == (level == DEPTH[COUNT_W-1:0]))
  );
  p_no_underflow: assert property (@(posedge clk) disable iff (rst) !(empty && pop_fire));
  p_no_overflow: assert property (
    @(posedge clk) disable iff (rst)
      full && push_valid && !pop_ready |-> !push_ready
  );
  p_level_increments_on_push: assert property (
    @(posedge clk) disable iff (rst)
      push_fire && !pop_fire |=> level == $past(level) + 1'b1
  );
  p_level_decrements_on_pop: assert property (
    @(posedge clk) disable iff (rst)
      pop_fire && !push_fire |=> level == $past(level) - 1'b1
  );
  p_simultaneous_push_pop_full: assert property (
    @(posedge clk) disable iff (rst)
      full && push_valid && pop_ready |-> (push_ready && push_fire && pop_fire) ##1 (full && level == $past(level))
  );
  p_pop_data_stable_when_stalled: assert property (
    @(posedge clk) disable iff (rst)
      pop_valid && !pop_ready |=> pop_valid && $stable(pop_data)
  );
  p_fifo_ordering: assert property (
    @(posedge clk) disable iff (rst)
      pop_fire |-> ref_count_q != '0 && pop_data == ref_mem[ref_rd_q]
  );
  p_eventual_pop: assert property (@(posedge clk) disable iff (rst) pop_valid |-> ##[0:4] pop_fire);

  cov_fill_to_full: cover property (@(posedge clk) disable iff (rst) !full ##1 push_fire [*4] ##1 full);
  cov_simultaneous_full_push_pop: cover property (
    @(posedge clk) disable iff (rst)
      full && push_valid && push_ready && pop_ready && push_fire && pop_fire
  );
  cov_reset_release_first_push: cover property (@(posedge clk) rst ##1 !rst ##[1:3] push_fire);
  cov_stall_then_pop: cover property (
    @(posedge clk) disable iff (rst)
      pop_valid && !pop_ready ##1 pop_valid && pop_ready
  );
  cov_invalid_empty_and_full: cover property (@(posedge clk) disable iff (rst) empty && full);

endmodule
