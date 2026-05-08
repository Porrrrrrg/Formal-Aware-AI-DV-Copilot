module apb_regblock_assumptions (
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

  a_reset_initial: assume property (@(posedge pclk) $initstate |-> !presetn);
  a_reset_deasserts: assume property (@(posedge pclk) !presetn |=> presetn);
  a_no_x_controls: assume property (@(posedge pclk) !$isunknown({presetn, psel, penable, pwrite, paddr}));
  a_apb_enable_follows_setup: assume property (@(posedge pclk) disable iff (!presetn) psel && !penable |=> psel && penable);

endmodule
