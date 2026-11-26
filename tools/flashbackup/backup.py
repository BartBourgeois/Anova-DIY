"""Back up a SPI NOR flash with flashrom: read it until two reads are equal, then keep them with a manifest.

The project's rule 1 (no write without a dump read twice with the same SHA-256), done the same way whatever the
reader: a Raspberry Pi (flashrom's linux_spi, run on the Pi), a Raspberry Pi Pico with serprog firmware or an FT232H
(serprog and ft2232_spi, run on the PC). See docs/flashbackup/.

Read-only by construction: flashrom is only ever started with --version, --flash-name, --flash-size or -r (read).
There is no option here that passes -w, -E, -v, --wp-* or anything else to it.

  backup.py read  --programmer <flashrom -p string> --out <dir> --name <stem> [options]
      1. flashrom --version; then the chip: --flash-name and --flash-size (both probe only)
      2. stops if the chip or the size isn't the one expected (--expect-chip, --expect-size)
      3. reads to <stem>_1.bin, <stem>_2.bin, ... until two reads are equal, at most --max-reads (default 3)
      4. writes <stem>.json (versions, programmer, chip, size, each read's SHA-256 and duration, the verdict) and
         <stem>.log (flashrom's own output); never overwrites an existing file
      Exit 0 = a verified pair (the backup), 1 = no two reads equal, 2 = refused or flashrom failed, 3 = wrong chip.
      A read that fails or stalls (killed after --read-timeout) counts as one attempt; the next read follows.
      A failed probe reads nothing: its log is kept as <stem>.probe-<time>.log and the name stays free.
  backup.py check <stem>.json
      re-hashes the files a manifest names (after copying them off a Pi, or to the off-machine copy) and says
      whether they still match. Exit 0 = all match.

Standard library only (Python 3.7+), so it runs as it is on Raspberry Pi OS and on the PC.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ALLOWED = {"--version", "--flash-name", "--flash-size", "-r"}  # the only flashrom operations this script runs
SEVERAL = re.compile(r"Multiple flash chip definitions match the detected chip\(s\): (.*)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Flashrom:
    def __init__(self, exe: str, programmer: str, chip: str, log):
        self.exe, self.programmer, self.chip, self.log = exe, programmer, chip, log

    def run(self, op: str, *extra: str, timeout: float = 120) -> str:
        if op not in ALLOWED:
            raise SystemExit(f"backup.py: refusing flashrom operation {op!r} (read-only tool)")
        cmd = [self.exe] if op == "--version" else [self.exe, "-p", self.programmer] + (
            ["-c", self.chip] if self.chip else [])
        cmd += [op, *extra]
        self.log.write(f"\n$ {' '.join(cmd)}\n")
        self.log.flush()
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                               timeout=timeout)
        except subprocess.TimeoutExpired as e:  # a stalled serial link (J-216): flashrom would wait forever
            out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            self.log.write(out + f"\n[backup.py: killed after {timeout:.0f} s without finishing]\n")
            self.log.flush()
            raise RuntimeError(f"flashrom {op} timed out after {timeout:.0f} s (stalled link?)")
        self.log.write(p.stdout)
        self.log.flush()
        if p.returncode != 0:
            tail = "\n  ".join(p.stdout.strip().splitlines()[-8:])
            raise RuntimeError(f"flashrom {op} failed (exit {p.returncode}):\n  {tail}")
        return p.stdout


def probe(fr: Flashrom, m: dict, args) -> int:
    """flashrom's version, then the chip's name and size (probe only). 0 = go on, 2 = probe failed, 3 = wrong chip."""
    try:
        m["flashrom"] = fr.run("--version").strip().splitlines()[0]
        name_out = fr.run("--flash-name")
        size_out = fr.run("--flash-size")
    except RuntimeError as e:
        print(f"backup.py: {e}", file=sys.stderr)
        several = SEVERAL.search(str(e))
        if several:
            print(f"backup.py: pass one of these with --chip (the part on the board decides): {several.group(1)}",
                  file=sys.stderr)
        return 2
    pgm = re.search(r'Programmer name is "([^"]*)"', name_out)
    if pgm:
        m["programmer_name"] = pgm.group(1)
        if pgm.group(1).startswith("espserprog") and not pgm.group(1).endswith("-ro"):
            print(f"backup.py: WARNING: the reader runs {pgm.group(1)!r}, the write-capable build: flash the read-only "
                  "one (espserprog-ro) before it goes near a board", file=sys.stderr)
    found = re.search(r'vendor="([^"]*)" name="([^"]*)"', name_out)
    m["chip"] = f"{found.group(1)} {found.group(2)}" if found else name_out.strip().splitlines()[-1]
    sizes = re.findall(r"^\s*(\d+)\s*$", size_out, re.M)
    m["size"] = int(sizes[-1]) if sizes else None
    print(f"{m['flashrom']}\nchip: {m['chip']}, {m['size']} bytes")
    if args.expect_chip and args.expect_chip.lower() not in m["chip"].lower():
        m["verdict"] = f"wrong chip: expected {args.expect_chip}"
        print(f"backup.py: stop: the chip is not {args.expect_chip} (clip seated? right board?)", file=sys.stderr)
        return 3
    if args.expect_size and m["size"] != args.expect_size:
        m["verdict"] = f"wrong size: expected {args.expect_size}"
        print(f"backup.py: stop: size {m['size']}, expected {args.expect_size}", file=sys.stderr)
        return 3
    return 0


def read_timeout(size, args) -> float:
    """Seconds a read may take before it counts as stalled: --read-timeout, or the chip's size at 15 kB/s (a third of
    the slowest reader measured, the ESP32's verified reads at about 52 kB/s), at least 120 s."""
    return args.read_timeout or max(120.0, (size or 16 << 20) / 15000)


