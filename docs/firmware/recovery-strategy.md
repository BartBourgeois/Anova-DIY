# Recovery strategy (DRAFT)

> Status: **hypotheses based on FCC photos + TI documentation. Nothing measured yet.**
> Golden rule: **dump before you write.** See the ground rules in [the timeline](../timeline.md).

## 1. What the hardware implies

### CC3220S (Wi-Fi MCU, main board)
- The **CC3220S has no internal flash.** At boot the ROM bootloader authenticates and decrypts the application image
  (`/sys/mcuimg.bin`) from the **external SPI serial flash** and copies it to SRAM. The same flash holds:
  - the NWP service pack
  - certificates
  - the "secure" filesystem and user files

  Sources: TI E2E answers and the CC3220 datasheet (see [references](../references.md)).
- **Secure device:** secure files are AES-encrypted with **device-unique keys** derived from a per-chip hardware secret,
  and the filesystem allocation table (FAT) is encrypted too. Consequences:
  - A raw dump of the **bricked unit's own flash** is a perfect *backup*. Writing it back restores exactly the current state.
  - A dump from the **working second unit cannot simply be cloned** onto the bricked unit. The keys differ, so the files
    won't decrypt. (TI E2E statements. Confidence: likely.)
  - Reading the dump with an SPI programmer (SOIC clip) works regardless. *Interpreting* it is limited to the
    unencrypted metadata.
  - **Production mode disconnects JTAG/SWD** (TI E2E). Only development-mode images, which are bound to the device MAC,
    allow debugging. So the CC3220 on this unit can't be JTAG-debugged.
  - The ROM bootloader still accepts a **complete new image** via UARTLOAD (the previous image is cleared). The chip is not
    locked, but the image's mcuimg must be signed by a trusted cert. Details: [bench-setup.md](../hardware/bench-setup.md).
- **Boot modes via SOP[2:0]** (TI SWAS035C table 9-6, confirmed from datasheet):

  | Mode | SOP2 | SOP1 | SOP0 | Use |
  |---|---|---|---|---|
  | FUNCTIONAL_4WJ | 0 | 0 | 0 | normal boot + 4-wire JTAG |
  | FUNCTIONAL_2WJ | 0 | 0 | 1 | normal boot + 2-wire SWD |
  | UARTLOAD_FUNCTIONAL_4WJ | 0 | 1 | 0 | UART break on RX: load mode, otherwise normal boot |
  | **UARTLOAD** | **1** | 0 | 0 | flash/SRAM programming over UART (Uniflash). Waits for UART indefinitely. |
  | **RET_FACTORY_IMAGE** | 0 | **1** | **1** | on reset, the bootloader **restores the factory default image** |

  The datasheet recommends 100 k pull resistors on SOP0/SOP1 and 2.7 k on SOP2. SOP0/SOP1 are dedicated pins.
  **Hypothesis:** the J14 DIP footprint drives some of these straps, and J29 exposes UART0. On raptox's production unit
  **neither is fitted** (empty footprint/holes). Fitting a 3-pin header on J29 and wires or a switch on the J14 pads is reversible.

### The serial flash (confirmed on raptox's unit)
- **U15/U16 = XMC XM25QH64AHIG**: 64 Mbit = **8 MiB** SPI NOR, 2.7-3.6 V, **SOP-8 208 mil (wide body)**.
  JEDEC ID `20 70 17` (per the Linux spi-nor patch). Date code 1830.
- Reading it with a programmer:
  - Use a SOIC-8 clip that fits **208 mil** (many cheap clips are 150 mil only).
  - Use a **3.3 V** programmer. A stock CH341A outputs 5 V on its data lines, so it needs the 3.3 V mod or a 3.3 V adapter.
  - Check whether flashrom auto-detects the ID. If not, look the chip up in flashrom's list or pick a compatible
    8 MiB definition for a **read only**.
