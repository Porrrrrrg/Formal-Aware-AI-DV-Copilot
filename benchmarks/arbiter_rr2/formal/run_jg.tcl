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
  redirect -file "$report_dir/cover.rpt" {report -cover -all}
} elseif {$mode == "vacuity"} {
  check_vacuity -all
  redirect -file "$report_dir/vacuity.rpt" {report -vacuity -all}
} else {
  prove -all
  redirect -file "$report_dir/properties.rpt" {report -property -all}
}
