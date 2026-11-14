# flashbackup

`backup.py` backs up a SPI NOR flash chip with [flashrom](https://flashrom.org): it reads the chip until two reads
are equal, and keeps the pair with a manifest. That pair is the project's rule-1 backup (no write without a dump read
twice with the same SHA-256). The step-by-step procedure, with the wiring for each reader and the board pictures, is
the [flash backup handbook](../../docs/flashbackup/index.md).

**Read-only by construction.** flashrom is only ever started with `--version`, `--flash-name`, `--flash-size` or
`-r`. The script has no option that would pass `-w`, `-E`, `-v` or a write-protect operation.

Standard library only (Python 3.7+): it runs unchanged on the PC (Windows, flashrom from MSYS2) and on a Raspberry Pi
(Raspberry Pi OS, `sudo apt install flashrom`).

## Usage
```sh
# read until two reads are equal (at most three), stop if the chip or its size is not the expected one
python3 backup.py read --programmer <flashrom -p string> --out <dir> --name <stem> \
    --expect-chip <part> --expect-size <bytes> [--chip <flashrom -c name>] [--label "<board, setup>"]

# after copying the files elsewhere (off the Pi, to the off-machine copy): do they still match?
python3 backup.py check <dir>/<stem>.json
```
On Windows use `py -3.13` for `python3`, and point `--flashrom` (or the `FLASHROM` environment variable) at
`flashrom.exe` if it isn't on the PATH.

| Reader | Runs on | `--programmer` | Notes |
|---|---|---|---|
| Raspberry Pi (SPI0, CE0) | the Pi | `linux_spi:dev=/dev/spidev0.0,spispeed=2000` | speed in kHz; SPI enabled once (`raspi-config`) |
| Raspberry Pi Pico, serprog firmware | the PC | `serprog:dev=COM<n>:115200,spispeed=2M` | the baud is ignored on USB; `COM<n>` from Device Manager |
| ESP32 with `tools/espserprog` | the PC | `serprog:dev=COM<n>:921600,spispeed=2M` | the firmware is read-only itself; 921 600 baud is built in |
| FT232H (Adafruit 2264) | the PC | `ft2232_spi:type=232H,divisor=30` | 60 MHz / 30 = 2 MHz; WinUSB driver via Zadig once |

The expected chips: the cooker's U15 `--expect-chip XM25QH64A --expect-size 8388608`, the LaunchPad's U8
`--expect-chip MX25R3235F --expect-size 4194304`, the spare practice chip `--expect-chip W25Q64JV`. All three are in
flashrom 1.8.0's chip list (`flashrom -L`, checked 2026-11-06); an older flashrom on the Pi may lack the XMC part
(see the handbook).

## What it writes
Into `--out` (keep it outside git: `dumps/...`):
- `<stem>_1.bin`, `<stem>_2.bin` (a third if the first two differ)
- `<stem>.json`, the manifest: started/finished, host, OS, flashrom version, programmer string, the chip flashrom
  detected and its size, every read with its bytes, SHA-256 and duration, and the verdict (`verified` with the
  SHA-256 of the pair, `no two reads equal`, `wrong chip`, `wrong size`)
- `<stem>.log`, flashrom's own output for every call

Every flashrom call has a time limit (reads: the chip's size at 15 kB/s, at least 120 s; `--read-timeout`): a
stalled serial link would otherwise make flashrom wait without end. A failed or stalled read counts as
one attempt; the next read follows, up to `--max-reads`.

It never overwrites a file. A probe that fails (no chip, or several chip definitions that match: then it names them,
pass one with `--chip`) reads nothing: its log is kept as `<stem>.probe-<time>.log` and the name stays free.

Exit codes: 0 a verified pair, 1 no two reads equal, 2 refused or flashrom failed, 3 wrong chip or size.

## Tested
Against flashrom's own emulated chip (`-p dummy:emulate=MX25L6436`, 2026-11-06): the several-definitions probe, a
verified pair, the wrong-chip stop, and `check` catching a file changed by one byte.

## u7read.py: the Bluetooth chip (U7, CC2640R2F)

`u7read.py` does for U7's internal flash (128 KiB) what `backup.py` does for U15: it reads until two reads are
equal and keeps the pair with a manifest. The probe is an XDS110 (the CC3220S LaunchPad's own) in 2-pin cJTAG on
U7's TMSC and TCKC test points (TP13, TP14). The reading is TI's DSLite, from Uniflash. The procedure with the
wiring and the beeper checks: [flash backup page 10](../../docs/flashbackup/10-cooker-u7.md).

**Read-only by construction.** DSLite is only ever started in its `memory` mode, which copies target memory into a
file: no flash loader, no erase, no program. Nothing here starts its `flash` or `load` modes.
`cc2640r2f_xds110_cjtag.ccxml` is TI's own CC2640R2F example with one change, target-supplied power. The script
checks it before every run and refuses a configuration that would let the probe power the target.

```sh
py -3.13 tools/flashbackup/u7read.py ccfg --out dumps/cooker/<date>             # connect test: the CCFG, decoded
py -3.13 tools/flashbackup/u7read.py read --out dumps/cooker/<date> --name u7_jtag --label "<board, setup>"
py -3.13 tools/flashbackup/u7read.py compare <image.bin> [--ref NAME=PATH]     # sector by sector vs the known images
py -3.13 tools/flashbackup/u7read.py pair <a>.json <b>.json --name u7_backup  # one read per power-up: the pair
py -3.13 tools/flashbackup/u7read.py check dumps/cooker/<date>/u7_jtag.json
```
DSLite is found through `--dslite`, `DSLITE` (the exe), `UNIFLASH` (Uniflash's folder), or TI's default Uniflash
9.7.1 install on the system drive.

`read` writes `<stem>_1.bin`, `<stem>_2.bin` (a third if they differ), `<stem>.log` (DSLite's output) and
`<stem>.json`: DSLite's path, the configuration's SHA-256, every read with its SHA-256 and duration, the verdict,
the decoded CCFG (CPU debug, ROM boot loader, backdoor pin, image valid) and the comparison. The known images are
the two U7 images from the update packages (pinned by SHA-256, read from `dumps/`, never in git): the one the
cooker's flash holds committed (`old`) and 3.3.35's. The comparison names the image the backup equals, or, per
4 KiB sector, which image each run of sectors equals, `erased`, or `other`.

A read that fails or stalls (`--read-timeout`, 300 s) counts as one attempt. It also stops if DSLite writes a file
of the wrong size: DSLite's `--range` length counts 32-bit words on this target (found on U7, 2026-11-06), so the
script asks for words. **U7 answers once per power-up**: later sessions fail with Error -242 ("a router subpath
could not be accessed"), so a backup is one read per power-up and `pair` makes the manifest. **DSLite updates
the XDS110's firmware by itself** on its first run with an older probe (2.3.0.7 to 3.0.0.45), without asking. Exit codes: 0 verified (or,
for `compare`, equal to a known image), 1 no two reads equal (or no known image), 2 refused or DSLite failed.

### Tested
Offline, 2026-11-06: `compare` on both known images (each equal to itself) and on two made-up half-flashed images
(the sector runs come out right); the refusal of a configuration with probe-supplied power; DSLite parsing the
configuration through to the CC2640R2F's Cortex-M3 and stopping at "no XDS110 is connected". On the cooker's U7,
2026-11-06: two reads from two power-ups, equal (`0f4d7ede…`), paired, verified, and equal to the old U7 image.
