#!/usr/bin/env python3
"""Stage and verify upstream YPCB hardware/software; never access a device."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/fedora-baseline"
INPUTS = {
    "examples/YPCB_00338_1P1_systest/top_wrapper.xsa":
        "d15b2be561d8b6acd53a370d53db4fc61803f53e6fe86159c0b9d6a626832647",
    "examples/YPCB_00338_1P1_software.zip":
        "d47ca9c6773686b328b411fa877d2ed8114ad2aa1a2718a50a7836f5278034e4",
}
BIT_HASH = "22e7281f7574d4e56153ce7345d9e0fb0044c80d56075e45724adcb496337931"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stage(archive, member, destination):
    name = PurePosixPath(member.filename)
    if name.is_absolute() or ".." in name.parts:
        raise RuntimeError(f"Unsafe ZIP path: {name}")
    if stat.S_ISLNK(member.external_attr >> 16):
        raise RuntimeError(f"ZIP symlink rejected: {name}")
    target = destination.joinpath(*name.parts)
    if not target.resolve().is_relative_to(OUTPUT.resolve()):
        raise RuntimeError(f"Output path escapes staging directory: {target}")
    if member.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return
    data = archive.read(member)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != data:
            raise RuntimeError(f"Refusing to overwrite changed staged file: {target}")
    else:
        target.write_bytes(data)


def main():
    for name, expected in INPUTS.items():
        actual = sha((ROOT / name).read_bytes())
        if actual != expected:
            raise RuntimeError(f"Archive hash mismatch: {name}: {actual}")

    xsa, software = (ROOT / name for name in INPUTS)
    bit_copies = []
    with zipfile.ZipFile(xsa) as archive:
        metadata = json.loads(archive.read("xsa.json"))
        if metadata["board"]["part"] != "xc7k480tffg1156-2":
            raise RuntimeError("XSA targets a different FPGA")
        bit_copies.append(sha(archive.read("top_wrapper.bit")))
        for member in archive.infolist():
            stage(archive, member, OUTPUT / "hardware")

    with zipfile.ZipFile(software) as archive:
        elf_members = [n for n in archive.namelist() if n.lower().endswith(".elf")]
        for member in archive.infolist():
            if member.filename.endswith("top_wrapper.bit"):
                bit_copies.append(sha(archive.read(member)))
            stage(archive, member, OUTPUT / "software")

    if len(bit_copies) != 4 or any(value != BIT_HASH for value in bit_copies):
        raise RuntimeError("The four supplied hardware bitstreams disagree")
    manifest = {
        "status": "ARTIFACTS_STAGED_HARDWARE_NOT_RUN",
        "source_revision": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "archive_sha256": INPUTS,
        "bitstream_sha256": BIT_HASH,
        "matching_bitstream_copies": len(bit_copies),
        "part": metadata["board"]["part"],
        "vivado_version": metadata["generatedVersion"],
        "application_elf_members": elf_members,
        "supplied_test_bytes_per_channel": 4096,
        "ddr_channel_bases": ["0x100000000", "0x180000000"],
        "ddr_mapped_bytes_per_channel": 2147483648,
        "compiler_required_for_supplied_application": True,
        "hardware_programmed": False,
        "flash_written": False,
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    print(f"Staged files: {OUTPUT}")


if __name__ == "__main__":
    main()
