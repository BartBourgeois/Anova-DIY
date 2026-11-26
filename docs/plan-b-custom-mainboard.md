# Plan B: our own main board

Status: **the committed fallback**. Evaluated 2026-11-01, nothing built or ordered yet.
Step 1 is still to fix the original board if that can reasonably be done ([recovery-strategy.md](firmware/recovery-strategy.md));
this is step 2.

## When this applies
When the original main board can't reasonably be fixed: recovery fails (Phase 5), or the board turns out to be dead as
hardware, not just as firmware. Anova is not counted on; an image from them would be a bonus for step 1.

## Goal and limits
- Result: **one working cooker** with a replacement "brain". Budget **€500**, all prototypes included.
- Reuse the 30-way FFC, the speaker (J9), the housing and the bezel, light guide and glass.
- **The power board is never modified.** Everything on the mains side stays original. We only replace or reprogram
  the low-voltage main board.
- We lose the Anova app and cloud. The replacement is controlled locally, e.g. ESPHome with Home Assistant.

## The two questions that decide the scope
1. **Is there an MCU on the power board?** U2 is the candidate (unknown, [power-board.md](hardware/power-board.md)).
   - **Yes:** J8 probably carries a serial protocol (`guess`): "set heater/pump" one way, "temperature/status" the
     other. We reproduce that protocol. This is the easier case.
   - **No:** J8 carries raw signals: a sensor voltage, relay drive, pump drive. Then our board runs the control loop
     and the safety logic, and we calibrate the sensor ourselves.
   - **Trap:** if the failed OTA was updating a power-board MCU (hypothesis H3 in the recovery strategy), a new
     main board fixes nothing. It would be talking to a dead chip.
2. **Is the main board hardware dead, or only its firmware?** If the hardware is fine, routes A and B below are much
   cheaper than a new board and keep the original mechanics.

## Routes

| | What | Cost (`guess`) | Main risk |
|---|---|---|---|
| **A. Own firmware on the original CC3220** | Swap in one of the spare W25Q64JVSSIQ chips (208 mil, fits U15/U16), so the original chip is kept untouched. Program our own development-mode image with Uniflash and TI's test certificate ([bench-setup.md](hardware/bench-setup.md#what-the-cc3220s-security-means-for-debugging)). Practise on the CC3220S LaunchPad first. | ~€0 (parts already ordered) | Needs working board hardware. Whether the CC3220 ROM accepts the Winbond part is `unverified`. TI SDK. BLE (CC2640R2F) unused. Still a WRITE under the backup-first rule: dump the original first. |
| **B. ESP32 transplant** | Hold U1 and U7 in reset. Wire an ESP32-S3 module to the J8 nets and to whatever drives the LEDs and touch keys (U14?). The old board stays the display, touch and speaker carrier. | €20-40 | Only works if the LEDs and touch keys go through a separate driver chip, not straight to U1/U7 pins. That their pins float while in reset is a `guess`. Fiddly wiring. |
| **C. New main board** | Same outline, ESP32-S3, LED driver, touch, amplifier, our own firmware | €360-480 | Mechanics (LED and touch-pad positions), RF next to the steel tube, the most work |
| **C0. Zero-spin headless** | The FPC-30P break-out + an ESP32-S3 dev kit + a buck module + a speaker driver, wired on a 3D-printed carrier behind the bezel. No display, no touch; Home Assistant is the UI. The old board stays on the bezel unpowered, or comes off. | €30-40 | Same J8 groundwork as B/C. Same safety requirements. It's the prototype for B and C anyway, and the product if the display is dropped. Weeks, not months, once J8 is understood. |
| **D. Donor main board** (added , not an ESP32 route) | A second-hand Pro with a **mechanical** fault (pump, impeller, motor) gives an untouched main board. The flash is bound to its own CC3220 and both move together, so it's a complete working set. Swap the bezel assembly: 4 screws, FFC, speaker plug. | €50-120 | Account release by the previous owner (`guess`). The app may offer the same OTA again (guess): decline it until the brick is understood. Needs the power board to be OK. **Bonus:** the old board becomes a risk-free lab specimen for everything destructive (un-staking, LED-side scan, lifting the flash). |

All three routes need the same groundwork (the J8 pinout and meaning, plus a map of which chip drives what), so
none of it is wasted. The first prototype for C is effectively route B or a dev kit on the bench.

## Route C: what the board needs

