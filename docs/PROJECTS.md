# YPCB SoC and accelerator inventory

Observed **2026-10-23 (Asia/Hong_Kong)** from the local home workspace. This
index covers 13 project implementations, their reference copies and useful
support repositories. The accompanying [JSON snapshot](project-inventory.json)
records full Git revisions, local-change status and hashes of the inspected
status/evidence files. Paths beginning with `~/` refer to the workspace owner's
home; other paths in a project row are relative to that project's checkout.

This was a read-only survey of independent projects. Source and stored receipts
were inspected; no FPGA implementation, programming, inference or board test
was run. A receipt describes its exact historical sources and image. It does
not qualify later working-tree edits, another board, or the current SRAM/flash
contents. OpenXC7 frequency estimates are separate from full device timing
signoff. USB enumeration, IDCODE and INIT/DONE are separate from computation.

## Project map

| Project and location | Implemented scope | Recorded result and remaining boundary | Start with |
| --- | --- | --- | --- |
| **OpenTPU** — `~/openTPU` | Full accelerator, compiler/runtime, dual DDR channels and JTAG/PCIe paths | Fixed-clock `c0182800`/`c0182863` artifacts and recorded local JTAG/TinyStories and Mac LFM/Qwen results remain preserved. The `c01848` runtime-clock effort was **abandoned on October 22**; latest `c0184812` passed source/synthesis/model checks but was never admitted to P&R and has no bitstream. Compiled `c0182863` retains later-discovered Gray-counter/pending-count reset corners despite its historical LFM/Qwen passes. Do not revive the abandoned effort from an old resume table. | `HANDOFF.md`, `docs/bitstreams.md`, `docs/mac_c0182800.md`, `docs/mac_c0182863.md`, `tools/ypcb.py` |
| **KohakuTPU** — `~/KohakuTPU` | Full RV64/mesh/matrix/vector accelerator with DDR and both host paths | October 21 snapshot is `PREPARED_NO_VIVADO`: 165 frozen files and 69 board-tool tests. Previous reset-isolated routing failed with 41,092 overlaps. Earlier AltSpread image passed offline checks and SRAM configuration, but PCIe PERST held the memory/debug clock path in reset. New reset/CDC source needs fresh synthesis; DDR, compute and FPGA inference remain unqualified. Work is paused. | `progress.md`, `boards/ypcb-00338/README.md` |
| **Vortex** — `~/vortex` | RISC-V GPGPU, CH1 DDR, JTAG/PCIe transport and Blackwell-like tensor profile | Preceding frozen image passed **53 physical command checks** and a **457-check completion audit**, including all five basic example scripts, 21 study cases and 22 format/shape cases. The newer reset/PIO/LR-SC work has separate qualification; its physical queue was unarmed in the inspected state. Physical PCIe, full-capacity DDR soak and complete external DDR I/O timing are not established by that audit. | `progress.md`, `hw/syn/xilinx/ypcb/`, `examples/README.md`, `build_ypcb_blackwell_fixed32/goal-state.json` |
| **ET-SOC / CORE-ET** — `~/etsoc` | Single Minion/VPU FPGA integration with CH1 DDR and an external llama.cpp backend; separate SysEmu experiments | October 21 receipt records normal upstream `llama-cli`, eight TinyStories tokens matching CPU control and **279 physical JTAG matrix dispatches**. Other operations stay on CPU. Combined JTAG/PCIe image has offline and JTAG evidence; physical PCIe control/DMA remains unqualified. This is not a complete ET-SOC1 chip implementation. | `examples/fpga/README.md`, `docs/llama.md`, `docs/mac-etsoc-pcie-handoff.md` |
| **LPULite** — `~/LPULite` | Complete eight-lane LPU, 96-bit VLIW and MicroGPT runtime through USER1 JTAG | October 14 Vivado candidate passed 50 MHz route/timing/DRC and packet CRC checks. Setup margin is +0.046 ns and hold +0.066 ns. Physical operation and reset behavior remain untested; DE1-SoC results in the upstream README are a different platform. | `synthesis/ypcb/README.md`, `build/ypcb/current-vivado-preparation.json` |
| **soDLA** — `~/soDLA` | Complete checked-in small core, APB/AXI workload and convolution checker | October 8 openXC7 reference candidate passed assembly and full frame-data/ECC comparison, with a 50.5076 MHz routed estimate for a 50 MHz target. Configuration CRC and physical operation remain unverified. | `docs/ypcb/bringup.md`, `build/ypcb/kintex-assembly-current.json` |
| **Somnia** — `~/somnia` | Complete C8×K8 INT8 PE with CMAC/CACC and board workload; not a full NVDLA SoC | October 6 native candidate has passing simulation/mapping, exact-part route/FASM/assembly receipts and 64-DSP checks; estimate 185.70 MHz at a 50 MHz target. No physical execution or full vendor timing signoff. | `docs/YPCB_PREPARATION.md`, `out/prepare/native-candidate-pass.json` |
| **RK-NPU FPGA** — `~/rknpu-fpga` | Strict FP16 EW register-stream slice and separate full C32/K16 512-product CMAC preparation | Source regressions and historical packing checks exist, but no accepted bitstream or physical result. October 23 direction is **Vivado preparation only**, using OpenTPU as a reference; openXC7 P&R was retired. Preserve the full CMAC target and do not launch either implementation flow from this survey. Git has an unborn `main`, so source is currently uncommitted. | `README.md`, `docs/REVIEW_AND_PLAN.md`, `docs/FPGA.md`, `verification/README.md` |
| **tiny-tpu** — `~/tiny-tpu` | Autonomous XOR compute demo with scoreboard and LEDs | October 17 **150 MHz SRAM quick test passed**: 95/95 JTAG SAMPLE captures had PASS asserted, failure clear, with 22 heartbeat transitions. Exact image had clean routed timing/DRC. This covers XOR, not DDR, PCIe, MNIST or LLM inference. | `HARDWARE_TEST_20261017.md`, `ypcb_demo/README.md`, `ypcb_demo/docs/hardware/20261017/manifest.json` |
| **tiny-gpu** — `~/tiny-gpu` | Actual two-core/four-thread GPU with all arithmetic including DIV and BRAM matadd/matmul workload | Historical October 6 candidate passed native route/artifact checks with a 97.428 MHz estimate. Current tooling has later changes: historical receipts do not validate them. Physical execution, electrical checks and complete Kintex timing remain pending. | `fpga/README.md`, `fpga/STATUS.md`, `fpga/tools/board.py` |
| **VeriGPU** — `~/verigpu` | Existing GPU integer/FP32 pipelines, 16 KiB program/data BRAM and USER1 host transport | October 5/6 snapshot passed functional/mapped tests, native routing (74.46 MHz estimate), frame/ECC audit and bit assembly. Physical execution remains pending; changed sources need new receipts. | `fpga/ypcb/README.md`, `fpga/ypcb/TRANSPORT.md`, `fpga/ypcb/open_board.py` |
| **Bonetto SoC** — `~/bonetto-soc` | First-profile JTAG/Wishbone baseline: two 4 KiB BRAM banks, no CPU or external DDR path | October 6 first-profile candidate has 35 selected simulation results, bounded formal checks, native route and structural bitstream checks. They are historical evidence; the October 23 tooling/source fixes need fresh build receipts. The newer October 17 CH1 2 GiB access-enabled candidate generated a bitstream but failed timing (WNS −3.853 ns, 208 setup failures); CRC and physical DDR were not checked. No physical BRAM pass is recorded in the bring-up guide. | `docs/fedora-bringup.md`, `scripts/fedora-bringup.sh`, `boards/ypcb-00338/` |
| **TiferKing board system** — `~/ypcb/projects/ypcb_00338_1p1_hack` | Supplied MicroBlaze, dual MIG, MDM UART, BRAM, GPIO/I²C and XDMA design | Exact supplied 2022.2 image passes structural checks; source archives contain no application ELF. Local scripts prepare/build one. October 10 SRAM/ELF launch attempt timed out before a complete CPU/DDR transcript, so it is not a successful dual-channel DDR test. | `docs/FEDORA_BRINGUP.md`, `scripts/fedora_soc.py`, `scripts/prepare_fedora_baseline.py` |

