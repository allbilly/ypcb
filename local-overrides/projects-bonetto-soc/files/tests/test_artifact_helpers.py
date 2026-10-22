"""Offline regressions for bitstream selectors and native-run supervision."""

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_script('fedora-check-bitstream')
runner = load_script('fedora-run-native-jtag')


def bitstream_fixture():
    """Build a structural fixture, not a programmable FPGA configuration."""
    word = lambda value: struct.pack('>I', value)
    payload = b''.join([
        word(0xAA995566), word(0x30018001), word(0x03751093),
        word(0x30004000), word(0x50000000 | 250001), b'\0' * (250001 * 4),
        word(0x30008002), word(5), word(13),
    ])
    header = struct.pack('>H', 9) + bytes.fromhex('0ff00ff00ff00ff000') + b'\0\1'
    for tag, value in [('a', 'offline-test'), ('b', checker.PART),
                       ('c', '2026/01/01'), ('d', '00:00:00')]:
        encoded = value.encode() + b'\0'
        header += tag.encode() + struct.pack('>H', len(encoded)) + encoded
    return header + b'e' + word(len(payload)) + payload


class SelectorChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bonetto-selector-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bit = self.root / 'fixture.bit'
        self.bit.write_bytes(bitstream_fixture())
        self.fasm = self.root / 'fixture.fasm'

    def check(self, text):
        self.fasm.write_text(text)
        return checker.check(self.bit, self.fasm, 1)

    def test_scalar_forms_and_disabled_other_chain(self):
        for expression in ['CHAIN_1', 'CHAIN_1[0]', "CHAIN_1[0:0] = 1'b01",
                           "CHAIN_1 = 1'h01", "CHAIN_1 = 'o1", 'CHAIN_1 = 0_1']:
            with self.subTest(expression=expression):
                report = self.check('CFG.BSCAN.JTAG_' + expression +
                                    "\nCFG.BSCAN.JTAG_CHAIN_2[0] = 1'b0\n")
                self.assertEqual(report['status'], 'PASS')

    def test_second_enabled_chain_cannot_be_hidden_by_spelling(self):
        for expression in ['CHAIN_2[0]', "CHAIN_2[0] = 1'b1", "CHAIN_2 = 1'h01",
                           "CHAIN_2 = 1'b01", "CHAIN_2 = 'd1"]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.check('CFG.BSCAN.JTAG_CHAIN_1\nCFG.BSCAN.JTAG_' + expression)

    def test_unsupported_and_conflicting_selectors_fail_closed(self):
        for expression in ['CHAIN_2[1]', 'CHAIN_2 = 2', "CHAIN_2 = 2'b01",
                           'CHAIN_2 = nonsense', 'CHAIN_5', 'CHAIN_1 = 0']:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.check('CFG.BSCAN.JTAG_CHAIN_1\nCFG.BSCAN.JTAG_' + expression)


def manifest_for(directory, command):
    structure_checker = SCRIPTS / 'fedora-check-vivado-bitstream.py'
    info = {
        'status': 'NATIVE_VIVADO_JTAG_ROUTE_AND_BITSTREAM_PREPARED',
        'inputs': [runner.describe(structure_checker)],
        'command': command,
        'structure_checker': runner.describe(structure_checker),
    }
    (directory / 'manifest.json').write_text(json.dumps(info))


class TimingChecks(unittest.TestCase):
    def test_finite_gate_values_and_rejections(self):
        with tempfile.TemporaryDirectory(prefix='bonetto-timing-test-') as temp:
            path = Path(temp) / 'gate.txt'
            path.write_text('WNS=0.000\nWHS=0.037\n')
            self.assertEqual(runner.read_timing_gate(path), {'WNS': '0.000', 'WHS': '0.037'})
            invalid = ['WNS=nan\nWHS=0\n', 'WNS=0\nWHS=NaN\n',
                       'WNS=inf\nWHS=0\n', 'WNS=0\nWHS=-Infinity\n',
                       'WNS=-0.001\nWHS=0\n', 'WNS=0\n', '',
                       'WNS=0\nWHS=0\nWNS=1\n', 'WNS=0\nWHS=0\nOTHER=1\n',
                       'WNS=0\nWHS=\n', 'WNS=0\nWHS\n']
            for text in invalid:
                with self.subTest(text=text), self.assertRaises(ValueError):
                    path.write_text(text)
                    runner.read_timing_gate(path)

    def test_native_run_rejects_nonfinite_slack_before_bitstream_check(self):
        for slack in ('nan', 'inf'):
            with self.subTest(slack=slack), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                (directory / 'output').mkdir()
                (directory / 'output/timing-gate.txt').write_text(f'WNS={slack}\nWHS=0\n')
                manifest_for(directory, [sys.executable, '-c', 'pass'])
                self.assertEqual(runner.run(directory), 1)
                info = json.loads((directory / 'manifest.json').read_text())
                self.assertEqual(info['status'], 'FAIL')
                self.assertIn('setup/hold', info['error'])
                self.assertFalse((directory / 'structure-check.log').exists())

    def test_success_records_limited_timing_scope_and_real_structure_check(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'output').mkdir()
            (directory / 'output/design.bit').write_bytes(bitstream_fixture())
            (directory / 'output/timing-gate.txt').write_text('WNS=0.139\nWHS=0.037\n')
            manifest_for(directory, [sys.executable, '-c', 'pass'])
            self.assertEqual(runner.run(directory), 0)
            info = json.loads((directory / 'manifest.json').read_text())
            self.assertEqual(info['timing_scope'], 'CONSTRAINED_SETUP_HOLD_ONLY')
            self.assertEqual(info['external_io_timing'], 'NOT_QUALIFIED')
            check = json.loads((directory / 'bitstream-structure-check.json').read_text())
            self.assertEqual(check['status'], 'PASS')


