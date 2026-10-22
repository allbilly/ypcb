"""Exercise both BRAM tops and prove the integration bench rejects unknowns."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "boards/ypcb-00338/sim/tb_jtag_bram_first.sv",
    "boards/ypcb-00338/rtl/top_jtag_bram_first.v",
    "boards/ypcb-00338/rtl/top_jtag_bram.v",
    "ip/wb-memory/rtl/wb_memory.v",
    "ip/jtag-uart/rtl/jtag_uart.v",
    "ip/jtag-uart/rtl/jtag_wb_master.v",
    "ip/wishbone/rtl/wb_decode2.v",
]


@unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                     "Icarus Verilog is required")
class BramProfiles(unittest.TestCase):
    def run_bench(self, profile, unknown_signal=None):
        with tempfile.TemporaryDirectory(prefix="bonetto-bram-profiles-") as directory:
            work = Path(directory)
            sources = [str(ROOT / source) for source in SOURCES]
            options = ["-s", "tb_jtag_bram_first",
                       f"-Ptb_jtag_bram_first.FIRST_PROFILE={profile}"]
            if unknown_signal is not None:
                # Drive only the bench observation; normal memory behavior
                # must not conceal an unknown completion/reset indication.
                fault = work / "fault.sv"
                trigger = "#1;" if unknown_signal == "rst" else "wait (bench.rst === 1'b0);"
                fault.write_text(
                    "`timescale 1ns/1ps\n"
                    "module fault;\n"
                    f"tb_jtag_bram_first #(.FIRST_PROFILE({profile})) bench();\n"
                    f"initial begin {trigger} force bench.{unknown_signal} = 1'bx; end\n"
                    "endmodule\n"
                )
                sources.append(str(fault))
                options = ["-s", "fault"]
            binary = work / "test.vvp"
            subprocess.run(
                ["iverilog", "-g2012", "-DBONETTO_SOC_SIM", *options,
                 "-o", str(binary), *sources],
                check=True, capture_output=True, text=True, timeout=30,
            )
            return subprocess.run(["vvp", str(binary)], capture_output=True,
                                  text=True, timeout=30)

    def test_profiles(self):
        for profile, words in ((1, 2048), (0, 8)):
            with self.subTest(first_profile=profile):
                result = self.run_bench(profile)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"RESULT PASS: first_profile={profile}; {words} words;",
                              result.stdout)

    def test_unknown_status_is_rejected(self):
        for signal in ("jwb_busy", "jwb_last_ack", "jwb_last_err", "rst"):
            with self.subTest(signal=signal):
                result = self.run_bench(1, unknown_signal=signal)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("FATAL:", result.stdout)
                self.assertNotIn("RESULT PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
