module apb_regblock_harness;
  logic pclk;
  logic presetn;
  logic psel;
  logic penable;
  logic pwrite;
  logic [7:0] paddr;
  logic [31:0] pwdata;
  logic [31:0] prdata;
  logic pready;
  logic pslverr;
  logic [31:0] reg0;
  logic [31:0] reg1;

  apb_regblock dut (.*);

  apb_regblock_assumptions assumptions_i (.*);
  apb_regblock_properties properties_i (.*);
endmodule
