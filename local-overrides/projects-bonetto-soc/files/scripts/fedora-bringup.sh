#!/usr/bin/env bash
# Fedora preparation and SRAM-only hardware steps for the current upstream image.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/fedora-env.sh"
cd "$BONETTO_ROOT"
board=boards/ypcb-00338
ofl="$BONETTO_ROOT/build/openfpgaloader-xvc-dlc10/openFPGALoader"
bit="$BONETTO_ROOT/$board/build/bonetto_soc_ypcb00338_jtag_bram_first.bit"
init=${BONETTO_CABLE_INIT:-${YPCB_ROOT:-$HOME/ypcb}/dlc10-init.sh}
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
[[ $# -le 1 ]] || die 'Usage: bash scripts/fedora-bringup.sh [check|sim-bram|formal-bram|build|detect|program|xvc|validate]'

require_loader() {
    [[ -x "$ofl" ]] || die "Build the XVC-enabled loader first: $ofl"
    [[ -r build/fedora-loader.sha256 ]] || die 'Run bash scripts/fedora-build-loader.sh to record the loader build.'
    sha256sum --check --status build/fedora-loader.sha256 || die 'Loader or its recorded source changed; rebuild it.'
    "$ofl" --help | grep -F -- '--xvc' >/dev/null || die 'The selected loader has no XVC support.'
}

require_bit() {
    [[ -s "$bit" && -r build/fedora-bram-inputs.sha256 ]] || die 'Run bash scripts/fedora-bringup.sh build first.'
    sha256sum --check --status build/fedora-bram-inputs.sha256 || die 'BRAM bitstream or hardware inputs changed; rebuild it.'
}

case ${1:-check} in
    check)
        for tool in yosys nextpnr-himbaechel fasm2frames xc7frames2bit iverilog vvp sby z3 yices-smt2; do
            command -v "$tool" || die "Missing tool: $tool"
        done
        "$COCOTB_PYTHON" -c 'import cocotb, cocotb_tools; print("cocotb", cocotb.__version__)'
        [[ -r "$PRJXRAY_DB_DIR/kintex7/xc7k480tffg1156-2/part.yaml" ]] || die 'Missing exact-part database'
        [[ -r "$BONETTO_HIMBAECHEL_CHIPDB" ]] || die 'Missing native chip database'
        require_loader
        require_bit
        [[ -r "$init" ]] || die "Missing cable initializer: $init"
        printf 'Host preparation is ready; physical hardware has not been validated.\n'
        if ! lsusb -d 03fd: | grep -E '03fd:(0013|0008)'; then
            printf 'DLC10 is disconnected. Attach it and power the board before detect/program.\n'
        fi
        ;;
    sim-bram)
        make lint
        make -C ip/wishbone sim
        make -C ip/wb-memory sim
        make -C ip/jtag-uart/sim -f Makefile.cocotb COCOTB_RESULTS_FILE=results_uart.xml
        make -C ip/jtag-uart/sim -f Makefile.jwb COCOTB_RESULTS_FILE=results_jwb.xml
        make -C "$board/sim" -f Makefile.cocotb
        make -C "$board/sim" -f Makefile.clk_liveness
        make -C "$board/sim" -f Makefile.memtest
        mkdir -p build/first-bram-sim
        iverilog -g2012 -DBONETTO_SOC_SIM -s tb_jtag_bram_first \
            -o build/first-bram-sim/test.vvp "$board/sim/tb_jtag_bram_first.sv" \
            "$board/rtl/top_jtag_bram_first.v" "$board/rtl/top_jtag_bram.v" \
            ip/wb-memory/rtl/wb_memory.v ip/jtag-uart/rtl/jtag_uart.v \
            ip/jtag-uart/rtl/jtag_wb_master.v ip/wishbone/rtl/wb_decode2.v
        timeout 120 vvp build/first-bram-sim/test.vvp
        iverilog -g2012 -DBONETTO_SOC_SIM -s tb_jtag_bram_first \
            -Ptb_jtag_bram_first.FIRST_PROFILE=0 \
            -o build/first-bram-sim/default.vvp "$board/sim/tb_jtag_bram_first.sv" \
            "$board/rtl/top_jtag_bram_first.v" "$board/rtl/top_jtag_bram.v" \
            ip/wb-memory/rtl/wb_memory.v ip/jtag-uart/rtl/jtag_uart.v \
            ip/jtag-uart/rtl/jtag_wb_master.v ip/wishbone/rtl/wb_decode2.v
        timeout 120 vvp build/first-bram-sim/default.vvp
        ;;
    formal-bram)
        make formal-wishbone formal-wb-memory SOLVER=yices
        # Keep upstream assertions and depth 30; use the faster native solver.
        # Put the work directories under build rather than into source folders.
        for spec in ip/jtag-uart/formal/jtag_wb_master.sby "$board/formal/memtest_lite.sby"; do
            name=$(basename "$spec" .sby)
            (
                cd "$(dirname "$spec")"
                sed 's/smtbmc z3/smtbmc yices/g' "$name.sby" |
                    sby -f --prefix "$BONETTO_ROOT/build/formal-$name"
            )
        done
        ;;
    build)
        bash scripts/fedora-build-bram.sh
        ;;
    detect)
        bash "$init"
        ;;
    program)
        require_loader
        require_bit
        bash "$init"
        "$ofl" --cable xilinxPlatformCableUsb \
            --misc-device 0x10931093,8,inspur_cpld \
            --freq 6000000 --index-chain 0 "$bit"
        ;;
    xvc)
        require_loader
        # This loader waits on getchar(). Keep stdin open without a tail process,
        # including when launched from a noninteractive shell.
        fifo_dir=$(mktemp -d)
        mkfifo "$fifo_dir/stdin"
        exec 3<>"$fifo_dir/stdin"
        trap 'exec 3>&-; rm -- "$fifo_dir/stdin"; rmdir -- "$fifo_dir"' EXIT
        "$ofl" --cable xilinxPlatformCableUsb --freq 750000 --xvc --port 3721 <&3
        ;;
    validate)
        require_bit
        log="build/fedora-hardware-bram-$(date -u +%Y%m%dT%H%M%SZ).log"
        "$COCOTB_PYTHON" tools/jtag_bram_validate.py --profile first --tck-ns 1334 2>&1 | tee "$log"
        ;;
    *) die 'Unknown action. Use check, sim-bram, formal-bram, build, detect, program, xvc or validate.' ;;
esac
