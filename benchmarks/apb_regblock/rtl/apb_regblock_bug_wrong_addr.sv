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

  logic access;
  logic valid_addr;

  assign access = psel && penable;
  assign valid_addr = (paddr == 8'h00) || (paddr == 8'h04);
  assign pready = 1'b1;
  assign pslverr = access && !valid_addr;

  always_comb begin
    prdata = 32'h0;
    if (paddr == 8'h00) begin
      prdata = reg1;
    end else if (paddr == 8'h04) begin
      prdata = reg0;
    end
  end

  always_ff @(posedge pclk or negedge presetn) begin
    if (!presetn) begin
      reg0 <= 32'h0;
      reg1 <= 32'h0;
    end else if (access && pwrite && valid_addr) begin
      if (paddr == 8'h00) begin
        reg1 <= pwdata;
      end else begin
        reg0 <= pwdata;
      end
    end
  end

endmodule
