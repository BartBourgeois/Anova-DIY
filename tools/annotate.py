"""Render annotated board images and callout tables from annotations/<board>.json.

Each annotation file names a board image in images/boards/ and lists callouts:
    {"id": 1, "ref": "U7", "label": "...", "part": "...", "marking": "...",
     "bbox": [x0, y0, x1, y1]  or  [[x0, y0, x1, y1], ...],
     "category": "mcu", "confidence": "confirmed", "note": "..."}
bbox coordinates are pixels in the (unscaled) board image.

Optional, for step-by-step wiring pictures (files without them render exactly as before):
    "caption": "one or two sentences under the title: what this step does",
    "terminals": [{"id": "ftdi_rxd", "label": "FTDI RXD", "group": "ftdi"}, ...]
        off-board endpoints (instrument pins), drawn in a panel between the photo and the legend;
        group = supply | ftdi | esp32 | meter | lead_red | lead_black | other (sets the colour), or "color": "#rrggbb";
        optional "y" (base-image px) places the terminal's centre there instead of at the mean y of its links
    "links": [{"from": "3", "to": "ftdi_rxd", "label": "4.7 kOhm", "style": "solid|dashed|dotted"}, ...]
        a line from a callout to a terminal or to another callout. A label on a terminal link is printed in the
        terminal's box ("via 4.7 kOhm"); on a callout-to-callout link it sits at the line's midpoint.
        Optional "via": [[x, y], ...] waypoints in base-image px: the line runs through them in order, so it can be
        routed around parts it must not seem to touch (the mid-label then sits on the middle segment, or at
        "label_at": [x, y], base-image px, the label's centre).
    "tag_px", "line_px", "box_px": tag font size (default 22), link line width (4) and box outline width (3), in
        output px, for large pictures that get shrunk to fit a screen.
    per callout, optional "tag_side": "left" | "right" | "below" (default: above the box's top-left corner) and
        "tag_dx" / "tag_dy" (output px, added last), when the default tag position would cover a neighbouring part.
    "format": "jpg" writes images/annotated/<board>.jpg (quality 90, no chroma subsampling) instead of the PNG, for
        large photo-based pictures that would exceed the repository's file-size limit as PNG. A stale output in the
        other format is removed.

Outputs (generated, never edit by hand):
    images/annotated/<board>.png         upscaled image + numbered boxes + legend
    docs/hardware/callouts/<board>.md    the same callouts as a markdown table

Usage:  py -3.13 tools/annotate.py [board ...]
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ANN_DIR = ROOT / "annotations"
BOARD_DIR = ROOT / "images" / "boards"
OUT_DIR = ROOT / "images" / "annotated"
MD_DIR = ROOT / "docs" / "hardware" / "callouts"

CATEGORIES = {
    "mcu":       ("#ff3030", "MCU / SoC"),
    "memory":    ("#ff5cc8", "Memory"),
    "debug":     ("#ffe600", "Debug / programming / test"),
    "connector": ("#2f9bff", "Connector"),
    "power":     ("#ff8c00", "Power"),
    "ui":        ("#b65cff", "UI: LEDs / touch keys"),
    "sensor":    ("#a8ff3e", "Sensor"),
    "rf":        ("#00e5ff", "RF / antenna"),
    "info":      ("#ffffff", "Marking / label"),
    "unknown":   ("#a0a0a0", "Unidentified"),
}
CONFIDENCE = {           # outline dash pattern (on, off) in output pixels; None = solid
    "confirmed": None,
    "likely":    (14, 7),
    "guess":     (4, 6),
}

GROUPS = {               # terminal / line colours
    "supply":     ("#ff8c00", "Bench supply"),
    "ftdi":       ("#00e5ff", "USB-serial adapter (FTDI, 3.3 V)"),
    "esp32":      ("#ff5cc8", "ESP32 recorder"),
    "meter":      ("#ffffff", "Multimeter"),
    "lead_red":   ("#ff4040", "Meter, red lead"),
    "lead_black": ("#b0b0b0", "Meter, black lead"),
    "other":      ("#ffe600", "Other"),
}
LINK_STYLE = {None: None, "solid": None, "dashed": (18, 9), "dotted": (5, 7)}

FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"), Path("/Library/Fonts")]


def load_font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for d in FONT_DIRS:
        for n in names:
            if (d / n).exists():
                return ImageFont.truetype(str(d / n), size)
    return ImageFont.load_default(size=size)


def boxes_of(c: dict) -> list[list[int]]:
    b = c["bbox"]
    return b if isinstance(b[0], list) else [b]


def validate(ann: dict, size: tuple[int, int], name: str) -> list[str]:
    errors, seen = [], set()
    w, h = size
    for c in ann["callouts"]:
        cid = c.get("id")
        if cid in seen:
            errors.append(f"{name}: duplicate id {cid}")
        seen.add(cid)
        if c.get("category") not in CATEGORIES:
            errors.append(f"{name}#{cid}: unknown category {c.get('category')!r}")
        if c.get("confidence") not in CONFIDENCE:
            errors.append(f"{name}#{cid}: unknown confidence {c.get('confidence')!r}")
        if c.get("tag_side") not in (None, "left", "right", "below"):
            errors.append(f"{name}#{cid}: unknown tag_side {c.get('tag_side')!r}")
        for x0, y0, x1, y1 in boxes_of(c):
            if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
                errors.append(f"{name}#{cid}: bbox {[x0, y0, x1, y1]} outside image {w}x{h}")
    ids = {str(c.get("id")) for c in ann["callouts"]}
    tids = set()
    for t in ann.get("terminals", []):
        tid = str(t.get("id"))
        if tid in ids or tid in tids:
            errors.append(f"{name}: terminal id {tid!r} clashes with another id")
        tids.add(tid)
        if "color" not in t and t.get("group", "other") not in GROUPS:
            errors.append(f"{name}: terminal {tid!r}: unknown group {t.get('group')!r}")
        if not t.get("label"):
            errors.append(f"{name}: terminal {tid!r} has no label")
        if "y" in t and not (isinstance(t["y"], (int, float)) and 0 <= t["y"] <= h):
            errors.append(f"{name}: terminal {tid!r}: y {t['y']!r} outside the image height {h}")
    for i, ln in enumerate(ann.get("links", [])):
        a, b = str(ln.get("from")), str(ln.get("to"))
        for end in (a, b):
            if end not in ids and end not in tids:
                errors.append(f"{name}: link {i}: unknown endpoint {end!r}")
        if a in tids and b in tids:
            errors.append(f"{name}: link {i}: joins two terminals; one end must be a callout")
        if ln.get("style") not in LINK_STYLE:
            errors.append(f"{name}: link {i}: unknown style {ln.get('style')!r}")
        at = ln.get("label_at")
        if at is not None and not (isinstance(at, list) and len(at) == 2 and 0 <= at[0] <= w and 0 <= at[1] <= h):
            errors.append(f"{name}: link {i}: label_at {at!r} outside image {w}x{h}")
        for pt in ln.get("via", []):
            if not (isinstance(pt, list) and len(pt) == 2 and 0 <= pt[0] <= w and 0 <= pt[1] <= h):
                errors.append(f"{name}: link {i}: waypoint {pt!r} outside image {w}x{h}")
    return errors


def dashed_line(draw, p0, p1, fill, width, pattern):
    if pattern is None:
        draw.line([p0, p1], fill=fill, width=width)
        return
    on, off = pattern
    (x0, y0), (x1, y1) = p0, p1
    length = max(abs(x1 - x0), abs(y1 - y0))
    pos = 0
    while pos < length:
        end = min(pos + on, length)
        a = (x0 + (x1 - x0) * pos / length, y0 + (y1 - y0) * pos / length)
        b = (x0 + (x1 - x0) * end / length, y0 + (y1 - y0) * end / length)
        draw.line([a, b], fill=fill, width=width)
        pos += on + off


def styled_rect(draw, box, color, pattern, width=3):
    x0, y0, x1, y1 = box
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for a, b in zip(corners, corners[1:]):
        draw.line([a, b], fill="black", width=width + 2)   # halo for contrast
    for a, b in zip(corners, corners[1:]):
        dashed_line(draw, a, b, color, width, pattern)


def tag(draw, xy, text, color, font):
    x, y = xy
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    tw, th = r - l, b - t
    pad = 4
    box = [x, y, x + tw + 2 * pad, y + th + 2 * pad]
    draw.rectangle(box, fill=color, outline="black", width=2)
    draw.text((x + pad - l, y + pad - t), text, fill="black", font=font)
    return box


def border_point(box, target):
    """Where the ray from the box's centre toward target leaves the box."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = target[0] - cx, target[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    hw, hh = (x1 - x0) / 2, (y1 - y0) / 2
    t = min(hw / abs(dx) if dx else float("inf"), hh / abs(dy) if dy else float("inf"))
    return cx + dx * t, cy + dy * t


