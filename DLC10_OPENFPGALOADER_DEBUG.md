# DLC10 / openFPGALoader firmware-init handoff

Started: 2026-09-16; updated: 2026-09-17. Board: YPCB-00338 / XC7K480T. Cable: Xilinx Platform Cable USB II (DLC10). Host: Fedora 44, kernel `7.0.9-205.fc44.x86_64`.

## Fedora answer: source fix versus working procedure

**Latest Python cold-start test (2026-09-17): PASSED.** Physical replug was confirmed as `03fd:0013`, bus 001 device 048. Running `bash dlc10-init.sh` directly, without fxload or Vivado, transitioned to `03fd:0008` device 049 and detected `status 43`, IDCODE `0x23751093`, XC7K480T, IR length 6; wrapper exit 0. Logs: `/tmp/dlc10-init.dys11v/{boot,overlay,detect}.log`. This verifies one complete cold cycle with the current Python usbfs implementation. Earlier failures remain unexplained; this result does not establish that the transport change caused recovery. The comparisons below are historical.

**Latest controlled comparison (2026-09-17): reference cold start PASSED; Python warm reload PASSED.** Confirmed physical replug as `03fd:0013`, bus 001 device 046. Reference boot upload followed by `ref/fxload/fxload -v -t fx2 -D /dev/bus/usb/001/047 -s ref/fxload/a3load.hex -I firmware/xusb_xp2-overlay.hex` produced `status 43`, IDCODE `0x23751093`, XC7K480T, detection exit 0. Logs: `/tmp/dlc10-fxload-cold.GZiATu/`. Running the current Python `bash dlc10-init.sh` on that working runtime state also passed with the same status and IDCODE; logs: `/tmp/dlc10-init.kocFSd/`. Python can therefore reload an already working cable, but this does not establish reliable Python cold initialization or explain the preceding failures. Another fresh physical replug is needed to test the current Python implementation independently of fxload.

**Latest Python test (2026-09-17): FAILED final JTAG detection.** Following a physical replug at `03fd:0013` device 043, the wrapper reached `03fd:0008` device 045. The revised Python helper uses direct Linux `USBDEVFS_CONTROL` ioctls, matching fxload's transport, and completed all 10 helper A0, 28 external A3, and 74 internal A0 requests. Firmware version was `6109`, but status remained `00` and IDCODE was zero. Logs: `/tmp/dlc10-init.PiDSY5/`. Running reference fxload on that same warm state also completed but did not restore detection (`/tmp/dlc10-fxload-comparison.log`). This does not prove a Python-specific failure or validate the replacement. The next discriminating test needs a fresh replug with reference fxload, with board power and JTAG connection checked. Current patch files are experimental, not ready for a success claim or upstream PR.

The upstream `openFPGALoader` cold firmware path is **not fixed yet**. Its existing `--probe-firmware` implementation accepts one HEX file, asserts CPUCS, sends every record with A0, releases CPUCS, and waits for `03fd:0008`. That is sufficient for cables whose HEX is a single internal-RAM image. This YPCB cable needs a staged sequence: reference boot image through A0, re-enumeration, `a3load.hex` helper, then the runtime overlay split between A3 external-memory writes and A0 internal-memory writes. Adding that behavior is a protocol/API change, not a ten-line edit.

The tested Fedora solution is a wrapper, not a modified upstream driver. `dlc10-init.sh` runs the existing openFPGALoader binary for the boot image and final JTAG scan, and uses `ref/inspur-adventures/scripts/xpcu_stage2.py` for the helper/overlay stage. That Python helper uses Linux usbfs control transfers and does not require the `fxload` executable. `dlc10-fedora-wrapper.patch` adds both files; it does not embed the proprietary HEX files. It expects the paths and SHA-256-checked files documented below. The Python replacement has now passed both warm reload and one physical cold-start detection test.

No PR has been opened. A PR for a ten-line change would be misleading because the ten-line candidate concerns macOS bulk-read behavior, not this Fedora cold-start failure. The appropriate upstream contribution would first need an agreed interface for selecting a boot image, helper, and overlay (and a decision about the proprietary helper firmware); until then, the wrapper is the verified Fedora solution.

