# Tooling review and fixes — 2026-10-23

Three subagents reviewed the versioned YPCB shared tools and source overlays,
then fixed the confirmed findings in their assigned files. A second review
checked the fixes and project inventory. Independent SoC checkouts were read
for context and evidence; fixes here do not claim a full code audit of all 13
projects or modify those repositories.

## Fixed findings

| Area | Defect and correction |
| --- | --- |
| USB trace symbol resolution | `dlsym(RTLD_DEFAULT, ...)` could resolve the wrapper as its own real function and recurse; failed lookups could become non-null. Preserve lookup failure and resolve the real implementation before interposition. |
| USB trace content | Firmware transfer traces exposed the first payload byte and read asynchronous IN data before completion. Trace transfer metadata only. |
| FX2 stage2 input | Empty, malformed or truncated HEX input could reach USB and report success. Validate nonempty images and exact EOF structure before device access; upload the already-validated records. |
| FTDI write loop | A zero-byte write could spin forever. Stop on zero progress. |
| DLC10 packaging | Both compatibility patches embedded an older initializer without the board CPLD declaration/process guard. Regenerate them from the current wrapper and validated helper; the normal initializer uses the tracked helper. |
| Bonetto cache provenance | Stale Make outputs could be labeled with current source hashes. Require source/tool-bound cache admission and rebuild stale synthesis outputs. |
| Bonetto native runner | Concurrent controllers could race; interruption could leave child processes alive. Add exclusive ownership and bounded process-group cleanup, including descendants. |
| Bonetto timing admission | NaN/infinite slack could pass. Require complete, finite timing values. |
| Bonetto FASM audit | Alternate JTAG-selector encodings could bypass checking. Decode supported forms and reject conflicts. |
| Bonetto configuration | Shell/Python workspace overrides differed; programming lacked the CPLD declaration. Align path resolution and preserve the known board chain declaration. |
| Bonetto simulation | Unknown reset/completion signals could pass the BRAM test. Require known values and verify both memory profiles. |
| MicroBlaze ELF admission | A PT_LOAD with file bytes larger than its memory span could escape the BRAM bound. Validate header/table bounds, segment sizes and executable reset-vector coverage. |
| MicroBlaze UART admission | Reordered, duplicated or mixed test transcripts could pass. Require complete ordered markers and reject prefixed duplicate diagnostic markers while retaining valid noise/progress lines. |
| Restoration and project docs | Old paths, misleading historical status, ambiguous workspace overrides and manual XSDB context could break the documented flow. Correct paths/commands; distinguish patch bases, current workspace state and historical evidence. |

The Bonetto fixes reuse reviewed changes already present in its live checkout.
Its source patch was regenerated against the original `f6eea6c8` base, and
three regression modules were added to the overlay. Historical progress remains
preserved with an archive notice. `repositories.json` retains the original
capture/base revisions and records updated hashes for **36 exported sources
and three tracked patches**.

## Validation performed

| Check | Result |
| --- | --- |
| DLC10 mock USB/FTDI, tracer and compatibility-patch regressions | **11 passed**, no skips |
| MicroBlaze ELF/UART/host-flow regressions | **45 passed**, no skips |
| Bonetto reconstructed-checkout regressions, including Icarus RTL | **17 passed**, no skips |
| Native C DDR algorithm test | Passed with `-std=c11 -Wall -Wextra -Werror -O2` |
| Tracer/native mocks and FTDI source compilation | Passed with strict compiler warnings |
| Clean reconstruction of loader, cable reference, Bonetto and TiferKing overlays | All four restored from pinned Git archives; each applicable patch applied cleanly |
| Exported Python and shell syntax; Git whitespace | Passed |
| Overlay sizes and SHA256s | All 36 source copies and three patches matched |
| Project inventory | 13 implementations, 23 checkout/reference entries, 45 inspected evidence files; 11 retained bitstream hashes checked |

The **73 regression tests** use temporary directories, fake tool/hardware
interfaces and local simulation. Logs are retained locally under
`build/review-20261023/`; that directory is ignored because it is generated
evidence. Reproduction commands are in
[the restoration guide](../local-overrides/README.md). The machine-readable
[project snapshot](project-inventory.json) is versioned; it records file hashes
and Git observations, not a repeat of historical hardware validation.

No Vivado synthesis/implementation, USB/JTAG access, FPGA/flash programming,
Git commit or push was performed by this review. Existing independent project
jobs and the original hardware lock file were preserved. The new source and
tooling revisions require their own future hardware qualification.
