import pcbnew, math
from pcbnew import VECTOR2I, FromMM as MM

OUT="ffc30-tap.kicad_pcb"  # rev A: KiCad 7 API, generated outside this repo; superseded by rev C
b=pcbnew.BOARD()
ds=b.GetDesignSettings()
ds.SetCopperLayerCount(2)
ds.m_TrackMinWidth=MM(0.15); ds.m_MinClearance=MM(0.15); ds.m_CopperEdgeClearance=MM(0.3)
ds.m_NetSettings.m_DefaultNetClass.SetClearance(MM(0.15))
ds.SetBoardThickness(MM(1.6))

def P(x,y): return VECTOR2I(MM(x),MM(y))
nets={}
def net(name):
    if name not in nets:
        n=pcbnew.NETINFO_ITEM(b,name); b.Add(n); nets[name]=n
    return nets[name]

# ---------- FPC footprint: XKB X05A20H30G (datasheet rev A1) ----------
VOFF=1.865  # origin at pad bounding-box centre
def fpc_fp(ref, val):
    fp=pcbnew.FOOTPRINT(b)
    fp.SetReference(ref); fp.SetValue(val)
    fp.SetFPID(pcbnew.LIB_ID("ffc30-tap","XKB_X05A20H30G_FPC30_P0.5mm"))
    fp.SetAttributes(pcbnew.FP_SMD)
    for n in range(1,31):
        p=pcbnew.PAD(fp); p.SetNumber(str(n))
        p.SetShape(pcbnew.PAD_SHAPE_RECT); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetLayerSet(p.SMDMask()); p.SetSize(VECTOR2I(MM(0.25),MM(1.30)))
        p.SetPos0(P(-7.25+(n-1)*0.5, 0-VOFF)); p.SetPosition(P(-7.25+(n-1)*0.5, 0-VOFF))
        fp.Add(p)
    for sx in (-1,1):
        p=pcbnew.PAD(fp); p.SetNumber("MP")
        p.SetShape(pcbnew.PAD_SHAPE_RECT); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetLayerSet(p.SMDMask()); p.SetSize(VECTOR2I(MM(1.72),MM(2.60)))
        p.SetPos0(P(sx*9.19, 3.08-VOFF)); p.SetPosition(P(sx*9.19, 3.08-VOFF)); fp.Add(p)
    # fab body outline (B=18.5, depth ~5.9) + silk pin-1 mark
    def line(layer,x1,y1,x2,y2,w=0.1):
        s=pcbnew.FP_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(layer)
        s.SetStart0(P(x1,y1)); s.SetEnd0(P(x2,y2)); s.SetWidth(MM(w)); fp.Add(s)
    y0,y1=-0.65-VOFF+0.3, 5.25-VOFF
    for a in [(-9.25,y0,9.25,y0),(9.25,y0,9.25,y1),(9.25,y1,-9.25,y1),(-9.25,y1,-9.25,y0)]:
        line(pcbnew.F_Fab,*a)
    cy1,cy2=-1.0-VOFF, 5.5-VOFF
    for a in [(-10.3,cy1,10.3,cy1),(10.3,cy1,10.3,cy2),(10.3,cy2,-10.3,cy2),(-10.3,cy2,-10.3,cy1)]:
        line(pcbnew.F_CrtYd,*a,0.05)
    c=pcbnew.FP_SHAPE(fp); c.SetShape(pcbnew.SHAPE_T_CIRCLE); c.SetLayer(pcbnew.F_SilkS)
    c.SetStart0(P(-7.25,-1.3-VOFF-0.3)); c.SetEnd0(P(-7.25+0.25,-1.3-VOFF-0.3)); c.SetWidth(MM(0.2)); c.SetFilled(True); fp.Add(c)
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    return fp

X_L, X_R = 75.0, 125.0
Y_T, Y_B = 78.0, 122.0
YC=100.0
J1=fpc_fp("J1","FPC30 host side"); b.Add(J1)
J1.SetPosition(P(X_L+4.8-VOFF, YC)); J1.SetOrientationDegrees(-90)
J2=fpc_fp("J2","FPC30 target side"); b.Add(J2)
J2.SetPosition(P(X_R-4.8+VOFF, YC)); J2.SetOrientationDegrees(90)

# ---------- 2x15 header, odd = left column, even = right column ----------
XO, XE = 100-1.27, 100+1.27
def yrow(r): return YC+(r-8)*2.54
H=pcbnew.FOOTPRINT(b); H.SetReference("J3"); H.SetValue("Tap 2x15 2.54mm")
H.SetFPID(pcbnew.LIB_ID("ffc30-tap","PinHeader_2x15_P2.54mm_tap"))
H.SetAttributes(pcbnew.FP_THROUGH_HOLE)
b.Add(H); H.SetPosition(P(100,YC))
for n in range(1,31):
    r=(n+1)//2
    p=pcbnew.PAD(H); p.SetNumber(str(n))
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetAttribute(pcbnew.PAD_ATTRIB_PTH); p.SetLayerSet(p.PTHMask())
    p.SetSize(VECTOR2I(MM(1.6),MM(1.6))); p.SetDrillSize(VECTOR2I(MM(1.0),MM(1.0)))
    p.SetPos0(P(-1.27 if n%2 else 1.27, (r-8)*2.54)); p.SetPosition(P(XO if n%2 else XE, yrow(r)))
    H.Add(p)
