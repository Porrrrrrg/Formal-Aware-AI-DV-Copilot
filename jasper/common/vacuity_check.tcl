source jasper/common/jg_common.tcl
check_vacuity -all
set report_dir [jl_report_dir]
redirect -file "$report_dir/vacuity.rpt" {report -vacuity -all}
