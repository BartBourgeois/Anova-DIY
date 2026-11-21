"""List and extract the files of a CC3220S serial-flash dump (SimpleLink file system), offline and read-only.

The layout, as read from cc3200tool's CC32xx parser and checked against the LaunchPad's dumps (J-183, J-184):
- Blocks 0 and 1 hold two copies of the allocation table (FAT); the valid one with the higher revision is active.
  Header `<revision u16><signature u16>`: 0x634C on a CC3220S (the CC3200's is 0x534C, which is why cc3200tool calls
  a CC3220S table broken). Then 240 entries of 4 bytes (cc3200tool reads 128, the CC3200's count; the name table's
  offsets end at 0x3C0 = 240 x 4, and the cooker's table uses entries past 127, J-222): index, size in blocks, start
  block LSB, and a byte whose low nibble is the start block's MSB and whose high nibble holds flags; flag 0x4 clear
  means mirrored (fail-safe, two copies back to back).
- The name table sits in the block two after the active FAT (block 2 for FAT 0, block 3 for FAT 1): `<offset u16>
  <length u16>` per entry, the names from 0x3C0 in that block.
- Each copy of a file starts with `<length u32><sequence u16><0x634C>`, then the data. Of a mirrored pair, the copy
  with the valid header and the higher sequence is the active one.
Plain files lie in the flash as they are; secure files (the application image, the service pack, the catalogue)
are encrypted with the chip's own key and come out as ciphertext (J-182).

Usage:
  py -3.13 tools/sflash/sffs.py <dump.bin>                         # the file list
  py -3.13 tools/sflash/sffs.py <dump.bin> --manifest <ota.cmd>    # plus a SHA-256 check against an update package
  py -3.13 tools/sflash/sffs.py <dump.bin> --extract <dir>         # plus each active copy's data into <dir>
  py -3.13 tools/sflash/sffs.py <dump.bin> --all-copies <dir>      # every copy of every file, and the unowned blocks
--all-copies (J-218) writes `<name>.copy<k>-blk<block>-seq<seq>` for a copy with a valid header (its data), and
`<name>.copy<k>-blk<block>-raw` for one without (all its blocks as they lie: an erased or half-written copy). Blocks that
no file in the active table owns, and that aren't erased (all FF), go to `_unowned/blk<first>-<last>.bin`: the
leftovers of deleted or rolled-back files.
"""

import argparse
import hashlib
import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path

BLOCK = 4096
SIGNATURE = 0x634C
NAMES_AT = 0x3C0
MAX_FILES = NAMES_AT // 4  # 240


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in Counter(data).values())


def active_fat(dump: bytes):
    """(fat index, revision) of the valid table with the higher revision."""
    found = []
    for i in (0, 1):
        rev, sig = struct.unpack("<HH", dump[i * BLOCK:i * BLOCK + 4])
        if sig == SIGNATURE and rev != 0xFFFF:
            found.append((rev, i))
    if not found:
        raise SystemExit("no allocation table with signature 0x634C in blocks 0-1: not a CC3220S dump?")
    rev, i = max(found)
    return i, rev


def copy_header(dump: bytes, block: int):
    """(length, sequence, mark) of a copy, or None. The length field's top byte is a mark: 0x02 only on copies an
    update bundle wrote and closed but never committed (`likely`, SWRU455M 8.9; J-222)."""
    length, seq, magic = struct.unpack("<IHH", dump[block * BLOCK:block * BLOCK + 8])
    return (length & 0xFFFFFF, seq, length >> 24) if magic == SIGNATURE else None


