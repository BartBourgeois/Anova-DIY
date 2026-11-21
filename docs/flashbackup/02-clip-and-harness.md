# 2. The clip and the harness

One harness for every read: the SOIC-8 clip (KeeYees kit), its ribbon, and five jumper leads to the reader.
It's built and checked once, on the bench, with nothing powered. Then it moves unchanged from the practice chip to the
LaunchPad to the cooker.

## 2.1 Map the clip, unpowered (the meter's beeper)
The kit's clip ends in a ribbon to a small adapter board with eight pins, made for the CH341A's socket. Which
adapter pin is which jaw contact is **not assumed**: it is measured.

1. Open the clip. Beeper from **each jaw contact** to the adapter pins; write the table below. Pin 1 of the clip is
   usually the red wire of the ribbon (`unverified` for this kit).
2. Mark the clip's **pin-1 jaw** with a dot of paint or tape. On the chips it goes to pin 1 (the dot or the bevel of
   the package).
3. Check that **no two contacts ring together** (a pinched ribbon).

| Jaw contact (chip pin) | Signal | Adapter pin | Lead colour | To the reader |
|---|---|---|---|---|
| 1 | CS# | | orange | CS |
| 2 | DO | | green | MISO |
| 3 | WP# | | none (practice chip: to 3.3 V) | not connected on a board |
| 4 | GND | | grey | GND |
| 5 | DI | | blue | MOSI |
| 6 | CLK | | yellow | CLK |
| 7 | HOLD# | | none (practice chip: to 3.3 V) | not connected on a board |
| 8 | VCC | | red, taped off | **practice chip only** |

The colours are the drawings' ([Pi](../../images/diagrams/fb-reader-pi.png),
[Pico](../../images/diagrams/fb-reader-pico.png), [ESP32](../../images/diagrams/fb-reader-esp32.png), [FT232H](../../images/diagrams/fb-reader-ft232h.png)). Use them
on the real leads too, or label each lead with a flag of tape.

## 2.2 The harness
- Five female-female jumper leads from the adapter pins of CS, DO, GND, DI and CLK to the reader's pins, as short as
  the bench allows (about 20 cm or less).
- **The VCC lead**: one lead on adapter pin 8, its far end taped. It is connected **only** for the practice chip
  (2.3), to the reader's 3.3 V pin. On a board it stays taped: the board feeds its own flash, and a reader's 3.3 V
  would back-feed the board's regulator (on the cooker U17).
- WP# and HOLD#: no leads. On both boards pull-ups hold them high (cooker: HOLD# about 10 kΩ).

Check the finished harness end to end with the beeper: from each reader-end lead to its jaw contact, and no
continuity between neighbouring leads.

## 2.3 Smoke test on the loose practice chip (zero risk)
If a spare **W25Q64JVSSIQ** is at hand (DigiKey order of 2026-11-01, bench kit): the first read of the whole chain
happens on a chip that matters to nobody.

1. The chip on the bench, the clip on it, pin-1 jaw on the chip's pin 1 (the dot).
2. **This once, the VCC lead** goes to the reader's 3.3 V pin (Pi pin 17, Pico pin 36, ESP32 3V3, FT232H 3V). The
   chip has no board, so nothing else is fed. **And WP# (pin 3) and HOLD# (pin 7) to the same 3.3 V**: a loose chip
   has none of the board's pull-ups, and a floating HOLD# stops its output. The symptom: every ID byte reads `00`
   (no contact, as on 2026-11-06 before the chip was re-seated; or HOLD# floating). Measure pin 8 to pin 4 on
   the chip's legs: about 3.3 V.
3. `backup.py read ... --name practice --expect-chip W25Q64JV --expect-size 8388608` (the reader's `--programmer`
   from [page 1](01-readers.md)). Expected: flashrom names a W25Q64JV, two reads, **VERIFIED**. A new chip reads as
   all `FF`; the hash is the same each time.
4. Then the VCC lead is taped off again, **before** the harness goes near a board.

What this proves: the reader, flashrom, the harness, the clip's pin 1 and the tool, in one go. A failure here
costs nothing: an ID of all `00` means nothing comes back on DO (HOLD# floating, no power on the chip, or MISO and MOSI
swapped, the commonest wiring slip); all `FF` points at CS or MOSI.

## 2.4 Write a pattern, read it back (the practice chip only)
A blank chip reads as all `FF`: every bit 1, so a stuck data line could hide. A **pseudo-random pattern** (half the
bits 0, half 1) written and read back proves every bit of the path.

1. Only with the **loose practice chip** in the clip. With the ESP32: the write-capable build `esp32-rw`
   ([espserprog](../../tools/espserprog/README.md)); the others write as they are.
2. The rule-1 backup of the practice chip comes first: 2.3's verified pair (blank).
3. An 8 MiB pattern from a fixed seed (so it can be made again), its SHA-256 noted.
4. `flashrom -p <reader> -c <chip> -w pattern.bin`: flashrom reads, erases, writes and verifies by itself.
5. **Then the independent check:** `backup.py read ... --name practice_pattern`: two equal reads, and **their hash
   equals the pattern's**.
6. **The ESP32 back to the read-only build** (`espserprog-ro`) and `guard_test.py` passes, before the harness goes
   near a board.

No practice chip at hand: skip 2.3 and 2.4; [page 3](03-launchpad-qualify.md) is then the first read, on a board whose flash
already has a backup.

## 2.5 Photo
One photo of the finished harness with the colours visible, and one of the clip's pin-1 mark. Import them as every
photo (rule 6: byte-identical into `images/own/<date>/` under a name that says what they show, logged in
[photos.md](../photos.md)).