## Verified non-Vivado result and runnable procedure

**Scope clarification:** this verifies a non-Vivado Fedora workflow; it does not mean the upstream single-image openFPGALoader firmware path has been fixed. The local openFPGALoader source changes in this worktree add diagnostics and strict transfer/error checks only. The working cold-start command is a wrapper: openFPGALoader loads the matching boot image, the Python usbfs helper loads the A3 helper plus runtime overlay, and the unchanged openFPGALoader JTAG path performs the final detection.

No USB packet replay was used. `dlc10_usb_trace.so` intercepted Vivado's libusb calls only to record request addresses, lengths, return codes, and payload hashes; it never replayed packets and did not capture firmware payload bytes. The non-Vivado sequence sends staged Intel-HEX files through libusb in openFPGALoader and Linux usbfs ioctls in the Python helper.

**A complete manual cold-start sequence succeeded without Vivado.** After the user replugged, the cable was `03fd:0013`, bus 001 device 034; no `hw_server` or XSDB was running.

1. openFPGALoader loaded `firmware/xusb_xp2-boot.hex` via A0. The cable became `03fd:0008`, device 035, reporting FX2 version `fc08`. Its immediate JTAG scan returned zero (`TDO is stuck at 0`). A later scan at device 036 returned a bulk overflow. Thus boot firmware fixes re-enumeration but was insufficient for a working JTAG scan in these tests. Log: `/tmp/dlc10-openfpgaloader-boot-cold.log`.
2. After resolving the current USB node (it changed again to device 036), `ref/fxload/fxload -v -t fx2 -D /dev/bus/usb/001/036 -s ref/fxload/a3load.hex -I ${VIVADO_INSTALL_ROOT}/data/xicom/xusb_xp2.hex` returned zero. Log: `/tmp/dlc10-fxload-overlay.log`. An earlier attempt targeting the vanished device 035 failed before opening the device; no upload occurred on that attempt.
3. openFPGALoader then reported FX2 version `6109` and detected **`0x23751093`, `xc7k480t`, IR length 6**, exit zero. No Vivado process was used during this cold cycle. The same generic helper that failed from cold worked after the proper boot image.

Run the packaged Fedora sequence from this directory:

```sh
bash dlc10-init.sh
```

The script verifies firmware hashes, refuses multiple matching cables or running cable tools, uploads the boot image when at `0013`, waits for the `0008` USB node to settle, loads the overlay through the Python A3 helper, and requires successful detection of `0x23751093`. It saves per-stage logs under a new `/tmp/dlc10-init.*` directory. It only writes cable RAM and performs JTAG detection; it does not program FPGA configuration, board flash, or cable EEPROM. It does not launch or depend on an installed Vivado executable. The companion `dlc10-fedora-wrapper.patch` is a packaging patch that adds the wrapper and helper; it is not a patch to the upstream openFPGALoader driver.

The overlay has been copied locally to `firmware/xusb_xp2-overlay.hex` (SHA-256 `f551e3c71efee0556b465dc9975d528115f9849ea143f51b5c44d6f3f4f4a9cf`). Both boot and overlay images remain vendor firmware; the host tools are open source. Do not confuse an open host solution with open-source cable firmware.

Verification scope: syntax and patch-application checks passed. The earlier complete wrapper cold run in `/tmp/dlc10-init.0hKMWy/` used fxload. The Python replacement emits 10 helper A0, 28 external A3, and 74 internal A0 requests and passed a physical cold cycle in `/tmp/dlc10-init.dys11v/`. No hw_server or XSDB was running. An independent earlier `xc3sprog -c xpc -j` also detected `0x23751093`, XC7K480T, IR length 6.

These runs verify cable initialization and JTAG detection, not FPGA/flash programming. The current wrapper targets Fedora/Linux and uses usbfs for the Python helper; Bash alone cannot issue these vendor control transfers.

## Latest finding: boot firmware versus runtime overlay

