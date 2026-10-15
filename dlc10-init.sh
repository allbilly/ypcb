#!/usr/bin/env bash
# Fedora DLC10 volatile boot + overlay initialization and YPCB JTAG detection.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ofl="$root/openFPGALoader/build-xpcu-debug/openFPGALoader"
stage2="$root/ref/inspur-adventures/scripts/xpcu_stage2.py"
boot="$root/firmware/xusb_xp2-boot.hex"
overlay="$root/firmware/xusb_xp2-overlay.hex"
helper="$root/ref/fxload/a3load.hex"
# The documented YPCB JTAG chain has a CPLD-like device before the FPGA.
misc_device=(--misc-device 0x10931093,8,inspur_cpld)
die() { echo "Error: $*" >&2; exit 1; }
[[ $# == 0 ]] || die 'Usage: bash dlc10-init.sh (initializes cable RAM and detects FPGA only)'
for cmd in lsusb sha256sum awk pgrep python3; do
    command -v "$cmd" >/dev/null || die "Missing command: $cmd"
done
[[ -x "$ofl" && -r "$stage2" ]] || die 'Build openFPGALoader/build-xpcu-debug and provide xpcu_stage2.py first.'
for process in openFPGALoader hw_server xsdb fxload; do
    if pgrep -x "$process" >/dev/null; then
        die "Stop $process before using this cable."
    fi
done
check_hash() {
    [[ -r "$1" ]] || die "Missing firmware: $1"
    local actual
    actual=$(sha256sum -- "$1")
    [[ ${actual%% *} == "$2" ]] || die "Unexpected firmware checksum: $1"
}
check_hash "$boot" 4fe1a679efcc7ed7c01e738beaf29d8a1f1201731780dfc026f724a88aee527a
check_hash "$overlay" f551e3c71efee0556b465dc9975d528115f9849ea143f51b5c44d6f3f4f4a9cf
check_hash "$helper" 5f27f666e408512b4e7ba6d53bee89410b31e4cb9f7c27930dfa3db65ab2a240
logs=$(mktemp -d /tmp/dlc10-init.XXXXXX)
echo "Logs: $logs"
# Refuse ambiguous cable selection. Device numbers can change after CPU release.
device() {
    local rows
    rows=$(lsusb -d 03fd: | awk '$6 == "03fd:0013" || $6 == "03fd:0008"')
    [[ -n "$rows" ]] || return 1
    [[ $(printf '%s\n' "$rows" | wc -l) == 1 ]] || die 'Connect exactly one DLC10 cable.'
    printf '%s\n' "$rows" | awk '{gsub(":", "", $4); print $6, "/dev/bus/usb/" $2 "/" $4}'
}
current=$(device) || die 'No DLC10 found.'
echo "Before: $current"
if [[ $current == 03fd:0013* ]]; then
    echo 'Loading boot firmware with openFPGALoader...'
    # This old boot firmware may fail the preliminary JTAG scan; the required
    # result of this step is USB re-enumeration. Detection is checked after overlay.
    boot_rc=0
    "$ofl" --cable xilinxPlatformCableUsb "${misc_device[@]}" \
        --probe-firmware "$boot" --freq 500000 --detect --verbose-level 2 \
        >"$logs/boot.log" 2>&1 || boot_rc=$?
    echo "Boot command exit: $boot_rc (see boot.log)"
fi
# Require an operational node stable for several seconds before the next upload.
previous=''
stable=0
for ((attempt=0; attempt<30; attempt++)); do
    current=$(device) || current=''
    if [[ $current == 03fd:0008* && $current == "$previous" ]]; then
        stable=$((stable + 1))
        if ((stable >= 3)); then break; fi
    else
        stable=0
    fi
    previous=$current
    sleep 1
done
((stable >= 3)) || die "Cable did not stabilize as 03fd:0008; inspect $logs/boot.log and replug."
node=${current#* }
echo "Loading runtime overlay on $node with Python usbfs helper..."
if ! python3 "$stage2" --device "$node" --helper "$helper" --overlay "$overlay" \
    --timeout 10000 --verbose >"$logs/overlay.log" 2>&1; then
    tail -20 "$logs/overlay.log" >&2
    die 'Overlay upload failed; replug before retrying.'
fi
sleep 1
if ! "$ofl" --cable xilinxPlatformCableUsb "${misc_device[@]}" \
    --freq 500000 --detect --verbose-level 2 >"$logs/detect.log" 2>&1; then
    cat "$logs/detect.log"
    die 'FPGA detection failed.'
fi
cat "$logs/detect.log"
grep -q 'idcode 0x23751093' "$logs/detect.log" || die 'Expected YPCB XC7K480T IDCODE was not detected.'
echo 'PASS: DLC10 initialized and YPCB XC7K480T detected without Vivado.'
