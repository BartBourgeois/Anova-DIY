# Microscope: Andonstar AD409 Pro-ES

What is known about the bench microscope, written for building software that drives it and stitches its images
into measurable board mosaics ([photos.md](photos.md) has the capture protocol). In use since 2026-11-03.

Confidence as everywhere in this repository: `confirmed` (measured or read here), `likely` (strong evidence),
`guess`. "Measured" means on our unit, on a Windows 11 PC, on 2026-11-03. The sources are listed at the end.

## At a glance
| | | Confidence, source |
|---|---|---|
| What | 10.1" digital microscope: camera + monitor on a column stand, two LED lights on the base. Pro-ES = the AD409 Pro plus a 13 mm endoscope. | manual [M]; [E2] |
| Camera chip | **Novatek NT96660**, a dashcam / action-camera SoC | `likely`: photo EXIF [E1]; the USB vendor ID 0603 is Novatek's |
| Sensor | 4 MP | manual [M], `unverified` |
| Live view over USB | standard UVC webcam "USB Camera", **at most 1920x1080 at 30 fps** (MJPG or H.264) | `confirmed`, measured |
| Photos to the microSD card | JPG, up to 5600x4200 ("24M") | manual [M]; above the sensor's 4 MP, so interpolated: `likely` |
| Video to the microSD card | MP4: 2880x2160 at 24 fps, 1920x1080 at 60/30, 1280x720 at 120 | manual [M] |
| HDMI out | yes, resolution unknown | manual [M] |
| Wi-Fi | "test function": own access point + phone app; probably Novatek's dashcam HTTP API | manual [M]; API `guess` [D] |
| Not controllable from a PC | magnification, focus, lights | manual [M] |
| **Biggest trap** | **asking the USB camera for a mode it doesn't advertise hangs it until the cable is replugged** | `confirmed`, measured |

## Hardware and optics
- **Variants:** the AD409, AD409 Pro, AD409 Max Pro and AD409 Pro-ES share the same optics, camera and display. They
  differ in what's in the box (stand, endoscope). Source: [E1].
- **Monitor:** 10.1", 1280x800 [M]. Only one display is active at a time: the built-in one or HDMI [E2].
- **Magnification** = the height of the monitor/camera on the column. Up to 300x, a marketing figure measured "on a
  27 inch HDMI monitor" [M]. Minimum focus distance 5 cm [M]. Lens-to-baseplate clearance: up to 253 mm on the Pro's
  stand, 77-85 mm on the plain AD409's [E1, E2]; not measured on ours.
- **Focus:** a manual knob, always manual [E1]. **Turning it also moves the image** [E2], and it probably rescales it
  too (focus breathing: `likely`). So: one focus setting per mosaic.
- **Optics are not telecentric** (`likely`, a single zoom lens above the board): tall parts lean and change size
  between tiles. Flat parts (chips, pads, traces) stitch; caps and connectors won't line up perfectly.
- **Lights:** two flexible white LED spotlights on the base [E1], not controllable from the PC.
- **Buttons** [M]: power, Menu/Mode (long press = menu), Up (digital Zoom+), Down (digital Zoom-), OK/record, capture.
  Also an **IR receiver**, the endoscope socket, the microSD slot, USB, HDMI, and a reset hole.
- **Power:** 5 V 2 A over USB, from the supplied adapter and power cable [M]. The **data** cable is a separate USB
  cable (the supplied one is angled 90 degrees) [M, E1].
- **Endoscope (Pro-ES only):** 13 mm pen camera with a dimmable LED ring and a focus ring, no magnification. It
  shows on the screen and over HDMI, **not over USB** [E2, T]. Picture-in-picture and dual recording (files ending
  in A = microscope, B = endoscope) [E2].

## Ways to get images out

### 1. USB "PC Camera" mode (measured)
**Enter it:** plug in the data cable, select "PC Camera" on the microscope with Down, press OK [M]. The screen probably
offers another USB mode (mass storage) at that point: Elektor writes that the files are "also accessible over USB"
[E2]. Not tried yet.

**What Windows sees** (`confirmed`, read from Windows' device properties, which doesn't open the device):

