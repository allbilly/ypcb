#!/usr/bin/env python3
"""Check host readiness or run the supplied SoC + diagnostic through JTAG, SRAM only."""

try:
    from .workspace_paths import expand_paths
except ImportError:
    from workspace_paths import expand_paths
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/fedora-microblaze"
BIT = ROOT / "build/fedora-baseline/hardware/top_wrapper.bit"
ELF = OUT / "ddr_diag.elf"
FULL_DDR_OUT = ROOT / "build/fedora-microblaze-full-ddr"
LAB = Path(os.environ.get("VIVADO_LAB_ROOT", expand_paths('@VIVADO_LAB_ROOT@')))
LOADER = Path(os.environ.get("YPCB_LOADER", expand_paths('@YPCB@/openFPGALoader/build-xpcu-debug/openFPGALoader')))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_artifacts(elf=ELF):
    manifest = json.loads((OUT / "manifest.json").read_text())
    if manifest.get("status") != "CPU_SOFTWARE_BUILT_HARDWARE_NOT_RUN":
        raise RuntimeError("CPU software build has not completed")
    if sha(ROOT / "scripts/fedora_ddr_diag.c") != manifest["diagnostic_source_sha256"]:
        raise RuntimeError("Diagnostic source changed; rebuild its ELF first")
    if sha(ROOT / "examples/YPCB_00338_1P1_software.zip") != manifest["software_archive_sha256"]:
        raise RuntimeError("Supplied software archive changed")
    if sha(BIT) != manifest["bitstream_sha256"]:
        raise RuntimeError("Supplied SoC bitstream hash mismatch")
    if elf.name == "ddr_full.elf":
        full = json.loads((FULL_DDR_OUT / "manifest.json").read_text())
        if (full.get("status") != "FULL_CAPACITY_CPU_SOFTWARE_BUILT_HARDWARE_NOT_RUN"
                or full.get("bytes_tested_per_channel") != 2147483648
                or full.get("patterns") != 2
                or full.get("ddr_bases") != ["0x100000000", "0x180000000"]
                or full.get("flags") != manifest["flags"]
                or full.get("bitstream_sha256") != manifest["bitstream_sha256"]):
            raise RuntimeError("Full-capacity CPU software build/profile differs")
        for path, expected_sha in full["source"].items():
            if sha(Path(path)) != expected_sha:
                raise RuntimeError("Full diagnostic input changed; rebuild its ELF first: " + path)
        if Path(full["application"]["path"]).resolve() != elf.resolve() or sha(elf) != full["application"]["sha256"]:
            raise RuntimeError("Full diagnostic ELF differs from the verified build")
        return full
    expected = next(a["sha256"] for a in manifest["applications"] if Path(a["path"]).name == elf.name)
    if sha(elf) != expected:
        raise RuntimeError(f"{elf.name} ELF hash mismatch")
    return manifest


def validate_uart(transcript):
    text = transcript.replace("\r", "")
    if "YPCB CPU READY diag=1 addr_bits=36\n" not in text or "CPU BRAM PASS bytes=4096\n" not in text:
        raise RuntimeError("CPU/BRAM ready markers missing")
    if re.search(r"\bFAIL(?:ED)?\b", text):
        raise RuntimeError("CPU/DDR transcript reports a failure")
    if text.count("DDR BEGIN bytes_per_channel=4096\n") != 1:
        raise RuntimeError("Expected exactly one DDR test")
    for ch in (0, 1):
        for width in (32, 16, 8):
            if text.count(f"DDR CH{ch} {width}-bit PASS\n") != 1:
                raise RuntimeError(f"DDR CH{ch} {width}-bit result missing or duplicated")
    if text.count("DDR RESULT PASS checks=6\n") != 1:
        raise RuntimeError("DDR final result missing or duplicated")


