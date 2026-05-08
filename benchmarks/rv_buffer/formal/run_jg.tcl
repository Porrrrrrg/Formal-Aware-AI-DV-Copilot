clear -all
source jasper/common/jg_common.tcl

set rtl_file [jl_rtl]
if {$rtl_file == ""} {
  set rtl_file "benchmarks/rv_buffer/rtl/rv_buffer_correct.sv"
}

analyze -sv $rtl_file
analyze -sv benchmarks/rv_buffer/formal/rv_buffer_assumptions.sv
analyze -sv benchmarks/rv_buffer/formal/rv_buffer_properties.sv
analyze -sv benchmarks/rv_buffer/formal/rv_buffer_harness.sv
elaborate -top rv_buffer_harness
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