def running(pid):
    try:
        # A dead grandchild can briefly remain a zombie until the host reaps it.
        stat = Path(f'/proc/{pid}/stat').read_text()
        return stat.rsplit(')', 1)[1].split()[0] != 'Z'
    except FileNotFoundError:
        return False


def wait_until(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError('Timed out waiting for fake process state')


@contextmanager
def live_native_fixture():
    with tempfile.TemporaryDirectory(prefix='bonetto-runner-test-') as temp:
        directory = Path(temp)
        child_source = directory / 'child.py'
        # The grandchild ignores TERM to ensure cleanup reaches the entire group
        # even after its direct parent exits on TERM.
        grandchild = (
            'import os,signal,time;from pathlib import Path;'
            'signal.signal(signal.SIGTERM,signal.SIG_IGN);'
            'Path("grandchild.pid").write_text(str(os.getpid()));time.sleep(60)'
        )
        child_source.write_text(
            'import os,subprocess,sys,time\nfrom pathlib import Path\n'
            'Path("child.pid").write_text(str(os.getpid()))\n'
            f'subprocess.Popen([sys.executable,"-c",{grandchild!r}])\n'
            'time.sleep(60)\n'
        )
        command = [sys.executable, str(SCRIPTS / 'fedora-run-native-jtag.py'),
                   '--out', str(directory)]
        manifest_for(directory, [sys.executable, str(child_source)])
        controller = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            wait_until(lambda: (directory / 'grandchild.pid').exists())
            child_pid = int((directory / 'child.pid').read_text())
            grandchild_pid = int((directory / 'grandchild.pid').read_text())
            wait_until(lambda: json.loads((directory / 'manifest.json').read_text()).get('vivado_pid') == child_pid)
            yield directory, command, controller, child_pid, grandchild_pid
        finally:
            if controller.poll() is None:
                controller.send_signal(signal.SIGTERM)
            try:
                controller.communicate(timeout=12)
            except subprocess.TimeoutExpired:
                controller.kill()
                controller.communicate()
            if (directory / 'child.pid').exists():
                try:
                    os.killpg(int((directory / 'child.pid').read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux process supervision')
class LifecycleChecks(unittest.TestCase):
    def test_interrupt_during_spawn_still_reaps_new_child(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            manifest_for(directory, [sys.executable, '-c', 'import time; time.sleep(60)'])
            popen = subprocess.Popen
            children = []

            def launch_and_interrupt(*args, **kwargs):
                child = popen(*args, **kwargs)
                children.append(child)
                os.kill(os.getpid(), signal.SIGTERM)
                return child

            previous = signal.signal(signal.SIGTERM, runner.interrupted)
            try:
                with patch.object(runner.subprocess, 'Popen', side_effect=launch_and_interrupt):
                    self.assertEqual(runner.run(directory), 1)
                self.assertEqual(len(children), 1)
                self.assertIsNotNone(children[0].poll())
                self.assertFalse(running(children[0].pid))
            finally:
                signal.signal(signal.SIGTERM, previous)
                for child in children:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()

    def test_sigint_and_sigterm_stop_child_and_grandchild(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig), live_native_fixture() as fixture:
                directory, _, controller, child, grandchild = fixture
                controller.send_signal(sig)
                controller.communicate(timeout=12)
                self.assertEqual(controller.returncode, 1)
                wait_until(lambda: not running(child) and not running(grandchild))
                info = json.loads((directory / 'manifest.json').read_text())
                self.assertEqual(info['status'], 'FAIL')
                self.assertIn(signal.Signals(sig).name, info['error'])
                self.assertTrue((directory / 'native-command.exit').exists())

    def test_contending_controller_preserves_live_manifest(self):
        with live_native_fixture() as fixture:
            directory, command, controller, child, grandchild = fixture
            before = (directory / 'manifest.json').read_bytes()
            contender = subprocess.run(command, capture_output=True, text=True, timeout=5)
            self.assertEqual(contender.returncode, 1)
            self.assertIn('Another controller owns', contender.stderr)
            self.assertEqual((directory / 'manifest.json').read_bytes(), before)
            self.assertIsNone(controller.poll())
            self.assertTrue(running(child) and running(grandchild))


if __name__ == '__main__':
    unittest.main()