def validate_peripheral_uart(transcript):
    text = transcript.replace("\r", "")
    menu = "Press 'r','g','y' to toggle LEDs. Press 'm' to run memory test. 't' to get temperature.\n"
    if text.count(menu) != 1:
        raise RuntimeError("Original application's UART menu missing or duplicated")
    if re.search(r"\bFAIL(?:ED)?\b|Temperature Sensor Error", text, re.IGNORECASE):
        raise RuntimeError("Peripheral transcript reports an initialization or sensor failure")
    values = re.findall(r"^Temperature: (\d+)\.(\d{1,2})C$", text, re.MULTILINE)
    if len(values) != 1 or text.count("Temperature:") != 1:
        raise RuntimeError("Expected exactly one complete LM73 temperature response")
    # memorytest.c prints an unpadded integer number of hundredths after '.'.
    whole, hundredths = map(int, values[0])
    if whole > 511 or hundredths > 99:
        raise RuntimeError("Temperature response exceeds the original unsigned sample format")
    return {"whole_c": whole, "hundredths_c": hundredths,
            "temperature_c": whole + hundredths / 100,
            "sensor_sample_interpretation": "Original unsigned application; signed range not verified"}


def validate_full_ddr_uart(transcript):
    text = transcript.replace("\r", "")
    if re.search(r"\bFAIL(?:ED)?\b", text):
        raise RuntimeError("Full-capacity DDR transcript reports a failure")
    if text.count("DDR FULL BEGIN ") != 1 or text.count("DDR FULL RESULT ") != 1:
        raise RuntimeError("Expected exactly one complete full-capacity DDR test")
    markers = ["YPCB CPU READY diag=2 addr_bits=36\n", "CPU BRAM PASS bytes=4096\n",
               "READY FOR FULL DDR send=f\n",
               "DDR FULL BEGIN bytes_per_channel=2147483648 patterns=2\n"]
    markers.extend(f"DDR FULL PASS ch={channel} pattern={pattern} bytes=2147483648\n"
                   for pattern in (0, 1) for channel in (0, 1))
    markers.append("DDR FULL RESULT PASS checks=4 bytes_per_channel=2147483648\n")
    previous = -1
    for marker in markers:
        if text.count(marker) != 1 or text.find(marker) <= previous:
            raise RuntimeError("Full-capacity DDR result missing, duplicated or out of order: " + marker.strip())
        previous = text.find(marker)
    if len(re.findall(r"^DDR FULL PASS ", text, re.MULTILINE)) != 4:
        raise RuntimeError("Unexpected full-capacity DDR result count")


def cable_present():
    listing = subprocess.check_output(["lsusb"], text=True).lower()
    return "03fd:0013" in listing or "03fd:0008" in listing


