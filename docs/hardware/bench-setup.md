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

The main board gets all its power through the **30-way FFC J8** from the power board. The voltage on J8 is unknown.
The main board seems to have its own regulators (U17 and U2 are the candidates, both `guess`), so it probably receives
something above 3.3 V (5 V or 12 V are typical).

### Step 1a: measure the J8 supply in the cooker (one-time, with care)
Purpose: learn the supply voltage(s) and check whether the power board delivers them at all (hypothesis H4).
- The main board is low-voltage: an isolated flyback (transformer + Y-caps) feeds it, and the touch keys sit behind the glass.
  **Verify before trusting it.**
- **This is the one exception to "never power the unit with the head open"** ([disassembly.md](disassembly.md#safety)):
  main-board side only, nothing on the power board is touched, and the isolation check comes first.
- Setup:
  - head open, bezel hinged out and **resting on an insulating surface**
  - **battery multimeter only**: no PC, scope or other mains-grounded gear connected
  - one hand, and keep away from the open housing and the power board
  - find main-board GND by continuity first, **unplugged** (e.g. the J9 speaker connector shell or a ground pad)
- **First, the isolation check:** measure **AC volts between main-board GND and the mains earth pin**.
  - A few tens of volts (Y-cap leakage, no current behind it) is normal.
  - **About 230 V AC means the board is not isolated: stop**, unplug, and only ever work on it from a bench supply.
    No DC measurement is made in that case.
- Only if the isolation check passes, measure DC between main-board GND and:
  - each J8-side test point (TP1/TP2/TP3/TP8/TP9 near J8)
  - the input and output caps of U17 and U2
  - the CC3220 supply caps

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
  - or solder thin wires to the test points that carry the supply and GND (map them by continuity first).
- Start with the **current limit at about 100 mA**, then raise it to about 500 mA. Note the idle current: it is a diagnostic
  in itself (ROM idle vs app running vs short).
- If step 1a isn't possible: inject **3.3 V directly on the 3.3 V rail** (the regulator output cap), regulators
  bypassed, with the current limit low. Only once that rail is identified for certain.
- The power board stays out of the circuit, so there is no mains on the bench. The app firmware may complain about the
  missing power board (sensor errors), but the ROM bootloader, UART and the flash don't need it.

## 2. Map the debug pads first (unpowered, continuity)
CC3220 VQFN-64 pins, checked against SWAS035C table 7-1 on 2026-11-04 (confirmed). The datasheet lists pins 55/57
among the UART0 TX/RX options. That the ROM bootloader uses exactly those two is from TI's tools and is **unverified**.
Traced nets: [nets.md](nets.md).

| Signal | CC3220 pin | Expected on |
|---|---|---|
| UART0 TX (bootloader) | 55 | J29? (via R579/R580?) |
| UART0 RX (bootloader) | 57 | J29? |
| SOP2 | 21 | J14 pads? |
| SOP1 | 34 | J14 pads? |
| SOP0 | 35 | J14 pads? |
| nRESET | 32 | J14 / TP? |
| TCK / TMS / TDI / TDO | 19 / 20 / 16 / 17 | J37/J38? (disabled in production mode anyway) |

CC2640R2F (U7): find RESET_N, TMSC, TCKC (cJTAG) and its bootloader UART on TP13/14/42/43/44 or J37/J38.

### J14 (empty DIP-switch footprint)
On the FCC sample J14 holds a 4-way DIP switch. On raptox's unit only the 8 pads are left: pitch about 1.27 mm (half-pitch),
rows about 6 mm apart, both measured from photo `05_main-board_component-side.jpg` with U1's 9 mm body as the scale (likely).
- **Function (likely, not measured):** CC3220 SOP boot-mode straps. Evidence:
  - three resistors (R533, R535, R577) sit right next to it, matching the three SOP pull-downs
  - the FCC sample also had the J29 header fitted: a boot-mode switch plus UART is what a test lab needs to load RF-test firmware
  - without the switch the pull-downs hold SOP = 000, which is normal boot
- **The fourth switch is unknown (guess):** nRESET, the CC2640R2F bootloader pin, or a test-mode input.
- **The mosaic shows the top layer** ([nets.md](nets.md)): pins 1-3 are linked to each other and to R577, pin 4 is not, and
  pins 5-8 lead off to vias. U1's bottom row, SOP2 included, drops to vias near C221 too (likely). Map the rest
  unpowered:
  1. Find 3.3 V and GND by continuity. The flash U15 has the standard SPI NOR pinout: pin 8 = VCC, pin 4 = GND.
  2. Check each of the 8 pads against both. One row is probably common to 3.3 V, so a closed switch pulls that strap high.
  3. Measure each pad of the other row to GND. The pull resistors are a fingerprint: about 100 k for SOP0 and SOP1, about
     2.7 k for SOP2 (SWAS035, see [recovery-strategy.md](../firmware/recovery-strategy.md)). Where the QFN pins can be
     reached, confirm with continuity to the CC3220 (SOP2 = 21, SOP1 = 34, SOP0 = 35).
- **Never close the SOP1 and SOP0 positions together before the flash backup exists:** SOP 011 = RET_FACTORY_IMAGE,
  which rewrites the flash at the next reset (backup-first ground rule, [the timeline](../timeline.md)).

## 3. Debug interfaces, in order of usefulness
1. **UART on J29** (after fitting a 1x3 header): USB-UART adapter at **3.3 V**. Capture power-up output at
   115200 and 921600 baud, and use a logic analyser if the baud rate is unknown. Any output at all tells us the CC3220 is
   alive and how far it gets.
2. **SOP straps on J14 pads:**
   - Read the SOP levels at power-up: they should be 000 = normal boot. A wrong strap would explain a "dead" unit (H5).
   - For **UARTLOAD**, pull SOP2 high through a few hundred ohms (the board may have a strong pull-down), then reset.
   - With **Uniflash**, *connect and read device info only* (MAC, versions). **Do not click Program/Format.**
3. **Serial flash dump** (the main event): SOIC-8 208 mil clip, CC3220 held in reset, 3.3 V programmer. Read 2x and
   compare hashes. See [recovery-strategy.md](../firmware/recovery-strategy.md).
4. **CC2640R2F via cJTAG** (XDS110 + Tag-Connect TC2030): connect and **read** flash + CCFG. If CCFG has locked debug,
   don't try to unlock it: unlocking means a mass erase.
5. Scope/logic analyser on the crystals (Y3 40 MHz, Y4 32 kHz) and nRESET: shows whether the CC3220 is powered and
   running at all.

## Bench kit
Status as of 2026-11-01.

| Item | Status | Why |
|---|---|---|
| Current-limited bench supply (0-15 V, 1 A+) | owned (several) | safe power, current as a diagnostic |
| 30-pin 0.5 mm FPC breakout board + 30-pin 0.5 mm FFC | ordered 2026-11-01: QUARKZMAN 2-pack + one 100 mm type A FFC, **delivered 2026-11-03** | feed the main board without the power board. The second board lets us build a pass-through later, to sniff J8 between the boards; that needs a second FFC (type to be decided once the geometry is known). |
| USB-UART, 3.3 V logic | owned (several FTDI adapters; set the I/O jumper to 3.3 V) | J29 UART, Uniflash |
| Hands-free probes | owned: Sensepeek PCBite kit 6012 + 2x 6005 (8 SQ10 probes with Dupont/banana test wires, 2 DMM probes) | probing pads, test points and QFN pins; the logic-analyser leads go onto the SQ10 probes |
| Logic analyser: **DreamSourceLab DSLogic Plus** (specs from the listing). Supported by **sigrok-cli**, so captures and protocol decoding can be scripted from the PC. One-time firmware setup: libsigrok needs the FPGA bitstreams from DSView. If sigrok doesn't support this hardware revision: capture in DSView, export VCD, decode with sigrok-cli. | ordered 2026-11-01 (delivery 20-25 Nov) | boot UART at unknown baud, SOP/nRESET timing, J8 signals, SPI flash bus at boot (clock speed unknown, probably tens of MHz: guess). Connect only with the board on the bench supply: the PC ground goes to the board ground. |
| Hook clips (HALJIA, 10 pcs) | ordered 2026-11-01, 2 packs (delivery expected Thu 2026-11-05) | component legs, header pins, wires |
| SOIC-8 clip **208 mil** | ordered 2026-11-01: KeeYees kit (clip listed for wide and narrow body), delivery expected Thu 2026-11-05. **Don't use the kit's CH341A on this board**: the stock board puts 5 V on the data lines. | flash dump |
| 3.3 V SPI programmer | owned: Raspberry Pi (flashrom `linux_spi`, driven over SSH) or an RP2040 Pico (pico-serprog) | flash dump |
| Spare SPI NOR: 2x Winbond **W25Q64JVSSIQ** (64 Mbit; `SS` = SOIC-8 208 mil per Winbond's ordering code: likely) | ordered 2026-11-01 | First a **practice target**: try the clip, the programmer and the read-twice/compare-hash routine on a chip that doesn't matter. Later maybe a recovery route that leaves the original flash untouched: program a fresh chip and swap it in. That is still a WRITE under rule 1, and whether the CC3220 ROM accepts this flash part is unverified. |
| Half-pitch DIP switch: 2x Omron **A6H-4101** (4-way SMD slide) | ordered 2026-11-01 | J14, **only once the pads are confirmed as the SOP straps**. The 1.27 mm pitch matches the photo measurement. Check the row spacing (about 6 mm) against the A6H footprint before soldering (unverified). Solder it with every position OFF (SOP = 000). Never fit it on the working unit (it is read-only, ground rule in ). |
| No-clean tack flux (Chip Quik SMD291, 5 ml) | ordered 2026-11-01 | J14 switch, J29 header, wires to pads |
| Digital microscope Andonstar AD409 Pro-ES | ordered 2026-11-01, **in use since 2026-11-03**. USB live view up to 1920x1080 ([microscope.md](../microscope.md), [capture tool](../../tools/microscope/README.md)). **First job:** the mosaic photoshoot. | markings, traces, soldering wires to pads |
| Backlight panel: Elgato Key Light | owned | shines through the board under the microscope: layer count, inner copper (see [photos.md](../photos.md)) |
| ESD kit: wrist strap, earthing plug, 2 coil cords, ESD brush | ordered 2026-11-01 | handling the bare boards (CC3220, CC2640R2F and the flash are ESD-sensitive). The earthing plug uses only the mains earth pin. Clean the boards with the brush. |
| 1x3 2.54 mm pin header, thin wire, 470 R-1 k resistors | workshop stock | J29, J14 straps |
| **TI CC3220S LaunchPad** (CC3220S-LAUNCHXL) | ordered 2026-11-01 | has an XDS110 on board, and gives a known-good CC3220S to practise Uniflash, SOP modes and flash dumps on before touching the cooker |
| 2x **ESP32 dev kit** (Diymore 2-pack; exact variant to check on arrival: an S3 is needed for native touch, any Wi-Fi/BLE variant does for the rest) | ordered 2026-11-01 | first plan-B hardware: the zero-spin headless prototype (route C0), and before that a BLE/Wi-Fi scanner for track T8 |
| Tag-Connect TC2030-CTX-NL (or pogo pins) | later | J37/J38 |

### Spent so far (2026-11-02)
Prices as paid, incl. VAT. Order numbers and addresses stay out of the repo.

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
| ESD wrist strap | 4.50 |
| 2x ESD coil cord | 6.53 |
| ESD brush | 2.44 |
| **Total so far** | **546.63** |

Not priced yet: Chip Quik flux. Already owned before this project, not
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
