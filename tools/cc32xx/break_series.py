"""Time the CC3220 network processor's post-switch break: connect-only sessions through ccx.py --cc3220 (J-161).

Each trial resets the chip through the LaunchPad's XDS110 (TI's xds110reset.exe from Uniflash), waits, and runs a
connect-only session (no subcommand: the version query, TI's step 3, the network processor's version query) with one
break window. It records whether the network processor's boot loader answered and when its ACK arrived after the
switch. Nothing is read from or written to the flash, but every missed break lets the network processor boot its own
firmware, which rewrites its radio calibration file /tmp/phy.cal (J-160, J-186): run it only on a board whose flash
has a backup.

The board: a LaunchPad with J13 on SOP2 (boot loader). Results go to stdout as JSON lines and, with --out, into one
JSON file; ccx.py also logs every session in .capture/cc32xx/.

Usage:
  py -3.13 tools/cc32xx/break_series.py --venv <cc3200tool venv> --port COM11 --probe E0081010 \\
      [--window 1.0:0.2 --window 0.5:1.5 ...] [--trials 5] [--out series.json]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# TI's xds110reset.exe ships with Uniflash (simplelink/imagecreator/bin/): --reset-tool, $XDS110RESET or the PATH
# J-161's four windows: cc3200tool's own timing, the whole second, the default, a short late one
DEFAULT_WINDOWS = ["1.0:0.2", "0.0:2.0", "0.5:1.5", "0.8:1.0"]


def trial(args, lead, hold):
    subprocess.run([str(args.reset_tool), "-a", "toggle", "-d", "200", "-s", args.probe], capture_output=True)
    time.sleep(args.settle)
    p = subprocess.run([sys.executable, str(HERE / "ccx.py"), "--venv", args.venv, "--cc3220",
                        "--break-lead", str(lead), "--break-hold", str(hold), "-p", args.port, "--reset", "none"],
                       capture_output=True, text=True, cwd=ROOT)
    log = p.stdout + p.stderr
    rx = re.findall(r"\+(\d+\.\d+) s rx ([0-9a-f ]+)", log)
    nwp = re.search(r"network processor boot loader ([\d.]+)", log)
    err = re.search(r"CC3200Error: .*", log)
    return {"lead": lead, "hold": hold, "exit": p.returncode, "nwp": nwp.group(1) if nwp else None,
            "ack_times": [float(t) for t, d in rx if "00 cc" in d], "error": err.group(0)[:160] if err else None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--venv", required=True, help="cc3200tool's virtual environment")
    ap.add_argument("--port", required=True, help="the LaunchPad's Application/User UART, e.g. COM11")
    ap.add_argument("--probe", required=True, help="the XDS110's serial number (Windows' device ID shows it)")
    ap.add_argument("--window", action="append", help="LEAD:HOLD in seconds after the switch's ACK (repeatable)")
    ap.add_argument("--trials", type=int, default=5, help="sessions per window (default 5)")
    ap.add_argument("--settle", type=float, default=2.0, help="seconds between the reset and the session (default 2)")
    ap.add_argument("--reset-tool", type=Path, default=os.environ.get("XDS110RESET") or shutil.which("xds110reset"),
                    help="TI's xds110reset.exe (Uniflash's simplelink/imagecreator/bin/); default $XDS110RESET or the PATH")
    ap.add_argument("--out", type=Path, help="write all results into this JSON file")
    args = ap.parse_args()
    if not args.reset_tool or not Path(args.reset_tool).is_file():
        ap.error("xds110reset.exe not found: give --reset-tool or set XDS110RESET")
    args.reset_tool = Path(args.reset_tool)
    windows = [tuple(float(x) for x in w.split(":")) for w in (args.window or DEFAULT_WINDOWS)]
    results = []
    for lead, hold in windows:
        for k in range(args.trials):
            r = trial(args, lead, hold) | {"trial": k + 1}
            results.append(r)
            print(json.dumps(r), flush=True)
    for lead, hold in windows:
        rs = [r for r in results if (r["lead"], r["hold"]) == (lead, hold)]
        acks = [t for r in rs for t in r["ack_times"]]
        print(f"window {lead:.1f}-{lead + hold:.1f} s: {sum(1 for r in rs if r['nwp'])}/{len(rs)} caught; "
              f"ACK at {min(acks):.3f}-{max(acks):.3f} s" if acks else
              f"window {lead:.1f}-{lead + hold:.1f} s: 0/{len(rs)} caught")
    if args.out:
        args.out.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    return 0 if all(r["nwp"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