def xsdb_probe():
    code = "puts XSDB_READY; puts [version]; puts [help jtagterminal]; exit"
    p = subprocess.run(["bash", str(ROOT / "scripts/fedora-xsdb.sh"), "-eval", code],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
    (OUT / "xsdb-check.log").write_text(p.stdout)
    if p.returncode or "XSDB_READY" not in p.stdout or "MDM UART" not in p.stdout:
        raise RuntimeError("XSDB startup/JTAG UART check failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run", "validate"))
    parser.add_argument("--application", choices=("ddr_diag", "systest", "ddr_full"), default="ddr_diag",
                        help="first 4 KiB DDR test, original GPIO/LM73 application, or full 4 GiB DDR test")
    parser.add_argument("--uart", type=Path, help="saved UART transcript for validate")
    parser.add_argument("--timeout", type=int, help="timeout in seconds; default 120, or 3600 for ddr_full")
    args = parser.parse_args()
    if args.timeout is None:
        args.timeout = 3600 if args.application == "ddr_full" else 120
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.action == "validate":
        if not args.uart:
            parser.error("validate requires --uart")
        if args.application == "systest":
            temperature = validate_peripheral_uart(args.uart.read_text())
            print(f"PASS: original UART menu + LM73 response, {temperature['temperature_c']:.2f} C; "
                  "physical GPIO outputs unverified")
        elif args.application == "ddr_full":
            validate_full_ddr_uart(args.uart.read_text())
            print("PASS: CPU BRAM + both full 2 GiB DDR channels, two address-tagged patterns")
        else:
            validate_uart(args.uart.read_text())
            print("PASS: CPU BRAM + all six DDR checks, 4096 bytes per channel")
        return
    elf = (FULL_DDR_OUT if args.application == "ddr_full" else OUT) / (args.application + ".elf")
    verify_artifacts(elf)
    for path in (LAB / "bin/hw_server", LOADER, Path(expand_paths('@YPCB@/dlc10-init.sh'))):
        if not path.is_file():
            raise RuntimeError(f"Required JTAG tool missing: {path}")
    xsdb_probe()
    connected = cable_present()
    if args.action == "check":
        state = {"status": "HOST_READY", "physical_test": "NOT_RUN", "cable_present": connected,
                 "bitstream": str(BIT), "elf": str(elf), "application": args.application,
                 "xsdb": "STARTUP_AND_MDM_UART_HELP_PASS"}
        readiness = "readiness.json" if args.application == "ddr_diag" else "readiness-" + args.application + ".json"
        (OUT / readiness).write_text(json.dumps(state, indent=2) + "\n")
        print(json.dumps(state, indent=2))
        return
    if not connected:
        raise RuntimeError("No DLC10 cable detected; connect the powered board and JTAG cable")
    run = OUT / ("hardware-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run.mkdir()
    result = {"status": "RUNNING", "bitstream_sha256": sha(BIT), "elf_sha256": sha(elf),
              "application": args.application, "uart": str(run / "uart.log"), "flash_written": False}
    if args.application == "ddr_diag":
        result["bytes_tested_per_channel"] = 4096
    elif args.application == "ddr_full":
        result.update(bytes_tested_per_channel=2147483648, patterns=2,
                      scope="All 32-bit words of both 2 GiB DDR regions; global address-tagged and complementary patterns",
                      all_ddr_contents_overwritten=True)
    else:
        result.update(scope="Original UART menu and LM73 I2C response; GPIO commands submitted only",
                      gpio_commands_planned=["r", "r", "g", "g", "y", "y"],
                      physical_gpio_outputs="NOT_VERIFIED", ddr_test="NOT_RUN")
    report = run / "result.json"
    report.write_text(json.dumps(result, indent=2) + "\n")
    server = None
    try:
        # The existing initializer verifies the firmware/cable and FPGA IDCODE.
        with (run / "program.log").open("w") as log:
            subprocess.run(["bash", expand_paths('@YPCB@/dlc10-init.sh')], stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=60)
            subprocess.run([str(LOADER), "--cable", "xilinxPlatformCableUsb", "--freq", "6000000",
                            "--index-chain", "0", str(BIT)], stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=120)
        # Use an owned server; stop it even when programming/loading/testing fails.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"tcp:127.0.0.1:{port}"
        with (run / "hw-server.log").open("w") as log:
            server = subprocess.Popen([str(LAB / "bin/hw_server"), "-s", url], stdout=log,
                                      stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 20
            while True:
                if server.poll() is not None:
                    raise RuntimeError("hw_server exited before accepting connections")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("hw_server did not start")
                    time.sleep(0.2)
            with (run / "xsdb.log").open("w") as debug:
                subprocess.run(["bash", str(ROOT / "scripts/fedora-xsdb.sh"),
                                str(ROOT / "scripts/fedora_cpu_run.tcl"), str(elf), url,
                                str(run / "uart.log"), str(args.timeout * 1000), args.application],
                               stdout=debug, stderr=subprocess.STDOUT, check=True,
                               timeout=args.timeout + 60)
        transcript = (run / "uart.log").read_text()
        if args.application == "systest":
            commands = re.findall(r"^HOST_SENT ([rgyt])$", (run / "xsdb.log").read_text(), re.MULTILINE)
            if commands != ["r", "r", "g", "g", "y", "y", "t"]:
                raise RuntimeError("Original application's command submission did not complete")
            result["gpio_commands_submitted"] = commands[:-1]
            result["temperature"] = validate_peripheral_uart(transcript)
        elif args.application == "ddr_full":
            validate_full_ddr_uart(transcript)
        else:
            validate_uart(transcript)
        result["status"] = "PASS"
    except Exception as error:
        result.update(status="FAIL", error=str(error))
        raise
    finally:
        if server and server.poll() is None:
            os.killpg(server.pid, signal.SIGTERM)
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait()
        report.write_text(json.dumps(result, indent=2) + "\n")
        print(f"{result['status']}: {report}")


if __name__ == "__main__":
    main()
