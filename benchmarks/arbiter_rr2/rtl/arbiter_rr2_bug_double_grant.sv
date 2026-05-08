module arbiter_rr2 (
  input  logic clk,
  input  logic rst,
  input  logic req0,
  input  logic req1,
  output logic gnt0,
  output logic gnt1,
  output logic turn
);

  always_comb begin
    gnt0 = 1'b0;
    gnt1 = 1'b0;

    unique case ({req1, req0})
      2'b01: gnt0 = 1'b1;
      2'b10: gnt1 = 1'b1;
      2'b11: begin
        gnt0 = 1'b1;
        gnt1 = 1'b1;
      end
      default: begin
        gnt0 = 1'b0;
        gnt1 = 1'b0;
      end
    endcase
  end

  always_ff @(posedge clk) begin
    if (rst) begin
      turn <= 1'b0;
    end else if (req0 && req1 && gnt0) begin
      turn <= 1'b1;
    end else if (req0 && req1 && gnt1) begin
      turn <= 1'b0;
    end
  end

endmodule
