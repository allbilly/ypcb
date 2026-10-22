#!/usr/bin/env bash
# Native Himbaechel build of the two-4-KiB first JTAG/Wishbone proof.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/fedora-env.sh"
cd "$BONETTO_ROOT"
board=boards/ypcb-00338
project=bonetto_soc_ypcb00338_jtag_bram_first
work=build/himbaechel-first
router_work=build/himbaechel-router1-tuned
native=build/himbaechel-probe
placer="$native/nextpnr-himbaechel"
router="$router_work/nextpnr-himbaechel"
delays="$native/xc7k480t-default-delays.bin"
router_donor=${BONETTO_HIMBAECHEL_BINARY:-${BONETTO_WORKSPACE_ROOT:-$HOME}/tiny-gpu/build/ypcb/nextpnr-cli-build/nextpnr-himbaechel}
chipdb=${BONETTO_HIMBAECHEL_CHIPDB:-${BONETTO_WORKSPACE_ROOT:-$HOME}/tiny-gpu/build/ypcb/nextpnr-build/himbaechel/uarch/xilinx/chipdb-xc7k480t.bin}
database="$PRJXRAY_DB_DIR"
part=xc7k480tffg1156-2
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

mkdir -p "$work" "$native"
if [[ ! -x "$placer" ]]; then
    [[ -x "$router_donor" ]] || die "Missing native router: $router_donor"
    cp --reflink=auto "$router_donor" "$placer"
fi
[[ -r "$chipdb" ]] || die "Missing Himbaechel chip database: $chipdb"
[[ -r "$database/kintex7/$part/part.yaml" ]] || die 'Missing exact-part assembler database'
[[ $(git -C "$database" rev-parse HEAD) == 517d66a383676cb971177ea92b0ff3b6ea6e8690 ]] || die 'Assembler database revision changed'
[[ -z $(git -C "$database" status --porcelain) ]] || die 'Assembler database has local changes'
[[ $(git -C "$BONETTO_XRAY_SOURCE" rev-parse HEAD) == ed3331c6200f421164101388759fc2860b0f5634 ]] || die 'Assembler source revision changed'
[[ -z $(git -C "$BONETTO_XRAY_SOURCE" status --porcelain) ]] || die 'Assembler source has local changes'
[[ -x "$router" && -r "$router_work/build-manifest.json" ]] || python3 scripts/fedora-build-router.py
python3 - <<'PYVERIFY'
import hashlib,json
from pathlib import Path
p=Path('build/himbaechel-router1-tuned/build-manifest.json')
d=json.loads(p.read_text())
b=p.parent/'nextpnr-himbaechel'
if d['status']!='BUILT' or hashlib.sha256(b.read_bytes()).hexdigest()!=d['binary_sha256']:
    raise SystemExit('The isolated router build is incomplete or changed')
s=p.parent/'source-manifest.json'
if hashlib.sha256(s.read_bytes()).hexdigest()!=d['source_manifest_sha256']:
    raise SystemExit('The router source manifest changed')
source=json.loads(s.read_text())
patch=Path('scripts/patches/nextpnr-router1-precision.patch')
if hashlib.sha256(patch.read_bytes()).hexdigest()!=source['patch_sha256']:
    raise SystemExit('The router patch changed; rebuild the isolated router')
for name, expected in source['files_sha256'].items():
    if hashlib.sha256((p.parent/'source'/name).read_bytes()).hexdigest()!=expected:
        raise SystemExit(f'The isolated router source changed: {name}')
PYVERIFY
"$router" --version

# The upstream JSON target does not track its Makefile, synthesis options or
# tool. Bind both generated inputs to their effective recipes and contents.
synth_command=(make -C "$board" PROJECT="$project" TOP=top_jtag_bram_first
    RTL='rtl/top_jtag_bram_first.v rtl/top_jtag_bram.v ../../ip/wb-memory/rtl/wb_memory.v ../../ip/jtag-uart/rtl/jtag_uart.v ../../ip/jtag-uart/rtl/jtag_wb_master.v ../../ip/wishbone/rtl/wb_decode2.v'
    "build/$project.json" "build/$project.xdc")
python3 - "$board" "$project" "${synth_command[@]}" <<'PYSYNTH'
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

