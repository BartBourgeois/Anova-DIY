"""Cut views out of a stitched board mosaic for following traces: plain, contrast-enhanced, or copper islands.

Modes:
  crop     the box as it is (Lanczos when scaled)
  enhance  CLAHE on the lightness channel: copper under the green solder mask stands out from bare laminate
  islands  top-layer copper segmented and each connected island drawn in its own colour on a dimmed board, so a
           trace can be followed from pin to pin at a glance. Colour breaks where silkscreen crosses a trace, at the
           edge of a pad, and under chip bodies: the island map suggests, the eye and the meter decide.

Copper under the mask reads yellower than bare laminate (CIELAB b* about 150-167 against about 134, hue below 78 on
OpenCV's 0-180 scale); bare tin pads read grey (low saturation, mid lightness). The thresholds below were tuned on
the 2026-11-03 component-side mosaic under the microscope's ring light; another light needs a new look at them.

The box is in mosaic pixels (x0 y0 x1 y1, the same pixels as "box" in annotations/crops.json). --grid draws a
labelled line every N mosaic pixels, so positions can be read back off the output.

Read-only: writes PNGs to .capture/trace/ (gitignored) and, with --cache, a raw copy of the mosaic to
.capture/cache/ so later views skip the PNG decode (about 1.1 GB for the main-board mosaic).

Usage:  py -3.13 tools/trace/trace.py islands 3150 10050 4250 11250 --scale 0.9 --grid 200 --cache
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# Stitched mosaics run to hundreds of megapixels; they are our own files, not untrusted input.
Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SOURCE = ROOT / "micro" / "2026-11-03_main_component-side" / "mosaic.png"
OUT_DIR = ROOT / ".capture" / "trace"
CACHE_DIR = ROOT / ".capture" / "cache"

COPPER_B_MIN, COPPER_S_MIN, COPPER_H_MAX = 143, 70, 78   # Lab b*, HSV saturation, HSV hue (OpenCV scales)
PAD_S_MAX, PAD_L_RANGE = 60, (110, 205)                  # bare tin: grey, not as bright as silkscreen
MIN_ISLAND_PX = 160                                      # at scale 1; smaller islands are noise


def load(source: Path, cache: bool) -> np.ndarray:
    """The mosaic as an RGB array (memory-mapped from the cache when there is one)."""
    npy = CACHE_DIR / (source.parent.name + ".npy")
    if cache and npy.exists():
        return np.load(npy, mmap_mode="r")
    with Image.open(source) as im:
        rgb = np.asarray(im.convert("RGB"))
    if cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.save(npy, rgb)
        print(f"cached {npy}")
    return rgb


def islands(rgb: np.ndarray, scale: float) -> np.ndarray:
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    light, _, yellow = cv2.split(lab)
    hue, sat, _ = cv2.split(hsv)
    copper = (yellow > COPPER_B_MIN) & (sat > COPPER_S_MIN) & (hue < COPPER_H_MAX)
    pad = (sat < PAD_S_MAX) & (light > PAD_L_RANGE[0]) & (light < PAD_L_RANGE[1])
    mask = cv2.morphologyEx((copper | pad).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, label, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    colour = np.random.default_rng(7).integers(60, 256, (n, 3)).astype(np.uint8)
    keep = stats[:, cv2.CC_STAT_AREA] >= MIN_ISLAND_PX * scale * scale
    keep[0] = False
    dimmed = (cv2.cvtColor(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB) * 0.35).astype(np.uint8)
    return np.where(keep[label][..., None], colour[label], dimmed)


def enhance(rgb: np.ndarray) -> np.ndarray:
    light, a, b = cv2.split(cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB))
    light = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8)).apply(light)
    return cv2.cvtColor(cv2.merge((light, a, b)), cv2.COLOR_LAB2RGB)


def grid(rgb: np.ndarray, box, scale: float, step: int) -> np.ndarray:
    out = rgb.copy()
    x0, y0, x1, y1 = box
    for x in range(-(-x0 // step) * step, x1, step):
        u = round((x - x0) * scale)
        cv2.line(out, (u, 0), (u, out.shape[0] - 1), (255, 255, 0), 1)
        cv2.putText(out, str(x), (u + 3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)
    for y in range(-(-y0 // step) * step, y1, step):
        v = round((y - y0) * scale)
        cv2.line(out, (0, v), (out.shape[1] - 1, v), (255, 255, 0), 1)
        cv2.putText(out, str(y), (3, v - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["crop", "enhance", "islands"])
    ap.add_argument("box", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), help="mosaic pixels")
    ap.add_argument("--scale", type=float, default=1.0, help="output scale (default 1 = full resolution)")
    ap.add_argument("--grid", type=int, default=0, metavar="N", help="labelled line every N mosaic pixels")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="mosaic PNG (default: main board, component side)")
    ap.add_argument("--cache", action="store_true", help="keep a raw copy in .capture/cache/ for fast repeat views")
    ap.add_argument("--out", type=Path, help="output PNG (default: .capture/trace/<mode>_<box>.png)")
    args = ap.parse_args()

    if not args.source.exists():
        sys.exit(f"mosaic not found: {args.source} (micro/ is local only, see docs/photos.md)")
    mosaic = load(args.source, args.cache)
    x0, y0, x1, y1 = args.box
    if not (0 <= x0 < x1 <= mosaic.shape[1] and 0 <= y0 < y1 <= mosaic.shape[0]):
        sys.exit(f"box outside the mosaic ({mosaic.shape[1]}x{mosaic.shape[0]})")
    rgb = np.ascontiguousarray(mosaic[y0:y1, x0:x1])
    if args.scale != 1:
        interp = cv2.INTER_AREA if args.scale < 1 else cv2.INTER_LANCZOS4
        rgb = cv2.resize(rgb, None, fx=args.scale, fy=args.scale, interpolation=interp)
    if args.mode == "enhance":
        rgb = enhance(rgb)
    elif args.mode == "islands":
        rgb = islands(rgb, args.scale)
    if args.grid:
        rgb = grid(rgb, args.box, args.scale, args.grid)

    out = args.out or OUT_DIR / f"{args.mode}_{x0}_{y0}_{x1}_{y1}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(out)
    print(f"{out}  {rgb.shape[1]}x{rgb.shape[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
