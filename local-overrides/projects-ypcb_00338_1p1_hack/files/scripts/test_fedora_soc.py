"""Host acceptance checks: incomplete/failing output must never prove hardware success."""
import unittest
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from fedora_soc import validate_uart, validate_peripheral_uart, validate_full_ddr_uart


def completed_transcript():
    return ("YPCB CPU READY diag=1 addr_bits=36\r\nCPU BRAM PASS bytes=4096\r\n"
            "READY FOR DDR send=m\r\nDDR BEGIN bytes_per_channel=4096\r\n"
            + "".join(f"DDR CH{ch} {width}-bit PASS\r\n"
                      for ch in (0, 1) for width in (32, 16, 8))
            + "DDR RESULT PASS checks=6\r\n")


def peripheral_transcript(value="25.7"):
    return ("Press 'r','g','y' to toggle LEDs. Press 'm' to run memory test. "
            "'t' to get temperature.\n\r"
            f"Temperature: {value}C\r\n")


def full_ddr_transcript():
    return ("YPCB CPU READY diag=2 addr_bits=36\r\nCPU BRAM PASS bytes=4096\r\n"
            "READY FOR FULL DDR send=f\r\n"
            "DDR FULL BEGIN bytes_per_channel=2147483648 patterns=2\r\n"
            + "".join(f"DDR FULL PASS ch={ch} pattern={pattern} bytes=2147483648\r\n"
                      for pattern in (0, 1) for ch in (0, 1))
            + "DDR FULL RESULT PASS checks=4 bytes_per_channel=2147483648\r\n")


class FullDdrAcceptance(unittest.TestCase):
    def test_complete(self):
        validate_full_ddr_uart(full_ddr_transcript())

    def test_partial_or_duplicate_results_rejected(self):
        text = full_ddr_transcript()
        for line in text.splitlines(keepends=True):
            for changed in (text.replace(line, ""), text + line):
                with self.subTest(line=line), self.assertRaises(RuntimeError):
                    validate_full_ddr_uart(changed)

    def test_false_final_pass_after_fault_rejected(self):
        with self.assertRaises(RuntimeError):
            validate_full_ddr_uart(full_ddr_transcript() + "DDR FULL FAIL ch=1 pattern=1\r\n")

    def test_small_region_or_wrong_channel_cannot_prove_capacity(self):
        for text in (completed_transcript(), full_ddr_transcript().replace("2147483648", "4096"),
                     full_ddr_transcript().replace("ch=1", "ch=0")):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                validate_full_ddr_uart(text)

    def test_out_of_order_result_rejected(self):
        lines = full_ddr_transcript().splitlines(keepends=True)
        lines[4], lines[6] = lines[6], lines[4]
        with self.assertRaises(RuntimeError):
            validate_full_ddr_uart("".join(lines))

    def test_additional_wrong_scope_test_rejected(self):
        for extra in ("DDR FULL BEGIN bytes_per_channel=4096 patterns=2\r\n",
                      "DDR FULL RESULT PASS checks=1 bytes_per_channel=4096\r\n"):
            with self.subTest(extra=extra), self.assertRaises(RuntimeError):
                validate_full_ddr_uart(full_ddr_transcript() + extra)


class Acceptance(unittest.TestCase):
    def test_complete(self):
        validate_uart(completed_transcript())

    def test_missing_results(self):
        transcript = completed_transcript()
        for line in transcript.splitlines(keepends=True):
            if line.startswith(("DDR CH", "CPU BRAM", "YPCB CPU", "DDR BEGIN", "DDR RESULT")):
                with self.subTest(line=line), self.assertRaises(RuntimeError):
                    validate_uart(transcript.replace(line, ""))

    def test_failure_hidden_by_final_pass(self):
        transcript = completed_transcript()
        for ch in (0, 1):
            for width in (32, 16, 8):
                with self.subTest(ch=ch, width=width), self.assertRaises(RuntimeError):
                    validate_uart(transcript.replace(f"DDR CH{ch} {width}-bit PASS",
                                                      f"DDR CH{ch} {width}-bit FAIL"))

    def test_duplicate_results(self):
        transcript = completed_transcript()
        for ch in (0, 1):
            for width in (32, 16, 8):
                line = f"DDR CH{ch} {width}-bit PASS\r\n"
                with self.subTest(ch=ch, width=width), self.assertRaises(RuntimeError):
                    validate_uart(transcript.replace(line, line * 2))

    def test_generic_upstream_completion_is_insufficient(self):
        with self.assertRaises(RuntimeError):
            validate_uart("Successfully ran Memory Test Application.\r\n")


