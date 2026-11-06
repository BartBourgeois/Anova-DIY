# j8probe

A listen-only probe for the cooker's two boards: an ESP32 on a J8 break-out records what every free pin does from
power-on (level, edges, frequency, pulse widths, voltages, serial bursts), and a second setup watches the main board's
other signs of life (3.3 V rail, flash chip select, J29, Bluetooth and Wi-Fi). Pin meanings go into
[j8.md](../../docs/hardware/j8.md).

**Read-only by construction.** Every channel pin is an input with both pulls off. The firmware holds no code that
drives one: a single function sets a channel's direction, always to input. The pulse counter only counts, and the UART
sniffer routes RX only. No command can change that. Prodding pins (driving them on purpose) is not in this firmware.

## When it may be connected
- **After the flash dump**. Until then it is built and tested on the desk only. The dump is taken
  through the CC3220's boot loader with the chip held in load mode ([handbook chapter 3](../../docs/recovery/03-bootloader-session.md));
  the `aux` listen on J29 is [chapter 4b](../../docs/recovery/04-boot-listen.md), the run after it.
- **Power board:** only after bench step 1a: isolation checked, the J8 supply measured, and every pin's idle voltage
  known ([bench setup](../../docs/hardware/bench-setup.md#step-1a-measure-the-j8-supply-in-the-cooker-one-time-with-care)).
  No ESP32 pin on anything above 3.3 V: such a pin needs a divider first. The tube in water, as in step 1a.
- **Never on the working unit.** It is the read-only reference.

## Hardware
- A classic ESP32 dev kit with an **ESP32-WROOM-32** module (not WROVER: its PSRAM takes GPIO 16/17).
- A **4.7 kΩ resistor in series on every signal line**. It keeps a wiring mistake from hurting either side, and it
  limits what an unexpected 5 V level can push into the ESP32.
- Dividers: **20 kΩ over 10 kΩ** for a 5 V supply (scale 3.0, up to 6 V reads 2.0 V), **10 kΩ over 10 kΩ** for the
  3.3 V rail (scale 2.0). The tap goes straight to the GPIO.
- Nothing on the flash clock: tens of MHz (`guess`), and a probe would load it. Chip select is slow enough.

## Setup `j8`: one ESP32 per break-out
The same harness fits break-out A (main board, 100 mm FFC) and break-out B (power board, the cooker's own FFC).
Header pin n = J8 pin n ([j8.md](../../docs/hardware/j8.md)).

| J8 / header pin | ESP32 GPIO | Kind | Through |
|---|---|---|---|
| 1-6 (supply) | 36 | analog, power channel | 20k/10k divider |
| 24 | 39 | analog | 4.7k |
| 25 | 34 | analog | 4.7k |
| 26 | 35 | analog | 4.7k |
| 7 | 32 | analog | 4.7k |
| 9 | 33 | analog | 4.7k |
| 8 | 4 | digital | 4.7k |
| 12 | 13 | digital | 4.7k |
| 13 | 16 | digital | 4.7k |
| 14 | 17 | digital | 4.7k |
| 15 | 18 | digital | 4.7k |
| 16 | 19 | digital | 4.7k |
| 18 | 21 | digital | 4.7k |
| 20 | 22 | digital | 4.7k |
| 21 | 23 | digital | 4.7k |
| 27 | 25 | digital | 4.7k |
| 28 | 26 | digital | 4.7k |
| 29 | 27 | digital | 4.7k |
| 10 (GND) | GND | | direct |

Pins 7 and 9 sit on the two spare ADC inputs because they may not be connected at all (j8.md). Any pin that step 1a
shows as analog can take their place: change `include/pinmap.h` and this table together.

**Power, and the one wiring mistake that matters:**
- **Power board (break-out B):** the ESP32's **5V pin** goes to header pins 1-6 and runs from the power board. **No
  USB cable**: the PC's ground would join the cooker's. Reports go over Wi-Fi.
- **Main board (break-out A):** the main board runs from the bench supply at JP5. The ESP32 runs from **USB**, and its
  5V pin stays **unconnected**: on header pins 1-6 it would feed USB power into the main board. Only the divider and GND
  join the header.

## Setup `aux`: the main board's other signs of life
A second ESP32 next to the `j8` probe on break-out A, on USB, with Bluetooth and Wi-Fi scanning.

| Signal | ESP32 GPIO | Kind | Through |
|---|---|---|---|
| JP5 pin 1 (VIN) | 39 | analog, power channel | 20k/10k divider |
| U15 pin 8 (3.3 V) | 36 | analog, power channel | 10k/10k divider |
| U15 pin 1 (flash CS; XM25QH64A pinout, measured to the CC3220/) | 4 | digital, moves to a pulse counter when busy | 4.7k |
| J29 pin 1 (signal, rings to TP29) | 16 | digital, UART sniffer from boot | 4.7k |
| J29 pin 2 (signal, rings to TP28) | 17 | digital, UART sniffer from boot | 4.7k |
| J29 pin 3 (GND) or U15 pin 4 | GND | | direct |

Flash CS activity after power-on means the CC3220 ROM is alive and reading the flash. A Bluetooth advertisement with
the power board out of the loop says the main board runs ( found the unit silent in the cooker). The SOIC
clip may carry these taps, but never with a programmer on it at the same time.

## Boot log on J29
J29 is the main board's 3-pin header beside the CC3220: pins 1 and 2 are signals, pin 3 is GND, and it
is `likely` the CC3220's UART0. The `aux` setup sniffs both signal pins from its own boot at 115200 baud
(`BOOT_UART_BAUD`), because which one is the CC3220's TX isn't measured yet. The other one is the CC3220's RX input and
stays quiet.
1. **Gate:** the main board gets power here. That waits for the flash dump (; taken in circuit through
   the boot loader since , handbook chapter 3). The simplest listen, a USB-serial adapter on the TX hole alone,
   is [chapter 4a](../../docs/recovery/04-boot-listen.md); this setup is chapter 4b.
2. **Wiring:** J29 pin 1 through 4.7k to GPIO 16, pin 2 through 4.7k to GPIO 17, pin 3 to the ESP32's GND. The ESP32
   runs from USB; its 5V and 3V3 pins stay unconnected. Nothing drives J29: the sniffers have no TX pin.
   Optionally the VIN divider on GPIO 39, so t0 is the moment the board's supply comes on.
3. **Start the logger first:** `py -3.13 tools/j8probe/j8log.py --port COMx --label j29-boot --console`.
4. **Power the main board** at JP5 from the bench supply: 5.0 V, current limit 100 mA, then 500 mA (bench-setup.md
   step 1b).
5. **Read it:** text scrolls in the console. `<fe=...>` means framing errors, usually the wrong baud. Then
   `uart off J29.2` (or J29.1), power-cycle, read the `bd` hint in the window lines, `uart J29.2 <bd>`, and power-cycle
   again. Try 921600 too.

Before power-up the floating lines can show a few garbage bytes and framing errors; that is noise, not the board.

## Build and flash (on the desk)
```sh
py -3.13 -m platformio run -d tools/j8probe                                   # build both setups
py -3.13 -m platformio run -d tools/j8probe -e j8 -t upload --upload-port COM5
py -3.13 -m platformio run -d tools/j8probe -e aux -t upload --upload-port COM6
```
Wi-Fi: copy `include/secrets.example.h` to `include/secrets.h` (gitignored) to join a network. Without it, the `j8`
setup opens its own access point `j8probe-XXXXXX` (password `j8probe-ap`, address 192.168.4.1), and `aux` reports over
USB only.

## Logging
```sh
py -3.13 tools/j8probe/j8log.py --list                                        # serial ports
py -3.13 tools/j8probe/j8log.py --port COM6 --label mainboard-aux
py -3.13 tools/j8probe/j8log.py --port COM6 --label j29-boot --console      # only the sniffed text, like a terminal
py -3.13 tools/j8probe/j8log.py --tcp j8probe-a1b2c3.local --label powerboard  # or 192.168.4.1
py -3.13 tools/j8probe/j8log.py --summary .capture/j8probe/<file>.jsonl       # per-pin table for j8.md
```
Captures go to `.capture/j8probe/` (gitignored), one JSON object per line with the PC's time added as `pc`. Lines
typed into the logger go to the probe as commands. Opening the serial port doesn't reset the dev kit (DTR and RTS are
held off).

## Output
One line per window: 100 ms for the first 3 s after t0, then 1 s.
- Digital: `l` level now, `e` edges in the window, `hi` / `lo` shortest high and low pulse in µs, `bd` a baud rate the
  shortest pulse would fit (a hint: interrupt latency is a few µs), `pc` counted by a pulse counter, `uart` sniffed.
- Analog: `v` [min, mean, max] in probe volts (scale applied), `x` logic-level crossings (1.2 / 1.8 V at the pin).

Events: `hello` (setup, firmware, channel map), `t0`, `power` (a power channel on or off), `first` (a channel's first
edge after t0), `pcnt` / `muted` (a pin moved off the edge interrupt), `uart_on` (a sniffer started), `uart` (the
bytes in `txt`, lossless: printable ASCII as is, every other byte as `\u00xx`; `n` bytes, `fe` framing errors and `ovf`
overruns since the last event), `ble` and
`wifi` (a device or network seen for the first time, `aux` only), `ok` / `err` (commands).

**t0** is boot, then every power-on of a power channel when no other power channel was on, so on the main board it is
the moment the bench supply comes on. On the power board the ESP32 starts with the supply, so t0 is its own start.

## Commands
| Command | |
|---|---|
| `help`, `map` | list commands; repeat the `hello` line |
| `t0` | set t0 now |
| `window <ms>` / `window 0` | fixed window length (10-10000 ms) / automatic |
| `uart <channel> <baud>` / `uart off [<channel>]` | sniff a digital channel as 8N1 UART, RX only, two channels at a time (e.g. `uart J29.2 921600`); `uart off` alone stops both |
| `rearm` | put pins that moved to a pulse counter back on the edge interrupt |
| `radio` | list every Bluetooth device and Wi-Fi network seen (`aux`) |

## Limits
- Classic ESP32 timing: pulse widths and baud hints are approximate to a few µs. A pin with more than 5000 edges in
  one window moves to a pulse counter: counts stay exact, widths stop.
- Two UART sniffers (the ESP32's UART1 and UART2; UART0 is the USB link). A sniffed channel has no edge counts or
  baud hint while it sniffs. USB runs at 921600 baud: a sustained source above about 500 kbaud can overrun it, a boot
  burst fits the 8 KB buffers.
- Analog channels are sampled at 1 kHz. The ESP32 ADC is accurate from about 0.15 to 2.45 V at the pin, and saturates
  near 3.1 V.
- A floating pin picks up noise: random edges on a digital channel, a wandering mean on an analog one. Telling
  floating from driven needs a weak pull, which is prodding and not in this firmware.