| | |
|---|---|
| USB device | composite, `VID_0603 & PID_8612`, `REV_0010` (bcdDevice 0x0010), name reported by the device: "USB Camera" |
| Interface 0 | video (UVC, class 0E/03), Windows' built-in `usbvideo` driver. Camera name: **"USB Camera"** |
| Interface 2 | audio (class 01/02), built-in `usbaudio`. Shows up as "Microphone (USB Camera)". Untested. |
| Speed | USB 2.0 high speed: `likely` (it sits on a high-speed root-hub port, `HS08`) |
| Drivers | Windows' built-in drivers only. No vendor driver is needed. |

The name "USB Camera" is generic: other cheap webcams use it too. Find the device by that name and refuse to continue
if more than one device carries it. The **video index changes** whenever cameras come and go (measured: the
microscope moved from index 1 to absent and back, and the other cameras renumbered), so never hard-code an index.

**Video modes** (`confirmed`, read from its DirectShow capabilities):

| Format | Sizes | Frame rate |
|---|---|---|
| H.264 | 1920x1080, 1280x720, 640x480, 320x240 | 30 fps |
| MJPG | 1920x1080, 1280x720, 640x480, 320x240 | 30 fps |

Nothing above 1920x1080: **USB frames are 2 MP**, half the sensor. Use MJPG; H.264 needs a decoder and adds
inter-frame artefacts. A frame from USB is the JPEG the camera sent; saving it as PNG keeps that frame lossless
from there on, but the camera's own JPEG compression is already in it.

**The hang** (`confirmed`):
- Requesting a size it doesn't advertise (seen with 3840x2160) kills the stream on the spot. After that, every open
  waits about 25 s and fails, in every program, until the **USB cable is replugged**. Windows keeps listing the
  device, so a device list doesn't reveal the hang. Andonstar's FAQ says to delete the device in Device Manager and
  replug [M, FAQ 6]. Restarting the device from software needs administrator rights.
- **Open question:** it also hung once after a good 1920x1080 capture, followed twice by a program that opened the
  device's DirectShow filter only to read its mode list (no format set, no stream). Either opening the filter or
  closing the camera after a 1080p stream did it. A test is pending. Until then: one program owns the camera, it
  opens it once, and it doesn't query capabilities through the driver.
- Software must assume the camera can hang: put a timeout on every open, and when it trips, ask for a replug
  instead of retrying.

