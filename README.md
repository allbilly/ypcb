# YPCB Linux workspace tooling

Shared tools, source overrides and a project index for the Inspur
YPCB-00338-1P1 / XC7K480T board and DLC10 cable. The SoC and accelerator
implementations live in independent repositories; this repository keeps their
locations and evidence boundaries visible.

## Project index

The [YPCB project inventory](docs/PROJECTS.md) covers **13 local SoC and
accelerator projects**, plus upstream copies, board references and supporting
tools. It was refreshed from the home workspace on **2026-10-23**. The
[machine-readable snapshot](docs/project-inventory.json) records checkout
identities and inspected evidence. Local changes are common, so a Git HEAD
alone does not identify the tested hardware sources.

| Project group | Start here | Recorded state |
| --- | --- | --- |
| Full accelerator stacks | `~/openTPU`, `~/KohakuTPU` | OpenTPU fixed-clock releases retained; runtime-clock effort abandoned. Kohaku reset/CDC fixes prepared, native rebuild pending. |
| GPGPU and Minion compute | `~/vortex`, `~/etsoc` | Exact older images have physical JTAG/DDR/compute evidence; newer images and physical PCIe have separate gates. |
| Small compute demonstrations | `~/tiny-tpu`, `~/tiny-gpu`, `~/verigpu` | tiny-tpu has a 150 MHz XOR board test; tiny-gpu and VeriGPU have historical offline candidates. |
| Neural accelerators | `~/LPULite`, `~/soDLA`, `~/somnia`, `~/rknpu-fpga` | LPULite has a qualified offline Vivado image; soDLA/Somnia have openXC7 candidates; RK-NPU full CMAC preparation has no accepted bitstream. |
| Board/SoC baselines | `~/bonetto-soc`, `projects/ypcb_00338_1p1_hack` | Bonetto BRAM/JTAG preparation and TiferKing MicroBlaze/DDR diagnostics; neither establishes a completed local full-DDR SoC test. |

These are saved results inspected offline, not a fresh board test or a claim
about the image currently running on the card. See the inventory for exact
receipts, limitations and project-specific stop/pause instructions.

## Workspace layout

```text
~/openTPU/                 independent accelerator checkout
~/bonetto-soc/             independent Bonetto checkout
~/KohakuTPU/, ~/vortex/…   other independent project checkouts
~/ypcb/
  dlc10-init.sh            staged cable initialization and JTAG detection
  DLC10_OPENFPGALOADER_DEBUG.md
  docs/                   current project inventory and review results
  local-overrides/        versioned source overlays for independent clones
  repositories.json      pinned restoration bases and overlay hashes
  openFPGALoader/         independent loader clone, ignored here
  ref/                   board references and cable dependencies, ignored
  projects/              secondary checkouts and linked worktree, ignored
  firmware/              locally supplied proprietary firmware, ignored
  build/                  local runtime locks/output, ignored
  migration-receipts/     historical recovery material, ignored
```

The current workspace has no `~/ypcb_ref`, `projects/openTPU`, or
`projects/bonetto-soc` compatibility entry. Use the real paths in the inventory.
The registered `projects/openTPU-upstream-e15b4a44` linked worktree and separate
`~/upstream_openTPU` reference clone are distinct from `~/openTPU`.

## Shared tools and restoration

Set `YPCB_ROOT="$(pwd)"` from this repository root. Tool installation overrides
include `VIVADO_ROOT`, `VIVADO_LAB_ROOT` and `VIVADO_INSTALL_ROOT`; see each
project's instructions before invoking a build or hardware command.

The DLC10 initializer needs the independent `openFPGALoader` clone,
`ref/fxload/a3load.hex`, the tracked stage2 helper and locally supplied firmware
whose hashes it checks. Read [the DLC10 guide](DLC10_OPENFPGALOADER_DEBUG.md)
for prerequisites and the historical cold/warm initialization evidence.
Initialization writes cable RAM and scans JTAG; it is not an offline check.

[`repositories.json`](repositories.json) preserves the original restoration
bases. Its revisions are not a live project inventory. See
[local overrides](local-overrides/README.md) to reconstruct a clean checkout
with the reviewed source overlays. Build artifacts, firmware, models, waveform
captures and independent Git histories are not included. OpenTPU and the other
home projects need their own source and artifact handoffs.

The [review record](docs/REVIEW.md) lists the tooling fixes and offline checks
performed with this inventory refresh. No FPGA build or hardware operation is
part of that review.
