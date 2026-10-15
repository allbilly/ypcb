#!/usr/bin/env bash
# Keep XSDB's debug/ELF/JTAG packages; do not load the optional HSI design tools.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
lab="${VIVADO_LAB_ROOT:-${HOME}/vivado/2026.1.1/Vivado_Lab}"
sdk="$root/build/fedora-xsdb-sdk"
mkdir -p "$sdk/scripts/xsdb"
for package in xsdb tcf; do
    [[ -d "$lab/scripts/xsdb/$package" ]] || { echo "Missing XSDB package: $lab" >&2; exit 1; }
    ln -sfn "$lab/scripts/xsdb/$package" "$sdk/scripts/xsdb/$package"
done
unset XILINX_VITIS
export XILINX_SDK="$sdk"
export TCL_LIBRARY="$lab/tps/tcl/tcl8.6"
export TCLLIBPATH="$lab/tps/tcl/tcllib2.0"
export LD_LIBRARY_PATH="$lab/lib/lnx64.o${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$lab/bin/unwrapped/lnx64.o/xsdb" "$@"
