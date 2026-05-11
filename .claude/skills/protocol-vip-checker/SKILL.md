---
name: protocol-vip-checker
description: Review bus protocol compliance checks and assertions for standard DUT interfaces.
---

# Protocol VIP Checker Skill

## Description

Verify structural and behavioral compliance of DUT interfaces against standard bus protocol specifications. Covers AXI4/AXI4-Lite/AXI4-Stream, APB, AHB, CHI, and custom handshake protocols. Checks include mandatory signal presence, handshake ordering, response legality, channel pairing, timeout detection, and protocol-specific assertion coverage.

- **Requires:** SystemVerilog simulator with SVA support; UVM optional for integration
- **Supported Protocols:** AXI4, AXI4-Lite, AXI4-Stream, APB3/APB4, AHB2/AHB5, CHI (basic), custom valid/ready

> **Expertise:**
> You are an expert in on-chip bus protocol specifications and verification IP design. You understand the full transaction lifecycle for each protocol, legal and illegal operation sequences, response ordering rules, and how to write assertions that catch protocol violations early in simulation.

---

## Disclaimer

> **Append this notice to your first output:**
>
> `Note: VIP checks are based on static protocol specification rules. Protocol compliance in full-system context (QoS, ordering, ID reuse) may require additional integration-level checks. Consult the full protocol specification for edge cases not covered here.`

---

## When to Use This Skill

Trigger this skill when users:
- Ask to verify AXI, APB, AHB, or CHI interface compliance
- Mention protocol violation, assertion failure, or handshake error
- Need to add protocol checkers or assertions to an interface
- Ask about signal ordering, response legality, or ID reuse rules
- Mention terms like: "VIP", "protocol checker", "AXI compliance", "handshake", "RRESP", "BRESP", "SLVERR", "DECERR", "ordering"

---

## Core Workflow

### Step 1 -Gather Context

- **Protocol and Version:** AXI4 / AXI4-Lite / APB3 / AHB5 / CHI-B
- **Interface Role:** Master (initiator) or slave (target)
- **Check Depth:** Structural only, handshake/ordering, or full compliance
- **Timeout Values:** Maximum allowed cycles for response (default: 1000 cycles)
- **ID Width:** For AXI -number of outstanding transaction IDs

---

### Step 2 -Protocol Compliance Checks

#### 2.1 AXI4 Checks

**Structural completeness:**

| Channel | Required Signals | Optional |
|---------|-----------------|---------|
| AW | AWVALID, AWREADY, AWADDR, AWLEN, AWSIZE, AWBURST, AWID | AWLOCK, AWCACHE, AWPROT, AWQOS |
| W  | WVALID, WREADY, WDATA, WSTRB, WLAST | -|
| B  | BVALID, BREADY, BRESP, BID | -|
| AR | ARVALID, ARREADY, ARADDR, ARLEN, ARSIZE, ARBURST, ARID | ARLOCK, ARCACHE, ARPROT, ARQOS |
| R  | RVALID, RREADY, RDATA, RRESP, RLAST, RID | -|

**Handshake assertions:**

```systemverilog
// AXI rule: once VALID is asserted, it must not deassert before READY
property axi_valid_stable_aw;
  @(posedge aclk) disable iff (!aresetn)
  ($rose(awvalid) && !awready) |=> awvalid;
endproperty
assert property (axi_valid_stable_aw)
  else `uvm_error("AXI_VIP", "AWVALID deasserted before AWREADY -protocol violation")

// WLAST must match AWLEN beat count
property axi_wlast_beat_count;
  @(posedge aclk) disable iff (!aresetn)
  (awvalid && awready) |->
    ##[1:$] (wvalid && wready && wlast) ##0 (beat_count == awlen + 1);
endproperty

// BID must match AWID of completed write
property axi_bid_matches_awid;
  @(posedge aclk) disable iff (!aresetn)
  (bvalid && bready) |-> (bid == pending_awid);
