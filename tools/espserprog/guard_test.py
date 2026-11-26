"""Check espserprog's write guard over raw serprog packets, with nothing (or anything) on its pins (J-212).

Sends SYNCNOP, then SPI operations: reads (RDID 0x9F, READ 0x03, RDSR 0x05) must be accepted (ACK + data), and every
write-type opcode (WREN 0x06, EWSR 0x50, page program 0x02, sector erase 0x20, chip erases 0xC7 and 0x60, WRSR 0x01)
must be refused (NAK) before it reaches the chip. Then pin drivers off and a NOP: still in sync. Exit 0 if all is as
expected. Needs pyserial (any venv that has it).

Usage:  python -I tools/espserprog/guard_test.py COM<n>
"""

import sys
import time

import serial

ACK, NAK = 0x06, 0x15
CASES = [("RDID 9F, read 3", b"\x9f", 3, ACK), ("READ 03 at 0, read 16", b"\x03\x00\x00\x00", 16, ACK),
         ("WREN 06", b"\x06", 0, NAK), ("EWSR 50", b"\x50", 0, NAK), ("PP 02 + 1 byte", b"\x02\x00\x00\x00\xaa", 0, NAK),
         ("SE 20", b"\x20\x00\x00\x00", 0, NAK), ("CE C7", b"\xc7", 0, NAK), ("CE 60", b"\x60", 0, NAK),
         ("WRSR 01", b"\x01\x00", 0, NAK), ("RDSR 05, read 1", b"\x05", 1, ACK)]


def main() -> int:
    p = serial.Serial(sys.argv[1], 921600, timeout=1)
    time.sleep(1.0)  # the dev board may reset when the port opens
    p.reset_input_buffer()
    p.write(b"\x10")
    sync = p.read(2)
    print("SYNCNOP ->", sync.hex(" "), "(expect 15 06)")
    ok = sync == bytes([NAK, ACK])
    for name, send, rlen, want in CASES:
        p.write(bytes([0x13]) + len(send).to_bytes(3, "little") + rlen.to_bytes(3, "little") + send)
        first = p.read(1)
        got = first[0] if first else None
        data = p.read(rlen) if got == ACK else b""
        good = got == want
        ok &= good
        print(f"{name:24} -> {'ACK' if got == ACK else 'NAK' if got == NAK else repr(first)}"
              f"{' ' + data.hex(' ') if data else ''}  {'ok' if good else 'UNEXPECTED'}")
    p.write(b"\x15\x00")
    off = p.read(1)
    p.write(b"\x00")
    nop = p.read(1)
    print("S_PIN_STATE 0 ->", off.hex(), "; NOP ->", nop.hex(), "(expect 06, 06)")
    ok &= off == bytes([ACK]) and nop == bytes([ACK])
    print("ALL AS EXPECTED" if ok else "SOMETHING UNEXPECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
