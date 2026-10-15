#!/usr/bin/env python3
"""Build one patched router object and relink verified native cached objects."""

try:
    from .workspace_paths import expand_paths
except ImportError:
    from workspace_paths import expand_paths
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DONOR = Path(expand_paths('@WORKSPACE@/tiny-gpu/build/ypcb/nextpnr-cli-build'))
ORIGINAL = Path(expand_paths('@WORKSPACE@/tiny-gpu/build/ypcb/nextpnr-himbaechel'))
WORK = ROOT / 'build/himbaechel-router1-tuned'
SOURCE = WORK / 'source'
PATCH = ROOT / 'scripts/patches/nextpnr-router1-precision.patch'
REVISION = 'c68c13582e972292c86a5025140d52e713384cbc'
DONOR_HASH = '72f8d48aad976ce098ecb7f0c591a96da59f333f3a27ceff57e59aabcd8fb74a'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(str(message))


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    require(digest(DONOR / 'nextpnr-himbaechel') == DONOR_HASH, 'Native donor binary changed')
    source_manifest = WORK / 'source-manifest.json'
    if source_manifest.exists():
        recorded = json.loads(source_manifest.read_text())
        require(recorded['patch_sha256'] == digest(PATCH), 'Router patch changed')
        for name, value in recorded['files_sha256'].items():
            require(digest(SOURCE / name) == value, f'Isolated source changed: {name}')
    else:
        archive = subprocess.check_output(['git', '-C', str(ORIGINAL), 'archive', REVISION])
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            if SOURCE.exists():
                for entry in stream.getmembers():
                    if entry.isfile():
                        require((SOURCE / entry.name).read_bytes() == stream.extractfile(entry).read(), entry.name)
            else:
                SOURCE.mkdir()
                stream.extractall(SOURCE, filter='data')
        subprocess.run(['git', 'apply', '--directory=build/himbaechel-router1-tuned/source', str(PATCH)],
                       cwd=ROOT, check=True)
        source_manifest.write_text(json.dumps({'revision': REVISION, 'patch_sha256': digest(PATCH),
            'files_sha256': {str(p.relative_to(SOURCE)): digest(p) for p in sorted(SOURCE.rglob('*'))
                            if p.is_file()}}, indent=2) + '\n')

    target = DONOR / 'himbaechel/CMakeFiles/nextpnr-himbaechel.dir'
    flags = {}
    for line in (target / 'flags.make').read_text().splitlines():
        if line.startswith('CXX_'):
            key, value = line.split(' = ', 1)
            flags[key] = shlex.split(value)
    obj, binary = WORK / 'router1.cc.o', WORK / 'nextpnr-himbaechel'
    compile_args = ['/usr/bin/c++'] + flags['CXX_DEFINES'] + flags['CXX_INCLUDES'] + flags['CXX_FLAGS']
    compile_args = [s.replace(str(ORIGINAL), str(SOURCE)) for s in compile_args]
    compile_args += ['-o', str(obj), '-c', str(SOURCE / 'common/route/router1.cc')]
    link = shlex.split((target / 'link.txt').read_text())
    replacement = 'CMakeFiles/nextpnr-himbaechel.dir/__/common/route/router1.cc.o'
    link_args, inputs = [], {}
    for index, arg in enumerate(link):
        if index and link[index - 1] == '-o':
            link_args.append(str(binary))
        elif arg.startswith('-Wl,--dependency-file='):
            link_args.append('-Wl,--dependency-file=' + str(WORK / 'link.d'))
        elif arg == replacement:
            link_args.append(str(obj))
        elif arg.endswith(('.o', '.a')):
            path = (DONOR / 'himbaechel' / arg).resolve() if not Path(arg).is_absolute() else Path(arg)
            require(path.stat().st_mtime_ns <= (DONOR / 'nextpnr-himbaechel').stat().st_mtime_ns, path)
            inputs[str(path)] = digest(path)
            link_args.append(str(path))
        else:
            link_args.append(arg)
    manifest = {'revision': REVISION, 'donor_binary_sha256': DONOR_HASH,
        'compile_argv': compile_args, 'link_argv': link_args, 'cached_inputs_sha256': inputs,
        'source_manifest_sha256': digest(source_manifest), 'physical_validation': False,
        'status': 'BUILDING'}
    manifest_path = WORK / 'build-manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Verified {len(inputs)} cached link inputs; compiling the isolated router module', flush=True)
    subprocess.run(compile_args, cwd=WORK, check=True)
    subprocess.run(link_args, cwd=WORK, check=True)
    for name, value in inputs.items():
        require(digest(Path(name)) == value, f'Cached object changed during build: {name}')
    manifest.update(status='BUILT', binary_sha256=digest(binary))
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    subprocess.run([str(binary), '--version'], check=True)
    print(f'Isolated configurable router built: {binary}', flush=True)


if __name__ == '__main__':
    main()
