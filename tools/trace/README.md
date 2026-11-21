# trace

Views of a stitched board mosaic for following traces on the top layer. Read-only: it writes PNGs to `.capture/trace/`
(gitignored) and never touches the mosaic. The nets found with it go to [docs/hardware/nets.md](../../docs/hardware/nets.md).

```sh
py -3.13 -m pip install opencv-python numpy pillow   # once
py -3.13 tools/trace/trace.py enhance 2900 9900 4300 11400                      # full resolution, contrast up
py -3.13 tools/trace/trace.py islands 3150 10050 4250 11250 --scale 0.9 --grid 200 --cache
```

The box is `X0 Y0 X1 Y1` in mosaic pixels, the same pixels as `box` in `annotations/crops.json`. The default source is
the main board's component side, `micro/2026-11-03_main_component-side/mosaic.png` (229.4 px/mm), which is local only
([photos.md](../../docs/photos.md)); `--source` picks another mosaic.

## Modes
| Mode | Shows |
|---|---|
| `crop` | the box as it is |
| `enhance` | contrast raised on lightness only (CLAHE): copper under the green mask stands out from bare laminate |
| `islands` | top-layer copper segmented, each connected island in its own colour on a dimmed board |

`islands` relies on colour: copper under the mask reads yellower than bare laminate (CIELAB b* about 150-167 against
about 134). The thresholds were tuned on the 2026-11-03 mosaic under the microscope's ring light. An island breaks
where silkscreen crosses a trace, at pad edges and under chip bodies, so it suggests connections; the full-resolution
view and the multimeter decide them.

## Options
| Option | Default | |
|---|---|---|
| `--scale F` | 1 | output scale; 0.5 for an overview, 1 or more to read a single trace |
| `--grid N` | off | labelled line every N mosaic pixels (229 = 1 mm), to read positions back |
| `--source PNG` | main board, component side | another mosaic |
| `--cache` | off | keeps a raw copy in `.capture/cache/` (about 1.1 GB) so the next views skip the 10 s PNG decode |
| `--out PNG` | `.capture/trace/<mode>_<box>.png` | output file |

## What the top layer can and can't tell
- **Can:** where a trace runs, through which series part, to which pin; pin functions then come from the datasheet.
- **Can't:** anything past a via (the main board is full of ground-stitching vias, so it probably has inner planes),
  routes under chip bodies and connector housings, the LED side, or the value of an unmarked passive. Those come from
  continuity on the unpowered board, a scan of the other side, and in-circuit resistance.
