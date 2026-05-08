clear -all
source jasper/common/jg_common.tcl

set rtl_file [jl_rtl]
if {$rtl_file == ""} {
  set rtl_file "benchmarks/arbiter_rr2/rtl/arbiter_rr2_correct.sv"
}

analyze -sv $rtl_file
analyze -sv benchmarks/arbiter_rr2/formal/arbiter_rr2_assumptions.sv
analyze -sv benchmarks/arbiter_rr2/formal/arbiter_rr2_properties.sv
analyze -sv benchmarks/arbiter_rr2/formal/arbiter_rr2_harness.sv
elaborate -top arbiter_rr2_harness
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
