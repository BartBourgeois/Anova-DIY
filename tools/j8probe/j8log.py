"""Log a j8probe over USB serial or TCP, and summarise a capture.

Every line the probe sends is a JSON object. This script stores each one, with the PC's time added as "pc", in
.capture/j8probe/<YYYYMMDD_HHMMSS>_<label>.jsonl at the repository root (gitignored), and prints a short view:
events in full, window lines only for channels that do something. Lines typed on stdin go to the probe as commands.
With --console the view shows only the sniffed UART bytes as text, like a terminal, and power events as markers;
everything is still stored.

Usage:
  py -3.13 tools/j8probe/j8log.py --list
  py -3.13 tools/j8probe/j8log.py --port COM5 --label mainboard-aux
  py -3.13 tools/j8probe/j8log.py --port COM6 --label j29-boot --console
  py -3.13 tools/j8probe/j8log.py --tcp j8probe-a1b2c3.local --label powerboard
  py -3.13 tools/j8probe/j8log.py --summary .capture/j8probe/20261105_201500_powerboard.jsonl
"""

import argparse
import datetime as dt
import json
import socket
import sys
import threading
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / ".capture" / "j8probe"
BAUD = 921600
TCP_PORT = 2323


class SerialLink:
    def __init__(self, port: str):
        import serial  # pyserial

        self.s = serial.Serial()
        self.s.port = port
        self.s.baudrate = BAUD
        self.s.timeout = 0.2
        self.s.dtr = False  # keep the dev kit's auto-reset circuit quiet: opening the port shouldn't reboot it
        self.s.rts = False
        self.s.open()

    def readline(self) -> bytes:
        return self.s.readline()

    def send(self, line: str) -> None:
        self.s.write((line + "\n").encode())


class TcpLink:
    def __init__(self, target: str):
        host, _, port = target.partition(":")
        self.sock = socket.create_connection((host, int(port or TCP_PORT)), timeout=10)
        self.sock.settimeout(0.2)
        self.f = self.sock.makefile("rb")

    def readline(self) -> bytes:
        try:
            return self.f.readline()
        except (socket.timeout, TimeoutError):
            return b""

    def send(self, line: str) -> None:
        self.sock.sendall((line + "\n").encode())


def active(name: str, ch: dict, prev: dict) -> bool:
    """Is this channel worth a line in the live view?"""
    if "v" in ch:
        if ch["v"] is None:
            return False
        lo, _, hi = ch["v"]
        old = (prev.get(name) or {}).get("v")
        moved = old is None or abs(ch["v"][1] - old[1]) > 0.1
        return ch.get("x", 0) > 0 or hi - lo > 0.2 or moved
    old = prev.get(name) or {}
    return ch.get("e", 0) > 0 or ch.get("l") != old.get("l")


def show(msg: dict, prev: dict) -> None:
    if "ev" in msg:
        print(json.dumps(msg, separators=(",", ":")))
        return
    parts = []
    for name, ch in msg.get("ch", {}).items():
        if active(name, ch, prev):
            if "v" in ch:
                parts.append(f"{name} {ch['v'][0]:.2f}..{ch['v'][2]:.2f}V" + (f" x{ch['x']}" if ch.get("x") else ""))
            else:
                extra = "".join(f" {k}={ch[k]}" for k in ("hi", "lo", "bd", "pc", "uart") if k in ch)
                parts.append(f"{name} l{ch['l']} e{ch['e']}{extra}")
    prev.update(msg.get("ch", {}))
    if parts:
        print(f"t={msg['t']} win={msg['win']}ms  " + " | ".join(parts))


def console(msg: dict, state: dict) -> None:
    """Terminal view: sniffed bytes as text (other bytes as <xx>), power and sniffer events as marker lines."""
    ev = msg.get("ev")
    if ev == "uart":
        if msg.get("ch") != state.get("ch"):
            sys.stdout.write(f"\n[{msg.get('ch')} @ {msg.get('baud')}] ")
            state["ch"] = msg.get("ch")
        data = msg.get("txt", "").encode("latin-1", errors="replace")  # txt holds one code point per byte
        sys.stdout.write("".join(chr(b) if b in (9, 10, 13) or 32 <= b < 127 else f"<{b:02x}>" for b in data))
        if msg.get("fe") or msg.get("ovf"):
            sys.stdout.write(f"<fe={msg.get('fe', 0)} ovf={msg.get('ovf', 0)}>")
    elif ev in ("hello", "t0", "power", "uart_on", "ok", "err", "raw"):
        sys.stdout.write("\n--- " + json.dumps({k: v for k, v in msg.items() if k != "map"}, separators=(",", ":")) + "\n")
        state["ch"] = None
    sys.stdout.flush()


