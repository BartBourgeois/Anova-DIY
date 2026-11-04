# Roadmap: two cases

There are two ways this can go, and both are planned. Which one we're on depends on one thing: whether Anova helps.
Nothing waits for that answer; the work continues on both tracks until it's clear.

> **The point of no return.** Even if Anova comes over the bridge, there is a point past which I'm too invested to
> back down. The investment is made, the journey has started. Help would change the *repair* part; it wouldn't end the
> project.
>
> raptox

Status: `todo` · `now` · `done` · `n/a`. Every step links to its evidence when it's done. The dated record is the
[timeline](timeline.md).

## Case 1: Anova helps

Unlikely, judging by the answers so far ([incident](incident.md); the exchange itself, word for word:
[correspondence](correspondence.md)), but it's the cheap outcome, so it gets a full plan and full documentation if it
happens.

| Step | What | Status |
|---|---|---|
| 1.1 | Anova provides one of the four things asked on 2026-11-01: a firmware image with recovery instructions, a replacement main board at the owner's cost, a mail-in reflash, or a refurbished unit. Dated and documented, whatever the form. | todo |
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
| 0.1 | Bluetooth and Wi-Fi scan of the dead unit, closed, plugged in. Does anything on the board still talk? | which chip is alive | todo |
| 0.2 | Continuity map, unpowered: ground, rails, the 30-pin connector, the debug footprints, every test point. The first [nets table](hardware/bench-setup.md). | what crosses the cable, where the debug pins are | todo |
| 0.3 | The working unit from outside: power-on sequence with a stopwatch, current draw, behaviour of every key. | what "normal" looks like | todo |
| 0.4 | Desk research: how Anova's updates travel, what TI documents about interrupted updates, every datasheet. | the shape of the problem | now |

### Stage 1: eyes. The microscope
| Step | What | What it tells us | Status |
|---|---|---|---|
| 1.1 | Stitched, measurable mosaics of every board side, shot tile by tile under a 4K-capable digital microscope ([protocol](photos.md)). | the reference images for everything else | **started**: main board, component side, 3 Nov ([photo log](photos.md#2026-11-03-microscope-mosaic-main-board-component-side)) |
| 1.2 | Close-ups of every marking under two light angles, including the ones nobody could read so far. | every chip identified | **started**: the main board's markings read from the mosaic; U13, U14, U17, U2 still unidentified |
| 1.3 | **Transillumination**: the bare board on a light panel, photographed from above. Inner copper shows as shadow. Layer count without an X-ray. | the board's layer count, inner traces | todo |
| 1.4 | The power board, out of the tube, both sides. Is its biggest chip a microcontroller? | whether a second brain is involved | todo |
| 1.5 | **Reverse-engineer the schematics**, net by net, from the mosaics, the transillumination shots and the continuity map, drawn in KiCad. Anova's schematics are confidential in the FCC filing; ours will be the public ones. | the wiring of the whole thing | **started**: the first nets from the mosaic's top layer, 4 Nov ([nets](hardware/nets.md)) |

### Stage 2: hands and power
| Step | What | What it tells us | Status |
|---|---|---|---|
| 2.1 | One careful measurement of the supply arriving over the 30-pin cable, isolation check first ([procedure](hardware/bench-setup.md)). | whether the power board even delivers | todo |
| 2.2 | The main board alone on a current-limited bench supply, through a break-out board on the flat cable. Idle current as a diagnostic. | ROM wait vs. app running vs. short | todo |
| 2.3 | Solder a header onto the empty UART footprint and a DIP switch onto the empty boot-strap pads. | access to the chip's boot modes | todo |

### Stage 3: ears. Logic analyser and UART
| Step | What | What it tells us | Status |
|---|---|---|---|
| 3.1 | Boot log on the UART at power-up, every baud rate tried, a logic analyser to find the right one. | how far the chip gets | todo |
| 3.2 | Logic analyser on the power-up sequence: reset, boot straps, crystals, the first flash access. | where the boot stops | todo |
| 3.3 | The SPI flash bus at boot, decoded: which addresses are read, in what order. | the chip's view of its own flash | todo |
| 3.4 | The link between the Wi-Fi chip and the Bluetooth chip, found and decoded. | how the two brains talk | todo |
| 3.5 | The 30-pin cable, sniffed through a pass-through tap, first with the main board alone, later with the power board live under its own safety procedure. | the protocol to the power board | todo |

### Stage 4: the flash
| Step | What | What it tells us | Status |
|---|---|---|---|
| 4.1 | Practise on a spare chip: clip, programmer, read twice, compare hashes. | that the routine is safe | todo |
| 4.2 | **Dump the unit's flash**, chip held in reset, read twice, hashed, archived. The most important single step in this plan, and the backup every later write depends on. | the state the update left behind | todo |
| 4.3 | Structural analysis of the dump: file system layout, what's readable, what looks half-written. | which file the update was writing | todo |
| 4.4 | A known-good development board of the same Wi-Fi chip: rehearse every boot mode, every write, and an interrupted update on purpose. | what "dead" looks like when you cause it yourself | todo |
| 4.5 | The Bluetooth chip over its debug interface: read its configuration first, then its flash, if it isn't locked. | whether the Bluetooth chip is the victim | todo |

### Stage 5: the repair
| Step | What | Status |
|---|---|---|
| 5.1 | Decide, on evidence, which of the [three explanations](firmware/recovery-strategy.md#2-why-is-the-unit-completely-dead-hypotheses) it is. | todo |
| 5.2 | Factory restore via the boot straps, if the factory image is intact. Targeted repair of the file system, if that's what broke. Reflash of the Bluetooth chip, if that's the victim. Each one only after the backup. | todo |
| 5.3 | Own firmware on the original Wi-Fi chip, if the hardware is fine but the original image can't be had. | todo |
| 5.4 | The cooker cooks. Side-by-side run with the working unit. Procedure published. | todo |

### Stage 6: if the board can't be fixed, we build our own
| Step | What | Status |
|---|---|---|
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
