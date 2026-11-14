"""Read-only structure report for the files in a SimpleLink OTA bundle. Parses, never executes.
Usage: py -3.13 -I fw_inspect.py <dir-with-ota.cmd> [<file> ...] [--write-sigs DIR]
--write-sigs DIR: for every secured manifest entry with a signature, decode signature_base64 into DIR/<basename>.sig
next to a byte-identical copy of the file, and print a table (filename, size, signature bytes, certificate, digest)."""
import base64
import hashlib
import json
import math
import os
import re
import shutil
import sys


def entropy(b):
    if not b:
        return 0.0
    c = [0] * 256
    for x in b:
        c[x] += 1
    n = len(b)
    return -sum((k / n) * math.log2(k / n) for k in c if k)


def block_entropy(b, step=4096):
    return [round(entropy(b[i:i + step]), 2) for i in range(0, len(b), step)]


def strings(b, n=5):
    return re.findall(rb"[\x20-\x7e]{%d,}" % n, b)


def report(path):
    b = open(path, "rb").read()
    print(f"\n=== {path}  ({len(b)} bytes) ===")
    print(f"sha256 {hashlib.sha256(b).hexdigest()}")
    print(f"entropy {entropy(b):.3f} bits/byte   first32 {b[:32].hex()}")
    be = block_entropy(b)
    hi = sum(1 for e in be if e > 7.5)
    print(f"4K blocks {len(be)}  >7.5 bits: {hi}/{len(be)}  min {min(be)} max {max(be)}")
    sp = int.from_bytes(b[0:4], "little")
    rv = int.from_bytes(b[4:8], "little")
    print(f"u32[0]=0x{sp:08x}  u32[1]=0x{rv:08x}  (ARM Cortex-M: SP then reset vector)")
    ss = strings(b)
    print(f"ascii runs >=5: {len(ss)}")
    pat = re.compile(rb"(?i)\b(\d+\.\d+\.\d+|version|anova|cc32|cc26|simplelink|ti-rtos|build|"
                     rb"git|gcc|arm|freertos|servicepack|mcuimg|/sys/|\.bin)\b")
    seen, out = set(), []
    for s in ss:
        if pat.search(s) and s not in seen:
            seen.add(s)
            out.append(s.decode("latin-1"))
    for s in out[:60]:
        print("   ", s[:120])


def write_sigs(rows, out_dir):
    """rows: (manifest entry, local path or None, digest ok). Writes DIR/<basename> and DIR/<basename>.sig."""
    os.makedirs(out_dir, exist_ok=True)
    print(f"\nsignatures -> {out_dir}")
    print(f"{'filename':<24} {'size':>8} {'sig bytes':>9}  {'certificate':<18} digest")
    for e, cand, ok in rows:
        if not e.get("secured") or not e.get("signature_base64"):
            continue
        sig = base64.b64decode(e["signature_base64"], validate=True)
        warn = "" if len(sig) == 256 else "  WARNING: expected 256 bytes"
        if cand is None:
            print(f"{e['filename']:<24} {'missing':>8} {len(sig):>9}  {e['certificate'] or '-':<18} -{warn}")
            continue
        name = os.path.basename(e["filename"])
        shutil.copyfile(cand, os.path.join(out_dir, name))
        with open(os.path.join(out_dir, name + ".sig"), "wb") as f:
            f.write(sig)
        print(f"{e['filename']:<24} {os.path.getsize(cand):>8} {len(sig):>9}  {e['certificate'] or '-':<18} "
              f"{'OK' if ok else 'MISMATCH'}{warn}")


argv = sys.argv[1:]
sigs_dir = None
if "--write-sigs" in argv:
    i = argv.index("--write-sigs")
    sigs_dir = argv[i + 1]
    del argv[i:i + 2]

d = argv[0]
cmd = os.path.join(d, "ota.cmd")
rows = []
if os.path.exists(cmd):
    manifest = json.load(open(cmd))
    print("ota.cmd digest check (sha256 of content vs manifest):")
    base = d
    for e in manifest:
        fn = e["filename"].lstrip("/")
        # files live under 1/, 2/ ... next to ota.cmd's parent; search for them
        cand = None
        for root, _, files in os.walk(os.path.dirname(d)):
            for f in files:
                if os.path.join(root, f).replace("\\", "/").endswith(fn):
                    cand = os.path.join(root, f)
        if cand:
            h = hashlib.sha256(open(cand, "rb").read()).hexdigest()
            ok = "OK " if h == e["digest"] else "MISMATCH"
            print(f"  [{ok}] secured={e['secured']} {e['filename']}")
            rows.append((e, cand, h == e["digest"]))
        else:
            print(f"  [missing] {e['filename']}")
            rows.append((e, None, False))
    if sigs_dir is not None:
        write_sigs(rows, sigs_dir)

for p in argv[1:]:
    report(p)
