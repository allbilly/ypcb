#!/usr/bin/env python3
"""Compile the supplied BSP and two BRAM-resident applications. No hardware I/O."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
TC = ROOT / "build/fedora-toolchain"
OUT = ROOT / "build/fedora-microblaze"
RELEASE = "https://github.com/mdednev/mb-gcc/releases/download/2021-0623%2B2/"
PACKAGES = [
    (RELEASE + "binutils-microblaze_2.35-2021-0623%2B1_amd64.deb", "31f1602530253e0b87e3968ed4e2b1f94f6b97305c716eb5d43d585d6bf0b137"),
    (RELEASE + "gcc-microblaze_10.2.0-2021-0623%2B2_amd64.deb", "e33f3cb1662510890e5fe13e72bd53d5fc39111f2da3c910de9ad64e79c6bb84"),
    (RELEASE + "libnewlib-microblaze-dev_3.3.0-2021-0623%2B3_all.deb", "307e72de6f0b4dcb420c09423e36531ebce214a24994af1b5d6291db59229698"),
    (RELEASE + "libnewlib-microblaze_3.3.0-2021-0623%2B3_all.deb", "a8533bf00a714dcdc7fc55c0d5655d298c1dbf563bcde1e16e1ae61a07607667"),
    ("https://deb.debian.org/debian/pool/main/f/flex/libfl2_2.6.4-8_amd64.deb", "f4213b29b04ccaa13a7a2bc001ef4156c8fb31fc8a1fca6dc7a490fef21092cb"),
]
FLAGS = ["-mcpu=v11.0", "-mlittle-endian", "-mno-xl-reorder", "-mno-xl-soft-mul",
         "-mxl-barrel-shift", "-mxl-pattern-compare"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_toolchain():
    from urllib.parse import unquote
    (TC / "downloads").mkdir(parents=True, exist_ok=True)
    (TC / "sysroot").mkdir(exist_ok=True)
    for url, expected in PACKAGES:
        path = TC / "downloads" / unquote(url.rsplit("/", 1)[1])
        if not path.exists():
            temporary = path.with_suffix(".partial")
            subprocess.run(["curl", "--fail", "--location", "--retry", "2", url,
                            "-o", str(temporary)], check=True)
            if sha(temporary) != expected:
                raise RuntimeError(f"Download hash mismatch: {url}")
            temporary.rename(path)
        if sha(path) != expected:
            raise RuntimeError(f"Toolchain package hash mismatch: {path}")
        receipt = TC / (expected + ".extracted")
        if not receipt.exists():
            member = next(n for n in subprocess.check_output(["ar", "t", str(path)],
                          text=True).splitlines() if n.startswith("data.tar."))
            process = subprocess.Popen(["ar", "p", str(path), member], stdout=subprocess.PIPE)
            with tarfile.open(fileobj=process.stdout, mode="r|*") as archive:
                archive.extractall(TC / "sysroot", filter="data")
            process.stdout.close()
            if process.wait() != 0:
                raise RuntimeError("Debian archive extraction failed")
            receipt.write_text(url + "\n")
    wrappers = TC / "bin"
    wrappers.mkdir(exist_ok=True)
    wrapper = wrappers / "mb-gcc"
    if wrapper.is_symlink():
        wrapper.unlink()
    wrapper.write_text('''#!/usr/bin/env bash
set -euo pipefail
toolchain="$(cd "$(dirname "$0")/.." && pwd)"
export LD_LIBRARY_PATH="$toolchain/sysroot/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$toolchain/sysroot/usr/bin/microblaze-xilinx-elf-gcc" -isystem "$toolchain/sysroot/usr/include/newlib-microblaze-xilinx-elf" -B"$toolchain/sysroot/usr/lib/microblaze-xilinx-elf/newlib/" "$@"
''')
    wrapper.chmod(0o755)
    for name in ("as", "ar", "objdump", "readelf", "size", "nm", "objcopy"):
        dest = wrappers / ("mb-" + name)
        if not dest.exists():
            dest.symlink_to("../sysroot/usr/bin/microblaze-xilinx-elf-" + name)


def elf_check(path):
    data = path.read_bytes()
    if data[:7] != b"\x7fELF\x01\x01\x01":
        raise RuntimeError("Expected ELF32 little-endian")
    header = struct.unpack_from("<HHIIIIIHHHHHH", data, 16)
    etype, machine, _, entry, phoff = header[:5]
    if etype != 2 or machine != 189 or entry != 0:
        raise RuntimeError("Expected MicroBlaze executable with reset vector entry")
    loads = []
    for i in range(header[9]):
        segment = struct.unpack_from("<8I", data, phoff + i * header[8])
        if segment[0] == 1:
            _, offset, vaddr, paddr, filesz, memsz, _, _ = segment
            if vaddr != paddr or paddr + memsz > 0x80000 or offset + filesz > len(data):
                raise RuntimeError("ELF load segments must fit the supplied 512 KiB BRAM")
            loads.append({"address": paddr, "file_bytes": filesz, "memory_bytes": memsz})
    if not loads:
        raise RuntimeError("ELF has no loadable segments")
    return {"path": str(path), "sha256": sha(path), "loads": loads}


def main():
    subprocess.run(["python3", str(ROOT / "scripts/prepare_fedora_baseline.py")], check=True)
    OUT.mkdir(exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps({"status": "BUILDING", "hardware_test": "NOT_RUN"}) + "\n")
    prepare_toolchain()
    staged = ROOT / "build/fedora-baseline/software"
    source = staged / "YPCB_00338_1P1_plat/microblaze_0/standalone_domain/bsp"
    bsp = OUT / "bsp"
    if not bsp.exists():
        shutil.copytree(source, bsp)
    app = staged / "YPCB_00338_1P1_App/src"
    env = os.environ.copy()
    env["PATH"] = str(TC / "bin") + ":" + env["PATH"]
    env["LD_LIBRARY_PATH"] = str(TC / "sysroot/usr/lib/x86_64-linux-gnu")
    with (OUT / "bsp-build.log").open("w") as log:
        # Archive only after every parallel compile finishes.
        for targets in (["seq_libs", "par_libs"], ["archive"]):
            subprocess.run(["make", "-j", "4", *targets], cwd=bsp, env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    outputs = []
    with (OUT / "app-build.log").open("w") as log:
        for name, sources in [
            ("systest", [app / "memorytest.c", app / "memory_config_g.c", app / "platform.c"]),
            ("ddr_diag", [ROOT / "scripts/fedora_ddr_diag.c"]),
        ]:
            elf = OUT / (name + ".elf")
            cmd = ["mb-gcc", *FLAGS, "-O2", "-g", "-Wall", "-Wextra", "-ffunction-sections",
                   "-fdata-sections", "-I" + str(bsp / "microblaze_0/include"),
                   "-I" + str(app), "-include", "xuartlite_l.h", *map(str, sources),
                   "-Wl,-T," + str(app / "lscript.ld"), "-Wl,--gc-sections",
                   "-Wl,-Map," + str(OUT / (name + ".map")),
                   "-L" + str(bsp / "microblaze_0/lib"), "-Wl,--start-group", "-lxil", "-lc",
                   "-lgcc", "-Wl,--end-group", "-o", str(elf)]
            subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            item = elf_check(elf)
            disassembly = subprocess.check_output(["mb-objdump", "-d", str(elf)], env=env, text=True)
            for opcode in ("lwea", "swea", "lhuea", "shea", "lbuea", "sbea"):
                if "\t" + opcode + "\t" not in disassembly:
                    raise RuntimeError(f"Missing extended address opcode {opcode}: {elf}")
            (OUT / (name + ".disassembly")).write_text(disassembly)
            item["compile_command"] = cmd
            outputs.append(item)
            print(subprocess.check_output(["mb-size", str(elf)], env=env, text=True).strip())
    manifest = {"status": "CPU_SOFTWARE_BUILT_HARDWARE_NOT_RUN", "hardware_test": "NOT_RUN",
                "source_revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
                "diagnostic_source_sha256": sha(ROOT / "scripts/fedora_ddr_diag.c"),
                "software_archive_sha256": sha(ROOT / "examples/YPCB_00338_1P1_software.zip"),
                "flags": FLAGS, "toolchain_packages": PACKAGES,
                "compiler": subprocess.check_output(["mb-gcc", "--version"], env=env, text=True).splitlines()[0],
                "bsp_sha256": sha(bsp / "microblaze_0/lib/libxil.a"), "applications": outputs,
                "ddr_bases": ["0x100000000", "0x180000000"], "bytes_tested_per_channel": 4096,
                "bitstream_sha256": "22e7281f7574d4e56153ce7345d9e0fb0044c80d56075e45724adcb496337931"}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Built both MicroBlaze executables; physical CPU/DDR tests remain pending.")


if __name__ == "__main__":
    main()
