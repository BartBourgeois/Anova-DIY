# microscope

Still frames from the Andonstar AD409 Pro-ES microscope's USB live view, saved as PNG. Windows only.
Everything known about the microscope: [docs/microscope.md](../../docs/microscope.md).

```sh
py -3.13 -m pip install opencv-python pygrabber   # once
py -3.13 tools/microscope/capture.py --list       # which video index is the microscope
py -3.13 tools/microscope/capture.py --name U14-t3018
```

Frames go to `.capture/` at the repository root (gitignored), named `YYYYMMDD_HHMMSS[_name]_WxH.png`. A frame worth
keeping is imported from there like any other photo (see [photos.md](../../docs/photos.md)).

## What the microscope does over USB
- Plug in the **data** cable and select **PC Camera** on the microscope. Windows sees a standard UVC webcam called
  "USB Camera" (USB VID 0603, PID 8612). The tool finds it by that name, because its video index shifts when cameras
  come and go. The name lookup reads the device list only and opens nothing.
- **The live view tops out at 1920x1080**: MJPG and H.264 at 1920x1080, 1280x720, 640x480 and 320x240, all at 30 fps.
  The 4K and "24M" photo sizes exist only for shots saved to the microSD card.
- **Asking for any other mode hangs its video stream** until the USB cable is replugged (seen with 3840x2160).
  Windows keeps listing the device, but every open times out after about 25 s. The tool only requests the listed MJPG
  modes.
- `--size` picks one of those modes (default 1920x1080). The tool waits about 1 s for the auto exposure before it keeps
  a frame.

## Options
| Option | Default | |
|---|---|---|
| `--out DIR` | `<repo>/.capture` | output directory |
| `--name TEXT` | none | added to the file name |
| `--size WxH` | `1920x1080` | an advertised MJPG size |
| `--list` | | list the video devices, mark the microscope, and exit |
