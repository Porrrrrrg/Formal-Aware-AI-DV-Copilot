clear -all
source jasper/common/jg_common.tcl

set rtl_file [jl_rtl]
if {$rtl_file == ""} {
  set rtl_file "benchmarks/fifo_1r1w/rtl/fifo_1r1w_correct.sv"
}

analyze -sv $rtl_file
analyze -sv benchmarks/fifo_1r1w/formal/fifo_1r1w_assumptions.sv
analyze -sv benchmarks/fifo_1r1w/formal/fifo_1r1w_properties.sv
analyze -sv benchmarks/fifo_1r1w/formal/fifo_1r1w_harness.sv
elaborate -top fifo_1r1w_harness
clock clk
reset rst

set mode [jl_mode]
set report_dir [jl_report_dir]

if {$mode == "cover"} {
  cover -all
  report -summary -results -detailed -file "$report_dir/cover.rpt" -force
} elseif {$mode == "vacuity"} {
  check_vacuity -all
  report -summary -results -detailed -file "$report_dir/vacuity.rpt" -force
} else {
  file mkdir "$report_dir/traces"
  prove -all -dump_trace -dump_trace_type vcd -dump_trace_dir "$report_dir/traces"
  report -summary -results -detailed -file "$report_dir/properties.rpt" -force
}