**Camera controls over USB** (exposure, white balance, gain, sharpness): unknown. UVC exposes them through the
driver, which means opening the device. Test them once the open question above is settled. The device's own menus
and remote set most of them anyway (see [Settings](#settings) and [IR remote](#5-ir-remote)).

**Windows software notes** (measured, OpenCV 5.0 on Python 3.13):
- OpenCV's DirectShow backend (`cv2.CAP_DSHOW`) works: set the FOURCC to MJPG first, then width and height.
  Without that OpenCV defaults to 640x480. Discard about 30 frames (1 s) after opening, so the auto exposure settles.
- OpenCV's Media Foundation backend (`cv2.CAP_MSMF`) opened **no** camera on this PC, the microscope included.
  Don't rely on it.
- Camera names come from DirectShow's device enumerator (e.g. `pygrabber`'s `FilterGraph().get_input_devices()`),
  which reads names only. DirectShow and OpenCV number devices in the same order.
- Andonstar's own PC software, "Microscope Measure" (Windows, .NET 4.0 + VC++ 2010; link in the manual): live view,
  ruler calibration, measuring, capture. Not needed and not installed.
- The working tool here is [`tools/microscope/capture.py`](../tools/microscope/README.md): finds the camera by name,
  only accepts the four MJPG sizes, saves PNG frames.

### 2. microSD card (photos and video)
- The only route to full resolution. Photo sizes go up to 5600x4200; Elektor quotes the manual of their unit for a
  4032x3024 maximum and suspects oversampling [E1]. Which size is the sensor's native one is unknown: shoot a fine
  target at every setting and compare the detail ([photos.md](photos.md), resolution test).
- JPG only, no RAW [E1].
- Getting the shot taken: the capture button (moves the microscope), the IR remote, or Wi-Fi (below).
- Getting the files: the card in a reader, or Wi-Fi's file browser, or probably USB mass storage (above).
- Card trouble is common: Elektor's 64 GB card wouldn't record video, an 8 GB card did; UHD recording locked up the
  menus until a reboot [E2]. The manual says to format the card in the microscope first [M, FAQ 4]. No hot swap [M].

### 3. HDMI
HDMI output exists [M]; its resolution and whether the on-screen icons and grid lines are burned into it are unknown.
**Worth testing with an HDMI capture card:** if it outputs above 1080p, that is a sharper live source than USB.

### 4. Wi-Fi ("test function")
- Needs a microSD card inserted. Menu: long press M, press M again for the system settings, "WIFI" → On. The access
  point is `Andonstar-…`, password `12345678` by default. App: "Ucam Dashcam" [M]; Elektor used another app and needed
  location services on [E1].
- While Wi-Fi is on, the buttons and the remote stop working except M, which turns Wi-Fi off. The remote's "50/60Hz"
  button turns Wi-Fi on. [E1]
- Elektor reached the stored files with a browser at "198.168.1.254" [E1], probably a typo for **192.168.1.254**,
  the default of Novatek dashcams [D].
- **Probably Novatek's dashcam HTTP API** (`guess`: same SoC family, same address, a dashcam app). Documented only by
  users, for NT96655 dashcams, on a forum [D]: `http://192.168.1.254/?custom=1&cmd=<n>&par=<p>`. Commands that would
  matter here:

  | cmd | | Kind |
  |---|---|---|
  | 1001 | take a photo (returns the file name) | changes state: the point of a capture trigger |
  | 3001 | mode: 0 photo, 1 video, 2 playback | changes state |
  | 3002 | list the supported commands | read-only: **try this first** |
  | 3012 | firmware version | read-only |
  | 3014 | status of the last command | read-only |
  | 3015 | file list | read-only |
  | 3016 | heartbeat | read-only |
  | 3017 | free space | read-only |
  | 4001 / 4002 | thumbnail / preview of a file | read-only |
  | 2015 | start/stop the live stream; RTSP at `rtsp://192.168.1.254/<any>.mov` | changes state |

  **Never send** 3003/3004/3032/3033 (network settings), 3010 (format the card), 3011 (factory defaults),
  3013 (firmware update), 3021 (save settings), 4003/4004 (delete files) or 5001 (unknown flash data). The forum
  posters report that some commands freeze or restart their cameras [D].
- If 1001 works, a capture program can trigger full-resolution card shots during a mosaic, and fetch them
  afterwards over the same link.

### 5. IR remote
Two AAA cells [E1]. Buttons, from the manual's figure P6 [M]:

| | |
|---|---|
| Capture | Menu, Mode, OK/start video |
| Zoom+ / Zoom- (digital) | Frozen (freeze the picture) |
| Brightness + / - | Contrast + / - |
| Sharpness + / - | Black & white, Inverse, Image rotate |
| Cross line (on-screen grid) | Lock/unlock file |
| WIFI On/Off (printed "50/60HZ") | Switch lens image (endoscope only), NTSC/PAL, Default set |

So the remote changes the **image processing** too: brightness, contrast, sharpness, black & white, inverse and
rotation are set on the device, and they reach every output (`likely`). For a mosaic, set them once and don't touch
the remote mid-set. The IR codes are unknown. A microcontroller with an IR LED could press "Capture" for the PC: the
fallback trigger if Wi-Fi doesn't work. Learning the codes needs an IR receiver module.

## Settings
- **Menus** [M, figures P7 and P8]: long press M in video standby for the video menu; press M to switch to photo mode,
  then long press M for the photo menu; press M again for the system settings (Wi-Fi among them).
  - Video menu: Resolution, Exposure, **Date Stamp**, Sharpness, Freeze, Contrast, color.
  - Photo menu (page 1 of 2): Resolution, Burst, Quality, Sharpness, **White Balance**, color, **ISO**.
  - So exposure, white balance and ISO can probably be fixed on the device, whatever USB exposes (`likely`). Switch
    the **date stamp** off before shooting tiles: if it's on, it is probably burned into the photos (`guess`).
- Settings survive only a **long press on the power button** before the power is removed; pulling the power loses
  them [M, FAQ 3]. Elektor found that settings didn't persist even so [E2].
- On-screen **grid lines** (cross, lines, direction, position, colour, width) are configurable [M]. Whether they show
  up in USB frames, card photos or HDMI is unknown: switch them off for mosaics until that's checked.
- The Zoom+/- buttons are **digital zoom**. Keep them at 1x for mosaics.

## What capture and stitching software has to handle
From the protocol in [photos.md](photos.md) and the behaviour above:
- **Tiles:** the board moves, the microscope doesn't. Slide the board along a straightedge (no rotation), about 40 %
  overlap in both directions, row by row in a serpentine order. One magnification and one focus for the whole set.
- **Stitch model:** translation only (flat board, fixed camera), not a panorama warp. Expect parallax on tall parts.
- **Scale:** the first frame of every set is a millimetre ruler in the board plane at the same settings: it gives
  mm/px. Check the result against known sizes (U1 body 9 mm, J14 pitch 1.27 mm).
- **Two tile sources:** USB at 1920x1080 (instant, automatic, 2 MP) or the card at full resolution (sharper,
  needs a trigger and an import step). A capture assistant can watch the USB live view, tell when the board has
  moved about 40 % and stands still and sharp, then save the frame or trigger a card shot. It also keeps a coverage map.
- **Field of view, for planning only** (`guess`): the first frame, of U14 (a QFN-40 whose body is about 5 or 6 mm
  wide), works out at about 170-210 px/mm, so a 1920x1080 frame covers roughly 9-11 x 5-6 mm at that height. The
  ruler frame replaces this.
- **Originals stay originals:** tiles are copied byte-identical, never re-encoded, and the mosaic is a generated file
  ([photos.md](photos.md), storage and stitching).
- **Robustness:** only advertised modes, a timeout on every open, a clear "replug the microscope" message, and the
  camera found by name, not by index.

## Is 1920x1080 enough?
For the mosaics, yes (`likely`). Magnification, not the pixel count, decides how much detail a frame holds. Fewer
pixels per frame only means more tiles.
- **What has to stay visible:** traces and gaps of about 0.2 mm (measured on the first frame), pads at 0.4 mm pitch
  (U14), J8 at 0.5 mm pitch, vias, chip markings. Rule of thumb: at least 3-4 px across the narrowest gap and
  10-15 px of character height.
- **Simulation** on the first frame (U14 at about 206 px/mm, scaled down): at 50 and even at 30 px/mm, the traces,
  gaps, 0.4 mm-pitch pads, a via and the 0.7 mm-high marking stay clear. This is optimistic: a frame shot at low
  magnification is softer than a sharp one scaled down.
- **So:** at 40-50 px/mm one frame covers about 38 x 22 to 48 x 27 mm, and with 40 % overlap each new tile adds about
  23 x 13 mm. A board takes tens of tiles, not hundreds. Lower magnification also brings more depth of field, so tall
  parts blur less.
- **Close-ups** of small or faint markings (U13, U17, the laser-etched ones) are single frames at high magnification.
  At about 200 px/mm, 1080p is more than enough (the U14 frame).
- **What the card would add:** the sensor has 4 MP, at best about 1.4x the linear resolution of 1080p (the larger
  photo sizes are interpolated). The same detail with about half the tiles, but every set needs a trigger and an
  import step. Worth it only if real USB frames turn out soft or show MJPG artefacts.
- **The test that settles it:** at the mosaic magnification, the ruler frame plus one spot shot over USB and on the
  card, compared at 100 %.

## First mosaic (2026-11-03)
The main board's component side, stitched by the separate capture/stitch project; set details in
[photos.md](photos.md#2026-11-03-microscope-mosaic-main-board-component-side). What it shows about the capture, as
feedback for that project:
- **Numbers:** 344 USB tiles in one hour (one resume), 13 captured by hand, 335 placed; 867 tile pairs found, 713 used,
  170 flagged. Seams RMS 0.85 px, worst 3.48 px, against the stitcher's own target of 0.3 / 1 px. At this scale that
  is 4 µm RMS and 15 µm worst: harmless for reading the board and for tracing (traces are about 200 µm wide).
- **Scale and geometry** (measured on the mosaic, `likely`): the 0.5 mm pad pitch of U1 (all four sides), U7 and J8
  gives 114.25-115.21 px per pitch, **229.4 px/mm** on average, the same to ±0.5 % from the left edge to the right.
  Cross-checks: J29 and JP5 hole pitch 2.53-2.55 mm (2.54 nominal), J8's 30-pin span 14.55 mm (14.5 nominal), U1's
  body 9.02 mm (9 nominal). No sign of drift over the 90 mm board.
- **Magnification:** about 229 px/mm, roughly 5x the 40-50 px/mm planned above. A frame covered about 8.4 x 4.7 mm,
  hence 344 tiles. Every refdes and marking is legible, so the trade worked; for the power board, decide on purpose
  (fewer tiles at a lower magnification, close-ups for markings).
- **Gaps:** 9 tiles found no partner and were left out. They leave 27 small uncovered spots inside the board area,
  11 of them over 0.5 mm²: beside R57/R58/TP28 (8.6 mm², it clips the heat stake by TP29), beside TP8/TP49 (4 mm²),
  right of J8's actuator (3.2 mm²), at Y2 (2.8 mm²), at Y4/C521 and R587/C491 (about 1.9 mm² each), in the right
  antenna zone, between C590 and the centre heat stake, at C432, at C587, right of the right heat stake. The bottom
  antenna zone runs past the coverage. All are re-shoot spots: resume the session there.
- **Featureless areas:** the yellow antenna zones show patchy brightness, tile by tile. Few features to match and a
  different gain per tile; a flat-field or a gain model that holds across a region would help.
- **No ruler frame** in this set: the scale had to come from pad pitches. Put the ruler in the next sets.

## Open questions
- What hung the camera the third time: opening its DirectShow filter, or closing it after a 1080p stream? (above)
- Which UVC controls does it expose, and can exposure and white balance be locked over USB?
- Native photo size on the card, and what the larger sizes add.
- HDMI output resolution, and whether the screen overlays are in it.
- Does the Wi-Fi speak Novatek's HTTP API (`cmd=3002` first), and does `cmd=1001` take a full-resolution photo?
- Is there a USB mass-storage mode for the card?
- The IR remote's codes.
- What, if anything, the USB microphone records.

## Sources
- [M] Andonstar, *Digital Microscope AD409-Pro Users Manual*, Ver 01,
  <https://electrokit.com/upload/quick/1a/a6/873e_AD409-pro_users_manual-Ver_01_1.pdf> (20 pages; SHA-256 of the copy
  read on 2026-11-03: `ae97a7aa4924bd263acfcebb3a8629ee888f29490b9ec21a570becb8e1ad0af6`). The Pro-ES is the same unit
  with the endoscope (`likely`, [E1]).
- [E1] Elektor, *Get Precise with the Andonstar AD409 Digital Microscope*,
  <https://www.elektormagazine.com/review/get-precise-with-the-andonstar-ad409-digital-microscope>
- [E2] Elektor, *Review: Andonstar AD409 Pro(-ES)*, <https://www.elektormagazine.com/review/review-andonstar-ad409-pro>
- [T] Thinkrobotics product page, AD409 Pro-ES: "PC output (endoscope not supported)",
  <https://thinkrobotics.com/products/ad409-pro-es-hdmi-digital-microscope-with-endoscope>
- [D] DashCamTalk forum, *Reverse engineering, Web API, Live feed...etc* (Novatek NT96655 dashcams, user-compiled
  command lists, 2016), <https://dashcamtalk.com/forum/threads/reverse-engineering-web-api-live-feed-etc.21057/>
- Measured: Windows device properties, DirectShow capabilities and OpenCV captures on our unit, 2026-11-03.
