"""Render annotated board images and callout tables from annotations/<board>.json.

Each annotation file names a board image in images/boards/ and lists callouts:
    {"id": 1, "ref": "U7", "label": "...", "part": "...", "marking": "...",
     "bbox": [x0, y0, x1, y1]  or  [[x0, y0, x1, y1], ...],
     "category": "mcu", "confidence": "confirmed", "note": "..."}
bbox coordinates are pixels in the (unscaled) board image.

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
        for x0, y0, x1, y1 in boxes_of(c):
            if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
                errors.append(f"{name}#{cid}: bbox {[x0, y0, x1, y1]} outside image {w}x{h}")
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
    f_tag = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 22)
    f_leg = load_font(["arial.ttf", "DejaVuSans.ttf", "Arial.ttf"], 19)
    f_leg_b = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 19)
    f_title = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 26)

    for c in ann["callouts"]:
        color = CATEGORIES[c["category"]][0]
        for x0, y0, x1, y1 in boxes_of(c):
            box = [x0 * scale, y0 * scale, x1 * scale, y1 * scale]
            styled_rect(draw, box, color, CONFIDENCE[c["confidence"]])
            # tag above the box's top-left corner, or inside it when at the image top
            ty = box[1] - 32 if box[1] >= 32 else box[1] + 4
            tag(draw, (max(box[0], 0), ty), str(c["id"]), color, f_tag)

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

    title_h = 70
    legend_h = margin * 2 + line_h * len(lines)
    W = img.width + panel_w
    H = max(img.height, legend_h) + title_h
    canvas = Image.new("RGB", (W, H), "#1b1b1f")
    canvas.paste(img, (0, title_h))
    cd = ImageDraw.Draw(canvas)
    cd.text((margin, 10), ann["title"], fill="white", font=f_title)
    cd.text((margin, 42), f"Source: {ann['source']}", fill="#c8c8c8", font=f_leg)

    y = title_h + margin
    x = img.width + margin
    for text, font, swatch in lines:
        if swatch:
            cd.rectangle([x, y + 4, x + 14, y + 18], fill=swatch, outline="black")
        cd.text((x + 22 if swatch else x, y), text.lstrip() if swatch else text, fill="white", font=font)
        y += line_h

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}.png"
    canvas.save(out, optimize=True)
    write_markdown(name, ann)
    print(f"  {out.relative_to(ROOT)}  {canvas.width}x{canvas.height}  {len(ann['callouts'])} callouts")
    return []


def md_cell(s) -> str:
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def write_markdown(name: str, ann: dict):
    MD_DIR.mkdir(parents=True, exist_ok=True)
    rows = [
        f"<!-- GENERATED by tools/annotate.py from annotations/{name}.json. Do not edit by hand. -->",
        f"# Callouts: {ann['title']}",
        "",
        f"Source: {ann['source']}  ",
        f"Annotated image: [images/annotated/{name}.png](../../../images/annotated/{name}.png)",
        "",
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
