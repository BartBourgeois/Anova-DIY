"""Stitch overlapping hand-held phone photos of a flat board into one image.

annotations/stitches.json names each stitch and its inputs:
  {"<name>": {"inputs": ["own/<date>/NN_....jpg", ...], "box": [x0, y0, x1, y1], "description": "..."}}
Inputs are relative to images/ (the byte-identical originals, EXIF rotation applied). The script writes
  images/stitched/<name>.jpg    the stitch, cut to "box" (canvas pixels; leave it out to get the whole canvas), q92
  images/stitched/<name>.json   provenance: input SHA-256, the reference photo, the links and their inlier counts,
                                each photo's homography to the canvas, canvas size, OpenCV version
Both are generated: never edit them, change stitches.json and re-run. crops.json cuts board images from the stitch
like from any photo ("source": "stitched/<name>.jpg").

How: SIFT features on a 0.35x copy, ratio-test matches and a RANSAC homography for every pair of photos. The photo
with the most inliers overall is the reference; the others are chained onto it along the strongest links (a maximum
spanning tree). A board is flat, so one homography per photo is the right model; tall parts (headers, jumpers)
show parallax and are not blended across photos: each canvas pixel comes from the photo in which it lies nearest
the centre (sharper, no fingers at the edges), and a multiband blend hides the seams.
The canvas is in the reference photo's perspective, not a true top view.

Usage:  py -3.13 tools/stitch_photos.py [name ...]      (no name: every stitch in stitches.json)
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "images"
OUT_DIR = IMG_DIR / "stitched"
SPEC_FILE = ROOT / "annotations" / "stitches.json"
WORK = 0.35       # feature detection scale: 4080 px photos -> ~1400 px
RATIO = 0.75      # Lowe's ratio test
MIN_LINK = 40     # inliers needed to chain a photo onto another
QUALITY = 92


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> np.ndarray:
    return cv2.cvtColor(np.asarray(ImageOps.exif_transpose(Image.open(path)).convert("RGB")), cv2.COLOR_RGB2BGR)


def pair_homographies(imgs):
    """H[i, j] maps photo i onto photo j (work scale); inl[i, j] = RANSAC inliers."""
    sift = cv2.SIFT_create(nfeatures=12000)
    feats = [sift.detectAndCompute(cv2.cvtColor(cv2.resize(im, None, fx=WORK, fy=WORK, interpolation=cv2.INTER_AREA),
                                                cv2.COLOR_BGR2GRAY), None) for im in imgs]
    bf = cv2.BFMatcher(cv2.NORM_L2)
    n = len(imgs)
    H, inl = {}, np.zeros((n, n), int)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            (ki, di), (kj, dj) = feats[i], feats[j]
            good = [a for a, b in bf.knnMatch(di, dj, k=2) if a.distance < RATIO * b.distance]
            if len(good) < 20:
                continue
            p = np.float32([ki[m.queryIdx].pt for m in good])
            q = np.float32([kj[m.trainIdx].pt for m in good])
            h, mask = cv2.findHomography(p, q, cv2.RANSAC, 3.0)
            if h is not None:
                H[i, j], inl[i, j] = h, int(mask.sum())
    return H, inl


def chain(H, inl):
    """The reference photo and every photo's homography onto it, along a maximum spanning tree."""
    n = len(inl)
    ref = int(np.argmax(inl.sum(0) + inl.sum(1)))
    to_ref, links = {ref: np.eye(3)}, []
    while len(to_ref) < n:
        cands = [(inl[b, a], b, a) for a in to_ref for b in range(n) if b not in to_ref and inl[b, a] >= MIN_LINK]
        if not cands:
            break
        w, b, a = max(cands)
        to_ref[b] = to_ref[a] @ H[b, a]
        links.append((b, a, int(w)))
    return ref, to_ref, links