def log(args) -> int:
    link = SerialLink(args.port) if args.port else TcpLink(args.tcp)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUT_DIR / f"{stamp}_{args.label}.jsonl"
    print(f"logging to {path}  (type commands, Ctrl+C to stop)")

    def stdin_reader():
        for line in sys.stdin:
            if line.strip():
                link.send(line.strip())

    threading.Thread(target=stdin_reader, daemon=True).start()
    for c in args.cmd or []:
        link.send(c)
    prev: dict = {}
    state: dict = {}
    with path.open("a", encoding="utf-8") as f:
        try:
            while True:
                raw = link.readline()
                if not raw:
                    continue
                text = raw.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                pc = dt.datetime.now().isoformat(timespec="milliseconds")
                try:
                    msg = json.loads(text)
                except json.JSONDecodeError:
                    msg = {"ev": "raw", "text": text}  # boot messages from the ESP32 ROM, for instance
                msg["pc"] = pc
                f.write(json.dumps(msg, separators=(",", ":")) + "\n")
                f.flush()
                if args.console:
                    console(msg, state)
                elif not args.quiet:
                    show(msg, prev)
        except KeyboardInterrupt:
            print(f"\nstopped; {path}")
    return 0


def summary(path: Path) -> int:
    """Per channel since the last t0 in the file: idle level, toggling, first edge, voltages, baud hints."""
    msgs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    last_t0 = max((i for i, m in enumerate(msgs) if m.get("ev") == "t0"), default=0)
    msgs = msgs[last_t0:]
    levels: dict = defaultdict(Counter)
    edges: Counter = Counter()
    peak: Counter = Counter()
    volts: dict = {}
    hints: dict = defaultdict(set)
    flags: dict = defaultdict(set)
    first = {m["ch"]: m["t"] for m in msgs if m.get("ev") == "first"}
    order: list = []
    for m in msgs:
        if "ev" in m:  # events name one channel in "ch"; only window lines carry the channel table
            continue
        for name, ch in m["ch"].items():
            if name not in order:
                order.append(name)
            if "v" in ch:
                if ch["v"] is not None:
                    lo, _, hi = ch["v"]
                    old = volts.get(name, (lo, hi))
                    volts[name] = (min(old[0], lo), max(old[1], hi))
                    edges[name] += ch.get("x", 0)
                continue
            levels[name][ch["l"]] += 1
            edges[name] += ch["e"]
            peak[name] = max(peak[name], round(ch["e"] * 1000 / max(m["win"], 1)))
            if "bd" in ch:
                hints[name].add(ch["bd"])
            for k in ("pc", "muted"):
                if k in ch:
                    flags[name].add(k)
    print(f"Summary of {path.name}, from the last t0\n")
    print("| Channel | Idle | Edges | Peak edges/s | First edge (s after t0) | Volts | Notes |")
    print("|---|---|---|---|---|---|---|")
    for name in order:
        idle = levels[name].most_common(1)[0][0] if levels[name] else ""
        v = f"{volts[name][0]:.2f}-{volts[name][1]:.2f}" if name in volts else ""
        notes = ", ".join([f"baud? {b}" for b in sorted(hints[name])] + sorted(flags[name]))
        print(f"| {name} | {idle} | {edges[name]} | {peak[name] or ''} | {first.get(name, '')} | {v} | {notes} |")
    for kind in ("power", "uart", "ble", "wifi", "pcnt", "muted", "err"):
        found = [m for m in msgs if m.get("ev") == kind]
        if found:
            print(f"\n{kind}: {len(found)} event(s)")
            for m in found[:20]:
                print("  " + json.dumps({k: v for k, v in m.items() if k not in ("ev", "pc")}, separators=(",", ":")))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--port", help="serial port of the probe, e.g. COM5")
    src.add_argument("--tcp", help="host[:port] of the probe on Wi-Fi (port 2323 by default)")
    src.add_argument("--summary", type=Path, help="summarise a capture file and exit")
    src.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--label", default="probe", help="added to the capture file name")
    ap.add_argument("--cmd", action="append", help="command to send after connecting (repeatable)")
    ap.add_argument("--quiet", action="store_true", help="store only, no live view")
    ap.add_argument("--console", action="store_true", help="live view of the sniffed UART text only")
    args = ap.parse_args()
    if args.list:
        from serial.tools import list_ports

        for p in list_ports.comports():
            print(f"{p.device}  {p.description}  {p.hwid}")
        return 0
    if args.summary:
        return summary(args.summary)
    return log(args)


if __name__ == "__main__":
    sys.exit(main())