class PeripheralAcceptance(unittest.TestCase):
    def test_original_unpadded_fraction(self):
        result = validate_peripheral_uart(peripheral_transcript())
        self.assertEqual(result["hundredths_c"], 7)
        self.assertAlmostEqual(result["temperature_c"], 25.07)

    def test_two_digit_fraction(self):
        self.assertAlmostEqual(validate_peripheral_uart(peripheral_transcript("42.75"))
                               ["temperature_c"], 42.75)

    def test_missing_or_duplicate_response(self):
        text = peripheral_transcript()
        for corrupt in (text.split("Temperature:")[0], text + "Temperature: 30.0C\r\n",
                        text.replace("Temperature: 25.7C", "Temperature: 25.7")):
            with self.subTest(text=corrupt), self.assertRaises(RuntimeError):
                validate_peripheral_uart(corrupt)

    def test_missing_or_duplicate_menu(self):
        text = peripheral_transcript()
        menu = text.split("Temperature:")[0]
        for corrupt in (text.replace(menu, ""), menu + text):
            with self.subTest(text=corrupt), self.assertRaises(RuntimeError):
                validate_peripheral_uart(corrupt)

    def test_sensor_or_initialization_failure_rejects_later_response(self):
        for failure in ("Temperature Sensor Error.", "Gpio Initialization Failed", "FAILED!"):
            with self.subTest(failure=failure), self.assertRaises(RuntimeError):
                validate_peripheral_uart(failure + "\r\n" + peripheral_transcript())

    def test_invalid_unsigned_format(self):
        for value in ("512.0", "25.100", "-1.0", "nan", "25.7C\nTemperature: junk"):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                validate_peripheral_uart(peripheral_transcript(value))

    def test_peripheral_output_does_not_prove_ddr(self):
        with self.assertRaises(RuntimeError):
            validate_uart(peripheral_transcript())


