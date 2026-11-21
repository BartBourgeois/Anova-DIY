"""Decompress one TI ARM compiler C start-up record (LZSS) into the RAM image it initialises. Read-only.

The TI ARM runtime initialises RAM at reset from a table of (load address, run address) pairs; the first byte at each
load address picks a handler (copy, zero, RLE or LZSS). This decodes the LZSS form: a flag byte, eight items per flag
byte, bit = 1 a literal byte, bit = 0 a back-reference of two bytes (12-bit offset, 4-bit length + 3; length 18 takes
one or two extension bytes; offset 0xFFF ends the record). The format was transcribed from the runtime's own LZSS
handler in a CC26xx image, so it is the compiler's, not any one product's.

usage:
  py -3.13 -I tools/firmware/ti_cinit.py <image.bin> <load_offset_hex> <run_address_hex> [address_hex ...]

Prints the record's size and, for each address given, four little-endian words of the decompressed RAM there.
Use it to read values a firmware fills in at start-up (driver configuration tables in RAM, for example).
"""
import struct
import sys


def lzss(b: bytes, ip: int) -> tuple[bytes, int]:
    out = bytearray()
    while True:
        flags = b[ip]
        ip += 1
        for _ in range(8):
            if flags & 1:
                out.append(b[ip])
                ip += 1
            else:
                b0, b1 = b[ip], b[ip + 1]
                ip += 2
                length = (b1 & 0xF) + 3
                off = (b1 >> 4) | (b0 << 4)
                if length == 18:
                    ext = b[ip]
                    ip += 1
                    if ext & 0x80:
                        ext = (ext & 0x7F) | (b[ip] << 7)
                        ip += 1
                    length += ext
                if off == 0xFFF:
                    return bytes(out), ip
                src = len(out) - off - 1
                for k in range(length):
                    out.append(out[src + k])
            flags >>= 1


def main() -> None:
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    b = open(sys.argv[1], "rb").read()
    load, run = int(sys.argv[2], 16), int(sys.argv[3], 16)
    print(f"handler index at {load:#x}: {b[load]} (the table's LZSS handler is the one this decodes)")
    ram, end = lzss(b, load + 1)
    print(f"{end - load} bytes in -> {len(ram)} bytes at {run:#x}..{run + len(ram):#x}")
    for a in sys.argv[4:]:
        a = int(a, 16)
        words = struct.unpack_from("<4I", ram, a - run)
        print(f"{a:#x}: " + " ".join(f"{w:08x}" for w in words))


if __name__ == "__main__":
    main()