def link_line(draw, p0, p1, color, pattern, width=4):
    dashed_line(draw, p0, p1, "black", width + 4, pattern)    # halo for contrast on the board
    dashed_line(draw, p0, p1, color, width, pattern)


def wrap_px(text: str, font, max_px: int) -> list[str]:
    """Greedy word wrap by rendered width."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}" if cur else word
        if cur and font.getlength(trial) > max_px:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def render(ann_path: Path) -> list[str]:
    ann = json.loads(ann_path.read_text(encoding="utf-8"))
    name = ann_path.stem
    src = BOARD_DIR / ann["image"]
    if not src.exists():
        return [f"{name}: missing board image {src.relative_to(ROOT)} (run extract_images.py)"]
    base = Image.open(src).convert("RGB")
    errors = validate(ann, base.size, name)
    if errors:
        return errors

    scale = ann.get("scale", 2)
    img = base.resize((base.width * scale, base.height * scale), Image.LANCZOS)
    draw = ImageDraw.Draw(img)
    tag_px = int(ann.get("tag_px", 22))
    line_px = int(ann.get("line_px", 4))
    box_px = int(ann.get("box_px", 3))
    tag_off = 32 if tag_px == 22 else tag_px + 12
    f_tag = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], tag_px)
    f_leg = load_font(["arial.ttf", "DejaVuSans.ttf", "Arial.ttf"], 19)
    f_leg_b = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 19)
    f_title = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 26)

    # wiring: terminals (off-board endpoints) and links. Absent in most files; then nothing below changes.
    terms = {str(t["id"]): t for t in ann.get("terminals", [])}
    links = ann.get("links", [])
    by_id = {str(c["id"]): c for c in ann["callouts"]}

    def sbox(c):  # a callout's first box, scaled
        x0, y0, x1, y1 = boxes_of(c)[0]
        return [x0 * scale, y0 * scale, x1 * scale, y1 * scale]

    def tcolor(t):
        return t.get("color") or GROUPS[t.get("group", "other")][0]

    f_term = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 20)
    f_term_s = load_font(["arial.ttf", "DejaVuSans.ttf", "Arial.ttf"], 18)
    f_link = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 18 if tag_px == 22 else tag_px - 2)
    term_w, term_gutter = (470, 170) if terms else (0, 0)
    tpos = {}  # terminal id -> (x_left, y_top, x_right, y_bottom), in image coordinates (x beyond img.width)
    if terms:
        tlines = {}
        for tid, t in terms.items():
            via = [ln.get("label") for ln in links if str(ln.get("to")) == tid or str(ln.get("from")) == tid]
            body = wrap_px(t["label"], f_term, term_w - term_gutter - 36)
            extra = [s for v in via if v for s in wrap_px(f"via {v}", f_term_s, term_w - term_gutter - 36)]
            tlines[tid] = (body, extra)
        want = {}
        for tid in terms:
            ys = []
            for ln in links:
                a, b = str(ln.get("from")), str(ln.get("to"))
                other = b if a == tid else a if b == tid else None
                if other in by_id:
                    bx = sbox(by_id[other])
                    ys.append((bx[1] + bx[3]) / 2)
            want[tid] = sum(ys) / len(ys) if ys else 0
            if "y" in terms[tid]:  # explicit placement, in base-image px, when the mean y would cross other boxes
                want[tid] = float(terms[tid]["y"]) * scale
        order = sorted(terms, key=lambda k: want[k])
        x_l, x_r = img.width + term_gutter, img.width + term_w - 16
        prev = 8
        for tid in order:
            body, extra = tlines[tid]
            h = 14 + 25 * len(body) + 22 * len(extra)
            top = max(want[tid] - h / 2, prev + 14)
            tpos[tid] = [x_l, top, x_r, top + h]
            prev = top + h
        overflow = prev - max(img.height, 200) + 8
        if overflow > 0:  # push back up from the bottom, never above the top
            nxt = max(img.height, 200) - 8
            for tid in reversed(order):
                x0_, top, x1_, bot = tpos[tid]
                h = bot - top
                bot = min(bot, nxt)
                tpos[tid] = [x0_, max(bot - h, 8), x1_, max(bot - h, 8) + h]
                nxt = tpos[tid][1] - 14

    def endpoint(eid, toward):
        if eid in tpos:
            x0_, y0_, _, y1_ = tpos[eid]
            return (x0_, (y0_ + y1_) / 2)
        return border_point(sbox(by_id[eid]), toward)

    def centre(eid):
        if eid in tpos:
            x0_, y0_, _, y1_ = tpos[eid]
            return (x0_, (y0_ + y1_) / 2)
        b = sbox(by_id[eid])
        return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)

    segs = []  # (points, color, pattern, label or None, is_terminal_link)
    for ln in links:
        a, b = str(ln["from"]), str(ln["to"])
        via = [(x * scale, y * scale) for x, y in ln.get("via", [])]
        p0 = endpoint(a, via[0] if via else centre(b))
        p1 = endpoint(b, via[-1] if via else centre(a))
        t = terms.get(a) or terms.get(b)
        color = tcolor(t) if t else ln.get("color", "#ffffff")
        at = ln.get("label_at")
        segs.append(([p0, *via, p1], color, LINK_STYLE[ln.get("style")], ln.get("label"), t is not None,
                     (at[0] * scale, at[1] * scale) if at else None))
    for pts, color, pattern, _, _, _ in segs:   # on the photo, clipped at its right edge
        for q0, q1 in zip(pts, pts[1:]):
            link_line(draw, q0, q1, color, pattern, line_px)

    for c in ann["callouts"]:
        color = CATEGORIES[c["category"]][0]
        for x0, y0, x1, y1 in boxes_of(c):
            box = [x0 * scale, y0 * scale, x1 * scale, y1 * scale]
            styled_rect(draw, box, color, CONFIDENCE[c["confidence"]], box_px)
            # tag above the box's top-left corner, or inside it when at the image top
            ty = box[1] - tag_off if box[1] >= tag_off else box[1] + 4
            tx = max(box[0], 0)
            side = c.get("tag_side")
            if side:
                l, t_, r, b_ = draw.textbbox((0, 0), str(c["id"]), font=f_tag)
                tw, th = r - l + 8, b_ - t_ + 8
                if side == "left":
                    tx, ty = box[0] - tw - 6, (box[1] + box[3]) / 2 - th / 2
                elif side == "right":
                    tx, ty = box[2] + 6, (box[1] + box[3]) / 2 - th / 2
                elif side == "below":
                    ty = box[3] + 6
            tx += c.get("tag_dx", 0)
            ty += c.get("tag_dy", 0)
            tag(draw, (tx, ty), str(c["id"]), color, f_tag)

    for pts, color, _, label, is_term, at in segs:   # mid-line labels of callout-to-callout links
        if label and not is_term:
            l, t, r, b = draw.textbbox((0, 0), label, font=f_link)
            k = (len(pts) - 1) // 2
            (q0x, q0y), (q1x, q1y) = pts[k], pts[k + 1]
            mx, my = at if at else ((q0x + q1x) / 2, (q0y + q1y) / 2)
            tag(draw, (mx - (r - l) / 2 - 4, my - (b - t) / 2 - 4), label, color, f_link)

    # legend panel to the right
    panel_w, line_h, margin = 640, 25, 18
    text_px = panel_w - 2 * margin - 30
    lines = []  # (text, font, color-swatch or None)
    for c in ann["callouts"]:
        head = f"{c['id']}  {c.get('ref') or '-'}  {c['label']}"
        first, *rest = wrap_px(head, f_leg_b, text_px)
        lines.append((first, f_leg_b, CATEGORIES[c["category"]][0]))
        for seg in rest:
            lines.append(("      " + seg, f_leg_b, None))
        detail = c.get("part") or ""
        detail = f"{detail}  [{c['confidence']}]".strip()
        for seg in wrap_px(detail, f_leg, text_px):
            lines.append(("      " + seg, f_leg, None))
    lines.append(("", f_leg, None))
    used = sorted({c["category"] for c in ann["callouts"]}, key=list(CATEGORIES).index)
    lines.append(("Colour = category", f_leg_b, None))
    for cat in used:
        lines.append((f"      {CATEGORIES[cat][1]}", f_leg, CATEGORIES[cat][0]))
    lines.append(("Outline = confidence: solid confirmed, dashed likely, dotted guess", f_leg, None))
    if links:
        def name_of(eid):
            if eid in terms:
                return terms[eid]["label"]
            c = by_id[eid]
            return f"{c['id']} {c.get('ref') or ''}".strip()
        lines.append(("", f_leg, None))
        lines.append(("Connections", f_leg_b, None))
        for ln in links:
            a, b = str(ln["from"]), str(ln["to"])
            t = terms.get(a) or terms.get(b)
            color = tcolor(t) if t else ln.get("color", "#ffffff")
            text = f"{name_of(a)} -> {name_of(b)}" + (f" ({ln['label']})" if ln.get("label") else "")
            first, *rest = wrap_px(text, f_leg, text_px)
            lines.append((first, f_leg, color))
            for seg in rest:
                lines.append(("      " + seg, f_leg, None))
        used_g = [g for g in GROUPS if any(t.get("group", "other") == g and "color" not in t for t in terms.values())]
        if used_g:
            lines.append(("Line colour = where it goes", f_leg_b, None))
            for g in used_g:
                lines.append((f"      {GROUPS[g][1]}", f_leg, GROUPS[g][0]))

    title_h = 70
    cap_lines = []
    if ann.get("caption"):
        cap_w = max(img.width + term_w + panel_w - 2 * margin, 600)
        cap_lines = wrap_px(ann["caption"], f_leg_b, cap_w)
        title_h += 25 * len(cap_lines) + 8
    legend_h = margin * 2 + line_h * len(lines)
    term_h = int(round(max((v[3] for v in tpos.values()), default=0))) + 16
    W = img.width + term_w + panel_w
    H = max(img.height, legend_h, term_h) + title_h
    canvas = Image.new("RGB", (W, H), "#1b1b1f")
    canvas.paste(img, (0, title_h))
    cd = ImageDraw.Draw(canvas)
    cd.text((margin, 10), ann["title"], fill="white", font=f_title)
    cd.text((margin, 42), f"Source: {ann['source']}", fill="#c8c8c8", font=f_leg)
    for i, seg in enumerate(cap_lines):
        cd.text((margin, 70 + 25 * i), seg, fill="#ffe680", font=f_leg_b)

    if terms:   # the rest of each terminal link, then the terminal boxes
        for pts, color, pattern, _, is_term, _ in segs:
            if not is_term:
                continue
            for q0, q1 in zip(pts, pts[1:]):
                (xa, ya), (xb, yb) = sorted([q0, q1])
                if xb <= img.width:
                    continue
                xs = max(xa, img.width)
                ys = ya + (yb - ya) * ((xs - xa) / (xb - xa) if xb != xa else 0)
                link_line(cd, (xs, ys + title_h), (xb, yb + title_h), color, pattern, line_px)
        for tid, t in terms.items():
            x0_, y0_, x1_, y1_ = tpos[tid]
            col = tcolor(t)
            cd.rectangle([x0_, y0_ + title_h, x1_, y1_ + title_h], fill="#26262c", outline=col, width=3)
            body, extra = tlines[tid]
            ty_ = y0_ + title_h + 8
            for seg in body:
                cd.text((x0_ + 12, ty_), seg, fill=col, font=f_term)
                ty_ += 25
            for seg in extra:
                cd.text((x0_ + 12, ty_), seg, fill="#d8d8d8", font=f_term_s)
                ty_ += 22

    y = title_h + margin
    x = img.width + term_w + margin
    for text, font, swatch in lines:
        if swatch:
            cd.rectangle([x, y + 4, x + 14, y + 18], fill=swatch, outline="black")
        cd.text((x + 22 if swatch else x, y), text.lstrip() if swatch else text, fill="white", font=font)
        y += line_h

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ext = "jpg" if ann.get("format") == "jpg" else "png"
    out = OUT_DIR / f"{name}.{ext}"
    if ext == "jpg":
        canvas.save(out, quality=90, subsampling=0, optimize=True)
    else:
        canvas.save(out, optimize=True)
    stale = OUT_DIR / f"{name}.{'png' if ext == 'jpg' else 'jpg'}"
    if stale.exists():
        stale.unlink()
    write_markdown(name, ann)
    print(f"  {out.relative_to(ROOT)}  {canvas.width}x{canvas.height}  {len(ann['callouts'])} callouts")
    return []


def md_cell(s) -> str:
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def write_markdown(name: str, ann: dict):
    ext = "jpg" if ann.get("format") == "jpg" else "png"
    MD_DIR.mkdir(parents=True, exist_ok=True)
    rows = [
        f"<!-- GENERATED by tools/annotate.py from annotations/{name}.json. Do not edit by hand. -->",
        f"# Callouts: {ann['title']}",
        "",
        f"Source: {ann['source']}  ",
        f"Annotated image: [images/annotated/{name}.{ext}](../../../images/annotated/{name}.{ext})",
        "",
    ]
    if ann.get("caption"):
        rows += [ann["caption"], ""]
    rows += [
        "| # | Ref | Identification | Part / marking | Category | Confidence | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in ann["callouts"]:
        part = c.get("part") or ""
        if c.get("marking"):
            part = f"{part}<br>marking: `{c['marking']}`" if part else f"marking: `{c['marking']}`"
        rows.append("| " + " | ".join([
            str(c["id"]), md_cell(c.get("ref")), md_cell(c["label"]), md_cell(part),
            CATEGORIES[c["category"]][1], c["confidence"], md_cell(c.get("note")),
        ]) + " |")
    if ann.get("links"):
        terms = {str(t["id"]): t for t in ann.get("terminals", [])}
        by_id = {str(c["id"]): c for c in ann["callouts"]}

        def name_of(eid):
            if eid in terms:
                return terms[eid]["label"]
            c = by_id[eid]
            return f"{c['id']} {c.get('ref') or ''}".strip()
        rows += ["", "## Connections", "", "| From | To | Through | Line |", "|---|---|---|---|"]
        for ln in ann["links"]:
            a, b = str(ln["from"]), str(ln["to"])
            rows.append("| " + " | ".join([md_cell(name_of(a)), md_cell(name_of(b)), md_cell(ln.get("label")),
                                            ln.get("style") or "solid"]) + " |")
    (MD_DIR / f"{name}.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    wanted = set(sys.argv[1:])
    files = [p for p in sorted(ANN_DIR.glob("*.json")) if p.name != "crops.json"]
    if wanted:
        files = [p for p in files if p.stem in wanted]
    errors = []
    for p in files:
        errors += render(p)
    for e in errors:
        print(f"ERROR {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
