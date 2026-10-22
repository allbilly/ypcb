# Resume the full DDR800 JTAG design from a preserved constrained placed DCP.
# Arguments: placed.dcp new-output-directory expected-port-constraints.tsv
# This only builds local artifacts; it never connects to or programs hardware.
set_param general.maxThreads 8
if {[llength $argv] != 3} {error "expected placed DCP, new output directory and pin inventory"}
lassign $argv placed_dcp out_dir pins_file
set placed_dcp [file normalize $placed_dcp]
set out_dir [file normalize $out_dir]
if {![file isfile $placed_dcp]} {error "missing placed checkpoint: $placed_dcp"}
if {[file exists $out_dir]} {error "refusing to overwrite output: $out_dir"}
file mkdir $out_dir

proc phase {value} {
    global out_dir
    set fp [open [file join $out_dir stage.txt] w]
    puts $fp $value
    puts $fp [clock format [clock seconds] -gmt true -format {%Y-%m-%dT%H:%M:%SZ}]
    close $fp
    puts "YPCB_NATIVE_STAGE $value"
}

proc drc_gate {name} {
    global out_dir
    report_drc -file [file join $out_dir $name.rpt]
    set errors {}
    foreach violation [get_drc_violations -quiet] {
        if {[string equal -nocase [get_property SEVERITY $violation] Error]} {
            lappend errors [get_property NAME $violation]
        }
    }
    if {[llength $errors]} {error "$name has DRC errors: $errors"}
}

phase OPEN_PLACED_CHECKPOINT
open_checkpoint $placed_dcp
if {[get_property TOP [current_design]] ne "otpu_fpga_top_openxc7_jtag"} {
    error "wrong standalone top: [current_design]"
}
if {[get_property PART [current_design]] ne "xc7k480tffg1156-2"} {
    error "wrong target part"
}

phase VERIFY_BOARD_AND_FULL_DESIGN
set expected [dict create]
set fp [open $pins_file r]
while {[gets $fp line] >= 0} {
    lassign [split $line "\t"] name pin standard
    if {$name eq "" || $pin eq "" || $standard eq "" || [dict exists $expected $name]} {
        error "invalid pin inventory row: $line"
    }
    dict set expected $name [list $pin $standard]
}
close $fp
set ports [get_ports]
if {[llength $ports] != 243 || [dict size $expected] != 243} {
    error "full standalone design must have all 243 board port bits"
}
set fp [open [file join $out_dir checkpoint-audit.txt] w]
puts $fp "PART=[get_property PART [current_design]]"
puts $fp "TOP=[get_property TOP [current_design]]"
puts $fp "CHECKPOINT_NAME=[get_property NAME [current_design]]"
puts $fp "MAX_THREADS=[get_param general.maxThreads]"
puts $fp "PORTS=[llength $ports]"
foreach port $ports {
    set name [get_property NAME $port]
    if {![dict exists $expected $name]} {error "unexpected board port: $name"}
    lassign [dict get $expected $name] pin standard
    if {[get_property PACKAGE_PIN $port] ne $pin || [get_property IOSTANDARD $port] ne $standard} {
        error "board pin or I/O standard mismatch: $name"
    }
    puts $fp "PORT\t$name\t$pin\t$standard"
}
foreach {property expected_value} {CFGBVS GND CONFIG_VOLTAGE 1.8} {
    set actual [get_property $property [current_design]]
    if {$actual ne $expected_value} {error "configuration mismatch: $property=$actual"}
    puts $fp "$property=$actual"
}
set scans [get_cells -quiet -hier -filter {REF_NAME == BSCANE2}]
if {[llength $scans] != 1} {error "standalone JTAG image requires exactly one BSCANE2"}
set scan [lindex $scans 0]
set properties [list_property $scan]
set chain_property ""
foreach candidate {JTAG_CHAIN CONFIG.JTAG_CHAIN} {
    if {[lsearch -exact $properties $candidate] >= 0} {set chain_property $candidate; break}
}
if {$chain_property eq "" || [get_property $chain_property $scan] != 2} {
    error "standalone image does not select JTAG USER2"
}
puts $fp "JTAG_CHAIN=[get_property $chain_property $scan]"
foreach type {DSP48E1 RAMB36E1 RAMB18E1 ISERDESE2 OSERDESE2 IDELAYE2 MMCME2_ADV PLLE2_ADV} {
    puts $fp "$type=[llength [get_cells -quiet -hier -filter "REF_NAME == $type"]]"
}
if {[llength [get_cells -quiet -hier -filter {REF_NAME == DSP48E1}]] < 700} {
    error "full accelerator DSP scope missing"
}
if {[llength [get_cells -quiet -hier -filter {REF_NAME == ISERDESE2}]] != 144 ||
    [llength [get_cells -quiet -hier -filter {REF_NAME == OSERDESE2}]] != 214} {
    error "both complete DDR channels are required"
}
close $fp
report_io -file [file join $out_dir checkpoint-io.rpt]
report_clocks -file [file join $out_dir checkpoint-clocks.rpt]
drc_gate pre-route-drc

phase PHYSICAL_OPTIMIZATION
phys_opt_design
phase ROUTING
route_design
phase REPORTS_AND_ROUTED_CHECKPOINT
report_route_status -file [file join $out_dir route-status.rpt]
report_utilization -hierarchical -file [file join $out_dir final-utilization.rpt]
report_timing_summary -delay_type min_max -report_unconstrained \
    -check_timing_verbose -file [file join $out_dir final-timing.rpt]
report_bus_skew -file [file join $out_dir final-bus-skew.rpt]
report_cdc -file [file join $out_dir final-cdc.rpt]
write_checkpoint [file join $out_dir final-routed.dcp]
drc_gate final-drc

phase TIMING_GATE
# This gate covers constrained setup/hold paths only. The reports above retain
# external-I/O coverage, pulse-width, bus-skew and CDC findings for review;
# passing this gate is not full DDR timing or physical-hardware qualification.
set setup [get_timing_paths -delay_type max -max_paths 1 -nworst 1]
set hold [get_timing_paths -delay_type min -max_paths 1 -nworst 1]
if {[llength $setup] != 1 || [llength $hold] != 1} {error "missing setup/hold timing paths"}
set wns [get_property SLACK $setup]
set whs [get_property SLACK $hold]
set fp [open [file join $out_dir timing-gate.txt] w]
puts $fp "WNS=$wns"
puts $fp "WHS=$whs"
close $fp
if {$wns < 0 || $whs < 0} {error "timing closure incomplete: WNS=$wns WHS=$whs"}

phase WRITE_BITSTREAM
# Preserve the board's configuration voltage, unused-pin and BPI properties.
# Normal Vivado bitstream DRC remains enabled; no severities are downgraded.
write_bitstream [file join $out_dir design.bit]
phase VIVADO_BITSTREAM_GENERATED_PHYSICAL_TEST_NOT_RUN
close_design
exit 0