endproperty
```

**Response legality:**

```systemverilog
// BRESP must be OKAY or SLVERR or DECERR (no EXOKAY for non-exclusive)
property axi_bresp_legal;
  @(posedge aclk) disable iff (!aresetn)
  (bvalid) |-> (bresp inside {2'b00, 2'b10, 2'b11});
endproperty

// RLAST must assert exactly once per transaction
property axi_rlast_once_per_burst;
  @(posedge aclk) disable iff (!aresetn)
  (rvalid && rready && rlast) |->
    ##1 !(rvalid && !arvalid);  // No extra beats after RLAST
endproperty
```

**Timeout assertions:**

```systemverilog
// AW channel: response must come within timeout
property axi_aw_timeout;
  @(posedge aclk) disable iff (!aresetn)
  (awvalid && !awready) |-> ##[1:AXI_TIMEOUT] awready;
endproperty
assert property (axi_aw_timeout)
  else `uvm_error("AXI_TIMEOUT", "AWREADY not seen within timeout")
```

---

#### 2.2 AXI4-Lite Checks

Additional restrictions beyond AXI4:
- No burst transactions (AWLEN/ARLEN must be 0)
- No exclusive access
- No QoS, cache, or region signals required
- Data width must be 32 or 64 bits

```systemverilog
property axilite_no_burst;
  @(posedge aclk) disable iff (!aresetn)
  (awvalid) |-> (awlen == 8'd0);
endproperty

property axilite_data_width;
  @(posedge aclk) disable iff (!aresetn)
  (wvalid) |-> ($bits(wdata) inside {32, 64});
endproperty
```

---

#### 2.3 APB Checks

```systemverilog
// Setup phase must precede enable phase by exactly 1 cycle
property apb_setup_before_enable;
  @(posedge pclk) disable iff (!presetn)
  ($rose(psel) && !penable) |=> penable;
endproperty

// PSEL must remain asserted through enable phase
property apb_sel_stable;
  @(posedge pclk) disable iff (!presetn)
  (psel && penable && !pready) |=> (psel && penable);
endproperty

// Write strobe must be zero for reads
property apb_strb_zero_on_read;
  @(posedge pclk) disable iff (!presetn)
  (psel && !pwrite) |-> (pstrb == '0);
endproperty
```

---

#### 2.4 AHB Checks

```systemverilog
// HADDR must be stable during data phase
property ahb_addr_stable_data_phase;
  @(posedge hclk) disable iff (!hresetn)
  (hready && htrans inside {2'b10, 2'b11}) |=>
    $stable(haddr) until hready;
endproperty

// HTRANS must not go to NONSEQ in middle of burst without IDLE/BUSY
property ahb_burst_seq;
  @(posedge hclk) disable iff (!hresetn)
  (htrans == 2'b11) |-> ##1 (htrans inside {2'b01, 2'b11});
endproperty
```

---

### Step 3 -Coverage for Protocol Compliance

```systemverilog
covergroup axi4_protocol_cg @(posedge aclk);
  cp_bresp:  coverpoint bresp iff (bvalid && bready) {
    bins okay   = {2'b00};
    bins slverr = {2'b10};
    bins decerr = {2'b11};
  }
  cp_burst:  coverpoint awburst iff (awvalid && awready) {
    bins fixed = {2'b00};
    bins incr  = {2'b01};
    bins wrap  = {2'b10};
  }
  cp_size:   coverpoint awsize iff (awvalid && awready);
  cp_len:    coverpoint awlen iff (awvalid && awready) {
    bins single = {8'd0};
    bins short  = {[8'd1:8'd15]};
    bins medium = {[8'd16:8'd63]};
    bins long   = {[8'd64:8'd255]};
  }
  cx_burst_x_resp: cross cp_burst, cp_bresp;
endgroup
```

---

## Helper Scripts Reference

| Script | Purpose |
|--------|---------|
| `protocol_assertion_gen.py` | Generates complete SVA assertion set for a specified protocol and role (master/slave) |
| `vip_coverage_gen.py` | Generates protocol-specific covergroups covering all mandatory transaction types and responses |
| `timeout_monitor.py` | Configurable channel timeout monitor -flags any channel stall exceeding threshold |
| `protocol_signal_checker.py` | Verifies all mandatory protocol signals are present in the RTL interface and connected |

---

## Validation Checklist

- [ ] All mandatory protocol signals present and connected
- [ ] Handshake assertions cover VALID stability, READY/VALID handshake, and LAST signaling
- [ ] Response legality assertions cover all legal response codes
- [ ] Timeout assertions configured per channel with project-appropriate values
- [ ] Protocol coverage group instantiated in monitor
- [ ] Assertions verified to fire on known-bad stimulus before integration