| Block | Choice | Why | Confidence / source |
|---|---|---|---|
| MCU | **ESP32-S3-WROOM-1** module with PCB antenna | 14 capacitive-touch pins (6 keys need no extra chip), Wi-Fi + BLE, I²S. ESPHome support. | `confirmed`: Espressif ESP32-S3 datasheet. The C3 and C6 have no touch pins (`likely`). |
| LEDs (about 135) | 1x **IS31FL3731** (16x9 = 144 LEDs, I²C, per-LED dimming) or 2x **HT16K33** (16x8 = 128 each) | one I²C bus, no multiplexing load on the MCU | `likely`: ISSI and Holtek datasheets, not re-checked for this note |
| Touch | ESP32-S3 native touch, pads copied from the original layout | the glass thickness is fixed, so copy what works | position from the LED-side scan |
| Speaker | **MAX98357A** I²S class-D, or a MOSFET + PWM if beeps are enough | reuses the original speaker on a J9-compatible connector | `likely`: ADI datasheet |
| Power | buck converter from the J8 supply to 3.3 V, at least 600 mA | Wi-Fi peaks of about 500 mA (`likely`, Espressif) | the J8 voltage is unknown: [bench-setup.md](hardware/bench-setup.md) step 1a |
| J8 | new 30-pin 0.5 mm FPC connector, same contact side as the original | the original FFC must plug in unchanged | 0.5 mm pitch: the 30-pin span measures 14.55 mm on the microscope mosaic. Position and pin-1 end in [main-board.md](hardware/main-board.md#mechanics). Check the contact side. |
| Outline and fixing | same outline, the 6 heat-stake and 2 locating-pin positions | the bezel stays as it is | component-side positions measured on the mosaic, `likely`: [main-board.md](hardware/main-board.md#mechanics). The outline still needs a caliper check. |
| Antenna | module antenna at one of the original antenna zones (left edge or bottom) | the original designers already found a spot that works next to the tube | [main-board.md](hardware/main-board.md#mechanics) |
| Firmware | **ESPHome**: PID climate, OTA, logs over Wi-Fi, Home Assistant. Custom components for the display and J8. | least code to write | ESPHome docs |

### Safety requirements (route B and C)
These are requirements, not nice-to-haves:
1. **Heater off by default.** Pull-downs on every power-board control line, so a reset, a brown-out or an unflashed
   ESP32 means "off".
2. **Hardware watchdog in the heater path** (e.g. TI TPS3431): the heater-enable line only passes while the firmware
   keeps kicking the watchdog. A hung ESP32 drops the relay.
3. **Keep the power board's own thermal cut-off.** Find it first (one of the wire terminals is a candidate,
   [power-board.md](hardware/power-board.md)). Never rely on firmware alone.
4. **Learn how the original detects low water** before our firmware ever switches the heater on (unknown).
5. **Over-temperature limit in firmware too**, independent of the PID: a hard upper limit that latches the heater off.
6. **Mains tests with the head closed:** bezel screwed in, ESP32 reached only over Wi-Fi (OTA and logs), no wires
   leaving the housing, RCD-protected outlet, always in a filled water container.

## Reuse

| Part | Reuse? | Why |
|---|---|---|
| FFC cable, speaker, bezel, light guide, glass, housing | yes | that's what the board must fit |
| J9 speaker plug | yes | or a connector that fits it |
| U14 (`T3018`), U18 (optical sensor) | maybe | only once identified as standard parts |
| 135 LEDs | no | new ones cost fractions of a cent. Match package and colour under the microscope instead. |
| CC3220, CC2640R2F, crystals, passives | no | no use with an ESP32 |
| J8 connector | **not until our board works** | buy a new one. The old board stays intact: it's the reference for mapping, and the recovery path if Anova ever sends an image. |

## Budget
Estimates (`guess`): typical JLCPCB/LCSC prices and shipping to Belgium, not quoted. The bench kit already ordered
(DSLogic, LaunchPad, spare flash, breakouts) isn't counted.

| Item | € |
|---|---|
| J8 tap: second 30-pin FFC + jumper wires (the FPC-30P breakout 2-pack is already ordered) | 10 |
| 2x ESP32-S3 dev kit | 25 |
| High-speed USB isolator for the logic analyser (cheap ADuM3160 isolators are full-speed only) | 50 |
| Probe thermometer (the working Anova in the same bath is the real reference) | 15 |
| Spin 1: works but isn't the final shape, 2-layer, partly hand-soldered | 40-60 |
| Spin 2: final shape, 4-layer, machine-assembled, 5 PCBs / 2 populated | 100-150 |
| Spin 3: fixes | 100-150 |
| Consumables, screws, standoffs | 20 |
| **Total** | **≈ 360-480** |

So €500 buys many tries on the dev-kit level but only 2-3 real boards. Only order a final-shape board once J8 and the
LED matrix work on the bench.

## Risks
- **Mechanics:** LED positions must match the light guide to a fraction of a mm. They come from a scan of the LED side
  (flatbed at 1200 dpi, calipers, microscope). That needs the board off the bezel: warm the 6 heat stakes (community
  method, [disassembly.md](hardware/disassembly.md)). The stakes probably won't survive many cycles, so plan screws or
  clips for the new board.
- **RF:** the board sits against a steel tube. Keep the module antenna where the original antennas are.
- **Sensor calibration (if the power board is "dumb"):** a two-point check (ice water, boiling water) plus a
  side-by-side run with the working unit.
- **Time:** this takes months of evenings. Time runs out before money does.

## Making the top for our own board
The "top" is the assembly the bezel screws hold in the head: the black glass (glued on), the white bezel and light
guide, and the main board heat-staked behind it. In the head it meets four threaded inserts in the corner bosses, a
foam gasket on the rim, the FFC's free end, the speaker plug, and the mains wiring below the power board's top edge
([photos of 2026-11-21](photos.md#2026-11-21-the-head-open-and-empty-the-top-assembly-out)). Proposed in
; raptox decides.

**Fit comes from copying, not from modelling.** The surest fit is the part Anova already made:
- **Route C keeps the original bezel, light guide and glass.** Our board copies MAIN_V2.0's outline, the two
  locating-pin holes and the six heat-stake holes ([main-board.md](hardware/main-board.md#mechanics), measured on the
  mosaic, `likely` ±0.5 %), so it drops onto the bezel where the old board sat. Nothing printed touches the housing.
  The cost: the original board comes off the bezel (heat stakes, decision in the journal first), or a second bezel
  from a donor unit (route D's bonus).
- **The printer makes everything that only has to fit our own parts:** the C0 carrier for a dev kit behind the
  bezel, jigs, a bench stand for the head, probe holders. Loose tolerances, cheap iterations.
- **A printed top of our own** (glass, bezel and board all new, the original top kept intact) is the hard case. It
  is possible, but the fit then has to be measured, and the part has to survive heat, steam and splashes.

**If the top itself is printed, how to make it fit:**
1. **One datum: the four inserts.** Every other dimension hangs on their centres: caliper the centre distances
   (both sides and both diagonals, which also shows whether the pattern is square), the insert bore and the screw
   thread (take one of the white screws to the caliper, RS-0068). The outline is placed relative to them, never
   measured on its own.
2. **The rim outline, three ways from cheap to exact:**
   - a **rubbing**: paper over the rim, pencil along the edge and over the four holes, then photographed flat with a
     ruler in the plane and corrected for perspective (OpenCV, as for the stitches): about ±0.3 mm;
   - the **original glass and bezel on a flatbed scanner** at 600-1200 dpi (the outline exactly as Anova cut it;
     the board side needs a scanner with depth of field, a CCD one, not CIS);
   - the **CNC as a measuring machine**: the camera on the CNC jogged to each corner and hole, the coordinates read
     off; only through PCBoardNav. **Its accuracy is not measured yet**: a 3018-Pro, GRBL 1.1f,
     open-loop steppers, 800 steps/mm; X checked once over 10 mm with a ruler, Y never; at the microscope's zoom X
     gave 600 px per 2 mm and Y 617, a 3 % gap that is either Y's scale or the camera (PCBoardNav's bench notes).
     Expect about ±0.1 mm over 100 mm once checked (`guess` for this machine class). The check: a steel rule
     under the camera, its lines read at 0, 50 and 100 mm in X and in Y, every point approached from the same side
     (backlash), each move done three times (repeatability). Only flat parts fit under the gantry (the bezel, the
     glass, a rubbing, test plates, boards), never the cooker's head itself.
   - a **touch probe on the CNC** instead of the camera: GRBL 1.1f has a probe input and G38.2. A continuity probe
     needs a conductive part, so plastic needs a switch-type (3D touch) probe. It pushes on the part and the light
     frame flexes, where the camera touches nothing; PCBoardNav has no probing moves, so it would be a request to
     that app. The camera route needs no new hardware.
3. **Heights**, with the caliper's depth rod: the inserts' tops against the rim, the gasket's height free and
   compressed, the speaker's top, the power board's top edge and the FFC's exit. They decide how deep the top may
   reach into the head.
4. **Model parametrically, from code**, like the KiCad boards (`hardware/<board>/` is generated): build123d or
   CadQuery in Python, with the outline from step 2 as a DXF and every clearance a named parameter. **The board
   outline and the top's pocket come from one sketch**, exported to KiCad as `Edge.Cuts`, so the two cannot
   disagree; KiCad's STEP export goes back into the model to check the parts' clearance.
5. **Iterate on thin test pieces before the real part:** a 1 mm plate with the outline and the four holes (a quarter
   of an hour), then a ring with the gasket face, then the full top. Each round fixes one thing. Calibrate the printer
   first with a coupon in the chosen material: holes print undersize, the first layer spreads, and every material
   shrinks by its own amount.
6. **Material: measure the heat first, then choose from what is on order** (Prusament PETG in several colours,
   PETG-CF, PA11, PA11-CF, TPU 95A; ordered 2026-11-18 with the printer, a Prusa CORE One L+ INDX, Raptox-Stock
   OR-0008). How hot the top gets is unknown: the bath reaches about 90 °C, but the top sits above the clamp, behind
   the glass. **Measure it on the working unit from the outside only** (rule 2): the IR thermometers (RS-0062,
   RS-0064) on the glass and the head, the thermocouple (RS-0217) taped to the head, a long cook at the top
   temperature with the lid off the pot. Heat-deflection figures (Prusa's published values, `likely`, not checked
   against the data sheets): PETG about 68-74 °C; PA11 about 59 °C as printed and about 122 °C annealed (annealing
   shrinks the part, so the test plates must be annealed too); PA11-CF about 150 °C (1.8 MPa) to 190 °C (0.45 MPa).
   - **PETG**: test plates, jigs, the carrier, the stand; the top itself too if the measured heat stays well below
     about 60 °C.
   - **PA11-CF**: the top if it gets hotter. Stiff and low-warp, which helps the fit. Needs a hardened nozzle
     (`unverified` for the INDX tools) and dry filament. Its carbon may load the Wi-Fi antenna and the touch pads
     (`guess`): keep it away from the antenna zone, or compare Wi-Fi signal strength with a test plate over it.
   - **PA11**: clips, snap fits, screw bosses (tough). Dry it before printing; no filament dryer in stock yet.
   - **TPU 95A**: the rim gasket, if the original foam one doesn't survive, and strain reliefs.
   - **ASA**: not needed unless the measurement rules out PETG and nylon is unwanted.
   A printed wall is not watertight by default: solid sealing faces (100 % infill there, extra perimeters) and the
   gasket do the sealing.
7. **What the top must keep:** the glass flat against the touch pads (capacitive touch reads through a fixed glass
   thickness, [disassembly.md](hardware/disassembly.md#glass-removal)), the LED positions under the light guide (the
   LED-side scan in Risks above), J8 where the FFC reaches (its length and contact side are fixed; a standard 30-way
   0.5 mm FFC of another length is cheap, but type A and type B are not interchangeable), the speaker plug within
   reach, and the mains wiring covered. The top is never put on or off while the cooker is on mains.

## Groundwork (shared by all routes, part of Phase 2)
In this order, mains-free first:
1. **Identify U2 and the other power-board ICs:** microscope survey set 3 ([photos.md](photos.md)), power board
   unplugged and out of the tube.
2. **Map J8 by continuity, unpowered, on the dead unit:** which pins are GND and supply, and which go to U2, the relay
   driver, the sensor divider, U14 and U1/U7. This answers most of question 1 without any mains.
3. **Rails:** [bench-setup.md](hardware/bench-setup.md) steps 1a and 1b.
4. **Only if 1-3 leave the protocol open:** log J8 with the DSLogic while the power board runs on mains. That means
   the head is open on mains, which [disassembly.md](hardware/disassembly.md#safety) currently forbids. So it needs:
   - its own decision, recorded before it's done
   - the isolation check from bench-setup step 1a
   - an isolated logic analyser
   - its own safety procedure, written before it's done

   Try it on the dead unit's power board first. Opening the **working** unit means cutting its glass free: raptox's call,
   and only if the dead unit can't answer the question.

## Sources
- Espressif ESP32-S3 datasheet (touch channels, Wi-Fi current):
  <https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf>
- TI TPS3431 programmable watchdog timer: <https://www.ti.com/lit/ds/symlink/tps3431.pdf>
- ISSI IS31FL3731, Holtek HT16K33, ADI MAX98357A datasheets (by name; not re-checked for this note).
- CC3220 development mode with TI's test certificate: see the sources in [bench-setup.md](hardware/bench-setup.md#sources).
