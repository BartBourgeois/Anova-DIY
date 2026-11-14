# Roadmap: two cases

There are two ways this can go, and both are planned. Which one we're on depends on one thing: whether Anova helps.
Nothing waits for that answer; the work continues on both tracks until it's clear.

> **The point of no return.** Even if Anova comes over the bridge, there is a point past which I'm too invested to
> back down. The investment is made, the journey has started. Help would change the *repair* part; it wouldn't end the
> project.
>
> raptox

> **6 November 2026: the cooker cooks again**, on case 2's track, nine days after the update stalled (stage 5
> below; [the story](../blog/posts/2026-11-06-it-cooks-again.md)). The repair part is done. The rest of the roadmap goes on, because of the
> point of no return.

Status: `todo` · `now` · `done` · `n/a`. Every step links to its evidence when it's done. The dated record is the
[timeline](timeline.md).

## Case 1: Anova helps

Unlikely, judging by the answers so far ([incident](incident.md); the exchange itself, word for word:
[correspondence](correspondence.md)), but it's the cheap outcome, so it gets a full plan and full documentation if it
happens. Since 6 November the cooker cooks without it. Anova's answer to the message of 1 November came on
2 November: a procedure on the touch panel to reload the firmware, which doesn't address the four requests. The
panel had been dark since the update. On 6 November the owner told support how the cooker was fixed and offered the
ticket for closing; on 8 November Anova forwarded the account to its engineering and development teams.