## Concrete evidence anchors

The snapshot JSON hashes these files where present. Reading a receipt and
checking a bitstream's hash are integrity checks, not rerunning its validator
or hardware test.

| Project | Evidence inside its checkout | What it establishes |
| --- | --- | --- |
| OpenTPU | `HANDOFF.md`; `build/handoffs/runtime-clock-abandoned-by-user-20261022.json` | Final disposition takes precedence over earlier resume notes. |
| KohakuTPU | `build/ypcb/offline-hardening-prepared-20261021T004321Z/offline-checks/report.json` | Source-only checks on the frozen preparation; no native qualification of the new reset/CDC source. |
| Vortex | `build_ypcb_blackwell32/next-intmul-source/build_ypcb_blackwell32/completion-audit-20261023-v10-cleanup-recovery.json` | Physical JTAG/CH1/compute result for SHA256 `3c3ac665c8403cc9fa203a7c89e551cb74092c26dec83b53c076a772610f6cc2`; cleanup failure and its recovery are retained. |
| ET-SOC | `docs/data/stock-et-normal-cli-combined-jtag-eight-reference-20261021.json` | Eight-token CPU comparison and physical JTAG execution for SHA256 `ef74b6be6b90f2fa01557b9811cf43471d6a7ac9c4aaa395ea824dd3c1cabf25`; PCIe false. |
| tiny-tpu | `ypcb_demo/docs/hardware/20261017/manifest.json` | Historical XOR scoreboard observation for the exact 150 MHz image; no flash write. |
| Bonetto | `build/fedora-simulation-results.json`; `build/fedora-first-bitstream-check.json`; `build/vivado-ddr3-ch1-2gib-access-20261017T202400Z/build-manifest.json` | Historical BRAM checks; separate newer CH1 candidate is `BITSTREAM_GENERATED_TIMING_NOT_MET`, not a qualified DDR image. |
| TiferKing | `build/fedora-baseline/vivado-bitstream-check-live-20261010T1017HKT.json`; `build/fedora-microblaze/hardware-20261010T135515978852Z/result.json` | Supplied image identity/structure and the incomplete later CPU launch. |

