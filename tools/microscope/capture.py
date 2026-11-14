"""Save still frames from the Andonstar AD409 microscope's USB live view (PC Camera mode) as PNG.

The microscope is a UVC camera named "USB Camera" (USB VID 0603, PID 8612). Its DirectShow index changes whenever
cameras come and go, so it is looked up by name; the lookup only reads names and never opens a device. It advertises
MJPG and H.264 at 1920x1080, 1280x720, 640x480 and 320x240, 30 fps (read from its DirectShow capabilities on
2026-11-03). Asking it for any other mode hangs its video stream until the USB cable is replugged, so only those MJPG
modes are ever requested. Full-resolution stills only go to the microSD card.

Changes nothing on the device except the stream format. Windows only (DirectShow).
"""
import argparse
import datetime
import os
import sys

import cv2
from pygrabber.dshow_graph import FilterGraph

DEVICE = "USB Camera"
MODES = [(1920, 1080), (1280, 720), (640, 480), (320, 240)]  # advertised MJPG sizes, all 30 fps
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_device(name):
    """Return the DirectShow index of the one device called `name`, and all device names."""
    names = FilterGraph().get_input_devices()
    hits = [i for i, n in enumerate(names) if n == name]
    if len(hits) != 1:
        sys.exit(f"expected one video device named {name!r}, found {len(hits)}: {names}\n"
                 "Is the microscope plugged in (data cable) and set to PC Camera?")
    return hits[0], names


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(ROOT, ".capture"), help="output directory (default: <repo>/.capture)")
    ap.add_argument("--name", default="", help="added to the file name, e.g. U14-t3018")
    ap.add_argument("--size", default="1920x1080", help="WxH of an advertised MJPG mode (default 1920x1080)")
    ap.add_argument("--list", action="store_true", help="list the video devices, then exit")
    a = ap.parse_args()

    idx, names = find_device(DEVICE)
    if a.list:
        for i, n in enumerate(names):
            print(i, n, "<- microscope" if i == idx else "")
        return
    w, h = (int(v) for v in a.size.lower().split("x"))
    if (w, h) not in MODES:
        sys.exit(f"{w}x{h} is not an advertised mode (it would hang the stream); use one of "
                 + ", ".join(f"{mw}x{mh}" for mw, mh in MODES))

    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        sys.exit("the microscope did not open: replug its USB cable and select PC Camera again")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    ok, f = False, None
    for _ in range(30):  # about 1 s, so auto exposure settles
        ok, f = cap.read()
    cap.release()
    if not ok or f.shape[:2] != (h, w):
        sys.exit(f"no {w}x{h} frame (got {None if f is None else f.shape[1::-1]})")

    os.makedirs(a.out, exist_ok=True)
    stem = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + (f"_{a.name}" if a.name else "") + f"_{w}x{h}.png"
    path = os.path.join(a.out, stem)
    cv2.imwrite(path, f)
    print(path)


if __name__ == "__main__":
    main()
