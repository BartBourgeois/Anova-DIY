"""Back up the cooker's Bluetooth chip (U7, CC2640R2F): its 128 KiB flash over cJTAG, until two reads are equal.

The probe is an XDS110 (the CC3220S LaunchPad's own) on U7's TMSC and TCKC test points; TI's DSLite (from Uniflash)
does the reading. The procedure, wiring and pictures: docs/flashbackup/10-cooker-u7.md (J-228).

Read-only by construction: DSLite is only ever started in its `memory` mode, which copies target memory into a file
(no flash loader, no erase, no program). Nothing here starts its `flash` or `load` modes. The probe configuration
(cc2640r2f_xds110_cjtag.ccxml, next to this script) is checked before every run: target-supplied power, 2-pin cJTAG,
the CC2640R2F.

  u7read.py ccfg --out <dir>
      the connect test: only the CCFG (the flash's last 88 bytes, where debug and the boot loader are configured),
      read once and decoded. Run it first: if debug is locked, the connect fails here and nothing else is tried.
  u7read.py read --out <dir> --name <stem> [--label "..."]
      reads the whole flash into <stem>_1.bin, <stem>_2.bin, ... until two reads are equal (at most --max-reads),
      writes <stem>.json (DSLite's version, the configuration's SHA-256, every read, the verdict, the CCFG and the
      comparison below) and <stem>.log (DSLite's output); never overwrites a file
  u7read.py compare <image.bin> [--ref NAME=PATH ...]
      per 4 KiB sector: which known image it equals, erased (all FF), or other. The known images by default: the
      CC2640 image the cooker's own flash holds committed (the old app's partner, the backup's extract) and 3.3.35's
  u7read.py pair <a>.json <b>.json --name <stem>
      one manifest from several sessions: U7 answers once per power-up (later connects fail with "router subpath",
      Error -242, J-233), so each session gives one read; two equal ones across power cycles are the backup
  u7read.py check <stem>.json
      re-hashes the files a manifest names
Exit 0 = verified (read) or all match (check, compare equal to a known image); 1 = no two reads equal, a changed
file, or an image that matches no known one; 2 = refused, or DSLite failed.

Standard library only.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CCXML = HERE / "cc2640r2f_xds110_cjtag.ccxml"
DSLITE_IN_UNIFLASH = Path("deskdb/content/TICloudAgent/win/ccs_base/DebugServer/bin/DSLite.exe")
UNIFLASH = Path(os.environ.get("SystemDrive", "C:") + os.sep, "ti", "uniflash_9.7.1")  # TI's default install
FLASH_SIZE = 0x20000                # CC2640R2F: 128 KiB at address 0 (SWRS204)
SECTOR = 0x1000                     # its flash sector, 4 KiB
CCFG_AT, CCFG_LEN = 0x1FFA8, 0x58   # the last 88 bytes (TI hw_ccfg.h, CC26x0R2)
# DSLite's --range length counts 32-bit words on this target (`likely`, J-233): 0x1FFA8 plus 0x58 ran into 0x20000,
# which 0x58 bytes wouldn't reach. The size check below tells if that's wrong.
UNIT = 4
REFS = {                            # SHA-256 pinned: a ref file that differs is refused
    "old": (REPO / "dumps/cooker/2026-11-06/extract/sys/cc2640.bin",
            "0f4d7ede27f9b8c48cdb8ada6b332d8c45a8880a6e13be756e5d14c5e76e34be"),
    "3.3.35": (REPO / "dumps/ota/2026-11-05/extract/pro-controller-3.3.35/ota/2/sys/cc2640.bin",
               "e267c585143515a55fb8347be544627f84b360b84b5f4da8d2280c36c3763b01"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_ccxml(path: Path) -> str:
    """Refuse a configuration that would power the target from the probe, or isn't cJTAG on a CC2640R2F."""
    root = ET.parse(path).getroot()
    props = {p.get("id"): p.get("Value") for p in root.iter("property")}
    devices = [i.get("href") for i in root.iter("instance") if "devices/" in (i.get("href") or "")]
    if props.get("Power Selection") != "0":
        raise SystemExit(f"{path.name}: 'Power Selection' must be 0 (target supplied power): the probe would feed "
                         "the cooker's 3.3 V rail")
    if props.get("SWD Mode Settings") != "4" or devices != ["devices/cc2640r2f.xml"]:
        raise SystemExit(f"{path.name}: not 2-pin cJTAG on a CC2640R2F")
    return sha256(path.read_bytes())


