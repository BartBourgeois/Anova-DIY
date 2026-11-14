"""Disassemble a window of a Thumb image. Read-only; prints only. Does not run the code.
Usage: py -3.13 -I disarm.py <file> <load_addr_hex> <start_addr_hex> [count]"""
import sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN

path = sys.argv[1]
load = int(sys.argv[2], 16)
start = int(sys.argv[3], 16) & ~1          # clear Thumb bit
count = int(sys.argv[4]) if len(sys.argv) > 4 else 24

b = open(path, "rb").read()
off = start - load
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
md.detail = False
print(f"{path}: load=0x{load:08x} start=0x{start:08x} fileoff=0x{off:x}")
for i, ins in enumerate(md.disasm(b[off:off + count * 4], start)):
    print(f"  0x{ins.address:08x}  {ins.bytes.hex():<12} {ins.mnemonic:<7} {ins.op_str}")
    if i + 1 >= count:
        break
