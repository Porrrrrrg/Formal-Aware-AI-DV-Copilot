# Common JasperLoop-DV JasperGold helpers.

proc jl_getenv {name default_value} {
  if {[info exists ::env($name)]} {
    return $::env($name)
  }
  return $default_value
}

proc jl_report_dir {} {
  set report_dir [jl_getenv JASPERLOOP_REPORT_DIR "jasper/reports/local"]
  file mkdir $report_dir
  return $report_dir
}

proc jl_mode {} {
  return [jl_getenv JASPERLOOP_MODE "prove"]
}

proc jl_rtl {} {
  return [jl_getenv JASPERLOOP_RTL ""]
}

proc jl_report_property_status {} {
  set report_dir [jl_report_dir]
  report -summary -results -detailed -file "$report_dir/properties.rpt" -force
}
