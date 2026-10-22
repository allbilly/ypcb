> Historical handoff archived from the earlier shared workspace. This file preserves
> dated OpenTPU and MicroBlaze observations, paths and commands; it is not a current
> Bonetto readiness report. Consult the shared YPCB project inventory and each
> current checkout before reusing artifacts or resuming work. No build or hardware
> action was performed by the 2026-10-23 documentation and snapshot review.

# YPCB MicroBlaze and OpenTPU preparation

Native Vivado completed 2026-10-10 20:25 HKT; physical JTAG bring-up started at 21:38 HKT.
The user selected Vivado and explicitly deferred OpenXC7, which remains stopped
and preserved. The full OpenTPU JTAG bitstream now exists and passes provenance,
routing and internal timing checks. MicroBlaze is host-ready. The connected
XC7K480T has now been loaded with the native OpenTPU image into volatile SRAM.
Physical USER2 communication and the expected accelerator configuration pass;
both DDR channels report calibration by the core's CPU. Full memory integrity
failed on channel 0 byte lane 6; channel 1 passed full-region zero, random and address
BISTs. Bounded vector and matrix computation now matches the ISA reference
bit for bit on hardware; full-memory and README model qualification remain
incomplete. OpenTPU CDC and synthesis findings remain open.

## User-selected first run

- YPCB card separately powered, connected by JTAG only per the user's choice;
  the PCIe host path is out of scope for the first run. Static MicroBlaze
  connectivity shows CPU/DDR clocks on the board/MIG domains and XDMA on a
  separate PCIe-derived domain; startup with that clock absent remains to be
  proven on the powered board.
- The current goal is to load OpenTPU and return correct computation results
  over JTAG. Its native Vivado image is loaded; OpenXC7 remains deferred.
  The MicroBlaze/vendor-MIG baseline remains available for separate diagnosis.
- The original 20:36 HKT scan found no adapter. At 21:38 HKT the DLC10 became
  available, and its initialization identified one XC7K480T at index 0 with
  IDCODE `0x23751093` and IR length 6.

## MicroBlaze

Repository: `${YPCB_ROOT}/projects/ypcb_00338_1p1_hack` (source revision
`8b13ecf71b7061dd43a2b1580f0caa469f64303f`). The supplied XC7K480T bitstream
passes the offline structural check and matches SHA256
`22e7281f7574d4e56153ce7345d9e0fb0044c80d56075e45724adcb496337931`.
The 18:54 HKT host-only refresh has all three apps (`ddr_diag`, `systest` and
`ddr_full`) at `HOST_READY`; all physical tests are `NOT_RUN`, with
`cable_present: false`. The receipt is in
`../ypcb_00338_1p1_hack/build/fedora-microblaze/host-refresh-20261010T1853HKT/`.
The host-flow suite passed 28
tests, and the full-DDR C algorithm model passed range, alias, corruption and
stuck-bit checks. These are host/model checks, not FPGA or DDR proof.

At 17:53 HKT, the static clock/reset audit was rerun against the saved HWH: all
13 checked connections matched (`STATIC_CONNECTIONS_VERIFIED`, zero
mismatches; source SHA256
`cf75cb7a6a445f0e04260a8984cae36190ed446c27ed275aca7701db30db19ba`). The
fresh receipt is
`../ypcb_00338_1p1_hack/build/fedora-microblaze/clock-review.json`. A USB
recheck at 17:52 HKT still found no Digilent, FTDI or Xilinx JTAG adapter. The
clock review confirms the CPU/MDM and MIG wiring, with XDMA on a separate PCIe
clock; startup with PCIe absent remains a powered-board test.

The 18:01 HKT preflights are preserved under
`../ypcb_00338_1p1_hack/build/fedora-microblaze/host-refresh-20261010T1801HKT/`.
At 18:12 HKT, all three app checks (`ddr_diag`, `systest`, `ddr_full`) were
rerun and again report `HOST_READY`, `STARTUP_AND_MDM_UART_HELP_PASS`,
`cable_present: false`, and `physical_test: NOT_RUN`. Receipts, XSDB logs and
USB enumeration are saved under
`../ypcb_00338_1p1_hack/build/fedora-microblaze/recheck-20261010T1812HKT/`.
No JTAG adapter is present, so the physical tests still cannot run.

At 18:37 HKT, all three host-only readiness checks were rerun. Each command
exited 0 and reported `HOST_READY`, `STARTUP_AND_MDM_UART_HELP_PASS`,
`cable_present: false`, and `physical_test: NOT_RUN`. The refresh receipts,
XSDB logs and USB/process snapshots are under
`../ypcb_00338_1p1_hack/build/fedora-microblaze/host-refresh-20261010T183748HKT/`.
The fresh USB scan still shows no JTAG adapter.

Evidence and handoff: [docs/FEDORA_BRINGUP.md](../ypcb_00338_1p1_hack/docs/FEDORA_BRINGUP.md).
Latest host-flow test log:
`../ypcb_00338_1p1_hack/build/fedora-microblaze/host-flow-20261010T134349HKT/unittest.log`.
Latest full-DDR algorithm model log:
`../ypcb_00338_1p1_hack/build/fedora-microblaze/ddr-full-core-host-20261010T134451HKT/test.log`.

## OpenTPU

Current native image:
`build/opentpu-placer-recovery-20261007T165149Z/vivado-full-jtag-route-bitstream-20261010T121007Z/output/design.bit`.
SHA256: `a0a2b5cb2f410b0db7426aaef5d1b603d3c84a30c14a362bf8de61ca835b0a73`;
11,599,613 bytes. Vivado routed all 278,220 routable nets with zero errors.
Setup, hold and pulse-width checks pass (WNS +0.139 ns, WHS +0.037 ns,
WPWS +0.264 ns), and all 30 bus-skew constraints are met. DRC has zero errors.
External DDR timing and full-memory integrity remain unqualified; bounded
physical computation has passed, as described in the latest entries below.
Two reset-related CDC-10 findings and eight memory-removal synthesis warnings
remain under review; this is a test candidate, not a physical pass.

The native-image selection is
`../openTPU/build/fedora-vivado/jtag-current.json`, pointing to the completed
run's immutable manifest. `native-image-check.json` and
`native-program-negative-checks.json` in the run directory preserve the image
check and rejection of a reduced profile or changed bitstream hash. See
`../openTPU/docs/fedora_bringup.md` for the native loading and USER2 test commands.
They reuse the DDR800 calibration data and require no OpenXC7 build tools.

The latest USB-only replug retest completed at 23:45 HKT: native SRAM loading
and all fourteen bounded compute cases passed, channel 1 passed full 2 GiB
zero/random/address patterns, and channel 0 still failed exclusively on lane
6. The cable is released; a physical card power cycle remains unconfirmed.
See the final progress entry for the current receipts and next action.

### Earlier implementation history

Repository: `${OTPU_ROOT}` (checkout `5b1e646cdec9de449ba416952ec854b0b2d973d7`). Vivado's original native synthesis succeeded in 5h18m42s elapsed (3h46m04s CPU); writing the reference synthesis checkpoint then took another 5m24s. The full Vivado session ran 00:12:49–05:40:55 HKT. The reference script explicitly set `general.maxThreads 1` and launched synthesis with `-jobs 1`; the log records a 399.251 MHz CPU frequency at startup and peak synthesized-design PSS of about 6.46 GiB. The synthesized netlist contains 716 DSP48E1s, 562 RAMB36E1s and 34 RAMB18E1s. The thread limit constrained synthesis parallelism; the startup frequency is a single observation. No controlled comparison quantifies either condition's contribution to elapsed time. The 5m24s figure is checkpoint writing only, not total synthesis time. The hashed synthesis log is
`build/opentpu-placer-recovery-20261007T165149Z/vivado-full-jtag-reference-20261009T154026Z/project/native_full_jtag.runs/synth_1/runme.log`
(SHA256 `97343fd22e1d5fba38ef2ea8f641ef42c99929d3f4621271138392c97c09bc6e`). The preserved placement/pre-route checkpoint is at
`build/opentpu-placer-recovery-20261007T165149Z/vivado-full-jtag-implementation-corrected-v2-20261010T001951Z/project/native_full_jtag.runs/impl_1/otpu_fpga_top_openxc7_jtag_physopt.dcp`
(SHA256 `0d31325391d3eda33dc1baa57b9e5a78efdad147a68a5475721bd1210e3386ea`).

The resumed `route_design` started at 16:42 HKT and completed successfully at 17:10 HKT. Route time was 1,288 seconds wall-clock (21m32s), 47m04s aggregate CPU, with 6.75 GiB peak memory. It routed all 278,219 routable nets with zero routing errors and zero final node overlaps. Timing on this checkpoint is WNS `+0.086 ns`, TNS `0`, WHS `+0.017 ns`, THS `0`; the report says user timing constraints are met. Evidence is in
`build/opentpu-placer-recovery-20261007T165149Z/vivado-full-jtag-implementation-corrected-v2-20261010T001951Z/project/native_full_jtag.runs/impl_1/`.

The long wait in that attempt was the timing-driven router resolving congestion across a large design: 278k routable nets and several global rip-up/reroute iterations. The earlier run had reported 278,185 failed nets after initial routing and stalled in congestion recovery; Fedora rebooted before that attempt completed. The resumed route itself then took 21m32s. This evidence points to routing congestion and the interrupted first attempt, not Vivado synthesis/export or a demonstrated Vivado defect.

That earlier unconstrained route is not a usable bitstream reference. Its implementation XDC contained only a timing exception, so routed DRC reported NSTD-1 and UCIO-1 for 234 of 243 ports. A read-only probe applied the DDR XDC after routing and produced placement conflicts and other errors; late application cannot repair a route. No bitstream was generated from that attempt.

The pre-placement audit has now resolved that uncertainty. The DDR XDC's 117 pins per channel match both supplied vendor MIG pin files exactly (234/234). With `board-jtag.xdc`, the full corrected DDR XDC, and `jtag-clock.xdc` loaded on the synthesized checkpoint, Vivado's DRC has no NSTD-1, UCIO-1, BIVC-1, or other errors; all 243 top-level ports have pins and standards. The post-route BIVC/LOC errors came from applying constraints to already placed I/O. Audit reports are under
`build/opentpu-placer-recovery-20261007T165149Z/constraint-validation-20261010T1727HKT/`.

A separate copy of the implementation project is at
`build/opentpu-placer-recovery-20261007T165149Z/vivado-full-jtag-implementation-constrained-20261010T1732HKT/`.
In that copy, the implementation-only `litedram-implementation.xdc` contains
the full corrected DDR pins and timing constraints; the previous route and
checkpoints remain preserved. Its fresh Vivado implementation started around
17:35 HKT from the saved synthesis checkpoint. It passed `opt_design` and
post-opt DRC with zero errors, completed placement in 10m42s wall time (25m18s
aggregate CPU time across worker threads; peak memory about 6.1 GiB), and wrote
`project/native_full_jtag.runs/impl_1/otpu_fpga_top_openxc7_jtag_placed.dcp`.
Physical optimization then completed, but the implementation script was
interrupted at 17:50 HKT on the user's request before routing began. No current
Vivado process remains. This constrained placed checkpoint is preserved, but
it is not a routed design or bitstream. A route-only resume script is prepared
at
`build/opentpu-placer-recovery-20261007T165149Z/vivado-full-jtag-implementation-constrained-20261010T1732HKT/resume-route-from-placed.tcl`.
It opens the preserved DCP, checks the top and all 243 ports for LOC and
IOSTANDARD constraints, routes with up to four threads, and writes reports plus
a routed DCP under a new output directory. It does not write a bitstream and
has not been run. Tcl syntax/precondition checks passed; script SHA256 is
`1c5540caf6b14d56838966f1ab54d16c47e8e9fdebd17ffd91d42b8bfc691c01`.

Vivado's elapsed time is coming from the size and implementation work of this
XC7K480T design, rather than a silent or dead process: the previous route had
278,219 routable nets and took 21m32s, while the new, correctly constrained
attempt spent about 11 minutes in placement alone. Parallel workers account
for aggregate CPU time being greater than wall time. The first implementation
also used the wrong XDC scope, so its completed routing effort could not serve
as the reference and had to be preserved as diagnostic evidence instead.

Eight `Synth 8-13374` BRAM/URAM-unreachable warnings remain unresolved. The separately powered JTAG-only board test is pending because no JTAG adapter is enumerated on the host. The interrupted-run snapshot and constraint probe are under
`build/opentpu-placer-recovery-20261007T165149Z/route-recovery-20261010T1638HKT/`.

The old 10-second host sample found all cores near 399.25 MHz under CPU pressure, with memory and I/O pressure near zero. Saved evidence:
`../openTPU/build/fedora-openxc7/route-host-sample-20261010T1350HKT.txt`
(SHA256 `38a930acbe9c9e38b6d271421aed7ca8414c637ffd4fec9e7731b28e6f8f8e23`).

The JTAG host and RTL preparation is in place: host tests passed (13 JTAG
transport tests and 36 host-behavior tests), and `make -C boards/ypcb-00338
sim-jtag` passed all three RTL benches, including the serial USER2-to-AXI
read/write path. These do not model the full FPGA top/BSCANE2 or prove physical
JTAG. Latest bench log:
`../openTPU/build/fedora-openxc7/sim-jtag-target-20261010T134619HKT/make.log`
(SHA256 `8a6ee9906d9b49cfe93cbce333b8a3c6f042a83d364ef4cac2f4f1a63b7e0a75`).

At 18:04 HKT, the focused JTAG transport and OpenXC7 reference Python tests
were rerun in the repository's pinned Fedora virtual environment: 20 passed.
All three `sim-jtag` benches also passed again. Their logs and the contemporaneous
USB/process snapshots are saved in
`../openTPU/build/fedora-openxc7/host-recheck-20261010T1804HKT/`. The snapshot
still has no JTAG adapter and no Vivado/nextpnr/Yosys process. These remain
host and RTL-simulation results, not a physical board pass.

The repository-wide pytest suite collected 1,511 cases. It was started at
18:06 HKT and intentionally interrupted at 18:11 HKT after 43 passing progress
markers while the broader RTL/model suite continued to consume build time. It
exited 130 without a final summary and is not a full-suite pass. The partial
log and explicit status are in
`../openTPU/build/fedora-openxc7/full-suite-20261010T1806HKT/`.

At 18:15 HKT, a source-level audit confirmed that the prepared USER2 transport
supports compute over JTAG: `fedora_jtag.py selftest` uses `JtagTransport` for
DDR program/input writes, control-register start/poll, and output readback;
the existing kernel check compares card output with the ISA simulator.
`fedora_chat.py --transport jtag` selects the same transport for inference and
checks the full DDR800 profile before creating `BoardBackend`. The XVC server
dry run revalidated the prepared binary/firmware and command pair; its receipt
is `../openTPU/build/fedora-openxc7/host-recheck-20261010T1804HKT/jtag-server-dry-run-20261010T1814HKT.json`.
These remain source/host checks: no bitstream was loaded and no physical
compute was verified.

At 18:18 HKT, a new loopback regression exercised the Python XVC TCP client
against a local IDCODE/USER2 endpoint, including TMS scan framing, register
read/write and DDR read/write at channel 1's upper boundary. The combined
JTAG/OpenXC7 host tests passed 21 cases and all three USER2/AXI RTL benches
passed. Logs and source hashes are saved under
`../openTPU/build/fedora-openxc7/jtag-xvc-recheck-20261010T1818HKT/`. This
tests the host socket/mailbox path and RTL bridge separately; it does not
prove BSCANE2 or physical JTAG.

At 18:23 HKT, the focused full-board-model kernel test passed: Verilator's
`tb_board` ran the program and the modeled DDR output matched the ISA
simulator. The captured run took 204.89 seconds, including its first build of
cache `tb_board_665f39be259f`. The receipt and log are under
`../openTPU/build/fedora-openxc7/board-kernel-sim-20261010T1819HKT/`. This
proves compute parity in the Verilator board model only; it does not include
the USER2 mailbox/BSCANE2 or physical JTAG.

At 18:29 HKT, the complete staged `otpu-selftest --sim --bw-mib 1` passed on
the Verilator board model: link, configuration, both calibration channels,
registers, DDR address/pattern checks, kernels, VPU operations, and streaming.
Bandwidth was skipped by design on the model. The log and exit code are in
`../openTPU/build/fedora-openxc7/full-selftest-20261010T182553HKT/`. This is
model-level evidence only; no physical JTAG or DDR test has run.