def stitch(name: str, spec: dict) -> int:
    paths = [IMG_DIR / p for p in spec["inputs"]]
    imgs = [load(p) for p in paths]
    H, inl = pair_homographies(imgs)
    ref, to_ref, links = chain(H, inl)
    if len(to_ref) < len(imgs):
        missing = [spec["inputs"][i] for i in range(len(imgs)) if i not in to_ref]
        print(f"  ERROR {name}: no link of {MIN_LINK}+ inliers for {missing}")
        return 1
    s = np.diag([WORK, WORK, 1.0])
    full = {k: np.linalg.inv(s) @ h @ s for k, h in to_ref.items()}
    corners = np.vstack([cv2.perspectiveTransform(
        np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2), full[k]).reshape(-1, 2)
        for k, (h, w) in ((k, imgs[k].shape[:2]) for k in full)])
    x0, y0 = np.floor(corners.min(0))
    x1, y1 = np.ceil(corners.max(0))
    W, Hc = int(x1 - x0), int(y1 - y0)
    shift = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]])
    # Weight = distance to the photo's own border (1 at the centre); each pixel takes the photo where it is highest.
    warped, weight = [], []
    for k in range(len(imgs)):
        h, w = imgs[k].shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        centre = np.minimum(np.minimum(xx, w - 1 - xx) / (w / 2), np.minimum(yy, h - 1 - yy) / (h / 2))
        m = shift @ full[k]
        warped.append(cv2.warpPerspective(imgs[k], m, (W, Hc), flags=cv2.INTER_LANCZOS4))
        weight.append(cv2.warpPerspective(centre, m, (W, Hc), flags=cv2.INTER_LINEAR, borderValue=0))
    weight = np.stack(weight)
    best, covered = weight.argmax(0), weight.max(0) > 0.01
    blender = cv2.detail_MultiBandBlender(0, 6)
    blender.prepare((0, 0, W, Hc))
    for k, im in enumerate(warped):
        blender.feed(im.astype(np.int16), ((best == k) & covered).astype(np.uint8) * 255, (0, 0))
    out, mask = blender.blend(None, None)
    out = np.clip(out, 0, 255).astype(np.uint8)
    out[mask == 0] = 0
    box = spec.get("box") or [0, 0, W, Hc]
    if not (0 <= box[0] < box[2] <= W and 0 <= box[1] < box[3] <= Hc):
        print(f"  ERROR {name}: box {box} outside the {W}x{Hc} canvas")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jpg = OUT_DIR / f"{name}.jpg"
    cv2.imwrite(str(jpg), out[box[1]:box[3], box[0]:box[2]], [cv2.IMWRITE_JPEG_QUALITY, QUALITY])
    names = spec["inputs"]
    prov = {
        "name": name,
        "inputs": [{"path": p, "sha256": sha256(IMG_DIR / p)} for p in names],
        "reference": names[ref],
        "links": [{"photo": names[b], "onto": names[a], "inliers": w} for b, a, w in links],
        "canvas": [W, Hc],
        "box": box,
        "homography_to_canvas": {names[k]: (shift @ full[k]).round(6).tolist() for k in sorted(full)},
        "opencv": cv2.__version__,
        "params": {"work_scale": WORK, "ratio": RATIO, "min_link": MIN_LINK, "jpeg_quality": QUALITY},
    }
    (OUT_DIR / f"{name}.json").write_text(json.dumps(prov, indent=1) + "\n", encoding="utf-8")
    print(f"  {jpg.relative_to(ROOT)}: canvas {W}x{Hc}, box {box}, reference {names[ref]}")
    for b, a, w in links:
        print(f"    {names[b]} -> {names[a]}: {w} inliers")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("names", nargs="*", help="stitches to build (default: all)")
    args = ap.parse_args()
    spec = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
    unknown = [n for n in args.names if n not in spec]
    if unknown:
        print(f"unknown stitch(es): {', '.join(unknown)}")
        return 2
    return max([stitch(n, spec[n]) for n in (args.names or spec)], default=0)


if __name__ == "__main__":
    sys.exit(main())