| Step | What | Status |
|---|---|---|
| 1.1 | Anova provides one of the four things asked on 2026-11-01: a firmware image with recovery instructions, a replacement main board at the owner's cost, a mail-in reflash, or a refurbished unit. Dated and documented, whatever the form. | n/a: none came; the ticket was offered for closing on 2026-11-06, the cooker cooking through case 2 ([correspondence](correspondence.md), messages 9 and 10) |
| 1.2 | If an image: verify it (hashes, signature chain as far as TI's tooling shows it), and **back up the unit's own flash first**, read twice, hashed. The ground rule doesn't bend for an official image. | todo |
| 1.3 | Apply the official procedure exactly as given, on a bench supply, never interrupting power. Log every step and every output. | todo |
| 1.4 | The cooker cooks. Side-by-side run with the working unit. | todo |
| 1.5 | Publish the procedure here, so every other owner with a dead Pro can follow it. Credit Anova, in full. | todo |
| 1.6 | The repair part of the project ends. Case 2 continues as a side project, at whatever pace, because of the point of no return. | todo |

## Case 2: no help. We do it ourselves, all the way

Every step below is a real step, and some of them are insane for a kitchen appliance. That's the point.

### Stage 0: now, with nothing but a multimeter and a phone
| Step | What | What it tells us | Status |
|---|---|---|---|
| 0.1 | Bluetooth and Wi-Fi scan of the dead unit, closed, plugged in. Does anything on the board still talk? | which chip is alive | **done**, 4 Nov: nothing on Bluetooth or Wi-Fi, while the working unit shows up in the same scan ([timeline](timeline.md)) |
| 0.2 | Continuity map, unpowered: ground, rails, the 30-pin connector, the debug footprints, every test point. The first [nets table](hardware/bench-setup.md). | what crosses the cable, where the debug pins are | **now**: the 30-pin connector's supply and ground, 4 Nov ([J8](hardware/j8.md)); the flash bus end to end, the Wi-Fi chip's three boot straps with their pull-downs, the serial header J29, nine bare pads and eleven test points, 5 Nov ([test points](hardware/testpoints.md), [nets](hardware/nets.md)) |
| 0.3 | The working unit from outside: power-on sequence with a stopwatch, current draw, behaviour of every key. | what "normal" looks like | todo |
| 0.4 | Desk research: how Anova's updates travel, what TI documents about interrupted updates, every datasheet. | the shape of the problem | **now**: the Anova app and the Pro's update package examined, 5 Nov: the cooker fetches its update itself, and the package writes both chips and the radio's service pack ([timeline](timeline.md)) |

### Stage 1: eyes. The microscope
| Step | What | What it tells us | Status |
|---|---|---|---|
| 1.1 | Stitched, measurable mosaics of every board side, shot tile by tile under a 4K-capable digital microscope ([protocol](photos.md)). | the reference images for everything else | **started**: main board, component side, 3 Nov ([photo log](photos.md#2026-11-03-microscope-mosaic-main-board-component-side)) |
| 1.2 | Close-ups of every marking under two light angles, including the ones nobody could read so far. | every chip identified | **started**: the main board's markings read from the mosaic; U17 identified as the 3.3 V regulator, 4 Nov ([nets](hardware/nets.md#supply)); U13, U14, U2 still unidentified |
| 1.3 | **Transillumination**: the bare board on a light panel, photographed from above. Inner copper shows as shadow. Layer count without an X-ray. | the board's layer count, inner traces | todo |
| 1.4 | The power board, out of the tube, both sides. Is its biggest chip a microcontroller? | whether a second brain is involved | todo |
| 1.5 | **Reverse-engineer the schematics**, net by net, from the mosaics, the transillumination shots and the continuity map, drawn in KiCad. Anova's schematics are confidential in the FCC filing; ours will be the public ones. | the wiring of the whole thing | **started**: the first nets from the mosaic's top layer, 4 Nov; the flash, boot-strap and serial-header nets measured, 5 Nov ([nets](hardware/nets.md)) |

### Stage 2: hands and power
| Step | What | What it tells us | Status |
|---|---|---|---|
| 2.1 | One careful measurement of the supply arriving over the 30-pin cable, isolation check first ([procedure](hardware/bench-setup.md)). | whether the power board even delivers | **done**, 4 Nov: 5.01 V on the supply pins with the main board unplugged ([J8](hardware/j8.md)); under load still to measure |
| 2.2 | The main board alone on a current-limited bench supply, through a break-out board on the flat cable. Idle current as a diagnostic. | ROM wait vs. app running vs. short | **done**, 6 Nov: fed through the break-out at 5 V, a few mA with the Wi-Fi chip held in reset; the repaired firmware's first start needs about 1 A in bursts ([timeline](timeline.md)) |
| 2.3 | Solder a header onto the empty UART footprint and a DIP switch onto the empty boot-strap pads. | access to the chip's boot modes | **done with probes**, 6 Nov: the boot modes reached with spring probes on the strap pads and in the serial holes ([repair handbook](recovery/index.md)). Nothing gets soldered onto this unit (7 Nov); a development unit, if one is ever set up, gets the header and the switch |

### Stage 3: ears. Logic analyser and UART
| Step | What | What it tells us | Status |
|---|---|---|---|
| 3.1 | Boot log on the UART at power-up, every baud rate tried, a logic analyser to find the right one. | how far the chip gets | todo |
| 3.2 | Logic analyser on the power-up sequence: reset, boot straps, crystals, the first flash access. | where the boot stops | todo |
| 3.3 | The SPI flash bus at boot, decoded: which addresses are read, in what order. | the chip's view of its own flash | todo |
| 3.4 | The link between the Wi-Fi chip and the Bluetooth chip, found and decoded. | how the two brains talk | **started**: the firmware shows a serial link between the two chips, 5 Nov; its pins are next ([timeline](timeline.md)) |
| 3.5 | The 30-pin cable, sniffed through a pass-through tap, first with the main board alone, later with the power board live under its own safety procedure. | the protocol to the power board | todo |

### Stage 4: the flash
| Step | What | What it tells us | Status |
|---|---|---|---|
| 4.1 | Practise on a spare chip: clip, programmer, read twice, compare hashes. | that the routine is safe | **done**, 6 Nov: a spare chip written and read back on the reader; the development board's flash read in circuit, matching its boot-loader read ([flash backup handbook](flashbackup/index.md)) |
| 4.2 | **Dump the unit's flash** with a clip on the flash chip while the Wi-Fi chip is held in reset, before the board ever boots normally (desoldering the flash is the fallback; the chip's own boot loader was the plan until 6 Nov, when a development board set up in production mode showed that its boot loader refuses to read the flash), read twice, hashed, archived ([handbook](recovery/index.md)). The most important single step in this plan, and the backup every later write depends on. | the state the update left behind | **done**, 6 Nov: two identical reads by clip, a copy off the bench PC ([flash backup, page 8](flashbackup/08-cooker-backup.md)) |
| 4.3 | Structural analysis of the dump: file system layout, what's readable, what looks half-written. | which file the update was writing | **done**, 6 Nov: the file system intact, the update half done in a state the chip rolls back ([page 9](flashbackup/09-cooker-analysis.md)) |
| 4.4 | A known-good development board of the same Wi-Fi chip: rehearse every boot mode, every write, and an interrupted update on purpose. | what "dead" looks like when you cause it yourself | under way: the board arrived 5 Nov; the flash read, the maker's signed firmware installed and run offline, a one-file write, and production mode (6 Nov) rehearsed. Not yet: the interrupted update, the factory restore, the undo |
| 4.5 | The Bluetooth chip over its debug interface: read its configuration first, then its flash, if it isn't locked. | whether the Bluetooth chip is the victim | **done**, 6 Nov: its debug port open, two identical reads, the firmware the cooker lists as installed: not the victim ([page 10](flashbackup/10-cooker-u7.md)) |

### Stage 5: the repair
| Step | What | Status |
|---|---|---|
| 5.1 | Decide, on evidence, which of the [three explanations](firmware/recovery-strategy.md#2-why-is-the-unit-completely-dead-hypotheses) it is. | **done**, 6 Nov: none of the three as framed. The Wi-Fi chip had **locked itself**, its security-alert counter at the limit. What raised the alerts is open ([timeline](timeline.md)) |
| 5.2 | Replace the one broken file through the boot loader with the maker's signed file, which keeps the unit's network address and cloud identity. Targeted repair of the file system, if that's what broke. Reflash of the Bluetooth chip, if that's the victim. Factory restore via the boot straps last: it erases that identity. Each one only after the backup. Since 6 Nov: on a production-mode chip the boot loader refuses the one-file write, so it comes down to a full image (with the unit's own readable files carried over from the backup) or the factory restore. | **done**, 6 Nov: the full image, the current firmware with the unit's own files carried over, through the boot loader; the lock cleared |
| 5.3 | Own firmware on the original Wi-Fi chip, if the hardware is fine but the original image can't be had. | n/a for the repair: the original image could be had |
| 5.4 | The cooker cooks. Side-by-side run with the working unit. Procedure published. | **done** in part, 6 Nov: **it cooks**, 54 °C held for ten minutes, on point; the route published ([the story](../blog/posts/2026-11-06-it-cooks-again.md)). The side-by-side run is todo |

### Stage 6: if the board can't be fixed, we build our own
This unit's board was fixed (6 Nov). The stage stays on the list, for the point of no return and for every unit
whose board can't be. Since 7 November it also holds the other way to own the brain: our own firmware on the
original board (6.0).

| Step | What | Status |
|---|---|---|
| 6.0 | **Our own firmware for the original Wi-Fi chip**: cloud-free, controlled from home automation over the home network; the Bluetooth chip keeps its firmware and the cooking hardware it drives. A separate project; the hardware and protocol findings stay documented here. | **now**, 7 Nov: decided. First the link between the two chips, captured on the serial header while the cooker runs its own firmware ([timeline](timeline.md)) |
| 6.1 | **Zero-spin prototype**: an ESP32 development board on the break-out, wired to the 30-pin cable and the original speaker, no custom PCB. Headless: controlled from home automation. Hardware watchdog in the heater path from day one. | todo |
| 6.2 | Protocol or raw signals to the power board understood and documented, from the sniffing above. PID tuned against the working unit in the same water bath. | todo |
| 6.3 | **Spin 1**: a real PCB that fits the bezel, hand-assembled, works but isn't pretty. | todo |
| 6.4 | **Spin 2 and 3**: machine-assembled, final shape, screws instead of heat stakes. | todo |
| 6.5 | Stretch goal: the display. All 135 LEDs behind the original light guide, touch keys through the original glass. The scan of the LED side comes from un-staking the old board. | todo |
| 6.6 | Safety sign-off before any unattended cook: watchdog, thermal cut-off, over-temperature latch, closed head, RCD. | todo |

### Stage 7: beyond
| Step | What | Status |
|---|---|---|
| 7.1 | Diagnostics software: a console for the UART, a flash-dump parser, a local client for the working unit's Bluetooth and Wi-Fi. | todo |
| 7.2 | The 30-pin interface documented well enough that someone else can build a brain for this cooker. | todo |
| 7.3 | Whatever else turns out to be necessary. The list grows. | todo |

## What's spent
Tools so far: about €545 ([list](hardware/bench-setup.md#spent-so-far-2026-11-02)). The cooker cost about $450. That
ratio is not an argument against anything.
