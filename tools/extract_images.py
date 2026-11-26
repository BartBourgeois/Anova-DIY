"""Extract embedded images from the photo PDFs under .docs/ and cut per-board crops.

Step 1: for each entry under "sources" in annotations/crops.json ({"pdf": path relative
        to .docs/, "dir": output directory, "images": {"p<page>_<n>": "descriptive-name"}}),
        each embedded image is written byte-for-byte as stored in the PDF (JPEG stays JPEG,
        no re-encode) to images/source/<dir>/<descriptive-name>.<ext>. Images without a
        name in the map keep the p<page>_<n> key, so new ones show up and can be named.
        The FCC test reports are left out on purpose: their images are RF plots.
Step 2: crops listed under "crops" are cut and saved to images/boards/<name>.<format>.
        "source" is relative to images/ (FCC images: source/..., own photos: own/...).
        The EXIF orientation is applied first, so "box" is in upright full-resolution
        pixels. Optional "max_size" downscales the result (longest side, Lanczos).
        Optional "format": "png" (default, lossless) or "jpg" (q=92, for big photo crops).
        Optional "redact": a list of [x0, y0, x1, y1] boxes (same pixels as "box") filled
        grey before cropping, for anything that must not be published (e.g. a label code).
        Optional "local": true marks a source that is not in git (stitched mosaics live in
        the gitignored micro/, so their "source" starts with ../micro/) or not in the public
        copy (an original withheld from publication). On a clone without it the crop is
        skipped, not an error; its committed output stays as it is.

Usage:  py -3.13 tools/extract_images.py
"""

import json
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageOps

# Stitched mosaics run to hundreds of megapixels; they are our own files, not untrusted input.
Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / ".docs"
IMG_DIR = ROOT / "images"
SRC_DIR = IMG_DIR / "source"
BOARD_DIR = IMG_DIR / "boards"
CROPS_FILE = ROOT / "annotations" / "crops.json"


def extract_pdf(pdf_path: Path, out_name: str, names: dict[str, str]) -> list[Path]:
    out_dir = SRC_DIR / out_name
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    seen_xrefs = set()
    with fitz.open(pdf_path) as doc:
        for page_no, page in enumerate(doc, start=1):
            for n, img in enumerate(page.get_images(full=True), start=1):
                xref = img[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                info = doc.extract_image(xref)
                key = f"p{page_no}_{n}"
                out = out_dir / f"{names.get(key, key)}.{info['ext']}"
                out.write_bytes(info["image"])
                written.append(out)
                print(f"  {out.relative_to(ROOT)}  xref={xref}  "
                      f"{info['width']}x{info['height']}  {len(info['image'])} bytes")
    return written


def in_bounds(box, size) -> bool:
    x0, y0, x1, y1 = box
    return 0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]


def cut_crops(spec: dict) -> int:
    BOARD_DIR.mkdir(parents=True, exist_ok=True)
    errors = 0
    # Group by source: a stitched mosaic takes over a GB to decode, so open each source once.
    by_source: dict[str, list[dict]] = {}
    for crop in spec["crops"]:
        by_source.setdefault(crop["source"], []).append(crop)
    for source, crops in by_source.items():
        src = IMG_DIR / source
        if not src.exists():
            for crop in crops:
                if crop.get("local"):
                    print(f"  skipped {crop['name']}: local-only source {source} not here")
                else:
                    print(f"  ERROR {crop['name']}: missing source {source}")
                    errors += 1
            continue
        with Image.open(src) as opened:
            full = ImageOps.exif_transpose(opened).convert("RGB")
        for crop in crops:
            im = full
            redact = crop.get("redact", [])
            bad = [b for b in [crop.get("box")] + redact if b and not in_bounds(b, im.size)]
            if bad:
                print(f"  ERROR {crop['name']}: box {bad[0]} outside {im.size}")
                errors += 1
                continue
            if redact:
                im = im.copy()
                draw = ImageDraw.Draw(im)
                for x0, y0, x1, y1 in redact:
                    draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=(128, 128, 128))
            box = crop.get("box")
            if box:
                im = im.crop(tuple(box))
            if crop.get("rotate"):
                im = im.rotate(crop["rotate"], expand=True)
            if crop.get("max_size"):
                im = im.copy() if im is full else im
                im.thumbnail((crop["max_size"], crop["max_size"]), Image.LANCZOS)
            fmt = crop.get("format", "png")
            out = BOARD_DIR / f"{crop['name']}.{fmt}"
            if fmt == "jpg":
                im.save(out, quality=92, subsampling=0)
            else:
                im.save(out, optimize=False)
            print(f"  {out.relative_to(ROOT)}  {im.width}x{im.height}")
    return errors


def main() -> int:
    spec = json.loads(CROPS_FILE.read_text(encoding="utf-8"))
    errors = 0
    for source in spec["sources"]:
        pdf = DOCS / source["pdf"]
        if not pdf.exists():
            print(f"ERROR missing {pdf.relative_to(ROOT)}")
            errors += 1
            continue
        print(f"{pdf.relative_to(ROOT)} -> images/source/{source['dir']}")
        extract_pdf(pdf, source["dir"], source.get("images", {}))
    print("crops")
    errors += cut_crops(spec)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
