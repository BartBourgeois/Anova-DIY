# Nets: main board

The wiring of the main board, net by net, as far as it is known: the start of the schematic (roadmap step 1.5). J8's
30 pins get their own page once the first one is measured; every other net is here, one row per net, with the
evidence and a confidence for each connection.

**Sources.** The top layer comes from the stitched mosaic of 2026-11-03 (229.4 px/mm,
[photo log](../photos.md#2026-11-03-microscope-mosaic-main-board-component-side)), viewed with `tools/trace`.
Pin functions come from the datasheets. Positions are in mm from FID1, with the axes of the
[mechanics table](main-board.md#mechanics).

## How far the photos go
Copper under the green solder mask is clearly visible at full resolution: every top-layer trace can be followed from
pin to pin, through series parts, to the next pad or via. That is enough to draw whole blocks where the routing stays on
top. It stops at:
- **vias**: the board is covered in ground-stitching vias, so it probably has an inner ground plane (`guess`), and any
  signal that drops through a via continues out of sight
- **chip bodies and connector housings**: routes under them are hidden
- **silkscreen** printed across a trace: the trace is still there, but a break in it can't be ruled out
- **the LED side**: not photographed yet (the board is heat-staked to the bezel)
- **values**: the 0402 resistors and capacitors are unmarked

Continuity on the unpowered board closes those gaps, and a mosaic of the LED side would show the bottom layer.

## CC3220 (U1) pins used on this page
From TI SWAS035C, table 7-1 (pin descriptions), `confirmed` as datasheet facts. Pin 1 is the first pin of the row
next to the pin-1 dot (top left on the mosaic), counted counter-clockwise. On the mosaic, pin 1's pad sits 0.75 mm
below the body's top edge, and the pitch is 0.5 mm.

| Pin | Name | Dir | Function |
|---|---|---|---|
| 11 | FLASH_SPI_CLK | O | serial flash clock |
| 12 | FLASH_SPI_DOUT | O | serial flash data, CC3220 to flash |
| 13 | FLASH_SPI_DIN | I | serial flash data, flash to CC3220 |
| 14 | FLASH_SPI_CS | O | serial flash chip select |
| 16, 17, 19, 20 | TDI, TDO, TCK, TMS | | JTAG/SWD, disabled in production mode |
| 21 | SOP2 | I | boot-mode strap (2.7 kΩ pull recommended) |
| 32 | nRESET | I | reset, active low |
| 34, 35 | SOP1, SOP0 | I | boot-mode straps (100 kΩ pulls recommended) |

## Nets
| Net | Connections | Evidence | Confidence |
|---|---|---|---|
| FLASH_SPI_CLK | U1.11, series resistor A (top of four), pad P5, then U15 | top-layer trace U1.11 to A; A to P5 | `likely`; U15 pin: to measure (6 expected) |
| FLASH_SPI_DOUT | U1.12, series resistor B, pad P6, then U15 | top layer; the trace passes under a silkscreen logo between B and U1 | `likely`; U15 pin: to measure (5, DI, expected) |
| FLASH_SPI_DIN | U1.13, series resistor C, pad P7, then U15 | top layer, same logo | `likely`; U15 pin: to measure (2, DO, expected) |
| FLASH_SPI_CS | U1.14, series resistor D (bottom of four), pad P8, then U15 | top layer; the P8 trace passes under a silkscreen line | `likely`; U15 pin: to measure (1 expected) |
| GND (assumed) | U15.4, via right beside it | short top-layer stub | `likely` |
| J14 common row | J14 pins 1, 2 and 3, R577 | short top-layer links between the pads; pin 4 is not linked | `likely` |

The four series resistors (0402, black body, no reference designator printed near them) stand in a column between the
bare pads and U1's left edge, about 6.1-6.3 mm right of FID1 and 30.5-32.9 mm down. The order of the traces between
them and U1 is preserved: the top resistor goes to the top pin. The U15 pins "expected" above follow the standard SPI
NOR SOP-8 pinout (1 CS#, 2 DO, 3 WP#, 4 GND, 5 DI, 6 CLK, 7 HOLD#, 8 VCC) and the signal directions in SWAS035C. The
XMC datasheet itself has not been checked.

## Bare round pads P1-P9
Nine mask-free round pads, about 0.9 mm across, sit between U15 and U1. No reference designators are printed for them,
so P1-P9 are this project's names, numbered top to bottom. Pads like these are typical for a bed-of-nails test fixture.
On P5-P8, a fixture could reach the flash bus (`guess`).

| Pad | x mm | y mm | Goes to |
|---|---|---|---|
| P1 | 4.66 | 22.86 | not followed yet (its trace heads for U1's left row) |
| P2 | 6.01 | 24.30 | not followed yet |
| P3 | 4.66 | 25.04 | not followed yet |
| P4 | 5.97 | 25.74 | not followed yet |
| P5 | 4.84 | 28.77 | FLASH_SPI_CLK |
| P6 | 4.79 | 30.32 | FLASH_SPI_DOUT |
| P7 | 4.74 | 31.77 | FLASH_SPI_DIN |
| P8 | 4.23 | 33.06 | FLASH_SPI_CS |
| P9 | 2.90 | 33.83 | not followed yet |

±0.2 mm. In the annotated mosaic they are callout 34, the resistors callout 35
([callouts](callouts/main_component-side_micro.md)).

## Open
- **U15 to P5-P8:** four continuity checks, unpowered. The routes run along U15's right edge and partly under its body.
- **P1-P4 and P9:** follow on the mosaic.
- **J14 pins 5-8:** their traces leave toward vias below the footprint. U1's bottom row (pins 17-21: TDO, GPIO28, TCK,
  TMS, SOP2) also drops to vias within a few mm, around C221. Whether J14 reaches SOP0-2 is a job for the meter
  ([bench setup](bench-setup.md#j14-empty-dip-switch-footprint)).
- **UART0 toward J29** (U1 pins 55/57, UART0 TX/RX in the pin-mux table of SWAS035C) is next on the mosaic.
