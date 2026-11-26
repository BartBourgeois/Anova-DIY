"""Ask a SPI flash for its ID four ways over espserprog, and print the raw bytes (read-only; J-218).

When flashrom says "No EEPROM/flash device found", the raw answers tell the cases apart:
  FF FF FF everywhere   DO not driven: no contact on CS, CLK or DO, or the chip unpowered
  00 00 00 everywhere   DO held low: a short, HOLD# low, or the chip unpowered with DO clamped
  RDID FF, then RES and a second RDID answer: the chip was in deep power-down; RES (AB) woke it
  RDID right            the chip answers; flashrom's chip list or the speed is the question

Commands sent: RDID 9F, RES AB (release from deep power-down + electronic ID), RDID 9F again, REMS 90, RDSR 05.
None of them changes the memory; the firmware refuses write-type opcodes anyway. Needs pyserial.

Usage:  python -I tools/espserprog/idprobe.py COM<n> [hz]     (default 250000)
"""

import sys
import time

import serial

ACK = 0x06
CASES = [("RDID 9F", b"\x9f", 3), ("RES AB", b"\xab\x00\x00\x00", 1), ("RDID 9F again", b"\x9f", 3),
         ("REMS 90", b"\x90\x00\x00\x00", 2), ("RDSR 05", b"\x05", 1)]


def op(p, send: bytes, rlen: int):
    p.write(bytes([0x13]) + len(send).to_bytes(3, "little") + rlen.to_bytes(3, "little") + send)
    first = p.read(1)
    if first != bytes([ACK]):
        return None
    return p.read(rlen)


def main() -> int:
    hz = int(sys.argv[2]) if len(sys.argv) > 2 else 250000
    p = serial.Serial(sys.argv[1], 921600, timeout=1)
    time.sleep(1.5)  # the dev board resets when the port opens
    p.reset_input_buffer()
    p.write(b"\x10")
    print("SYNCNOP ->", p.read(2).hex(" "), "(expect 15 06)")
    p.write(b"\x14" + hz.to_bytes(4, "little"))
    r = p.read(5)
    print("SPI clock ->", int.from_bytes(r[1:5], "little") if len(r) == 5 and r[0] == ACK else r.hex(" "), "Hz")
    p.write(b"\x15\x01")
    p.read(1)
    for name, send, rlen in CASES:
        d = op(p, send, rlen)
        print(f"{name:14} -> {d.hex(' ') if d is not None else 'no ACK'}")
        time.sleep(0.01)
    p.write(b"\x15\x00")
    p.read(1)
    p.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
