"""FFC30 0.5 mm tap, rev D (rev C, as ordered, is frozen in ../revC): the KiCad board, generated from code.

Run with KiCad's own Python (KiCad 10), from anywhere:
    "<KiCad>/bin/python.exe" -I generate_board.py [--out DIR]
then build_fab.py for DRC, gerbers and the JLCPCB files.

What it is: a gated pass-through for any 30-way 0.5 mm FFC. Two sockets (same part, bottom contact); between them a
bus (every line on a 2.54 mm pin beside a ground pin, as rev C), and a jumper gate on each side that decides which
lines of that side reach the bus.

Top view, one row per line (pin 30 at the top, pin 1 at the bottom, in the order of the socket pads):
    socket A | fan-out | [A BUS]   [BUS GND]   [BUS B] | fan-out | socket B
                          gate A      bus        gate B
- Nets per line n: An (left socket pin n), BUSn (the three BUS pins of the row), Bn (right socket pin n).
- A cap on A|BUS puts side A's line n on the bus, a cap on BUS|B side B's. Every gate cap on = rev C's pass-through.
- A cap on BUS|GND joins line n to the ground rail (as in rev C); the rail floats until one is on.
- The pairs stand one empty pitch apart, so a cap can't bridge two pairs.
- 4 layers: every line on the top layer (45 degree fan-out, then straight into the outer column; the BUS link round
  the ground pin runs in the gap below its row), In1 and In2 solid ground planes that join the ground column.
- Numbering: row n = pin n of the board in the LEFT socket, when that board's connector has bottom contacts and
  numbers its pins like these sockets (pin 1 on the left, seen from where the cable enters). The other way round
  the row reads 31 - n; the lines pass through either way.
"""
import argparse
import os

import pcbnew
from pcbnew import VECTOR2I, FromMM as MM

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=HERE)
args = ap.parse_args()
OUT = os.path.join(args.out, "ffc30-tap.kicad_pcb")
LIB = os.path.join(args.out, "ffc30-tap.pretty")
REV = "D"

b = pcbnew.NewBoard(OUT)
ds = b.GetDesignSettings()
ds.SetCopperLayerCount(4)
ds.SetBoardThickness(MM(1.6))
ds.m_TrackMinWidth = MM(0.15)
ds.m_MinClearance = MM(0.15)
ds.m_CopperEdgeClearance = MM(0.3)   # JLCPCB: 0.3 mm copper to a routed edge
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetClearance(MM(0.15))
nc.SetTrackWidth(MM(0.2))
nc.SetViaDiameter(MM(0.6))
nc.SetViaDrill(MM(0.3))


def P(x, y):
    return VECTOR2I(MM(x), MM(y))


nets = {}


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
        nets[name] = n
    return nets[name]


def fp_line(fp, layer, x1, y1, x2, y2, w=0.1):
    s = pcbnew.PCB_SHAPE(fp)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(layer)
    s.SetStart(P(x1, y1))
    s.SetEnd(P(x2, y2))
    s.SetWidth(MM(w))
    fp.Add(s)


def fp_rect(fp, layer, x0, y0, x1, y1, w=0.1):
    for a in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
        fp_line(fp, layer, *a, w=w)


def new_fp(name, ref, val, attrs):
    """Built at the origin, orientation 0, so item positions are footprint-relative until it is placed."""
    fp = pcbnew.FOOTPRINT(b)
    fp.SetFPID(pcbnew.LIB_ID("ffc30-tap", name))
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetAttributes(attrs)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    return fp


saved = set()
IO = pcbnew.PCB_IO_KICAD_SEXPR()   # pcbnew.FootprintLibCreate finds no plugin for a new path in KiCad 10


def to_lib(fp):
    """Write each footprint once to the project library (before it is placed)."""
    name = fp.GetFPID().GetLibItemName().wx_str()
    if name in saved:
        return
    if not os.path.isdir(LIB):
        IO.CreateLibrary(LIB)
    IO.FootprintSave(LIB, fp)
    saved.add(name)


def place(fp, x, y, deg=0):
    to_lib(fp)
    b.Add(fp)
    fp.SetPosition(P(x, y))
    if deg:
        fp.SetOrientationDegrees(deg)
    return fp


