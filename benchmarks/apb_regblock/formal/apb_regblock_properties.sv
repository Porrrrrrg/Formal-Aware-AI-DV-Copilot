module apb_regblock_properties (
  input logic        pclk,
  input logic        presetn,
  input logic        psel,
  input logic        penable,
  input logic        pwrite,
  input logic [7:0]  paddr,
  input logic [31:0] pwdata,
  input logic [31:0] prdata,
  input logic        pready,
  input logic        pslverr,
  input logic [31:0] reg0,
  input logic [31:0] reg1
);

  p_setup_then_enable: assert property (@(posedge pclk) disable iff (!presetn) psel && !penable |=> psel && penable);
  p_write_updates_reg0: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && pwrite && pready && paddr == 8'h00 |=> reg0 == $past(pwdata));
  p_write_updates_reg1: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && pwrite && pready && paddr == 8'h04 |=> reg1 == $past(pwdata));
  p_read_returns_reg0: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && !pwrite && paddr == 8'h00 |-> prdata == reg0);
  p_read_returns_reg1: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && !pwrite && paddr == 8'h04 |-> prdata == reg1);
  p_no_write_without_access: assert property (@(posedge pclk) disable iff (!presetn) !(psel && penable && pwrite) |=> reg0 == $past(reg0) && reg1 == $past(reg1));
  p_pready_response_valid: assert property (@(posedge pclk) disable iff (!presetn) psel && penable |-> pready);
  p_reset_clears_registers: assert property (@(posedge pclk) !presetn |=> reg0 == 32'h0 && reg1 == 32'h0);
  p_invalid_address_behavior: assert property (@(posedge pclk) disable iff (!presetn) psel && penable && !(paddr inside {8'h00, 8'h04}) |-> pslverr);

  cov_write_reg0_then_read: cover property (@(posedge pclk) disable iff (!presetn) psel && penable && pwrite && paddr == 8'h00 ##1 psel && penable && !pwrite && paddr == 8'h00);
  cov_invalid_address: cover property (@(posedge pclk) disable iff (!presetn) psel && penable && paddr == 8'h08 && pslverr);

endmodule