board, project = Path(sys.argv[1]), sys.argv[2]
command = sys.argv[3:]
record_path = Path('build/fedora-bram-first-synthesis.json')
sources = next(arg[4:] for arg in command if arg.startswith('RTL=')).split()
inputs = [board / name for name in sources]
inputs += [board / 'Makefile', board / 'constraints/ypcb003381p1_active.xdc']
outputs = [board / 'build' / (project + suffix) for suffix in ('.json', '.xdc')]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot():
    yosys = shutil.which('yosys')
    if not yosys:
        raise SystemExit('Missing synthesis tool: yosys')
    # -B -n expands the actual Makefile recipes even when targets already exist.
    recipe = subprocess.check_output([command[0], '-B', '-n', *command[1:]], text=True)
    return {
        'schema': 1,
        'command': command,
        'recipe': recipe,
        'inputs_sha256': {str(path): digest(path) for path in inputs},
        'yosys': {'path': yosys, 'sha256': digest(Path(yosys))},
        'environment': {key: value for key, value in os.environ.items()
                        if key.startswith('YOSYS_') or key in ('MAKEFLAGS', 'MAKEFILES')},
    }

expected = snapshot()
try:
    recorded = json.loads(record_path.read_text())
    reusable = recorded['inputs'] == expected and recorded['outputs_sha256'] == {
        str(path): digest(path) for path in outputs
    }
except (OSError, ValueError, KeyError):
    reusable = False
if reusable:
    print('Reusing verified synthesis and XDC; recipes, sources and tool are unchanged.', flush=True)
else:
    # A successful make exit alone is insufficient: inherited -n/-t modes can
    # skip compilation. Preserve old outputs and require newly generated files.
    # Keep legitimate make variable overrides intact.
    with tempfile.TemporaryDirectory(prefix='synthesis-backup-', dir=record_path.parent) as directory:
        existed = {path: path.exists() for path in outputs}
        backups = {}
        published = False
        try:
            for path in outputs:
                if existed[path]:
                    backup = Path(directory) / path.name
                    path.replace(backup)
                    backups[path] = backup
            subprocess.run([command[0], '-B', *command[1:]], check=True)
            if snapshot() != expected:
                raise SystemExit('Synthesis inputs changed during the build; run the build again')
            if any(not path.is_file() or path.stat().st_size == 0 for path in outputs):
                raise SystemExit('Synthesis or constraint generation produced no fresh output; check make flags')
            recorded = {'inputs': expected,
                        'outputs_sha256': {str(path): digest(path) for path in outputs}}
            temporary = record_path.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(recorded, indent=2, sort_keys=True) + '\n')
            temporary.replace(record_path)
            published = True
        finally:
            if not published:
                for path, backup in backups.items():
                    backup.replace(path)
                for path in outputs:
                    if not existed[path]:
                        path.unlink(missing_ok=True)
PYSYNTH
placed="$work/placed.json"
routing_input="$work/router1.json"
place_record=build/fedora-bram-first-placement.sha256
if [[ -r "$place_record" ]] && sha256sum --check --status "$place_record"; then
    printf 'Reusing the recorded placement checkpoint.\n'
else
    timeout "${BONETTO_PLACE_TIMEOUT_SECONDS:-900}" "$placer" \
        --device "$part" --chipdb "$chipdb" \
        -o "xdc=$board/build/$project.xdc" --json "$board/build/$project.json" \
        --freq 50 --seed 1 -o "delay-matrix=$delays" --no-route --write "$placed"
    sha256sum "$board/build/$project.json" "$board/build/$project.xdc" \
        "$placer" "$chipdb" "$placed" "$delays" > "$place_record"
fi
# Restored module settings override the CLI. Set the router in the copy;
# retain the checkpoint's placement seed state and explicit 50 MHz target.
python3 - <<'PYROUTE'
import json
from pathlib import Path
p=Path('build/himbaechel-first/placed.json')
d=json.loads(p.read_text())
settings=d['modules']['top']['settings']
if settings['target_freq']!='50000000.000000':
    raise SystemExit('Unexpected saved target frequency')
settings['router']='router1'
Path('build/himbaechel-first/router1.json').write_text(json.dumps(d,indent=2)+'\n')
PYROUTE
export BONETTO_ROUTER1_ESTIMATE_PRECISION=1000
route_command=("$router" --device "$part" --chipdb "$chipdb"
    --json "$routing_input" --freq 50 --no-pack --no-place --router router1
    -o "fasm=$work/bonetto_jtag_bram.fasm"
    -o "placement=$work/placement.json"
    --write "$work/bonetto_jtag_bram_routed.json"
    --report "$work/bonetto_jtag_bram_timing.json")
python3 - "$BONETTO_ROUTER1_ESTIMATE_PRECISION" "${route_command[@]}" <<'PYCOMMAND' > "$work/route-command.json"
import json,sys
print(json.dumps({'argv':sys.argv[2:],
    'environment':{'BONETTO_ROUTER1_ESTIMATE_PRECISION':sys.argv[1]}},indent=2))
