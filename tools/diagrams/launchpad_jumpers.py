"""Draw the CC3220S LaunchPad's jumper column for handbook step 2.10 (J-190): which caps stay, which come off, the
one placed across VBAT/BRD, and the USB-serial adapter's two wires on the CC3220's own RX/TX pins.

A drawing rather than callouts on a photo: the photos of the column are too soft to mark single pins. It is drawn as
the silkscreen reads (TI SWRU463C figures 13/14: the board's USB connector top-left, the labels under the column).
The pin roles of the three-pin RX/TX positions are `likely` (TI 2.5.7: an external UART uses "the second pin on the
J6 column"; the caps sit on the J6 and middle pins as shipped).

Output (generated, never edit by hand): images/diagrams/rec2-10_launchpad-jumper-column.png

Usage:  py -3.13 tools/diagrams/launchpad_jumpers.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "images" / "diagrams" / "rec2-10_launchpad-jumper-column.png"
FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"), Path("/Library/Fonts")]

BG, BOARD, BODY, PIN, CAP = "#1e1e1e", "#9c1c1c", "#141414", "#d8b45a", "#3a3a3a"
STAY, OFF, ACROSS, WIRE, TEXT, DIM = "#3ddc5a", "#ff4040", "#ff8c00", "#00e5ff", "#ffffff", "#c8c8c8"

# column label, silkscreen designator above it, state: stay | off | across | wire
COLUMNS = [("GND", "J21", "stay"), ("5V", "J20", "stay"), ("VBAT", "J19", "across"), ("BRD", "J17", "across"),
           ("RX", "", "wire"), ("TX", "", "wire"), ("RST", "", "off"), ("TMS", "", "off"), ("TCK", "", "off"),
           ("TDI", "", "off"), ("TDO", "", "off"), ("BRD", "J18", "stay")]
STATUS = {"stay": ("stays", STAY), "off": ("OFF", OFF), "across": ("cap across", ACROSS), "wire": ("OFF + wire", OFF)}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]
    for d in FONT_DIRS:
        for n in names:
            if (d / n).exists():
                return ImageFont.truetype(str(d / n), size)
    return ImageFont.load_default(size=size)


def centred(draw, xy, text, fnt, fill):
    l, t, r, b = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - (r - l) / 2, xy[1] - (b - t) / 2 - t), text, font=fnt, fill=fill)


def main() -> None:
    W, H = 1700, 1100
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_title, f_sub, f_lab, f_small, f_note = font(34, True), font(21), font(26, True), font(19), font(21)

    d.text((40, 24), "Recovery 2.10 - the LaunchPad's jumper column, wired like the cooker", font=f_title, fill=TEXT)
    d.text((40, 72), "Drawn as the silkscreen reads: the board's USB connector top-left, the labels under the column "
           "(TI SWRU463C fig. 13). Pin roles in RX/TX: likely (TI 2.5.7).", font=f_sub, fill=DIM)

    pitch, x0 = 110, 260
    xs = [x0 + i * pitch for i in range(len(COLUMNS))]
    y6, yt, yb = 430, 540, 650                       # J6/J5 row, upper row, label-side row
    d.rounded_rectangle((120, 330, W - 120, 830), 24, fill=BOARD)
    d.rectangle((xs[0] - 48, yt - 48, xs[-1] + 48, yb + 48), fill=BODY)
    rx, tx = xs[4], xs[5]
    d.rectangle((rx - 36, y6 - 48, tx + 36, y6 + 48), fill=BODY)

    def pin(x, y):
        d.rectangle((x - 13, y - 13, x + 13, y + 13), fill=PIN)

    def cap(x0_, y0_, x1_, y1_, colour):
        d.rounded_rectangle((x0_ - 34, y0_ - 34, x1_ + 34, y1_ + 34), 10, fill=CAP, outline=colour, width=6)

    for x, (_, _, state) in zip(xs, COLUMNS):
        if state == "stay":
            cap(x, yt, x, yb, STAY)
    cap(xs[2], yb, xs[3], yb, ACROSS)                # one cap across the label-side pins of VBAT and BRD
    for x in xs:
        pin(x, yt)
        pin(x, yb)
    pin(rx, y6)
    pin(tx, y6)

    for x, (label, ref, state) in zip(xs, COLUMNS):
        centred(d, (x, yb + 80), label, f_lab, TEXT)
        text, colour = STATUS[state]
        centred(d, (x, yb + 118), text, f_small, colour)
        if ref:
            centred(d, (x, yt - 72 if x not in (rx, tx) else y6 - 72), ref, f_small, DIM)
    centred(d, (rx, y6 - 72), "J6", f_small, DIM)
    centred(d, (tx, y6 - 72), "J5", f_small, DIM)

    # the adapter's wires: from the middle pins, out between the columns, up to the adapter
    for x, side, label in ((rx, -1, "CH340 TXD"), (tx, 1, "CH340 RXD")):
        d.ellipse((x - 24, yt - 24, x + 24, yt + 24), outline=WIRE, width=5)
        xw = x + side * 55
        d.line((x + side * 20, yt - 14, xw, yt - 55, xw, 220), fill=WIRE, width=6)
        bx = (xw - 250, 170, xw - 10, 215) if side < 0 else (xw + 10, 170, xw + 250, 215)
        d.rectangle(bx, outline=WIRE, width=3, fill=BG)
        centred(d, ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2), label, f_lab, WIRE)
        d.line((xw, 192, bx[2] if side < 0 else bx[0], 192), fill=WIRE, width=6)
    d.rectangle((rx - 55 - 16, 262, rx - 55 + 16, 318), fill=BG, outline=WIRE, width=4)      # the 1 kOhm
    d.text((rx - 55 - 112, 274), "1 kΩ", font=f_lab, fill=WIRE)

    # pin roles of RX/TX, in the free space right of J6/J5 (the circled middle pins are explained in the notes)
    d.line((tx + 40, y6, tx + 90, y6), fill=DIM, width=2)
    d.text((tx + 100, y6 - 13), "top pins (J6, J5): the XDS110's side, stay free", font=f_small, fill=DIM)

    notes = [
        "RX and TX have three pins. The circled middle pin is the CC3220's own (RX = pin 57, TX = pin 55): the wire goes "
        "there. The pin by the label (header / op-amp) stays free.",
        "Caps: GND, 5V and BRD-SENSE stay. RX, TX, RST, TMS, TCK, TDI, TDO off (keep them: park each on one pin).",
        "VBAT and BRD: both caps off, then one cap across their two label-side pins (TI 2.6.2 step 4: the board runs from J22).",
        "Elsewhere: USB unplugged · J22: 3V3 = bench supply + (3.30 V, limit 100 mA, never 5 V), GND = supply −, "
        "GND = CH340 GND",
        "· J9 (RST PU) jumper on · J13: SOP2 only · CH340 I/O on 3.3 V, its VCC, DTR and RTS unconnected. "
        "Picture of the board: rec2-10_launchpad-bench-wiring.",
    ]
    for i, n in enumerate(notes):
        d.text((40, 860 + i * 42), n, font=f_note, fill=TEXT if i < 3 else DIM)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, optimize=True)
    print(f"  {OUT.relative_to(ROOT)}  {W}x{H}")


if __name__ == "__main__":
    main()