- **In-circuit caveat:** the clip powers the whole 3.3 V net, so the CC3220 may wake up and drive the SPI bus.
  Hold the CC3220 in reset (nRESET low) during the read, or lift pin 8 / desolder the chip. Read **at least twice**
  and compare SHA-256 before trusting the dump.
- **OTA safety net:** a CC3220 OTA leaves the new image *pending commit*. A reset before commit should **roll back** to the
  previous (failsafe) image. The bootloader can also arm a watchdog for uncommitted images. TI E2E threads also report
  update functionality that **breaks when an update is interrupted at certain points**, so the safety net is not absolute.

### CC2640R2F (BLE MCU, main board)
- Internal 128 KB flash. The ROM serial bootloader (UART/SPI) is enabled and configured in **CCFG** (bootloader-enable
  byte `0xC5`, backdoor pin + level). An invalid image can also drop into the bootloader. cJTAG debug through an XDS110
  (likely via one of the Tag-Connect footprints).
- **Risk:** CCFG can **lock the debug interface**. If Anova locked it, JTAG reads fail and only the serial bootloader
  (if enabled) or a mass erase remains, and a mass erase destroys the image. Check this before trying anything invasive.
- Fact sources: TI SWRA466 (CC26xx serial bootloader), TI E2E. Confidence: likely. Verify in TRM SWCU117.

### Power board
- Unknown whether it contains an MCU (U2 is the candidate). If it does, it may also receive OTA updates relayed by the main board.

## 2. Why is the unit *completely* dead? (hypotheses)

**The central puzzle.** The CC3220's OTA design keeps the previous image and rolls back when the new one isn't
committed (TI docs, `likely`, sources in [references.md](../references.md)). That mechanism sits on this very board,
with 8 MiB of flash to hold both images. So a unit that is *completely* dead after an interrupted update is itself a
piece of evidence. There are only three ways to get here:
- **(a)** Anova's firmware doesn't use the failsafe mechanism, or uses it in a way that an interruption at this point
  defeats (H1).
- **(b)** The update touched something the mechanism doesn't cover: the CC2640R2F, a power-board MCU, the file-system
  metadata, the service pack (H1, H2, H3).
- **(c)** The failure isn't in the CC3220 at all (H4, H5).

The flash dump and the boot log separate (a) from (b). The rails and a radio scan separate (c) from both. Whichever
it is, the answer and its evidence go into the README.

| # | Hypothesis | Fits "no beep, no LEDs"? | How to test |
|---|---|---|---|
| H1 | CC3220 filesystem or boot metadata corrupted (update interrupted in a non-failsafe phase, e.g. service pack or FS metadata). The ROM bootloader can't start any app image. | yes, if the CC3220 drives the UI | UART boot log at SOP=000; current draw; Wi-Fi AP beacons; flash dump analysis |
| H2 | The update targeted the **CC2640R2F** (relayed by the CC3220) and left it half-written. The UI depends on it. | yes, if the CC2640 drives the UI or gates power-up | cJTAG connect; check whether the BLE device advertises (nRF Connect) |
| H3 | A **power-board MCU** was being updated | possible | identify U2; probe the J8 FFC traffic |
| H4 | Coincidental hardware failure: AC/DC module, F1 fuse, regulator | yes | measure rails at J8 / TPs (safe setup) |
| H5 | The CC3220 sits in a ROM wait state (e.g. UARTLOAD because a strap is wrong) | yes | measure SOP pins at reset |

Quick non-invasive checks first, with the unit closed and plugged in normally:
- Does any Wi-Fi AP or BLE advertisement appear (phone scan)?
- Is there any current draw beyond the idle SMPS?

## 3. Ordered plan (each step read-only unless marked WRITE)
1. **Photograph** both sides of raptox's main and power boards at high resolution. Read all chip markings, especially the
   U15/U16 flash part number and the power-board ICs. Compare revisions with the FCC photos.
   *Main board component side: done 2026-11-01 (flash = XMC XM25QH64AHIG; same PCB layout as the FCC sample; DIP switch
   and J29 header not fitted). Still to do: power board, and the main board LED side if ever needed.*
