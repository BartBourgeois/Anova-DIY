"""Publish a stitched microscope mosaic at full resolution: a Deep Zoom pyramid for the site's viewer.

The mosaics stay out of git (the gitignored micro/<set>/mosaic.png, hundreds of MB, see docs/photos.md). This script
cuts one into tiles that the site serves and docs/mosaics.md shows with OpenSeadragon:
  images/mosaics/<set>.dzi                              the descriptor: size, tile size, format
  images/mosaics/<set>_files/<level>/<col>_<row>.webp   510 px tiles + 1 px overlap, WebP q90 with alpha (the
                                                        mosaic's uncovered areas stay transparent); the highest
                                                        level is the mosaic at 100 %, each level below halves it
Optional --png writes the same pixels as a lossless PNG: the download behind the viewer (a GitHub release asset,
never committed).
Before anything is written, every "redact" box used by any crop of this mosaic in annotations/crops.json (crops whose
"source" is ../micro/<set>/mosaic.png) is filled grey as extract_images.py does it, so the full-resolution copies
never show more than the published crops.

Usage:  py -3.13 tools/deepzoom.py <set> [--mosaic path/to/mosaic.png] [--png out.png]
"""

import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Stitched mosaics run to hundreds of megapixels; they are our own files, not untrusted input.
Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "images" / "mosaics"
CROPS_FILE = ROOT / "annotations" / "crops.json"
TILE = 510     # + 1 px overlap on each side: 512 px tiles
OVERLAP = 1
QUALITY = 90   # WebP: at 2x zoom indistinguishable from JPEG q90 on the 2026-11-03 mosaic, 17-25 % smaller


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def redact_boxes(set_name: str) -> list[list[int]]:
    spec = json.loads(CROPS_FILE.read_text(encoding="utf-8"))
    source = f"../micro/{set_name}/mosaic.png"
    boxes = []
    for crop in spec["crops"]:
        if crop["source"] == source:
            boxes += [b for b in crop.get("redact", []) if b not in boxes]
    return boxes


def write_level(im: Image.Image, level_dir: Path) -> tuple[int, int]:
    level_dir.mkdir(parents=True)
    cols, rows = math.ceil(im.width / TILE), math.ceil(im.height / TILE)
    for col in range(cols):
        for row in range(rows):
            x0, y0 = col * TILE - (OVERLAP if col else 0), row * TILE - (OVERLAP if row else 0)
            x1, y1 = min((col + 1) * TILE + OVERLAP, im.width), min((row + 1) * TILE + OVERLAP, im.height)
            im.crop((x0, y0, x1, y1)).save(level_dir / f"{col}_{row}.webp", quality=QUALITY, method=4)
    return cols, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("set", help="mosaic set, e.g. 2026-11-03_main_component-side")
    ap.add_argument("--mosaic", type=Path, help="the stitched mosaic (default: micro/<set>/mosaic.png)")
    ap.add_argument("--png", type=Path, help="also write the redacted mosaic here as a lossless PNG")
    args = ap.parse_args()

    src = args.mosaic or ROOT / "micro" / args.set / "mosaic.png"
    if not src.exists():
        print(f"ERROR missing {src}")
        return 1
    print(f"{src}  sha256 {sha256(src)}")
    with Image.open(src) as opened:
        im = opened.convert("RGBA")
    width, height = im.size

    boxes = redact_boxes(args.set)
    draw = ImageDraw.Draw(im)
    for x0, y0, x1, y1 in boxes:
        if not 0 <= x0 < x1 <= width or not 0 <= y0 < y1 <= height:
            print(f"ERROR redact box {[x0, y0, x1, y1]} outside {im.size}")
            return 1
        draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(128, 128, 128, 255))
        print(f"  redacted {[x0, y0, x1, y1]}")
    if not boxes:
        print("  no redact boxes in crops.json for this set")

    if args.png:
        im.save(args.png, optimize=False)
        print(f"  {args.png}  {args.png.stat().st_size} bytes  sha256 {sha256(args.png)}")

    files_dir = OUT_DIR / f"{args.set}_files"
    if files_dir.exists():
        shutil.rmtree(files_dir)
    n = 0
    for level in range(math.ceil(math.log2(max(width, height))), -1, -1):
        cols, rows = write_level(im, files_dir / str(level))
        n += cols * rows
        print(f"  level {level:2d}  {im.width}x{im.height}  {cols}x{rows} tiles")
        if level:
            im = im.reduce(2)  # 2x2 box filter; Pillow premultiplies the alpha for it
    dzi = OUT_DIR / f"{args.set}.dzi"
    dzi.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" Format="webp" Overlap="{OVERLAP}" TileSize="{TILE}">\n'
        f'  <Size Width="{width}" Height="{height}"/>\n'
        "</Image>\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in files_dir.rglob("*.webp"))
    print(f"{dzi.relative_to(ROOT)}: {n} tiles, {size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
