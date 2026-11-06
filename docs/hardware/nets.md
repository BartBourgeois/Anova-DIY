# Nets: main board

The wiring of the main board, net by net, as far as it is known: the start of the schematic (roadmap step 1.5). J8's
30 pins have their own page, [j8.md](j8.md); every other net is here, one row per net, with the
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
next to the pin-1 dot (top left on the mosaic), counted counter-clockwise. The datasheet's figure 7-1 draws the same
chip with the mark at the bottom left: turn it a quarter clockwise to match the mosaic, so its bottom edge (pins 1-16)
becomes U1's left side. On the mosaic, pin 1's pad sits 0.75 mm
below the body's top edge, and the pitch is 0.5 mm.

| Pin | Name | Dir | Function |
|---|---|---|---|
| 11 | FLASH_SPI_CLK | O | serial flash clock |
| 12 | FLASH_SPI_DOUT | O | serial flash data, CC3220 to flash |
| 13 | FLASH_SPI_DIN | I | serial flash data, flash to CC3220 |
| 14 | FLASH_SPI_CS | O | serial flash chip select |
| 5, 6, 7, 8 | GPIO14, GPIO15, GPIO16, GPIO17 | I/O | general purpose. Muxable as the GSPI port (CLK, MISO, MOSI, CS); 14/15 also I2C_SCL/SDA, 16/17 also UART1_TX/RX (pages 15, 24) |
| 16, 17, 19, 20 | TDI, TDO, TCK, TMS | | JTAG/SWD at reset, disabled in production mode. Pin 16 can be muxed as GPIO23, UART1_TX or I2C_SCL; pin 17 as GPIO24, UART1_RX, PWM0, I2C_SDA, GT_CCP06 or McAFSX (pages 15, 24) |
| 21 | SOP2 | I | boot-mode strap (2.7 kΩ pull recommended) |
| 32 | nRESET | I | reset, active low |
| 34, 35 | SOP1, SOP0 | I | boot-mode straps (100 kΩ pulls recommended) |
| 55 | GPIO1 | I/O | muxable as UART0_TX or UART1_TX (pages 13, 17). UART0_TX can also sit on pins 3, 53, 62 (page 23) |
| 57 | GPIO2 | I/O | muxable as UART0_RX; UART0_RX can also sit on pins 4, 45 (page 23) |

## U17 (onsemi NCP59800) pins
From onsemi NCP59800/D rev. 2, pin function table and pin connections (top view), `confirmed` as datasheet facts.
U17's marking `59800 / ADJB` is the datasheet's marking for the adjustable version (NCP59800BMNADJT*G). On the mosaic
the dot sits at the end of the pad row that faces away from C604, and the board fits the pinout: the NR pad has its
small cap, the FB pad its divider, the IN pads the bulk cap and the vias.

| Pin | Name | On the board (top layer) |
|---|---|---|
| 1, 2 | OUT | the large pour below U17 (as the mosaic is oriented); C579 |
| 3 | FB | toward the divider R589/R590 |
| 4, exposed pad | GND | |
| 5 | EN | short stub, not followed yet |
| 6 | NR | C604 (0402) |
| 7, 8 | IN | the pour above U17, with C577 and three vias down to an inner layer |

Output: VOUT = 0.8 V × (1 + R1/R2), R1 from OUT to FB, R2 from FB to GND; for 3.3 V the datasheet's table lists
R1 = 30.9 kΩ, R2 = 10.0 kΩ. Input: 2.2 to 6.0 V, at least VOUT + 0.5 V at 1 A (dropout max 500 mV); absolute maximum
6.5 V on IN, and OUT no higher than VIN + 0.3 V.

