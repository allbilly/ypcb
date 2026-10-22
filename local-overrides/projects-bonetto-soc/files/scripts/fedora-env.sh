#!/usr/bin/env bash
# Source from any directory. Reuse the native tools already built on this host.
BONETTO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export BONETTO_WORKSPACE_ROOT=${BONETTO_WORKSPACE_ROOT:-${OTPU_WORKSPACE_ROOT:-$HOME}}
export YPCB_ROOT=${YPCB_ROOT:-$BONETTO_WORKSPACE_ROOT/ypcb}
BONETTO_HIMBAECHEL_BINARY=${BONETTO_HIMBAECHEL_BINARY:-${BONETTO_WORKSPACE_ROOT:-$HOME}/tiny-gpu/build/ypcb/nextpnr-cli-build/nextpnr-himbaechel}
BONETTO_HIMBAECHEL_CHIPDB=${BONETTO_HIMBAECHEL_CHIPDB:-${BONETTO_WORKSPACE_ROOT:-$HOME}/tiny-gpu/build/ypcb/nextpnr-build/himbaechel/uarch/xilinx/chipdb-xc7k480t.bin}
BONETTO_XRAY_BIN=${BONETTO_XRAY_BIN:-${BONETTO_WORKSPACE_ROOT:-$HOME}/tiny-gpu/build/ypcb/xray-venv/bin}
BONETTO_XRAY_SOURCE=${BONETTO_XRAY_SOURCE:-${BONETTO_WORKSPACE_ROOT:-$HOME}/tiny-gpu/build/ypcb/prjxray}
BONETTO_FRAMES_BIN=${BONETTO_FRAMES_BIN:-${BONETTO_WORKSPACE_ROOT:-$HOME}/tiny-gpu/build/ypcb/prjxray-build/tools}
export PRJXRAY_DB_DIR=${BONETTO_PRJXRAY_DB_DIR:-${BONETTO_WORKSPACE_ROOT:-$HOME}/tiny-gpu/build/ypcb/prjxray-db}
export PATH="$BONETTO_ROOT/build/fedora-venv/bin:$BONETTO_ROOT/build/fedora-tools/bin:$BONETTO_ROOT/build/openfpgaloader-xvc-dlc10:$BONETTO_ROOT/build/himbaechel-probe:$BONETTO_XRAY_BIN:$BONETTO_FRAMES_BIN:$PATH"
export COCOTB_PYTHON="$BONETTO_ROOT/build/fedora-venv/bin/python"
export PYTHONPATH="$BONETTO_XRAY_SOURCE${PYTHONPATH:+:$PYTHONPATH}"
export BONETTO_ROOT
