"""Compare CC3220S flash dumps: which blocks differ and which file owns them, and which allocation-table bytes tell
two groups of dumps apart. Offline and read-only, like sffs.py, whose parser it uses.

  blockdiff.py blocks A.bin B.bin
      every run of differing 4 KiB blocks, with the bytes that differ and the file (from B's allocation table) that
      the blocks belong to, or "(no file)" for free or reserved blocks. For: clip read against boot-loader read (they
      must be equal), before against after a write, one programming against another.
  blockdiff.py fat --a A1.bin [A2.bin ...] --b B1.bin [B2.bin ...]
      the active allocation table's bytes (block 0 or 1) at which every dump of group A agrees, every dump of group B
      agrees, and the two groups differ. For: where the file system keeps a property one group has and the other
      hasn't (development against production: the mode that Image Creator reads with GET_FS_USAGE, J-194, J-202).
      Offsets 0-3 are the revision and the signature; entries start at 4, four bytes per file.

Usage:  py -3.13 -I tools/sflash/blockdiff.py blocks <a.bin> <b.bin>
        py -3.13 -I tools/sflash/blockdiff.py fat --a <dev1.bin> <dev2.bin> --b <prod1.bin>
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sffs  # noqa: E402

BLOCK = sffs.BLOCK


def owners(dump: bytes) -> dict:
    """block number -> file name, from the dump's active allocation table (both copies of a mirrored file)."""
    fat_i, _, entries = sffs.files(dump)
    own = {fat_i: "(allocation table, active)", 1 - fat_i: "(allocation table, other)",
           fat_i + 2: "(name table)", 3 - fat_i: "(name table, other)"}
    for e in entries:
        span = e["size_blocks"] * (2 if e["mirrored"] else 1)
        for b in range(e["start"], e["start"] + span):
            own[b] = e["name"]
    return own


def cmd_blocks(args) -> int:
    a, b = args.a.read_bytes(), args.b.read_bytes()
    if len(a) != len(b):
        print(f"sizes differ: {len(a)} and {len(b)} bytes")
        return 2
    diff = [i for i in range(len(a) // BLOCK) if a[i * BLOCK:(i + 1) * BLOCK] != b[i * BLOCK:(i + 1) * BLOCK]]
    print(f"{args.a.name} against {args.b.name}: {len(diff)} of {len(a) // BLOCK} blocks differ")
    if not diff:
        return 0
    own = owners(b)
    runs, start = [], diff[0]
    for prev, cur in zip(diff, diff[1:] + [None]):
        if cur is None or cur != prev + 1 or own.get(cur) != own.get(prev):
            runs.append((start, prev))
            start = cur
    for s, e in runs:
        nbytes = sum(x != y for x, y in zip(a[s * BLOCK:(e + 1) * BLOCK], b[s * BLOCK:(e + 1) * BLOCK]))
        print(f"  blocks {s:4d}-{e:4d}  0x{s * BLOCK:06x}-0x{(e + 1) * BLOCK - 1:06x}  {nbytes:7d} bytes  "
              f"{own.get(s, '(no file)')}")
    return 1


def active_table(path: Path) -> bytes:
    dump = path.read_bytes()
    fat_i, _ = sffs.active_fat(dump)
    return dump[fat_i * BLOCK:(fat_i + 1) * BLOCK]


def cmd_fat(args) -> int:
    ga, gb = [active_table(p) for p in args.a], [active_table(p) for p in args.b]
    found = []
    for off in range(BLOCK):
        va, vb = {t[off] for t in ga}, {t[off] for t in gb}
        if len(va) == 1 and len(vb) == 1 and va != vb:
            found.append((off, va.pop(), vb.pop()))
    print(f"group A: {len(ga)} dumps, group B: {len(gb)} dumps; {len(found)} table bytes constant in each group and "
          f"different between them")
    for off, x, y in found:
        where = "header" if off < 4 else f"entry {(off - 4) // 4}, byte {(off - 4) % 4}"
        print(f"  offset 0x{off:03x} ({where}): A {x:#04x}, B {y:#04x}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True
    b = sub.add_parser("blocks", help="differing blocks and the files they belong to")
    b.add_argument("a", type=Path)
    b.add_argument("b", type=Path)
    f = sub.add_parser("fat", help="allocation-table bytes that tell two groups of dumps apart")
    f.add_argument("--a", type=Path, nargs="+", required=True)
    f.add_argument("--b", type=Path, nargs="+", required=True)
    args = ap.parse_args()
    return cmd_blocks(args) if args.cmd == "blocks" else cmd_fat(args)


if __name__ == "__main__":
    sys.exit(main())
