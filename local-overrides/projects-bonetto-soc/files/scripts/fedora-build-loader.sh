#!/usr/bin/env bash
# Snapshot the proven Fedora driver, then add DLC10 support to its XVC server.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/fedora-env.sh"
cd "$BONETTO_ROOT"
export BONETTO_LOADER_DONOR=${BONETTO_LOADER_DONOR:-${YPCB_ROOT:-$HOME/ypcb}/openFPGALoader}
python3 - <<'PY'
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import tarfile

root = Path(os.environ['BONETTO_ROOT'])
donor = Path(os.environ['BONETTO_LOADER_DONOR'])
source = root / 'build/openfpgaloader-source'
patch = root / 'scripts/patches/openfpgaloader-xpcu-xvc.patch'
revision = subprocess.check_output(['git', '-C', str(donor), 'rev-parse', 'HEAD'], text=True).strip()
expected = 'dafa7fcab2b96e927fd3108c3f33d1cc46117c8b'
if revision != expected:
    raise SystemExit(f'Loader donor revision changed: expected {expected}, got {revision}')
local_patch = subprocess.check_output(['git', '-C', str(donor), 'diff', '--binary', 'HEAD'])
digest = lambda data: hashlib.sha256(data).hexdigest()
provenance = {'donor': str(donor), 'revision': revision,
              'donor_local_patch_sha256': digest(local_patch),
              'xvc_patch_sha256': digest(patch.read_bytes()), 'physical_validation': False}
manifest = source / 'fedora-source-manifest.json'
if source.exists():
    if not manifest.exists():
        raise SystemExit(f'Incomplete source snapshot: inspect {source} before rebuilding')
    recorded = json.loads(manifest.read_text())
    if recorded['provenance'] != provenance:
        raise SystemExit('Donor or patch changed; retain this snapshot and choose a fresh build directory')
    for name, value in recorded['files_sha256'].items():
        if digest((source / name).read_bytes()) != value:
            raise SystemExit(f'Staged loader source was modified: {name}')
else:
    source.mkdir(parents=True)
    archive = subprocess.check_output(['git', '-C', str(donor), 'archive', 'HEAD'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as archive_file:
        archive_file.extractall(source, filter='data')
    if local_patch:
        subprocess.run(['git', 'apply', '--directory=build/openfpgaloader-source', '-'],
                       cwd=root, input=local_patch, check=True)
    subprocess.run(['git', 'apply', '--directory=build/openfpgaloader-source', str(patch)],
                   cwd=root, check=True)
    files = {str(p.relative_to(source)): digest(p.read_bytes())
             for p in sorted(source.rglob('*')) if p.is_file()}
    manifest.write_text(json.dumps({'provenance': provenance, 'files_sha256': files}, indent=2) + '\n')
    (root / 'build/fedora-loader-donor-local.patch').write_bytes(local_patch)
print('Isolated DLC10/XVC source verified:', source)
PY
cmake -S build/openfpgaloader-source -B build/openfpgaloader-xvc-dlc10 \
    -DCMAKE_BUILD_TYPE=Release -DENABLE_OPTIM=OFF \
    '-DCMAKE_CXX_FLAGS_RELEASE=-O0 -DNDEBUG' -DCMAKE_CXX_COMPILER=/usr/bin/g++ \
    -DPKG_CONFIG_EXECUTABLE=/usr/bin/pkg-config \
    -DENABLE_CABLE_ALL=OFF -DENABLE_VENDORS_ALL=OFF \
    -DENABLE_XILINX_SUPPORT=ON -DENABLE_XILINX_PLATFORM_CABLE_USB=ON \
    -DENABLE_XILINX_VIRTUAL_CABLE_CLIENT=ON \
    -DENABLE_XILINX_VIRTUAL_CABLE_SERVER=ON -DENABLE_LIBGPIOD=OFF
cmake --build build/openfpgaloader-xvc-dlc10 -j2
sha256sum build/openfpgaloader-xvc-dlc10/openFPGALoader \
    scripts/patches/openfpgaloader-xpcu-xvc.patch \
    build/openfpgaloader-source/fedora-source-manifest.json > build/fedora-loader.sha256