**The firmware filename alone was misleading.** The installed `data/xicom/xusb_xp2.hex` is not the image Vivado first uploads to the cold cable. The firmware URL in `ref/inspur-adventures/Makefile` provides a different image that matches **all 177 initial boot-upload packets** in the new Vivado trace (address, length, and FNV-1a payload hash).

The reference boot image is now staged at `${YPCB_ROOT}/firmware/xusb_xp2-boot.hex`: 23,542 file bytes, 7,962 data bytes, highest address `0x1f87`, SHA-256 `4fe1a679efcc7ed7c01e738beaf29d8a1f1201731780dfc026f724a88aee527a`. Source: <https://raw.githubusercontent.com/bwhite/fpga-image-registration/master/edk_project/install_drivers/linux_drivers/pcusb/xusb_xp2.hex>. It is vendor firmware from the reference mirror, not newly open-source firmware.

The earlier two-stage-only hypothesis below is incomplete. On a confirmed physical replug to `03fd:0013` (bus 001 device 031), `fxload -t fx2 -s ref/fxload/a3load.hex -I ${VIVADO_INSTALL_ROOT}/data/xicom/xusb_xp2.hex` returned zero and reported 8,605 firmware bytes written, including 28 external writes, but the cable stayed `0013`. Full output: `/tmp/dlc10-fxload-cold-init.log`. No short-write/error messages occurred. A subsequent openFPGALoader detection attempt without an explicit firmware path failed on its missing default firmware file, before any firmware upload.

Vivado then recovered that failed state to `03fd:0008` (device 033). The complete, file-backed trace at `/tmp/dlc10-vivado-recovery-init.log` contains this sequence; it is a **recovery trace after fxload**, not an untouched cold-plug trace:

1. CPUCS hold; 177 A0 writes totaling 7,962 bytes at `0x0000..0x1f87`; CPUCS run. All packets match `firmware/xusb_xp2-boot.hex`.
2. CPUCS hold; 54 dense A0 blocks totaling 3,456 bytes at `0x0000..0x0d7f`; CPUCS run. This helper is not yet identified by payload comparison.
3. 28 A3 writes totaling 523 bytes at `0x2000..0x220a`, all matching installed `data/xicom/xusb_xp2.hex`.
4. CPUCS hold; 166 A0 writes totaling 8,082 bytes below `0x2000`, all matching the same installed firmware; CPUCS run.

Every captured synchronous firmware transfer returned its requested length. After stopping our `hw_server`, openFPGALoader again detected `0x23751093`, `xc7k480t`, IR length 6. No FPGA bitstream, board flash, or cable EEPROM was written.

