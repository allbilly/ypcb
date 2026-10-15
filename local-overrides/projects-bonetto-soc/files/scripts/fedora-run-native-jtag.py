#!/usr/bin/env python3
"""Run the prepared native Vivado route and check its local bitstream."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def describe(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha)


def run(directory):
    manifest = directory / 'manifest.json'
    info = json.loads(manifest.read_text())
    if info['status'] != 'NATIVE_VIVADO_JTAG_ROUTE_AND_BITSTREAM_PREPARED':
        raise RuntimeError('Refusing to repeat a started or terminal run')

    def save(**fields):
        info.update(fields, updated_utc=datetime.now(timezone.utc).isoformat())
        temporary = manifest.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(info, indent=2) + '\n')
        temporary.replace(manifest)

    def verify():
        for item in info['inputs']:
            if describe(item['path']) != item:
                raise RuntimeError('Prepared input changed: ' + item['path'])

    try:
        verify()
        save(status='RUNNING', stage='native-vivado', controller_pid=os.getpid())
        command = info['command']
        with (directory / 'native-command.log').open('x') as log:
            child = subprocess.Popen(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT)
            save(vivado_pid=child.pid)
            code = child.wait()
        (directory / 'native-command.exit').write_text(str(code) + '\n')
        if code:
            raise RuntimeError('Vivado exited ' + str(code) + '; inspect native-command.log')
        verify()
        output = directory / 'output'
        gate = dict(line.split('=', 1) for line in (output / 'timing-gate.txt').read_text().splitlines())
        if float(gate['WNS']) < 0 or float(gate['WHS']) < 0:
            raise RuntimeError('Native setup/hold timing did not close')
        bit = describe(output / 'design.bit')
        checker_command = [sys.executable, info['structure_checker']['path'], '--bit', bit['path'],
                           '--expected-sha256', bit['sha256'],
                           '--out', str(directory / 'bitstream-structure-check.json')]
        (directory / 'structure-check.command.json').write_text(json.dumps(checker_command, indent=2) + '\n')
        with (directory / 'structure-check.log').open('x') as log:
            code = subprocess.run(checker_command, stdout=log, stderr=subprocess.STDOUT).returncode
        (directory / 'structure-check.exit').write_text(str(code) + '\n')
        if code:
            raise RuntimeError('Independent native bitstream structure check failed')
        verify()
        artifacts = {p.name:describe(p) for p in output.iterdir() if p.is_file()}
        save(status='VIVADO_JTAG_BITSTREAM_STRUCTURAL_CHECK_PASS_PHYSICAL_TEST_NOT_RUN',
             stage='independently-checked', artifacts=artifacts, timing_gate=gate,
             structure_check=describe(directory / 'bitstream-structure-check.json'),
             synthesis_warning_review='EIGHT_MEMORY_REMOVAL_WARNINGS_FUNCTION_RETENTION_UNPROVEN',
             physical_hardware='NOT_RUN', programming='NOT_RUN', flash_written=False)
        return 0
    except BaseException as error:
        save(status='FAIL', error=str(error))
        print(error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.out.resolve()))