class Dslite:
    def __init__(self, exe: Path, ccxml: Path, log):
        self.exe, self.ccxml, self.log = exe, ccxml, log

    def memory(self, address: int, length: int, out: Path, timeout: float) -> None:
        """Read `length` bytes from `address` into `out`."""
        cmd = [str(self.exe), "memory", f"--config={self.ccxml}", f"--range=0x{address:X},0x{length // UNIT:X}",
               f"--output={out}", "--verbose"]
        self.log.write(f"\n$ {' '.join(cmd)}\n")
        self.log.flush()
        try:
            run = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"DSLite stalled: killed after {timeout:.0f} s")
        text = (run.stdout + run.stderr).strip()
        self.log.write(text + "\n")
        self.log.flush()
        if run.returncode != 0 or not out.is_file():
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            fatal = [line for line in lines if line.startswith(("fatal:", "Failed:", "Error"))]
            raise RuntimeError(f"DSLite exit {run.returncode}: " + (fatal[0] if fatal else " / ".join(lines[-3:])))
        if out.stat().st_size != length:
            got = out.stat().st_size
            raise RuntimeError(f"DSLite wrote {got} bytes for {length // UNIT} units: a unit is "
                               f"{got / (length // UNIT):g} bytes here, not {UNIT} (set UNIT); nothing is wrong with "
                               "the chip")


def decode_ccfg(ccfg: bytes) -> dict:
    """The CCFG fields that decide debug and the boot loader (offsets in the last 88 bytes, TI hw_ccfg.h)."""
    def u32(off):
        return int.from_bytes(ccfg[off:off + 4], "little")
    bl, tap0 = u32(0x30), u32(0x3C)
    return {
        "erased": ccfg == b"\xff" * CCFG_LEN,
        "BL_CONFIG": f"0x{bl:08x}", "TAP_DAP_0": f"0x{tap0:08x}", "TAP_DAP_1": f"0x{u32(0x40):08x}",
        "IMAGE_VALID_CONF": f"0x{u32(0x44):08x}", "ERASE_CONF": f"0x{u32(0x34):08x}",
        "PROT": [f"0x{u32(off):08x}" for off in (0x48, 0x4C, 0x50, 0x54)],
        "cpu_dap_enabled": (tap0 & 0xFF) == 0xC5,
        "rom_boot_loader_enabled": (bl >> 24) == 0xC5,
        "backdoor": {"enabled": (bl & 0xFF) == 0xC5, "dio": (bl >> 8) & 0xFF, "active_high": bool(bl >> 16 & 1)},
        "image_valid": u32(0x44) == 0,
    }


def print_ccfg(c: dict) -> None:
    if c["erased"]:
        print("  CCFG: erased (all FF): the last sector was erased and not written again")
        return
    bd = c["backdoor"]
    print(f"  CCFG: CPU debug {'open' if c['cpu_dap_enabled'] else 'LOCKED'}; ROM boot loader "
          f"{'enabled' if c['rom_boot_loader_enabled'] else 'disabled'}; backdoor "
          f"{'DIO%d active %s' % (bd['dio'], 'high' if bd['active_high'] else 'low') if bd['enabled'] else 'off'}; "
          f"image {'valid' if c['image_valid'] else 'NOT valid (the ROM boot loader runs instead)'}")
    print(f"        BL_CONFIG {c['BL_CONFIG']}  TAP_DAP_0 {c['TAP_DAP_0']}  IMAGE_VALID_CONF {c['IMAGE_VALID_CONF']}")


def load_refs(pairs) -> dict:
    refs = {}
    for name, (path, digest) in REFS.items():
        if path.is_file():
            data = path.read_bytes()
            if sha256(data) != digest:
                raise SystemExit(f"reference {name}: {path} isn't the file it should be ({digest[:8]}...)")
            refs[name] = data
    for pair in pairs or []:
        name, _, path = pair.partition("=")
        refs[name] = Path(path).read_bytes()
    return {k: v for k, v in refs.items() if len(v) == FLASH_SIZE}