## Nets
| Net | Connections | Evidence | Confidence |
|---|---|---|---|
| FLASH_SPI_CLK | U1.11, series resistor A (top of four), pad P5, then U15 | top-layer trace U1.11 to A; A to P5 | `confirmed` U1.11 to P5 (beeper); `likely` (the resistor); U15 pin 6 (CLK): `confirmed`, beeper to P5 |
| FLASH_SPI_DOUT | U1.12, series resistor B, pad P6, then U15 | top layer; the trace passes under a silkscreen logo between B and U1 | `confirmed` U1.12 to P6 (beeper); `likely` (the resistor); U15 pin 5 (DI): `confirmed`, beeper to P6 |
| FLASH_SPI_DIN | U1.13, series resistor C, pad P7, then U15 | top layer, same logo | `confirmed` U1.13 to P7 (beeper); `likely` (the resistor); U15 pin 2 (DO): `confirmed`, beeper to P7 |
| FLASH_SPI_CS | U1.14, series resistor D (bottom of four), pad P8, then U15 | top layer; the P8 trace passes under a silkscreen line | `confirmed` U1.14 to P8 (beeper); `likely` (the resistor); U15 pin 1 (CS#): `confirmed`, beeper to P8 |
| GND | U15.4, via right beside it | short top-layer stub; U15 pin 4 to JP5 pin 2, beeper | `confirmed` |
| J14 common row | J14 pins 1, 2 and 3, R577 (right end); **270 Ω to 3V3** (U15.8) | short top-layer links between the pads; pin 4 is not linked. Beeper, pins 1-3 one net (raptox, 2026-11-05). J14.1 to U15.8: 270 Ω; to JP5.1 (VIN): 161 kΩ / 0.3 MΩ by polarity, so not on 5 V | `confirmed` (pins 1-3; 270 Ω to 3V3); `likely` (R577 is the 270 Ω) |
| SOP0 (J14 strap, position 1) | U1.35, pad X4, J14 pin 8, the top part of the C231 box (its other end on GND); **100 kΩ to GND** | X4 to U1.35: beeper (raptox, 2026-11-05). 100 kΩ pad to GND. Pin 8 to an X pad and the cap to GND: beeper; pin 8 to X4: top-layer trace at full resolution | `confirmed` (X4 to U1.35, the 100 kΩ; J14 pin 8 to an X pad); `likely` (pin 8 to X4) |
| SOP1 (J14 strap, position 2) | U1.34, pad X5, J14 pin 7, the middle part of the C231 box; **100 kΩ to GND** | X5 to U1.34: beeper; 100 kΩ; the rest as above | `confirmed` (X5 to U1.34, the 100 kΩ); `likely` (pin 7 to X5) |
| SOP2 (J14 strap, position 3) | U1.21, pad X6, J14 pin 6, the bottom part of the C231 box; **2.68 kΩ to GND** | X6 to U1.21: beeper; 2.68 kΩ; the rest as above | `confirmed` (X6 to U1.21, the 2.68 kΩ); `likely` (pin 6 to X6) |
| nRESET (U1) | U1.32 (the bottom edge's last pin on the right), a top-layer trace from U1's bottom-right corner down past C331, C322 and R321, to **TP33** | traced on the mosaic and beeper U1.32 to TP33 (raptox, 2026-11-06); R321 and C322's left pads beep to TP33; TP33 to U15.8 (3V3) **9.7 kΩ both polarities** | `confirmed` (U1.32, TP33, R321, C322 on the net; the 9.7 kΩ; **R321's other pad on 3V3**, U15.8: the pull-up); `likely`: R321 = 10 kΩ, C322 the filter cap to GND, nothing drives the net. Held to GND for the clip read: 0.34 mA |
| J37 pin 2 (our name) | J37 pin 2, TP18 | beeper (raptox, 2026-11-05) | `confirmed`; its function (SWDIO/TMS or TMSC, by the usual Tag-Connect pinout) `guess` |
| J14 position 4 | J14 pins 4 and 5: nothing | no top-layer trace; no connection found (raptox) | `likely` (unused) |
| VIN_J8 (our name; about 5 V expected, see [Supply](#supply)) | J8 pins 1-6, JP5 pin 1, TP1, C7 (0805) and C588 (1210), the pads nearer J8; pad 1 of the empty U6 (TP1's strip) | J8 pins 1-6 to JP5 pin 1: continuity through break-out A, 2026-11-04. TP1 to JP5 pin 1: beeper, 2026-11-05. The caps: one top-layer pour; pin 6's contact tail is the last one inside it, pin 7's sits on bare laminate | `confirmed` (J8 1-6, JP5 1, U17 IN via C577's pad: ; TP1: ); `likely` (C7, C588, U6 pad 1) |
| GND (J8 end) | C7's other pad, the via-stitched pour around J8's right and bottom end | top layer. This pour isn't joined to the board-edge pour on the top layer; both are via-stitched | `likely` |
| GND (JP5 pin 2 net) | JP5 pin 2, pad 2 of the empty U6 footprint (SOT-23-5), a via-stitched strip that runs up past U6; J8 pins 10, 11, 17, 19, 22, 23, 30; TP2, TP3, TP4, TP7, TP8, TP9 | the island map (U6, strip); continuity through break-out A (J8 pins, 2026-11-04); the TPs to JP5 pin 2, beeper (2026-11-05) | `likely` (U6, strip); `confirmed` (J8 pins; JP5 pin 2 to U15 pin 4; the TPs/) |
| U17 IN | U17 pins 7-8, C577, three vias | top layer, NCP59800 pinout | `likely` (pins); fed from VIN_J8: `confirmed` (continuity JP5 pin 1 to C577's pad) |
| 3V3 (U17 OUT) | U17 pins 1-2, C579, the pour below U17 | top layer, NCP59800 pinout | `likely`. That it feeds U15 pin 8 and U1's VBAT pins: to measure |
| U17 NR | U17 pin 6, C604 | short top-layer trace | `likely` |
| U17 FB | U17 pin 3, R589/R590 | top layer | `likely`; which resistor is R1: to measure |

The four series resistors (0402, black body, no reference designator printed near them) stand in a column between the
bare pads and U1's left edge, about 6.1-6.3 mm right of FID1 and 30.5-32.9 mm down. The order of the traces between
them and U1 is preserved: the top resistor goes to the top pin. The U15 pins "expected" above follow the XM25QH64A's
SOP-8 pinout (1 CS#, 2 DO, 3 WP#, 4 VSS, 5 DI, 6 CLK, 7 HOLD#/RESET#, 8 VCC; XMC datasheet rev. J, figure 1, `confirmed`
as datasheet facts) and the signal directions in SWAS035C. The
XMC datasheet itself has not been checked.

## Bare round pads P1-P9
Nine mask-free round pads, about 0.9 mm across, sit between U15 and U1. No reference designators are printed for them,
so P1-P9 are this project's names, numbered top to bottom. Pads like these are typical for a bed-of-nails test fixture.
On P5-P8, a fixture could reach the flash bus (`guess`).

| Pad | x mm | y mm | Goes to |
|---|---|---|---|
| P1 | 4.66 | 22.86 | U1 pin 6, **GPIO15** (GSPI_MISO / I2C_SDA), beeper |
| P2 | 6.01 | 24.30 | U1 pin 5, **GPIO14** (GSPI_CLK / I2C_SCL), beeper |
| P3 | 4.66 | 25.04 | U1 pin 8, **GPIO17** (GSPI_CS / UART1_RX), beeper |
| P4 | 5.97 | 25.74 | U1 pin 7, **GPIO16** (GSPI_MOSI / UART1_TX), beeper |
| P5 | 4.84 | 28.77 | FLASH_SPI_CLK, U1 pin 11 (beeper) |
| P6 | 4.79 | 30.32 | FLASH_SPI_DOUT, U1 pin 12 (beeper) |
| P7 | 4.74 | 31.77 | FLASH_SPI_DIN, U1 pin 13 (beeper) |
| P8 | 4.23 | 33.06 | FLASH_SPI_CS, U1 pin 14 (beeper) |
| P9 | 2.90 | 33.83 | **U1 pin 16, TDI** (muxable as GPIO23 / UART1_TX / I2C_SCL): rings to the bottom pin of U1's left row, pin 16 by SWAS035C figure 7-1 (raptox, `confirmed`). On the top layer its one trace runs toward J14 and is lost under J14's outline, so the join is on another layer |

±0.2 mm. In the annotated mosaic they are callout 34, the resistors callout 35
([callouts](callouts/main_component-side_micro.md)).

## Supply
What the main board runs on, reasoned from the chips (2026-11-04). **Measured since:** the power board
delivers **5.01 V on J8 pins 1-6** against pin 30, with the main board unplugged (2026-11-04, [J8](j8.md)).
The 3.3 V rail isn't measured yet. **Unpowered, the 3.3 V rail reads about 24 kΩ to GND with the meter's red lead on
GND and about 42 kΩ the other way** (from J14 pin 1, so through R577's 270 Ω; `likely` for the rail itself,
the direct U15 pin 8 to pin 4 reading would make it `confirmed`): semiconductors in the path, and no short on the rail.

- **Logic rail: 3.3 V** (`likely`). The CC3220 runs from 2.1 to 3.6 V, 3.3 V typical (SWAS035C section 8.4). The flash
  XM25QH64A runs from 2.7 to 3.6 V. They share the SPI lines directly, so they share a rail. The CC2640R2F
  accepts 1.8-3.8 V (TI datasheet, unverified here). U17 is the regulator that fits: an adjustable 1 A low-noise LDO,
  and the CC3220 alone draws up to 272 mA transmitting and 450 mA during calibration at 3.3 V (SWAS035C section 8.5).
- **J8 supply: about 5 V** (`likely` when written; **5.01 V measured**, `confirmed`), on **pins 1-6**. U17
  needs 3.8-6.0 V at its input for a 3.3 V output, and
  6.5 V is its absolute maximum. The component side has no switching regulator: its only inductors are L381/L401/L431,
  for the CC3220's internal DC/DC converters. The LED side shows none in the FCC photo either. So whatever arrives on J8
  reaches U17 through linear parts at most. The one other candidate, U2 (SOT-23, 3 leads), couldn't drop 12 V to 5 V
  at Wi-Fi currents: that would be about 2-3 W in a SOT-23 (`guess`). 12 V on J8 is therefore out, and 5 V is the
  usual choice. The power board's buck (L1, 6.8 µH) is the natural source (`guess`).
- **Why pins 1-6:** six contacts on one pour carry the current, the bulk cap C588 and C7 sit on that pour, and C7's
  other pad is on the via-stitched ground pour. A ground pin wouldn't need a cap to ground.
- **GND on J8:** not visible on the top layer. The candidates are the pins with no visible copper (7, 9-12, and 18, 20,
  22?, 24, 30 from the (private planning notes, not published)). They most likely
  drop to the ground plane under the connector body (`guess`).
- **JP5** (2.54 mm, empty): pin 1 on the J8 supply, pin 2 probably GND. It looks like a power header for feeding the
  board without the power board, on a test fixture or on the bench (`guess`).

Done: J8 pins 1-6 to JP5 pin 1; checks 1 and 2 below, and no short between JP5's pins. All
`confirmed`, pin by pin in [j8.md](j8.md).
Four unpowered checks settle the rest, and they also tell the bench what it may feed:
1. ~~J8 pin 1 (or JP5 pin 1) to U17 pin 7/8 (C577's pad)~~: 0 Ω, so J8 feeds U17 directly.
2. ~~JP5 pin 2 to U15 pin 4~~: 0 Ω, so JP5 is a power header: pin 1 supply, pin 2 GND.
3. R589 and R590 in circuit: their ratio gives U17's output voltage.
4. ~~U17 pin 1/2 (C579's pad) to U15 pin 8~~: beep, so U17 makes the flash's rail.

Nothing above 6 V goes anywhere near J8 pins 1-6 or JP5.

## Open
- **The supply checks** above, then the measured J8 voltage (J8 campaign step 5).
- **U2** (`CG4`, SOT-23, 3 leads): its single-lead pad sits on a separate pour with a 2x2 via cluster and C584. The
  layout looks like a 3-pin LDO with that lead as the input (`guess`); a supervisor is still possible.
- **U15 to P5-P8:** all four done: the flash bus is measured from end to end.
- **U15's other pins, before the dump**. Only pin 7 decides the read: HOLD# (or RESET#) low stalls it. WP#
  on pin 3 only guards the status register (XM25QH64A datasheet, page 5). Unpowered, on U15's legs:
  1. pin 8 (VCC) to U17 pin 1 or 2 (OUT): a beep puts the flash on the 3.3 V rail
  2. pin 7 to pin 8: a beep means tied straight to VCC. No beep: ohms, both lead polarities. The same few kΩ to
     100 kΩ both ways is a pull-up resistor; a reading that changes with polarity is a chip's protection diode,
     not a resistor
  3. pin 7 to pin 4 (GND): should be open. A low value here means something pulls HOLD# down, which the dump would
     have to override
  4. pin 3 to pin 8 and to pin 4, the same way (for later writes, not the dump)

  If pin 7 is open to both, something else drives it (a CC3220 GPIO?): follow its trace.

  **Measured:** pin 8 rings to U17 OUT. Pin 7 reads 9.9 kΩ to pin 8 and open to pin 4: a pull-up of about
  10 kΩ (`likely` a resistor; the swapped-lead reading would make it `confirmed`), so HOLD# idles high. Pin 3 gave a
  short beep to pin 8 and open to pin 4: no low-ohm path, a capacitance charging; its settled value in ohms is still
  to read.
  **For the dump this means:** the programmer must not feed the 3.3 V rail, because that drives U17's output with
  its input unpowered (OUT at most IN + 0.3 V). Feed 5 V at JP5 instead and leave the clip's VCC lead off
  ([recovery strategy](../firmware/recovery-strategy.md)).
- **P1-P4** are GPIO14-17, the GSPI port. Whether they go anywhere besides U1: each to U7's and U14's pins and to
  J8, unpowered.
- **J14's three straps:** pins 8, 7 and 6 run to X4, X5 and X6 on the top layer, each with a cap to GND;
  from there the route leaves the top layer. U1's bottom row (pins 17-21: TDO, GPIO28, TCK, TMS, SOP2) also drops to
  vias within a few mm, around C221. **Measured: X4 = SOP0 (U1.35), X5 = SOP1 (U1.34), X6 = SOP2 (U1.21)**,
  so the switch positions 1-3 are SOP0-2 in order (`likely`, through 's pin-to-pad order). **Pull-downs:
  X4 and X5 100 kΩ, X6 2.68 kΩ**, TI's recommended values, so a second, independent reading gives the same mapping.
  **The common side** is on 3V3 through about 270 Ω (R577, `likely`), not on 5 V, so a closed position would
  lift SOP2 to about 3.0 V and SOP0/SOP1 to about 3.3 V
  ([handbook chapter 1](../recovery/01-meter-checks.md), step 3).
- **UART0 toward J29: settled by use, `confirmed`: hole 1 = the CC3220's RX (pin 57), hole 2 = its TX (pin
  55), hole 3 GND; driven directly (no series part worth the name), and shared with U7**, whose firmware drives the
  CC3220's RX line from power-up. The ROM boot loader answers through J29 (921 600 baud, the CH340's TXD through
  1.2 kΩ on hole 1) once U7 is held in reset at **C3's top pad** (U7's RESET_N, pin 35). The 2026-11-05
  readings below are kept as they were taken; their pairing and the 192 kΩ didn't hold up.
  **Measured: J29 pin 1
  reads 192 kΩ to U1 pin 55 and open to pin 57; J29 pin 2 reads 192 kΩ to pin 57 and open to pin 55** (red lead on
  the hole, one polarity). The pairing is the expected one, hole 1 = pin 55 (TX), hole 2 = pin 57 (RX) (`likely`).
  But the value isn't the few hundred ohms of a series resistor. Since each hole beeps to its TP, the 192 kΩ
  lies between TP29/TP28 and the U1 pins. What it is (matched high-value resistors, or a path through other parts)
  is open. If it's a series element, it is too slow for the boot loader's 921 600 baud through J29 (about
  192 kΩ × 10 pF ≈ 2 µs against a 1.09 µs bit), and the probes go on the U1 side of it. But the diode test shows a
  chip junction directly on each hole's net, which argues against a series element at the hole. The toe
  count and more readings decide.
