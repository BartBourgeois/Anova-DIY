"""Draw the flash-backup wiring: the SOIC-8 clip to each reader (Raspberry Pi, Pico, FT232H), and the power sequence.

Drawings, not photos: the point is which clip lead goes to which reader pin, and in what order things are switched on
and off, which no photo shows. The SPI NOR pinout is the JEDEC one that the cooker's XM25QH64A (U15), the LaunchPad's
MX25R3235F (U8) and the spare W25Q64JV all share (1 CS#, 2 DO, 3 WP#, 4 GND, 5 DI, 6 CLK, 7 HOLD#, 8 VCC).
The reader pins are the readers' documented ones: the Raspberry Pi's SPI0 on the 40-pin header, pico-serprog's
GP2-GP5 (check against the README of the firmware actually flashed), flashrom's ft2232_spi on ADBUS0-3.

Outputs (generated, never edit by hand): images/diagrams/fb-reader-pi.png, fb-reader-pico.png, fb-reader-esp32.png,
fb-reader-ft232h.png,
fb-power-sequence.png

Usage:  py -3.13 tools/diagrams/clip_wiring.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "images" / "diagrams"
FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"), Path("/Library/Fonts")]

BG, PANEL, BODY, PIN, TEXT, DIM, NO = "#1e1e1e", "#2a2a2a", "#141414", "#d8b45a", "#ffffff", "#c8c8c8", "#ff4040"
# one colour per signal, the same in every drawing and in the annotated photos' reader terminals
SIG = {"CS": "#ff8c00", "CLK": "#ffe600", "MOSI": "#2f9bff", "MISO": "#3ddc5a", "GND": "#b0b0b0", "VCC": NO}

# SOIC-8 pin: (number, name, signal or None)
CHIP = [(1, "CS#", "CS"), (2, "DO", "MISO"), (3, "WP#", None), (4, "GND", "GND"),
        (5, "DI", "MOSI"), (6, "CLK", "CLK"), (7, "HOLD#", None), (8, "VCC", "VCC")]

READERS = {
    "pi": {
        "title": "Raspberry Pi: flashrom linux_spi on the Pi itself",
        "box": "Raspberry Pi 40-pin header",
        "pins": {"CS": "pin 24  GPIO8 (SPI0 CE0)", "CLK": "pin 23  GPIO11 (SCLK)", "MOSI": "pin 19  GPIO10 (MOSI)",
                 "MISO": "pin 21  GPIO9 (MISO)", "GND": "pin 25  GND (or 6, 9, 14, 20)", "VCC": "pin 17  3V3"},
        "cmd": "flashrom -p linux_spi:dev=/dev/spidev0.0,spispeed=2000   (SPI enabled once: raspi-config, Interfaces)",
        "src": "Pin numbers: the Raspberry Pi's documented 40-pin header (physical pin numbers, pin 1 by the board corner).",
    },
    "pico": {
        "title": "Raspberry Pi Pico: pico-serprog firmware, flashrom serprog on the PC",
        "box": "Pico (RP2040), pins counted from the USB end",
        "pins": {"CS": "pin 7  GP5", "CLK": "pin 4  GP2", "MOSI": "pin 5  GP3",
                 "MISO": "pin 6  GP4", "GND": "pin 3  GND (or 8)", "VCC": "pin 36  3V3(OUT)"},
        "cmd": "flashrom -p serprog:dev=COM<n>:115200,spispeed=2M   (the Pico's COM port; the baud is ignored on USB)",
        "src": "Pins: pico-serprog's README (likely: check it against the README of the .uf2 actually flashed).",
    },
    "esp32": {
        "title": "ESP32 dev board: espserprog, flashrom serprog on the PC",
        "box": "ESP32 dev board, pins as printed (GPIO numbers)",
        "pins": {"CS": "GPIO5  (VSPI CS)", "CLK": "GPIO18  (VSPI SCK)", "MOSI": "GPIO23  (VSPI MOSI)",
                 "MISO": "GPIO19  (VSPI MISO)", "GND": "GND", "VCC": "3V3"},
        "cmd": "flashrom -p serprog:dev=COM<n>:921600,spispeed=2M   (tools/espserprog: read-only, pins hi-Z when idle)",
        "src": "Pins: tools/espserprog/src/main.cpp (the ESP32's VSPI). Its firmware refuses write enable, program and erase.",
    },
    "ft232h": {
        "title": "FT232H (Adafruit 2264): flashrom ft2232_spi on the PC",
        "box": "Adafruit FT232H breakout",
        "pins": {"CS": "D3  (ADBUS3)", "CLK": "D0  (ADBUS0)", "MOSI": "D1  (ADBUS1)",
                 "MISO": "D2  (ADBUS2)", "GND": "GND", "VCC": "3V"},
        "cmd": "flashrom -p ft2232_spi:type=232H,divisor=30   (60 MHz / 30 = 2 MHz; WinUSB driver via Zadig once)",
        "src": "Pins: flashrom's ft2232_spi mapping (ADBUS0 SCK, 1 MOSI, 2 MISO, 3 CS); likely until the first probe.",
    },
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]
    for d in FONT_DIRS:
        for n in names:
            if (d / n).exists():
                return ImageFont.truetype(str(d / n), size)
    return ImageFont.load_default(size=size)


def dashed(d, a, b, fill, width, on=14, off=9):
    (x0, y0), (x1, y1) = a, b
    length = max(abs(x1 - x0), abs(y1 - y0))
    n, t = max(1, int(length)), 0.0
    while t < n:
        t1 = min(t + on, n)
        d.line((x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n, x0 + (x1 - x0) * t1 / n, y0 + (y1 - y0) * t1 / n),
               fill=fill, width=width)
        t += on + off


def reader(key: str) -> None:
    r = READERS[key]
    W, H = 1800, 1070
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_t, f_s, f_pin, f_lab, f_note = font(34, True), font(20), font(24, True), font(22), font(21)
    d.text((40, 24), f"Flash backup - the SOIC-8 clip to the {r['title']}", font=f_t, fill=TEXT)
    d.text((40, 72), "The chip seen from above, as the clip sits on it: pin 1 at the dot. "
           "Same pinout on the cooker's U15, the LaunchPad's U8 and the spare W25Q64JV.", font=f_s, fill=DIM)

    # the chip: pins 1-4 down the left side, 8-5 down the right side; labels inside the body, clear of the wires
    cx0, cy0, cx1, cy1 = 260, 190, 580, 690
    d.rounded_rectangle((cx0, cy0, cx1, cy1), 14, fill=BODY, outline="#555555", width=2)
    d.ellipse((cx0 + 16, cy0 + 14, cx0 + 40, cy0 + 38), fill="#8a8a8a")
    d.text((cx0 + 108, cy0 + 220), "SPI NOR", font=f_lab, fill=DIM)
    d.text((cx0 + 112, cy0 + 252), "top view", font=f_s, fill=DIM)
    ys = [cy0 + 80 + i * 120 for i in range(4)]
    ends = {}
    for num, name, sig in CHIP:
        left = num <= 4
        y = ys[num - 1] if left else ys[8 - num]
        label = f"{num} {name}"
        if left:
            d.rectangle((cx0 - 46, y - 16, cx0, y + 16), fill=PIN)
            d.text((cx0 + 14, y - 14), label, font=f_pin, fill=TEXT)
            ends[num] = (cx0 - 46, y)
        else:
            d.rectangle((cx1, y - 16, cx1 + 46, y + 16), fill=PIN)
            l, t, r_, b = d.textbbox((0, 0), label, font=f_pin)
            d.text((cx1 - 14 - (r_ - l), y - 14), label, font=f_pin, fill=TEXT)
            ends[num] = (cx1 + 46, y)

    # the reader's pins
    order = ["CS", "CLK", "MOSI", "MISO", "GND", "VCC"]
    rx0, ry0 = 1080, 170
    d.rounded_rectangle((rx0, ry0, rx0 + 640, ry0 + 90 + len(order) * 96), 18, fill=PANEL)
    d.text((rx0 + 24, ry0 + 18), r["box"], font=f_lab, fill=TEXT)
    rp = {}
    for i, sig in enumerate(order):
        y = ry0 + 100 + i * 96
        d.rectangle((rx0 + 24, y - 18, rx0 + 60, y + 18), fill=SIG[sig])
        d.text((rx0 + 76, y - 26), sig if sig != "VCC" else "3.3 V", font=f_pin, fill=SIG[sig])
        d.text((rx0 + 76, y + 4), r["pins"][sig], font=f_lab, fill=TEXT)
        rp[sig] = (rx0 + 24, y)

    # wires: each chip pin to its reader pin, each in its own vertical lane; the left-side pins run under the chip
    lanes = {"CS": 780, "MISO": 830, "GND": 880, "MOSI": 930, "CLK": 980}
    under = {"CS": 720, "MISO": 745, "GND": 770}  # the horizontal run under the chip, per left-side signal
    side = {"CS": 196, "MISO": 180, "GND": 164}  # the vertical run left of the chip
    for num, name, sig in CHIP:
        if sig is None or sig == "VCC":
            continue
        (x0, y0), (x1, y1) = ends[num], rp[sig]
        lane = lanes[sig]
        if num <= 4:
            pts = [(x0, y0), (side[sig], y0), (side[sig], under[sig]), (lane, under[sig]), (lane, y1), (x1, y1)]
        else:
            pts = [(x0, y0), (lane, y0), (lane, y1), (x1, y1)]
        for a, b in zip(pts, pts[1:]):
            d.line((*a, *b), fill=SIG[sig], width=6)
    # VCC: a short dead-end stub, crossed out; the reader's 3.3 V pin stays free on a board
    vx, vy = ends[8]
    dashed(d, (vx, vy), (vx + 80, vy), NO, 5)
    d.line((vx + 82, vy - 20, vx + 118, vy + 16), fill=NO, width=7)
    d.line((vx + 82, vy + 16, vx + 118, vy - 20), fill=NO, width=7)
    d.text((vx + 4, vy - 52), "no lead", font=f_s, fill=NO)
    ry = rp["VCC"][1]
    d.text((rx0 + 76, ry + 34), "free on a board; the loose practice chip only", font=f_s, fill=NO)

    notes = [
        ("VCC (pin 8): never from the reader on a board: the board feeds its own flash (on the cooker U17's 3.3 V,", TEXT),
        ("  which a reader would back-feed). Only the loose practice chip takes the reader's 3.3 V.", TEXT),
        ("WP# (3) and HOLD# (7): no lead on a board (its pull-ups hold them high). The loose practice chip: both to 3.3 V.", TEXT),
        (r["cmd"], DIM),
        (r["src"] + " Lead pin 1 of the clip: find it with the beeper (handbook page 02).", DIM),
    ]
    for i, (n, c) in enumerate(notes):
        d.text((40, 830 + i * 42), n, font=f_note, fill=c)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"fb-reader-{key}.png"
    im.save(out, optimize=True)
    print(f"  {out.relative_to(ROOT)}  {W}x{H}")


def sequence() -> None:
    W, H = 1800, 900
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_t, f_s, f_lab, f_step, f_note = font(34, True), font(20), font(23, True), font(20, True), font(21)
    d.text((40, 24), "Flash backup - the order: hold first, board before reader, reader off before board", font=f_t,
           fill=TEXT)
    d.text((40, 72), "Read left to right. Each bar is on where it is drawn. The same order on the LaunchPad "
           "(board power = its USB) and on the cooker (board power = 5 V through break-out A on J8).", font=f_s, fill=DIM)
    x0, x1 = 700, 1720
    steps = ["hold on", "board on", "check", "reader on", "read x2", "reader off", "board off", "hold off"]
    xs = [x0 + i * (x1 - x0) / (len(steps) - 1) for i in range(len(steps))]
    rows = [  # (title, second line, colour, from step, to step)
        ("Reset hold to GND", "TP33 (cooker), R321's chip-side pad (LaunchPad)", "#ff5cc8", 0, 7),
        ("Board power", "5 V on J8 (cooker), USB (LaunchPad); limit 100 mA", "#ff8c00", 1, 6),
        ("Checks", "3.3 V at pin 8, the current, HOLD# high", "#ffffff", 2, 3),
        ("Reader", "leads connected (Pi), plugged in (Pico, FT232H)", "#2f9bff", 3, 5),
        ("backup.py", "probe, two reads, the two hashes", "#3ddc5a", 4, 5),
    ]
    for i, (title, line2, col, a, b) in enumerate(rows):
        y = 200 + i * 105
        d.text((40, y - 4), title, font=f_lab, fill=TEXT)
        d.text((40, y + 26), line2, font=f_s, fill=DIM)
        d.rounded_rectangle((xs[a], y, xs[b], y + 44), 10, fill=col)
    for i, (x, text) in enumerate(zip(xs, steps)):
        d.line((x, 170, x, 720), fill="#555555", width=2)
        num = str(i + 1)
        d.ellipse((x - 20, 120, x + 20, 160), fill="#ffffff")
        l, t, r, b = d.textbbox((0, 0), num, font=f_step)
        d.text((x - (r - l) / 2, 140 - (b - t) / 2 - t), num, font=f_step, fill="#000000")
        l, t, r, b = d.textbbox((0, 0), text, font=f_s)
        d.text((x - (r - l) / 2, 735), text, font=f_s, fill=TEXT)
    notes = [
        "Why this order: a reader's CS line idles high. Into an unpowered board it would feed the 3.3 V rail through the",
        "flash's input diodes (on the cooker: U17's output with its input unpowered, J-076). The hold is on before power,",
        "so the CC3220 never starts: it can't touch the flash, and nothing on the board writes. Abort at any step: reader off, then board off.",
    ]
    for i, n in enumerate(notes):
        d.text((40, 790 + i * 34), n, font=f_note, fill=DIM if i else TEXT)
    out = OUT / "fb-power-sequence.png"
    im.save(out, optimize=True)
    print(f"  {out.relative_to(ROOT)}  {W}x{H}")


def main() -> None:
    for key in READERS:
        reader(key)
    sequence()


if __name__ == "__main__":
    main()
