"""Exercise preparation helpers using temporary projects and fake hardware tools."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ENV_SCRIPT = ROOT / 'scripts/fedora-env.sh'
BUILD_SCRIPT = ROOT / 'scripts/fedora-build-bram.sh'
SPEC = importlib.util.spec_from_file_location('bonetto_workspace_paths', ROOT / 'scripts/workspace_paths.py')
PATHS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATHS)


class WorkspacePathsTest(unittest.TestCase):
    def test_shell_and_python_agree_on_workspace_and_ypcb(self):
        cases = [
            ({}, str(Path.home()), str(Path.home() / 'ypcb')),
            ({'OTPU_WORKSPACE_ROOT': '/tmp/legacy'}, '/tmp/legacy', '/tmp/legacy/ypcb'),
            ({'BONETTO_WORKSPACE_ROOT': '/tmp/bonetto', 'OTPU_WORKSPACE_ROOT': '/tmp/legacy'},
             '/tmp/bonetto', '/tmp/bonetto/ypcb'),
            ({'BONETTO_WORKSPACE_ROOT': '', 'OTPU_WORKSPACE_ROOT': '/tmp/legacy'},
             '/tmp/legacy', '/tmp/legacy/ypcb'),
            ({'BONETTO_WORKSPACE_ROOT': '/tmp/bonetto', 'YPCB_ROOT': '/tmp/shared'},
             '/tmp/bonetto', '/tmp/shared'),
        ]
        for overrides, workspace, ypcb in cases:
            with self.subTest(overrides=overrides):
                env = {key: value for key, value in os.environ.items()
                       if not key.startswith(('BONETTO_', 'OTPU_')) and key != 'YPCB_ROOT'}
                env.update(overrides)
                with patch.dict(os.environ, env, clear=True):
                    self.assertEqual(PATHS.expand_paths('@WORKSPACE@'), workspace)
                    self.assertEqual(PATHS.expand_paths('@YPCB@'), ypcb)
                result = subprocess.run(
                    ['bash', '-c', 'source "$1"; printf "%s\\n" "$BONETTO_WORKSPACE_ROOT" '
                     '"$YPCB_ROOT" "$BONETTO_HIMBAECHEL_BINARY" "${BONETTO_CABLE_INIT:-$YPCB_ROOT/dlc10-init.sh}" '
                     '"${BONETTO_LOADER_DONOR:-$YPCB_ROOT/openFPGALoader}"', 'test', str(ENV_SCRIPT)],
                    env=env, check=True, text=True, capture_output=True)
                self.assertEqual(result.stdout.splitlines(), [
                    workspace, ypcb,
                    workspace + '/tiny-gpu/build/ypcb/nextpnr-cli-build/nextpnr-himbaechel',
                    ypcb + '/dlc10-init.sh', ypcb + '/openFPGALoader'])

    def test_program_supplies_cpld_descriptor_without_hardware_or_ripgrep(self):
        with tempfile.TemporaryDirectory(prefix='bonetto-program-test-') as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            for name in ('fedora-env.sh', 'fedora-bringup.sh'):
                shutil.copyfile(ROOT / 'scripts' / name, root / 'scripts' / name)
            loader = root / 'build/openfpgaloader-xvc-dlc10/openFPGALoader'
            loader.parent.mkdir(parents=True)
            loader.write_text('#!' + sys.executable + '\nimport json, pathlib, sys\n'
                              'if "--help" in sys.argv: print("--xvc")\n'
                              'else: pathlib.Path("program-argv.json").write_text(json.dumps(sys.argv[1:]))\n')
            loader.chmod(0o755)
            bit = root / 'boards/ypcb-00338/build/bonetto_soc_ypcb00338_jtag_bram_first.bit'
            bit.parent.mkdir(parents=True)
            bit.write_bytes(b'fake bitstream for invocation test only')
            for artifact, receipt in ((loader, 'fedora-loader.sha256'), (bit, 'fedora-bram-inputs.sha256')):
                (root / 'build' / receipt).write_text(
                    hashlib.sha256(artifact.read_bytes()).hexdigest() + '  ' + str(artifact) + '\n')
            workspace = root / 'workspace'
            initializer = workspace / 'ypcb/dlc10-init.sh'
            initializer.parent.mkdir(parents=True)
            initializer.write_text('exit 0\n')
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith('BONETTO_') and key != 'YPCB_ROOT'}
            env['BONETTO_WORKSPACE_ROOT'] = str(workspace)
            fake_tools = root / 'fake-tools'
            fake_tools.mkdir()
            unavailable_rg = fake_tools / 'rg'
            unavailable_rg.write_text('#!/bin/sh\nexit 127\n')
            unavailable_rg.chmod(0o755)
            env['PATH'] = str(fake_tools) + os.pathsep + env['PATH']
            subprocess.run(['bash', str(root / 'scripts/fedora-bringup.sh'), 'program'],
                           env=env, check=True, capture_output=True, text=True)
            argv = json.loads((root / 'program-argv.json').read_text())
            self.assertEqual(argv[argv.index('--misc-device') + 1], '0x10931093,8,inspur_cpld')
            self.assertEqual(argv[argv.index('--index-chain') + 1], '0')
            self.assertEqual(argv[-1], str(bit))
            self.assertNotIn('--write-flash', argv)


class SynthesisProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='bonetto-synthesis-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.board = self.root / 'board'
        (self.board / 'constraints').mkdir(parents=True)
        (self.root / 'build').mkdir()
        shutil.copyfile(ROOT / 'boards/ypcb-00338/Makefile', self.board / 'Makefile')
        (self.board / 'rtl.v').write_text('module top; endmodule\n')
        (self.board / 'constraints/ypcb003381p1_active.xdc').write_text('# pins\n')
        tools = self.root / 'tools'
        tools.mkdir()
        self.yosys = tools / 'yosys'
        self.yosys.write_text('#!' + sys.executable + '\n'
                             'import json, os, pathlib, re, sys\n'
                             'counter = pathlib.Path("yosys-count")\n'
                             'count = int(counter.read_text()) + 1 if counter.exists() else 1\n'
                             'counter.write_text(str(count))\n'
                             'if os.environ.get("FAKE_YOSYS_FAIL"): sys.exit(1)\n'
                             'if os.environ.get("FAKE_MUTATE_INPUT"):\n'
                             '    with pathlib.Path("rtl.v").open("a") as f: f.write("// changed during synthesis\\n")\n'
                             'output = re.search(r"write_json ([^; ]+)", sys.argv[2])[1]\n'
                             'pathlib.Path(output).write_text(json.dumps({"invocation": count}))\n')
        self.yosys.chmod(0o755)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith('YOSYS_') and key not in ('MAKEFLAGS', 'MAKEFILES', 'MFLAGS')}
        self.env['PATH'] = str(tools) + os.pathsep + self.env['PATH']
        self.block = BUILD_SCRIPT.read_text().split("<<'PYSYNTH'\n", 1)[1].split('\nPYSYNTH\n', 1)[0]
        self.command = [sys.executable, '-', 'board', 'image', 'make', '-C', 'board',
                        'PROJECT=image', 'TOP=top', 'RTL=rtl.v', 'build/image.json', 'build/image.xdc']

    def run_synthesis(self, **overrides):
        return subprocess.run(self.command, input=self.block, env={**self.env, **overrides},
                              cwd=self.root, text=True, capture_output=True)

    def assert_synthesis_passes(self, count, **overrides):
        result = self.run_synthesis(**overrides)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(int((self.board / 'yosys-count').read_text()), count)

    def test_cache_reuses_only_matching_sources_recipes_tools_and_outputs(self):
        self.assert_synthesis_passes(1)
        self.assert_synthesis_passes(1)
        makefile = self.board / 'Makefile'
        makefile.write_text(makefile.read_text().replace('-flatten -abc9', '-flatten -noabc'))
        self.assert_synthesis_passes(2)
        self.assert_synthesis_passes(3, YOSYS_SYNTH_ARGS='-flatten')
        self.assert_synthesis_passes(3, YOSYS_SYNTH_ARGS='-flatten')
        self.env['YOSYS_SYNTH_ARGS'] = '-flatten'
        for path in (self.board / 'rtl.v', self.board / 'constraints/ypcb003381p1_active.xdc', self.yosys):
            stat = path.stat()
            with path.open('a') as stream:
                stream.write('\n# changed\n' if path == self.yosys else '\n// changed\n')
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            previous = int((self.board / 'yosys-count').read_text())
            self.assert_synthesis_passes(previous + 1)
        for suffix in ('.json', '.xdc'):
            (self.board / 'build' / ('image' + suffix)).write_text('unrecorded output\n')
            previous = int((self.board / 'yosys-count').read_text())
            self.assert_synthesis_passes(previous + 1)

    def test_failed_or_changing_synthesis_does_not_issue_a_receipt(self):
        receipt = self.root / 'build/fedora-bram-first-synthesis.json'
        result = self.run_synthesis(FAKE_YOSYS_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(receipt.exists())
        result = self.run_synthesis(FAKE_MUTATE_INPUT='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('inputs changed during the build', result.stderr)
        self.assertFalse(receipt.exists())
        self.assert_synthesis_passes(3)

    def test_noexec_make_modes_cannot_certify_new_sources_with_old_outputs(self):
        self.assert_synthesis_passes(1)
        receipt = self.root / 'build/fedora-bram-first-synthesis.json'
        original_receipt = receipt.read_bytes()
        outputs = [self.board / 'build' / ('image' + suffix) for suffix in ('.json', '.xdc')]
        original_outputs = {path: path.read_bytes() for path in outputs}
        (self.board / 'rtl.v').write_text('module changed; endmodule\n')
        for flags in ('n', '-n', 'Bn', '--just-print', '--dry-run', '--recon',
                      't', '--touch', 'q', '--question'):
            with self.subTest(MAKEFLAGS=flags):
                result = self.run_synthesis(MAKEFLAGS=flags)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(receipt.read_bytes(), original_receipt)
                self.assertEqual(int((self.board / 'yosys-count').read_text()), 1)
                for path in outputs:
                    self.assertEqual(path.read_bytes(), original_outputs[path])
        # Ordinary make variable overrides still reach the synthesis recipe.
        self.assert_synthesis_passes(2, MAKEFLAGS='-- YOSYS_SYNTH_ARGS=-flatten')
        self.assertIn('synth_xilinx -flatten -arch xc7',
                      json.loads(receipt.read_text())['inputs']['recipe'])

    def test_source_changes_during_later_stages_prevent_image_publication(self):
        self.assert_synthesis_passes(1)
        block = BUILD_SCRIPT.read_text().split("<<'PYRECHECK'\n", 1)[1].split('\nPYRECHECK\n', 1)[0]
        result = subprocess.run([sys.executable, '-'], input=block, cwd=self.root,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.board / 'rtl.v').write_text('module changed; endmodule\n')
        result = subprocess.run([sys.executable, '-'], input=block, cwd=self.root,
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('provenance changed before image publication', result.stderr)


if __name__ == '__main__':
    unittest.main()