def read_until_pair(fr: Flashrom, m: dict, args, out: Path) -> None:
    hashes = []
    for k in range(1, args.max_reads + 1):
        path = out / f"{args.name}_{k}.bin"
        t0 = time.monotonic()
        try:
            fr.run("-r", str(path), timeout=read_timeout(m.get("size"), args))
        except RuntimeError as e:
            print(f"backup.py: read {k}: {e}", file=sys.stderr)
            m["reads"].append({"file": path.name, "error": str(e).splitlines()[0]})
            continue  # a failed read is one attempt: the next one may succeed
        secs = round(time.monotonic() - t0, 1)
        digest, nbytes = sha256(path), path.stat().st_size
        m["reads"].append({"file": path.name, "bytes": nbytes, "sha256": digest, "seconds": secs})
        print(f"read {k}: {path.name}  {nbytes} bytes  {secs} s  sha256 {digest}")
        if m["size"] and nbytes != m["size"]:
            print(f"backup.py: read {k} is {nbytes} bytes, the chip has {m['size']}", file=sys.stderr)
        hashes.append(digest)
        pairs = [h for h in set(hashes) if hashes.count(h) >= 2]
        if pairs and k >= args.reads:
            m["verdict"], m["sha256"] = "verified", pairs[0]
            break
    m["verdict"] = m["verdict"] or "no two reads equal"


def cmd_read(args) -> int:
    exe = args.flashrom or os.environ.get("FLASHROM") or shutil.which("flashrom")
    if not exe:
        print("backup.py: flashrom not found: give --flashrom or set FLASHROM", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path, log_path = out / f"{args.name}.json", out / f"{args.name}.log"
    planned = [out / f"{args.name}_{k}.bin" for k in range(1, args.max_reads + 1)] + [manifest_path, log_path]
    existing = [str(p) for p in planned if p.exists()]
    if existing:
        print("backup.py: refusing to overwrite:\n  " + "\n  ".join(existing), file=sys.stderr)
        return 2
    started = dt.datetime.now().astimezone()
    m = {"tool": "tools/flashbackup/backup.py", "started": started.isoformat(timespec="seconds"),
         "host": platform.node(), "os": platform.platform(), "programmer": args.programmer, "chip_option": args.chip,
         "label": args.label, "reads": [], "verdict": None}
    with log_path.open("w", encoding="utf-8") as log:
        fr = Flashrom(exe, args.programmer, args.chip, log)
        rc = probe(fr, m, args)
        if rc == 0:
            read_until_pair(fr, m, args, out)
            m["finished"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    if rc == 2:  # nothing was read: keep the probe's log under its own name, so the next try can use this --name
        log_path.replace(out / f"{args.name}.probe-{started:%Y%m%d-%H%M%S}.log")
        return 2
    manifest_path.write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    if rc == 3:
        return 3
    if m["verdict"] == "verified":
        same = [r["file"] for r in m["reads"] if r.get("sha256") == m["sha256"]]
        print(f"VERIFIED: {', '.join(same)} are equal, sha256 {m['sha256']}\nmanifest: {manifest_path}")
        return 0
    print("NOT VERIFIED: no two reads are equal. Re-seat the clip, check every lead, lower the SPI speed, read again "
          "into a new --name. Keep these files: they are evidence.", file=sys.stderr)
    return 1


def cmd_check(args) -> int:
    path = Path(args.manifest)
    m = json.loads(path.read_text(encoding="utf-8"))
    bad = 0
    for r in m.get("reads", []):
        if "sha256" not in r:
            continue
        f = path.parent / r["file"]
        if not f.exists():
            print(f"missing   {f}")
            bad += 1
            continue
        ok = sha256(f) == r["sha256"]
        bad += not ok
        print(f"{'ok' if ok else 'CHANGED':9} {f}")
    print(f"verdict in the manifest: {m.get('verdict')}; sha256 {m.get('sha256', '-')}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True
    r = sub.add_parser("read", help="read the flash until two reads are equal")
    r.add_argument("--programmer", required=True,
                   help="flashrom's -p string, e.g. linux_spi:dev=/dev/spidev0.0,spispeed=2000")
    r.add_argument("--out", required=True, help="directory for the dumps (outside git: dumps/...)")
    r.add_argument("--name", required=True, help="file stem, e.g. u15_clip -> u15_clip_1.bin, u15_clip_2.bin")
    r.add_argument("--chip", default="", help="flashrom's -c, only if it asks (several definitions match)")
    r.add_argument("--expect-chip", default="", help="stop unless the detected chip name contains this, e.g. XM25QH64A")
    r.add_argument("--expect-size", type=int, default=0, help="stop unless the chip has this many bytes")
    r.add_argument("--reads", type=int, default=2, help="reads before a verdict (default 2)")
    r.add_argument("--max-reads", type=int, default=3, help="stop after this many reads (default 3)")
    r.add_argument("--label", default="", help="free text for the manifest: board, setup, who")
    r.add_argument("--read-timeout", type=float, default=0,
                   help="seconds before a read counts as stalled (default: the size at 15 kB/s, at least 120)")
    r.add_argument("--flashrom", default="", help="flashrom executable (default: $FLASHROM, then the PATH)")
    c = sub.add_parser("check", help="re-hash the files of a manifest")
    c.add_argument("manifest")
    args = ap.parse_args()
    if args.cmd == "read":
        if args.reads < 2 or args.max_reads < args.reads:
            ap.error("--reads must be at least 2 and --max-reads at least --reads")
        return cmd_read(args)
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