These eleven retained bitstreams were read and SHA256-checked during this survey:

| Project | Image path inside checkout | SHA256 |
| --- | --- | --- |
| OpenTPU c0182800 | `bitstreams/spare-dual-host-4gb-c0182800/otpu.bit` | `df2521d80de1d69ea4ca758821dc67a814b95d67ac851b78727c9154a3104bf2` |
| OpenTPU c0182863 | `bitstreams/spare-dual-host-4gb-c0182863/otpu.bit` | `03b513a44544009afff9dfb82515bf84c5df84ac6a63673a0882308ce8a323ae` |
| KohakuTPU AltSpread | `bitstreams/ypcb-d5d4d90-altspread-v1/kohakutpu_ypcb.bit` | `d913b05cb9f6dd2a668c7f0bedfe05d439fa41f425c18ef90e16a2b923e5921d` |
| LPULite | `build/ypcb/lpulite-ypcb-vivado-bitstream-20261014/lpu_ypcb.bit` | `b2fb4f1ee27a775d438317ebeb3d1c78e5af26a579c78612f32a5f85a2795320` |
| Somnia | `out/openxc7/1791241578261530791/somnia.bit` | `b775df6fa26c240c002e97f3ce9afa83eb7804c32bc5ea622fdf9ec8d28dcbcb` |
| soDLA | `build/ypcb/assembled-kintex-1791420935597750730/sodla_ypcb.bit` | `c23654426ec9824c0b85d84e13ee8fe7933d0ebaff7278504e814855dae4b338` |
| tiny-gpu | `build/ypcb/openxc7-1791294584961856221/tiny_gpu_demo.bit` | `2b64691f5a0be6deed105fb720e8896310ef246391179aaddae9c55bb9e1bd5b` |
| VeriGPU | `build/ypcb-openxc7/bit-20261006T113134895712Z/verigpu_ypcb.bit` | `803203a2697862fda52b28bafc6c0b644745019b3c5c91b5948508093860980a` |
| tiny-tpu | `ypcb_demo/artifacts/build-20261016T102846491634Z/tiny_tpu_ypcb.bit` | `b377cee1dc3082ab6de7cced229a1538bfa987335cfa5dc8cbd63a9268ecae42` |
| Bonetto first BRAM | `boards/ypcb-00338/build/bonetto_soc_ypcb00338_jtag_bram_first.bit` | `dbde7024a7e7e9485944cdedc3087384d7ac48d3357e5ce6d7d7d892067245dc` |
| Bonetto CH1 (timing failed) | `build/vivado-ddr3-ch1-2gib-access-20261017T202400Z/bonetto_ddr3_ch1_2gib_access.bit` | `2d2e113f381f090eb9062e467765a68e8870befa8401962c07f860030040e2d3` |

