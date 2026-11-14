"""Builds the JLCPCB order files for ffc30-tap.kicad_pcb with kicad-cli (KiCad 10).

Run with KiCad's own Python, after generate_board.py:
    "<KiCad>/bin/python.exe" -I build_fab.py
Writes into fab/: drc.txt, gerbers/ + ffc30-tap_gerbers_JLC.zip, jlc_bom.csv, jlc_cpl.csv; and the two renders
render_top.png / render_bottom.png next to the board. Stops if DRC finds anything but the expected warnings.
"""
import csv
import math
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "ffc30-tap.kicad_pcb")
FAB = os.path.join(HERE, "fab")
GERB = os.path.join(FAB, "gerbers")

exe = "kicad-cli.exe" if os.name == "nt" else "kicad-cli"
CLI = os.path.join(os.path.dirname(sys.executable), exe)
if not os.path.isfile(CLI):
    CLI = shutil.which("kicad-cli") or sys.exit("kicad-cli not found: run this with KiCad's Python")

PARTS = {   # designator prefix of the board's footprints -> JLCPCB BOM row
    "socket": ("HanElectricity 05A20L30P FPC 30P 0.5mm bottom contact flip", "FPC-30P-0.5mm", "C5362159", ["J1", "J2"]),
    "header": ("2x15 pin header 2.54mm straight male (6 mm pins)", "PinHeader_2x15_P2.54mm", "C56496", ["J3", "J4"]),
}

# JLCPCB's own part models don't share our footprints' origin or orientation. Measured in their placement viewer
# (2026-11-12) and corrected here, in the CPL only; the copper follows the makers' drawings:
#   C5362159 (socket): their model sits 2.0 mm toward the cable entry from our pads -> move it 2.0 mm toward the
#                      pads (the footprint's -y, rotated with the part)
#   C56496 (header):   their model lies across (15 pins along x) at 0 degrees -> turn it 90 degrees
JLC_SHIFT_TO_PADS = {"C5362159": 2.0}
JLC_ROT_ADD = {"C56496": 90}
LCSC_OF = {d: p[2] for p in PARTS.values() for d in p[3]}


def cli(*a):
    r = subprocess.run([CLI, *a], capture_output=True, text=True)
    if r.returncode not in (0, 5):          # 5 = DRC violations found (reported below)
        sys.exit("kicad-cli %s failed:\n%s%s" % (a[:3], r.stdout, r.stderr))
    return r


if os.path.isdir(FAB):
    for root, _, files in os.walk(FAB):
        for n in files:   # a file open in another program (Excel on a CSV) can't be replaced: say which one
            try:
                with open(os.path.join(root, n), "ab"):
                    pass
            except PermissionError:
                sys.exit("close %s first: another program has it open" % os.path.join(root, n))
    shutil.rmtree(FAB)
os.makedirs(GERB)

# DRC (zones refilled); the report names the board by file name only, never a local path
cli("pcb", "drc", "--severity-all", "--refill-zones", "--output", os.path.join(FAB, "drc.txt"), BOARD)
with open(os.path.join(FAB, "drc.txt"), encoding="utf-8") as f:
    rep = f.read()
rep = re.sub(r"(Drc report for ).*?ffc30-tap\.kicad_pcb", r"\1ffc30-tap.kicad_pcb", rep)
with open(os.path.join(FAB, "drc.txt"), "w", encoding="utf-8", newline="\n") as f:
    f.write(rep)
kinds = re.findall(r"^\[(\w+)\]", rep, re.M)
bad = [k for k in kinds if k not in ("lib_footprint_mismatch",)]
unconnected = re.search(r"Found (\d+) unconnected", rep)
print("DRC:", len(kinds), "violations", sorted(set(kinds)), "| unconnected:", unconnected and unconnected.group(1))
if bad or (unconnected and unconnected.group(1) != "0"):
    sys.exit("DRC not clean: see fab/drc.txt")

layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
cli("pcb", "export", "gerbers", "--output", GERB + os.sep, "--layers", layers, BOARD)
cli("pcb", "export", "drill", "--output", GERB + os.sep, "--format", "excellon", "--excellon-units", "mm",
    "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", BOARD)
with zipfile.ZipFile(os.path.join(FAB, "ffc30-tap_gerbers_JLC.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for n in sorted(os.listdir(GERB)):
        z.write(os.path.join(GERB, n), n)

pos = os.path.join(FAB, "pos.csv")
cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "--output", pos, BOARD)
with open(pos, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
os.remove(pos)
with open(os.path.join(FAB, "jlc_cpl.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        x, y, rot = float(r["PosX"]), float(r["PosY"]), float(r["Rot"])
        lcsc = LCSC_OF.get(r["Ref"])
        d = JLC_SHIFT_TO_PADS.get(lcsc, 0.0)
        if d:   # the footprint's -y (y down) is "up" in the pos file (y up); turned with the part, counter-clockwise
            x += -d * math.sin(math.radians(rot))
            y += d * math.cos(math.radians(rot))
        rot = (rot + JLC_ROT_ADD.get(lcsc, 0)) % 360
        w.writerow([r["Ref"], "%.3fmm" % x, "%.3fmm" % y, "Top" if r["Side"] == "top" else "Bottom", "%g" % rot])
placed = sorted(r["Ref"] for r in rows)
want = sorted(d for p in PARTS.values() for d in p[3])
if placed != want:
    sys.exit("placement file has %s, BOM expects %s" % (placed, want))
with open(os.path.join(FAB, "jlc_bom.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for comment, footprint, lcsc, refs in PARTS.values():
        w.writerow([comment, ",".join(refs), footprint, lcsc])

for side in ("top", "bottom"):
    cli("pcb", "render", "--side", side, "--quality", "basic", "--width", "1800", "--height", "1650",
        "--background", "opaque", "--use-board-stackup-colors",
        "--output", os.path.join(HERE, "render_%s.png" % side), BOARD)

# no local path may leave this machine in a public file: neither this folder's nor the home folder's
needles = set()
for p in (HERE, os.path.expanduser("~")):
    for v in (p, p.replace("\\", "/"), p.replace("/", "\\")):
        needles.update({v.encode(), v.lower().encode(), v.upper().encode()})
for root, _, files in os.walk(FAB):
    for n in files:
        with open(os.path.join(root, n), "rb") as f:
            data = f.read()
        if any(s in data for s in needles):
            sys.exit("local path left in " + os.path.join(root, n))
print("fab files in", FAB)