# ---------- FPC socket: HanElectricity 05A20L30P ----------
# (XKB X05A20L30T, the first choice, was out of stock at JLCPCB.) Land pattern from HanElectricity's drawing
# "05A20LXX" (model H-05A20LXX, rev A 2015-05-03), 30 pins:
#   signal pads 0.30 x 1.25 at 0.50 pitch (pad 1 to pad 30: A = 14.52 +-0.10, i.e. 29 pitches);
#   mounting pads 2.00 x 3.00; outer edge 2.54 beyond the end pads' outer edge (inner edge 0.69 beyond their centre);
#   from 1.45 to 4.45 below the pads' top.
# Body 19.41 wide (C), 5.25 deep, 2.00 high; pins stick out 0.73 behind it (5.98 overall); the fixing tab (1.00)
# ends 2.58 from the pin tips. The flip lid and the cable entry are at the front, opposite the pins (section A-A).
# Pin tips put 0.13 inside the pads' top, which centres the tab on its pad: the front is then 5.485 from the
# pad-row centre (likely, within about 0.2).
# Origin = body centre (JLCPCB's centroid); pads at -y, cable entry at +y.
SOCKET_PART, SOCKET_LCSC = "HanElectricity 05A20L30P", "C5362159"
SOCK_PAD_Y = -2.86               # signal-pad row centre (pads' top at -3.485)
SOCK_FRONT = 2.625               # body front (cable entry) from the origin (body 5.25 deep)
SOCK_MP_Y = SOCK_PAD_Y - 0.625 + 1.45 + 1.50   # mounting-pad centre: 1.45-4.45 below the pads' top


def socket_fp(ref):
    fp = new_fp("HanElectricity_05A20L30P_FPC30_P0.5mm", ref, SOCKET_PART, pcbnew.FP_SMD)
    for n in range(1, 31):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(n))
        p.SetShape(pcbnew.PAD_SHAPE_RECTANGLE)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetLayerSet(p.SMDMask())
        p.SetSize(VECTOR2I(MM(0.30), MM(1.25)))
        p.SetFPRelativePosition(P(-7.25 + (n - 1) * 0.5, SOCK_PAD_Y))
        fp.Add(p)
    for sx in (-1, 1):
        p = pcbnew.PAD(fp)
        p.SetNumber("MP")
        p.SetShape(pcbnew.PAD_SHAPE_RECTANGLE)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetLayerSet(p.SMDMask())
        p.SetSize(VECTOR2I(MM(2.00), MM(3.00)))
        p.SetFPRelativePosition(P(sx * (7.25 + 0.15 + 2.54 - 1.00), SOCK_MP_Y))
        fp.Add(p)
    fp_rect(fp, pcbnew.F_Fab, -9.705, SOCK_FRONT - 5.25, 9.705, SOCK_FRONT)
    fp_rect(fp, pcbnew.F_CrtYd, -10.2, SOCK_PAD_Y - 0.95, 10.2, SOCK_FRONT + 0.25, w=0.05)
    return fp


# ---------- 2x15 header: two columns of 15; origin at the body centre ----------
# Two of them butt end to end to make one 2x30 pair (pins 15 and 16 meet at the middle), so the courtyard is the
# body itself, a hair inside its ends, and the two courtyards don't overlap.
HDR_PART, HDR_LCSC = "BOOMELE 2.54-2*15P (2x15 2.54 mm male, straight)", "C56496"
PITCH, PAD_D, DRILL = 2.54, 1.7, 1.0


def header_fp(ref):
    fp = new_fp("PinHeader_2x15_P2.54mm_Vertical_centred", ref, HDR_PART, pcbnew.FP_THROUGH_HOLE)
    for r in range(15):
        for c in range(2):
            p = pcbnew.PAD(fp)
            p.SetNumber(str(2 * r + c + 1))
            p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            p.SetLayerSet(p.PTHMask())
            p.SetSize(VECTOR2I(MM(PAD_D), MM(PAD_D)))
            p.SetDrillSize(VECTOR2I(MM(DRILL), MM(DRILL)))
            p.SetFPRelativePosition(P((c - 0.5) * PITCH, (r - 7) * PITCH))
            fp.Add(p)
    fp_rect(fp, pcbnew.F_Fab, -PITCH, -7.5 * PITCH, PITCH, 7.5 * PITCH)
    fp_rect(fp, pcbnew.F_CrtYd, -PITCH, -7.5 * PITCH + 0.02, PITCH, 7.5 * PITCH - 0.02, w=0.05)
    return fp


