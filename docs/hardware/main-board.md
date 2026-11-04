# Main board: `ANOVA_PRO_MAIN_V2.0`

Two sources:
- **raptox's unit** (AN600-20 EU, opened 2026-11-01): a stitched microscope mosaic of the component side
  (2026-11-03, about 229 px/mm, [set details](../photos.md#2026-11-03-microscope-mosaic-main-board-component-side)),
  the reference since then. Callouts: [main_component-side_micro](callouts/main_component-side_micro.md). Earlier: 12 MP
  phone photos plus chip close-ups, callouts [main_component-side_own](callouts/main_component-side_own.md).
  Traced nets (the start of the schematic): [nets.md](nets.md).
- **FCC sample** (2018 pre-production, low-res). Callouts: [component side](callouts/main_component-side.md) · [LED side](callouts/main_led-side.md).

The layout and reference designators match, so raptox's board is the same PCB design (likely `MAIN_V2.0`; the silkscreen
name is on the LED side, not yet photographed). The **production BOM leaves out the debug parts**, see below.

## Component side: raptox's unit

![main board component side, raptox's unit, stitched microscope mosaic](../../images/annotated/main_component-side_micro.png)

Full board at 43 px/mm: [main_component-side_micro_large.jpg](../../images/boards/main_component-side_micro_large.jpg).
At 100 % (229 px/mm): the zoomable [mosaic viewer](../mosaics.md#main-board-component-side-2026-11-03) or the
[lossless PNG](https://github.com/BartBourgeois/Anova-DIY/releases/download/mosaics/2026-11-03_main_component-side_mosaic.png).
The production label's Data Matrix is greyed out in every published image until its content is known.

### Chip markings (confirmed from close-ups unless marked)
| Ref | Marking | Part | Role |
|---|---|---|---|
| **U1** | `CC3220S / M2A / TI 92J / P5KH G4` | **TI CC3220SM2ARGK** (VQFN-64) | Wi-Fi MCU. No internal flash, boots from U15/U16. |
| **U15/U16** | `XMC / QH64AHIG / P1L09000 20 / 1830C` | **XMC XM25QH64AHIG**: 64 Mbit (8 MiB) SPI NOR, **SOP-8 208 mil**, 2.7-3.6 V | CC3220 serial flash: firmware + filesystem. **Dump target.** |
| **U7** | `CC2640 / R2F / TI 931 / A0J3 G4` | **TI CC2640R2F** (VQFN-48 7x7) | BLE MCU, 128 KB internal flash |
| U14 | `T3018 / 3737` | unidentified QFN-40 (~5x5 mm) | central; LED/touch driver or a third MCU? |
| U13 | `4637 / 838A` (or `B38A`; the mosaic corrects the earlier `638A`) | unidentified QFN-20, about 3x3 mm, 0.4 mm pitch | right next to the speaker connector J9: audio driver? |
| U17 | `S9800 / A0J8 / GAJL` (first character S or 5) | unidentified DFN-8, about 3x3 mm | with bulk caps C577/C579 and divider R589/R590: regulator / load switch? |
| U2 | `CG4` (a faint first character may precede it) | **SOT-23, 3 leads** (not SOT-23-5, as read before) | with C586/C4: LDO or supervisor? (guess) |
| Y3 | `T400 / Mc73` | 40 MHz crystal | CC3220 main clock (likely) |
| Y1, Y4? | `TAeAV`, `TA?AV` | 2-pad crystals, about 3.2x1.5 mm | 32.768 kHz for the CC2640R2F (Y1) and the CC3220 (the one below R573; its refdes isn't printed next to it) (guess) |
| Y2 | - | 4-pad crystal | CC2640R2F main clock (guess) |

**Not fitted on this board** (tinned pads only, seen on the mosaic): **U6** (a 5-pad SOT-23-5 footprint beside J8, not
SOT-23-6 as guessed before), C9, C19, R578, besides J14, J29 and JP5. R588 next to them is fitted.

Close-up crops (originals in [images/own/2026-11-01/chips/](../../images/own/2026-11-01/chips/)):

| | |
|---|---|
| ![U1 + U15/U16](../../images/boards/chip_U1-U15_cc3220-flash.jpg) | ![U7](../../images/boards/chip_U7_cc2640r2f.jpg) |
| U15/U16 XMC flash, U1 CC3220S, Y3, J14 footprint | U7 CC2640R2F + test points |
| ![U14](../../images/boards/chip_U14_t3018.jpg) | ![U13 + J9](../../images/boards/chip_U13_J9.jpg) |
| U14 `T3018` | U13 `4637`, TP21-27, J9 speaker, U2 |
| ![U17](../../images/boards/chip_U17.jpg) | ![J29](../../images/boards/chip_J29.jpg) |
| U17 (rotated) | J29 3-hole footprint, TP28/TP29 |

Microscope close-ups (2026-11-03, from the mosaic):

| | |
|---|---|
| ![J8 area](../../images/boards/micro_J8_area.jpg) | ![J8 contact row](../../images/boards/micro_J8_pins.jpg) |
| J8 with TP1/2/3/8/9/49, JP5, U6 (empty), C7, C588 | J8 contact row: `30` at the top, pin-1 circle at the bottom |
| ![U17](../../images/boards/micro_U17.jpg) | ![U13 + J9](../../images/boards/micro_J9_U13_TP21-27.jpg) |
| U17 `S9800 / A0J8 / GAJL` | J9, U13 `4637`, TP21-27 |
| ![U2](../../images/boards/micro_U2.jpg) | ![U7](../../images/boards/micro_U7_TP13-14-42-44_Y1.jpg) |
| U2 `CG4`, 3 leads | U7 CC2640R2F, TP13/14/42/43/44, Y1, FL1 |
| ![J29](../../images/boards/micro_J29_TP28-29.jpg) | ![J37](../../images/boards/micro_J37_TP16-18.jpg) |
| J29, TP28/TP29, the crystal below R573 | J37 with pin numbers, TP16, TP18 |

More: [U14](../../images/boards/micro_U14.jpg), [U1/U15/Y3/J14](../../images/boards/micro_U1_U15_Y3_J14.jpg),
[Y2](../../images/boards/micro_Y2.jpg), [TP15/34-37](../../images/boards/micro_TP15_TP34-37.jpg),
[TP45-48](../../images/boards/micro_TP45-48_pad.jpg), [Q3/TP50](../../images/boards/micro_Q3_TP50.jpg),
[label](../../images/boards/micro_label.jpg).

### Production unit vs FCC sample
| Item | FCC sample (2018) | raptox's unit | Consequence |
|---|---|---|---|
| **J14** DIP switch (4-way) | fitted (orange) | **empty footprint** | If J14 is confirmed as the SOP straps, a switch or wires on the pads change them |
| **J29** header (1x3, 2.54 mm) | fitted | **empty holes** | Solder a 3-pin header for UART access |
| Spring contacts (3x) | fitted | **bare copper pads** | probably not needed in production |
| "2.0.2" sticker | yes | no | |
| Chip date codes | flash ?, CC2640 `813` | flash `1830`, CC3220 `92J`, CC2640 `931` | built around 2019 (likely, from the TI date codes) |

### Debug / programming candidates
| Ref | What | Hypothesis | How to confirm |
|---|---|---|---|
| **J29** | 1x3 holes at 2.54 mm, `3` printed at one end, a dot at the other (pin 1), with TP28/TP29 and R573/R579/R580 | **CC3220 UART0** (TX/RX/GND), used by UARTLOAD/Uniflash | continuity to the U1 UART pins; scope at power-up |
| **J14** | 4-way DIP footprint near R533/R535/R577; `DIP`, pins 1/4/5/8 and an `ON` mark printed. On the top layer pins 1-3 are linked to each other and to R577, pin 4 is not; pins 5-8 lead off to vias ([nets](nets.md)) | **CC3220 SOP0/1/2** straps (+ nRESET?) | continuity to the U1 SOP pins |
| P1-P9 (our names) | 9 bare round pads between U15 and U1, no refdes printed. P5-P8 sit on the flash bus, on the flash side of four 0402 series resistors | test-fixture access to the flash bus (guess) | continuity to the U15 pins ([nets](nets.md)) |
| **J37** | Tag-Connect TC2030 (6 pads + 3 holes), pins 1/2/5/6 printed, TP16/TP18 beside it | JTAG/SWD (CC3220) or cJTAG (CC2640R2F) | continuity; J38 on the LED side is its twin |
| TP13/14/42/43/44 | test points beside U7 | CC2640R2F cJTAG / reset / UART | continuity to U7 pins |
| TP15, TP34-37 | boxed group with R17-R21, R585, C101 | production test / programming | continuity |
| TP21-27 | around U13 | U13 signals | |
| TP45-48 | under an exposed copper pad | ? | |

### Connectors
- **J8**: 30-pin 0.5 mm FPC to the power board, flip actuator. `30` is printed at one end of the contact row and a
  circle at the other, so pin 1 is the circle end (`likely`; the circle sits right beside the end pin). The pin-1 end
  has the bulk cap C588 and C7 next to it, and pins 1-6 share one copper pour on the top layer, so that end is a
  supply/ground group (`likely` from the copper; which rail is for the multimeter). Test points around it: TP1, TP2,
  TP3, TP8, TP9, TP49. Pinout work: the J8 campaign (`j8.md` from the first measured row).
- **J9**: 2-pin, **speaker** (confirmed: twisted yellow/black pair to a round speaker labelled `20 / 219` in the housing).
- **JP5**: 2 empty holes at 2.54 mm, pin 1 square, pin 2 round with thermal spokes, between two copper pours beside
  J8's pins 1-12. A power jumper or a supply-injection header (guess): if it carries the J8 input rail, it is the
  natural place to feed the board from a bench supply.

### Mechanics
- The board is **heat-staked** to the white bezel (6 melted posts) and located by two more bezel pins in plated holes.
  Everything needed for Phase 1-3 is on this side, so there is no need to remove it.
- Two yellow antenna zones (on the mosaic: the right edge and the bottom). The CC3220 RF path probably goes via FL2
  near U1 (guess).
- No mounting holes for screws on the board itself: the three round pads in the corners are **fiducials** (a 1 mm
  copper dot in a mask-free disc, `likely`).

**Positions** (measured on the 2026-11-03 mosaic at 229.4 px/mm, `likely`, about ±0.5 % plus ±0.05 mm; the stage-6
spec for a board of our own). Origin = centre of FID1, x to the right and y down in the mosaic's orientation (U1 bottom
left, U7 top right, J8 upright right of centre). The mosaic axes follow the parts (U1's pad rows are level, J8's row is
vertical); the fiducials are not level, FID2 sits 2 mm higher than FID1.

| Feature | x mm | y mm | Note |
|---|---|---|---|
| FID1 (top left) | 0.00 | 0.00 | origin |
| FID2 (top right) | 78.77 | -1.98 | |
| FID3 (bottom right) | 67.31 | 51.42 | |
| Locating pin, top | 13.16 | -8.96 | white bezel pin in a plated hole, about 1.9 mm visible |
| Locating pin, bottom right (beside J8) | 61.24 | 43.71 | same, about 2.1 mm |
| Heat stake 1 (by J29/TP29) | 19.1 | 11.4 | partly in a stitching gap, ±0.2 mm |
| Heat stake 2 (top centre) | 42.33 | 9.52 | melted tops about 2.9 mm across |
| Heat stake 3 (right of J8) | 61.70 | 11.34 | |
| Heat stake 4 (bottom left) | 24.26 | 38.49 | |
| Heat stake 5 (bottom centre, by JP5) | 42.18 | 35.84 | |
| Heat stake 6 (bottom right, by Q3) | 69.24 | 42.14 | |
| J29 holes 3 / 2 / 1 | 12.28 / 12.27 / 12.23 | 10.55 / 13.09 / 15.62 | pitch 2.54; drill about 1.2 mm visible |
| JP5 holes 2 / 1 | 48.33 / 48.30 | 34.77 / 37.32 | pitch 2.55; pin 1 square |
| J8 contact tails, pin 30 / pin 1 | 53.18 | 24.70 / 39.25 | 0.5 mm pitch; tails at the left, actuator at the right |
| U1 centre | 13.14 | 28.45 | |
| U7 centre | 48.89 | -2.27 | |
| Board extent (green area) | -4.3 to 85.6 | -12.1 to 54.1 | about 90 x 66 mm; the bottom edge runs past the mosaic in places, so check with calipers |

The full-board image [main_component-side_micro_large.jpg](../../images/boards/main_component-side_micro_large.jpg)
is 43.3 px/mm (229.4 x 4000 / 21200); FID1 is at pixel (236, 586) in it. Scale it by that to use it as a KiCad
image underlay.

## LED / touch side (FCC sample only so far)

![main board LED side, FCC filing](../../images/annotated/main_led-side.png)

*Source: FCC ID 2APBOAN600, internal-photos exhibit 3999178 (2018 sample).*

The display is built from **discrete SMD LEDs** (about D1-D135) behind a white light guide, not an LCD.

The key mapping below comes from overlaying this side on the (mirrored) bezel photo. It is `likely`:

| Touch key (LED) | Bezel icon | Function (per manual) |
|---|---|---|
| D5 | thermometer | target temperature |
| D6 | filled circle | ? |
| D33 | clock | timer |
| D4 | + | increase |
| D3 + D32 | triangle + bar | start / stop |
| D1 | - | decrease |

- Digit rows (D38-D135 approx.): 3 rows x 4 seven-segment digits.
- **D8**: Wi-Fi status LED (likely). **U18**: optical sensor behind the rectangular window (guess).
- **J38**: Tag-Connect footprint, back-to-back with J37.
- Two copper-free zones with 2 domed gold pins each (one is J36). They contact the two black strips on the bezel (antenna elements? guess).

## Open questions
- [ ] Map J29, J14 (pads), J37 and the TP groups to U1/U7 pins (continuity, board unpowered).
- [ ] Identify U14 (`T3018`), U13 (`4637`), U17 (`S9800`). Which chip drives the LEDs, touch keys and speaker?
- [ ] Interconnect between the CC3220S and CC2640R2F (UART? SPI?).
- [ ] J8 FPC pinout and rails.
- [ ] Confirm the `MAIN_V2.0` silkscreen on raptox's board (LED side, not photographed).
