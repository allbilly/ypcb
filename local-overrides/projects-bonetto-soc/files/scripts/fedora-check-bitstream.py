#!/usr/bin/env python3
"""Check an XC7K480T bitstream's structure and selected JTAG FASM feature.

With --pipeline-manifest, require the completed full OpenTPU DDR800 pipeline
and its exact recorded bitstream. This does not check CRC, timing or hardware.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

PART = 'xc7k480tffg1156-2'
FULL_CONFIG = dict(MCOLS=4, ACT_ROWS=4, LANES=8, VPU_CL=2,
                   MXU_IMPL=2, CORE_KHZ=100000, DDR_MTS=800)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_bitstream(data):
    require(len(data) > 1000000, 'Bitstream is unexpectedly small')
    pos = 0

    def take(n):
        nonlocal pos
        require(0 <= n <= len(data)-pos, 'Truncated bitstream header')
        chunk = data[pos:pos+n]
        pos += n
        return chunk

    def u16():
        return struct.unpack('>H', take(2))[0]

    require(take(u16()) == bytes.fromhex('0ff00ff00ff00ff000'), 'Invalid bit header signature')
    require(u16() == 1, 'Invalid bit header marker')
    fields = {}
    while True:
        tag = take(1).decode('ascii')
        if tag == 'e':
            length = struct.unpack('>I', take(4))[0]
            break
        require(tag in 'abcd' and tag not in fields, 'Unexpected or duplicate header field')
        fields[tag] = take(u16()).rstrip(b'\0').decode('ascii')
    require(set(fields) == set('abcd'), 'Missing required bitstream header field')
    payload = data[pos:]
    require(len(payload) == length, 'Declared payload length differs from file')
    require(fields['b'] == PART, 'Wrong FPGA part in bit header')
    require(len(payload) % 4 == 0, 'Misaligned configuration payload length')
    sync = payload.find(bytes.fromhex('aa995566'))
    require(0 <= sync < 128 and sync % 4 == 0, 'Missing or misaligned configuration sync word')
    cursor = sync+4
    last_reg = None
    ids, commands, packets = [], [], []
    fdri_words = 0
    while cursor < len(payload):
        offset = cursor
        word = struct.unpack_from('>I', payload, cursor)[0]
        cursor += 4
        if word in (0, 0xffffffff):
            continue
        kind, op = (word >> 29) & 7, (word >> 27) & 3
        require(kind in (1, 2), f'Unknown packet type at payload offset {offset}')
        require(op in (0, 1, 2), 'Reserved configuration opcode')
        if kind == 1:
            reg, count = (word >> 13) & 0x3fff, word & 0x7ff
            last_reg = reg
        else:
            require(last_reg is not None, 'Type-2 packet has no register context')
            reg, count = last_reg, word & 0x7ffffff
        require(cursor+4*count <= len(payload), 'Truncated configuration packet')
        packets.append(dict(offset=offset, data_offset=cursor, kind=kind, opcode=op,
                            register=reg, words=count))
        if op == 2 and reg in (4, 12):
            words = [struct.unpack_from('>I', payload, cursor+4*i)[0] for i in range(count)]
            (commands if reg == 4 else ids).extend(words)
        if op == 2 and reg == 2:
            fdri_words += count
        cursor += 4*count
    require(ids == [0x03751093], 'Configuration IDCODE does not match XC7K480T')
    require(fdri_words > 100000, 'No substantial frame-data packet')
    require(5 in commands and 13 in commands, 'Missing START or DESYNC command')
    return dict(header=fields, payload_offset=pos, payload_bytes=len(payload),
                sync_offset=sync, idcode=hex(ids[0]), fdri_words=fdri_words,
                commands=commands, packets=packets)


def jtag_features(text):
    """Read scalar chain selectors, rejecting syntax we cannot account for.

    This is deliberately not a general FASM parser. Other features are outside
    this check, but no BSCAN chain selector may be silently skipped.
    """
    features = set()
    values = {}
    for number, original in enumerate(text.splitlines(), 1):
        line = original.split('#', 1)[0].strip()
        if '.BSCAN.JTAG_CHAIN_' not in line:
            continue
        match = re.fullmatch(
            r"([A-Za-z][A-Za-z0-9_]*\.BSCAN\.JTAG_CHAIN_[1-4])"
            r"(?:\[0(?::0)?\])?(?:\s*=\s*(.+))?", line)
        require(match is not None, f'Unsupported JTAG selector on FASM line {number}')
        feature, literal = match.groups()
        value = 1
        if literal is not None:
            plain = re.fullmatch(r'[0-9_]+', literal)
            based = re.fullmatch(r"(?:(\d+)\s*)?'([bhdo])\s*([0-9a-fA-F_]+)", literal)
            require(plain is not None or based is not None,
                    f'Invalid JTAG selector value on FASM line {number}')
            if plain:
                value = int(literal.replace('_', ''), 10)
            else:
                width, base, digits = based.groups()
                require(width is None or int(width) == 1,
                        f'JTAG selector must be one bit on FASM line {number}')
                value = int(digits.replace('_', ''), {'b': 2, 'h': 16, 'd': 10, 'o': 8}[base])
            require(value in (0, 1), f'JTAG selector is not scalar on FASM line {number}')
        require(feature not in values or values[feature] == value,
                f'Conflicting JTAG selector values on FASM line {number}')
        values[feature] = value
        if value:
            features.add(feature)
    return features


def check(bit, fasm, chain, pipeline_manifest=None):
    bit, fasm = bit.resolve(), fasm.resolve()
    parsed = parse_bitstream(bit.read_bytes())
    features = jtag_features(fasm.read_text())
    require(len(features) == 1 and next(iter(features)).endswith('_'+str(chain)),
            'FASM does not select exactly the requested JTAG chain')
    provenance = None
    if pipeline_manifest:
        pipeline_manifest = pipeline_manifest.resolve()
        info = json.loads(pipeline_manifest.read_text())
        require(info.get('status') == 'FULL_CONFIGURATION_ASSEMBLY_PASS_TIMING_QUALIFICATION_INCOMPLETE',
                'Full pipeline has not completed bitstream assembly')
        require(info.get('configuration') == FULL_CONFIG, 'Full OpenTPU configuration differs')
        require(chain == 2, 'OpenTPU standalone image requires USER2')
        item = info['artifacts']['design.bit']
        require(Path(item['path']).resolve() == bit, 'Bitstream is not the selected pipeline artifact')
        require(sha(bit) == item['sha256'] and bit.stat().st_size == item['bytes'],
                'Bitstream differs from the recorded assembled artifact')
        frame_item = info['artifacts']['design.frames']
        frame = Path(frame_item['path']).resolve()
        require(frame == pipeline_manifest.parent/'design.frames', 'Wrong strict-frame artifact path')
        require(sha(frame) == frame_item['sha256'] and frame.stat().st_size == frame_item['bytes'],
                'Strict frames differ from the recorded assembled artifact')
        require(parsed['header']['a'].split(';', 1)[0] == str(frame),
                'Bitstream header refers to another frame input')
        require(fasm == pipeline_manifest.parent/'route/design.fasm', 'Wrong full-route FASM path')
        route_path = pipeline_manifest.parent/'route/manifest.json'
        route = json.loads(route_path.read_text())
        require(route.get('status') == 'ROUTE_PASS_TIMING_QUALIFICATION_INCOMPLETE',
                'Full route did not pass')
        require(route.get('parameters') == FULL_CONFIG, 'Routed full configuration differs')
        require(sha(fasm) == route['artifacts']['design.fasm']['sha256'],
                'FASM differs from the recorded full route')
        for name in ('carry_probe', 'cascade_probe'):
            require(name in info, 'Missing required correction gate: '+name)
            require(info[name]['status'] in (
                'CARRY_ROUTE_EQUIVALENCE_AND_STRICT_FRAMES_PASS',
                'PROBE_ROUTE_AND_STRICT_FRAMES_PASS_NUMERICAL_TIMING_NOT_QUALIFIED'),
                'Correction gate did not pass: '+name)
        provenance = dict(pipeline=str(pipeline_manifest), pipeline_sha256=sha(pipeline_manifest),
                          configuration=FULL_CONFIG)
    return dict(status='PASS', scope='Bitstream header, packet bounds, exact part/device ID and selected FASM JTAG feature',
                bit=str(bit), bytes=bit.stat().st_size, sha256=sha(bit),
                fasm=str(fasm), fasm_sha256=sha(fasm), jtag_chain=chain,
                structure=parsed, provenance=provenance, crc='NOT_CHECKED',
                numerical_timing='NOT_QUALIFIED', physical_hardware='NOT_RUN', programming='NOT_RUN')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bit', type=Path, required=True)
    ap.add_argument('--fasm', type=Path, required=True)
    ap.add_argument('--jtag-chain', type=int, choices=(1, 2, 3, 4), required=True)
    ap.add_argument('--pipeline-manifest', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    require(not args.out.exists(), 'Output report already exists')
    try:
        report = check(args.bit, args.fasm, args.jtag_chain, args.pipeline_manifest)
    except (ValueError, OSError, KeyError, struct.error) as error:
        report = dict(status='FAIL', error=str(error), physical_hardware='NOT_RUN', programming='NOT_RUN')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(args.out)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