def hole_fp(ref):
    m = new_fp("MountingHole_2.2mm_M2", ref, "M2", pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    pd = pcbnew.PAD(m)
    pd.SetNumber("")
    pd.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pd.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pd.SetLayerSet(pd.UnplatedHoleMask())
    pd.SetSize(VECTOR2I(MM(2.2), MM(2.2)))
    pd.SetDrillSize(VECTOR2I(MM(2.2), MM(2.2)))
    pd.SetFPRelativePosition(P(0, 0))
    m.Add(pd)
    return m


# ---------- geometry ----------
XC, YC = 100.0, 100.0
X_L, X_R = 52.0, 148.0          # 96 x 92 mm: the 45 degree fan-out from 15 mm of pads to 76 mm of rows
Y_T, Y_B = 54.0, 146.0
# the six columns: gate A (A, BUS), bus (BUS, GND), gate B (BUS, B); one empty pitch between the pairs
C_A, C_BA = XC - 3.5 * PITCH, XC - 2.5 * PITCH
C_BUS, C_GND = XC - 0.5 * PITCH, XC + 0.5 * PITCH
C_BB, C_B = XC + 2.5 * PITCH, XC + 3.5 * PITCH


def yrow(pin):                   # pin 30 at the top, pin 1 at the bottom, like the socket pads
    return YC + (15.5 - pin) * PITCH


def ysock(pin):                  # lateral position at both sockets: pin 30 at the top, pin 1 at the bottom
    return YC + (15.5 - pin) * 0.5


x_sp = X_L + SOCK_FRONT - SOCK_PAD_Y   # socket signal-pad centre line (left); the body front is flush with the edge
X_FD = x_sp + 1.2                # end of the straight escape from the pads; the 45 degree fan-out starts here
W = 0.2                          # 0.5 mm escape pitch: 0.2 mm tracks, 0.15 mm gaps on the diagonals

J_L = place(socket_fp("J1"), X_L + SOCK_FRONT, YC, -90)
J_R = place(socket_fp("J2"), X_R - SOCK_FRONT, YC, 90)
HDRS = []
for cx, refs in [((C_A + C_BA) / 2, ("J3", "J4")), ((C_BUS + C_GND) / 2, ("J5", "J6")),
                 ((C_BB + C_B) / 2, ("J7", "J8"))]:
    HDRS.append(place(header_fp(refs[0]), cx, YC - 7.5 * PITCH))   # lines 16-30
    HDRS.append(place(header_fp(refs[1]), cx, YC + 7.5 * PITCH))   # lines 1-15
for i, (hx, hy) in enumerate([(X_L + 3, Y_T + 3), (X_R - 3, Y_T + 3), (X_L + 3, Y_B - 3), (X_R - 3, Y_B - 3)]):
    place(hole_fp("H%d" % (i + 1)), hx, hy)

GND = net("GND")


def pad_at(fps, x, y):
    for fp in fps:
        for pd in fp.Pads():
            q = pd.GetPosition()
            if abs(pcbnew.ToMM(q.x) - x) < 1e-3 and abs(pcbnew.ToMM(q.y) - y) < 1e-3:
                return pd
    raise KeyError((x, y))


for pin in range(1, 31):
    y = yrow(pin)
    a, bus, bb = net("A%02d" % pin), net("BUS%02d" % pin), net("B%02d" % pin)
    pad_at([J_L], x_sp, ysock(pin)).SetNet(a)
    pad_at([J_R], 2 * XC - x_sp, ysock(pin)).SetNet(bb)
    pad_at(HDRS, C_A, y).SetNet(a)
    pad_at(HDRS, C_B, y).SetNet(bb)
    for x in (C_BA, C_BUS, C_BB):
        pad_at(HDRS, x, y).SetNet(bus)
    pad_at(HDRS, C_GND, y).SetNet(GND)


def track(pts, name, layer=pcbnew.F_Cu, w=W):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if (x1, y1) == (x2, y2):
            continue
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(P(x1, y1))
        t.SetEnd(P(x2, y2))
        t.SetWidth(MM(w))
        t.SetLayer(layer)
        t.SetNet(net(name))
        b.Add(t)


def mirror(pts):
    return [(2 * XC - x, y) for x, y in reversed(pts)]


for pin in range(1, 31):
    ys, yr = ysock(pin), yrow(pin)
    fan = [(x_sp, ys), (X_FD, ys), (X_FD + abs(yr - ys), yr), (C_A, yr)]
    assert X_FD + abs(yr - ys) < C_A - PAD_D / 2 - 0.5, "fan-out runs into the gate: widen the board"
    track(fan, "A%02d" % pin)
    track(mirror(fan), "B%02d" % pin)
    bus = "BUS%02d" % pin
    track([(C_BA, yr), (C_BUS, yr)], bus, w=0.3)                      # straight across the empty pitches
    yl = yr + PITCH / 2                                                # round the ground pin, in the gap below
    track([(C_BUS, yr), (C_BUS, yl), (C_BB, yl), (C_BB, yr)], bus)

# ---------- outline, ground planes ----------
for (x1, y1), (x2, y2) in [((X_L, Y_T), (X_R, Y_T)), ((X_R, Y_T), (X_R, Y_B)), ((X_R, Y_B), (X_L, Y_B)),
                           ((X_L, Y_B), (X_L, Y_T))]:
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(P(x1, y1))
    s.SetEnd(P(x2, y2))
    s.SetWidth(MM(0.1))
    b.Add(s)

for layer in (pcbnew.In1_Cu, pcbnew.In2_Cu):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(GND)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in [(X_L, Y_T), (X_R, Y_T), (X_R, Y_B), (X_L, Y_B)]:
        ol.Append(MM(x), MM(y))
    z.SetMinThickness(MM(0.25))
    z.SetLocalClearance(MM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)


# ---------- silkscreen: pin numbers, column names, ground box, title, site ----------
def text(s, x, y, h, just=0):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(s)
    t.SetPosition(P(x, y))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(VECTOR2I(MM(h), MM(h)))
    t.SetTextThickness(MM(h * 0.15))
    if just < 0:
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    b.Add(t)


def silk_line(x1, y1, x2, y2, w=0.15):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.F_SilkS)
    s.SetStart(P(x1, y1))
    s.SetEnd(P(x2, y2))
    s.SetWidth(MM(w))
    b.Add(s)


