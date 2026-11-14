# Bench setup: powering and debugging the main board

Status: **plan, nothing done yet.** Read [recovery-strategy.md](../firmware/recovery-strategy.md) first. Every step here is
**read-only** unless explicitly marked WRITE.

## What the CC3220S security means for debugging
Sources: TI docs and TI E2E answers (see the end of this page).

| Feature | What TI says | Consequence for us |
|---|---|---|
| **Signed boot image** | `/sys/mcuimg.bin` is a *secure-signed* file on the CC3220S. Its signature must chain to a CA in the trusted root catalog, and it is checked when the file is written. Image integrity is checked at boot. | We can't patch Anova's firmware: any change breaks the signature. |
| **Encrypted file system** | Secure files are encrypted with a **device-unique key** plus key rotation. The file allocation table is encrypted too. | A flash dump is a perfect **backup of this unit**, but we can't read the files in it and can't clone the working unit's flash onto this one. |
| **Production mode** | Production images **disconnect JTAG/SWD**. Development mode (image bound to the device MAC) enables debugging. | **No JTAG debugging of the CC3220 on a production unit.** The CC3220 can only be examined via the UART bootloader, its UART output and the flash dump. |
| **UART bootloader (ROM)** | SOP strap = UARTLOAD lets Uniflash program a **complete new image**; the previous image is cleared. | The chip is **not locked**. We *can* install firmware, but only with an mcuimg signed by a trusted cert: Anova's (we don't have it) or TI's test certificate in development mode (our own firmware). |

So the realistic routes to *Anova's* firmware are: a backup of this unit (none exists from before the brick), an official
image from Anova, or Anova's signed OTA files (speculative, needs research).

## 1. Power

