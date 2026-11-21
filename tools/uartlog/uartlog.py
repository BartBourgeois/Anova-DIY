"""Capture a UART boot log without touching the target: listen, store every byte, never send one.

The port is opened as a listener only: DTR and RTS are held off before it opens (the pattern of
tools/j8probe/j8log.py, so nothing pulses a dev kit's reset) and this script has no transmit path at all. Every
received byte goes losslessly into .capture/uart/<label>_<YYYYMMDD-HHMMSS>.log at the repository root (gitignored):
printable ASCII as is (the backslash as \\x5c, so the escapes stay unambiguous), every other byte as \\xNN. A stored
line is what arrived until a newline or a 100 ms gap, prefixed with the PC's time (ISO, milliseconds) of its first
byte; the console shows the same lines. A header line records port, baud, label and start time; a baud change
writes a marker line. Several bauds can be given (repeat --baud, or comma-separate them): the first is used from
the start, Enter reopens the port at the next one, round robin, for a target whose ROM and application talk at
different speeds. Ctrl+C stops and closes the port.

Usage:
  py -3.13 tools/uartlog/uartlog.py --list
  py -3.13 tools/uartlog/uartlog.py --port COM7 --label launchpad-oob
  py -3.13 tools/uartlog/uartlog.py --port COM7 --baud 115200,921600 --label j29-boot
"""

import argparse
import datetime as dt
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / ".capture" / "uart"
GAP = 0.1  # seconds of silence that end a line


def open_port(name: str, baud: int):
    """A listener: DTR and RTS off before the port opens, no flow control, short read timeout."""
    import serial  # pyserial

    s = serial.Serial()
    s.port = name
    s.baudrate = baud
    s.timeout = 0.02
    s.dsrdtr = s.rtscts = s.xonxoff = False
    s.dtr = s.rts = False  # set before open(): the modem lines come up in this state, nothing is pulsed
    s.open()
    return s


def escape(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 and b != 0x5C else f"\\x{b:02x}" for b in data)


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="milliseconds")


def capture(port_name: str, bauds: list, label: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{label}_{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    switch = threading.Event()

    def stdin_reader():  # Enter = next baud
        for _ in sys.stdin:
            switch.set()

    threading.Thread(target=stdin_reader, daemon=True).start()
    idx, buf, t0 = 0, bytearray(), ""
    port = open_port(port_name, bauds[idx])
    with path.open("a", encoding="utf-8") as f:

        def emit(text: str) -> None:
            f.write(text + "\n")
            f.flush()
            print(text)

        def flush_line() -> None:
            if buf:
                emit(f"{t0} {escape(bytes(buf))}")
                buf.clear()

        rotate = f"  bauds={','.join(map(str, bauds))} (Enter = next)" if len(bauds) > 1 else ""
        emit(f"# uartlog port={port_name} baud={bauds[idx]} label={label} started={now_iso()}{rotate}")
        print(f"logging to {path}  (Ctrl+C to stop)")
        last = time.monotonic()
        try:
            while True:
                if switch.is_set():
                    switch.clear()
                    if len(bauds) > 1:
                        flush_line()
                        port.close()
                        idx = (idx + 1) % len(bauds)
                        port = open_port(port_name, bauds[idx])
                        emit(f"# baud -> {bauds[idx]} at {now_iso()}")
                data = port.read(port.in_waiting or 1)
                now = time.monotonic()
                if data:
                    for b in data:
                        if not buf:
                            t0 = now_iso()
                        buf.append(b)
                        if b == 0x0A:
                            flush_line()
                    last = now
                elif buf and now - last > GAP:
                    flush_line()
        except KeyboardInterrupt:
            flush_line()
            emit(f"# stopped at {now_iso()}")
        finally:
            port.close()
    print(f"\nstopped; {path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", help="serial port to listen on, e.g. COM7")
    ap.add_argument("--baud", action="append",
                    help="baud rate (default 115200); repeat or comma-separate to rotate with Enter")
    ap.add_argument("--label", default="uart", help="added to the capture file name")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    args = ap.parse_args()
    if args.list:
        from serial.tools import list_ports

        for p in list_ports.comports():
            print(f"{p.device}  {p.description}  {p.hwid}")
        return 0
    if not args.port:
        ap.error("--port is required (or --list)")
    bauds = [int(x) for v in (args.baud or ["115200"]) for x in v.split(",") if x.strip()]
    return capture(args.port, bauds, args.label)


if __name__ == "__main__":
    sys.exit(main())
