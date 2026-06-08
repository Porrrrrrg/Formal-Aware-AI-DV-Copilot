clear -all
source jasper/common/jg_common.tcl

set rtl_file [jl_rtl]
set rtl_files [jl_getenv JASPERLOOP_RTL_FILES ""]
set assumptions_file [jl_getenv JASPERLOOP_ASSUMPTIONS ""]
set assumption_files [jl_getenv JASPERLOOP_ASSUMPTION_FILES ""]
set generated_properties_file [jl_getenv JASPERLOOP_GENERATED_PROPERTIES ""]
set generated_harness_file [jl_getenv JASPERLOOP_GENERATED_HARNESS ""]
set top_module [jl_getenv JASPERLOOP_TOP ""]
set clock_signal [jl_getenv JASPERLOOP_CLOCK ""]
set reset_command [jl_getenv JASPERLOOP_RESET_CMD ""]
set formal_mode [jl_getenv JASPERLOOP_FORMAL_MODE "prove"]
set report_dir [jl_report_dir]

if {$rtl_file == ""} {
  error "JASPERLOOP_RTL is required"
}
if {$generated_properties_file == ""} {
  error "JASPERLOOP_GENERATED_PROPERTIES is required"
}
if {$generated_harness_file == ""} {
  error "JASPERLOOP_GENERATED_HARNESS is required"
}
if {$top_module == ""} {
  error "JASPERLOOP_TOP is required"
}
if {$clock_signal == ""} {
  error "JASPERLOOP_CLOCK is required"
}

if {$rtl_files != ""} {
  foreach rtl_path [split $rtl_files "\n"] {
    if {$rtl_path != ""} {
      analyze -sv $rtl_path
    }
  }
} else {
  analyze -sv $rtl_file
}
if {$assumption_files != ""} {
  foreach assumption_path [split $assumption_files "\n"] {
    if {$assumption_path != ""} {
      analyze -sv $assumption_path
    }
  }
} elseif {$assumptions_file != ""} {
  analyze -sv $assumptions_file
}
analyze -sv $generated_properties_file
analyze -sv $generated_harness_file
elaborate -top $top_module
clock $clock_signal

if {$reset_command != ""} {
  eval $reset_command
}

file mkdir "$report_dir/traces"
if {$formal_mode == "cover"} {
  # JasperGold 2018 reports cover-property reachability through prove -all;
  # the older Moore build does not support an all-properties cover switch.
  prove -all
  report -summary -results -detailed -file "$report_dir/cover.rpt" -force
} elseif {$formal_mode == "vacuity"} {
  check_vacuity -all
  report -summary -results -detailed -file "$report_dir/vacuity.rpt" -force
} else {
  prove -all -dump_trace -dump_trace_type vcd -dump_trace_dir "$report_dir/traces"
  report -summary -results -detailed -file "$report_dir/properties.rpt" -force

  if {[catch {check_vacuity -all} vacuity_error]} {
    set fh [open "$report_dir/vacuity_error.txt" "w"]
    puts $fh $vacuity_error
    close $fh
  } else {
    report -summary -results -detailed -file "$report_dir/vacuity.rpt" -force
  }
}
