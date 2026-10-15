# XSDB: download a BRAM-resident application and capture its real MDM UART.
# Arguments: ELF hw_server_URL UART_log timeout_ms ?ddr_diag|systest|ddr_full?
if {[llength $argv] ni {4 5}} {
    error "usage: fedora_cpu_run.tcl ELF hw_server_URL UART_log timeout_ms ?ddr_diag|systest|ddr_full?"
}
lassign $argv elf server logfile timeout application
if {$application == ""} {set application ddr_diag}
if {$application ni {ddr_diag systest ddr_full}} {error "Unknown application: $application"}
connect -url $server
after 1500
puts "JTAG target properties: [targets -target-properties]"
# The MDM is also named MicroBlaze. Select the processor entry while keeping
# the single-processor guard before stop/reset/download operations.
set cpus [targets -target-properties -filter {name =~ "MicroBlaze #*"}]
if {[llength $cpus] != 1} {
    error "Expected exactly one MicroBlaze target, found [llength $cpus]"
}
set cpu [lindex $cpus 0]
set uart_ctx [dict get $cpu parent_ctx]
targets [dict get $cpu target_id]
if {![dict exists $cpu suspended] || ![dict get $cpu suspended]} {stop}
rst -processor
dow $elf
# The UART belongs to the MDM parent. Supply its context explicitly; the
# installed XSDB changes the CPU context to its parent without refreshing the
# cached UART properties when given a processor context.
set port [jtagterminal -ctx $uart_ctx -socket]
set uart [socket 127.0.0.1 $port]
fconfigure $uart -blocking 0 -buffering none -translation binary
set output [open $logfile w]
fconfigure $output -buffering none -translation binary
set transcript ""
set requested 0
set done 0
set command_timers {}
set sent_commands {}
set peripheral_response ""
set peripheral_complete 0
proc send_uart_command {command} {
    global uart sent_commands
    puts -nonewline $uart $command
    flush $uart
    puts "HOST_SENT $command"
    flush stdout
    lappend sent_commands $command
}
proc receive_uart {} {
    global uart output transcript requested done application command_timers
    global sent_commands peripheral_response peripheral_complete
    set chunk [read $uart]
    if {$chunk != ""} {
        puts -nonewline $output $chunk
        puts -nonewline stdout $chunk
        flush stdout
        append transcript $chunk
        if {$application == "ddr_diag" && !$requested &&
            [string first "READY FOR DDR send=m" $transcript] >= 0} {
            send_uart_command m
            set requested 1
        }
        if {$application == "ddr_full" && !$requested &&
            [string first "READY FOR FULL DDR send=f" $transcript] >= 0} {
            send_uart_command f
            set requested 1
        }
        if {$application == "systest" && !$requested &&
            [string first "Press 'r','g','y' to toggle LEDs. Press 'm' to run memory test. 't' to get temperature." $transcript] >= 0} {
            set delay 0
            foreach command {r r g g y y t} {
                lappend command_timers [after $delay [list send_uart_command $command]]
                incr delay 500
            }
            set requested 1
        }
        if {[regexp {DDR RESULT (PASS checks=6|FAIL)\r?\n} $transcript] ||
            [regexp {DDR FULL RESULT (PASS checks=4 bytes_per_channel=2147483648|FAIL)\r?\n} $transcript] ||
            [string first "CPU BRAM FAIL" $transcript] >= 0 ||
            [string first "GPIO INIT FAIL" $transcript] >= 0} {
            set done 1
        }
        if {$application == "systest"} {
            if {[llength $sent_commands] == 7 && [lindex $sent_commands end] == "t"} {
                append peripheral_response $chunk
                if {[regexp {Temperature: [0-9]+\.[0-9]+C\r?\n} $peripheral_response]} {
                    set peripheral_complete 1
                    set done 1
                }
            }
            if {[string first "Temperature Sensor Error" $transcript] >= 0 ||
                [string first "Gpio Initialization Failed" $transcript] >= 0} {
                set done 1
            }
        }
    }
    if {[eof $uart]} {set done 1}
}
fileevent $uart readable receive_uart
set timer [after $timeout {set done 1}]
con
vwait done
after cancel $timer
foreach pending $command_timers {after cancel $pending}
fileevent $uart readable {}
close $uart
close $output
jtagterminal -ctx $uart_ctx -stop
catch {stop}
disconnect
if {$application == "ddr_diag" && ![regexp {DDR RESULT (PASS|FAIL)} $transcript]} {
    error "CPU/DDR diagnostic did not finish; inspect the saved UART log"
}
if {$application == "ddr_full" && ![regexp {DDR FULL RESULT (PASS|FAIL)} $transcript]} {
    error "Full-capacity CPU/DDR diagnostic did not finish; inspect the saved UART log"
}
if {$application == "systest" && !$peripheral_complete} {
    error "Original peripheral application did not finish; inspect the saved UART log"
}
# The Python runner checks every result and the final marker, including failures.
exit
