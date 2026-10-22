# Linux YPCB BRAM preparation

These helpers were developed on Fedora and retain their `fedora-*` filenames.
They use standard Linux command-line tools and project-local dependencies.

Prepare `top_jtag_bram_first` for `xc7k480tffg1156-2`: a smaller configuration
of upstream `top_jtag_bram`, with two 4 KiB Wishbone BRAM banks and USER1
JTAG debug. It contains no CPU or DDR3 storage path. The original default
configuration has two 64 KiB banks. The replacement DDR3 controller remains
a later bring-up step; its predecessor's DDR3 results do not validate it.

The first wrapper selects `BRAM_ADDR_W=10` and version `0xB07EB002`. The
parameterized default retains width 14 and version `0xB07EB001`. Bank selection
uses the corresponding address bit, giving the first profile word addresses
`0x000–0x3ff` and `0x400–0x7ff` (byte addresses `0x0000–0x0fff` and
`0x1000–0x1fff`). The hardware validator selects these bounds with `--profile first`.

For this first run the card is powered separately with JTAG only. The BRAM
image can validate read/write access without PCIe or a processor application.

## Recorded BRAM preparation results (2026-10-06)

The results below describe a retained local build. The generated files under
`build/` and `boards/ypcb-00338/build/` are outside the source distribution.
Recheck or rebuild them against the current sources before use; a historical
hash or test count does not qualify subsequent source changes.

The selected simulation suites passed 34 tests. An additional first-profile
fabric integration test passed a write/read sweep of all 2,048 words across
both banks, bank isolation and byte masks. It injects commands at the bridge's
system-clock interface and exercises the real RTL master, decoder and memory;
it excludes the serial BSCAN path and physical cable. The 35 test results and
log hashes are in `build/fedora-simulation-results.json`. Four selected formal suites
passed their bounded checks, recorded in `build/fedora-formal-results.json`.
The isolated DLC10/XVC programmer compiled successfully, passed its source
and binary checksum recheck, and reached the USB driver in a no-cable probe.
The expected USB-open failure is not a physical JTAG validation.

The first-profile bitstream is built at
`boards/ypcb-00338/build/bonetto_soc_ypcb00338_jtag_bram_first.bit`.
It is 18,735,165 bytes, for `xc7k480tffg1156-2`, with SHA256
`dbde7024a7e7e9485944cdedc3087384d7ac48d3357e5ce6d7d7d892067245dc`.
The native router completed 2,428 initial arcs and passed the reported 50 MHz
target on all three clocks. Every FASM feature passed strict assembly. The
independent bitstream check verified its header, packet bounds, configuration
ID, frame payload and START/DESYNC commands. Evidence is in
`build/fedora-first-route-run.json`, `build/fedora-first-frame-assembly.json`
and `build/fedora-first-bitstream-check.json`. No FPGA programming has occurred.

At that snapshot, bounded legacy and default native routing attempts for the
full two-64-KiB profile did not complete. Their logs and the
verified 777-primitive placement checkpoint are preserved under `build/`.
The first wrapper reduces the mapped memory from 32 RAMB36 blocks to two.
The successful native stages are recorded in
`build/fedora-first-bram-uncached-build.log`; the final assembly/reuse log is
`build/fedora-first-bram-build.log`.

OpenTPU and MicroBlaze/MIG projects are optional external context. Consult
their own checkouts for current build state, transport requirements and
hardware validation. Earlier recovery work staged in Bonetto's local `build/`
directory belongs to those projects and is excluded from this BRAM procedure.

## Native host environment

