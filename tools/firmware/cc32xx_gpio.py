"""Decode a CC32xx application's GPIO driver table (SimpleLink SDK 2.x `GPIOCC32XX_config`) from a raw image. Read-only.

A TI-RTOS application for the CC3220 keeps `GPIOCC32XX_config` (pinConfigs, callbacks, counts, priority) as constant
data in the image, but `gpioPinConfigs[]` itself is writable: the TI ARM compiler places it in `.data`, which the C
start-up code fills at reset from a compressed record. So the pin list is not in the image in clear. This script:

1. finds the C start-up record table (`__TI_CINIT_Base`: (load address, run address) pairs, the last thing the TI
   linker puts in the image) and the handler table just before it;
2. decompresses every record whose handler is the runtime's LZSS routine (recognised by its `movw rN, #0xfff`
   end-marker constant; the format is in `ti_cinit.py`);
3. looks for the constant `GPIOCC32XX_config` struct whose pinConfigs pointer lands in a decompressed range;
4. decodes each `GPIO_PinConfig` with SDK 2.40.02.00's `GPIO.h` / `GPIOCC32XX.h` bit layout and maps the GPIO number to
   the VQFN-64 package pin with the SDK's own `pinTable` (`GPIOCC32XX.c`).

The table this prints is the state at `GPIO_init`. `GPIO_write` and `GPIO_toggle` update bit 19 (GPIO_CFG_OUT_HIGH) of
the RAM copy, so a table read from a running device's RAM shows the last level written, not the start-up one.

usage:
  py -3.13 -I tools/firmware/cc32xx_gpio.py <mcuimg.bin> [--base 0x20004000] [--cinit <file_offset_hex>]

`--base` is the address the image runs at (a CC3220S application is loaded to SRAM at 0x20004000). `--cinit` gives the
pair table's file offset when the automatic search (walk back from the end of the image) does not find it.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script's folder; this is tools/firmware
from ti_cinit import lzss  # noqa: E402

# GPIOCC32XX.c (SDK 2.40.02.00) pinTable[]: GPIO number -> package pin, 0 = no pin (PIN_XX).
PIN_TABLE = [50, 55, 57, 58, 59, 60, 61, 62,
             63, 64, 1, 2, 3, 4, 5, 6,
             7, 8, 0, 0, 0, 0, 15, 16,
             17, 21, 29, 30, 18, 20, 53, 45,
             52]

OUT_TYPE = {0: "push-pull", 1: "open drain, no pull", 2: "open drain, pull-up", 3: "open drain, pull-down"}
IN_TYPE = {0: "no pull", 1: "pull-up", 2: "pull-down", 3: "?"}
STRENGTH = {0: "low", 1: "medium", 2: "high"}
INT = {0: "none", 1: "falling", 2: "rising", 3: "both edges", 4: "low level", 5: "high level"}


def u32(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]


def find_cinit(b: bytes, base: int) -> int:
    """File offset of the (load, run) pair table that ends the image."""
    n = len(b)
    ok = lambda off: base <= u32(b, off) < base + n and 0x20000000 <= u32(b, off + 4) < 0x20040000
    off = n - 8
    while off >= 0 and ok(off):
        off -= 8
    if off == n - 8:
        raise SystemExit("no start-up pair table at the end of the image; give --cinit")
    return off + 8


def is_lzss_handler(b: bytes, base: int, fn: int) -> bool:
    """The LZSS routine loads its 0xFFF end marker with a movw early on (T3 encoding)."""
    off = (fn & ~1) - base
    for k in range(off, min(off + 24, len(b) - 4), 2):
        hw1, hw2 = struct.unpack_from("<2H", b, k)
        if hw1 == 0xF640 and (hw2 & 0x70FF) == 0x70FF:
            return True
    return False


def handler_table(b: bytes, base: int, table: int) -> tuple[int, list[int]]:
    """The handlers: a run of odd (Thumb) pointers into the image, within 64 bytes before the pair table (small
    records such as a zero-fill may sit between them)."""
    for off in range(table - 4, max(table - 64, 0), -4):
        w = u32(b, off)
        if w & 1 and base <= w < base + len(b):
            end = off
            while off - 4 >= 0 and u32(b, off - 4) & 1 and base <= u32(b, off - 4) < base + len(b):
                off -= 4
            return off, [u32(b, k) for k in range(off, end + 4, 4)]
    return -1, []


def decode_pin(cfg: int) -> dict:
    pin = cfg & 0xFFFF
    port, mask = pin >> 8, pin & 0xFF
    d = {"raw": cfg}
    if pin == 0 or mask & (mask - 1):
        d["gpio"] = None
        d["what"] = "empty pin" if pin == 0 else f"not one pin ({pin:#06x})"
        return d
    gpio = port * 8 + mask.bit_length() - 1
    d["gpio"] = gpio
    d["port"] = f"A{port} bit {mask.bit_length() - 1}"
    d["package_pin"] = PIN_TABLE[gpio] if gpio < len(PIN_TABLE) else 0
    if cfg & 0x40000000:
        d["what"] = "GPIO_DO_NOT_CONFIG (left alone by GPIO_init)"
        return d
    if cfg & (1 << 16):
        d["what"] = f"input, {IN_TYPE[(cfg >> 17) & 3]}, interrupt {INT.get((cfg >> 24) & 7, '?')}"
        if cfg & (1 << 27):
            d["what"] += " (interrupt only)"
    else:
        level = "high" if cfg & (1 << 19) else "low"
        d["what"] = (f"output, {OUT_TYPE[(cfg >> 17) & 3]}, strength {STRENGTH.get((cfg >> 20) & 0xF, '?')}, "
                     f"starts {level}")
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image")
    ap.add_argument("--base", default="0x20004000")
    ap.add_argument("--cinit")
    a = ap.parse_args()
    b = open(a.image, "rb").read()
    base = int(a.base, 16)

    table = int(a.cinit, 16) if a.cinit else find_cinit(b, base)
    pairs = [(u32(b, o), u32(b, o + 4)) for o in range(table, len(b) - 7, 8)]
    hoff, handlers = handler_table(b, base, table)
    print(f"start-up pair table at file {table:#x}: {len(pairs)} record(s); "
          f"handler table at file {hoff:#x}: " + ", ".join(f"{h:#x}" for h in handlers))

    ram: list[tuple[int, bytes]] = []
    for ld, run in pairs:
        idx = b[ld - base]
        fn = handlers[idx] if idx < len(handlers) else None
        kind = "LZSS" if fn and is_lzss_handler(b, base, fn) else "other (not decoded)"
        line = f"  record at file {ld - base:#x} -> RAM {run:#x}, handler {idx} ({kind})"
        if kind == "LZSS":
            data, end = lzss(b, ld - base + 1)
            ram.append((run, data))
            line += f": {end - (ld - base)} bytes in, {len(data)} bytes out, RAM {run:#x}..{run + len(data):#x}"
        print(line)

    def ram_word(addr: int):
        for run, data in ram:
            if run <= addr and addr + 4 <= run + len(data):
                return u32(data, addr - run)
        return None

    found = 0
    for off in range(0, len(b) - 20, 4):
        p, cb, n, m, prio = struct.unpack_from("<5I", b, off)
        if not (1 <= n <= 64 and m <= 64 and 0x20000000 <= cb < 0x20040000 and (prio == 0xFFFFFFFF or prio < 0x100)):
            continue
        if p & 3 or ram_word(p) is None or ram_word(p + 4 * (n - 1)) is None:
            continue
        entries = [decode_pin(ram_word(p + 4 * i)) for i in range(n)]
        if any(e["gpio"] is None and e["raw"] & 0xFFFF for e in entries):
            continue
        found += 1
        print(f"\nGPIOCC32XX_config candidate at file {off:#x} (address {base + off:#x}): pinConfigs {p:#x}, "
              f"callbacks {cb:#x}, {n} pin config(s), {m} callback(s), intPriority {prio:#x}")
        for i, e in enumerate(entries):
            if e["gpio"] is None:
                print(f"  [{i}] {e['raw']:08x}  {e['what']}")
            else:
                pkg = f"pin {e['package_pin']}" if e["package_pin"] else "no package pin"
                print(f"  [{i}] {e['raw']:08x}  GPIO_{e['gpio']:02d} ({e['port']}, {pkg}): {e['what']}")
    if not found:
        print("\nno GPIOCC32XX_config found whose pin list lies in a decompressed record")


if __name__ == "__main__":
    main()
