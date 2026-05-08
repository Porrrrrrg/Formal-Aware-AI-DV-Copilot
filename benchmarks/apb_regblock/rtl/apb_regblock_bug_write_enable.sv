module apb_regblock (
  input  logic        pclk,
  input  logic        presetn,
  input  logic        psel,
  input  logic        penable,
  input  logic        pwrite,
  input  logic [7:0]  paddr,
  input  logic [31:0] pwdata,
  output logic [31:0] prdata,
  output logic        pready,
  output logic        pslverr,
  output logic [31:0] reg0,
  output logic [31:0] reg1
);

  logic valid_addr;

  assign valid_addr = (paddr == 8'h00) || (paddr == 8'h04);
  assign pready = 1'b1;
  assign pslverr = psel && penable && !valid_addr;

  always_comb begin
    prdata = (paddr == 8'h04) ? reg1 : reg0;
  end

  always_ff @(posedge pclk or negedge presetn) begin
    if (!presetn) begin
      reg0 <= 32'h0;
      reg1 <= 32'h0;
    end else if (psel && pwrite && valid_addr) begin
      if (paddr == 8'h00) begin
        reg0 <= pwdata;
      end else begin
        reg1 <= pwdata;
      end
    end
  end

endmodule