for pin in range(1, 31):         # in both gaps between the pairs
    for x in ((C_BA + C_BUS) / 2, (C_GND + C_BB) / 2):
        text(str(pin), x, yrow(pin), 0.9)
x0, x1, y0, y1 = C_GND - 1.2, C_GND + 1.2, yrow(30) - 1.9, yrow(1) + 1.9
for a in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
    silk_line(*a)
for x, s in [(C_A, "A"), (C_BA, "BUS"), (C_GND, "GND"), (C_BB, "BUS"), (C_B, "B")]:
    text(s, x, y0 - 0.9, 0.8)
    text(s, x, y1 + 0.9, 0.8)
for x, s in [((C_A + C_BA) / 2, "GATE A"), ((C_BUS + C_GND) / 2, "BUS"), ((C_BB + C_B) / 2, "GATE B")]:
    text(s, x, y0 - 2.4, 1.0)
text("SIDE A", X_L + 13, YC - 14, 1.5)
text("SIDE B", X_R - 13, YC - 14, 1.5)
text("FFC30 0.5mm TAP rev " + REV, XC, Y_T + 2.6, 1.5)
text("cooked.raptox.be", XC, Y_B - 2.6, 1.2)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(OUT, b)

# ---------- stackup: 4 layers, 1.6 mm, black mask, white silk ----------
# The stackup descriptor isn't reachable from Python in KiCad 10, so it goes into the saved file. The colours only
# drive the renders (and the stackup table); the order form at JLCPCB sets the real mask colour.
STACKUP = """\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "prepreg") (thickness 0.1) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
\t\t\t(layer "In1.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 2" (type "core") (thickness 1.24) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
\t\t\t(layer "In2.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 3" (type "prepreg") (thickness 0.1) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
\t\t\t(copper_finish "None")
\t\t\t(dielectric_constraints no)
\t\t)
"""
with open(OUT, encoding="utf-8") as f:
    pcb = f.read()
assert "(stackup" not in pcb and pcb.count("\t(setup\n") == 1, "unexpected board file layout"
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(pcb.replace("\t(setup\n", "\t(setup\n" + STACKUP, 1))
with open(os.path.join(args.out, "fp-lib-table"), "w", newline="\n") as f:
    f.write('(fp_lib_table\n  (version 7)\n  (lib (name "ffc30-tap")(type "KiCad")(uri "${KIPRJMOD}/ffc30-tap.pretty")'
            '(options "")(descr "FFC30 tap footprints"))\n)\n')
print("saved", OUT)