def files(dump: bytes):
    fat_i, rev = active_fat(dump)
    fat = dump[fat_i * BLOCK:(fat_i + 1) * BLOCK]
    names = dump[(fat_i + 2) * BLOCK:(fat_i + 3) * BLOCK]
    out = []
    for i in range(MAX_FILES):
        meta = fat[(i + 1) * 4:(i + 2) * 4]
        if meta == b"\xff\xff\xff\xff" or meta == bytes([0xFF, i, 0xFF, 0x7F]):
            continue
        index, size_blocks, start_lsb, flags_msb = meta
        if index != i:
            continue  # not a file entry
        flags, start = flags_msb >> 4, ((flags_msb & 0xF) << 8) | start_lsb
        mirrored = not flags & 0x4
        off, ln = struct.unpack("<HH", names[i * 4:i * 4 + 4])
        name = names[NAMES_AT + off:NAMES_AT + off + ln].decode("ascii", "replace")
        copies = [start] + ([start + size_blocks] if mirrored else [])
        headers = [(b, copy_header(dump, b)) for b in copies]
        valid = [(h[1], b, h[0], h[2]) for b, h in headers if h and h[0] <= size_blocks * BLOCK - 8]
        committed = [v for v in valid if not v[3]]
        active = max(committed or valid)[:3] if valid else None  # (sequence, block, length); pending only if alone
        data = dump[active[1] * BLOCK + 8:active[1] * BLOCK + 8 + active[2]] if active else b""
        out.append({"index": i, "name": name, "start": start, "size_blocks": size_blocks, "mirrored": mirrored,
                    "flags": flags, "copies": [(b, h) for b, h in headers], "active": active, "data": data})
    return fat_i, rev, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dump", type=Path)
    ap.add_argument("--manifest", type=Path, help="a TI OTA manifest (ota.cmd): compare each listed file's SHA-256")
    ap.add_argument("--extract", type=Path, help="write each file's active copy into this directory")
    ap.add_argument("--all-copies", type=Path, help="write every copy of every file, and the unowned blocks, here")
    args = ap.parse_args()
    dump = args.dump.read_bytes()
    fat_i, rev, entries = files(dump)
    digests = {}
    if args.manifest:
        digests = {e["filename"]: str(e["digest"]).lower() for e in json.loads(args.manifest.read_text("utf-8"))}
    print(f"{args.dump.name}: {len(dump)} bytes, {len(dump) // BLOCK} blocks; FAT {fat_i} active, revision {rev}, "
          f"{len(entries)} files")
    print(f"{'#':>3} {'start':>5} {'blks':>4} {'mir':3} {'fl':>2} {'copies (block:seq)':22} {'length':>7} {'H':>4}  name / check")
    for e in entries:
        cps = " ".join(f"{b}:{h[1] if h else '-'}{'p' if h and h[2] else ''}" for b, h in e["copies"])
        a = e["active"]
        sha = hashlib.sha256(e["data"]).hexdigest() if a else ""
        check = ""
        if e["name"] in digests:
            check = "= package" if sha == digests[e["name"]] else "!= package (encrypted or different)"
        print(f"{e['index']:>3} {e['start']:>5} {e['size_blocks']:>4} {'yes' if e['mirrored'] else 'no':3} "
              f"{e['flags']:>2x} {cps:22} {a[2] if a else '-':>7} {entropy(e['data']):4.1f}  {e['name']}  {check}")
        if args.extract and a:
            target = args.extract / e["name"].lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(e["data"])
    if args.all_copies:
        write_all_copies(dump, fat_i, entries, args.all_copies)
    return 0


def write_all_copies(dump: bytes, fat_i: int, entries, out: Path) -> None:
    owned = {0, 1, 2, 3}  # the two tables and their name blocks
    for e in entries:
        for k, (b, h) in enumerate(e["copies"]):
            owned.update(range(b, b + e["size_blocks"]))
            base = out / e["name"].lstrip("/")
            base.parent.mkdir(parents=True, exist_ok=True)
            if h and h[0] <= e["size_blocks"] * BLOCK - 8:
                data = dump[b * BLOCK + 8:b * BLOCK + 8 + h[0]]
                mark = f"-mark{h[2]:02x}" if h[2] else ""
                (base.parent / f"{base.name}.copy{k}-blk{b}-seq{h[1]}{mark}").write_bytes(data)
            else:
                data = dump[b * BLOCK:(b + e["size_blocks"]) * BLOCK]
                (base.parent / f"{base.name}.copy{k}-blk{b}-raw").write_bytes(data)
    runs, first = [], None
    for blk in range(len(dump) // BLOCK + 1):
        used = blk < len(dump) // BLOCK and blk not in owned and dump[blk * BLOCK:(blk + 1) * BLOCK] != b"\xff" * BLOCK
        if used and first is None:
            first = blk
        elif not used and first is not None:
            runs.append((first, blk - 1))
            first = None
    (out / "_unowned").mkdir(parents=True, exist_ok=True)
    for a, z in runs:
        (out / "_unowned" / f"blk{a}-{z}.bin").write_bytes(dump[a * BLOCK:(z + 1) * BLOCK])
    print(f"all copies: {sum(len(e['copies']) for e in entries)} copies of {len(entries)} files; "
          f"{len(runs)} runs of unowned, non-erased blocks ({sum(z - a + 1 for a, z in runs)} blocks) -> {out}")


if __name__ == "__main__":
    sys.exit(main())