The main board gets all its power through the **30-way FFC J8** from the power board: **5.01 V on J8 pins 1-6**,
measured on the dead unit with the main board unplugged (`confirmed`, 2026-11-04; predicted in ). Under
load it isn't measured yet. The 3.3 V logic rail is made on the main
board by **U17, an onsemi NCP59800 LDO**, whose input accepts 2.2-6.0 V (6.5 V absolute maximum). There is no switching
regulator on the board to step 12 V down. Reasoning and the four checks that confirm it: [nets.md](nets.md#supply).
**Never put more than 6 V on J8 pins 1-6 or JP5.**

### Step 1a: measure the J8 supply in the cooker (one-time, with care)
Purpose: learn the supply voltage(s) and check whether the power board delivers them at all (hypothesis H4).

**Supply measured 2026-11-04**: 5.01 V on pins 1-6 against pin 30, main board unplugged
([J8](j8.md)). Still open from this step: the isolation check logged, the other pins' idle voltages, the sensor pins,
and the supply under load.
- The main board is low-voltage: an isolated flyback (transformer + Y-caps) feeds it, and the touch keys sit behind the glass.
  **Verify before trusting it.**
- **This is the one exception to "never power the unit with the head open"** ([disassembly.md](disassembly.md#safety)):
  nothing on the power board is touched, and the isolation check comes first. The open head exposes the power board's
  top edge: that is the live part.
- **Where (since 2026-11-04, J8 mapped):** at break-out B on the cooker's own FFC, with the **main board
  disconnected**, so the power board is measured alone and nothing can reach the main board. The FFC goes into
  break-out B with its contacts facing the way they faced in the main-board J8. The test-point probing on the main
  board, planned before J8 was mapped, is dropped.
- **Unplugged, first:**
  1. **Numbering:** on B's header, pins 1-6 ring to each other, and 10, 11, 17, 19, 22, 23 and 30 ring to each other
     but not to 1-6 ([J8](j8.md)). If they show up at the other end, B is the wrong way round: fix that before power.
  2. **Isolation, cold:** resistance from the plug's L and N pins to header GND: open.
  3. **Sensor:** resistance from header pins 24, 25 and 26 to GND with the tube in cold water, then in warm water from a
     kettle. The pin that moves is the temperature sensor.
- **Setup for the live part:**
  - the tube in a pot of water between the min and max lines. With the main board absent, the heater and pump inputs
    may float (`guess`); a heater that fires should fire in water.
  - head open side up and dry, the break-out on an insulating surface
  - **battery multimeter only**: no PC, scope or other mains-grounded gear connected
  - one hand, and a switched outlet within reach
- **Live, the isolation check first:** measure **AC volts between header GND and the mains earth pin**.
  - A few tens of volts (Y-cap leakage, no current behind it) is normal.
  - **About 230 V AC means the low-voltage side is not isolated: stop**, unplug, and only ever work on it from a bench
    supply. No DC measurement is made in that case.
- **Live, only if the isolation check passes, DC to header GND:**
  - pins 1-6: about 5 V expected ([nets](nets.md#supply)). About 0 V means the power board doesn't deliver (H4).
    With a mV AC range, the ripple too.
  - every other pin: which ones the power board drives on its own. A pin at about 3.3 V points to a regulator, and
    maybe a microcontroller, on the power board (U2).
  - pins 24-26: a voltage there is sensor excitation.
  - optional, under load: 47 Ω (1 W or more) from pins 1-6 to GND, about 100 mA at 5 V. Does the supply hold?
- Nothing else is connected or injected. The main board under power is step 1b's job, on the bench supply; the live
  pass-through between the boards comes later, with the logic analyser.

### Step 1b: bench supply (normal way of working afterwards)
- Unplug the FFC from **main board J8** and feed the main board from a **current-limited lab supply** at the voltage
  found in step 1a. Two ways to connect:
  - a **30-pin 0.5 mm FPC/FFC breakout board** plus a short 30-pin 0.5 mm FFC. J8 pitch was measured from raptox's photo:
    30 contacts over about 14.3 mm = 0.49 mm.
    **Ordered 2026-11-01:** QUARKZMAN `FPC-30P 0.5MM` breakout (2-pack; 2x15 2.54 mm right-angle header, odd pins 1-29
    on one row per the product photo) and a 30-pin 0.5 mm, 100 mm **type A** (same-side contacts) FFC.
    - The bare contacts of the FFC must face the contacts of each connector (the blue stiffener is usually on the back).
      The breakout is a loose board, so a type A cable always fits: flip the breakout over, or give the cable a gentle
      half twist.
    - **That orientation decides whether J8 pin 1 lands on header pin 1 or pin 30.** Before any power: find the GND pins
      of J8 on the main board (continuity to the ground plane), then check with continuity which header pins they arrive
      on. Write the mapping down before connecting the supply.
  - Don't reuse the cooker's own FFC. Its far end is plugged into the power board deep in the tube.
  - or solder thin wires to the test points that carry the supply and GND (map them by continuity first). Not on
    raptox's unit: nothing gets soldered onto it.
  - or **JP5** (2.54 mm, empty; pin 1 = J8 supply = U17's input, pin 2 = GND, `confirmed` 2026-11-04): 5.0 V on
    pin 1 (square), GND on pin 2. The checks below passed on the dead unit; repeat them on any other board:
    - JP5 pin 1 to U17 pin 7/8 (C577's pad) reads 0 Ω
    - JP5 pin 2 to U15 pin 4 reads 0 Ω (this sets the polarity)
    - JP5 pin 1 to pin 2 is no short: a rising reading is the caps charging, a steady few ohms is a fault (and a finding)
    - **the cooker's FFC is out of J8**: JP5 pin 1 is the same copper as J8 pins 1-6, so with the cable in, the bench
      supply would back-feed the power board's supply

    Probes or a header held in the holes need no change to the board. A soldered header is a hardware change:
    raptox decides, and it gets logged: on raptox's unit, nothing gets soldered.
    The supply's over-voltage protection, if it has one, goes to 6 V (U17's
    input limit, 6.5 V absolute maximum). Reverse polarity is not covered by U17's datasheet: don't.
- Start with the **current limit at about 100 mA**, then raise it to about 500 mA. Note the idle current: it is a diagnostic
  in itself (ROM idle vs app running vs short). The CC3220 draws up to 450 mA in calibration bursts (SWAS035C
  section 8.5), so a limit that's too low shows up as brown-out reset loops, not as a fault of the board.
- First reading once powered: 3.3 V at C579 or U15 pin 8 means U17 regulates. If it does and the board stays silent,
  the fault sits past the supply (the main-board half of the  test).
- If step 1a isn't possible: **feed about 5 V at U17's input side** (J8 pins 1-6 or JP5 pin 1, once the
  [supply checks](nets.md#supply) confirm them), current limit low. Don't inject 3.3 V straight onto the 3.3 V rail
  with U17's input unpowered: the NCP59800's absolute maximum keeps OUT at most 0.3 V above IN, so that back-feeds it
  out of spec.
- The power board stays out of the circuit, so there is no mains on the bench. The app firmware may complain about the
  missing power board (sensor errors), but the ROM bootloader, UART and the flash don't need it.

## 2. Map the debug pads first (unpowered, continuity)
CC3220 VQFN-64 pins, checked against SWAS035C table 7-1 on 2026-11-04 (confirmed). The datasheet lists pins 55/57
among the UART0 TX/RX options. That the ROM bootloader uses exactly those two is from TI's tools and is **unverified**.
Traced nets: [nets.md](nets.md).

| Signal | CC3220 pin | Expected on |
|---|---|---|
| UART0 TX (bootloader) | 55 | **J29 pin 2** (`confirmed` by a boot-loader session; 's pairing and 192 kΩ didn't hold up). J29: pin 3 GND |
| UART0 RX (bootloader) | 57 | **J29 pin 1**, shared with U7's TX: hold U7 in reset at C3's top pad for a session |
| SOP2 | 21 | **pad X6**, J14 pin 6 (pad to pin 21: beeper) |
| SOP1 | 34 | **pad X5**, J14 pin 7 |
| SOP0 | 35 | **pad X4**, J14 pin 8 |
| nRESET | 32 | J14 / TP? |
| TCK / TMS / TDI / TDO | 19 / 20 / 16 / 17 | TDI on pad P9; the others on P1-P4 or J37/J38? (disabled in production mode anyway) |

CC2640R2F (U7): **TMSC = TP13 (pin 24), TCKC = TP14 (pin 25)**, TDO = TP43, TDI = TP42 (traced on the mosaic,
`likely`; the beeper in [flash backup page 10](../flashbackup/10-cooker-u7.md) confirms). RESET_N (pin 35) runs
to an R/C pair, no test point. Its UART is pins 7 (RX) and 8 (TX), the same two lines as J29.

### J14 (empty DIP-switch footprint)
On the FCC sample J14 holds a 4-way DIP switch. On raptox's unit only the 8 pads are left: pitch about 1.27 mm (half-pitch),
rows about 6 mm apart, both measured from photo `05_main-board_component-side.jpg` with U1's 9 mm body as the scale (likely).
- **Function:** CC3220 SOP boot-mode straps, **confirmed by the meter since ** (below). The first evidence, from
  the photos:
  - three resistors (R533, R535, R577) sit right next to it, matching the three SOP pull-downs (R577 turned out to be
    the common side's 270 Ω feed from 3.3 V)
  - the FCC sample also had the J29 header fitted: a boot-mode switch plus UART is what a test lab needs to load RF-test firmware
  - without the switch the pull-downs hold SOP = 000, which is normal boot
- **The fourth switch is unknown (guess):** nRESET, the CC2640R2F bootloader pin, or a test-mode input.
- **Measured and traced:** pin 1 is the pad by the dot, top of the left row; pins 1-4 run down the left row,
  5-8 up the right, so the positions are 1-8, 2-7, 3-6, 4-5. Pins 1-3 are one net, with R577 (meter); pins 4 and 5
  are unused; pins 8, 7 and 6 run to the strap pads X4, X5 and X6 beside Y3 (meter, pair by pair: ), each with a
  cap to GND. From the pads the route leaves the top layer, and U1's bottom row, SOP2 included,
  drops to vias near C221 (likely). **Pads to U1 measured: X4 = SOP0 (pin 35), X5 = SOP1 (pin 34), X6 = SOP2
  (pin 21).** So the strap function is confirmed for three positions, and the switch's positions 1-3 are SOP0-2
  (confirmed). **Pull-downs measured: X4 and X5 100 kΩ, X6 2.68 kΩ**,
  the fingerprint of step 3 below, sorted the same way. **The common side: 270 Ω to 3V3** (U15 pin 8; R577,
  likely), not on 5 V, so the switch pulls a strap to 3.3 V. The steps below are done; kept as the method:
  1. Find 3.3 V and GND by continuity. The flash U15 has the standard SPI NOR pinout: pin 8 = VCC, pin 4 = GND.
  2. Check each of the 8 pads against both. One row is probably common to 3.3 V, so a closed switch pulls that strap high.
  3. Measure each pad of the other row to GND. The pull resistors are a fingerprint: about 100 k for SOP0 and SOP1, about
     2.7 k for SOP2 (SWAS035, see [recovery-strategy.md](../firmware/recovery-strategy.md)). Where the QFN pins can be
     reached, confirm with continuity to the CC3220 (SOP2 = 21, SOP1 = 34, SOP0 = 35).
  4. **Where to touch U1** (VQFN-64, 0.5 mm pitch; pin 1 by the dot at the top-left, counter-clockwise; mosaic ):
     pin 21 is the 5th pin from the left on the bottom edge (the edge toward Y3), pin 32 (nRESET) the last on the right
     of that edge, pins 34 and 35 the 2nd and 3rd from the bottom on the right edge. Touch the pin's toe at the package
     edge with a needle tip, and check the neighbour doesn't ring as well: a slip gives a false hit.
- **Never close the SOP1 and SOP0 positions together (pads X5 and X4) before the flash backup exists:** SOP 011 = RET_FACTORY_IMAGE,
  which rewrites the flash at the next reset (backup-first ground rule, [the timeline](../timeline.md)).

## 3. Debug interfaces, in order of usefulness
1. **J29, the U1-U7 link** (spring probes in the holes; nothing soldered on raptox's unit): hole 1 carries
   U7 → U1, hole 2 U1 → U7, hole 3 GND. It is the chips' own framed link, not a text console. A logic
   analyser on holes 1 and 2 (listen-only) sees every message both ways. A USB-UART adapter at 115200 or 921600 shows
   nothing readable. The same pins are U1's ROM boot-loader port, used with U7 held in reset.
2. **SOP straps on J14 pads:**
   - Read the SOP levels at power-up: they should be 000 = normal boot. A wrong strap would explain a "dead" unit (H5).
   - For **UARTLOAD**, pull SOP2 high through a few hundred ohms, then reset. SOP2 is pad **X6**, with a 2.68 kΩ
     pull-down: 470 Ω from 3.3 V gives about 2.81 V, above VIH (min 0.65 × VDD = 2.15 V, SWAS035C p. 35).
   - With **Uniflash**, *connect and read device info only* (MAC, versions). **Do not click Program/Format.**
     TI's programming procedure writes a boot-loader patch into the serial flash (SWPA230A steps 8-10); a
     Uniflash connection with "get device info" wrote nothing on the LaunchPad (, development mode). On the
     cooker still only after its backup.
3. **Serial flash dump** (the main event): **with the clip on U15, the CC3220 held in reset** (since 2026-11-06): a production-mode CC3220S's boot loader refuses raw reads, file reads and file writes (found on the
   LaunchPad with a production image; 's in-circuit read through the boot loader works only on a development
   image). Reader: the FT232H (`ft2232_spi`, on order); the clip's VCC lead off, the board fed at JP5.
   The listing then comes offline from the dump (`tools/sflash/sffs.py`). Fallback: **off
   the board**, U15 desoldered and read in a 208 mil adapter with a 3.3 V
   programmer, WP#/HOLD# tied high (, steps in [recovery-strategy.md](../firmware/recovery-strategy.md)). In
   circuit with the clip it would need the board fed at JP5, the clip's VCC lead off and the CC3220 in reset.
   Read 2x and compare hashes. See [recovery-strategy.md](../firmware/recovery-strategy.md).
   The whole bench sequence, step by step with pictures: the [recovery handbook](../recovery/index.md).
4. **CC2640R2F via cJTAG** (XDS110 + Tag-Connect TC2030): connect and **read** flash + CCFG. The XDS110 can be the
   LaunchPad's own: its connector J4 "XDS110 OUT" drives an external 3.3 V target once the RST/TMS/TCK/TDO/TDI
   jumpers are pulled (SWRU463C figure 9; cJTAG `likely`). If CCFG has locked debug,
   don't try to unlock it: unlocking means a mass erase.
5. Scope/logic analyser on the crystals (Y3 40 MHz, Y4 32 kHz) and nRESET: shows whether the CC3220 is powered and
   running at all.

## Bench kit
Status as of 2026-11-01.

| Item | Status | Why |
|---|---|---|
| Current-limited bench supply (0-15 V, 1 A+) | owned (several) | safe power, current as a diagnostic |
| Multimeter: **Fluke 25** ([photo](../../images/own/2026-11-05/03_fluke-25_multimeter_front.jpg)), battery-powered handheld. From the front panel (`confirmed`): RANGE and HOLD buttons; V, mV, mA/A, µA, each DC and AC; Ω; beeper and diode test on one dial position; jacks A (10 A max), mA/µA (320 mA max), COM, V/Ω/diode. Bar graph scaled 0-30, so a 3200-count display (`likely`). Ω test current and diode-mode test voltage: not known yet (the manual, unverified). | owned | every meter reading: the J8 supply (step 1a, a battery meter only), continuity with the beeper, resistance, diode mode ([handbook chapter 1](../recovery/01-meter-checks.md)) |
| 30-pin 0.5 mm FPC breakout board + 30-pin 0.5 mm FFC | ordered 2026-11-01: QUARKZMAN 2-pack + one 100 mm type A FFC, **delivered 2026-11-03** | feed the main board without the power board. The second board lets us build a pass-through later, to sniff J8 between the boards; that needs a second FFC (type to be decided once the geometry is known). |
| USB-UART, 3.3 V logic | owned (several adapters; set the I/O jumper to 3.3 V). The one plugged in on 2026-11-05 is a **WCH CH340** (USB 1A86:7523), not an FTDI: UART only, no SPI, so not a flash reader. Whether its Windows driver sends the 200 ms break cc3200tool needs is `unverified`: try it on the LaunchPad first (handbook step 2.5) | J29 UART, Uniflash |
| Hands-free probes | owned: Sensepeek PCBite kit 6012 + 2x 6005 (8 SQ10 probes with Dupont/banana test wires, 2 DMM probes) | probing pads, test points and QFN pins; the logic-analyser leads go onto the SQ10 probes |
| Logic analyser: **DreamSourceLab DSLogic Plus** (specs from the listing). Supported by **sigrok-cli**, so captures and protocol decoding can be scripted from the PC. One-time firmware setup: libsigrok needs the FPGA bitstreams from DSView. If sigrok doesn't support this hardware revision: capture in DSView, export VCD, decode with sigrok-cli. | ordered 2026-11-01; **in hand** | boot UART at unknown baud, SOP/nRESET timing, J8 signals, SPI flash bus at boot (clock speed unknown, probably tens of MHz: guess). Connect only with the board on the bench supply: the PC ground goes to the board ground. |
| Hook clips (HALJIA, 10 pcs) | ordered 2026-11-01, 2 packs, **delivered 2026-11-05** | component legs, header pins, wires |
| SOIC-8 clip **208 mil** | ordered 2026-11-01: KeeYees kit (clip listed for wide and narrow body), **delivered 2026-11-05**. With it, per the listing: a CH341A, a SOP8-to-DIP8 adapter, a 1.8 V adapter. **Don't use the kit's CH341A on this board**: the stock board puts 5 V on the data lines (measured 2026-11-06: about 5 V on MOSI). The 1.8 V adapter isn't needed (3.3 V flash). Arrival checks: clip contact to lead (which is pin 1), jaws on a 208 mil body, adapter footprint 208 mil? | flash dump: the clip on the loose U15 |
| 3.3 V SPI programmer | owned: Raspberry Pi (flashrom `linux_spi`, driven over SSH) or an RP2040 Pico (pico-serprog) | flash dump |
| Spare SPI NOR: 2x Winbond **W25Q64JVSSIQ** (64 Mbit; `SS` = SOIC-8 208 mil per Winbond's ordering code: likely) | ordered 2026-11-01 | First a **practice target**: try the clip, the programmer and the read-twice/compare-hash routine on a chip that doesn't matter. Later maybe a recovery route that leaves the original flash untouched: program a fresh chip and swap it in. That is still a WRITE under rule 1, and whether the CC3220 ROM accepts this flash part is unverified. |
| Half-pitch DIP switch: 2x Omron **A6H-4101** (4-way SMD slide) | ordered 2026-11-01, **delivered 2026-11-05** | J14, the boot-mode straps (pads confirmed as SOP0-2); **not fitted on raptox's unit** (, replaces 's plan): kept for a development unit. On raptox's unit the strap is a probe across position 3. Positions 1/2/3 = SOP0/SOP1/SOP2 (`confirmed`), 4 unconnected; a closed position gives about 3.0 V through the 270 Ω common feed. **UARTLOAD = position 3 alone. Positions 1 and 2 never ON together before the backup**: that is RET_FACTORY_IMAGE, a write (rule 1). The 1.27 mm pitch matches the photo measurement. Check the row spacing (about 6 mm) against the A6H footprint before soldering (unverified). Solder it with every position OFF (SOP = 000), with the iron (U1 and U15 are next to J14). Never fit it on the working unit (it is read-only, ground rule in ). |
| No-clean tack flux (Chip Quik SMD291, 5 ml) | ordered 2026-11-01 | J14 switch, J29 header, wires to pads: on a development unit only |
| Digital microscope Andonstar AD409 Pro-ES | ordered 2026-11-01, **in use since 2026-11-03**. USB live view up to 1920x1080 ([microscope.md](../microscope.md), [capture tool](../../tools/microscope/README.md)). **First job:** the mosaic photoshoot. | markings, traces, soldering wires to pads |
| Backlight panel: Elgato Key Light | owned | shines through the board under the microscope: layer count, inner copper (see [photos.md](../photos.md)) |
| ESD kit: wrist strap, earthing plug, 2 coil cords, ESD brush | ordered 2026-11-01 | handling the bare boards (CC3220, CC2640R2F and the flash are ESD-sensitive). The earthing plug uses only the mains earth pin. Clean the boards with the brush. |
| 1x3 2.54 mm pin header, thin wire, 470 R-1 k resistors | workshop stock | J29, J14 straps |
| **TI CC3220S LaunchPad** (CC3220S-LAUNCHXL, rev A) | ordered 2026-11-01, **delivered 2026-11-05** | has an XDS110 on board, and gives a known-good CC3220S to practise Uniflash, SOP modes, the boot-loader flash read and the file-level write on before touching the cooker ((private rehearsal chapter: names the vendor's firmware files and the signature handling, not published)). J13 ships on SOP1; its XDS110 also reaches external targets through J4 |
| **TI CC2640R2F LaunchPad** (LAUNCHXL-CC2640R2; CC2640R2F in the 7x7 VQFN-48, like U7) | ordered 2026-11-05, **backorder, estimated in stock 2027-01-28** | the Bluetooth/real-time chip's leg rehearsed (cJTAG read, ROM boot loader, Anova's `cc2640.bin`), and both 3.3.35 images on the bench, wired UART to UART |
| **Adafruit FT232H breakout** (2264, FTDI FT232H, 3.3 V) | ordered 2026-11-05 | the flash reader for the clip: flashrom `ft2232_spi` (Windows needs the WinUSB driver once, via Zadig); also a 3.3 V UART/SPI/I2C tool |
| **10-pin 2x5 1.27 mm cable** (Adafruit 1675) + **SWD 2x5 1.27 mm breakout** (Adafruit 2743) | ordered 2026-11-05 | the LaunchPad's J4 "XDS110 OUT" out to 2.54 mm pins and jumper wires: the cJTAG route to the cooker's U7 without a Tag-Connect |
| 2x Kapton (polyimide) tape, 20 mm | ordered 2026-11-05 | insulating and holding wires and probes on the boards |
| 2x **ESP32 dev kit** (Diymore 2-pack; exact variant to check on arrival: an S3 is needed for native touch, any Wi-Fi/BLE variant does for the rest) | ordered 2026-11-01 | first plan-B hardware: the zero-spin headless prototype (route C0), and before that a BLE/Wi-Fi scanner for track T8 |
| Tag-Connect TC2030-CTX-NL (or pogo pins) | later; for now the 1.27 mm cable and breakout above, with jumper wires to the pads | J37/J38 |
| 3-pin 2.54 mm Molex header (instead of a plain 1x3 male header, 0.64 mm square pins) | **on order** (raptox, 2026-11-05; part number and supplier to add); **not fitted on raptox's unit**, kept for a development unit | **J29**, the UART header: holes about 1.1 mm, open; pin 3 = GND. Leads to the USB-UART adapter or j8probe `aux`, RX only. J29 carried the revival's boot-loader sessions, with probes (, which corrects 's pairing and 192 kΩ) |
| Polarised 2-pin 2.54 mm connector: Molex KK 254 header (22-27-2021) with housing and crimps, or a 2.54 mm screw terminal (e.g. Phoenix MPT 0,5/2-2,54) | **Molex on order** (raptox, 2026-11-05; part number and supplier to add); **not fitted on raptox's unit**, kept for a development unit | **JP5**, the bench power entry: pin 1 (square) = VIN 5 V, pin 2 = GND. Polarised so the supply can't go on reversed. Check the part's pin size against the 1.1 mm holes |

### Spent so far (2026-11-02)
Updated 2026-11-05. Prices as paid, incl. VAT. Order numbers and addresses stay out of the repo.

| Item | € |
|---|---|
| Andonstar AD409 Pro-ES microscope | 238.00 |
| DreamSourceLab DSLogic Plus | 139.50 |
| TI CC3220S LaunchPad (CC3220S-LAUNCHXL) | 53.69 |
| 2x ESP32 dev kit | 22.98 |
| Hook clips, 2 packs | 17.98 |
| FPC-30P 0.5 mm break-out, 2-pack | 10.22 |
| 30-pin 0.5 mm FFC, 100 mm, type A | 7.99 |
| KeeYees SOIC-8 clip kit | 16.31 |
| ESD earthing plug | 10.39 |
| 2x Omron A6H-4101 DIP switch | 8.32 |
| 2x Winbond W25Q64JVSSIQ | 7.78 |
| TI CC2640R2F LaunchPad (LAUNCHXL-CC2640R2), backorder | 58.04 |
| Adafruit FT232H breakout | 16.06 |
| 10-pin 1.27 mm cable + SWD 2x5 breakout (Adafruit 1675, 2743) | 6.34 |
| 2x Kapton tape 20 mm | 11.16 |
| ESD wrist strap | 4.50 |
| 2x ESD coil cord | 6.53 |
| ESD brush | 2.44 |
| **Total so far** | **638.23** |

Not priced yet: Chip Quik flux. The 2026-11-05 DigiKey order is DigiKey's prices excl. VAT plus 21 % (calculated); shipping free (over €75 excl. VAT). Already owned before this project, not
counted: bench supplies, FTDI adapters, PCBite probes, Raspberry Pi / Pico, Key Light.


## Sources
- TI E2E: production mode disables JTAG, development mode enables it:
  <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/580493/ccs-cc3220sf-launchxl-error-connecting-to-the-target-error--1170-0x0-unable-to-access-the-dap>,
  <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/750077/ccs-cc3220sf-launchxl-issues-with-with-the-xds110-debugger-on-cc3220>
- TI CC3220 out-of-box guide (development mode, MAC-bound, dummy playground certificate):
  <https://www.ti.com/document-viewer/lit/html/SWRU473A/program-a-user-modified-oob-binary-t4345934-106>
- TI CC32xx programmer's guide, file roles (`/sys/mcuimg.bin` secure-signed):
  <https://www.ti.com/document-viewer/lit/html/SWRU455M/GUID-77F00B75-1E41-477B-AA66-211A3B21F082>
- TI E2E: secure boot, signature checked at write, integrity at boot:
  <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/887901/cc3220sf-boot-procedure-secure-boot-and-encryption>
- TI E2E: device-unique key + key rotation; whole image reprogrammed at once, previous image cleared:
  <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/974717/launchcc3220modasf-cloning-protection-and-encryption-of-gang_images>
