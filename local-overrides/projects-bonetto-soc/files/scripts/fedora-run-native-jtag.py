#!/usr/bin/env python3
"""Run the prepared OpenTPU native route and check its local bitstream.

The recorded timing gate covers constrained setup/hold paths only. External
DDR timing, pulse width, bus skew, CDC and functional retention need separate
review; a structural bitstream pass does not qualify those checks.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys


def describe(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha)


def read_timing_gate(path):
    fields = {}
    for line in path.read_text().splitlines():
        name, separator, value = line.partition('=')
        if not separator or name not in ('WNS', 'WHS') or name in fields:
            raise ValueError('Malformed or duplicate timing gate field: ' + line)
        slack = float(value)
        if not math.isfinite(slack) or slack < 0:
            raise ValueError('Native setup/hold timing did not close: ' + line)
        fields[name] = value
    if set(fields) != {'WNS', 'WHS'}:
        raise ValueError('Missing WNS or WHS timing gate field')
    return fields


@contextmanager
def ignore_interrupts():
    previous = {sig: signal.signal(sig, signal.SIG_IGN)
                for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


@contextmanager
def defer_interrupts():
    """Keep a signal from discarding a newly spawned Popen before assignment."""
    pending = []

    def defer(signum, frame):
        pending.append((signum, frame))

    previous = {sig: signal.signal(sig, defer)
                for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        for sig, frame in pending:
            handler = previous[sig]
            if callable(handler):
                handler(sig, frame)
            elif handler != signal.SIG_IGN:
                raise InterruptedError('Interrupted by ' + signal.Signals(sig).name)


def stop_child(child):
    """Stop the owned session, including descendants, and reap its leader."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # The leader may exit before a descendant (including one ignoring TERM).
    # Kill the original group even when wait() already reaped the leader.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait(timeout=5)


def run_locked(directory):
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

    child = None
    child_exit = None

    def invoke(command, log_name, exit_name, stage):
        nonlocal child, child_exit
        child_exit = directory / exit_name
        with (directory / log_name).open('x') as log:
            with defer_interrupts():
                child = subprocess.Popen(command, cwd=directory, stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
            fields = dict(stage=stage, child_pid=child.pid)
            if stage == 'native-vivado':
                fields['vivado_pid'] = child.pid
            save(**fields)
            code = child.wait()
        child_exit.write_text(str(code) + '\n')
        child = None
        return code

    try:
        verify()
        save(status='RUNNING', stage='native-vivado', controller_pid=os.getpid())
        command = info['command']
        code = invoke(command, 'native-command.log', 'native-command.exit', 'native-vivado')
        if code:
            raise RuntimeError('Vivado exited ' + str(code) + '; inspect native-command.log')
        verify()
        output = directory / 'output'
        gate = read_timing_gate(output / 'timing-gate.txt')
        bit = describe(output / 'design.bit')
        checker_command = [sys.executable, info['structure_checker']['path'], '--bit', bit['path'],
                           '--expected-sha256', bit['sha256'],
                           '--out', str(directory / 'bitstream-structure-check.json')]
        (directory / 'structure-check.command.json').write_text(json.dumps(checker_command, indent=2) + '\n')
        code = invoke(checker_command, 'structure-check.log', 'structure-check.exit',
                      'bitstream-structure-check')
        if code:
            raise RuntimeError('Independent native bitstream structure check failed')
        verify()
        artifacts = {p.name:describe(p) for p in output.iterdir() if p.is_file()}
        save(status='VIVADO_JTAG_BITSTREAM_STRUCTURAL_CHECK_PASS_PHYSICAL_TEST_NOT_RUN',
             stage='independently-checked', artifacts=artifacts, timing_gate=gate,
             timing_scope='CONSTRAINED_SETUP_HOLD_ONLY',
             external_io_timing='NOT_QUALIFIED', pulse_width='NOT_GATED',
             bus_skew='REPORT_ONLY', cdc='REPORT_ONLY',
             structure_check=describe(directory / 'bitstream-structure-check.json'),
             synthesis_warning_review='EIGHT_MEMORY_REMOVAL_WARNINGS_FUNCTION_RETENTION_UNPROVEN',
             physical_hardware='NOT_RUN', programming='NOT_RUN', flash_written=False)
        return 0
    except BaseException as error:
        with ignore_interrupts():
            if child is not None:
                try:
                    stop_child(child)
                except (OSError, subprocess.TimeoutExpired) as cleanup_error:
                    # Do not claim the run stopped when its child cannot be reaped.
                    save(status='RUNNING', stage='child-cleanup-failed', error=str(error),
                         cleanup_error=str(cleanup_error))
                    print(cleanup_error, file=sys.stderr)
                    return 1
                child_exit.write_text(str(child.returncode) + '\n')
            save(status='FAIL', error=str(error) or type(error).__name__)
        print(error, file=sys.stderr)
        return 1


def run(directory):
    directory = Path(directory).resolve()
    try:
        # Acquire before even reading the manifest. A competing invocation must
        # not change a live run's state or race its atomic manifest replacement.
        with (directory / '.native-run.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Another controller owns this native run') from None
            return run_locked(directory)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1


def interrupted(signum, _frame):
    raise InterruptedError('Interrupted by ' + signal.Signals(signum).name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(run(args.out.resolve()))
