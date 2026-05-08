source jasper/common/jg_common.tcl
cover -all
set report_dir [jl_report_dir]
redirect -file "$report_dir/cover.rpt" {report -cover -all}