## References, alternate checkouts and support

| Location | Classification and use |
| --- | --- |
| `~/upstream_openTPU` | Separate clean upstream reference clone, `main` at `f237dab2f196` in this snapshot. Its published board-performance claims are not evidence from the user's local card. |
| `~/ypcb/projects/openTPU-upstream-e15b4a44` | Clean detached linked worktree at `e15b4a442346`; keep its Git registration. It is an older reference, not the active OpenTPU checkout. |
| `~/ypcb/projects/inspur-adventures` | Clean secondary clone at `998bb2569ad3`; board reverse-engineering material. |
| `~/ypcb/ref/inspur-adventures` | Same base revision, with local DLC10 descriptor/stage2 changes. Independent reference/support clone. The shared initializer now uses the reviewed tracked helper copy in this repository. |
| `~/ypcb/ref/ypcb_00338_1p1_hack` | Clean TiferKing board reference at `8b13ecf71b70`; distinct from the diagnostic project copy. |
| `~/ypcb/ref/LC480T` | Board files, constraints/tutorials and an example image; a data directory, not an independent Git repository. |
| `~/ypcb/ref/ZYNQ-NVDLA` | Zynq/NVDLA integration reference; not a completed XC7K480T port. |
| `~/ypcb/openFPGALoader`, `ref/fxload`, `ref/xpcu-macos` | Loader, FX2 helper and cable reference code. They are transport/tool dependencies, not compute SoCs. |
| `~/nvdla`, `~/tinynvdla`, `~/tinygrad_nvdla`, `~/tinytenstorrent` | Potential RTL/software/reference donors; no direct YPCB port was found in the scanned source/documentation. |
| `~/rk3588`, `~/tinygrad` | Rockchip hardware/backend context for RK-NPU work; not additional YPCB FPGA implementations. |
| `~/et-platform`, `~/et-sysemu`, `~/etsoc1-native-matmul-mat-engine-perf-visulization` | ET toolchain/simulation/performance support; separate from the physical Minion port in `~/etsoc`. |
| `~/vortex-tools-v3.0.1` | Vortex compiler/simulator tool bundle, not another SoC checkout. |
| `~/vortex-local-backup-20261017T182432Z` | Recovery archive with patch, file tar and manifest; not an active repository. |
| `~/otpu-build` | Auxiliary build/staging directory, not the OpenTPU source checkout. |

The wider scan also checked the source/documentation of `ClusterSim`, `mgpusim`,
`miaow_gcn4`, `multi2sim`, `multi2sim-iiswc2016`, `navisim`, `npu`, `nvgpu`,
`onnc`, `qbox`, `tt` and `tt-metal`. No direct YPCB/`xc7k480t` port was found
there. Hidden caches, tool installations, generated build trees and recovery
copies are not counted as additional projects. This scope is a local workspace
inventory, not an exhaustive review of every upstream implementation.

## Maintaining the inventory

Keep restoration metadata and current workspace state separate:

- `../repositories.json` pins the bases for the versioned source overlays.
  Moving a checkout or advancing its branch does not change those patch bases.
- `project-inventory.json` is a dated observation, including uncommitted work.
  Refresh Git state and the latest handoff/receipt before starting project work.
- Read each project's `AGENTS.md` and current handoff before running commands.
  Abandoned or paused work is not resumed by updating this index.
- Record source checks, implementation/timing, bitstream integrity, SRAM load,
  DDR/compute behavior, PCIe and permanent flash separately. A newer README
  does not retroactively validate an older image against changed source.
