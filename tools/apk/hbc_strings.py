"""Dump the string table of a Hermes bytecode file (v96 header layout), one string per line: index<TAB>repr.
Read-only. Usage: py -3.13 -I hbc_strings.py <bundle> <out.tsv>"""
import struct
import sys

MAGIC = 0x1F1903C103BC1FC6

data = open(sys.argv[1], "rb").read()
magic, version = struct.unpack_from("<QI", data, 0)
assert magic == MAGIC, hex(magic)
(file_len, global_code, func_count, kind_count, ident_count, str_count, overflow_count,
 storage_size) = struct.unpack_from("<8I", data, 0x20)
print(f"version {version}, file {file_len}, functions {func_count}, strings {str_count}, "
      f"overflow {overflow_count}, storage {storage_size}", file=sys.stderr)


def align(x):
    return (x + 3) & ~3


off = 128
off = align(off + func_count * 16)        # function headers
off = align(off + kind_count * 4)         # string kinds
off = align(off + ident_count * 4)        # identifier hashes
small = off
off = align(off + str_count * 4)
overflow = off
off = align(off + overflow_count * 8)
storage = off

with open(sys.argv[2], "w", encoding="utf-8", newline="\n") as out:
    for i in range(str_count):
        (word,) = struct.unpack_from("<I", data, small + 4 * i)
        utf16, s_off, s_len = word & 1, (word >> 1) & 0x7FFFFF, word >> 24
        if s_len == 0xFF:
            s_off, s_len = struct.unpack_from("<II", data, overflow + 8 * s_off)
        if utf16:
            raw = data[storage + s_off: storage + s_off + 2 * s_len]
            s = raw.decode("utf-16-le", "replace")
        else:
            raw = data[storage + s_off: storage + s_off + s_len]
            s = raw.decode("latin-1")
        out.write(f"{i}\t{s!r}\n")
