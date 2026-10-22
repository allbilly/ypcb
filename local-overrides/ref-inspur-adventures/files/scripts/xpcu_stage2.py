#!/usr/bin/env python3
"""Load the XPCU FX2 A3 helper and runtime overlay through Linux usbfs.

This is the Fedora replacement for fxload's second-stage RAM operation.
It deliberately targets volatile RAM only: no EEPROM requests are sent.
The initialized XPCU must already be visible as 03fd:0008.
"""

import argparse
import ctypes
import errno
import os
import pathlib
import sys


class ControlTransfer(ctypes.Structure):
    _fields_ = [
        ("request_type", ctypes.c_uint8),
        ("request", ctypes.c_uint8),
        ("value", ctypes.c_uint16),
        ("index", ctypes.c_uint16),
        ("length", ctypes.c_uint16),
        ("timeout", ctypes.c_uint32),
        ("data", ctypes.c_void_p),
    ]


# Linux _IOWR('U', 0, struct usbdevfs_ctrltransfer), including native pointer size.
USBDEVFS_CONTROL = 0xc0005500 | (ctypes.sizeof(ControlTransfer) << 16)
lib = ctypes.CDLL(None, use_errno=True)
lib.ioctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_void_p]
lib.ioctl.restype = ctypes.c_int


def parse_ihex(path):
    base = 0
    segment_address = None
    segment = bytearray()
    saw_eof = False
    saw_data = False

    def flush_segment():
        nonlocal segment_address, segment
        if segment:
            result = (segment_address, bytes(segment))
            segment_address = None
            segment = bytearray()
            return result
        return None

    with pathlib.Path(path).open("r", encoding="ascii") as image:
        for line_no, line in enumerate(image, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if saw_eof:
                raise ValueError(f"{path}:{line_no}: record after EOF")
            if not line.startswith(":"):
                raise ValueError(f"{path}:{line_no}: missing ':'")
            try:
                raw = bytes.fromhex(line[1:])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid HEX") from exc
            if len(raw) < 5 or len(raw) != raw[0] + 5:
                raise ValueError(f"{path}:{line_no}: invalid record length")
            if sum(raw) & 0xff:
                raise ValueError(f"{path}:{line_no}: checksum mismatch")
            count = raw[0]
            addr = (raw[1] << 8) | raw[2]
            record_type = raw[3]
            data = raw[4:4 + count]
            if record_type == 0x00:
                saw_data |= count > 0
                absolute = base + addr
                if absolute + count > 0x10000:
                    raise ValueError(f"{path}:{line_no}: address exceeds FX2 range")
                if segment and (absolute != segment_address + len(segment)
                                or len(segment) + len(data) > 1023):
                    result = flush_segment()
                    if result:
                        yield result
                if segment_address is None:
                    segment_address = absolute
                segment.extend(data)
            elif record_type == 0x01:
                if count != 0 or addr != 0:
                    raise ValueError(f"{path}:{line_no}: bad EOF record")
                saw_eof = True
            elif record_type == 0x02:
                if count != 2:
                    raise ValueError(f"{path}:{line_no}: bad segment record")
                base = int.from_bytes(data, "big") << 4
            elif record_type == 0x04:
                if count != 2:
                    raise ValueError(f"{path}:{line_no}: bad linear-address record")
                base = int.from_bytes(data, "big") << 16
            elif record_type in (0x03, 0x05):
                continue
            else:
                raise ValueError(f"{path}:{line_no}: unsupported record type {record_type:02x}")
    if not saw_eof:
        raise ValueError(f"{path}: missing EOF record")
    if not saw_data:
        raise ValueError(f"{path}: no firmware data")
    result = flush_segment()
    if result:
        yield result


def control_out(handle, request, address, payload, timeout):
    if not payload:
        array = (ctypes.c_uint8 * 1)()
    else:
        array = (ctypes.c_uint8 * len(payload))(*payload)
    for attempt in range(6):  # fxload: initial attempt plus five timeout retries.
        transfer = ControlTransfer(0x40, request, address, 0, len(payload),
                                   timeout, ctypes.cast(array, ctypes.c_void_p))
        rc = lib.ioctl(handle, USBDEVFS_CONTROL, ctypes.byref(transfer))
        error = ctypes.get_errno()
        if rc >= 0 or error != errno.ETIMEDOUT:
            break
    if rc < 0:
        raise RuntimeError(
            f"request=0x{request:02x} address=0x{address:04x}: {os.strerror(error)}"
        )
    if rc != len(payload):
        raise RuntimeError(
            f"request=0x{request:02x} address=0x{address:04x}: "
            f"short write {rc}/{len(payload)}"
        )


def write_image(handle, image, request, timeout, predicate=lambda _a, _d: True):
    records = bytes_sent = requests = 0
    for address, data in image:
        records += 1
        if not predicate(address, data):
            continue
        for offset in range(0, len(data), 1023):
            chunk = data[offset:offset + 1023]
            control_out(handle, request, address + offset, chunk, timeout)
            bytes_sent += len(chunk)
            requests += 1
    return records, bytes_sent, requests


def fx2_external(address, length):
    """Match fxload's FX2 memory split at 0x2000 (not FX2LP's 0x4000)."""
    if address <= 0x1fff:
        return address + length > 0x2000
    if 0xe000 <= address <= 0xe1ff:
        return address + length > 0xe200
    return True


def load_stage2(helper, overlay, device, timeout, verbose):
    # Validate both images before modifying volatile device RAM.
    helper_image = list(parse_ihex(helper))
    overlay_image = list(parse_ihex(overlay))
    handle = os.open(device, os.O_RDWR | os.O_CLOEXEC)
    try:
        # Do not claim interface 0.  fxload uses Linux usbfs ioctl directly,
        # and the FX2 vendor requests are device-recipient control transfers;
        # avoiding a claim preserves that behavior and works with udev rules.
        # Stage 1: stop the FX2 CPU and install the generic A3 loader.
        control_out(handle, 0xa0, 0xe600, b"\x01", timeout)
        r, b, q = write_image(handle, helper_image, 0xa0, timeout)
        if verbose:
            print(f"helper: {r} records, {b} bytes, {q} A0 requests")
        control_out(handle, 0xa0, 0xe600, b"\x00", timeout)
        # Stage 2a: while the helper runs, write external overlay memory.
        r, b, q = write_image(
            handle, overlay_image, 0xa3, timeout,
            lambda address, data: fx2_external(address, len(data)),
        )
        if verbose:
            print(f"overlay external: {r} records, {b} bytes, {q} A3 requests")

        # Stage 2b: stop the CPU, write internal overlay memory, then run.
        control_out(handle, 0xa0, 0xe600, b"\x01", timeout)
        r, b, q = write_image(
            handle, overlay_image, 0xa0, timeout,
            lambda address, data: not fx2_external(address, len(data)),
        )
        if verbose:
            print(f"overlay internal: {r} records, {b} bytes, {q} A0 requests")
        control_out(handle, 0xa0, 0xe600, b"\x00", timeout)
    finally:
        os.close(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", required=True, metavar="HEX")
    parser.add_argument("--overlay", required=True, metavar="HEX")
    parser.add_argument("--device", required=True, metavar="/dev/bus/usb/BUS/DEV")
    parser.add_argument("--timeout", type=int, default=10000, metavar="MS")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    try:
        load_stage2(args.helper, args.overlay, args.device,
                    args.timeout, args.verbose)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"xpcu_stage2: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