2. **Rails:** see [bench-setup.md](../hardware/bench-setup.md). One careful in-situ measurement of the supply arriving
   at main-board J8 (step 1a: main-board side only, battery meter, isolation check first), then bench supply only.
   Measure the 3.3 V at the MCUs on the bench. **Power-board rails are never probed while plugged in.** Comparing with
   the working unit means opening it: a separate decision ([plan B](../plan-b-custom-mainboard.md), groundwork step 4).
3. **Map debug interfaces:**
   - DIP J14 positions: record them, then trace continuity to the CC3220 SOP0/1/2.
   - J29 pins to CC3220 UART0, nRESET and SOP2.
   - J37/J38 pads to JTAG/SWD (CC3220) and cJTAG (CC2640R2F).
4. **Observe the boot:** logic analyser / UART on J29 and on the CC3220 UART pins at power-up (SOP=000). Note any NWP/ROM output.
5. **Dump the CC3220 serial flash** with the CC3220 held in reset (or the chip lifted), using a SOIC-8 clip and a
   3.3 V-safe SPI programmer (flashrom, CH341A **with a 3.3 V mod**, or similar). Read at least twice, compare
   SHA-256 and archive. Optionally also dump the working unit's flash for *structural* comparison only (never write it
   anywhere). That means opening the working unit and powering its 3.3 V net through the clip, with its CC3220 held in
   reset: raptox's call, last resort.
6. **Try to read the CC2640R2F** via cJTAG/XDS110 (or the ROM bootloader). Archive the dump, CCFG included.
7. **Analyse:** SimpleLink FS layout (superblock, file entries, which file was being written, failsafe copies),
   compare with the working unit's layout, and identify the update target.
8. **Recovery options**, in order of invasiveness. **Each is a WRITE and needs a verified backup:**
   - a. **RET_FACTORY_IMAGE** (SOP 0/1/1 + reset). Only useful if Anova programmed a factory image. Restores the
     factory app/SP and possibly erases user data/provisioning. Afterwards the app may re-offer the update.
     Caveats (likely, from TI docs; Anova's configuration unknown):
     - It only covers the CC3220 serial flash. If the failed update targeted the CC2640R2F or a power-board MCU
       (H2/H3), that chip stays broken.
     - It can't work if the flash structures it relies on are the damaged part (H1).
     - Run it on the bench supply and **never interrupt power while it runs**: that is the same failure mode as the OTA.
     - With the verified dump, a failed attempt can be undone by writing the dump back with the SPI programmer
       (same chip, so the device keys match). Without the dump it can't.
   - b. **Restore the unit's own earlier state** from a dump, if one ever existed (it doesn't yet), or roll back
     filesystem failsafe copies by targeted repair (research needed).
   - c. **UARTLOAD + Uniflash** with a vendor `.sli` image. This needs Anova's signed image (keep asking Anova; see the incident).
   - d. **CC2640R2F reflash** via cJTAG/bootloader, if H2 is confirmed and an image is obtainable.
   - e. Last resort: replace the firmware with community/custom firmware. This is a big project (UI, control loop,
     power-board protocol) and needs a full understanding of the J8 interface. Evaluated in
     [plan-b-custom-mainboard.md](../plan-b-custom-mainboard.md): own CC3220 firmware, an ESP32 transplant, or a new board.

## 4. Tools likely needed
- Logic analyser (8 ch), USB-UART 3.3 V, multimeter, current-limited bench supply.
- SOIC-8 test clip that fits **208 mil** + SPI programmer at **3.3 V**.
- A 1x3 2.54 mm pin header for J29, and thin wire for the J14 pads.
- TI XDS110 (e.g. from a LaunchPad) + Tag-Connect TC2030-CTX-NL cable.
- TI Uniflash, the SimpleLink CC32xx SDK (Image Creator) and nRF Connect (BLE scan).