@unittest.skipUnless(shutil.which("tclsh"), "Tcl interpreter unavailable")
class TclFlow(unittest.TestCase):
    """Exercise the actual runner with fake XSDB commands and a real local UART socket."""
    def run_flow(self, application, scenario="complete", cpus=1, stopped=False):
        received = []
        finished = threading.Event()
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(0.05)
        port = listener.getsockname()[1]

        def serve():
            while not finished.is_set():
                try:
                    conn, _ = listener.accept()
                    break
                except socket.timeout:
                    continue
                except OSError:
                    return
            else:
                return
            with conn:
                conn.settimeout(0.05)
                menu = peripheral_transcript().split("Temperature:")[0]
                initial = ("YPCB CPU READY diag=1 addr_bits=36\r\nCPU BRAM PASS bytes=4096\r\n"
                           "READY FOR DDR send=m\r\n") if application in ("ddr_diag", "legacy") else menu
                if application == "ddr_full":
                    initial = full_ddr_transcript().split("DDR FULL BEGIN")[0]
                if scenario == "gpio_failure":
                    initial = "Gpio Initialization Failed\r\n"
                if scenario == "early_temperature":
                    initial += "Temperature: 25.7C\r\n"
                try:
                    # The menu/ready marker crosses separate receive callbacks.
                    conn.sendall(initial[:35].encode())
                    time.sleep(0.003)
                    conn.sendall(initial[35:].encode())
                    while not finished.is_set():
                        try:
                            data = conn.recv(64)
                        except socket.timeout:
                            continue
                        if not data:
                            return
                        received.extend(data.decode())
                        if b"m" in data and scenario == "complete":
                            reply = completed_transcript().split("DDR BEGIN", 1)[1]
                            conn.sendall(("DDR BEGIN" + reply).encode())
                        if b"f" in data and scenario == "complete":
                            reply = full_ddr_transcript().split("DDR FULL BEGIN", 1)[1]
                            conn.sendall(("DDR FULL BEGIN" + reply).encode())
                        if b"t" in data:
                            if scenario == "complete":
                                conn.sendall(b"Temperature: 25.")
                                time.sleep(0.003)
                                conn.sendall(b"7C\r\n")
                            elif scenario == "sensor_failure":
                                conn.sendall(b"Temperature Sensor Error.\r\n")
                except OSError:
                    return

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                temp = Path(directory)
                shim = temp / "fake-xsdb.tcl"
                log = temp / "uart.log"
                shim.write_text(r'''
lassign $argv runner port application logfile cpu_count initial_suspended
proc connect {args} {puts "MOCK_CONNECT"}
proc targets {args} {
    global cpu_count initial_suspended
    if {[lindex $args 0] == "-target-properties"} {
        # The physical debugger lists both the MDM and its processor. Honor
        # the name filter so a broad filter reproduces the real ambiguity.
        set entries [list [dict create target_id 1 name {MicroBlaze Debug Module at USER2}]]
        for {set i 0} {$i < $cpu_count} {incr i} {
            lappend entries [dict create target_id [expr {$i + 2}] name "MicroBlaze #$i" parent_ctx mock-MDM suspended $initial_suspended]
        }
        set filter_index [lsearch -exact $args -filter]
        if {$filter_index < 0} {return $entries}
        set filter [lindex $args [expr {$filter_index + 1}]]
        if {![regexp {name =~ "([^"]+)"} $filter -> pattern]} {error "Unsupported mock target filter"}
        set result {}
        foreach target $entries {
            if {[string match $pattern [dict get $target name]]} {lappend result $target}
        }
        return $result
    }
    return "Mock MicroBlaze target"
}
proc stop {} {
    global initial_suspended
    if {$initial_suspended} {error "Already stopped"}
    puts "MOCK_STOP"
}
proc rst {args} {}
proc dow {args} {puts "MOCK_DOWNLOAD [lindex $args 0]"}
proc jtagterminal {args} {
    global port
    set ctx_index [lsearch -exact $args -ctx]
    if {$ctx_index < 0 || [lindex $args [expr {$ctx_index + 1}]] != "mock-MDM"} {
        error "UART must use the selected processor's MDM parent"
    }
    if {[lsearch -exact $args -socket] >= 0} {return $port}
    puts "MOCK_JTAG_STOP"
}
proc con {} {}
proc disconnect {} {puts "MOCK_DISCONNECT"}
rename after original_after
proc after {args} {
    if {[llength $args] == 1 && [lindex $args 0] == 1500} {return}
    if {[llength $args] == 2 && [lindex [lindex $args 1] 0] == "send_uart_command"} {
        lset args 0 [expr {[lindex $args 0] / 100}]
    }
    return [original_after {*}$args]
}
set argv [list fake.elf tcp:127.0.0.1:1 $logfile 400]
if {$application != "legacy"} {lappend argv $application}
source $runner
''')
                process = subprocess.run([shutil.which("tclsh"), str(shim),
                                          str(Path(__file__).with_name("fedora_cpu_run.tcl")),
                                          str(port), application, str(log), str(cpus), str(int(stopped))],
                                         capture_output=True, text=True, timeout=8)
                transcript = log.read_text() if log.exists() else ""
                return process, received.copy(), transcript
        finally:
            finished.set()
            listener.close()
            worker.join(timeout=1)

    def test_default_four_argument_diagnostic(self):
        process, commands, transcript = self.run_flow("legacy")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(commands, ["m"])
        validate_uart(transcript)
        self.assertIn("MOCK_JTAG_STOP", process.stdout)
        self.assertIn("MOCK_DISCONNECT", process.stdout)

    def test_explicit_diagnostic(self):
        process, commands, transcript = self.run_flow("ddr_diag")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(commands, ["m"])
        validate_uart(transcript)

    def test_already_stopped_processor(self):
        process, commands, transcript = self.run_flow("ddr_diag", stopped=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(commands, ["m"])
        validate_uart(transcript)

    def test_full_capacity_command_and_uart(self):
        process, commands, transcript = self.run_flow("ddr_full")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(commands, ["f"])
        validate_full_ddr_uart(transcript)
        self.assertIn("MOCK_JTAG_STOP", process.stdout)
        self.assertIn("MOCK_DISCONNECT", process.stdout)

    def test_full_capacity_timeout_cleanup(self):
        process, commands, _ = self.run_flow("ddr_full", "no_response")
        self.assertEqual(commands, ["f"])
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("did not finish", process.stderr)
        self.assertIn("MOCK_JTAG_STOP", process.stdout)
        self.assertIn("MOCK_DISCONNECT", process.stdout)

    def test_peripheral_commands_and_fragmented_response(self):
        process, commands, transcript = self.run_flow("systest")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(commands, list("rrgg yyt".replace(" ", "")))
        self.assertAlmostEqual(validate_peripheral_uart(transcript)["temperature_c"], 25.07)
        self.assertEqual(process.stdout.count("HOST_SENT"), 7)
        self.assertIn("MOCK_JTAG_STOP", process.stdout)
        self.assertIn("MOCK_DISCONNECT", process.stdout)

    def test_missing_response_times_out_and_cleans_up(self):
        for app in ("ddr_diag", "systest"):
            with self.subTest(app=app):
                process, _, _ = self.run_flow(app, "no_response")
                self.assertNotEqual(process.returncode, 0)
                self.assertIn("did not finish", process.stderr)
                self.assertIn("MOCK_JTAG_STOP", process.stdout)
                self.assertIn("MOCK_DISCONNECT", process.stdout)

    def test_early_unsolicited_temperature_does_not_complete_run(self):
        process, commands, _ = self.run_flow("systest", "early_temperature")
        self.assertEqual(commands, ["r", "r", "g", "g", "y", "y", "t"])
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("did not finish", process.stderr)

    def test_sensor_and_gpio_errors_fail(self):
        for scenario in ("sensor_failure", "gpio_failure"):
            with self.subTest(scenario=scenario):
                process, _, _ = self.run_flow("systest", scenario)
                self.assertNotEqual(process.returncode, 0)
                self.assertIn("MOCK_JTAG_STOP", process.stdout)
                self.assertIn("MOCK_DISCONNECT", process.stdout)

    def test_target_count_rejected_before_download(self):
        for cpus in (0, 2):
            with self.subTest(cpus=cpus):
                process, commands, _ = self.run_flow("systest", cpus=cpus)
                self.assertNotEqual(process.returncode, 0)
                self.assertEqual(commands, [])
                self.assertNotIn("MOCK_DOWNLOAD", process.stdout)
                self.assertIn("Expected exactly one MicroBlaze", process.stderr)

    def test_unknown_application_rejected_before_connection(self):
        process, commands, _ = self.run_flow("unknown")
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(commands, [])
        self.assertNotIn("MOCK_CONNECT", process.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