The helper reuses existing native tools without installing Nix,
changing shell profiles or modifying those other checkouts. The
[openXC7 project](https://github.com/openXC7/toolchain-nix) describes the
underlying Yosys, nextpnr and Project X-Ray flow.

| Component | Required local source |
|---|---|
| Yosys and Icarus | Executables on PATH |
| Python simulation | `build/fedora-venv`, Python 3.13, cocotb 2.0.1 |
| SymbiYosys | `build/sby-source`, revision `b1a1e98cba941ec8433f8dc27f416cd7bb7f14be`, installed under `build/fedora-tools` |
| Yices | upstream 2.7.0 Linux binary, installed under `build/fedora-tools` |
| nextpnr-himbaechel | isolated copy at `build/himbaechel-probe/nextpnr-himbaechel`, version `c68c135`, source revision `c68c13582e972292c86a5025140d52e713384cbc` |
| Matching assembler database | `${BONETTO_WORKSPACE_ROOT}/tiny-gpu/build/ypcb/prjxray-db`, revision `517d66a383676cb971177ea92b0ff3b6ea6e8690` |
| Exact-part chipdb | `${BONETTO_WORKSPACE_ROOT}/tiny-gpu/build/ypcb/nextpnr-build/himbaechel/uarch/xilinx/chipdb-xc7k480t.bin` |
| FASM Python tool | `${BONETTO_WORKSPACE_ROOT}/tiny-gpu/build/ypcb/xray-venv/bin/fasm2frames` |
| Frame assembler | `${BONETTO_WORKSPACE_ROOT}/tiny-gpu/build/ypcb/prjxray-build/tools/xc7frames2bit`, source `ed3331c6200f421164101388759fc2860b0f5634` |
| XVC-enabled programmer | isolated `build/openfpgaloader-xvc-dlc10` build with DLC10 XVC support |

Source `scripts/fedora-env.sh` to put these tools on PATH for this shell.
Set `BONETTO_WORKSPACE_ROOT` to the workspace containing the `tiny-gpu` tool
donor. The helpers also accept the legacy `OTPU_WORKSPACE_ROOT` alias and
fall back to `$HOME`, in that order. The individual `BONETTO_*` environment
variables in `fedora-env.sh` allow tool paths to be changed independently.
Use `YPCB_ROOT` for the shared cable-tool checkout or `BONETTO_CABLE_INIT`
for the initializer script itself. `YPCB_ROOT` defaults to
`$BONETTO_WORKSPACE_ROOT/ypcb` after resolving the workspace fallback above.
The router is a local copy; its chipdb and assembler depend on the other checkouts.
Do not remove their build directories while using this environment.
The original placement binary has SHA256
`72f8d48aad976ce098ecb7f0c591a96da59f333f3a27ceff57e59aabcd8fb74a`;
the isolated routing derivative has SHA256
`630418ac83a9c8747f1b5bda8d5b642f5e94a8776d9cf46dfee0218edcbfd221`;
the chipdb has SHA256
`790e05a88e8406b4da69d4fb6a158317e2621c85aa8452973edc85a8a4be1492`.
The environment also supplies the Project X-Ray source directory on
`PYTHONPATH`, which the installed `fasm2frames` entry point needs.

The additional [`fedora-build-router.py`](../scripts/fedora-build-router.py)
helper archives source revision `c68c13582e972292c86a5025140d52e713384cbc`,
applies [`nextpnr-router1-precision.patch`](../scripts/patches/nextpnr-router1-precision.patch),
compiles that one module and relinks 56 recorded cached object/library inputs
from the matching native donor binary. It hashes its isolated source and
checks that cached inputs do not change during the build. It does not write
to the source or object donor directories.

This experiment exposes `BONETTO_ROUTER1_ESTIMATE_PRECISION`: the default
remains 12,000 ps for this device, while a value of 1,000 ps limits how far
router1 continues searching beyond its best path. This changes a routing
heuristic. Its legality checks and final 50 MHz timing requirement stay
enabled. The first wrapper changes bank capacity, the corresponding address
width and its version ID.

The strict assembler also runs through
[`fedora-fasm2frames.py`](../scripts/fedora-fasm2frames.py), which caches the
database's device grid. Stack sampling found the original entry point
reconstructing all 136,359 tiles repeatedly while configuring unused I/O
bank tiles. The cached grid matched freshly constructed location, tile and
dimension data in `build/fedora-grid-cache-check.json`. This runner uses the
original feature parser, lookup and frame generator, including required and
unused I/O features. It leaves the shared Project X-Ray source untouched.

Bootstrap the project-local Python and formal tools:

```sh
uv venv --python python3.13 build/fedora-venv
uv pip install --python build/fedora-venv/bin/python cocotb==2.0.1
uv pip install --python build/fedora-venv/bin/python click==8.3.0 pytest==8.4.2
git clone https://github.com/YosysHQ/sby build/sby-source
git -C build/sby-source checkout b1a1e98cba941ec8433f8dc27f416cd7bb7f14be
make -C build/sby-source install PREFIX="$PWD/build/fedora-tools"
```

Yices is the solver used by the upstream BRAM proof recipes. Its official
[2.7.0 release](https://github.com/SRI-CSL/yices2/releases/tag/yices-2.7.0)
provides `yices-2.7.0-x86_64-pc-linux-gnu-static-gmp.tar.gz`; verify SHA256
`49566b6f817692820538df78fe406878400d79810631c9372b2495bc81d3e00a`
and extract with `--strip-components=1` into `build/fedora-tools`.

The expected programmer donor source includes pre-existing cable-driver changes.
The initializer continues to use its original loader. Its upstream XVC server
only supports FTDI/GPIO and needs both DLC10 selection and arbitrary TMS/TDI
shifting before Bonetto can use this cable.

Build an isolated source snapshot and apply the project-local
[`openfpgaloader-xpcu-xvc.patch`](../scripts/patches/openfpgaloader-xpcu-xvc.patch):

```sh
bash scripts/fedora-build-loader.sh
```

The helper pins donor revision `dafa7fcab2b96e927fd3108c3f33d1cc46117c8b`,
preserves its existing tracked changes, and snapshots it under
`build/openfpgaloader-source`. Its manifest hashes every staged file, the donor
changes and the XVC patch. Rerunning verifies the snapshot and refuses to
replace modified source. The shared donor checkout is untouched.

The patch adds the DLC10 constructor branch and adapts the upstream
`patches/openfpgaloader-xpcu-writetmstdi.patch` by Felipe Sens Bonetto. Its
state-aware shift method captures TDO in Shift-IR/Shift-DR, flushes navigation
clocks separately, and uses the Fedora driver's packing and TDO decoder. XVC
closes a connection when the shift fails instead of returning zero data,
reports the actual clock period, and stops when opening the server fails.
The native build retains Xilinx, DLC10 and both XVC roles, disables other
vendors, and uses `-O0` with two build jobs to reduce preparation time on this
busy host. Physical operation still needs the connected-board acceptance test.

## Reproducible preparation and hardware steps

Run the checks directly, because some upstream aggregate simulation recipes
ignore submake failures:

```sh
bash scripts/fedora-bringup.sh sim-bram
bash scripts/fedora-bringup.sh formal-bram
bash scripts/fedora-bringup.sh build
bash scripts/fedora-bringup.sh check
```

These check the current BRAM bring-up components and board utility benches.
They do not constitute all DDR3 simulation/formal gates or full-project CI.
The upstream Wishbone and BRAM formal recipes are bounded checks to depth 20;
the JTAG master and board utility checks use the configured depth-30 BMC/cover
tasks. The helper replaces Z3 with Yices for those two task files without
changing assertions or depth, and stores their work under `build/formal-*`.
It uses separate UART and JTAG-master simulation result files so one suite
cannot overwrite the other's XML. Preserve their outcomes and scope; a bounded pass is not an unbounded
inductive proof.

The integration bench now sweeps all 2,048 first-profile words and checks
both default-profile bank boundaries, bank isolation, byte masks, version,
address echo and read-data status registers. Unknown reset or completion
signals fail the bench. The serial BSCAN path remains outside this bench's
scope. Run the focused profile and unknown-signal rejection checks with:

```sh
python3 -m unittest discover -s tests -p test_jtag_bram_profiles.py -v
```

To inspect a BRAM image's file structure independently after a build:

```sh
python3 scripts/fedora-check-bitstream.py \
  --bit boards/ypcb-00338/build/bonetto_soc_ypcb00338_jtag_bram_first.bit \
  --fasm boards/ypcb-00338/build/bonetto_soc_ypcb00338_jtag_bram_first.fasm \
  --jtag-chain 1 --out build/fedora-first-bitstream-recheck.json
```

This checks the header, FPGA part and configuration ID, packet bounds,
frame-data presence, START/DESYNC and the selected FASM JTAG feature.
CRC, timing qualification and physical operation need separate evidence.

The helpers record checksums of the programmer, its patch and source manifest,
and the bitstream and its RTL, constraints and native tools. `check` and
`program` refuse changed artifacts. The build helper invokes upstream
synthesis and XDC generation for the first wrapper. Its
`build/fedora-bram-first-synthesis.json` receipt records source, Makefile and
pin-input hashes, expanded Make recipes, the Yosys binary and relevant build
environment. Missing or mismatched receipts force regeneration, including a
one-time rebuild of synthesis outputs created before this receipt existed.
Inputs that change during synthesis are rejected. Placement then uses seed 1
and a cached measured delay model. Routing resumes the saved placement and
random-generator state.
The checkpoint copy explicitly sets `router1`, because saved settings override
the command-line selection. The route-only run uses the backend's standard
delay estimator; it does not rerun the placement delay-matrix initialization.
The helper reuses a completed placement, route or strict frame stage only while
its recorded input and output checksums match. Routing records its actual command
and search setting. The assembler source and database are pinned to clean
revisions. It sends every FASM feature to the matching database,
without the upstream assembly filter or missing-feature opt-in. Its routing
deadline is 1,800 seconds; `BONETTO_ROUTE_TIMEOUT_SECONDS` can extend that
bound when the host is busy. `check` can succeed with a
disconnected cable, while clearly reporting that hardware remains untested.

The build uses the existing upstream XDC at 50 MHz without a timing-failure
waiver. Inspect the actual route report and FASM assembly outcome. nextpnr's
timing estimates do not establish Vivado-equivalent setup/hold, electrical DRC
or physical hardware behavior. No local board pass exists yet.

Attach the DLC10 to a powered board, then:

```sh
bash scripts/fedora-bringup.sh detect
bash scripts/fedora-bringup.sh program
bash scripts/fedora-bringup.sh xvc       # leave running in this terminal
```

In a second terminal:

```sh
bash scripts/fedora-bringup.sh validate
```

`detect` uses the established Fedora boot/helper/overlay initializer and
requires IDCODE `0x23751093`. `program` loads only FPGA SRAM; it does not write
BPI flash. `xvc` keeps the loader's stdin open without a background `tail`, at
the DLC10 driver's minimum 750 kHz. The validator requests the corresponding
1,334 ns period; the patched server reports the clock rate actually selected.
`validate` requires first-profile version `0xB07EB002`, eight vector readbacks
including the endpoints of both 4 KiB banks, decoder isolation, byte-select
writes and clean ACK/error status. It is not a full hardware memory sweep.
Its real hardware outcome is
the acceptance gate, not successful bitstream generation.
The helper preserves its output in a UTC-stamped
`build/fedora-hardware-bram-*.log` and retains failures as nonzero exits.

No cable was present on 2026-10-06. Fedora preparation logs are under `build/`
and the bitstream/route products are under `boards/ypcb-00338/build/`.
Any pending, failed or timed-out stage remains incomplete.