The xc3sprog [Readme.DLC10](https://sources.debian.org/src/xc3sprog/0%2Bsvn795%2Bdfsg-3/Readme.DLC10) independently describes loading an initial firmware version and then a later version. The local `hw_server` binary also contains names `xusb_xp2_boot_hex`, `xusb_xp2_overlay_hex`, and `Vend_Ax_Fx2`. Together with the packet comparison, this supports a boot-image/runtime-overlay distinction rather than a universal requirement to add A3 to openFPGALoader cold loading.

**Boot-only test command (now executed; re-enumeration succeeded, JTAG required the overlay):**

```sh
./openFPGALoader/build-xpcu-debug/openFPGALoader \
  --cable xilinxPlatformCableUsb \
  --probe-firmware ${YPCB_ROOT}/firmware/xusb_xp2-boot.hex \
  --freq 500000 --detect --verbose-level 2
```

The verified full boot-plus-overlay sequence is recorded above. Boot-only loading achieved the USB transition but did not produce a successful JTAG scan. The sections below preserve the earlier investigation and superseded hypotheses for reference.

## Observed behavior on this host

1. After a physical USB replug, `lsusb -d 03fd:` reported `03fd:0013` (pre-firmware cable). No `hw_server` or XSDB process was running.
2. With openFPGALoader v1.1.1 (`openFPGALoader/build/openFPGALoader`), this read-only detection command failed:

   ```sh
   ./openFPGALoader/build/openFPGALoader \
     --cable xilinxPlatformCableUsb \
     --probe-firmware ${VIVADO_INSTALL_ROOT}/data/xicom/xusb_xp2.hex \
     --freq 6000000 --detect --verbose
   ```

   It printed `Loading firmware: 100.00%`, `Done`, then waited 100 seconds for `Waiting reload` and ended with `FX2: fail to open device` / `JTAG init failed with: lowlevel init failed`. `lsusb` still reported `03fd:0013` at the end. There was no JTAG scan or FPGA configuration. The progress bar only indicates that the software loop completed; the original source did not verify the exact number of bytes accepted by each USB control write or read the FX2 RAM back.
3. Without another physical replug, starting Vivado Lab 2026.1.1 `hw_server` and asking XSDB to enumerate targets changed the USB ID to `03fd:0008` (operational cable). A later libusb trace exposed the important low-level difference; see below.
4. After stopping `hw_server`, the same openFPGALoader binary detected the FPGA immediately through the initialized cable: one device, `0x23751093`, `xc7k480t`, IR length 6. This isolates the failure to cable initialization/re-enumeration, not openFPGALoader's subsequent JTAG scan. No bitstream or flash was written during these checks.

Firmware file: `${VIVADO_INSTALL_ROOT}/data/xicom/xusb_xp2.hex`, 24,830 bytes, SHA-256 `f551e3c71efee0556b465dc9975d528115f9849ea143f51b5c44d6f3f4f4a9cf`. It contains 634 Intel HEX data records and one EOF record.

## Instrumented cold-plug result

The separate debug build was run against a fresh `03fd:0013` cable with `--verbose-level 2`. It parsed `xusb_xp2.hex` into 101 sections / 8,605 firmware bytes. All 196 logged `0xA0` OUT transfers returned their exact requested lengths (194 data writes plus CPUCS hold/run), using 100 ms timeouts. Nevertheless, the device remained `03fd:0013` until the 100-second poll expired. Thus the immediate failure was **not** a libusb error or short write.

The reference standalone loader (`ref/inspur-adventures/scripts/xpcu_descriptor.py`) was also run from fresh `0013` with strict length checks and a 1,000 ms timeout. It likewise remained `0013`. Its optional `--verify-firmware` test successfully read back all 8,605 bytes through the `0xA0` aperture while the FX2 CPU was held in reset, using aligned `0xA0` IN reads. This rules out a simple write/timeout problem; it does **not** prove that external memory was populated as Vivado populates it through `0xA3`. (Odd-address A0 IN reads on this device rounded down to the prior even address, so verification was changed to aligned reads.)

## Vivado USB trace: key difference

An `LD_PRELOAD` libusb tracer (`dlc10_usb_trace.c`) captured a successful Vivado `hw_server` cold initialization that changed `03fd:0013` to `03fd:0008` and exposed `xc7k480t` to XSDB. The tracer records request metadata and FNV-1a hashes, **not firmware payload bytes**. It had to wrap `dlsym()` because `hw_server` resolves libusb through an explicit library handle. The first capture was output-truncated, so it is evidence of the following steps, **not yet a complete packet list**:

```text
OUT A0 E600 len=1 data=01              # hold FX2 CPU
OUT A0 0000 len=64 hash=536991b3     # first stage, dense 64-byte blocks
... A0 blocks through address 0D40 ...
OUT A0 E600 len=1 data=00              # run first-stage loader
OUT A3 2022 len=31 hash=2f7f7760    # xusb_xp2.hex external-memory record
OUT A3 20E7 len=20 hash=cd53d306    # another matching HEX record
... more A3 records ...
OUT A0 E600 len=1 data=01              # hold CPU again
... middle/final packets not captured completely ...
```

The `0xA3` data hashes matched those of the corresponding `xusb_xp2.hex` records. Vivado's first-stage image **has not been identified**: its first 64-byte hash did not match dense blocks from the local `xusbdfwu.hex`, `xusb_xup.hex`, or `xusb_xp2.hex` candidates. Do not assume one of those files is the first-stage loader. Also do not infer the exact final CPU release from the truncated trace.

Infineon's [FX2LP boot application note](https://www.infineon.com/dgdl/Infineon-AN50963_EZ-USB_FX1_FX2LP_Boot_Options-ApplicationNotes-v13_00-EN.pdf?fileId=8ac78c8c7cdc391c017d072418a1482a), section 3.1.2, documents this two-stage pattern: ROM request `0xA0` accesses only internal memory; a first-stage Vend_ax loader implements `0xA3` for external-memory reads/writes. The `0x2000` split is part of that loading algorithm. This is a strong explanation for why writing every record through `0xA0` can return exact lengths/read back internal RAM yet fail to produce operational firmware.

The tracer has now been rebuilt with output limited to `0xA0`/`0xA3` and USB resets, ready for one **complete** capture from a clean physical replug. Capture the entire `0013→0008` sequence if the independent `fxload` test below fails, identify the first-stage image and final CPUCS writes, then implement a targeted two-stage loader. **Do not blindly replay all Vivado USB traffic**: most later packets are ordinary JTAG operations, and raw replay may depend on USB state/timing.

For that capture, first physically replug the DLC10 and confirm `lsusb -d 03fd:0013`. With no other `hw_server` running, start this in one terminal (the log file is generated diagnostic output, not a firmware dump):

```sh
LD_PRELOAD=${YPCB_ROOT}/dlc10_usb_trace.so \
  ${VIVADO_LAB_ROOT}/bin/hw_server \
  -L- -ldiscovery,jtag2 > /tmp/dlc10-vivado-cold-init.log 2>&1
```

Then, in another terminal, trigger target discovery and verify re-enumeration:

```sh
${VIVADO_LAB_ROOT}/bin/xsdb \
  -eval 'connect; targets'
lsusb -d 03fd:0008
```

Stop `hw_server` with Ctrl-C after the `0008` and target result are recorded. Keep the full `/tmp/dlc10-vivado-cold-init.log`; display only a filtered excerpt in chat if it is large.

## Local diagnostic code

The local `openFPGALoader/src/fx2_ll.cpp` now logs the following at `--verbose-level 2`:

- matching USB VID:PID plus bus/address before upload and every ~10 seconds while waiting for re-enumeration;
- parsed HEX section/byte counts;
- CPUCS reset assertion/release (including `data=01` / `data=00`) and each FX2 `0xA0` firmware control-write address, requested length, actual returned length, and 100 ms timeout;
- USB devices remaining after a timeout.

It also treats a short USB control write or HEX parse failure as an error instead of silently proceeding, and removes a misleading `reset()` error message that passed a boolean-style result to `libusb_error_name()`. This local source **already checked** `if (!load_firmware(...))` before the 100-second poll; it did not ignore the loader's return value. The XPCU driver passes its verbose level into the FX2 loader. These diagnostics were exercised in the cold-plug result above; the cable is currently initialized as `03fd:0008`.

The separate `build-xpcu-debug` binary compiled successfully. A safe test against the already-initialized cable printed `FX2 USB before firmware: 03fd:0008 bus=1 address=23` and detected the one FPGA with raw IDCODE `0x23751093`. At a requested 500 kHz, this driver selected 750 kHz actual JTAG frequency. This verifies the diagnostic binary's post-init path, **not** its cold firmware-upload path.

The existing `build/` directory was configured at a former source path and could not be rebuilt in place, so the diagnostic binary was built separately with:

```sh
cmake -S openFPGALoader -B openFPGALoader/build-xpcu-debug \
  -DCMAKE_BUILD_TYPE=Debug -DENABLE_OPTIM=OFF \
  -DPKG_CONFIG_EXECUTABLE=/usr/bin/pkg-config \
  -DENABLE_CABLE_ALL=OFF -DENABLE_VENDORS_ALL=OFF \
  -DENABLE_XILINX_PLATFORM_CABLE_USB=ON -DENABLE_XILINX_SUPPORT=ON
cmake --build openFPGALoader/build-xpcu-debug -j4
```

For a repeat of the openFPGALoader cold test, on a **physical cable replug**, before starting Vivado, run:

```sh
lsusb -d 03fd:
./openFPGALoader/build-xpcu-debug/openFPGALoader \
  --cable xilinxPlatformCableUsb \
  --probe-firmware ${VIVADO_INSTALL_ROOT}/data/xicom/xusb_xp2.hex \
  --freq 500000 --detect --verbose-level 2
lsusb -d 03fd:
```

Expected successful transition: `03fd:0013` to `03fd:0008`, then IDCODE `0x23751093`. The current all-`0xA0` path did **not** achieve that transition. Do not infer a firmware checksum from the `100%` progress bar.

Interpret the new log as follows:

| Observation | Next inference/action |
| --- | --- |
| Any `actual < 0` or `actual < expected` | Record the first failing request/address; the previous code could hide short writes. |
| All transfers exact, including `CPUCS=RUN`, but `0013` remains | Observed. Standalone all-`0xA0` loader and full internal-RAM readback were tried; compare with Vivado's two-stage `0xA0`/`0xA3` upload. |
| `0013` disappears and `0008` appears, but openFPGALoader still fails | Investigate re-enumeration/open timing or later XPCU USB calls. |
| `0008` appears and `0x23751093` is detected | Cold initialization succeeded with this build; repeat to check reliability. |

## What `ref/inspur-adventures` says

Its `README.md`, `Makefile`, and `flake.nix` describe a macOS arm64 openXC7 flow for the YPCB-00338. The Makefile uses `--cable xilinxPlatformCableUsb --probe-firmware firmware/xusb_xp2.hex`, claims the firmware is auto-loaded on each plug-in, and retries detection up to 10 times at 500 kHz. Its Nix build pins a post-0.12.1 openFPGALoader commit and applies four macOS USB patches: small bulk-read bounce buffer, 1-second/retry control transfers, clearing halted bulk endpoints, and skipping an absent alternate interface setting. The bounce-buffer, clear-halt, and alternate-setting patches target post-re-enumeration/JTAG problems. The generic control-transfer timeout patch was motivated by a post-init GPIO timeout on macOS, but it **also affects firmware `0xA0` writes**, so it should not be categorically excluded as a Fedora factor.

`ref/inspur-adventures/scripts/xpcu_descriptor.py` contains a standalone firmware loader using the same all-`0xA0` / `CPUCS=1` / firmware writes / `CPUCS=0` sequence, with a 1000 ms timeout and strict `rc == len(payload)` checks. It was run and failed to re-enumerate this cable; its new optional readback mode confirmed the internal-RAM bytes. Therefore the reference script is not a working cold-init recipe for this particular firmware/cable state.

The reference Makefile adds `--misc-device 0x10931093,8,inspur_cpld`. **Do not copy that option for this board without evidence:** our live cable scan after Vivado initialization found only one device (`0x23751093`). The reference is useful but may describe a different card or JTAG chain revision.

## Alternative-tool triage

On 2026-09-17, Fedora's `libftdi-devel` and `libusb-compat-0.1-devel` were present. `xc3sprog` was built from the temporary `matrix-io/xc3sprog` checkout (commit `f4bebd0`) without system-wide installation, using `-DUSE_WIRINGPI=OFF -DUSE_FTD2XX=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5` and explicit include/library paths for Fedora's `libftdi1` and `libusb-0.1` compatibility library. Its cable/device databases include `xpc` (`03fd:0008`) and `XC7K480T`. With the Vivado-initialized cable at `03fd:0008` and `hw_server` stopped, this **read-only** scan succeeded:

```text
$ /tmp/ypcb-xc3sprog.WKKMtQ/build/xc3sprog -c xpc -j
JTAG loc.:   0  IDCODE: 0x23751093  Desc: XC7K480T Rev: C  IR length: 6
```

This independently corroborates the post-init DLC10/JTAG/FPGA path. It does **not** test the failing `03fd:0013` cold-init path, because `xc3sprog` requires an initialized `03fd:0008` cable. The binary remains in a temporary build directory, not on the system `PATH`.

The `fxload` used here is **not** `mbed-ce/fxload`: it is the locally built `${YPCB_ROOT}/ref/fxload/fxload` from the `esden/fxload` repository, commit `092d9b11f8881c6bf5a1b55288f07adf26d5ec0e`, without system installation. Its upstream [README](https://github.com/esden/fxload) describes the included `a3load.hex` and the second-stage external-memory case. `ref/fxload/a3load.hex` has SHA-256 `5f27f666e408512b4e7ba6d53bee89410b31e4cb9f7c27930dfa3db65ab2a240`. The cold two-stage attempt with the runtime overlay alone failed to re-enumerate; the later overlay upload after the correct boot image succeeded and is recorded above.

**Correction from source inspection:** use `-t fx2` for this experiment, not the previously proposed `-t fx2lp`. In `ref/fxload/ezusb.c`, `fx2_is_external()` splits code memory at `0x2000`, whereas `fx2lp_is_external()` splits at `0x4000`. The latter would classify Vivado's observed `A3 2022` and `A3 20E7` writes as internal and send them through A0. Choosing `fx2` reproduces the observed memory split; it does not establish the physical chip model. Both modes use CPUCS `0xE600`.

On resuming, the cable was `03fd:0008`, bus 001 device 030, with no `hw_server` or XSDB running. A physical replug was requested before the staged cold test. `ref/xpcu-macos/README.md` was also inspected: its overflow and alternate-interface workarounds address post-init USB behavior and provide no two-stage cold-init implementation.

## Historical two-stage test plan (now executed; did not initialize cable)

1. **Staged and exercised:** executable `${YPCB_ROOT}/ref/fxload/fxload` and loader `${YPCB_ROOT}/ref/fxload/a3load.hex`.
2. Physically replug **only the DLC10 USB cable** and confirm `lsusb -d 03fd:0013`. Stop `hw_server` and any other process using the cable. Note the bus/device numbers reported by `lsusb`, which give `/dev/bus/usb/BBB/DDD`.
3. Run a **volatile FX2 RAM** download, substituting the staged paths and the actual USB device node:

   ```sh
   ${YPCB_ROOT}/ref/fxload/fxload -v -t fx2 \
     -D /dev/bus/usb/BBB/DDD \
     -s ${YPCB_ROOT}/ref/fxload/a3load.hex \
     -I ${VIVADO_INSTALL_ROOT}/data/xicom/xusb_xp2.hex
   ```

   **Do not add `-c`**: that option selects EEPROM programming in this `fxload` interface. Do not run an all-`0xA0` load again as a substitute for `-s`.
4. Check `lsusb -d 03fd:`. If it became `03fd:0008`, stop there and run the read-only `/tmp/ypcb-xc3sprog.WKKMtQ/build/xc3sprog -c xpc -j`; expected IDCODE is `0x23751093`. This would validate an independent two-stage cold loader. Then implement the same *protocol* in openFPGALoader and repeat across cold replug cycles.
5. If it does **not** become `0008`, record the first `fxload` error and USB ID. A failure would not disprove the two-stage hypothesis: the generic loader might not match this cable. Physically replug the DLC10 again to start clean at `0013`, then run the filtered Vivado capture above and compare the complete successful sequence.

This test writes only the DLC10's volatile FX2 RAM. It does not configure the FPGA, program board flash, or modify the DLC10 EEPROM.

## Current conclusion

The failure involved two distinct firmware roles under the same original filename. The installed Vivado data image did not cold-initialize the cable, even with a generic A3 helper. The `ref/` boot image initialized USB successfully; following it with the generic helper and installed runtime overlay produced a working JTAG scan without Vivado. The Fedora host solution is packaged in `dlc10-init.sh` and verified across two physical cold-start cycles, including a complete wrapper run. Upstream openFPGALoader still has no direct boot/helper/overlay mode for this cable; implementing that would require a larger protocol-aware change and a deliberate firmware-file interface. No upstream PR has been opened.

Infineon documents vendor request `0xA0` as supporting both reads and writes of FX2 internal RAM: <https://community.infineon.com/t5/Knowledge-Base-Articles/Read-and-Write-to-EZ-USB-Internal-Memory-AN21xx-FX-FX1-FX2-FX2LP/ta-p/259431>.
