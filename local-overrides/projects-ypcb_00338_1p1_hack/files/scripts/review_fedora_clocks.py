#!/usr/bin/env python3
"""Review supplied MicroBlaze clock/reset connections without accessing JTAG."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "build/fedora-baseline/hardware/top.hwh"
OUT = ROOT / "build/fedora-microblaze/clock-review.json"


def main():
    raw = SOURCE.read_bytes()
    tree = ET.fromstring(raw)
    modules = {m.get("INSTANCE"): m for m in tree.findall(".//MODULE")}
    names = ("microblaze_0", "mdm_1", "clk_wiz_1", "rst_clk_wiz_1_100M",
             "axi_smc", "mig_7series_0", "rst_mig_7series_0_133M",
             "rst_mig_7series_0_133M_1", "microblaze_0_axi_periph", "xdma_0")
    clocks, interfaces = {}, {}
    for name in names:
        module = modules[name]
        clocks[name] = {p.get("NAME"): dict(p.attrib)
                        for p in module.findall("./PORTS/PORT")
                        if p.get("SIGIS") in ("clk", "rst")
                        or p.get("NAME") == "dcm_locked"}
        interfaces[name] = {}
        for bus in module.findall("./BUSINTERFACES/BUSINTERFACE"):
            if bus.get("VLNV", "").endswith("aximm:1.0"):
                params = {p.get("NAME"): p.get("VALUE")
                          for p in bus.iter("PARAMETER")}
                interfaces[name][bus.get("NAME")] = {
                    "bus": bus.get("BUSNAME"),
                    "clock_domain": params.get("CLK_DOMAIN"),
                    "frequency_hz": params.get("FREQ_HZ"),
                    "address_bits": params.get("ADDR_WIDTH"),
                }
    expected = {
        ("clk_wiz_1", "clk_in1"): "External_Ports_SYS_CLK",
        ("microblaze_0", "Clk"): "clk_wiz_1_clk_out1",
        ("mdm_1", "S_AXI_ACLK"): "clk_wiz_1_clk_out1",
        ("rst_clk_wiz_1_100M", "ext_reset_in"): "External_Ports_SYS_RSTN",
        ("rst_clk_wiz_1_100M", "dcm_locked"): "clk_wiz_1_locked",
        ("axi_smc", "aresetn"): "rst_clk_wiz_1_100M_peripheral_aresetn",
        ("axi_smc", "aclk1"): "clk_wiz_1_clk_out1",
        ("axi_smc", "aclk"): "mig_7series_0_c0_ui_clk",
        ("axi_smc", "aclk2"): "mig_7series_0_c1_ui_clk",
        ("axi_smc", "aclk3"): "xdma_0_axi_aclk",
        ("mig_7series_0", "sys_rst"): "External_Ports_SYS_RSTN",
        ("mig_7series_0", "c0_aresetn"): "rst_mig_7series_0_133M_peripheral_aresetn",
        ("mig_7series_0", "c1_aresetn"): "rst_mig_7series_0_133M_1_peripheral_aresetn",
    }
    mismatches = {f"{module}/{port}": clocks[module][port].get("SIGNAME")
                  for (module, port), net in expected.items()
                  if clocks[module][port].get("SIGNAME") != net}
    result = {
        "status": "STATIC_CONNECTIONS_VERIFIED" if not mismatches else "MISMATCH",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "clocks": clocks, "axi_interfaces": interfaces,
        "checked_connections": len(expected), "mismatches": mismatches,
        "physical_test": "NOT_RUN",
        "note": "CPU/MDM and SmartConnect global reset use board clock/reset. "
                "CPU S00_AXI uses the board-derived clock; DDR M00/M01 use "
                "their own MIG clocks. XDMA S01_AXI is a separate clock domain. "
                "SmartConnect startup with an absent PCIe clock and physical "
                "CPU/DDR operation still require the powered-board run.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{result['status']}: {len(expected)} clock/reset connections; {OUT}")
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