At 18:35 HKT, an isolated nextpnr-himbaechel build corrected the XC7 full-design
placement retry-limit overflow. Its 64-bit arithmetic contract passed nine
boundary cases under UBSan, including the 531,351-cell configuration; the
limit saturates at 2,147,483,646 so the placer counter can exceed it safely.
The new backend SHA256 is
`b7c15652ebea939e346fb580985240a54762f3feb0948eb285e6c2061b8de759`.
Carry equivalence (all 256 input combinations), four 16-DSP cascades, and FF
clock-edge timing probes passed on this binary. Strict Project X-Ray frame
assembly also passed for the carry, DSP, and corrected FF probes. Detailed
receipts are in
`../openTPU/build/fedora-openxc7/placer-timeout-backend-20261010T1831HKT/`,
`../openTPU/build/fedora-openxc7/placer-timeout-carry-check-20261010T1835HKT/`,
`../openTPU/build/fedora-openxc7/placer-timeout-dsp-check-20261010T1835HKT/`,
`../openTPU/build/fedora-openxc7/placer-timeout-ff-edge-check-20261010T1838HKT/`,
and
`../openTPU/build/fedora-openxc7/placer-timeout-strict-frames-20261010T1835HKT.json`.
Full-design placement, timing qualification, bitstream generation and physical
validation remain incomplete.

At 18:42 HKT, a synthesis cross-check confirmed that the native Vivado and
OpenXC7 runs used identical SHA256s for all 31 RTL/generated-core inputs and
the same full-compute DDR800 profile (MCOLS=4, ACT_ROWS=4, MXU_IMPL=2,
VPU_CL=2, LANES=8, 100 MHz, DDR_MTS=800). Both mapped a BSCANE2 and retained the
VexRiscv calibration CPU. Their synthesis resource counts differ by one DSP
(716 Vivado, 717 OpenXC7) and 24 RAMB18 equivalents (1,158 Vivado, 1,134
OpenXC7); these are tool mapping differences, not functional or timing proof.
The comparison receipt is
`../openTPU/build/fedora-openxc7/vivado-synthesis-crosscheck-20261010T1842HKT.json`.
Neither flow has completed a valid full-design route in this state.

Eight Vivado synthesis warnings about unreachable BRAM/URAM instances remain
unresolved. The instances are absent from the final mapped hierarchy/resource
inventory, but their source functions and functional harmlessness have not
been established. The warning paths are `u_vpui_89/i_8`, `u_vpui_89/i_9`,
`u_vpui_89/i_10`, `u_vpui_89/i_11`, `u_vpui_89/i_14`, `u_vpui_89/i_15`,
`u_vpui_89/i_19`, and `i_26`. A read-only Vivado checkpoint mapping query was
started at low priority and stopped after five minutes in `open_checkpoint`
without a result. The separate constrained implementation was later stopped at
the user's request before routing, as recorded above. No mapping result is
available yet.

## 2026-10-10 18:48 HKT — corrected full OpenXC7 route running

The three MicroBlaze host checks (`ddr_diag`, `systest`, `ddr_full`) were
rerun and all returned `HOST_READY`; each XSDB startup/MDM UART check passed.
They still report `cable_present: false` and `physical_test: NOT_RUN`. A fresh
`lsusb` likewise showed no Digilent/FTDI/Xilinx adapter.
The archived readiness outputs are under
`../ypcb_00338_1p1_hack/build/fedora-microblaze/host-refresh-20261010T1853HKT/`.

The normal OpenXC7 tool/profile check passed at
`../openTPU/build/fedora-openxc7/check-20261010T104503Z/manifest.json`.
Before routing, SHA256 validation confirmed that the existing full DDR800
netlist (`synth.json`, `074ed71d...`) and all 31 recorded RTL/generated-core
inputs still match the current files. The selected timeout-corrected nextpnr
binary is
`../openTPU/build/fedora-openxc7/placer-timeout-backend-20261010T1831HKT/nextpnr-himbaechel`
(SHA256 `b7c15652...`); its carry, DSP, FF-edge and strict-frame probe receipts
match that exact binary.

The first full JTAG-profile placement/route was launched in
`../openTPU/build/fedora-openxc7/timeout-corrected-full-jtag-route-20261010T1048Z/`.
with the corrected backend explicitly selected because the older
`implementation-active.json` still names the pre-timeout backend. At 18:47 HKT
nextpnr PID 37523 was active at about 129% CPU and 6.3 GiB RSS. The route log
records the corrected limit (`531351` cells, `2147483646` attempts) and initial
analytic placement of 300,290 cells. The run was still in the analytical
placer at 18:58 HKT, with no new log marker; it had not passed placement. No
Vivado process was started.

At 18:54 HKT, the two-thread corrected OpenXC7 route was still actively
computing in the main analytical placer (PID 37523, about 7.5 minutes elapsed,
121% CPU and 6.2 GiB RSS). Its log had no new progress marker or errors since
initialization; memory pressure remained zero.

The prior full static attempt in
`pipeline-full-static-exp-jtag-20261009T084508Z/` used the same saturated
2,147,483,646-attempt cap and ultimately failed static legalization on an
`SELMUX2_1` cell. That confirms the timeout arithmetic fix alone does not prove
full-design placement. The current attempt uses a different backend snapshot
and nextpnr's default `heap` placer (`--placer` omitted; verified by backend
help); the prior failed command explicitly selected `static`. At 18:58 HKT it
remained active in initial analytical placement with no new log marker or
error. Treat it as a distinct placement experiment, not evidence that the cap
change alone solved the previous failure.

## 2026-10-10 19:03 HKT — OpenXC7 route restarted with all available cores

The user requested all cores. This host exposes CPUs 0–7 to the job (`nproc=8`,
no lower cgroup quota); 27–28 GiB RAM was available and memory pressure was
zero. The initial two-thread route above was interrupted with SIGINT after
verifying its exact PID/command. Its netlist and logs are preserved, and its
manifest records `INTERRUPTED_SUPERSEDED_BY_ALL_CORE_RUN`.

`tools/fedora_openxc7.py` now accepts `OTPU_THREADS=all` (or a positive
integer); the default remains two for compatibility. Python byte-compilation
and `git diff --check` passed. The full route was restarted with eight threads,
the same DDR800 synthesis netlist and the same timeout-corrected backend in
`../openTPU/build/fedora-openxc7/timeout-corrected-full-jtag-route-all-cores-20261010T1903HKT/`.
The manifest says `route_threads: 8`, and `route.command.json` contains
`--threads 8`. At 19:03 HKT it was 14 seconds into nextpnr and still in
pre-placement packing; this early phase was using about one CPU and 5.7 GiB RSS.
The all-core setting enables up to eight workers where nextpnr's stages
parallelize; it does not guarantee an eightfold speedup. Placement, routing,
timing qualification, strict full-design frame assembly, bitstream creation and
physical tests remain pending.

At 19:04 HKT nextpnr had entered initial analytical placement (PID 39692, 56
seconds elapsed, about 128% CPU and 6.4 GiB RSS). At 19:05 HKT it had advanced
through placer iteration 1 (1 minute 48 seconds elapsed, 148% average CPU and
6.3 GiB RSS). The command requests eight threads, but this early stage was using
about one to two CPUs; nextpnr's thread setting applies to configurable parallel
passes, not every stage. Memory pressure remained zero. This is active placement,
not a route pass.

## 2026-10-10 19:18 HKT — exact MUXF8 probe passed; full legalizer advancing

The previous static failure's exact MUXF8 subtree was extracted from the full
DDR800 netlist, preserving its two MUXF7 cells, LUT6 and constant branches.
Its eight boundary signals became independent probe inputs. On the same
`b7c15652...` backend, all three MUX cells were placed in
`SLICE_X0Y231` (F7AMUX, F7BMUX and F8MUX), routed successfully, and compared
against the original XC7 primitive models for all 256 input combinations.
Strict Project X-Ray frame assembly passed. The final helper verification
produced byte-identical FASM, so it reused the checked strict frames after
revalidating their SHA256 rather than repeating assembly.

The source is `../openTPU/tools/openxc7_mux_cluster_check.py`; the final receipt
and an immutable copy of the tested helper are in
`../openTPU/build/fedora-openxc7/extracted-mux8-verified-20261010T1916HKT/`.
The receipt reports `EXTRACTED_MUX_ROUTE_EQUIVALENCE_AND_STRICT_FRAMES_PASS`.
This proves this specific isolated packing case. It does not establish that
the complete design can fit alongside the other cells, close timing, or run on
the board. No probe bitstream was generated or programmed.

Two bounded read-only debugger observations of the original all-core process
at 19:16:25 and 19:17:46 HKT captured the strict legalizer's call counter rising
from 57,020 to 60,390 and its queue length falling from 243,270 to 239,900.
Calls include retries/rip-ups and queue entries can include bound cells: these
are evidence of progress, not unique placement counts, percent complete or an
ETA. Both observations detached cleanly, confirmed the original PID/start time,
and verified CPU-time advancement with no remaining tracer. The snapshots are
`placer-counter-20261010T111624Z.json` and
`placer-counter-20261010T111745Z.json` inside the active full-route directory.
At 19:18 HKT PID 39692 remained running with about 6.2 GiB RSS. No full-route
result, FASM, bitstream or physical result exists yet.

Current ten-second host telemetry differs from the old 400 MHz snapshot:
nextpnr used approximately one CPU, aggregate host busy time was 13.6%,
reported per-CPU clocks ranged about 1.6–4.2 GHz, and CPU/memory pressure was
negligible. The active strict-legalizer stage is serial. Affinity permits all
eight CPUs, and every applicable cgroup `cpu.max` is unlimited. Receipts are
`host-telemetry.json` and `host-cpu-limits.json` in the active route directory.
These samples do not diagnose the cause of the historical 400 MHz condition.
The fresh USB enumeration still shows no JTAG adapter, so MicroBlaze and
OpenTPU physical tests remain unavailable. Vivado remains stopped.

## 2026-10-10 19:55 HKT — carry correction restored; merged full route active

The `b7c15652...` timeout-corrected backend omitted the previously validated
correction that permits carry clusters in the second slice of a tile. Its
lower-slice carry probe did not cover that regression. The upper-slice check
failed because the diagnostic option was absent, and a source comparison
confirmed that the placement correction itself was also absent. That diagnostic
returned exit zero without a routed output; the artifact checker correctly
rejected it. Evidence is in
`../openTPU/build/fedora-openxc7/placer-timeout-upper-carry-check-20261010T1928HKT/`.

A merged backend restores the second-slice correction while retaining carry
padding, consecutive DSP sites, DSP LOC handling, FF clock edges and finite
64-bit timeout arithmetic. The new binary is
`../openTPU/build/fedora-openxc7/merged-carry-sites-backend-20261010T1935HKT/nextpnr-himbaechel`,
SHA256 `975e6dbd3cb87e8e4cac71fc2e4b68b9afa0b1695c0a5b1ebd85e551485577d2`.
Five probe groups passed on this exact binary: lower carry, upper carry,
16-site DSP cascades, FF-edge semantics and the extracted MUXF8 tree. The upper
probe placed eight carries in second slices with four dedicated cascade links;
the DSP probe placed 64 DSPs and routed 2,880 cascade bits. Strict Project X-Ray
frame assembly passed for all five, recorded in
`../openTPU/build/fedora-openxc7/merged-correction-strict-frames-20261010T1943HKT.json`.
These are isolated correction checks, not full-design fit or hardware proof.

The JTAG image checker now verifies the selected backend against exact build,
source, probe and strict-frame receipts instead of accepting a backend name or
an unrelated old binary hash. The actual full synthesis selection passed;
substituting a different binary or reduced compute profile was rejected.
Receipt:
`../openTPU/build/fedora-openxc7/merged-carry-sites-backend-20261010T1935HKT/selection-verification.json`.
Python byte-compilation and `git diff --check` passed after the helper changes.
The separate PCIe checker policy was not changed.

Only after those checks passed was PID 39692 interrupted; its outputs are
preserved and its manifest records
`INTERRUPTED_SUPERSEDED_BY_RESTORED_CARRY_CORRECTION`. The replacement full
JTAG-profile run started at 19:49:39 HKT from the unchanged full DDR800 mapped
netlist, with `--threads 8`, in
`../openTPU/build/fedora-openxc7/merged-full-jtag-route-all-cores-20261010T114939Z/`.
At 19:54 HKT, parent PID 43429 and nextpnr PID 43460 were live; nextpnr had
about 4m35s elapsed, 141% lifetime-average CPU and 6.2 GiB RSS. Its manifest
was `RUNNING`, and its log had completed initial analytic iterations 0–3 and
entered the main analytical placer. No full-route pass or bitstream exists.
Vivado remains stopped. The thread setting enables parallel passes; serial
legalization cannot use all eight cores simultaneously.

The three MicroBlaze ELF/bitstream artifact sets were reverified without
programming or rerunning XSDB. The receipt is
`../ypcb_00338_1p1_hack/build/fedora-microblaze/artifact-integrity-20261010T112403Z.json`
(`ALL_THREE_APPLICATION_ARTIFACTS_VERIFIED`). Physical tests remain `NOT_RUN`.