H.Reference().SetVisible(False); H.Value().SetVisible(False)

# nets on pads, keyed by J1 pin number, matched to J2 by physical lateral position
def padmap(fp):
    return {pd.GetNumber():pd for pd in fp.Pads() if pd.GetNumber()!="MP"}
p1,p2,ph=padmap(J1),padmap(J2),padmap(H)
for n in range(1,31):
    nm="S%02d"%n
    a=p1[str(n)]; ya=pcbnew.ToMM(a.GetPosition().y)
    c=[pd for pd in p2.values() if abs(pcbnew.ToMM(pd.GetPosition().y)-ya)<1e-3]
    assert len(c)==1, n
    for pd in (a,c[0],ph[str(n)]): pd.SetNet(net(nm))
    assert abs(ya-(YC+(n-15.5)*0.5))<1e-3, (n,ya)

W=0.2
def track(pts,nm):
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
        t=pcbnew.PCB_TRACK(b); t.SetStart(P(x1,y1)); t.SetEnd(P(x2,y2))
        t.SetWidth(MM(W)); t.SetLayer(pcbnew.F_Cu); t.SetNet(net(nm)); b.Add(t)

xJ1=pcbnew.ToMM(p1["1"].GetPosition().x); xJ2=pcbnew.ToMM(p2["1"].GetPosition().x)
E1L,E2L=xJ1+1.2,96.0
E2R,E1R=104.0,xJ2-1.2
for n in range(1,31):
    r=(n+1)//2; yn=YC+(n-15.5)*0.5; yr=yrow(r)
    if n%2:   # odd: left level = pad row, right level = row-1.27
        yl, yrr = yr, yr-1.27
        mid=[(XO,yr),(XE,yr-1.27)]
    else:     # even: left level = row+1.27, right level = pad row
        yl, yrr = yr+1.27, yr
        mid=[(XO,yr+1.27),(XE,yr)]
    pts=[(xJ1,yn),(E1L,yn),(E2L,yl)]+mid+[(E2R,yrr),(E1R,yn),(xJ2,yn)]
    track(pts,"S%02d"%n)

# ---------- outline, holes, silk ----------
def edge(x1,y1,x2,y2):
    s=pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(P(x1,y1)); s.SetEnd(P(x2,y2)); s.SetWidth(MM(0.1)); b.Add(s)
edge(X_L,Y_T,X_R,Y_T); edge(X_R,Y_T,X_R,Y_B); edge(X_R,Y_B,X_L,Y_B); edge(X_L,Y_B,X_L,Y_T)
for i,(hx,hy) in enumerate([(X_L+3,Y_T+3),(X_R-3,Y_T+3),(X_L+3,Y_B-3),(X_R-3,Y_B-3)]):
    m=pcbnew.FOOTPRINT(b); m.SetReference("H%d"%(i+1)); m.SetValue("M2")
    m.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES); b.Add(m)
    pd=pcbnew.PAD(m); pd.SetNumber(""); pd.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pd.SetShape(pcbnew.PAD_SHAPE_CIRCLE); pd.SetLayerSet(pd.UnplatedHoleMask())
    pd.SetSize(VECTOR2I(MM(2.2),MM(2.2))); pd.SetDrillSize(VECTOR2I(MM(2.2),MM(2.2)))
    pd.SetPos0(P(0,0)); m.Add(pd); m.SetPosition(P(hx,hy)); m.Reference().SetVisible(False); m.Value().SetVisible(False)

def text(s,x,y,h=0.8,rot=0,just=0):
    t=pcbnew.PCB_TEXT(b); t.SetText(s); t.SetPosition(P(x,y)); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(VECTOR2I(MM(h),MM(h))); t.SetTextThickness(MM(h*0.15))
    t.SetTextAngleDegrees(rot)
    if just<0: t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    if just>0: t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    b.Add(t)
for n in range(1,31):
    r=(n+1)//2
    if n%2: text(str(n),XO-1.15,yrow(r),0.8,0,-1)
    else:   text(str(n),XE+1.15,yrow(r),0.8,0,1)
text("FFC30 0.5mm MITM TAP  rev A",100,Y_T+1.2,0.9)
text("header = J1 pin n  |  J2 pin = 31-n",100,Y_B-1.2,0.8)
text("J1 HOST",X_L+6.5,Y_T+5.5,1.0)
text("J2 TARGET",X_R-7.5,Y_T+5.5,1.0)
text("1",X_L+6.8,YC-8.4,0.8); text("1",X_R-6.8,YC+8.4,0.8)
# pin-1 marker on header
c=pcbnew.PCB_SHAPE(b); c.SetShape(pcbnew.SHAPE_T_CIRCLE); c.SetLayer(pcbnew.F_SilkS); c.SetStart(P(XO-1.5,yrow(1)-1.3)); c.SetEnd(P(XO-1.5+0.3,yrow(1)-1.3)); c.SetFilled(True); c.SetWidth(MM(0.15)); b.Add(c)

pcbnew.SaveBoard(OUT,b)
print("saved", xJ1, xJ2)
