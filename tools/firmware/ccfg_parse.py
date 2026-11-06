"""Decode the CC26x0R2 CCFG (last 88 bytes of the flash image). Read-only.
Offsets per TI hw_ccfg.h (CC26x0R2). Usage: py -3.13 -I ccfg_parse.py <cc2640.bin>"""
import sys

b = open(sys.argv[1], "rb").read()
base = len(b) - 0x58  # CCFG is the last 88 bytes


def u32(off):
    return int.from_bytes(b[base + off:base + off + 4], "little")


fields = {
    0x30: "BL_CONFIG", 0x34: "ERASE_CONF", 0x38: "TI_OPTIONS",
    0x3C: "TAP_DAP_0", 0x40: "TAP_DAP_1", 0x44: "IMAGE_VALID_CONF",
    0x48: "PROT_31_0", 0x4C: "PROT_63_32", 0x50: "PROT_95_64", 0x54: "PROT_127_96",
}
print(f"CCFG at image offset 0x{base:05x}")
for off, name in fields.items():
    print(f"  0x{off:02x} {name:16s} 0x{u32(off):08x}")

bl = u32(0x30)
tap0 = u32(0x3C)
tap1 = u32(0x40)
ti = u32(0x38)
erase = u32(0x34)
print("\ninterpretation (0xC5 = enabled/allowed, other = disabled/locked):")
print(f"  bootloader (BL_CONFIG BOOTLOADER_ENABLE, top byte) : 0x{(bl >> 24) & 0xff:02x}")
print(f"  BL_CONFIG BL_LEVEL/PIN low bytes                    : 0x{bl & 0xffffff:06x}")
print(f"  CPU DAP enable   (TAP_DAP_0 byte0)                  : 0x{tap0 & 0xff:02x}")
print(f"  PRCM TAP enable  (TAP_DAP_0 byte1)                  : 0x{(tap0 >> 8) & 0xff:02x}")
print(f"  TEST TAP enable  (TAP_DAP_0 byte2)                  : 0x{(tap0 >> 16) & 0xff:02x}")
print(f"  PBIST2/1, AON TAP(TAP_DAP_1)                        : 0x{tap1 & 0xffffff:06x}")
print(f"  TI_OPTIONS TI_FA_ENABLE (byte0)                     : 0x{ti & 0xff:02x}")
print(f"  IMAGE_VALID_CONF (0 = valid vector table at 0x0)    : 0x{u32(0x44):08x}")
print(f"  bank/chip erase (ERASE_CONF bit0/bit1)              : 0x{erase:08x}")
