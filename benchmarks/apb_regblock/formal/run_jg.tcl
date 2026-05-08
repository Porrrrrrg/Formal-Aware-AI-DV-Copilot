clear -all
source jasper/common/jg_common.tcl

set rtl_file [jl_rtl]
if {$rtl_file == ""} {
  set rtl_file "benchmarks/apb_regblock/rtl/apb_regblock_correct.sv"
}

analyze -sv $rtl_file
analyze -sv benchmarks/apb_regblock/formal/apb_regblock_assumptions.sv
analyze -sv benchmarks/apb_regblock/formal/apb_regblock_properties.sv
analyze -sv benchmarks/apb_regblock/formal/apb_regblock_harness.sv
elaborate -top apb_regblock_harness
clock pclk
reset -expression {!presetn}

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
