#!/usr/bin/env python3
"""Build the full-capacity diagnostic using the already verified BSP/toolchain."""
import json
import os
from pathlib import Path
import subprocess
from build_fedora_microblaze import ROOT, TC, OUT as BASE, FLAGS, elf_check, sha
from fedora_soc import verify_artifacts

OUT = ROOT / 'build/fedora-microblaze-full-ddr'


def main():
    baseline = verify_artifacts()
    bsp = BASE / 'bsp/microblaze_0'
    app = ROOT / 'build/fedora-baseline/software/YPCB_00338_1P1_App/src'
    sources = [ROOT / 'scripts/fedora_ddr_full.c', ROOT / 'scripts/fedora_ddr_full_core.h',
               Path(__file__).resolve(), ROOT / 'scripts/build_fedora_microblaze.py',
               BASE / 'manifest.json', bsp / 'lib/libxil.a', app / 'lscript.ld', TC / 'bin/mb-gcc']
    sources.extend(sorted((bsp / 'include').glob('*.h')))
    inputs = {str(p): sha(p) for p in sources}
    if sha(bsp / 'lib/libxil.a') != baseline['bsp_sha256'] or FLAGS != baseline['flags']:
        raise RuntimeError('Verified BSP or exact CPU flags changed')
    if OUT.exists():
        previous = json.loads((OUT / 'manifest.json').read_text())
        if previous['status'] != 'FULL_CAPACITY_CPU_SOFTWARE_BUILT_HARDWARE_NOT_RUN' or previous['source'] != inputs:
            raise RuntimeError('Existing full diagnostic differs; preserve its evidence before rebuilding')
        elf = OUT / 'ddr_full.elf'
        if elf_check(elf) != previous['application']:
            raise RuntimeError('Existing full diagnostic ELF changed')
        print('Verified existing full-capacity MicroBlaze software; hardware remains NOT_RUN.')
        return
    OUT.mkdir()
    manifest = dict(status='BUILDING', hardware_test='NOT_RUN', source=inputs,
                    flags=FLAGS, bytes_tested_per_channel=2147483648, patterns=2,
                    ddr_bases=['0x100000000', '0x180000000'],
                    bitstream_sha256=baseline['bitstream_sha256'], flash_written=False)
    path = OUT / 'manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    env = dict(os.environ)
    env['PATH'] = str(TC / 'bin') + ':' + env['PATH']
    env['LD_LIBRARY_PATH'] = str(TC / 'sysroot/usr/lib/x86_64-linux-gnu')
    elf = OUT / 'ddr_full.elf'
    command = [str(TC / 'bin/mb-gcc'), *FLAGS, '-O2', '-g', '-Wall', '-Wextra', '-Werror',
               '-ffunction-sections', '-fdata-sections', '-I' + str(bsp / 'include'),
               str(ROOT / 'scripts/fedora_ddr_full.c'), '-Wl,-T,' + str(app / 'lscript.ld'),
               '-Wl,--gc-sections', '-Wl,-Map,' + str(OUT / 'ddr_full.map'),
               '-L' + str(bsp / 'lib'), '-Wl,--start-group', '-lxil', '-lc', '-lgcc',
               '-Wl,--end-group', '-o', str(elf)]
    manifest['compile_command'] = command
    try:
        with (OUT / 'build.log').open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        assembly = subprocess.check_output([str(TC / 'bin/mb-objdump'), '-d', str(elf)], env=env, text=True)
        for opcode in ('lwea', 'swea', 'mbar'):
            if '\t' + opcode + '\t' not in assembly:
                raise RuntimeError('Missing required full-address/barrier opcode: ' + opcode)
        (OUT / 'ddr_full.disassembly').write_text(assembly)
        if any(sha(Path(p)) != expected for p, expected in inputs.items()):
            raise RuntimeError('Full diagnostic input changed during compilation')
        manifest.update(status='FULL_CAPACITY_CPU_SOFTWARE_BUILT_HARDWARE_NOT_RUN', application=elf_check(elf))
        print(subprocess.check_output([str(TC / 'bin/mb-size'), str(elf)], env=env, text=True).strip())
    except Exception as error:
        manifest.update(status='FAIL', error=str(error))
        raise
    finally:
        path.write_text(json.dumps(manifest, indent=2) + '\n')
    print('Built full-capacity MicroBlaze software; 4 GiB physical DDR test remains NOT_RUN.')


if __name__ == '__main__':
    main()
