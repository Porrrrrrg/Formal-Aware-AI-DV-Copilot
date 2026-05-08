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

  assign out_valid = full;
  assign out_data = data_q;
  assign in_ready = 1'b1;

  always_ff @(posedge clk) begin
    if (rst) begin
      full <= 1'b0;
      data_q <= '0;
    end else begin
      if (in_valid) begin
        full <= 1'b1;
        data_q <= in_data;
      end else if (out_valid && out_ready) begin
        full <= 1'b0;
      end
    end
  end

endmodule
