# Timeline

What happened, in order, with links to the evidence. The narrative is in the [blog](../blog/index.md).

## How the work is done
1. **Back up before any write.** Nothing is written to any flash until a dump exists that was read twice with the
   same hash.
2. **The working second unit is read-only.** It's the reference, not a donor.
3. **Mains.** The power board is never probed while plugged in. Logic runs from a bench supply.
4. **Every claim carries a confidence** (`confirmed` / `likely` / `guess`) **and a source.**
5. **No firmware is distributed**, ever, in any form.

## 2026

| Date | What |
|---|---|
| 28 or 29 Oct | A firmware update started from the Anova app stalls at 75 % and stays there overnight. |
| 29 Oct | After a power cycle the unit is dead: no beep, no display, no LEDs. Support ticket opened. Advice: leave it plugged in overnight. |
| 30 Oct | Still dead. |
| 1 Nov | Anova: out of warranty, 10 % off a new unit. Four things asked in return: a firmware image with recovery instructions, a replacement main board at the owner's cost, a mail-in reflash, or a refurbished unit. Awaiting a reply. [Incident](incident.md), [the exchange word for word](correspondence.md). |
| 1 Nov | Head opened, main board photographed. Chips identified: **U1 TI CC3220SM2A** (Wi-Fi MCU, no internal flash), **U15/U16 XMC XM25QH64A** (8 MiB SPI flash, the dump target), **U7 TI CC2640R2F** (BLE MCU). Same board layout as the 2018 FCC sample; the debug parts aren't fitted. [Main board](hardware/main-board.md). |
| 1 Nov | What the CC3220S security means: production mode disables JTAG, the file system is bound to the chip, the application image is signed. The working unit's flash can't be cloned; the chip's UART bootloader is still open. [Bench setup](hardware/bench-setup.md). |
| 1 Nov | Recovery order fixed: look, map, dump, analyse, and only then write. [Recovery strategy](firmware/recovery-strategy.md). |
| 1 Nov | Bench kit ordered: SOIC clip, logic analyser, CC3220S LaunchPad, spare flash chips, digital microscope, ESD kit, FPC break-out, ESP32 dev kits. [What's spent](hardware/bench-setup.md#spent-so-far-2026-11-02). |
| 1 Nov | Plan B evaluated: a replacement main board around an ESP32 if the original can't be fixed, a used donor board as a side route. [Plan B](plan-b-custom-mainboard.md). |
| 1 Nov | Decision: fix the original board if that can reasonably be done, otherwise build our own. Nothing waits on Anova. |
| 2 Nov | Working assumption: the power board is fine and the problem sits after the 30-pin cable. The test is one supply measurement at the connector. |
| 2 Nov | The central puzzle framed: the Wi-Fi chip's documented rollback mechanism sits on this very board, so a unit that is completely dead after an interrupted update is itself evidence. Three ways to get here. [Hypotheses](firmware/recovery-strategy.md#2-why-is-the-unit-completely-dead-hypotheses). |
| 2 Nov | Public repository and website live. Dual [roadmap](roadmap.md) published. |
| 3 Nov | Digital microscope on the bench. Its USB live view stops at 1920x1080; full-resolution shots only go to its memory card. [Microscope](microscope.md). |
| 3 Nov | The main board's component side stitched from 335 microscope frames at about 229 px/mm. Every reference designator is legible; the 30-pin connector's pin-1 and pin-30 marks found; positions of the fiducials, heat stakes and connectors measured, the start of a mechanical spec for a board of our own. [Main board](hardware/main-board.md), [photo log](photos.md#2026-11-03-microscope-mosaic-main-board-component-side). |
| 4 Nov | Schematic work started: the top-layer copper can be followed on the mosaic. The first nets: the Wi-Fi chip's four flash lines run through series resistors past four bare test pads. Two limits of the photos found: the boot-mode footprint J14 and the Wi-Fi chip's boot-mode pins both drop to vias, so they need the meter. [Nets](hardware/nets.md). |

## Corrections
Statements of substance about the cooker that were changed after publication, with the date. Wording and
housekeeping changes aren't listed.

| Date | Correction |
|---|---|
| 2 Nov | "Bricked by the update" was stated as fact. Changed to "died after an interrupted update": the update is the likely cause, not yet a measured one. The measurement that settles it is the first bench job. |
| 3 Nov | Three part readings from the phone photos corrected by the microscope mosaic: U13's second line is `838A` or `B38A` (not `638A`), U2 has 3 leads (not 5), and U6 is an empty footprint (not a fitted 6-lead part). |