Minutes to hours can be reasonable for a large FPGA implementation, depending
on size, constraints, congestion and host speed. AMD documents that congestion
can significantly increase routing runtime and that Vivado placement/routing
support up to eight threads:
[congestion guidance](https://docs.amd.com/r/en-US/ug949-vivado-design-methodology/Reducing-Net-Delay-Caused-by-Congestion),
[multithreading guidance](https://docs.amd.com/r/en-US/ug904-vivado-implementation/Multithreading-with-the-Vivado-Tools).
Our measured 10m42s constrained placement and 21m32s diagnostic route are
reasonable magnitudes for this design; the latter still lacked usable pin
constraints. The 5h18m42s synthesis was slow under an explicit one-thread limit;
the 399 MHz startup reading does not establish clocks throughout the run.
The multi-day preparation includes backend defects, a dropped correction,
constraint fixes, interruption and repeated attempts. It is not a measured
normal duration for one completed build, and the author's README provides no
comparable runtime benchmark.

## 2026-10-10 20:07 HKT — user selected Vivado; OpenXC7 stopped

The user explicitly said "we use vivado" and "no need openxc7 for now".
The exact OpenXC7 PID/start time/executable/command were verified before SIGINT.
Both PID 43460 and controller 43429 exited; its manifest now records
`INTERRUPTED_USER_SELECTED_VIVADO`, with logs, source and input netlist preserved.
OpenXC7 must not be restarted while this priority remains in force.

Native Vivado 2026.1 was confirmed installed. A durable user service started at
20:07:27 HKT, resuming the **correctly constrained placed checkpoint** without
resynthesis or replacement of the accelerator RTL:
`build/opentpu-placer-recovery-20261007T165149Z/vivado-full-jtag-route-bitstream-20261010T120727Z/`.
The service is `otpu-vivado-jtag-resume-20261010t120727z.service`, controller PID
45600 and actual Vivado process PID 45658. At 20:08 HKT it remained live and was
loading the placed DCP. The copied route script sets `general.maxThreads 8`.
The input DCP SHA256 is
`f4bb60dae19ed150a9d9ae8dc769f37e1f0ab9654d3dc7ab75e13ef0ec04eaf0`.
All 31 original/native RTL snapshot pairs were verified byte-for-byte, and the
full MCOLS=4, ACT_ROWS=4, LANES=8, DDR800/100 MHz configuration was verified.

`scripts/fedora-route-native-jtag.tcl` checks the exact part/top, all 243 board
pin/standard pairs, 1.8 V/GND configuration properties, USER2 BSCANE2 and both
DDR serializer sets before implementation. It runs physical optimization and
routing, preserves routed checkpoint/timing/CDC/bus-skew/DRC reports, and writes
a bitstream only after its setup/hold and DRC gates pass. Default Vivado
bitstream checks stay enabled. `scripts/fedora-run-native-jtag.py` verifies
pinned inputs before and after the native run and independently checks the
resulting .bit container/device/packets. Tcl structural completeness, Python
byte-compilation and whitespace checks passed; actual native execution is
still in progress. The bitstream has not been generated yet.

The host still enumerates no JTAG adapter. It is appropriate to connect JTAG
and power the card separately now, without PCIe, to prepare the first test.
The MicroBlaze bitstream and applications are prepared; OpenTPU loading awaits
the native image and report review. SRAM programming must preserve BPI flash.
Physical calibration, compute and MicroBlaze startup without PCIe are unproven.
The eight memory-removal warnings also remain unresolved; creating a .bit file
does not prove that the intended compute functions survived synthesis.

## Resume checklist

1. Keep OpenXC7 deferred. Native synthesis, placement, routing and bit generation
   have finished; do not restart them solely because hardware is absent.
2. Recheck the native selection with `bash tools/fedora_bringup.sh native-check
   --manifest build/fedora-vivado/jtag-current.json` from the OpenTPU repository.
   A successful check preserves the outstanding CDC, synthesis and physical
   limitations; it does not prove function retention or board operation.
3. Review the two software-reset CDC findings and eight memory-removal warnings.
   Detailed CDC evidence is in
   `build/opentpu-placer-recovery-20261007T165149Z/native-routed-cdc-review-20261010T122934Z/`.
4. Connect the separately powered card and JTAG adapter, then identify the
   single XC7K480T target (`0x23751093`) before SRAM programming. Run the
   MicroBlaze/vendor-MIG baseline first, then the native OpenTPU USER2 status,
   DDR calibration and compute tests. Preserve physical logs. PCIe is
   unnecessary for this first run, and BPI flash must remain untouched.

The two repository worktrees contain extensive existing uncommitted work. Do
not reset, clean, or stage unrelated files.

## 2026-10-10 20:10 HKT — native checkpoint guard corrected; new run started

The 20:07 attempt loaded the placed DCP in 56 seconds, then stopped before
routing: its guard compared `NAME` (the checkpoint's display label) with the
RTL top. This was a controller error. The checkpoint reports the RTL module in
`TOP`, as also demonstrated by the earlier saved native property inspection.
The script now checks `TOP` and records `NAME` separately. The failed run and
logs remain preserved; no bitstream was generated by it.

A new service started at 20:10:07 HKT, with the same placed DCP, full sources,
pin inventory and eight-thread setting:
`otpu-vivado-jtag-resume-20261010t121007z.service`.
Current run directory:
`build/opentpu-placer-recovery-20261007T165149Z/vivado-full-jtag-route-bitstream-20261010T121007Z/`.
All unchanged prepared inputs were reverified before launch. Do not use the
20:07 service or output as the current run. OpenXC7 remains stopped.

At 20:12 HKT the replacement's actual Vivado PID 45917 was confirmed live
against its exact command/executable/start time (controller PID 45860). The
TOP/part guard, all 243 pin/standard pairs, CFGBVS=GND, CONFIG_VOLTAGE=1.8 and
USER2 passed on the actual DCP. Its native inventory retains 716 DSP48E1s,
562 RAMB36E1s, 34 RAMB18E1s, 144 input and 214 output serializers, and 144
IDELAYE2s. The pre-route DRC report has warnings only, with zero errors.
Physical optimization started at 20:11:32 HKT; routing and bitstream creation
are still pending. Evidence is `output/checkpoint-audit.txt`,
`output/pre-route-drc.rpt` and `live-process-20261010T121204Z.json` in the
current run directory.

## 2026-10-10 20:36 HKT — native bitstream completed; hardware handoff prepared

The 20:10 native run completed at 20:25:29 HKT with command and independent
structure-check exit codes 0. Routing took 9m32s wall time; bit generation took
1m57s. The correctly constrained placed checkpoint and all 31 native source
pairs were reused and hash-verified. The retained configuration is MCOLS=4,
ACT_ROWS=4, MXU_IMPL=2, VPU_CL=2, LANES=8, CORE_KHZ=100000 and DDR_MTS=800.
All 243 pin/standard pairs, 1.8 V/GND configuration and USER2 were checked.
No DRC severity was downgraded. The final routed DCP and implementation reports
are preserved alongside the bitstream.

`tools/fedora_check_native_image.py` independently verifies the completed native
manifest, input/artifact hashes, full source/configuration identity, native cell
inventory, routing, internal timing coverage, all bus-skew constraints and
bitstream structure. The current image passes. The new `program-vivado` command
performs this check before cable access, checks a fresh single-device chain,
rechecks the image after initialization and programs volatile SRAM only.
Deliberately wrong-profile and wrong-hash manifests were both refused before
cable access. No positive programming command has been executed.

A read-only native report of the routed DCP completed at 20:31 HKT. It identifies
two CDC-10 Critical paths from `u_ld/reset_wr_stb_reg/C` to `u_ld/FDCE/D` and
`u_ld/FDCE_8/D`, each recognized as an eight-stage synchronizer. Source inspection
maps these to the CSR software-reset logic feeding the MMCM and PLL reset
chains. Combinational logic precedes their first stages; recognizing the chains
does not clear the finding or prove reliable pulse capture. The findings remain
open. The eight Synth 8-13374 memory-removal warnings also remain unresolved.

The separate timing-coverage limitations are explicit: 149 inputs and 221
outputs lack external delays (primarily the DDR PHY plus false-pathed board
signals). Internal constrained timing passed; external DDR interface timing is
not fully signed off. Calibration, both memory channels and actual compute
must be tested on the powered card.

All three MicroBlaze checks were refreshed and report `HOST_READY`, debugger
startup/help pass, `cable_present: false` and physical test `NOT_RUN`. The USB
scan found no JTAG adapter. OpenTPU's XVC host dry-run and matching DDR800 CLI
preparation also passed; neither the server nor physical tests were started.

The 20:38:59 HKT handoff snapshot is preserved in
`build/opentpu-placer-recovery-20261007T165149Z/native-jtag-handoff-20261010T123859Z/`:
native image check, all three MicroBlaze readiness receipts, USB enumeration,
source-mapped CDC review and `handoff.json`. Both repositories passed
`git diff --check`, and the updated documents passed whitespace/fence checks.

## 2026-10-10 20:44 HKT — global software-reset pulse loss reproduced

The two native CDC-10 findings were investigated with the exact generated CSR
storage/strobe logic, reset-combination logic and sixteen FDCE instance bodies
extracted from the hash-matched DDR800 core. The simulation used Vivado's
installed FDCE model and global startup model. At 100 MHz source / 50 MHz
destination, a one-source-cycle reset was captured in one tested clock phase
and missed in the other, for both the MMCM and PLL chains. A four-cycle control
pulse was captured in both phases. This is evidence of a real pulse-capture
limitation; the four-cycle stimulus is not a fix applied to the image.

Evidence and repeatable simulation inputs are in
`build/opentpu-placer-recovery-20261007T165149Z/native-reset-cdc-experiment-20261010T124442Z/`.
`result.json` records source/model hashes, exact commands and limitations.
The experiment covers the extracted reset cone, not metastability, a complete
routed-netlist simulation or physical hardware.

The affected CSR is `ctrl_reset` at LiteDRAM offset `0x2000` (host register
address `0x12000`). Do not use its global-reset bit on the current test image;
use a fresh volatile SRAM load for a full FPGA reset. The wrapper ties the
external LiteDRAM reset input to zero. The calibration CPU has a separate
`selfcal_hold` control; it is not this global clock-generator reset.

The exact pinned DDR800 RV32I firmware is now being run on the generated
VexRiscv/CSR/hold model to check both-channel calibration and CPU hold/release,
with CSR writes recorded to determine whether those paths touch `ctrl_reset`.
This is a software/RTL model check, not physical DDR qualification. Review run:
`build/opentpu-placer-recovery-20261007T165149Z/native-ddr800-firmware-reset-review-20261010T124653Z/`.
The first invocation lacked NumPy in the LiteDRAM environment; its error is
preserved. The live replacement uses the prepared host Python environment and
the existing pure-Python LiteX/Migen packages. Simulation compilation used eight
jobs and completed in seven seconds. OpenXC7 build tools remain deferred.

At 20:54:44 HKT the replacement was confirmed live as PID 49703, start ticks
1572663, under exec session 11497. Its log reports the expected selfcal identity
`0x5ca10018` and configuration `0x103` (both channels, scan stride 1). It is
executing the actual calibration firmware; no terminal result exists yet.
`live-process.json` preserves exact process identity, script hash and log paths.
Resume this existing session and inspect its eventual `result.json` or
`failure.json`; do not restart solely because output is quiet. Native image
selection was rechecked and still passes without source or bitstream changes.

## 2026-10-10 21:27 HKT — exact firmware model review passed

The earlier 20:54 live firmware review subsequently exited 1 during profiling
because `riscv64-elf-nm` was absent. The profiler now selects an installed ELF
symbol reader and reports simulated time using the selected core clock. The
replacement review reused the compiled model after checking generated logic
identity; only two generation timestamp comments differed. All pinned inputs
remained unchanged. Both DDR PHY models calibrated, and firmware/Python
reference traces matched all 6,951,674 PHY CSR writes. CPU hold stopped CSR
writes, and release completed calibration again. No global-reset CSR writes
occurred. First completion was 7.540 simulated seconds at 100 MHz.

The final result is `DDR800_ACTUAL_FIRMWARE_CPU_MODEL_CALIBRATION_AND_HOLD_RELEASE_PASS_GLOBAL_RESET_UNUSED`,
in `build/opentpu-placer-recovery-20261007T165149Z/native-ddr800-firmware-reset-review-20261010T131026Z/result.json`.
This covers actual firmware on the generated CPU/CSR model with modeled PHYs;
it does not establish routed-netlist equivalence or physical DDR integrity.
The global-reset CDC findings remain open. The shared-memory structural audit
is also incomplete: its first full comparison found a write-address alias
requiring resolution, so it has not cleared any synthesis warning.

## 2026-10-10 21:41 HKT — OpenTPU loaded and physical JTAG status passed

The current user goal authorizes programming and computation on the connected
card. Early USB connections at 21:36 HKT were transient; a stable DLC10 was
available at 21:38 HKT. The guarded native-image command verified provenance
and a fresh single-device `0x23751093` chain, then loaded the selected
11,599,613-byte Vivado bitstream into SRAM at 6 MHz. Loader exit was 0, with
`INIT=1`, `DONE=1`, and `isc_done=1`. BPI flash was not written.

The first XVC server exited because its quit prompt received EOF from a
noninteractive pipe. The replacement runs under a persistent PTY and exposes
localhost port 3721. Physical SMI exit was 0: OpenTPU ID `0x4f545055`, register
map 3, D=128, MCOLS=4, LANES=8, 100 MHz, DDR3-800, build `5b1e646c`, both
calibration bits set, idle accelerator, die temperature 50.69 C. `memcal cal`
confirmed both channels already calibrated by the core's CPU and exited 0.
The physical selftest passed link, configuration and calibration; memory scrub,
integrity and compute stages are still running and have no final result yet.

All commands, timestamps, USB observations, loader/server logs and physical
SMI output are saved under
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/`.
The active XVC exec session is 94202; physical selftest session is 69048.
Actual LFM2.5-230M weights are available locally for a subsequent token
comparison with the ISA simulator. No physical kernel or model pass is claimed
until those stages finish. OpenXC7 build work remains deferred.

## 2026-10-10 21:48 HKT — physical DDR0 lane 6 failure localized

The first selftest stopped at scrub. The full 2 GiB channel-0 zero-data read
reported 76,428 wrong beats, all on byte lane 6. Independent repeats with zero
and random data also failed on that lane, while channel 1 passed both full
2 GiB patterns with zero errors across all nine lanes. Physical BIST timings
are reported at the actual 100 MHz core clock, unlike the initial scrub
helper's historical 133.33 MHz bandwidth label.

The calibration CPU's mailbox reports only a two-step common channel-0 write
window (45 ps) at CK phase 25, against an 84-step channel-1 window. The CPU
was held using its separate hold CSR before PHY experiments. A 256 MiB read
tap scan found no passing tap for channel-0 lane 6; other lanes had 12–13
passing taps. A nearby write-phase scan from 17 through 33 found no error-free
setting and restored phase 25. All eight lane-6 read bitslips and all 32 delay
taps also failed under traffic. Original lane-6 read framing was restored.
A write-framing scan is now testing the other even write bitslips. These
results do not establish a damaged memory chip or synthesis fault. No compute
or model stage has run; no global-reset CSR or BPI flash write was used.

Evidence: `../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/`,
including `selftest.log`, `ddr-traffic-result.json`, `ddr-phase-result.json`,
and `ddr-lane6-framing-result.json`. The first traffic review correctly records
failure; its shell pipeline returned tee's status, so JSON and traceback, not
pipeline exit alone, define its outcome. Later experiment commands enable
pipefail.

## 2026-10-10 22:20 HKT — reload and stronger calibration review

The lane-6 write-framing review tested the other even write bitslips against
all eight read bitslips and 32 delay taps, with no passing lane-6 setting.
Original framing was restored. The XVC server was stopped cleanly before
loading the supplied MicroBlaze/vendor-MIG image into SRAM for diagnosis.

Two real debugger issues were reproduced and corrected in
`../ypcb_00338_1p1_hack/scripts/fedora_cpu_run.tcl`: the old processor name
filter also selected the MDM, and the installed XSDB UART command needed the
MDM parent context explicitly. The runner now also handles a processor
already stopped by an earlier failed attempt. Its host fixture models the
real MDM/CPU entries and UART ownership; all 29 host-flow checks pass. The
first target-selection regressions failed before the correction.

The recovered physical MIG diagnostic opened the UART, but received no CPU
text and timed out. A subsequent stopped-CPU snapshot read PC `0x000000b8`,
in C runtime startup before main; BRAM reset-vector words match the loaded
ELF. No DDR result exists from this diagnostic, and no PCIe/reset/board cause
is established. Evidence is in
`../ypcb_00338_1p1_hack/build/fedora-microblaze/hardware-20261010T135515978852Z/`,
including `recovered-ddr_diag-20261010T140013Z/result.json` and
`stalled-cpu-probe.log`. The owned hardware servers were stopped.

The selected OpenTPU image was reloaded into SRAM successfully and the
USER2 server restarted under PTY session 40630. The fresh calibration picked
channel-0 CK -40 with a nine-step window, but full 2 GiB zero/random BISTs
again failed only on lane 6. Channel 1 again passed both patterns across
its complete 2 GiB. The fresh report is
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/reload2/result.json`.

A separate calibration experiment copied the original firmware sources and
built RV32I variants for DQS static phases 4, 3 and 5 eighths of the VCO.
It validates the actual DQS phase against its compiled expected value and
increases scan BIST coverage from 64 to 256 MiB. Each 10,232-byte image fits
the original 16 KiB CPU memory; upload verifies the whole memory by readback.
Only channel 0 is recalibrated; channel 1's configuration remains in place.
The original native bitstream, 31 source pairs, generated DDR profile and
original firmware files have not been changed. These are runtime experiments
on the Vivado image, using the existing RISC-V compiler; no OpenXC7 synthesis
or routing is running. Reloading SRAM restores the original firmware/clocks.

The stronger scan found no common passing phase at DQS settings 4, 3 or 5.
The experiment finished at 22:21 HKT with `NO_QUALIFIED_SETTING_FOUND`.
At the original DQS phase, lane 6 has no passing scan point; the two altered
phases yielded no passing lane. These outcomes do not qualify a PHY setting.
Results, copied
source/diff, firmware hashes, compiler commands and guarded host CSR writes
are saved in
`../openTPU/build/fedora-openxc7/physical-ddr-dqs-tune-20261010T1410Z/`.
The global-reset CSR at `0x12000` is forbidden by the experiment's host
transport guard. No BPI flash write or physical compute/model pass is claimed.

## 2026-10-10 22:33 HKT — clock and vendor startup diagnostics

Both OpenTPU channel pin inventories match all 117 pins of their respective
vendor MIG project files, with no missing or mismatched assignments. The
comparison is saved as `pin-map-review.json` in the physical JTAG evidence
directory. This does not establish signal integrity or board health.

A native Vivado clock-only diagnostic is building from the unchanged selected
routed DCP under `clock-diagnostic-20261010T1435Z/`. It changes the system
MMCM output divider from 14 to 18 and each channel's input-period hint, giving
an actual 77.7778 MHz core and 622.222 MT/s DDR rate. The delay-controller
reference remains 200 MHz. Firmware, refresh counters and identification
registers retain their DDR800 values, so this is explicitly a short diagnostic,
not a qualified operating profile or a replacement selected manifest.
Its build is exec 57814; native reports and a separate bitstream are required
before physical use. No source or original bitstream is overwritten.

XVC session 40630 was stopped before another controlled vendor-MIG SRAM load.
The independent CPU startup probe is exec 9665, with evidence in
`../ypcb_00338_1p1_hack/build/fedora-microblaze/cpu-startup-probe-20261010T1433Z/`.
It samples run/step behavior and the GPIO register rather than assuming the
UART timeout proves a memory failure. The cable must have only one owner.
No compute or model result exists yet.

## 2026-10-10 22:59 HKT — physical vector and matrix results

The clock-only diagnostic passed offline route, timing and DRC, but reproduced
channel-0 lane-6 errors on both full 2 GiB patterns. Channel 1 passed again.
This experimental clock image retains the DDR800 refresh/identification values
and is not a qualified operating profile. It did not replace the selected
native manifest. Evidence is `clock-diagnostic-20261010T1435Z/` under the
physical JTAG directory.

The vendor CPU probe advanced and then regressed its BSS-clear pointer; GPIO
responded, but there was no UART or DDR test result. A read-only boundary scan
using Vivado's exact BSDL and SAMPLE instruction found R28 reset high in all
400 samples, while SYS_CLK showed both levels. This does not exclude short
reset glitches or establish the startup cause. Vendor evidence is in
`../ypcb_00338_1p1_hack/build/fedora-microblaze/cpu-startup-probe-20261010T1433Z/`.

An original-image restore was interrupted when XVC initialization started
before the upload completed. That attempt (`opentpu-reload-3.log`) failed with
exit 134; no flash was written. The cable initializer and XVC launcher now
reject an existing `openFPGALoader` process before USB firmware access. Both
guards passed a named-process contention check (`cable-owner-guard-test.json`).
The next restore (`opentpu-reload-4.log`) completed exit 0 with INIT/DONE set.
The original DDR800/100 MHz image and firmware were restored.

A 64 MiB-bin random-traffic scan failed lane 6 in every channel-0 region.
Normal JTAG readbacks of 1 KiB matched five sampled lower addresses, but near
the channel's top returned 13 wrong bytes. This confirms corruption through
the actual host path, not only the BIST checker. `address-result.json` records
the failure. The original whole-memory selftest remains failed and DRAM_INIT
has not been set.

The small workload in `bounded-compute.py` initializes and reads back every
DDR buffer it uses. It then runs real accelerator instructions and compares
returned data and instruction counts against the ISA simulator. It does not
override the failed memory scrub or assert model readiness. Fourteen physical
runs passed bit for bit:

- Five vector runs: 32 results of `3 * 4 = 12`, four instructions, 60 cycles.
- Three MXU runs: ones matrices 4x128 times 128x4, all 16 outputs equal 128,
  five instructions, 280 cycles.
- Six randomized quantized MXU runs: two deterministic sets of signed inputs,
  int8 weights and scales, three repeats each, five instructions, 305 cycles.

All results returned over JTAG; PCIe was not used. Receipt:
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/bounded-compute-result.json`.
The initial eight-case receipt is separately preserved. CDC and synthesis
findings remain open; these tests do not qualify every VPU operation.

An isolated firmware experiment forced lane 6's odd write bitslips (1,3,5,7),
kept the other lanes on even settings, and used a 256 MiB traffic scan. Its
10,264-byte firmware fits the original memory and was fully verified on upload.
It completed `NO_QUALIFIED_SETTING_FOUND`. Original source/profile files remain
unchanged. Evidence is
`../openTPU/build/fedora-openxc7/physical-ddr-odd-lane6-20261010T1458Z/`.

XVC session 84634 was stopped before another original-image restore. Restore
exec 88619 completed exit 0 with INIT/DONE set (`opentpu-reload-5.log`). The
original native DDR800/100 MHz image and firmware are restored. XVC session
50709 then ran the same fourteen compute cases: all passed again, with all
32 buffer initialization/readback checks returning zero wrong bytes. The run
finished at 23:04:29 HKT, exec 96040 exit 0. Its log is
`bounded-compute-reload5.log`; the latest JSON receipt is
`bounded-compute-result.json`, and the preceding fourteen-case receipt is
preserved as `bounded-compute-before-reload5-result.json`.

XVC session 50709 was stopped cleanly (exit 0). At 23:05 HKT the cable-owner
check found no openFPGALoader, hw_server, xsdb or fxload processes, and XVC
port 3721 was closed. `power-cycle-readiness.json` records this. The user has
been asked to turn card power off for ten seconds and back on, leaving the
JTAG USB cable attached, and report the power source/current limit. Wait for
the user's reply before another hardware operation. A power cycle will discard
the SRAM image; reload the selected native Vivado image, wait for programming
to terminate successfully, then start XVC and retest DDR integrity. SRAM
reloads alone do not cycle DDR power rails. Full-memory and README model
qualification remain incomplete; no power fault, chip damage or PHY root cause
is established. No BPI flash was written.

## Offline DDR follow-up, 2026-10-10 23:25 HKT

The previous goal turn made progress: the original Vivado image was restored,
the fourteen physical compute cases passed again, and cable ownership was
released. The physical power-cycle/power-source question remains unanswered.
No hardware operation has been performed since that request; the card's
present power state is unconfirmed.

A read-only Vivado audit opened the selected, SHA-verified `final-routed.dcp`
and exported the I/O chains for all 144 DQ pins and 18 positive DQS pins. Exec
92434 completed exit 0 at 23:24:46 HKT. The validator covered 162 ports and
648 component rows. Channel 0 lane 6 uses the same read/write clock sources,
serializer settings, 200 MHz VARIABLE input-delay reference, FAST slew and
UNTUNED_SPLIT_40 termination as the other channel-0 lanes. No lane-specific
mismatch was found in those properties. The clock report and Vivado datasheet
are preserved; absent external DDR delay constraints still prevent physical
timing signoff. This audit does not measure board voltages, skew or jitter,
exclude reset/framing faults, or establish a PHY root cause.

Evidence:
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/offline-phy-audit-20261010T1508Z/result.json`.
The selected bitstream and original source/profile files were not changed.
Vivado is no longer running.

An offline per-bit review of the saved physical scans found that every lane-6
DQ bit had errors at every recorded framing/tap setting: 256 read-framing
samples and 768 write/read-framing samples. There is no hidden zero-error
per-bit point in those tables. This covers only the CK/write-clock settings
used by those scans. `lane6-perbit-review.json` preserves the source hashes
and per-bit results. The upstream `docs/litedram.md` also records failed
write-clock group-offset experiments; that abandoned technique was not
repeated. The next physical action remains the confirmed cold power cycle,
native SRAM reload and full DDR integrity retest described above.

## Waiting for physical power-cycle confirmation

The goal's blocked audit has now reached three consecutive turns with the
same pending physical action. The preceding turn completed the offline PHY
and per-bit audits; this turn verified that their receipts are terminal, all
Vivado/cable clients are stopped and XVC port 3721 is closed. No further
hardware test can proceed until the user confirms the requested card power
cycle. FPGA/card power state cannot be inferred from the cable's USB presence.
The full goal is not achieved: bounded computation passes, channel-0 memory
integrity fails, and README model inference is NOT_RUN.

Receipt:
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/goal-blocked-audit.json`.
Resume after the user confirms the card is back on and identifies the power
source. Reload the selected native Vivado SRAM image using the command above,
wait for terminal programming success before starting XVC, then retest DDR.
Do not reuse the experimental firmware or change the selected manifest.

## Resumed: DLC10 USB replug and physical retest, 2026-10-10 23:45 HKT

The user resumed the goal and clarified that only USB to the DLC10 was
replugged. This supersedes the preceding blocked handoff for cable access;
it does not confirm a card/DDR power cycle. A fresh staged initialization
identified exactly one XC7K480T (`0x23751093`, IR length 6). Original native
Vivado SRAM programming completed exit 0 at 23:34 HKT, with INIT/DONE set and
the same selected bitstream SHA256. No BPI flash was written.

The first USER2 read encountered LIBUSB_ERROR_OVERFLOW before any DDR command.
The server was stopped. A warm retry was rejected on an invalid IDCODE, and
no programming was attempted with that chain. A software USB reset returned
ENODEV on the previous device node; the cable re-enumerated from 001/016 to
001/017. Fresh initialization passed. The new USB descriptor reports 480 Mbit/s
and 512-byte bulk packets; the preceding saved descriptor had 64-byte bulk
packets. This observation does not establish the overflow's cause. No XVC
binary or USB source changes were needed to complete the subsequent tests.

Exec 33624 then completed the full 2 GiB test region on both channels, with
33,554,432 beats for every write and read phase:

| Read pattern | Channel 0 bad beats | Channel 1 bad beats |
| --- | ---: | ---: |
| Zero | 828,385 | 0 |
| Random | 11,134,271 | 0 |
| Address | 4,765,597 | 0 |

Every channel-0 error was confined to byte lane 6 (mask
`0x00ff000000000000`); the other eight lanes had zero errors. Both channels
reported calibration ready, which does not qualify the failing channel's
integrity. The test command exited 0 because all phases completed, while its
JSON correctly reports `PHYSICAL_DDR_INTEGRITY_FAILED_AFTER_USB_REPLUG`.

Exec 51487 completed exit 0: all fourteen bounded vector and matrix compute
cases and all 32 buffer initialization/readback checks passed again. All
outputs and retired instruction counts matched the ISA reference bit for bit
over JTAG. Full memory integrity still fails, and README model inference is
NOT_RUN. No global-reset CSR, calibration override or DRAM_INIT marker was
written by these tests.

XVC exec 42317 stopped with exit 0. The subsequent live owner check found no
openFPGALoader, hw_server, xsdb or fxload processes, and port 3721 was closed.
Evidence and validated hashes are in
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/replug-retest-20261010T153130Z/`:
`manifest.json`, `memory-result.json`, `bounded-compute-result.json`,
`usb-reset-result.json` and `power-cycle-readiness.json`, with their logs.
The current pointer is `../openTPU/build/fedora-vivado/replug-retest-current.json`.
Earlier failed transport attempts are preserved separately and contain no
DDR results.

The goal remains active and incomplete; this resumed turn made new hardware
progress and starts a fresh blocked audit. The user has been asked to turn
the card's power off for ten seconds and back on, leaving DLC10 USB attached,
and identify the power source (including voltage/current limit for a bench
supply). Wait for that reply before another hardware operation. Then reload
the original selected native SRAM image, wait for terminal programming
success, start XVC and repeat full DDR integrity tests. Proceed to normal
accelerator/model qualification only if memory passes. USB-only replugging
and SRAM reloads have not tested a DDR cold start; no physical root cause is
established.

## Offline model reference prepared, 2026-10-10 23:51 HKT

The preceding goal turn made hardware progress by recovering USB, reloading
the native image, retesting both full DDR channels and repeating all fourteen
bounded compute cases. This continuation verified that those jobs are
terminal and that no cable/Vivado owners or XVC listener remain. Card power
cycle confirmation and power-source details are still pending; no new
hardware operation was performed.

Exec 17023 completed exit 0: the ISA simulator ran the real LFM2.5-230M int8
model with the recorded native device configuration (D=128, MCOLS=4, LANES=8,
four activation rows), the standard model-check prompt, capacity 256 and
eight-token limit. It produced `The capital of France is Paris.` and token
IDs `[1098, 5706, 803, 4481, 856, 5242, 523, 7]`, including EOS. Eleven
programs ran; the largest had 2,247 instructions, within the native IMEM's
4,096-instruction capacity. The reference image, weights, tokenizer and
current source hashes are recorded in `lfm2-reference-result.json`, beside
the repeat-test receipts; `lfm2-reference.py` and its log reproduce the run.
The simulator memory is sized to the model, with the same image layout and
compute configuration used by the normal physical model comparison.

This is an offline golden reference, not FPGA inference. The physical model
stage remains NOT_RUN because channel-0 DDR integrity still fails. The next
action remains the pending card power cycle, native reload and complete DDR
retest, then the normal `selftest --model lfm2 --tokens 8 --wformat int8` shown
in `../openTPU/docs/fedora_bringup.md`. No memory gate was bypassed. The goal
remains active; `goal-resumed-audit.json` records two resumed turns with the
same pending physical action and this turn's concrete reference progress.

## Blocked after resumed audit, 2026-10-10 23:53 HKT

The third resumed goal turn verified the completed hardware/reference receipt
hashes, terminal test results and live process state. No Vivado, cable or
model-test jobs remain, and XVC port 3721 is closed. The preceding turn
completed the exact ISA model reference; this turn has no new hardware
progress. The same physical card power-cycle confirmation and power-source
details have remained pending across all three resumed turns. USB-only
replugging does not confirm that action.

The blocked audit threshold is met. Native SRAM loading and fourteen bounded
compute cases passed, but channel-0 DDR integrity failed and physical README
model inference is NOT_RUN. Independent reference and PHY follow-ups are
complete; the goal is not achieved. The goal is being marked blocked pending
the user's physical action. The fresh audit is
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/replug-retest-20261010T153130Z/goal-blocked-audit.json`.

Resume after the user confirms the card is back on following ten seconds
without card power and identifies its supply. Reload the selected native
Vivado SRAM image, wait for terminal programming success, retest both full
DDR channels, then proceed to the normal accelerator and LFM2 model stages
only if memory passes. Keep the selected bitstream and original firmware;
do not set DRAM_INIT to bypass failed integrity checks or write BPI flash.


## Confirmed cold-cycle retest and next MIG probe, 2026-10-11 00:32 HKT

The user confirmed `power cycled`; the selected native Vivado OpenTPU image
was successfully loaded into SRAM at 23:58:20 HKT on October 10. Both full
2 GiB DDR channels completed zero, random and address tests at 23:59:21 HKT.
Channel 1 passed all three with zero errors. Channel 0 had 2,404,326,
19,108,595 and 8,413,924 bad read beats respectively; every error remained
on byte lane 6. No bounded compute cases were run after this cold cycle.
The earlier fourteen-case hardware passes and exact offline LFM2 reference
remain partial evidence; physical README model inference is NOT_RUN.

The user reported bench-supply settings of 12 V and a 2 A current limit.
Actual voltage, drawn current and CV/CC indication remain unknown. This does
not establish insufficient power. The user requested moving to the next test
without further supply-display questions; keep those settings unchanged.

Fedora subsequently rebooted at 00:16:35 HKT on October 11 (boot ID
`4cddaae6-3696-4792-b702-a5c6b261cf6a`). Kernel USB descriptor/address errors (-71)
at 00:19:25–00:19:36 precede the vendor-MIG attempt. The first attempt had a
Vivado server URL formatting error, which was corrected. The second could
not find a hardware target: DLC10 is absent from USB. Neither attempt
programmed the vendor image or obtained XADC/vendor DDR results. The last
successful SRAM load was native OpenTPU, but the current FPGA image cannot
be verified after the reboot. No BPI flash was written; no restore was
needed after these attempts because vendor programming never started.

The owned hw_server/Vivado/CS processes were stopped. A current process
check found no cable clients, and XVC port 3721 is closed. The next probe is
prepared in `../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/cold-power-retest-20261010T155620Z/vendor-mig-probe/`:
read XADC, program the SHA-verified supplied MIG SRAM image, halt the
MicroBlaze, require its data-cache-enable bit clear, then check 1 KiB at the
bottom, midpoint and near the top of each DDR channel using zero, ones and
deterministic data, with three read repetitions (54 cases). ECC remains
enabled; status and corrected-error counters are captured before/after
initialization and each read. Only documented ECC status/counter clears are
written. Sparse results cannot qualify full-capacity or dense DDR traffic.
Offline Tcl mocks verified all 54 cases, DDR-only write ranges and capture
of injected data/ECC errors. These checks did not access hardware.

The goal is active and incomplete. This fresh resumed turn completed the
cold-cycle tests and prepared the independent probe; the new USB blocker
has not met the three-turn blocked threshold. The user has been asked to
unplug only DLC10 USB for five seconds and reconnect it, leaving card power
unchanged. After it enumerates: freshly initialize the cable, require one
expected FPGA (`0x23751093`, IR length 6), run `vendor-mig-probe/run.py`, wait
for terminal completion, release its clients, review data plus ECC and XADC,
and restore the selected native SRAM image if vendor programming was
attempted. Then retest native DDR; proceed to normal accelerator/model
qualification only when the memory gate passes. Do not bypass DRAM_INIT,
write the known-problem global reset CSR, or touch BPI flash.

Current cold-cycle receipts are `manifest.json`, `native-sram-load.log`,
`memory-result.json` and `memory-retest.log`; the vendor directory contains
`result.json`, `hardware.log`, `usb-enumeration-kernel.log`,
`probe-process-cleanup.json`, `next-test-readiness.json` and offline checks.
The pointer is `../openTPU/build/fedora-vivado/cold-power-retest-current.json`.


## USB blocker confirmed across three turns, 2026-10-11 00:35 HKT

The third consecutive turn confirmed DLC10 is absent from USB, no cable or
Vivado clients are live, and XVC port 3721 is closed. The prior continuation
was no progress, not a wait on a live job. The same missing-cable condition
has prevented the prepared vendor-MIG probe across three turns. Probe script
hashes still match the saved readiness receipt. Neither XADC nor vendor DDR
results exist, and vendor programming never started. The cold-cycle native
DDR0 lane-6 failure remains; channel 1 passed. Physical README model inference
is NOT_RUN. The requested goal is incomplete.

The blocked audit threshold is met; the goal is being marked blocked pending
physical DLC10 USB reconnection. Keep card power settings unchanged. After
replugging USB for five seconds, resume: verify enumeration, initialize the
expected single FPGA, run the prepared MIG/ECC probe, release its clients,
restore native SRAM if vendor programming was attempted, then pursue normal
memory, accelerator and model qualification. Audit:
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/cold-power-retest-20261010T155620Z/goal-blocked-audit.json`.


## User reconnect observed, USB enumeration failed, 2026-10-11 07:22 HKT

The user reported `connected, check again`. Fedora detected a fresh plug-in
on USB port 1-2 at 07:21:03 HKT. Enumeration tried high speed then full speed,
failed descriptor/address requests with error -71, attempted a port power
cycle, and terminated with `unable to enumerate USB device` at 07:21:09.
A twenty-second device check completed without either DLC10 USB ID. The
USB device node 1-2 is absent, so no cable firmware or JTAG operation can
start. No FPGA image was programmed or DDR/model test run in this recheck.
All cable/Vivado clients remain stopped; XVC port 3721 is closed. This USB
failure does not diagnose the card's DDR problem or prove inadequate power.

The user has been asked to move DLC10 USB to another direct Fedora USB port,
without a hub, leaving card power settings unchanged. Continue with the
prepared independent MIG/ECC comparison once one cable enumerates and the
expected FPGA chain is freshly verified. Fresh receipt and kernel log:
`../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/cold-power-retest-20261010T155620Z/usb-reconnect-check-20261010T232233Z/result.json` and `kernel-usb.log`.
Pointer: `../openTPU/build/fedora-vivado/usb-reconnect-current.json`.


## DLC10 recovered; independent MIG comparison completed, 2026-10-11 08:03 HKT

The user's latest reconnect succeeded. Staged DLC10 initialization freshly
identified exactly one XC7K480T (`0x23751093`, IR 6), with USB at 480 Mb/s after
device-only resets. The supplied Vivado MIG SRAM image passed all 54 sparse
uncached read checks across three offsets per channel, with zero wrong words
and zero read CE/UE events. ECC remained enabled. Initial write-phase ECC
events are retained in the receipt; this is not full-capacity/load qualification.
XADC measured VCCINT 0.991–0.992 V, VCCAUX 1.802–1.805 V and VCCBRAM
0.991–0.993 V; actual 12 V input/current and DDR supply remain unmeasured.

The selected native OpenTPU SRAM image was restored with INIT/DONE set. Fresh
full 2 GiB zero/random/address tests on channel 0 still failed lane 6, with
167,634 / 3,579,775 / 755,542 bad beats; channel 1 had zero errors. The
calibration CPU's 54 error-register reads matched the host. Its original
firmware was fully verified restored, CPU held, with PHY settings unchanged.
Hardware clients stopped. No flash, global-reset CSR or DRAM_INIT override
was written. Earlier fourteen bounded computation passes remain partial proof;
physical README model inference is NOT_RUN. Controller/timing is the leading
suspect from the comparison, not a proven exclusion of a power/card issue.

Receipts: `../openTPU/build/fedora-vivado/physical-jtag-20261010T133821Z/cold-power-retest-20261010T155620Z/vendor-mig-probe-20261010T233827Z/current-review.json`,
`data-review.json`, `native-retest/memory-result.json`, and
`calibration-csr-probe/result.json`. The user resumed the goal. An isolated
DDR3-1066 ECC MIG native-interface candidate is prepared in
`../openTPU/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/`;
Vivado IP generation completed after creating the missing IP output directory.
Integration, synthesis/route and full DDR/accelerator/model checks remain.
The selected manifest is unchanged.


## Isolated MIG OpenTPU integration, 2026-10-11 08:16 HKT

The new candidate is `build/fedora-vivado/mig-jtag-controller-20261010T235833Z/`
in openTPU. It retains the full compute dimensions and USER2 transport, with
Vivado MIG DDR3-1066 ECC, a single existing native port per channel, hardware
full-memory write/read BIST and ECC reporting. Five memory-bridge simulations,
1,325 asynchronous diagnostic transactions (including injected data/ECC faults
and read ownership) and six host failure-gate tests passed. These are offline
checks. Vivado IP generation completed; actual native synthesis is running,
unified exec 86906, synthesis PID 43204 started at 08:12:45 HKT; parent PID
42941. Configured eight cores; Vivado reports seven helpers plus the main.
Check exact PID/start and log progress before any restart. Candidate README
records the continuation and required implementation/pin/timing/CDC audit, full
DDR/ECC test and normal accelerator/model test. The selected manifest and
physical native FPGA image are unchanged. No physical model run or flash write.


## Current recheck and MIG build, 2026-10-11 08:26 HKT

A final fresh verbose JTAG scan exited 0 and the existing strict chain parser
passed: exactly one XC7K480T, IDCODE 0x23751093, IR 6. The non-verbose scan
also detected it, but omitted the count field expected by the parser; its
parser rejection is not a cable fault. The successful receipt is
`vendor-mig-probe-20261010T233827Z/latest-chain-verbose-result.json`. Hardware
clients stopped after detection; USB remains 03fd:0008 at 480 Mb/s.

The isolated MIG candidate's declaration order was corrected. Its first
synthesis was intentionally terminated with exit143; a brief second attempt
exited1 because Vivado requires explicit input net types under default_nettype
none. Both terminal logs/directories are preserved. Inputs now use input wire,
and the 1,325-transaction diagnostic passed again. All five memory-bridge
scenarios also passed after moving declarations. Corrected native synthesis
is progressing past RTL elaboration with no adapter declaration warnings.
Current unified exec session91458, parent Vivado PID46234 started08:21:58 HKT,
synthesis PID46367 started08:22:08 HKT. Sessions86906 and32121 and their PIDs
are historical/terminal. Follow candidate manifest, README, stage.txt and
synth_1/runme.log; the build uses eight available cores. The original selected
native-image restore checker passed again. No new FPGA image was loaded; full
physical model inference remains NOT_RUN. The resumed goal remains active.


## Fresh connection check and MIG implementation, 2026-10-11 08:42 HKT

A fresh JTAG scan passed: exactly one XC7K480T, IDCODE 0x23751093,
IR6 and the expected chain-end marker. USB cable enumeration is 03fd:0008.
Receipt: `../openTPU/build/fedora-vivado/connection-recheck-20261011T003146Z/result.json`.
No image was loaded in this recheck. The physical original DDR800 image remains;
its full channel-0 memory failure is unresolved and physical model inference is
NOT_RUN. The sparse supplied-MIG pass remains separate from full-capacity proof.

The isolated MIG candidate synthesis session91458 exited0 at08:38:15 HKT.
It retained all716 compute DSPs. Checkpoint reopening exposed a late constraint
lookup error because synthesis merged the JTAG host clock with the identical
core clock. The isolated constraint now resolves the host FIFO register clock
and requires it to equal the core clock; both channels loaded with no errors
or critical warnings. No RTL resynthesis was necessary. The initial error log
and old constraint remain preserved. All247 package pins and I/O standards,
configuration properties, USER2, both complete PHYs and all expected core/UI/
input/JTAG clock periods passed the synthesized-checkpoint audit. The MIG
reference reset standards are LVCMOS15; both expected reset rows were corrected.
Twenty-four unchanged upstream snapshots and the exact single-port bridge patch
were reviewed;94 generated MIG inputs were frozen for the independent checker.

Implementation is running with eight available cores: unified exec72196,
parentVivadoPID48404 started08:39:05 HKT, startticks3015012; implementation
PID48637 startedSun Oct 11 08:40:35 2026. Candidate:
`../openTPU/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/`.
Follow its manifest, README, stage.txt, implementation-console.log and
impl_1/runme.log. Do not start a duplicate job or restart based on log silence.
After terminal exit0, run the new dedicated check_candidate.py and review all
remaining CDC paths. SRAM programming, both full2GiB/channel pattern/ECC tests,
normal accelerator tests and exact README model-token comparison remain.
The selected manifest and original checker are unchanged. No flash, global
reset CSR or DRAM_INIT override was written. The goal remains active.


## MIG routing and exact model receipt, 2026-10-11 09:08 HKT

Previous goal turn made progress: corrected shared-clock lookup and launched
implementation. The same live job72196 / parent48404 / child48637 advanced
through placement and physical optimization, and is now routing with a maximum
of8 CPUs. Initial routing completed; overlap refinement is progressing.
Intermediate WNS+0.548ns is not final timing; hold repair remains in progress.
Do not duplicate or restart this confirmed live job. No new FPGA image was
loaded; full memory/model qualification remains NOT_RUN for the new candidate.

A separate read-only synthesized CDC audit exited0 (session87736). Its first
attempt17605 exited1 because standalone synthesis-DCP use needs early clock
constraints reimported; only that audit setup was fixed, and both attempt logs
are preserved. The current audit imported the same board/MIG/JTAG clocks and
all late constraints successfully. Its detailed parser accounted for3366
endpoints. All3312 non-Info endpoints were source-reviewed in six groups: held
CSR requests1628, held CSR responses68, return-FIFO heads into AXI skid buffers512,
held JTAG requests572, responses531 and the vendor temperature-word filter1.
The temperature RTL uses five ASYNC_REG stages and a saturating stability
counter; multi-bit synchronization alone was not accepted as atomic. Source
witnesses and endpoint keys are in preflight-cdc-source-review.json. Final
routed CDC endpoint coverage and all final timing/route checks remain required;
this pre-route receipt is not a programming pass. The original DDR800 checker
stays unchanged. The dedicated candidate checker now parses detailed reports
and requires every critical/warning endpoint key covered by the final review.

The normal model check now prints actual/ISA token arrays and optionally records
them through the physical transport. mig_host.py saves those arrays and refuses
a successful model stage without one nonempty exact comparison. It logs successful
64-byte memory-transfer progress every10s. The six host failure-gate tests still
pass. All8 model files and6 numerical source files match the saved ISA reference:
expected tokens[1098,5706,803,4481,856,5242,523,7], text
“The capital of France is Paris.” Runtime source witnesses were saved.

The SRAM-only program_candidate.py is prepared. After implementation exits0
and final route/timing/CDC audits pass, use a new programming receipt directory;
it audits before USB access, runs the strict existing DLC10 initializer/chain
parser, rechecks the same bitstream and manifest, then requires INIT/DONE after
SRAM loading. Start the existing verified localhost XVC server only after that
process exits. Run both full2GiB/channel pattern/ECC tests, followed by the normal
selftest with --model lfm2 --tokens8 --wformat int8 and verify captured exact tokens.
No flash, global-reset CSR, failed-memory bypass, selected-image change or new
physical computation occurred in this turn. Goal remains active.


## Final MIG image qualified; USB reconnect needed, 2026-10-11 09:22 HKT

Native implementation session72196 completed with actualexit0 at09:13HKT.
All final reports/checkpoint are complete. Independent audit PASS: all290292
routable nets fullyrouted, zeroerrors, WNS+0.235ns/WHS+0.026ns/WPWS+0.264ns,
all30bus-skew bounds met. All247pins/standards, 716DSPs, both complete MIG PHYs
and expected clocks/configuration pass. Newbit12,870,600bytes SHA256
0863b3e2a7f45b1c75e8229e4d18247baaa73b3bc8746240f14d6199424d4e4f.
Candidate ../openTPU/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/.
Final CDC reviewed all3312 non-Info endpoints. All1945 changed representative
fan-in rows were checked against actual final paths/protocols/clock domains;
no unmatched endpoint remained. Extra read-only audit93810 exited0; all755
methodology and725DRC entries reviewed. Replica audit9428 exited0: all32 copied
FIFO address registers have no first-stage Gray synchronizer fanout. No new
placement/routing job is running; do not rebuild the qualified image.

Fresh JTAG scan at09:11HKT exited0: one0x23751093/IR6, expected chain-end.
Kernel logged DLC10 disconnect at09:13HKT followed by USB descriptor error-71;
current lsusb has no03fd cable and sysfs1-2 is absent. Actual programmer attempt
physical-jtag-20261011T011921Z exited1 at cable initialization ('No DLC10 found'),
before SRAM programming. No new FPGA image/flash write occurred. The user was
asked to reconnect the cable USB end, with FPGA power settings unchanged.
This is a missing USB adapter at this point, not evidence of a card/power fault.

Once oneDLC10 returns, use candidate program_candidate.py --out NEWDIR (newpath),
then existing verified tools/fedora_xvc_server.py. Check both MIG calibration
flags; run full memtest, then normal selftest --model lfm2 --tokens8 --wformatint8.
The normal model check captures exact actual/ISA tokens and refuses a missing
comparison. Receipts also include full BIST scrub results;6host gates still pass.
Full physical memory/model qualification is NOT_RUN for this candidate. Original
selected DDR800 manifest/bit/checker remain available unchanged for SRAM rollback.
Goal stays active; no failed-memory bypass, DRAM_INIT override or globalresetCSR.

The additional 60-second USB observation also found no DLC10. A software port-reset attempt could not execute because sudo requires a password; no port state was written. The port remains enabled (disable=0). No background hardware client remains. See the failed programming directory usb-disconnect-result.json for current USB/kernel evidence. Resume after physical USB replug.


## USB connection still unavailable, 2026-10-11 09:27 HKT

The previous goal turn made concrete progress by completing native implementation and the final offline audits. This continuation found the same external USB blocker. Fedora logged a fresh connection attempt at 09:24 HKT, but it again ended with descriptor error -71 and no enumerated DLC10. A further 45-second observation also found no adapter; receipt: ../openTPU/build/fedora-vivado/usb-enumeration-recheck-20261011T012617Z/result.json. The complete image audit passed again with the same bitstream SHA256. No image was loaded and no physical model computation ran. The user was asked to connect the USB end directly to a different Fedora port. This is the second consecutive goal turn with the same blocker; the goal remains active. No live build or hardware client is pending.


## Goal blocked on DLC10 USB, 2026-10-11 09:28 HKT

The previous goal continuation made no hardware progress because the DLC10 did not enumerate. A fresh third consecutive check again found no Xilinx USB adapter and no live build or hardware client. The qualified bitstream still has SHA256 0863b3e2a7f45b1c75e8229e4d18247baaa73b3bc8746240f14d6199424d4e4f. The goal was set to blocked after the required three-turn audit. No SRAM programming, full physical DDR qualification or README model comparison has run for this candidate. Resume after the cable USB connection is restored; use a new programmer receipt directory, then XVC, full memory tests and the complete normal model selftest. Do not rebuild the qualified image or bypass the failed-memory gates.


## User resumed; intermittent USB connection, 2026-10-11 12:59 HKT

User reconnected and explicitly set the goal active. The full image audit passed again with the same qualified MIG bitstream. Device030 did enumerate as03fd:0013 at12:51:08HKT, but disconnected at12:51:31. The actual SRAM-programmer attempt at12:51:46 therefore exited1 before programming because no DLC10 was present. Its receipt is physical-jtag-20261011T045146Z/result.json. Kernel then recorded a further descriptor error-71. An automatic loader watched for120seconds and would have started the strict programmer as soon as one adapter stabilized; session42839 is now terminal, actualexit1, zero programming attempts. Receipt auto-program-20261011T045413Z/state.json. No image or flash was written, no new memory/model test ran, and no client remains. The user was asked to reconnect once and leave USB connected. This resumed run starts a fresh blocker audit at1; the old three-turn blocked record is retained as history. Goal remains active.


## Automatic USB loader still waiting, 2026-10-11T13:05:33.598747+08:00

A single bounded 900-second watch is live: session 71592, PID 80732, started at 13:02:07 HKT and due to stop observing at 13:17:07 HKT. Receipt: ../openTPU/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/auto-program-20261011T050206Z/state.json; fresh USB/PID evidence is live-recheck.json in the same directory. The fresh scan has no Xilinx USB device; the watcher state is WAITING_FOR_DLC10 with 0 attempts. The quoted Device 030 was recorded by the kernel at 12:51:08 HKT and disconnected at 12:51:31 HKT. Programming has not started. Preserve this watcher; do not start a duplicate initializer or mutate the candidate manifest during a programming attempt. Once SRAM programming returns actual exit 0 and INIT/DONE, start XVC, check both MIG calibration flags, run full DDR/ECC tests, then the normal LFM2 selftest and exact ISA token comparison. The goal remains active pending a stable USB connection.


## Resumed goal blocked on USB, 2026-10-11T13:08:50.399636+08:00

Three consecutive resumed goal turns confirmed the same missing DLC10 USB connection. The previous turn was a verified wait on session 71592; the fresh third check again found no Xilinx adapter. update_goal returned status blocked. Evidence: ../openTPU/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/auto-program-20261011T050206Z/goal-turn-3-usb-audit.json. The qualified bitstream SHA256 is unchanged. SRAM programming, full DDR/ECC tests and physical LFM2 token comparison have not started as of this check.

The existing bounded watcher (session 71592, PID 80732) is preserved. It observes until 13:17:07 HKT and can still start the already-authorized guarded SRAM loader if exactly one adapter returns. Do not mistake this blocked goal status for a terminal watcher. On user resume, poll the same session and inspect its actual state, attempt result and command exit before launching any initializer. If it already loaded SRAM with exit 0 and INIT/DONE, continue directly with XVC, both calibration checks, complete DDR/ECC patterns and normal LFM2 selftest with exact ISA token comparison. Otherwise wait for stable USB and choose a new receipt directory only after the existing job is terminal. The candidate manifest was left unchanged to preserve the initializer hash guard.


## Vivado MIG image programmed; full DDR passes, 2026-10-11T14:04:11.030364+08:00

Device 033 was present as 03fd:0013. The old 900-second watcher was confirmed terminal (actual exit 1, zero attempts) before any new initializer started. The new guarded SRAM programmer completed actual exit 0 at 13:57:45 HKT, expected IDCODE 0x23751093 and INIT=1/DONE=1. New physical receipts: ${OTPU_ROOT}/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/physical-jtag-20261011T055654Z. Flash was not written; the selected old DDR800 pointer is retained only for rollback.

The first XVC invocation exited on stdin EOF; it was confirmed terminal before a persistent PTY invocation started. Live XVC session 93293/PID 92002 listens on 127.0.0.1:3721. Physical SMI exited 0: OpenTPU ID, D=128/MCOLS=4/LANES=8, 100 MHz, DDR3-1066, build 5b1e646c, both calibration flags true. The complete memtest exited 0: all 16 write/read passes (ones, address, xorshift, zero) cover all 33554432 64-byte beats on each 2 GiB channel, zero bad/corrected/uncorrectable beats, status 6 throughout. This is full 4 GiB physical memory evidence.

The complete normal selftest --model lfm2 --tokens 8 --wformat int8 is running: session 77894/PID 92284, console physical-selftest.console.log in the receipt directory. Link/config/calibration/scrub/register/address stages have passed. Pure JTAG writes measure about 15 kB/s; the 242628608-byte model weights alone are expected to take roughly 4.5 hours at that observed rate, after the remaining normal checks. Preserve this live command and XVC; do not start a second cable client or reset/reprogram the FPGA. Final hardware compute/model token comparison is still unproven. On resume poll the same handles and inspect actual terminal exit, full_memory_scrub, ECC and model_checks before declaring success. Latest process/stage evidence is candidate physical-status.json.


## Physical kernels passed; USB interrupted full selftest, 2026-10-11T14:52:52.621788+08:00

The normal selftest passed host address/region/pattern checks, 200 partial writes per channel, and both compute kernel programs. The all-units program completed 9124 cycles and the masked-write program 10865 cycles; both matched complete ISA reference output and retired instruction counts. The compiler/ISA LFM2 reference is saved, but physical LFM2 inference has not run.

At 14:48:03 HKT the kernel recorded Device 035 disconnecting, followed by USB descriptor timeouts (-110). XVC reported LIBUSB_ERROR_IO; the selftest stopped during vops with EOFError: XVC disconnected. Session 77894 is terminal, actual exit 1; final receipt has model_checks=[] and retains all four successful full 4 GiB scrub results. Stream/model stages were not reached. The failed XVC server was shut down normally via terminal input, session 93293 actual exit 0. Both processes are absent; no hardware client remains. Restore stable USB before any new initializer or full test. Earlier full 4 GiB pattern/ECC and kernel passes remain historical physical evidence, not a completed full-model result.

Documentation: ${OTPU_ROOT}/docs/fedora_vivado_jtag_results.md. Fresh failure/process evidence and hashed terminal receipts are in ${OTPU_ROOT}/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/physical-jtag-20261011T055654Z/usb-failure-snapshot.json and hardware-run-review.json. No flash write, global reset or DRAM_INIT override occurred.

## Vivado reference trials and DLC10 software investigation, 2026-10-12 HKT

User resumed the larger objective: finish pending physical Vivado OpenTPU tests,
then synthesize and route with OpenXC7 using that image as the reference. The
qualified full MIG bitstream remains unchanged, SHA256
0863b3e2a7f45b1c75e8229e4d18247baaa73b3bc8746240f14d6199424d4e4f.

Read-only Vivado export and complete Yosys netlist import succeeded, retaining
all716 DSPs and the full generated MIG PHY. Latest backend receipt:
../openTPU/build/fedora-openxc7/vivado-mig-reference-20261011T163720Z/.
Actual pack exit125 on a tristate-only OSERDESE2. Actual chipdb audit and six
one-cell placement trials also find zero usable PHASER_IN_PHY, PHASER_OUT_PHY,
PHASER_REF, PHY_CONTROL, IN_FIFO and OUT_FIFO BELs; every probe exited125.
Fixing the OSERDES packer alone cannot enable routing of this MIG image.
Independent frozen-RTL+real-MIG frontend elaboration ran, then strict
undriven-signal checks failed. No independent mapped output, full OpenXC7 route
or board bitstream was produced. The earlier LiteDRAM DDR800 checkpoints use
a different PHY and remain distinct from this working DDR1066 reference.

The hardware watcher in
../openTPU/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/physical-resume-20261011T163700Z/
expired at00:42:05HKT with actual exit2 and
WAIT_USB_EXPIRED_NO_HARDWARE_ACCESSED. No new FPGA load or physical model run.
All export/import/synthesis/probe/watcher processes are terminal.

The latest unexpected USB disconnect occurred at00:20:47HKT before JTAG
software was started, followed by descriptor/setup error-71. Online primary
DLC10 reports identify a separate invalid alternate-setting request in the
loader. An isolated descriptor-aware candidate was compiled with8workers and
passed the existing XPCU protocol test plus actual-FX2-driver libusb-response
tests. Manifest: ../openTPU/build/fedora-openxc7/xpcu-xvc-20261011T165026Z/manifest.json.
Binary SHA256: b87703a39c2fa068aacd15d22f15d6d83a868f47c84ba1523d713022b2d57def.
Physical stability remains unverified; the original XVC pointer/donor/firmware
are preserved. A scoped no-autosuspend udev rule passed verification but was
not installed because unattended sudo requires a password. No board/12V power
fault or specific kernel regression is established. No hardware client remains.

Current handoff: ../openTPU/progress.md. Detailed evidence/commands:
../openTPU/docs/dlc10_usb_stability.md and
../openTPU/docs/openxc7_vivado_reference.md. The user goal remains active and
unfinished; resume stable USB plus full normal model comparison, and address
the actual memory-PHY backend gaps before expecting a full OpenXC7 route.

## User approved LiteDRAM OpenXC7 route, 2026-10-12 01:10 HKT

After the controller choices were explained, the user approved continuing the
full LiteDRAM OpenXC7 implementation with the working Vivado MIG image as the
functional reference. The complete independent DDR800 synthesis and all31
recorded source inputs remain unchanged. All25 shared reference RTL files
match except otpu_mem_ch.sv, whose native-port wrapper differs for MIG.
The memory profiles are explicitly different, so this is not an equivalence
proof or a physical LiteDRAM acceptance result.

The latest merged corrected backend975e6dbd... was revalidated against all5
actual correction/probe/frame gates and1563 pinned inputs. The frozen Vivado
offline image audit also exited0. Full placement/routing started with8threads
at01:04:45HKT under the durable controller
../openTPU/tools/fedora_resume_openxc7_reference.py. Directory:
../openTPU/build/fedora-openxc7/litedram-vivado-reference-20261011T170600Z/.
Controller138687, route wrapper138736, exact nextpnr138789 are live.
All8CPUs are allowed; a bounded observation confirms advancing CPU time.
Four initial placement iterations completed and main placement is active.
Preserve this job; do not restart it from an unchanged log. The controller
invokes the existing guarded strict-frame/bitstream/independent image checks
only after successful full routing. No full route/bitstream result exists yet.

The independent frozen-MIG elaboration audit now passes the strict check after
full flatten/optimization, without explicit undriven-signal tie-offs. It
retains79241 coarse cells and all required MIG resource types. An intermediate
empty-top blackbox result was explicitly invalidated; its exit0 is not counted
as a pass. Actual graph/log hashes and the final check exit0 are recorded in
../openTPU/build/fedora-openxc7/mig-elaboration-audit-20261011T165813Z/strict-elaboration-result.json.
Mapped MIG synthesis and its backend PHY support remain unimplemented.

Fedora still has no enumerated DLC10. No hardware client is running; full
physical Vivado vector/stream/model completion remains pending. The tested
corrected driver and scoped autosuspend experiment are ready, but the latter
still needs root installation. The preceding turn made concrete software
progress; this turn made concrete route progress and is a verified live-job
wait. The goal remains active and unfinished.

## Verified live route and bounded hardware watch, 2026-10-12 01:21 HKT

The preceding goal turn made concrete progress by launching the verified full
LiteDRAM implementation and completing the strict optimized MIG elaboration
audit. This continuation confirmed the same exact live route process and
captured actual strict-legalizer counters twice. Between01:14:17and01:16:39HKT,
2851additional calls and2851fewer queued entries demonstrate forward progress.
Both read-only observers detached and the original process resumed. Counts
include repeated/rip-up placements and do not establish percent complete/ETA.
No backend/source change, route restart or result substitution occurred.

A new bounded physical watcher was started using the separately tested XVC
candidate after confirming the old watcher and all cable owners were terminal.
PID139871, tool session57211, receipts under
../openTPU/build/fedora-vivado/mig-jtag-controller-20261010T235833Z/physical-usb-fixed-watch-20261011T171809Z/.
Actual start01:18:09HKT; USB wait1800seconds. The process is live and records
WAITING_FOR_USBwith no adapter or hardware access. It will invoke the existing
guarded SRAM load and full normal model selftest only after one cable appears.
Do not start another watcher or cable client. Unattended sudo still requires a
password; no host autosuspend rule was installed by the agent.

Full route controller session31485 and exact nextpnr138789 remain live. The
full job has no terminal route exit, FASM or bitstream acceptance result. The
current turn is a verified live-job wait with evidence of forward progress;
the goal remains active because the full route and physical model work are
unfinished. Current handoff remains ../openTPU/progress.md.

## Hardware watch terminal; full route live, 2026-10-12 01:48 HKT

The corrected-driver USB watcher reached actual exit 2 at 01:48:09 HKT,
WAIT_USB_EXPIRED_NO_HARDWARE_ACCESSED. PID 139871 is absent and tool session
57211 is terminal. No programmer, XVC session or physical selftest started.
Its process-exit.json receipt is under the physical-usb-fixed-watch directory
above. No replacement watch was launched without a new USB observation.

Full OpenXC7 controller session 31485 remains live, with exact nextpnr PID
138789 and start ticks 8930713. The 01:45:16 read-only snapshot captured
1,542,270 legalizer calls and 184,173 queued entries, down another 8,289 entries
since 01:39:57. The observer exited 0 and detached normally. No route result
or bitstream exists yet. The goal remains active: placement is advancing and
the remaining physical tests await USB detection. Current handoff remains
../openTPU/progress.md.

## OpenTPU parallel checks and full static retry, 2026-10-12 02:44 HKT

The active work remains ../openTPU. The original full heap native job
PID 138789/start 8930713 and tool session 31485 are preserved. Its current
legalizer is serial despite eight requested threads. At 02:41, a complete
read-only snapshot found 133,592 bound and 166,698 unbound solve cells;
this is not an overall completion percentage.

A full static attempt exposed a real float exponential overflow. A new isolated
complete backend fixes the two exponentials using double precision. Its five
actual exact-binary checks and five strict-frame assemblies passed concurrently.
The new full static retry started 02:40:10 HKT with --threads 8, native
PID 148107/start 9503156, tool session 28636. It reached iteration 120 past the
old crash point. Eight workers exist and use CPU, but serial work limits total
utilization. Both full jobs remain incomplete and neither produced a new image.

The attempted Git pull fetched 700639b but left HEAD at 5b1e646 because local
changes conflict. Those changes were backed up and preserved; merging now would
invalidate running source guards. The latest lsusb has no Xilinx adapter, so
physical normal selftest/LFM2 work remains pending. Current detailed handoff:
../openTPU/progress.md and ../openTPU/docs/openxc7_static_placer.md.

## Full static legalization advances, 2026-10-12 03:00 HKT

The corrected full OpenTPU static run passed RAM/DSP legalization, completed
logic spreading at iteration 656, and is legalizing the full logic. The
read-only snapshot confirms 222,955 bound and 127,198 unbound concrete
representatives, with 127,223 queue entries. This is not a whole-design
completion percentage. GDB detached normally and native PID 148107/start
9503156 resumed. Original full heap PID 138789/start 8930713 is preserved.
Both jobs request eight threads; strict legalization remains serial.
No route result or accepted OpenXC7 image exists yet, and USB is still absent.
Exact current receipts and resume commands remain in ../openTPU/progress.md.


At 03:47 HKT on 2026-10-12, both complete native placements remain live
with their exact original process start identities. Both native commands request
`--threads 8` and can execute on CPUs 0-7. A bounded 10-second CPU measurement
shows heap used 0.995 busy cores and static used 0.790; all eight static workers
were idle during this serial strict-legalization interval. Thread configuration
is already all cores; eight requested workers do not make this stage parallel.
CPU, memory and I/O pressure were low in this interval. The receipt is
`build/fedora-openxc7/cpu-thread-check-20261011T194700Z.json`.

The same static placer's 03:47:17 HKT read-only snapshot has 313,637 bound
and 36,516 unbound concrete representatives, up 2,259 bound since 03:10:42.
Remaining representatives are 36,130 LUT and 386 SELMUX. Observer exited 0,
detached and verified TracerPid=0. This is measured late placement progress,
not full implementation completion or an overall completion percentage.

The saved full standard ABC mapping was freshly qualified and attempted as a
complete static route, but exited 125 before placement with 22 combinational
loops; its controller exited 1. That failure is preserved under
`build/fedora-openxc7/litedram-default-static-vivado-reference-20261011T192700Z`.
The first proposed custom area script incorrectly used commas as command
separators, executing only strash and producing 907,726 raw LUTs. Its native
and boundary/clock receipts are preserved but the candidate is not selected.
A new immutable helper `tools/fedora_openxc7_cut_mapping.py` uses pinned literal
ABC script files and verifies all three actual commands in the native log.
Two full corrected remaps now run concurrently from the same complete pre-LUT
checkpoint, retaining all source files and full compute/memory dimensions:
`build/fedora-openxc7/jtag-ddr800-area-cut-20261011T194900Z` (session 45212,
Yosys PID 155618/start ticks 9911133) and
`build/fedora-openxc7/jtag-ddr800-delay-cut-20261011T194900Z` (session 51443,
Yosys PID 155623/start ticks 9911259). These jobs use independent output
folders and preserve both existing placements. Full route, strict assembly
and independent bitstream verification still must pass before accepting an
OpenXC7 image. No timing loops are bypassed. Full Vivado normal selftest and
physical model inference still await the missing Xilinx USB adapter. HEAD
remains 5b1e646; the fetched upstream changes are not merged into pinned builds.


Both corrected full cut mappings completed native synthesis with exit 0.
The log observer expected individually echoed commands inside ABC `source`,
so both wrappers exited 1. Their failed receipts remain unchanged. Separate
adopted synthesis directories verify the pinned three-command ABC file,
actual source invocation and completion marker, native exit, every input hash,
full hardware counts and all 1,748 BSCAN clock sinks. No synthesis was rerun;
the immutable JSON is hard-linked to a separate accepted manifest.
Area candidate: 184,539 raw LUTs, 3,092 F7 and zero F8 cells; adopted directory
`build/fedora-openxc7/jtag-ddr800-area-cut-adopted-20261011T195400Z`.
Delay-recovery candidate: 181,546 raw LUTs, 28,836 F7 and 10,431 F8 cells;
adopted directory `build/fedora-openxc7/jtag-ddr800-delay-cut-adopted-20261011T195400Z`.
These results preserve full dimensions and both DDR channels but do not prove
fit, timing, full functional equivalence or a legal whole-chip timing graph.
The next fresh exact-binary witness is a real F7 subtree with all 128 unique
seven-input vectors for the full no-F8 candidate. Existing F8 witness policy is
retained. The updated image checker verifies zero F8 in the selected full JSON
and its actual F7 root/BEL before accepting that alternative witness. The checker
is absent from both running controllers' pinned inputs; all new selections pin
its new source. Original probe helpers and live route/backend helpers remain
unchanged. Both full original placements still run; FPGA USB is still absent.


At 2026-10-12 04:00:51 HKT, both new full cut-mapped static implementations are live.
The area trial has native PID 157975/start ticks 9968368, tool session 23263;
the delay trial has native PID 157970/start ticks 9967810, session 91723.
Both use the exact corrected backend 2bfd62e1..., `--placer static --threads 8`,
CPUs 0-7 and nine native threads. Both working Vivado reference audits exited 0,
and both passed the normal whole-design timing-graph checks and entered static
analytical placement. These are complete accelerator/dual-DDR implementations,
with existing full heap and fast-static placements still preserved and live.

The area trial's actual pre-spacer COMB estimate is 83.29%, versus 93.76%
in the original fast mapping; the delay trial is 93.53%. The area trial packs
270,142 SLICE_LUTX cells versus 300,747 in the original. This is a measurable
reduction in placement density for the unchanged full source/dimensions, but
neither count nor the estimate proves placement, routing, numerical timing or
physical operation. No timing loops were overridden. Both full routes and
accepted images remain incomplete.

Fresh actual MUX witnesses passed: the no-F8 source's F7 gate covered all 128
unique seven-input patterns and placed an actual SLICE_X0Y236/F7AMUX; the delay
source's F8 gate covered all 256 eight-input patterns. Both strict-frame
assemblies exited 0. The four unchanged exact-backend carry/upper-carry/DSP/FF
receipts are reused honestly; the prior F8 receipt remains preserved. Normal
selection/synthesis witness checks passed and each new selection pins 19
mapping/qualification evidence files, including the changed checker. Previously
qualified F8 selections still pass the unchanged F8 policy. New qualification
and full pipeline folders use prefixes `area-cut-` / `delay-cut-` and suffix
`20261011T195541Z`. Exact hashes, native arguments, process start identities and
sessions are in `build/fedora-openxc7/full-cut-trials-resume-20261011T195541Z.json`.
Preserve all four running implementations. Original failed mapping wrappers,
the 22-loop standard-mapping attempt and the unusable script experiment remain
retained. USB is still absent, and native full normal selftest plus actual model
inference remain pending. The goal is active, not complete or blocked.


The 04:00:18 HKT 15-second CPU sample confirms activity on all eight cores:
per-core busy percentages were 89.9, 72.9, 66.0, 82.6, 80.7, 63.2, 68.0
and 94.5 (host mean 77.2%). Both new static jobs accumulated CPU time on
all nine native threads; all eight workers participated. Original heap/static
jobs each used about one busy core in their current serial legalization phase.
This measures current usage, not a promise of constant 800% CPU consumption.
Memory pressure was zero in this sample and approximately 4.7 GiB remained
available. Actual receipt:
`build/fedora-openxc7/cpu-parallel-static-20261011T200018Z.json`.
All four controllers' complete pinned-input inventories were freshly checked
unchanged after the scoped checker addition; exact checks are saved in
`build/fedora-openxc7/full-cut-input-verification-20261011T200018Z.json`.
The new area/delay trials reached iterations 99/91 respectively. Neither full
route, accepted OpenXC7 image nor the pending physical model run is complete.
All four full implementations continue with eight threads requested.


At 04:04-04:06 HKT on 2026-10-12, all four exact native processes remain
live, and the new area/delay analytical placers have advanced to iterations
350/330. No native route exit or routed/FASM/image artifact exists yet.
The original heap's bounded read-only snapshot at 04:05:49 finds 149,617 bound
and 150,673 unbound entries in its same 300,290-cell solve vector, versus
133,592/166,698 at 02:41:44. The additional 16,025 bindings are FF entries;
LUT counts remain 44,489 bound/106,790 unbound. Its current search has 3,536,293
aggregate attempts and is still on FF placement. This confirms actual progress
in the original quiet-log job. The new reusable `run-heap-observer.py` checks
its exact PID/start/executable, records actual GDB exit 0 and handles lowercase
'detached'; the existing read-only GDB source remains unchanged.

The original fast-static snapshot at 04:04:33 remains 313,637 bound/36,516
unbound concrete representatives, unchanged since 03:47:17. It is consuming
CPU in a legalizer search, not terminal; this records no new binding progress
for that interval. Both observers exited 0, detached, and left TracerPid=0.
No native functions were called and no placement state was written. The vector
scopes are different and neither is an overall design completion percentage.
The snapshots are respectively
`build/fedora-openxc7/litedram-vivado-reference-20261011T170600Z/placer-counter-20261011T200546Z.json` and
`build/fedora-openxc7/litedram-static-double-vivado-reference-20261011T184000Z/static-legalizer-20261011T200429Z.json`.

Live lsusb and kernel-log refresh still show no Xilinx adapter or subsequent
USB recovery since the 00:20:47 disconnect/00:20:50 enumeration failure.
No hardware client was started. Full native normal selftest/model inference
still requires the adapter. The previous turn made concrete full-mapping and
qualification progress; this continuation is a verified wait on live full jobs.
The goal remains active while meaningful software work continues.


At 04:13 HKT, the full area-mapped static run reached iteration 600,
completed RAM/DSP legalization (1,962 queued entries, post-legalization HPWL
4,653,124), and entered strict logic legalization with 306,321 queued entries.
The full delay-mapped run also completed its RAM/DSP legalization (post HPWL
4,356,256) and reached iteration 600 while continuing logic spreading.
Both exact native processes and original two implementations remain live;
normal full timing-graph checks were retained and no input/helper/backend was
changed during placement. No route exit, routed JSON, FASM or image exists yet.
The stage receipt is `build/fedora-openxc7/full-cut-stage-progress-20261011T2013Z.json`.
A two-minute live-process monitor also recorded repeated CPU/log progress for
all four implementations and no USB adapter. Receipt:
`build/fedora-openxc7/live-full-jobs-20261011T200735Z.json`.

The original frozen route/assembly pipeline was reviewed for the new mappings:
it verifies the complete constrained JSON differs only by the two recorded
MMCM LOCs, exact full source/core/backend identity, native route exit 0,
required route artifacts, strict FASM/frame assembly, every encoded frame and
USER2 image structure. It does not accept incomplete live-route output. The
new no-F8/F7 selection preserves these normal full-image checks. Numerical
timing, CRC and physical behavior remain separate limits of its status.
The hardware continuation still runs the complete normal selftest including
vops/stream and physical eight-token LFM2/ISA comparison; no stages are skipped
to produce a pass. That continuation cannot start while USB is absent.


At 04:17 HKT, the full area-mapped implementation completed strict logic
legalization of the 306,321-entry queue and entered simulated annealing
placement refinement. The native log reports post-legalization HPWL 9,526,925
(delta 1,170,542). This is the actual normal full-stage completion, with all
source/dimensions, dual DDR and backend legality assertions retained. It is
not route completion, timing qualification or a ready bitstream. The exact
process is still PID 157975/start ticks 9968368, tool session 23263. Receipt:
`build/fedora-openxc7/area-cut-static-vivado-reference-20261011T195541Z/logic-legalization-pass.json`.
The preceding 04:13:51 read-only snapshot covered all 356,094 unique concrete
representatives in this candidate's vector, with 173,013 bound/183,081 unbound,
all carry/RAM/DSP representatives bound and zero unexpected BEL values; it was
an intermediate snapshot, not the final legalization result. Its observer
exited 0, detached and verified TracerPid=0. The later native log establishes
that this phase completed. No route exit, routed JSON, FASM or accepted image
exists yet. The other complete implementations remain live; JTAG USB is still
absent. This continuation now records concrete full-stage progress rather than
only a wait. Preserve the running full controller and let its normal guarded
routing/assembly/image checks complete.


At 04:22:49 HKT, a bounded read-only observation of the exact area process
finds it in SAPlacer::compute_cost_changes, with current wirelength estimate
14,764,740 versus the initial refinement log's 15,734,909. Its current timing
cost is 1,108.04 versus the initially rounded 1,449. These are internal placer
costs, not routed timing or MHz. Current counters are n_move=87,443 and
n_accept=34,940; the source resets them each outer iteration, so they are not
whole-run totals or completion percentages. The actual temperature is
8.145e-8; `%f` logs round that small nonzero value to 0.000000. GDB exited 0,
detached and verified TracerPid=0, with no native function calls or state writes.
Some optimized locals were unavailable and their errors are retained. Receipt:
`build/fedora-openxc7/area-cut-static-vivado-reference-20261011T195541Z/refinement-observe-20261011T202248Z.json`.

The original full logic-legalization pass's exact log prefix was copied to
`logic-legalization-frozen.log` and its SHA256 verified equal to the original
observation's recorded hash. A new immutable receipt
`logic-legalization-frozen-evidence.json` references that frozen prefix;
the original phase observation and live log are preserved. Use the frozen
receipt referenced by the full-job resume state for later evidence checks.

The compiled static placer calls serial placer1_refine after its parallel
analytical work; it does not call the separate parallel_refine implementation.
All eight threads remain requested, but this phase cannot sustain eight busy
cores through that flag. The live job and all pinned source/helpers were
preserved. No routed graph, accepted OpenXC7 image or numerical timing pass
exists yet; full Vivado normal selftest and actual LFM2 still await USB.


Final live check at 04:25:57 HKT: all four native PID/start identities still
match and no native route exit exists. Area refinement advanced through logged
iterations 5 and 10; at iteration 10 its wirelength estimate is 14,590,901 and
its rounded timing cost is 1,037. These are internal placement metrics. The
area implementation still has no completed routed graph/FASM/accepted image.
No Xilinx USB adapter is enumerated. The original full controllers and tool
sessions 31485, 28636, 23263 and 91723 remain live and are preserved. Updated
resume state is `build/fedora-openxc7/full-cut-trials-resume-20261011T195541Z.json`.
Tracked whitespace checks pass. The goal remains active: full routing/image
verification and remaining physical selftest/model comparisons are unfinished.


At 04:42:34 HKT, the full area-mapped implementation is live in refinement
at logged iteration 25, wirelength estimate 14,061,735 and rounded timing cost
892. Its native PID/start identity still matches 157975/9968368; no route exit,
routed graph, FASM or accepted image exists. The delay-mapped trial remains
live in strict logic legalization. Original two native implementations and
their owning sessions remain live. A six-minute read-only monitor confirms
continued CPU/log advancement in the exact area process and no USB adapter;
receipt `build/fedora-openxc7/area-refinement-live-20261011T203045Z.json`.

Actual process/parent PSS measurement at 04:37:51 finds the four native jobs
using roughly 6.2, 6.2, 7.7 and 6.2 GiB, plus their wrappers; approximately
3.9 GiB is available and current memory pressure is zero. The original heap's
sleeping wrapper has about 1.1 GiB swapped; the four native jobs have zero swap.
No further full trial is launched into this measured footprint. Receipt:
`build/fedora-openxc7/full-jobs-memory-20261011T203751Z.json`.
The pending physical receipt was freshly read: its full normal selftest is
actual FAIL/exit 1 and model_checks is empty; full physical completion is still
unproven. The separate full-memory receipt remains PASS and SRAM programming
receipt remains PASS_SRAM_PROGRAMMED_INIT_DONE, both with flash_written=false.

A current-state block now appears first in this repository's progress.md,
with exact live-job/proof links; all historical observations are preserved below.
The preceding goal turn made full-stage progress; this continuation is a verified
wait on live, advancing full jobs. The goal remains active, not complete or
blocked while software work can progress. No source-pinned build was restarted,
no hardware client ran, and no checkout, commit, stash, merge or push occurred.


Latest live check at 04:48:20 HKT confirms all four exact native identities
and live RUNNING controllers. Area refinement reached logged iteration 35,
wirelength estimate 13,928,108 and rounded timing cost 837. No native route
exit or accepted OpenXC7 image exists, and no Xilinx USB device is present.
Live receipt `build/fedora-openxc7/goal-continuation-live-20261011T204820Z.json`.
All 31 full-design source files were freshly hash-checked unchanged across
all four route inventories; HEAD/origin remain 5b1e646/700639b. The source
verification is `build/fedora-openxc7/full-source-verification-20261011T2049Z.json`.
The same software jobs continue; no narrower source/profile or replacement
process was used. This continuation is a verified wait, not a claim that the
requested full route/image or physical normal selftest/model run is complete.


OpenTPU goal continuation, 2026-10-12 05:24:58 HKT: the full area mapping has passed synthesis and logic legalization and is refining placement (latest logged iteration 80). The original full heap attempt ended normally with native error exit 125, unable to find legal placement at its utilization limit; its controller exited 1. Three other complete native implementations remain live, each requesting eight threads, with serial current stages. Routing and an accepted OpenXC7 image remain unfinished. Fedora still detects no Xilinx USB adapter, so the pending physical normal selftest and LFM2 token comparison have not resumed.

Full Vivado 2026.1 successfully exported raw speed models for the exact Kintex-7 part: DSP48E1, MMCM, input/output serializers and supporting I/O logic. A hash-verified full checkpoint inventory records 717 DSPs in 13 profiles, including 143 PREG=0 cells. These data are not yet imported or numerically qualified; all live full-design inputs and the backend remain unchanged. Details: ../openTPU/docs/openxc7_vivado_timing.md and ../openTPU/build/fedora-openxc7/goal-progress-timing-export-20261011T212458Z.json. The full goal remains active.


OpenTPU continuation, 2026-10-12 05:59:10 HKT: the full area candidate completed placement and entered main routing on the same native PID 157975/start ticks 9968368. Full route and accepted image are still pending. The provisional placement estimate misses the 100 MHz core target (41.86 MHz); numerical timing is not qualified. Router2 uses fixed 4/2/2-worker phases and serial work, so --threads 8 does not create eight simultaneous router workers. A 15-second sample measured 232.2% routing CPU. All 15 complete DSP configurations, covering 717 full-design DSPs, were queried with full Vivado: native exit 0, 122,150 finite timing arcs, zero parameter mismatches. Integration remains pending. The three native jobs remain live; USB/JTAG is still absent. See ../openTPU/progress.md and ../openTPU/docs/openxc7_vivado_timing.md.


OpenTPU continuation, 2026-10-12 06:13:09 HKT: all three exact native jobs remain live with --threads 8 and CPU affinity 0-7. The full area candidate is routing; no route exit or accepted OpenXC7 image exists. The 06:05 15-second sample measured 199.1% route CPU and 99.5%/99.4% for the other placement jobs. Router2 has fixed 4/2/2-worker phases, independent of the eight-thread flag. An eight-worker DSP table preparation completed natively with exit 0: all 15 configurations / 717 full-design DSPs / 122,150 arcs; independent raw vendor-bound comparison found zero mismatches, and 18 standalone converter tests passed. Negative, nonmonotonic hold corners are preserved. The tables are not yet imported into a backend; numerical timing remains unqualified. USB/JTAG is still absent. See ../openTPU/progress.md, ../openTPU/docs/openxc7_dsp_timing_plan.md and ../openTPU/build/fedora-openxc7/goal-all-cores-dsp-tables-20261011T221309Z.json.


OpenTPU continuation, 2026-10-12 06:40:26 HKT: the isolated opt-in DSP timing prototype compiled all 14 affected translation units with eight workers. Actual callbacks matched all 15 source modes (6,255 port classifications, 3,489 sequential pins, 117,024 combinational arcs, zero mismatches), including default omission and explicit mode/grade rejection. A complete full-design pack-only export exited 0 and preserved all 717 named DSPs. Its actual packing changes CARRYIN inversion and per-bit bus flags; the FASM rule yields 19 effective hardware modes, which need new Vivado characterization before full timing use. The live full route continues on the original unchanged backend; all three native identities remain live, no accepted image exists, and USB/JTAG is absent. See ../openTPU/progress.md and ../openTPU/docs/openxc7_vivado_timing.md.


OpenTPU continuation, 2026-10-12 07:18:12 HKT: all 19 effective packed DSP configurations were characterized with full Vivado (native exit 0, 152,458 arcs, zero parameter mismatches). The mask-aware backend rebuilt 14 translation units with eight workers and passed defaults, split-mask and rejection checks. Its complete native OpenTPU pack/audit passed for all 717 DSPs: 254,649 port classifications, 177,541 sequential pins and 1,842,120 combinational arcs, zero mismatches. The original full route remains active and unchanged; a read-only backtrace confirmed horizontal-partition routing, with normal detach. No accepted OpenXC7 image exists. Remaining actual PHY/clock profiles are input serializer 1, output serializer 2, MMCM 2, PLL 1 and BUFGCTRL 1. Whole-board timing/path validation and physical normal selftest/model execution remain pending; USB/JTAG is absent. See ../openTPU/progress.md and ../openTPU/docs/openxc7_vivado_timing.md.


OpenTPU continuation, 2026-10-12 07:45:17 HKT: full Vivado queried all seven actual PHY/clock parameter groups covering 378 cells. The corrected HR-site/feedback/default-compensation probe exited 0, with zero parameter mismatches and 376 finite timing arcs. Generated-clock data confirm 400 MHz quarter-phase waveforms (0.625/1.875 ns); current backend loses that phase and derives feedback clocks at VCO rate rather than vendor input rate. Intrinsic model integration, clock-family corrections and path checks remain pending. The complete 717-DSP callbacks remain verified. All three original full implementations are still live and unchanged, no accepted OpenXC7 bitstream exists, and USB/JTAG is absent. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 08:03:54 HKT: an isolated opt-in clock-feedback fix compiled and linked, preserving the verified DSP model. Complete unchanged-design on/off packs both exited 0. All 20 used clock outputs across four generators match expected periods; corrected direct feedback is 20,000 ps and buffered write-MMCM feedback is 10,000 ps. Off mode reproduces prior 555/714 ps direct periods and missing buffered feedback constraints. Phase/family timing, serializer intrinsic integration and whole-board timing remain unfinished. The three original native jobs remain live and unchanged, no accepted OpenXC7 bitstream exists, and JTAG USB is absent. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 08:25:56 HKT: the isolated serializer backend rebuilt all 14 affected files with eight compiler workers, and eight independent native validation cases ran with eight workers. A 15-second sample measured all eight cores busy at 68.61-99.73% as compilation completed. The complete unchanged design passed its actual native pack/callback audit for all 358 serializers: 6,174 port classifications, 4,746 sequential checks, 288 multi-clock pins, 288 falling-edge checks and 162 combinational arcs, zero mismatches. All 20 used generator periods still pass. Clock-generator intrinsic/reset semantics, generated-clock phase/family analysis and whole-board timing remain pending. All three original full implementations are live with their unchanged binary and eight-thread requests; no accepted OpenXC7 image exists, and JTAG USB is absent. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 08:46:34 HKT: the isolated clock backend rebuilt 14 files with eight compiler workers and passed eight parallel native configuration checks. It imports all 287 enabled clock arcs while retaining seven vendor-disabled reset records. The complete unchanged design passed its native clock audit for all 20 cells: 294 port classes, 122 sequential checks, 20 generated outputs, 16 falling-edge checks and 54 propagation arcs, zero mismatches; ten per-cell disabled model records are explicit. The same native run revalidated all 358 serializers, and all 20 output periods still match. Generated-clock phase/family/duty/ratio handling and the launch-domain selection issue remain to be implemented. All three original full jobs continue with their unchanged binary, full routing/image qualification remains pending, and JTAG USB is absent. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 09:51:23 HKT: exact nominal waveform/ancestry extraction passed on the unchanged full design. All 20 generator outputs match vendor periods, phases and high times; all share SYS_CLK ancestry, with four fine-phase outputs retained in two MMCM groups. The backend rebuilt four changed files with an eight-worker limit and passed eight parallel native cases, including an actual shifted-primary vendor comparison. The complete inventory has 38 known clock nets and one unknown raw BSCAN TCK; its only two API references are independently proven constant buffer controls. Both sampler clocks have 792 references after all callbacks initialize. The full area router is now running only its main thread and has emitted three route_arc warnings at five million iterations; no terminal route or accepted image exists. All three original jobs and all 31 source hashes remain unchanged, and JTAG USB is absent. Phase-aware engine budgets, clock skew and whole-board timing remain pending. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 10:34:48 HKT: nominal phase-edge timing integration compiled all 16 affected files with eight workers. Actual analyser budgets match 40 vendor register-path edge relations, and eight parallel native cases pass. The complete unchanged accelerator passed its explicitly unplaced intrinsic analysis: 18 clock-domain pairs, 14 known nominal budgets, two dynamic relative phases and two unrelated sources; smallest known setup allowance 5000 ps. Generic timing-index assignment now precedes extraction and analysis. Routed skew, uncertainty/reset/CDC, dynamic calibration and Kintex fabric timing remain unqualified. All three original processes retain their identities and binary; the full area router remains active with one thread and 5 five-million-iteration arc warnings. No accepted image exists, and JTAG USB is absent. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 11:03:26 HKT: the new isolated unplaced path exporter passed eight native cases and full-design export (exit 0, 17 critical paths, all four unknown pairs present). Two are falling-edge DDR command transfers and two enter JTAG toggle synchronizers. Both three-register JTAG chains retain net-level ASYNC_REG annotations. Actual DDR800 host and firmware use WRAP=112, requiring a conditional 1250 ps phase margin; 25,088 host moves and 936,544 mocked intermediate writes pass. No timing exception or bound was imported; routed timing, clock skew/jitter, exhaustive CDC and physical tests remain pending. All 31 full source files and the original live binary are freshly verified unchanged. All three original jobs remain live. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 11:29:09 HKT: 18 actual Vivado register paths validate declared phase snapshots, with unchanged MMCM parameters. An isolated software-bound backend rebuilt three affected translation units with an eight-worker pool; eleven native cases and full-design conditional analysis pass. The full 18-domain result has 14 nominal pairs, two software-conditional DDR command pairs at 3750/-3750 ps and two unrelated JTAG pairs. Fresh contracts are required on replay and checked against the actual MMCM source/root/VCO. This remains unplaced conditional evidence, not routed or hardware qualification. All 31 full source files and the live original binary are freshly verified unchanged. Three original native jobs remain live; no accepted OpenXC7 image exists. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 12:30:30 HKT: complete packed mailbox audit passes for all 1103 live payload crossings (572 request, 531 response), plus six synchronizer stages with no early-stage consumer fanout. Twenty-two digital phase/bus-delay cases pass with 17 transactions each; both injected late payloads fail as expected. Full exact-part FDRE-pair query validates all 20 ns/300 ns datapath-only requirements, using stand-in enables/clocks. Raw minimum queries return ignored false-path objects with infinite slack; filtering unconstrained paths returns zero constrained hold paths. A complete candidate endpoint contract is saved; native enforcement and synchronous-chain placement still need implementation. Original full source/binary hashes and all three live jobs remain unchanged. No accepted OpenXC7 image exists. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 13:03:00 HKT: isolated synchronizer placement backend passes compilation and eight native cases, including two completed geometry routes using both slice sites. Each chain occupies A/B/C primary FFs in one slice, and invalid annotations/clocks/connectivity/fanout are rejected. The complete unchanged accelerator packs with exit 0 and a direct audit proves both actual clusters, six annotations and relative offsets 0/16/32. Phase budgets are unchanged. Full physical placement/routing with these constraints and all 1103 payload datapath deadlines remain pending; no timing exception or original live-job change was made. All 31 full source files and original live binary hashes freshly match. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.


OpenTPU continuation, 2026-10-12 13:30:19 HKT: native direct-FF mailbox datapath enforcement passes compile/link/startup, eleven semantic cases and complete unchanged-design analysis. All 1103 limits are applied and individually audited (572 at 20 ns, 531 at 300 ns), with unchanged synchronizer clusters and phase budgets. Data route delay affects slack/criticality/reporting; clock route does not. Related roots, synchronizers and invalid mappings are rejected, stale tags are cleared and process-local validation is required. These are semantic and unplaced checks using provisional generic FF timing, not numerical route/hardware qualification. All 31 full source files and original live binary hashes freshly match; three original native jobs remain active. See ../openTPU/progress.md and ../openTPU/docs/openxc7_phy_timing_plan.md.

OpenTPU continuation 2026-10-12 14:10:45 HKT: all 179299 FF modes inventoried; 810 vendor measurements and 85 location-specific tables pass, native import pending. Router advances on ordinary fabric nets. Upstream fork main is 68 commits ahead; missing PR 81 is relevant to K480T, isolated guard implementation pending. Original full jobs/source preserved; no USB cable enumerated. See ../openTPU/docs/openxc7_router_review.md and ../openTPU/progress.md.

OpenTPU continuation 2026-10-12 14:38:40 HKT: upstream PR81 guard implemented in an isolated backend. Native A/B verifies both K480T clock tiles, three routes and four bad-FASM rejections. Full unchanged-design analysis exits 0 with all 1103 endpoints/clusters/phase budgets preserved. Fixed candidate available; no full new route or numerical timing/hardware qualification yet. Original three native jobs and all 31 source files unchanged. See ../openTPU/docs/openxc7_router_review.md and ../openTPU/progress.md.

## OpenTPU cross-handoff, 2026-10-12 15:36 HKT

OpenTPU progress is in ${OTPU_ROOT}/progress.md (`${OTPU_ROOT}/progress.md`). The full original area route reaches congestion iteration 1, with 564,545 overused wires; all three original jobs remain live and no terminal route output exists. Upstream main is 68 commits newer than our c68c135 base, with no general router source changes. The isolated PR 81 guard is validated, with full route and speedup pending. The independent FF context comparison passes 262 finite contributions in 272 queries; it demonstrates immediate-driver dependence, so the 85 port-driven models are not yet universal native FF callbacks. No hardware was accessed.

## OpenTPU cross-handoff, 2026-10-12 18:12 HKT

See ${OTPU_ROOT}/progress.md (`${OTPU_ROOT}/progress.md`). Complete read-only Vivado reference comparison passes 7,901 finite path contributions across 8,004 queries, with 70 untimed and 33 ignored paths retained. All 112,352 actual reference FFs are inventoried; numerical signatures vary within 522 groups, so universal native callback import remains pending. Current OpenXC7 main is 70 commits newer; original YosysHQ upstream has additional generic router patches worth isolated comparison. All original full implementation jobs and source scope are preserved; no accepted OpenXC7 image or new hardware result exists.

## OpenTPU compact router handoff, 2026-10-12 18:29 HKT

See ${OTPU_ROOT}/progress.md (`${OTPU_ROOT}/progress.md`). The isolated opt-in router memory backport passes six actual same-seed routes with byte-identical FASM and routed netlists. Its K480T wire vector allocates 256 MiB less memory, with no full-design speedup claim. Complete native packing keeps all 1,103 mailbox limits, two sync clusters and 18 domain pairs unchanged. Selected candidate: ${OTPU_ROOT}/build/fedora-openxc7/router-wire-memory-candidate-20261012T102923Z.json. All three original implementation jobs and all 31 source files are unchanged. Full route, timing/image qualification and physical compute/model tests remain pending. Fedora currently detects no JTAG adapter.

## OpenTPU clock LOC investigation, 2026-10-12 19:19 HKT

See ${OTPU_ROOT}/progress.md (`${OTPU_ROOT}/progress.md`). A clock preplacement ordering bug is identified and an isolated opt-in fix improves six channel-0 dedicated clock arcs: 12 failures become six in the same 54-arc diagnostic. Channel 1 remains unresolved. Diagnostics intentionally exit 125 before the main router and establish no full route/image/hardware pass. Forward traversals are limited; flagged no-bit PIPs need comparison with Vivado. All original jobs and all 31 source files remain unchanged. Latest evidence: ${OTPU_ROOT}/build/fedora-openxc7/goal-clock-loc-diagnostic-review-20261012T111912Z.json.

## OpenTPU clock cascade fix and new full route, 2026-10-12 20:24 HKT

The remaining six channel-1 failures are fixed by restoring 32 bit-mapped
top clock cascade connections in a private database. The stock rebuild
matches the installed database exactly. All 54 dedicated clock arcs pass,
and the actual clock fixture completes native main routing with exit 0;
all 12 cascade settings are emitted and all 16 global clock drivers are
configured. Full accelerator packing and all 1,103 mailbox limits, two
synchronizer clusters and 18 domain budgets remain unchanged. A new full
placement/route is running as PID 261549/start 15880662, tool session 61317,
with CPUs 0–7 allowed and the original core100/dualDDR800 scope. The three
earlier jobs and all 31 source hashes remain unchanged. Full route/timing,
accepted OpenXC7 image and remaining physical compiler/model tests are
pending; no Xilinx USB cable was detected at this check. See the current
OpenTPU handoff (`${OTPU_ROOT}/progress.md`) and
complete evidence (`${OTPU_ROOT}/build/fedora-openxc7/goal-clock-cascade-route-review-20261012T122414Z.json`).

## OpenTPU exact backend and image preparation, 2026-10-12 21:41 HKT

All five actual carry/upper-carry/DSP/FF-edge/MUXF7 witnesses now reproduce
their previously qualified FASM, strict frames and complete routed circuits
with the current executable/database. Only four disabled reporting settings
differ in JSON. Six strict assemblies pass. All 12 restored clock bits are
verified, including rejection of a flipped bit; the clock diagnostic's USER2,
all 46,336 frame payloads and ECC also pass. Full source/image preparation
verifies the mapped graph plus only two MMCM LOCs and pins 2,283 inputs.
The finalizer waits on the exact live full route without producing premature
outputs. New full PID 261549/start 15880662 remains live at refinement
iteration 68; all three earlier jobs and all 31 sources remain unchanged.
Full route/timing/image and physical compiler/model tests are pending. USB
and sysfs show no Xilinx cable. Current evidence (`${OTPU_ROOT}/build/fedora-openxc7/goal-clock-primitive-and-image-review-20261012T134137Z.json`).
## OpenTPU full routing and FF physical context, 2026-10-12 22:36 HKT

The corrected complete build has finished placement and entered the main
router. All 30 logged clock nets route without the earlier dedicated-resource
failures, and the 52-byte compact wire table is active. The provisional
post-placement core estimate is 50.97 MHz against the retained 100 MHz target;
it remains unqualified and no terminal route/image output exists. All four
native job identities and all 31 source hashes match, with no Xilinx USB cable.
Physical FF grouping reduces 522 varying groups to one using actual driver
BEL/site pins; 875 repeated contexts cover 2,118 samples. The fresh nine-cell
query matches all 18 raw arcs and finite path checks and records actual mux
choices. The remaining group has fanouts 31/1/1 and 2–4 ps variation; no
universal model was installed. Current evidence (`${OTPU_ROOT}/build/fedora-openxc7/goal-physical-ff-context-and-full-router-20261012T143644Z.json`).