def compare(image: bytes, refs: dict) -> dict:
    """Which known image each 4 KiB sector equals; runs of equal verdicts merged."""
    whole = [name for name, ref in refs.items() if ref == image]
    runs = []
    for s in range(FLASH_SIZE // SECTOR):
        chunk = image[s * SECTOR:(s + 1) * SECTOR]
        same = [name for name, ref in refs.items() if ref[s * SECTOR:(s + 1) * SECTOR] == chunk]
        verdict = "+".join(same) if same else "erased" if chunk == b"\xff" * SECTOR else "other"
        if runs and runs[-1][2] == verdict:
            runs[-1][1] = s
        else:
            runs.append([s, s, verdict])
    return {"equal_to": whole, "sectors": [{"from": a, "to": b, "is": v} for a, b, v in runs]}


def print_compare(c: dict, refs: dict) -> None:
    print(f"  known images: {', '.join(f'{k} ({sha256(v)[:8]}...)' for k, v in refs.items()) or 'none found'}")
    if c["equal_to"]:
        print(f"  EQUAL to {' and '.join(c['equal_to'])}")
        return
    print("  equal to no known image; per 4 KiB sector:")
    for r in c["sectors"]:
        span = f"{r['from']}" if r["from"] == r["to"] else f"{r['from']}-{r['to']}"
        print(f"    sectors {span:7} (0x{r['from'] * SECTOR:05x}-0x{(r['to'] + 1) * SECTOR - 1:05x}): {r['is']}")


def exe_path(args) -> Path:
    uniflash = Path(os.environ.get("UNIFLASH", UNIFLASH))
    exe = Path(args.dslite or os.environ.get("DSLITE") or uniflash / DSLITE_IN_UNIFLASH)
    if not exe.is_file():
        raise SystemExit(f"{exe}: DSLite not found; give --dslite, or set DSLITE (the exe) or UNIFLASH (its folder)")
    return exe


def cmd_ccfg(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target, log_path = out / f"u7_ccfg-{stamp}.bin", out / f"u7_ccfg-{stamp}.log"
    check_ccxml(CCXML)
    with log_path.open("w", encoding="utf-8") as log:
        try:
            Dslite(exe_path(args), CCXML, log).memory(CCFG_AT, CCFG_LEN, target, timeout=120)
        except RuntimeError as e:
            print(f"u7read.py: {e}\n  log: {log_path}", file=sys.stderr)
            return 2
    print(f"connected: {target.name}, {CCFG_LEN} bytes from 0x{CCFG_AT:05x}")
    print_ccfg(decode_ccfg(target.read_bytes()))
    return 0


def cmd_read(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path, log_path = out / f"{args.name}.json", out / f"{args.name}.log"
    planned = [out / f"{args.name}_{k}.bin" for k in range(1, args.max_reads + 1)] + [manifest_path, log_path]
    existing = [str(p) for p in planned if p.exists()]
    if existing:
        print("u7read.py: refusing to overwrite:\n  " + "\n  ".join(existing), file=sys.stderr)
        return 2
    ccxml_sha = check_ccxml(CCXML)
    refs = load_refs(args.ref)
    exe = exe_path(args)
    m = {"tool": "tools/flashbackup/u7read.py", "started": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
         "host": platform.node(), "os": platform.platform(), "dslite": str(exe),
         "ccxml": {"file": CCXML.name, "sha256": ccxml_sha}, "chip": "CC2640R2F (U7)", "size": FLASH_SIZE,
         "label": args.label, "reads": [], "verdict": None}
    hashes = []
    with log_path.open("w", encoding="utf-8") as log:
        dsl = Dslite(exe, CCXML, log)
        for k in range(1, args.max_reads + 1):
            path = out / f"{args.name}_{k}.bin"
            t0 = time.monotonic()
            try:
                dsl.memory(0, FLASH_SIZE, path, timeout=args.read_timeout)
            except RuntimeError as e:
                print(f"u7read.py: read {k}: {e}", file=sys.stderr)
                m["reads"].append({"file": path.name, "error": str(e)})
                continue
            secs = round(time.monotonic() - t0, 1)
            digest = sha256(path.read_bytes())
            m["reads"].append({"file": path.name, "bytes": FLASH_SIZE, "sha256": digest, "seconds": secs})
            print(f"read {k}: {path.name}  {FLASH_SIZE} bytes  {secs} s  sha256 {digest}")
            hashes.append(digest)
            pairs = [h for h in set(hashes) if hashes.count(h) >= 2]
            if pairs:
                m["verdict"], m["sha256"] = "verified", pairs[0]
                break
    m["verdict"] = m["verdict"] or "no two reads equal"
    m["finished"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    if m["verdict"] == "verified":
        image = next((out / r["file"]).read_bytes() for r in m["reads"] if r.get("sha256") == m["sha256"])
        m["ccfg"] = decode_ccfg(image[CCFG_AT:CCFG_AT + CCFG_LEN])
        m["compare"] = compare(image, refs)
    manifest_path.write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    if m["verdict"] != "verified":
        print("NOT VERIFIED: no two reads are equal. Probe off, supply off; check the two leads and GND, then read "
              "again into a new --name. Keep these files: they are evidence.", file=sys.stderr)
        return 1
    same = [r["file"] for r in m["reads"] if r.get("sha256") == m["sha256"]]
    print(f"VERIFIED: {', '.join(same)} are equal, sha256 {m['sha256']}\nmanifest: {manifest_path}")
    print_ccfg(m["ccfg"])
    print_compare(m["compare"], refs)
    return 0


def cmd_compare(args) -> int:
    image = Path(args.image).read_bytes()
    if len(image) != FLASH_SIZE:
        raise SystemExit(f"{args.image}: {len(image)} bytes, not {FLASH_SIZE}")
    refs = load_refs(args.ref)
    c = compare(image, refs)
    print(f"{args.image}: sha256 {sha256(image)}")
    print_ccfg(decode_ccfg(image[CCFG_AT:CCFG_AT + CCFG_LEN]))
    print_compare(c, refs)
    return 0 if c["equal_to"] else 1


def cmd_pair(args) -> int:
    """One manifest from several sessions' reads: U7 answers once per power-up (J-233, J-234)."""
    sessions = [Path(p) for p in args.manifests]
    if len({s.parent.resolve() for s in sessions}) != 1:
        raise SystemExit("the manifests must lie in one directory (their files are named relative to it)")
    out = sessions[0].parent
    target = out / f"{args.name}.json"
    if target.exists():
        print(f"u7read.py: refusing to overwrite {target}", file=sys.stderr)
        return 2
    reads = []
    for s in sessions:
        for r in json.loads(s.read_text(encoding="utf-8")).get("reads", []):
            if "sha256" in r:
                ok = sha256((out / r["file"]).read_bytes()) == r["sha256"]
                reads.append({**r, "session": s.name, "file_still_matches": ok})
    hashes = [r["sha256"] for r in reads if r["file_still_matches"]]
    pairs = [h for h in set(hashes) if hashes.count(h) >= 2]
    made = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    m = {"tool": "tools/flashbackup/u7read.py pair", "made": made,
         "sessions": [s.name for s in sessions], "chip": "CC2640R2F (U7)", "size": FLASH_SIZE, "reads": reads,
         "verdict": "verified" if pairs else "no two reads equal"}
    if pairs:
        m["sha256"] = pairs[0]
        image = next((out / r["file"]).read_bytes() for r in reads if r["sha256"] == pairs[0])
        m["ccfg"] = decode_ccfg(image[CCFG_AT:CCFG_AT + CCFG_LEN])
        m["compare"] = compare(image, load_refs(args.ref))
    target.write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    if not pairs:
        print("NOT VERIFIED: no two reads are equal across these sessions", file=sys.stderr)
        return 1
    same = [f"{r['file']} ({r['session']})" for r in reads if r["sha256"] == pairs[0]]
    print(f"VERIFIED: {', '.join(same)} are equal, sha256 {m['sha256']}\nmanifest: {target}")
    print_ccfg(m["ccfg"])
    print_compare(m["compare"], load_refs(args.ref))
    return 0


def cmd_check(args) -> int:
    path = Path(args.manifest)
    m = json.loads(path.read_text(encoding="utf-8"))
    bad = 0
    for r in m.get("reads", []):
        if "sha256" not in r:
            continue
        f = path.parent / r["file"]
        ok = f.exists() and sha256(f.read_bytes()) == r["sha256"]
        bad += not ok
        print(f"{'ok' if ok else 'missing' if not f.exists() else 'CHANGED':9} {f}")
    print(f"verdict in the manifest: {m.get('verdict')}; sha256 {m.get('sha256', '-')}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True
    c = sub.add_parser("ccfg", help="connect test: read and decode the CCFG only")
    c.add_argument("--out", required=True, help="directory (outside git: dumps/...)")
    r = sub.add_parser("read", help="read the whole flash until two reads are equal")
    r.add_argument("--out", required=True, help="directory for the dumps (outside git: dumps/...)")
    r.add_argument("--name", required=True, help="file stem, e.g. u7_jtag -> u7_jtag_1.bin, u7_jtag_2.bin")
    r.add_argument("--max-reads", type=int, default=3, help="stop after this many reads (default 3)")
    r.add_argument("--read-timeout", type=float, default=300, help="seconds before a read counts as stalled")
    r.add_argument("--label", default="", help="free text for the manifest: board, setup")
    for p in (c, r):
        p.add_argument("--dslite", default="",
                       help="DSLite.exe (default: $DSLITE, then the one in $UNIFLASH, then TI's default Uniflash)")
    for p in (r, sub.add_parser("compare", help="compare an image with the known ones, sector by sector")):
        p.add_argument("--ref", action="append", help="another known image, NAME=PATH (repeatable)")
    sub.choices["compare"].add_argument("image")
    pr = sub.add_parser("pair", help="one verified manifest from several sessions' reads (one read per power-up)")
    pr.add_argument("manifests", nargs="+", help="the sessions' <stem>.json, in one directory")
    pr.add_argument("--name", required=True, help="stem of the combined manifest, e.g. u7_backup")
    pr.add_argument("--ref", action="append", help="another known image, NAME=PATH (repeatable)")
    k = sub.add_parser("check", help="re-hash the files of a manifest")
    k.add_argument("manifest")
    args = ap.parse_args()
    if args.cmd == "read" and args.max_reads < 2:
        ap.error("--max-reads must be at least 2")
    return {"ccfg": cmd_ccfg, "read": cmd_read, "compare": cmd_compare, "pair": cmd_pair,
            "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
