# YPCB Linux workspace tooling

This repository holds shared YPCB-00338/DLC10 scripts, source patches and
workspace documentation. The active accelerator is a separate repository at
`~/openTPU`, intended for `github.com/allbilly/openTPU`. This tooling repository
is intended for `github.com/allbilly/ypcb`.

Commands in the shared tooling documentation use `YPCB_ROOT` for this clone,
and `VIVADO_ROOT`, `VIVADO_LAB_ROOT` or `VIVADO_INSTALL_ROOT` for installations
you select. Set `YPCB_ROOT="$(pwd)"` from this repository root. Python tool
helpers discover their checkout from their own file and accept environment
overrides; no developer username is embedded in their paths.

```text
~/openTPU/                 active accelerator checkout
~/ypcb/
  dlc10-init.sh            legacy staged USB initialization and JTAG detection
  DLC10_OPENFPGALOADER_DEBUG.md
  dlc10-*.patch           local openFPGALoader changes
  dlc10_usb_trace.c       USB trace interposer source
  smt2_tdo_loopback.cpp   diagnostic source
  openFPGALoader/         independent clone, excluded here
  ref/                   existing independent reference clones, excluded here
  projects/              former secondary project checkouts, excluded here
  local-overrides/       source changes for locally modified independent clones
  repositories.json      source URLs, revisions and captured changes
  firmware/              locally supplied cable firmware, excluded here
  migration-receipts/     local migration audit and recovery copies, excluded here
```

The legacy `~/ypcb_ref` path is a compatibility symlink to `~/ypcb/projects`.
Its `openTPU` entry points to `~/openTPU`. Preserve these aliases for old build
receipts and virtual-environment launchers. Current source and documentation
use the canonical paths above. The linked OpenTPU worktree was repaired after
the move; all original clones and their local changes were preserved.

## What is versioned

Shared scripts, source patches, documentation and source-only local overrides
are versioned. Independent repositories, firmware blobs, waveform captures,
compiled programs and migration recovery archives stay local. This repository
does not vendor or publish the cable's proprietary firmware.

`repositories.json` records each independent checkout's origin URL and exact
HEAD. For dirty checkouts, `local-overrides/<name>/tracked.patch` captures
tracked changes and `local-overrides/<name>/files/` captures untracked source
files. See [local overrides](local-overrides/README.md) before restoring them.
OpenTPU has its own commit and remote rather than an override copy here.

## FPGA and host setup

The legacy DLC10 initializer expects the independent `openFPGALoader` clone,
`ref/inspur-adventures/scripts/xpcu_stage2.py`, `ref/fxload/a3load.hex` and the
firmware files whose hashes it checks. Its historical validation is in
`DLC10_OPENFPGALOADER_DEBUG.md`. The latest permanent programming used native
Vivado's cable driver; avoid concurrent cable programs.

The current CH1-only PCIe FPGA image was written to NOR, verified separately
and booted through a JTAG boot request. Cold boot and PCIe inference remain a
separate test. The Linux PCIe host needs the matched XDMA driver and runtime;
normal use does not require Vivado or JTAG there.

Use `~/openTPU/docs/bitstreams.md` for bitstream locations and verified status,
and `~/openTPU/docs/permanent_pcie_ch1.md` for installation and LFM2 commands.
The local `~/openTPU/build/fedora-vivado/ch1-pcie-flash-host-20261015.tar`
contains the matched host/compiler/model/calibration data for transfer to the
other PC. Generated FPGA builds and model checkpoints are outside Git.