PYCOMMAND
route_record=build/fedora-bram-first-route.sha256
if [[ -r "$route_record" ]] && sha256sum --check --status "$route_record"; then
    printf 'Reusing the verified route; recorded inputs and outputs are unchanged.\n'
else
    timeout "${BONETTO_ROUTE_TIMEOUT_SECONDS:-1800}" "${route_command[@]}"
    sha256sum "$board/build/$project.json" "$board/build/$project.xdc" \
        "$router" "$chipdb" "$routing_input" "$work/route-command.json" \
        "$work/bonetto_jtag_bram.fasm" "$work/bonetto_jtag_bram_routed.json" \
        "$work/bonetto_jtag_bram_timing.json" "$work/placement.json" "$delays" \
        > "$route_record"
fi

# Feed every FASM feature to the matching database. Never opt into omission.
fasm="$board/build/$project.fasm"
frames="$board/build/$project.frames"
bit="$board/build/$project.bit"
cp "$work/bonetto_jtag_bram.fasm" "$fasm"
frame_record=build/fedora-bram-first-frames.sha256
if [[ -r "$frame_record" ]] && sha256sum --check --status "$frame_record"; then
    printf 'Reusing strict frame assembly; recorded inputs and output are unchanged.\n'
else
    env -u XRAY_ALLOW_MISSING_FEATURES "$BONETTO_XRAY_BIN/python" scripts/fedora-fasm2frames.py \
        --part "$part" --db-root "$database/kintex7" "$fasm" > "$frames.tmp"
    mv "$frames.tmp" "$frames"
    sha256sum "$fasm" "$frames" scripts/fedora-fasm2frames.py \
        "$database/kintex7/$part/part.yaml" \
        "$BONETTO_XRAY_SOURCE/utils/fasm2frames.py" \
        "$BONETTO_XRAY_SOURCE/prjxray/fasm_assembler.py" \
        "$BONETTO_XRAY_SOURCE/prjxray/db.py" "$BONETTO_XRAY_SOURCE/prjxray/grid.py" \
        > "$frame_record"
fi
xc7frames2bit --part_file "$database/kintex7/$part/part.yaml" \
    --part_name "$part" --frm_file "$frames" --output_file "$bit.tmp"
[[ -s "$bit.tmp" ]] || die 'The frame assembler produced no bitstream'
mv "$bit.tmp" "$bit"
# Routing/assembly can take a long time. Do not attach current source hashes
# to an image whose synthesis inputs changed while those stages were running.
python3 - <<'PYRECHECK'
import hashlib
import json
from pathlib import Path

record = json.loads(Path('build/fedora-bram-first-synthesis.json').read_text())
expected = {**record['inputs']['inputs_sha256'], **record['outputs_sha256']}
yosys = record['inputs']['yosys']
expected[yosys['path']] = yosys['sha256']
for name, digest in expected.items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
        raise SystemExit(f'Synthesis provenance changed before image publication: {name}')
PYRECHECK
sha256sum "$bit" "$fasm" "$frames" "$work/bonetto_jtag_bram_timing.json" \
    "$board/build/$project.json" "$board/build/$project.xdc" \
    "$board/rtl/top_jtag_bram_first.v" "$board/rtl/top_jtag_bram.v" \
    "$board/constraints/ypcb003381p1_active.xdc" \
    "$board/Makefile" ip/wb-memory/rtl/wb_memory.v \
    build/fedora-bram-first-synthesis.json "$(command -v yosys)" \
    ip/jtag-uart/rtl/jtag_uart.v ip/jtag-uart/rtl/jtag_wb_master.v \
    ip/wishbone/rtl/wb_decode2.v scripts/fedora-build-bram.sh \
    "$router" "$chipdb" "$routing_input" "$router_work/build-manifest.json" "$router_work/source-manifest.json" \
    scripts/patches/nextpnr-router1-precision.patch scripts/fedora-build-router.py \
    scripts/fedora-fasm2frames.py "$work/route-command.json" scripts/fedora-env.sh \
    tools/jtag_bram_validate.py tools/jtag_uart_read.py \
    "$database/kintex7/$part/part.yaml" \
    "$BONETTO_XRAY_SOURCE/utils/fasm2frames.py" \
    "$BONETTO_XRAY_SOURCE/prjxray/fasm_assembler.py" \
    "$BONETTO_XRAY_SOURCE/prjxray/db.py" "$BONETTO_XRAY_SOURCE/prjxray/grid.py" \
    "$(command -v xc7frames2bit)" > build/fedora-bram-inputs.sha256
printf 'BRAM image assembled without filtering FASM features: %s\n' "$bit"
