# Fedora first-run baseline

After Bonetto's BRAM test, use the supplied TiferKing system as the first CPU
and DDR3 board baseline. The upstream example contains
MicroBlaze, AXI, local BRAM, dual-channel MIG, MDM JTAG UART, GPIO, I²C and XDMA.
The author describes the example and tool imports in the
[board article](https://www.tiferking.cn/index.php/2024/12/19/650/).

## Verified supplied artifacts

The local source revision is `8b13ecf71b7061dd43a2b1580f0caa469f64303f`.
The XPR and XSA select `xc7k480tffg1156-2`; they were generated with Vivado 2022.2.
The XSA and three copies inside `examples/YPCB_00338_1P1_software.zip` contain
the same 18,735,113-byte `top_wrapper.bit`, SHA256
`22e7281f7574d4e56153ce7345d9e0fb0044c80d56075e45724adcb496337931`.
Its header records 2024/12/31 19:29:46 and the `7k480tffg1156` part.
An offline structural check also passed against this exact SHA256; the saved
report is `build/fedora-baseline/vivado-bitstream-structural-check.json`. It
checks the YPCB package/device header, configuration IDCODE, packet bounds,
frame-data presence and START/DESYNC markers. The `.bit` header omits speed
grade, so the XSA remains the source for the `-2` target. This check does not
verify CRC, Vivado DRC or timing, or physical board behavior.
The checker was rerun on 2026-10-10 at 10:17 HKT with the expected SHA256; the
fresh PASS report is `build/fedora-baseline/vivado-bitstream-check-live-20261010T1017HKT.json`.
Re-run it with a fresh report path:

```sh
python3 ${YPCB_ROOT}/projects/bonetto-soc/scripts/fedora-check-vivado-bitstream.py \
  --bit build/fedora-baseline/hardware/top_wrapper.bit \
  --expected-sha256 22e7281f7574d4e56153ce7345d9e0fb0044c80d56075e45724adcb496337931 \
  --out "build/fedora-baseline/vivado-bitstream-check-$(date -u +%Y%m%dT%H%M%SZ).json"
```

Stage and hash-check the archives without changing their contents:

```sh
cd ${YPCB_ROOT}/projects/ypcb_00338_1p1_hack
python3 scripts/prepare_fedora_baseline.py
```

Outputs are under `build/fedora-baseline/hardware/` and
`build/fedora-baseline/software/`; `manifest.json` records provenance and
explicitly states that hardware has not been run. Repeating the command
verifies existing staged files and rejects modified files.

**There is no application ELF in the supplied archives.** The software ZIP
includes application source, BSP source/headers and runtime libraries, but
does not contain `libxil.a` or a compiled application. Loading the supplied
bitstream does not by itself establish that the interactive test is running.
Its source BRAM configuration specifies no loaded COE initialization file;
execution still needs a built ELF loaded through the MicroBlaze debug path.

## Current host status (2026-10-10)

At 13:31 HKT, a recheck found the saved artifact-integrity receipt still
reports PASS. The
`ddr_diag`, `systest` and `ddr_full` readiness receipts report `HOST_READY`,
with each physical test marked `NOT_RUN`. USB enumeration during this pass found
no recognized Digilent, FTDI or Xilinx JTAG adapter, so no MicroBlaze bitstream
or software could be loaded onto the board.

The cable was connected later on 2026-10-10. Real SRAM programming succeeded
with INIT/DONE set and no BPI flash write. Physical debugger discovery exposed
both an MDM and a processor; the runner now selects `MicroBlaze #*` explicitly,
opens the UART through the MDM parent context, and handles an already stopped
processor. All 29 host-flow regression checks pass. These fix debugger startup,
not the FPGA design or application.

The recovered `ddr_diag` run downloaded the ELF and opened the MDM UART, but
received no text before its 120-second timeout. A stopped-CPU snapshot found
PC `0xb8` in runtime startup and BRAM vectors matching the ELF. No physical
DDR test result was obtained. Evidence is in
`build/fedora-microblaze/hardware-20261010T135515978852Z/`; a separate run/step
startup probe is in `build/fedora-microblaze/cpu-startup-probe-20261010T1433Z/`.
The static clock connections do not by themselves explain this startup failure.

## Exact supplied memory-test scope

`YPCB_00338_1P1_App/src/memory_config_g.c` defines two 2 GiB regions:

| Channel | MicroBlaze byte base | Mapped size | Test span |
|---|---|---|---|
| CH0 | `0x100000000` | 2 GiB | first 4 KiB |
| CH1 | `0x180000000` | 2 GiB | first 4 KiB |

`memorytest.c` performs 1,024 32-bit, 2,048 16-bit and 4,096 8-bit tests
at each base. These passes overlap the same 4 KiB. It prints each result,
then prints a successful completion message even if individual tests failed.
Acceptance must require all six individual results to say `PASSED!`.
This does not prove full capacity, absence of address aliasing, bandwidth,
long-term stability or agreement across different cards.

The processor runs at 100 MHz, uses 36-bit data addressing and little-endian
code. Keep extended addressing enabled when building the supplied application:
truncating the DDR bases to 32 bits accesses the wrong region. stdin/stdout
are `mdm_1`, with the UART register aperture at `0x41400000`. The application
accepts `r`, `g`, `y` for LEDs, `m` for the memory test and `t` for temperature.

## Build the CPU software

Checked on 2026-10-06: both CPU applications compile with a local standalone
MicroBlaze GCC 10.2.0 toolchain, the supplied BSP, and the exact BSP CPU flags.
The build script downloads hash-pinned Debian packages from the
[toolchain maintainer](https://github.com/mdednev/mb-gcc/releases/tag/2021-0623%2B2)
and extracts them under `build/fedora-toolchain/`; it does not install system
packages. Its GCC wrapper supplies the relocated newlib headers and multilibs.

```sh
cd ${YPCB_ROOT}/projects/ypcb_00338_1p1_hack
python3 scripts/build_fedora_microblaze.py
python3 scripts/fedora_soc.py check
```

The resulting `build/fedora-microblaze/` contains:

| Artifact | Purpose |
|---|---|
| `systest.elf` | Original interactive application, LEDs, DDR and temperature |
| `ddr_diag.elf` | First-run diagnostic: CPU marker, 4 KiB local BRAM check, then DDR on `m` |
| `bsp/microblaze_0/lib/libxil.a` | Compiled supplied standalone BSP |
| `manifest.json` | Package hashes, commands, ELF hashes and BRAM load segments |
| `*.map`, `*.disassembly`, `*-build.log` | Link and compilation evidence |
| `readiness.json`, `readiness-systest.json`, `xsdb-check.log` | Host readiness for the selected application; physical tests pending |

Both executables are ELF32 little-endian MicroBlaze images with entry at the
reset vector and every load segment inside the hardware's 512 KiB local BRAM.
The build checks that their disassemblies contain all six extended-address
load/store opcodes used by the memory tests. No special compiler flag makes C
pointers 36-bit: the supplied BSP's split high/low addresses and `*ea`
instructions preserve the DDR addresses. This follows AMD's
[extended-address programming interface](https://docs.amd.com/r/2024.1-English/ug984-vivado-microblaze-ref/Data-and-Instruction-Address-Extension).

The first-run diagnostic explicitly disables D-cache, does not initialize I²C,
and reports each DDR result and a final result based on all six checks. It uses
the same vendor memory-test routines and 4 KiB/channel scope as the original.
The original application is retained as a separate ELF for subsequent LED and
temperature checks. Compiler warnings in the original application's unused
callback parameters are recorded in `app-build.log`.

## Optional full-capacity DDR diagnostic

After the first CPU/BRAM and 4 KiB DDR baseline passes, a separate diagnostic
can test every 32-bit word in both complete 2 GiB regions. Build it using the
already verified BSP and compiler:

```sh
python3 scripts/build_fedora_ddr_full.py
```

This produces `build/fedora-microblaze-full-ddr/ddr_full.elf`, its manifest,
link map, disassembly and compiler log. Every ELF load segment fits local BRAM.
The disassembly contains the real `lwea`, `swea` and `mbar 1` instructions;
36-bit effective addresses preserve the DDR bases and both last-word addresses.
The build leaves the original `systest.elf` and `ddr_diag.elf` available.

The test disables D-cache and interrupts, checks local BRAM, and waits for `f`
on the MDM UART. It writes a distinct address-tagged value to every word of both
channels before reading either channel. A complementary second pass exercises
both values of every data bit. Filling both channels first allows a channel
alias to be detected. The data barrier follows
[AMD's documented `mbar 1` behavior](https://docs.amd.com/r/2024.1-English/ug984-vivado-microblaze-ref/mbar).
Progress appears every 64 MiB. A mismatch reports its full split address,
expected value and observed value, and prevents the final PASS marker.

This command overwrites all 4 GiB of card DDR and reloads the supplied SRAM image:

```sh
python3 scripts/fedora_soc.py run --application ddr_full --timeout 3600
```

The full diagnostic defaults to a 3,600-second host timeout. Acceptance requires
all four full-region verification markers in order and the exact final result;
a small-region result, duplicate/missing result or failure followed by a PASS
is rejected. A saved transcript can be checked with:

```sh
python3 scripts/fedora_soc.py validate --application ddr_full --uart PATH_TO_UART_LOG
```

The software build and host tests passed; the physical full-capacity test has
not run. Native algorithm tests cover address/channel aliasing, corruption of
the final model word and all 64 stuck-at-zero/one data-bit faults. Host UART/XSDB
tests use a local socket and substituted debug commands. These tests establish
software behavior, not DDR capacity, physical signal integrity or sustained
board stability.

## Run through JTAG

Vivado Lab 2026.1.1 is installed under
`${VIVADO_LAB_ROOT}`. Its standard XSDB launcher hangs when
loading the optional HSI design package on this host. `scripts/fedora-xsdb.sh`
exposes only AMD's existing XSDB and TCF Tcl packages through an isolated SDK
directory. HSI is absent and its optional import fails normally; the installed
tools are unchanged. Real XSDB version/help and a real connection to an owned
`hw_server` passed. HSI/BSP generation is not provided by this launcher.

No DLC10 cable was present during preparation. No physical CPU/DDR run has
been performed. The intended first connection is a separately powered board
with JTAG only.
The 12:45 HKT USB recheck showed no Digilent/Xilinx/FTDI adapter; no DLC10/JTAG
adapter was enumerated.

The host preflight was rerun on 2026-10-10 at 12:44 HKT for `ddr_diag`,
`systest` and `ddr_full`. All three reported `HOST_READY` and
`STARTUP_AND_MDM_UART_HELP_PASS`; all reported `cable_present: false` and
`physical_test: NOT_RUN`. The saved readiness receipts are
`build/fedora-microblaze/readiness.json` (SHA256
`ad9f70c3fa1bfc8170075c165a286847f328619feaa4a63ad118f743cb55315f`),
`build/fedora-microblaze/readiness-systest.json` (SHA256
`9a3be49b9a47d8456f6243efe7c9af7bc644e068c9b0a9863628ef1aa3845253`) and
`build/fedora-microblaze/readiness-ddr_full.json` (SHA256
`7153c8cd0c7f4f65d5f4219c8530aef511e81acdf1802cf98e43da2b58451a19`).
These are host checks only.

After the 2026-10-10 reboot, the host-only preflight was rerun at 16:54 HKT
for all three applications. `ddr_diag`, `systest` and `ddr_full` again reported
`HOST_READY` with `STARTUP_AND_MDM_UART_HELP_PASS`; `cable_present` was false
and `physical_test` was `NOT_RUN` for each. Fresh JSON receipts and individual
XSDB startup logs are saved under
`build/fedora-microblaze/host-refresh-20261010T165424HKT/`. This check does not
program the FPGA or establish that the CPU, PCIe clocking or DDR work on the
card.

At 13:43 HKT, `python3 scripts/test_fedora_soc.py` passed all 28 host-flow
tests. Coverage includes strict DDR/peripheral UART acceptance, command order,
single-target rejection, timeout cleanup and disconnect handling through local
sockets and substituted debug commands. The saved output is
`build/fedora-microblaze/host-flow-20261010T134349HKT/unittest.log` (SHA256
`493aab7cf6bb306796fa2d40e653aebb8204e446992857d8261d8ab8b1db6cf1`). This
does not access JTAG or prove DDR/FPGA hardware behavior.

At 13:44 HKT, `scripts/test_fedora_ddr_full_core.c` compiled with
`-std=c11 -Wall -Wextra -Werror -O2` and passed its algorithm checks for DDR
address endpoints, range guards, address/channel aliasing, final-word
corruption and all 64 stuck-at-zero/one data-bit faults. It uses a 128-word
per-channel memory model; it does not exercise physical DDR or the full 4 GiB.
The saved output is
`build/fedora-microblaze/ddr-full-core-host-20261010T134451HKT/test.log`
(SHA256 `0380147ec8032be22ada66c0a7f8d4d0c5db7384ac46931f8c7084bf51e1265a`).

A separate read-only artifact audit at 10:34 HKT reran the build-manifest and
source/ELF hash checks for all three applications, then confirmed the supplied
bitstream hash matches both its build manifest and the 10:17 structural-check
report. The receipt is
`build/fedora-microblaze/artifact-integrity-live-20261010T1034HKT.json`.
It did not connect to JTAG; physical testing remains `NOT_RUN`.

The hardware description connects the CPU and MDM UART to the board's 50 MHz
SYS_CLK through a 100 MHz clock generator. The shared AXI SmartConnect also has
an XDMA clock input. Its CPU input `S00_AXI` uses the board-derived clock,
the DDR outputs `M00_AXI`/`M01_AXI` use their respective MIG clocks, and
the XDMA input `S01_AXI` uses the PCIe clock. The global SmartConnect reset
comes from the board clock/reset domain. These supplied connections are
recorded, with the HWH source hash, in `build/fedora-microblaze/clock-review.json`.
The powered-board run still needs to establish startup with the PCIe clock
absent and actual CPU/UART/DDR operation. Repeat the static review with
`python3 scripts/review_fedora_clocks.py`.

After the physical Bonetto BRAM test passes:

```sh
cd ${YPCB_ROOT}/projects/ypcb_00338_1p1_hack
python3 scripts/fedora_soc.py run
```

This initializes the DLC10, verifies its target through the existing initializer,
loads the supplied FPGA image into SRAM, starts an owned hardware server, selects
the single real MicroBlaze target, resets it, downloads `ddr_diag.elf` to BRAM,
attaches the MDM UART, resumes the CPU and sends `m` after the ready marker.
It stops its hardware server on success or failure. Do not run another loader,
Bonetto XVC server or hardware server that owns this cable at the same time.

Each run creates a fresh `build/fedora-microblaze/hardware-*/` directory with
programming, server, XSDB and UART logs plus a `result.json` which moves from
`RUNNING` to `PASS` or `FAIL`. PASS requires the CPU and local BRAM markers,
exactly one result for every channel/width combination, no failure marker and
the final six-check PASS marker. Missing or incomplete output fails. The UART
validator was checked with synthetic valid and deliberately corrupt transcripts;
that check is host-only evidence, not a hardware result.

Rerun the host acceptance tests with `python3 scripts/test_fedora_soc.py`.
The latest run, at 10:54 HKT on 2026-10-10, passed all 28 checks; its output is
saved as `build/fedora-microblaze/test-fedora-soc-live-20261010T1054HKT.log`,
SHA256 `650944a28dd31b98ba836b0b1e30c415f86f5ec65c67045e54616bd3faf76a1f`.
The suite covers strict diagnostic and full-capacity DDR transcript acceptance,
peripheral UART parsing, and the Tcl runner with fake XSDB commands and a local
UART socket, including fragmented replies and timeout cleanup. It does not
establish a physical CPU, DDR, I²C or LED result.

Recheck a saved diagnostic transcript with:

```sh
python3 scripts/fedora_soc.py validate --uart build/fedora-microblaze/hardware-YYYYMMDDTHHMMSSffffffZ/uart.log
```

After the diagnostic passes, run the original LED/temperature application
through the same owned-server workflow:

```sh
python3 scripts/fedora_soc.py check --application systest
python3 scripts/fedora_soc.py run --application systest
```

This reuses the original, hash-verified `systest.elf` and reloads the supplied
FPGA image into SRAM. After its menu arrives, the runner sends paired `r`,
`g` and `y` toggles, 500 ms apart, then `t`. Observe the red, green and yellow
LEDs during these toggles. The UART session and host command submissions are
saved alongside the result. PASS requires one complete LM73 I²C response and
no failure marker. GPIO commands are recorded as submitted; physical LED
outputs remain `NOT_VERIFIED`. This result does not establish BRAM or DDR
operation. The default `run` command still selects the separate DDR diagnostic.

The original application prints the fractional temperature as an unpadded
integer number of hundredths: `25.7C` means 25.07 C in its format. The runner
records that interpretation. Its unsigned sample handling is retained; this
workflow does not establish signed-temperature support.

Recheck a saved peripheral transcript with:

```sh
python3 scripts/fedora_soc.py validate --application systest --uart build/fedora-microblaze/hardware-YYYYMMDDTHHMMSSffffffZ/uart.log
```

For an interactive session, keep the same SoC image loaded. In one terminal,
start a hardware server and leave it running:

```sh
${VIVADO_LAB_ROOT}/bin/hw_server -s tcp:127.0.0.1:3122
```

In a second terminal, run `bash scripts/fedora-xsdb.sh`. At its prompt:

```tcl
connect -url tcp:127.0.0.1:3122
targets
# Select the MicroBlaze target ID shown by targets (replace TARGET_ID).
targets TARGET_ID
stop
rst -processor
dow ${YPCB_ROOT}/projects/ypcb_00338_1p1_hack/build/fedora-microblaze/systest.elf
puts [jtagterminal -socket]
```

In a third terminal, run `nc 127.0.0.1 PORT`, replacing PORT with the returned
UART socket port. Then enter `con` at the XSDB prompt. In the UART terminal,
enter `r`, `g`, `y`, `m` or `t` followed by Enter. The original `m` result still
needs all six individual tests to pass. These peripheral checks have not been
run on a board here.

When finished, enter `stop`, `jtagterminal -stop`, `disconnect` and `exit` in
XSDB, then stop the foreground hardware server with Ctrl-C.

Full Vivado is needed to rebuild or change this vendor-IP hardware. It is
not needed to load the supplied bitstream or build these CPU applications.
The local toolchain uses standalone newlib, not a Linux BSP. Do not remap
the 36-bit memory addresses.

With a powered board and DLC10 attached, the existing verified Fedora cable
initializer performs volatile firmware initialization and checks the FPGA:

```sh
bash ${YPCB_ROOT}/dlc10-init.sh
```

Then the intended **SRAM-only** programming command is:

```sh
${YPCB_ROOT}/openFPGALoader/build-xpcu-debug/openFPGALoader \
  --cable xilinxPlatformCableUsb --freq 6000000 --index-chain 0 \
  ${YPCB_ROOT}/projects/ypcb_00338_1p1_hack/build/fedora-baseline/hardware/top_wrapper.bit
```

The `run` command performs these steps and then the CPU diagnostic. No flash
programming is part of this baseline.

## Next projects

The sequence is Bonetto BRAM, this MicroBlaze/vendor-MIG CPU/DDR baseline, then
the prepared OpenTPU standalone USER2 JTAG flow on the separately powered card.
PCIe enumeration and transfers follow when a PCIe host is available. The
OpenTPU flow is documented in
[`openTPU/docs/fedora_bringup.md`](../../openTPU/docs/fedora_bringup.md).
Bonetto's replacement DDR PHY still blocks
external Wishbone memory until calibration; the supplied vendor MIG baseline
helps distinguish board failures from custom-controller problems. MDM JTAG UART
and Bonetto's custom USER1 protocol use different host tools.

At 18:01 HKT on 2026-10-10, the host-only preflight was repeated for
`ddr_diag`, `systest` and `ddr_full`. All three report `HOST_READY` and
`STARTUP_AND_MDM_UART_HELP_PASS`, with `cable_present: false` and
`physical_test: NOT_RUN`. The exact receipts and XSDB startup logs are saved
under `build/fedora-microblaze/host-refresh-20261010T1801HKT/`. The live host
USB scan at 18:02 HKT found no JTAG adapter; no chain detection or programming
command ran.

At 18:12 HKT, all three host checks were rerun and still report `HOST_READY`
and `STARTUP_AND_MDM_UART_HELP_PASS`; `cable_present` remains false and
`physical_test` remains `NOT_RUN`. The receipts, XSDB logs and USB snapshot are
saved under `build/fedora-microblaze/recheck-20261010T1812HKT/`. The host-flow
suite was rerun: 28 tests passed. The standalone full-DDR algorithm model also
passed range/endpoints, alias, final-word corruption and all 64 stuck-bit
checks; its compile and run logs are in the same directory. These are host
checks only, not board DDR or JTAG evidence.

At 18:37 HKT, the host-only readiness checks were repeated for all three
applications. `ddr_diag`, `systest` and `ddr_full` each exited successfully and
reported `HOST_READY`, `STARTUP_AND_MDM_UART_HELP_PASS`, `cable_present: false`,
and `physical_test: NOT_RUN`. Receipts, XSDB logs, and contemporaneous USB and
process snapshots are under
`build/fedora-microblaze/host-refresh-20261010T183748HKT/`. The USB scan still
shows no JTAG adapter, so no chain detection or programming ran.
