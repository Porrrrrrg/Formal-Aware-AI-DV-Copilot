module rv_buffer #(
  parameter int WIDTH = 8
) (
  input  logic             clk,
  input  logic             rst,
  input  logic             in_valid,
  output logic             in_ready,
  input  logic [WIDTH-1:0] in_data,
  output logic             out_valid,
  input  logic             out_ready,
  output logic [WIDTH-1:0] out_data,
  output logic             full
);

  logic [WIDTH-1:0] data_q;
  logic input_fire;
  logic output_fire;

  assign out_valid = full;
  assign out_data = data_q;
  assign in_ready = !full;
  assign input_fire = in_valid && in_ready;
  assign output_fire = out_valid && out_ready;

  always_ff @(posedge clk) begin
    if (rst) begin
      full <= 1'b0;
      data_q <= '0;
    end else if (input_fire) begin
      full <= 1'b1;
      data_q <= in_data;
    end else if (output_fire) begin
      full <= 1'b0;
    end
  end

endmodule
