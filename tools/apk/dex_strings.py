"""Dump the string pool of one or more DEX files, one string per line: file<TAB>index<TAB>repr.
Read-only. Usage: py -3.13 -I dex_strings.py <out.tsv> <classes.dex> [...]"""
import struct
import sys


def uleb128(buf, pos):
    result = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if b < 0x80:
            return result, pos
        shift += 7


with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as out:
    for path in sys.argv[2:]:
        data = open(path, "rb").read()
        assert data[:4] == b"dex\n", path
        count, ids_off = struct.unpack_from("<II", data, 0x38)
        name = path.replace("\\", "/").rsplit("/", 1)[-1]
        for i in range(count):
            (s_off,) = struct.unpack_from("<I", data, ids_off + 4 * i)
            _, pos = uleb128(data, s_off)
            end = data.index(b"\0", pos)
            s = data[pos:end].decode("utf-8", "replace")
            out.write(f"{name}\t{i}\t{s!r}\n")
