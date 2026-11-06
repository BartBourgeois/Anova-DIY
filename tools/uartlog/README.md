# uartlog

A listen-only boot-log capture for any 3.3 V UART: the CC3220's ROM and application output on the LaunchPad's user
port, the cooker's J29 once a cable hangs on it, the j8probe's own console. The script opens the port with DTR and
RTS held off (nothing pulses a dev kit's reset) and has no transmit path: it never writes to the port.

**Read-only by construction.** The only call that could send anything, `write()`, does not occur in the script.
Wire the adapter's RX and GND only; leave its TX unconnected unless a later step needs it, and use a 3.3 V adapter.

## Usage
```sh
py -3.13 tools/uartlog/uartlog.py --list                                  # serial ports on this PC
py -3.13 tools/uartlog/uartlog.py --port COM7 --label launchpad-oob      # 115200 baud
py -3.13 tools/uartlog/uartlog.py --port COM7 --baud 115200,921600 --label j29-boot
```
- `--baud` may be repeated or comma-separated. The first rate is used from the start; **Enter** reopens the port
  at the next one (round robin) and logs a marker line, for a target whose ROM and application talk at different
  speeds. With one rate Enter does nothing.
- **Ctrl+C** closes the port and ends the file with a `# stopped` line.

## The capture file
`.capture/uart/<label>_<YYYYMMDD-HHMMSS>.log` at the repository root (gitignored), one text line per received line:

```
# uartlog port=COM7 baud=115200 label=launchpad-oob started=2026-11-05T19:02:11.482  bauds=115200,921600 (Enter = next)
2026-11-05T19:02:14.071 \x00\xff\xfe\x00boot text as sent\x0d\x0a
# baud -> 921600 at 2026-11-05T19:02:40.913
```
- A line is what arrived until a newline (`\x0a`, kept in the line) or a **100 ms gap** in the stream. Its prefix
  is the PC's time of the line's first byte (ISO, milliseconds).
- **Lossless:** printable ASCII (0x20-0x7e) is stored as is, except the backslash, which becomes `\x5c`; every
  other byte (framing errors on a wrong baud show as `\x00`, `\xff`, `\xfe`...) becomes `\xNN`. Decoding the file
  back to the byte stream is unambiguous.
- The console shows the same lines as they are written.

## Notes
- The ROM's own output (the CC3220 boot messages, when there are any) and the application's may differ in baud;
  rotate with Enter and look at which rate produces text instead of `\xNN` runs.
- The read timeout is 20 ms, so the PC time is accurate to about that.
- Needs pyserial (`tools/requirements.txt`).
