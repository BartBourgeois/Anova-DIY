# Component list (running BOM)

Confidence: **confirmed** = marking legible or measured · **likely** = strong visual/contextual evidence · **guess** = hypothesis.
Sources: "FCC" = FCC 2APBOAN600 internal photos (2018 sample). "Own" = raptox's unit, photos of 2026-11-01
(`images/own/2026-11-01/`, markings read from the `chips/` close-ups). "Mosaic" = the stitched microscope mosaic of
2026-11-03 (about 229 px/mm, [photos.md](../photos.md#2026-11-03-microscope-mosaic-main-board-component-side)).
Update this table whenever an annotation changes.

## Main board `ANOVA_PRO_MAIN_V2.0`
Markings below are from raptox's unit. FCC-sample markings are given where they differ.

| Ref | Marking | Identified as | Function | Confidence | Source / datasheet |
|---|---|---|---|---|---|
| U1 | `CC3220S / M2A / TI 92J / P5KH G4` (FCC: `TI ?CJ / PEH3 G4`) | TI **CC3220SM2ARGK** (VQFN-64 9x9) | Wi-Fi MCU (Cortex-M4 app + NWP), boots from external SPI flash | confirmed | Own; [TI CC3220 datasheet SWAS035](https://www.ti.com/lit/ds/symlink/cc3220sf.pdf) |
| U15/U16 | `XMC / QH64AHIG / P1L09000 20 / 1830C` | **XMC XM25QH64AHIG**: 64 Mbit (8 MiB) SPI NOR, SOP-8 **208 mil**, 2.7-3.6 V, JEDEC ID `20 70 17` | CC3220 serial flash (firmware + filesystem) | confirmed | Own; [Elnec device page](https://www.elnec.com/en/device/XMC/XM25QH64A%20[SOP8-208]%20(QuadSPI)), [Linux spi-nor patch (ID)](https://lists.infradead.org/pipermail/linux-mtd/2018-April/080447.html) |
| U7 | `CC2640 / R2F / TI 931 / A0J3 G4` (FCC: `TI 813 / P305 G4`) | TI **CC2640R2F** (VQFN-48 7x7, RGZ) | BLE 4.2 MCU, 128 KB flash | confirmed | Own; [TI CC2640R2F datasheet SWRS204](https://www.ti.com/lit/ds/symlink/cc2640r2f.pdf) |
| U14 | `T3018 / 3737` | **Lumissil IS31FL3737**: 12x12 LED matrix driver (144 LEDs, 8-bit PWM each), I2C, QFN-40 5x5, 0.4 mm pitch | drives the panel's LEDs (about 135): the CC3220 talks to it at I2C address 0x50 (ADDR to GND) with this family's unlock-and-page-select sequence; the touch keys are U7's | confirmed (marking `3737`, package, address and register layout); original or B revision open | Mosaic; [IS31FL3737 datasheet](https://www.lumissil.com/assets/pdf/core/IS31FL3737_DS.pdf) p3, p4, p9, p15; [callouts](callouts/micro_U14.md). Not the IS31FL3018 (QFN-32 per its datasheet, unverified). |
| U13 | `4637 / 838A` (or `B38A`; was read `638A`) | **AKM AK4637EN**: 24-bit mono audio codec with MIC amp and speaker amp (BTL, 400 mW into 8 Ω at 3.3 V, 1 W at 5 V), 20-pin QFN 3x3, 0.4 mm pitch | the cooker's sound: U1 sends the WAV sounds over I2S and controls it over I2C (address 0x12); speaker outputs (pins 13/14) toward J9 | confirmed (marking, against AKM's marking diagram) / likely (how it is wired) | Mosaic; [AKM AK4637 datasheet](https://www.akm.com/content/dam/documents/products/audio/audio-codec/ak4637en/ak4637en-en-datasheet.pdf) p6, p9, p94; [callouts](callouts/micro_J9_U13_TP21-27.md) |
| U17 | `59800 / ADJB / GAJL` (was read `S9800 / A0J8`) | **onsemi NCP59800** (adjustable, `ADJB`): 1 A low-noise LDO, DFN8 3x3, input 2.2-6.0 V (abs. max 6.5 V) | 3.3 V logic rail (C577 in, C579 out, C604 NR, R589/R590 FB) | confirmed (marking against onsemi's diagram line by line, package, pinout against the copper) / likely (3.3 V: the divider is unmeasured) | Mosaic; onsemi NCP59800/D Rev. 3 ([references](../references.md#power)); [callouts](callouts/micro_U17.md) |
| U2 | `CG4` (a faint first character may precede it) | SOT-23, **3 leads** | LDO or supervisor? (C586, C4) | likely (package) / guess (function) | Mosaic |
| U6 | - | 5-pad SOT-23-5 footprint, **not fitted** on raptox's unit | unfitted regulator? (`guess`: pad 1 on VIN, pad 2 on GND) | confirmed (empty) | Mosaic |
| C9, C19, R578 | - | small footprints beside U6, **not fitted** | ? | confirmed (empty) | Mosaic |
| C588, C7 | - | MLCCs, 1210 and 0805, on the J8 pins 1-6 pour | J8 supply decoupling (C7 to GND seen; C588's other pad not resolved) | likely | Mosaic ([nets](nets.md#supply)) |
| Y3 | `T400 / Mc73` | 40 MHz crystal | CC3220 main clock | likely | Own, mosaic |
| Y1 | `TAeAV` | 2-pad crystal, ~3.2x1.5 mm | CC2640R2F 32.768 kHz? | guess | Mosaic |
| Y4? | `TA?AV` | 2-pad crystal below R573, ~3.2x1.5 mm (refdes not printed beside it) | CC3220 32.768 kHz RTC? | guess | Mosaic |
| Y2 | - | 4-pad crystal | CC2640R2F main clock (24 MHz?) | guess | Mosaic |
| FL1 | - | 6-pad ceramic part, pin 3 dotted | CC2640R2F balun / filter? | likely | Mosaic |
| FL2 | - | RF filter / balun | CC3220 RF path | guess | Own |
| L381, L401, L431 | - | power inductors | CC3220 internal DC/DC converters | likely | Own |
| U18 | - | dual-element optical sensor | proximity / ambient light? | guess | FCC p3 |
| J8 | - | 30-pin 0.5 mm FPC with flip actuator (30-pin span measured 14.55 mm on the mosaic: 0.5 mm pitch) | to power board J8; `30` printed at one end, pin-1 circle at the other | confirmed | FCC p1-p3, own, mosaic |
| J9 | - | 2-pin JST-style | **speaker** (twisted yellow/black pair, speaker labelled `20 / 219`) | confirmed | Own |
| J14 | - | 4-way SMD DIP switch, **fitted on FCC sample only** (empty footprint on production unit) | CC3220 SOP straps? Positions 1-3 wired, 4 unused | confirmed (part) / likely (function) | FCC p2, own, meter |
| R567, R341, R566 | - | three 0402 resistors in stacked frames beside X4-X6 (called "the C231 box" until ) | the SOP straps' pull-downs: 100 kΩ, 100 kΩ, 2.68 kΩ to GND measured at X4-X6 | likely (names: legend) | Mosaic |
| C231, C241, C251 | - | 0402 capacitors right of Y3: C231 upright below, C241 and C251 above it | ? (raptox's meter found a cap to GND on each strap pad; not traced to these) | likely (named by raptox at the bench) | Mosaic |
| - (4x, no refdes printed) | - | 0402 resistors (black body), in a column left of U1 | series resistors on the flash bus, U1 pins 11-14 | likely | Mosaic, [nets](nets.md) |
| P1-P9 (our names) | - | bare round pads, about 0.9 mm, no refdes printed | test pads; P5-P8 on the flash bus | likely (P5-P8) / guess (rest) | Mosaic, [nets](nets.md) |
| J29 | - | 1x3 2.54 mm header, **fitted on FCC sample only** (empty holes on production unit) | the U1-U7 serial link, both directions (hole 1 U1 RX / U7 TX, hole 2 U1 TX / U7 RX, hole 3 GND); also U1's boot-loader port | confirmed (part; function by use) | FCC p2, own |
| J37, J38 | - | Tag-Connect TC2030-style 6-pad + 3 holes, back-to-back | JTAG/SWD/cJTAG? | likely | FCC p2, p3, own |
| JP5 | - | 2 TH pads at 2.54 mm, empty; pin 1 square, pin 2 with thermal spokes | power header: pin 1 = J8 pins 1-6 = U17 input (about 5 V), pin 2 = GND ([j8](j8.md)) | confirmed (wiring) | FCC p2, own, mosaic |
| FID1-FID3 | - | fiducials (1 mm copper dot, mask-free disc), three corners | assembly reference; origin of the mechanics table | likely | Mosaic |
| J36 + unlabeled | - | 2x2 domed gold pins in antenna zones | antenna feed / bezel contacts? | guess | FCC p3 |
| D1, D3, D4, D5, D6, D32, D33 | - | SMD LEDs in touch keys | key backlight | likely | FCC p3 |
| D8 | - | SMD LED | Wi-Fi indicator | likely | FCC p2-p3 |
| about D38-D135 | - | SMD LEDs | 3 x 4 seven-segment digits | likely | FCC p3 |
| Q3, TP50 | - | Q3: an empty SOT-23 footprint on raptox's unit; TP50 beside it | discrete circuit, unpopulated here | confirmed (Q3 empty) | FCC p2, own, mosaic |
| R559, R591-R594, C606, C607 | - | 0402-size footprints of the Q3 circuit, two bare pads each, **not fitted** on raptox's unit | ? | confirmed (empty) | Mosaic |
| C605 | - | big two-pad footprint of the Q3 circuit, 4.1 x 2.7 mm over both pads (1812 or tantalum size), tinned, **not fitted** | ? | confirmed (empty) | Mosaic |
| C601 | - | big two-pad footprint, 4.1 x 1.7 mm over both pads, tinned, **not fitted** | ? | confirmed (empty) | Mosaic |
| C36, C37, C595, C596, C597 | - | 0402-size footprints, two bare pads each, **not fitted** (C36/C37 above Y2, C595/C596 beside R571) | ? | confirmed (empty) | Mosaic |
| - | label `004D2 / 90718PM` + Data Matrix | production label; the Data Matrix is greyed out in published images | | confirmed | Own, mosaic |

## Power board `ANOVA_PRO_POWER_REV01`
| Ref | Marking | Identified as | Function | Confidence | Source |
|---|---|---|---|---|---|
| (module) | - | AC/DC flyback daughterboard | isolated LV supply | likely | FCC p3 |
| F1 | silkscreen `T2A/250V` | fuse | AC/DC input protection | confirmed | FCC p3 |
| - | - | cartridge fuse in clips | main/heater fuse | confirmed | FCC p3 |
| - | - | PCB power relay (black) | heater switching | likely | FCC p3 |
| - | - | grey box | 2nd relay or film cap | guess | FCC p3 |
| C25 | - | film capacitor | X2 / filtering | likely | FCC p3 |
| L1 | `6R8` / `1822` | 6.8 uH shielded inductor | DC/DC buck | confirmed | FCC p3 |
| U2 | illegible | IC, pins on two sides | MCU? DC/DC? AFE? | guess | FCC p3 |
| U3? | illegible | TSSOP/QFN IC | ? | guess | FCC p3 |
| U10 | illegible | TSSOP-16 class | driver / sensing? | guess | FCC p3 |
| U11, U5 | illegible | small IC | ? | guess | FCC p3 |
| (SOP-6) | illegible | 6-lead SOP + 20 R / 51 R | HV regulator / driver? | guess | FCC p3 |
| J8 | - | 30-pin FPC | to main board | confirmed | FCC p3 |
| J12, J15, J19 | - | wire-to-board connectors | sensors / motor? | confirmed (part) | FCC p3 |
| J23, J24, J25, J28, J30 | - | 2-pad wire terminals | heater/pump/TCO? | likely | FCC p3 |
| R57 | - | footprint at finger tip | temperature sensor? | guess | FCC p3 |
