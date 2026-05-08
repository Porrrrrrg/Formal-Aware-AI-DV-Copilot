module rv_buffer_properties #(
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

  p_reset_empty: assert property (@(posedge clk) rst |=> !full && !out_valid);
  p_out_valid_equals_full: assert property (@(posedge clk) disable iff (rst) out_valid == full);
  p_in_ready_when_empty: assert property (@(posedge clk) disable iff (rst) !full |-> in_ready);
  p_in_ready_when_full_and_out_ready: assert property (@(posedge clk) disable iff (rst) full && out_ready |-> in_ready);
  p_data_stable_while_stalled: assert property (@(posedge clk) disable iff (rst) out_valid && !out_ready |=> out_valid && $stable(out_data));
  p_capture_on_input_fire: assert property (@(posedge clk) disable iff (rst) in_valid && in_ready |=> full && out_data == $past(in_data));
  p_full_set_on_enqueue: assert property (@(posedge clk) disable iff (rst) in_valid && in_ready && !out_ready |=> full);
  p_full_clear_on_dequeue: assert property (@(posedge clk) disable iff (rst) out_valid && out_ready && !in_valid |=> !full);
  p_simultaneous_enqueue_dequeue_semantics: assert property (@(posedge clk) disable iff (rst) full && in_valid && in_ready && out_ready |=> full && out_data == $past(in_data));

  cov_simultaneous_enqueue_dequeue: cover property (@(posedge clk) disable iff (rst) full && in_valid && in_ready && out_ready);
  cov_stall_then_dequeue: cover property (@(posedge clk) disable iff (rst) out_valid && !out_ready ##1 out_valid && out_ready);

endmodule
