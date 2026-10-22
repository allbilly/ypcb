"""Offline regressions: mock USB/FTDI calls; never open a hardware device."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "local-overrides/ref-inspur-adventures/files/scripts/xpcu_stage2.py"
spec = importlib.util.spec_from_file_location("xpcu_stage2", HELPER)
stage2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage2)


def ihex(address, payload=b"", kind=0):
    record = bytes([len(payload), address >> 8, address & 255, kind]) + payload
    return ":" + (record + bytes([-sum(record) & 255])).hex() + "\n"


EOF = ihex(0, kind=1)


class Stage2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ypcb-stage2-test-")
        self.addCleanup(self.temp.cleanup)
        self.helper = Path(self.temp.name) / "helper.hex"
        self.overlay = Path(self.temp.name) / "overlay.hex"
        self.helper.write_text(ihex(0x100, b"\x12") + EOF)
        self.overlay.write_text(ihex(0, b"\x34") + ihex(0x2000, b"\x56") + EOF)

    def test_invalid_images_rejected_before_opening_device(self):
        invalid = {
            "empty": "",
            "no data": EOF,
            "truncated": ihex(0, b"\x00"),
            "EOF with data": ihex(0, b"\x00", kind=1),
            "EOF with address": ihex(1, kind=1),
            "data after EOF": ihex(0, b"\x00") + EOF + ihex(1, b"\x00"),
        }
        for target in (self.helper, self.overlay):
            original = target.read_text()
            for name, content in invalid.items():
                with self.subTest(image=target.name, defect=name):
                    target.write_text(content)
                    with mock.patch.object(stage2.os, "open") as device_open:
                        with mock.patch.object(stage2, "control_out") as transfer:
                            with self.assertRaises(ValueError):
                                stage2.load_stage2(self.helper, self.overlay,
                                                   "unused", 10000, False)
                    device_open.assert_not_called()
                    transfer.assert_not_called()
            target.write_text(original)

    def test_upload_preserves_staging_order(self):
        with mock.patch.object(stage2.os, "open", return_value=42):
            with mock.patch.object(stage2.os, "close") as close:
                with mock.patch.object(stage2, "control_out") as transfer:
                    stage2.load_stage2(self.helper, self.overlay, "unused", 10000, False)
        self.assertEqual([call.args[1:4] for call in transfer.call_args_list], [
            (0xa0, 0xe600, b"\x01"),
            (0xa0, 0x100, b"\x12"),
            (0xa0, 0xe600, b"\x00"),
            (0xa3, 0x2000, b"\x56"),
            (0xa0, 0xe600, b"\x01"),
            (0xa0, 0, b"\x34"),
            (0xa0, 0xe600, b"\x00"),
        ])
        close.assert_called_once_with(42)

    def test_upload_uses_the_validated_snapshot(self):
        def open_device(*_args):
            self.helper.write_text("")
            self.overlay.write_text("")
            return 42

        with mock.patch.object(stage2.os, "open", side_effect=open_device):
            with mock.patch.object(stage2.os, "close"):
                with mock.patch.object(stage2, "control_out") as transfer:
                    stage2.load_stage2(self.helper, self.overlay, "unused", 10000, False)
        self.assertEqual(len(transfer.call_args_list), 7)


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("cc") or not shutil.which("c++"):
            raise unittest.SkipTest("C and C++ compilers are required")
        cls.temp = tempfile.TemporaryDirectory(prefix="ypcb-native-test-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory = Path(cls.temp.name)
        cls.trace = cls.directory / "trace.so"
        cls.usb = cls.directory / "mock.so"
        cls.probe = cls.directory / "probe"
        cls.writer = cls.directory / "writer"
        cls.compile(["cc", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC",
                     "-o", str(cls.trace), str(ROOT / "dlc10_usb_trace.c"), "-ldl"])
        cls.source("mock.c", r'''
#include <libusb-1.0/libusb.h>
int libusb_control_transfer(libusb_device_handle *h, uint8_t a, uint8_t b,
        uint16_t c, uint16_t d, unsigned char *e, uint16_t f, unsigned int g)
{ return f; }
int libusb_reset_device(libusb_device_handle *h) { return 7; }
int libusb_submit_transfer(struct libusb_transfer *t) { return 9; }
''')
        cls.compile(["cc", "-shared", "-fPIC", "-o", str(cls.usb),
                     str(cls.directory / "mock.c")])
        cls.source("probe.c", r'''
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libusb-1.0/libusb.h>
int main(int argc, char **argv) {
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
    if (!h) return 10;
    if (!strcmp(argv[2], "missing")) {
        const char *names[] = {"libusb_control_transfer", "libusb_reset_device",
                               "libusb_submit_transfer"};
        for (int i = 0; i < 3; i++) if (dlsym(h, names[i])) return 11;
        puts("missing symbols remain NULL");
        return 0;
    }
    if (!strcmp(argv[2], "default")) h = RTLD_DEFAULT;
    int (*ctrl)(libusb_device_handle *, uint8_t, uint8_t, uint16_t, uint16_t,
                unsigned char *, uint16_t, unsigned int) =
        dlsym(h, "libusb_control_transfer");
    int (*reset)(libusb_device_handle *) = dlsym(h, "libusb_reset_device");
    int (*submit)(struct libusb_transfer *) = dlsym(h, "libusb_submit_transfer");
    if (!ctrl || !reset || !submit) return 12;
    unsigned char payload[] = {0xc7, 0x3a};
    unsigned char buffer[LIBUSB_CONTROL_SETUP_SIZE + 2] = {0};
    libusb_fill_control_setup(buffer, 0x40, 0xa3, 0x2000, 0, 2);
    memcpy(buffer + LIBUSB_CONTROL_SETUP_SIZE, payload, 2);
    struct libusb_transfer transfer = {0};
    transfer.type = LIBUSB_TRANSFER_TYPE_CONTROL;
    transfer.buffer = buffer;
    transfer.length = sizeof(buffer);
    transfer.timeout = 100;
    printf("control=%d reset=%d submit=%d\n",
           ctrl(NULL, 0x40, 0xa0, 0, 0, payload, 2, 100),
           reset(NULL), submit(&transfer));
    buffer[0] = 0xc0; /* IN transfers have no completed payload at submit time. */
    printf("submit_in=%d\n", submit(&transfer));
    return 0;
}
''')
        cls.compile(["cc", "-o", str(cls.probe), str(cls.directory / "probe.c"), "-ldl"])
        cls.source("writer.cpp", r'''
#define main loopback_main
#include "smt2_tdo_loopback.cpp"
#undef main
static int mode;
static unsigned char written[4];
static int count;
extern "C" int ftdi_write_data(struct ftdi_context *, const unsigned char *data, int len) {
    if (mode == 0) return 0;
    if (mode == 1) return -1;
    written[count++] = data[0];
    return 1;
}
extern "C" const char *ftdi_get_error_string(struct ftdi_context *) { return "mock error"; }
int main(int argc, char **argv) {
    mode = argv[1][0] - '0';
    const unsigned char expected[] = {0x12, 0x34, 0x56};
    bool success = write_all(nullptr, expected, sizeof(expected));
    if (mode < 2) return success ? 1 : 0;
    return success && count == 3 && !memcmp(expected, written, 3) ? 0 : 2;
}
''')
        cls.compile(["c++", "-I", str(ROOT), "-ffunction-sections", "-fdata-sections",
                     "-Wl,--gc-sections", "-o", str(cls.writer),
                     str(cls.directory / "writer.cpp")])

    @classmethod
    def source(cls, name, contents):
        (cls.directory / name).write_text(contents)

    @staticmethod
    def compile(command):
        subprocess.run(command, check=True, capture_output=True, text=True)

    def probe_run(self, mode, library=None):
        env = dict(os.environ, LD_PRELOAD=str(self.trace))
        return subprocess.run([str(self.probe), str(library or self.usb), mode],
                              env=env, check=True, capture_output=True, text=True, timeout=5)

    def test_failed_symbol_lookup_stays_failed(self):
        result = self.probe_run("missing", "libc.so.6")
        self.assertIn("missing symbols remain NULL", result.stdout)

    def test_default_symbol_lookup_does_not_recurse(self):
        result = self.probe_run("default")
        self.assertIn("control=2 reset=7 submit=9", result.stdout)

    def test_explicit_library_lookup_still_traces(self):
        result = self.probe_run("explicit")
        self.assertIn("control=2 reset=7 submit=9", result.stdout)
        self.assertIn("DLC10_USB ctrl", result.stderr)

    def test_trace_contains_hashes_without_payload_bytes(self):
        result = self.probe_run("default")
        self.assertIn("hash=", result.stderr)
        self.assertNotIn("first=", result.stderr)
        self.assertNotIn("data=", result.stderr)
        self.assertIn("submit-ctrl type=c0", result.stderr)

    def test_zero_progress_write_fails_promptly(self):
        result = subprocess.run([str(self.writer), "0"], check=True,
                                capture_output=True, text=True, timeout=5)
        self.assertIn("transfer made no progress", result.stderr)

    def test_negative_write_error_fails(self):
        subprocess.run([str(self.writer), "1"], check=True,
                       capture_output=True, text=True, timeout=5)

    def test_partial_writes_preserve_payload(self):
        subprocess.run([str(self.writer), "2"], check=True,
                       capture_output=True, text=True, timeout=5)


class PackagingTests(unittest.TestCase):
    def test_packaging_patches_restore_current_sources(self):
        relative_helper = HELPER.relative_to(ROOT)
        for name in ("dlc10-fedora-wrapper.patch", "dlc10-fedora-python-stage2.patch"):
            with self.subTest(patch=name), tempfile.TemporaryDirectory(prefix="ypcb-patch-test-") as path:
                destination = Path(path)
                subprocess.run(["git", "init", "-q", str(destination)], check=True)
                subprocess.run(["git", "-C", path, "apply", "--check", str(ROOT / name)],
                               check=True, capture_output=True, text=True)
                subprocess.run(["git", "-C", path, "apply", str(ROOT / name)], check=True)
                for relative in (Path("dlc10-init.sh"), relative_helper):
                    self.assertEqual((destination / relative).read_bytes(),
                                     (ROOT / relative).read_bytes())
                self.assertTrue(os.access(destination / "dlc10-init.sh", os.X_OK))


if __name__ == "__main__":
    unittest.main()
