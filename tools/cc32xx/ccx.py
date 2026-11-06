"""Run cc3200tool, the CC32xx ROM-bootloader client, read-only by default and with a log of every run.

cc3200tool (toniebox-reverse-engineering fork) is installed in a virtual environment outside the repository, named
with --venv DIR or the CC3200TOOL_VENV environment variable. This wrapper starts that environment's Python with -I
(nothing from the current directory gets imported), calls cc3200tool's main() and hands the arguments through,
after one check:

- the reading subcommands list_filesystem, read_file, read_all_files and read_flash run as they are, and so does a
  run without a subcommand (connect, print the ROM's version info, stop);
- everything else (write_file, write_all_files, write_flash, format_flash, erase_file, dll_data_test, an unknown
  subcommand, and --reboot-to-app, which can pulse the reset line) is refused with exit code 2 before anything
  opens, unless --write and --backup-sha256 <SHA-256 of the verified flash dump> are both given (rule 1: no write
  without a backup read twice with the same hash). The hash goes into the log.

With --write, a pre-flight check runs before anything opens, and the run is refused (exit code 2) unless:

- the backup is there twice: at least two files under dumps/ (whole 4 KiB blocks) hash to --backup-sha256;
- every write_file sends a file that a TI OTA manifest (ota.cmd) under dumps/ lists under the same device path with
  the same SHA-256; a secured entry needs --signature, a file of exactly 256 bytes equal to that entry's
  signature_base64, and an unsecured entry takes none (cc3200tool reads only the first 256 bytes and checks the
  length after it has erased the old file and uploaded the new one);
- every write_flash sends the backup itself (its SHA-256 is --backup-sha256).

A signed write_file (a secure file) further needs --cc3220 (TI's close, with the certificate's name), --cert equal to
the manifest's certificate, and --no-verify (reading a secure file back raises a security alert); J-174.

What the check matched (the backup's copies, the manifest entry) goes into the log.

Always, write or not: read_file of a secure file is refused before the port opens. On a CC3220S, an operation on a
secure file without its token raises a security alert, and at the threshold (3 by default) the device locks (TI
SWRU455M section 8.14; one alert on the LaunchPad from a file-info query of /sys/mcuimg.bin, J-173). Secure means TI's
system images (SECURE_FILES) or any file an OTA manifest (ota.cmd) under dumps/ marks secured. A name the tool can't
know about may be secure too: ask only for files known to be plain.

--cc3220 replaces cc3200tool's connect step for a chip whose ROM boot loader it refuses ("Unsupported device": it
takes chip type & 0x10 for a CC3200, but TI's SWPA230A table says that bit means the CC3220 family, 0x18 = CC3220S,
and the tool's switch only handles boot-loader versions 4 and up; the LaunchPad's CC3220S reports 0.1.0.3). With it,
only TI's step 3 runs (cc3220_connect.py): Switch UART to APPS MCU (0x33, delay 26666667), the break held for a
window (--break-lead S after the switch's ACK, for --break-hold S), the version query, which must come from the
network processor's boot loader. The RAM patch of TI's steps 4-7 (an SRAM erase and write, then execute from RAM)
is left out, and nothing touches the flash. A missed break is an error: the network processor then runs its own
firmware, which writes to the flash (J-160); reset before anything else.

--rom-only (J-200) stops after the ROM boot loader's version reply: the break and one version query, no switch,
so the network processor never starts; for a chip whose flash has no backup yet. It takes no subcommand.

--status (with --cc3220; --fs-usage is the same) then prints Image Creator's "Device status" panel from three reads:
TI's GET_FS_USAGE (0x37: mode, capacity, free space, security alerts and threshold), GET_STORAGE_INFO of the serial
flash (0x31: its size and ID bytes) and GET_DEVICE_PARAM (0x3A, parameter 0: the default MAC); J-194, J-195.

Each run appends .capture/cc32xx/<YYYYMMDD-HHMMSS>_<subcommand>.log at the repository root (gitignored): the PC's
time, the exact command line, the backup hash if any, the child's output (stdout and stderr together, also shown
on the console) and its exit code, which is also this script's. Everything after -- goes to cc3200tool untouched.

Usage:
  py -3.13 tools/cc32xx/ccx.py --venv <dir> -p COM7 --reset prompt list_filesystem
  py -3.13 tools/cc32xx/ccx.py --venv <dir> -p COM7 --reset prompt read_flash dumps/<unit>/u15_a.bin
  py -3.13 tools/cc32xx/ccx.py --venv <dir> -if dumps/<unit>/u15_a.bin -d cc32xx list_filesystem --extended
  py -3.13 tools/cc32xx/ccx.py --venv <dir> --write --backup-sha256 <hash> -p COM7 write_file <local> <name>
  py -3.13 tools/cc32xx/ccx.py --venv <dir> --cc3220 -p COM7 --reset none read_flash dumps/<unit>/u8_bl_1.bin
  py -3.13 tools/cc32xx/ccx.py --venv <dir> --cc3220 --status -p COM7 --reset none   # Uniflash's device status
  py -3.13 tools/cc32xx/ccx.py --venv <dir> --rom-only -p COM7 --reset none         # alive? ROM version only
  py -3.13 tools/cc32xx/ccx.py --venv <dir> -- --help          # cc3200tool's own help
"""

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / ".capture" / "cc32xx"
DUMPS = ROOT / "dumps"
BLOCK = 4096  # a flash dump is whole erase blocks
SUBCOMMANDS = {"format_flash", "erase_file", "write_file", "read_file", "write_flash", "read_flash",
               "list_filesystem", "read_all_files", "write_all_files", "dll_data_test"}
READ_ONLY = {"list_filesystem", "read_file", "read_all_files", "read_flash"}
# cc3200tool's global options that take a value: the value is never a subcommand
VALUE_OPTIONS = {"-p", "--port", "-if", "--image_file", "-of", "--output_file", "--reset", "--sop2",
                 "--erase_timeout", "-d", "--device", "-rw", "--reset-wait"}
CHILD = "import sys; sys.argv[0] = 'cc3200tool'; from cc3200tool.cc import main; main()"
# --cc3220: TI's step 3 only (SWPA230A 5.3.3), in place of cc3200tool's switch_to_nwp_bootloader (cc3220_connect.py)
CHILD_CC3220 = f"import sys; sys.path.insert(0, {str(Path(__file__).resolve().parent)!r}); import cc3220_connect; cc3220_connect.run()"


def split_args(argv):
    """Wrapper options come first; the rest belongs to cc3200tool.
    Returns (venv, write, sha, cc3220, rest) or None for help."""
    venv, write, sha, cc3220, i = os.environ.get("CC3200TOOL_VENV"), False, None, False, 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            return None
        if a == "--venv" and i + 1 < len(argv):
            venv, i = argv[i + 1], i + 2
        elif a.startswith("--venv="):
            venv, i = a[7:], i + 1
        elif a == "--write":
            write, i = True, i + 1
        elif a == "--cc3220":
            cc3220, i = True, i + 1
        elif a == "--cert" and i + 1 < len(argv):
            os.environ["CCX_CERT"], i = argv[i + 1], i + 2
        elif a == "--rom-only":
            os.environ["CCX_ROM_ONLY"], cc3220, i = "1", True, i + 1
        elif a in ("--status", "--fs-usage"):
            os.environ["CCX_STATUS"], i = "1", i + 1
        elif a in ("--break-lead", "--break-hold") and i + 1 < len(argv):
            os.environ["CCX_BREAK_" + a[8:].upper()], i = argv[i + 1], i + 2
        elif a == "--backup-sha256" and i + 1 < len(argv):
            sha, i = argv[i + 1], i + 2
        else:
            break
    rest = argv[i:]
    return venv, write, sha, cc3220, rest[1:] if rest[:1] == ["--"] else rest


def refusals(rest):
    """Why this command line is not a read. Empty for the allowed subcommands and a connect-only run."""
    why, seen_sub, skip = [], False, False
    for tok in rest:
        if skip:
            skip = False
        elif tok in SUBCOMMANDS:
            seen_sub = True
            if tok not in READ_ONLY:
                why.append(f"{tok} writes or erases")
        elif tok == "--reboot-to-app":
            why.append("--reboot-to-app can pulse the reset line")
        elif not seen_sub:
            if tok in VALUE_OPTIONS:
                skip = True
            elif not tok.startswith("-"):
                why.append(f"unknown subcommand {tok!r}")
    return why


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def _parser(name, *positionals, flags=(), values=()):
    p = _Parser(prog=name, add_help=False)
    for a in positionals:
        p.add_argument(a)
    for a in flags:
        p.add_argument(a, action="store_true")
    for a in values:
        p.add_argument(a)
    return p


# Files a CC3220S keeps secure: asking for one without its token raises a security alert (J-173)
SECURE_FILES = {"/sys/mcuimg.bin", "/sys/mcuimg1.bin", "/sys/mcuimg2.bin", "/sys/mcuimg3.bin",
                "/sys/servicepack.ucf", "/sys/certstore.lst", "/sys/factory.img"}
READ_PARSER = _parser("read_file", "cc_filename", "local_file", flags=("--inactive", "--no-verify"),
                      values=("--file-id",))

# the write subcommands that carry an image, with cc3200tool's own options (cc.py, v1.3.0)
WRITE_PARSERS = {
    "write_file": _parser("write_file", "local_file", "cc_filename", flags=("--commit-flag", "--no-verify"),
                          values=("--signature", "--file-size", "--file-id")),
    "write_flash": _parser("write_flash", "gang_image_file", flags=("--no-erase", "--no-verify")),
}


def sections(rest):
    """cc3200tool's own split (split_argv): a new section at every subcommand name. Returns [(subcommand, args)]."""
    out = []
    for tok in rest:
        if tok in SUBCOMMANDS:
            out.append((tok, []))
        elif out:
            out[-1][1].append(tok)
    return out


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def dumps_with(sha):
    """Files under dumps/ that are whole 4 KiB blocks and hash to sha: the copies of a flash dump."""
    return sorted(p for p in DUMPS.rglob("*")
                  if p.is_file() and (n := p.stat().st_size) and n % BLOCK == 0 and sha256(p) == sha)


def manifest_entries():
    """(manifest, entry) for every file entry of every TI OTA manifest (ota.cmd) under dumps/."""
    out = []
    for m in sorted(DUMPS.rglob("ota.cmd")):
        try:
            entries = json.loads(m.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(entries, list):
            out += [(m, e) for e in entries if isinstance(e, dict) and "filename" in e and "digest" in e]
    return out


def sig_problem(entry, sig):
    """Why the --signature file sig (a Path or None) doesn't go with this manifest entry, or None if it does."""
    if str(entry.get("secured")) != "1":
        return "the manifest entry isn't secured, so no --signature" if sig else None
    if sig is None:
        return "the manifest entry is secured: --signature needed"
    if not sig.is_file():
        return f"no signature file {sig}"
    data = sig.read_bytes()
    if len(data) != 256:
        return f"{sig} is {len(data)} bytes, not 256"
    try:
        want = base64.b64decode(entry.get("signature_base64") or "", validate=True)
    except ValueError:  # binascii.Error
        want = b""
    return None if data == want else f"{sig} is not the manifest's signature for this file"


def preflight(rest, sha, cc3220=False):
    """The checks before a write (see the module docstring). Returns (problems, notes for the log)."""
    problems, notes, entries = [], [], None
    copies = dumps_with(sha)
    if len(copies) < 2:
        problems.append(f"the backup {sha} is in {len(copies)} file(s) under dumps/; rule 1 needs two equal reads")
    notes += [f"# backup copy {p.relative_to(ROOT)}" for p in copies]
    for sub, args in sections(rest):
        if sub not in WRITE_PARSERS:
            continue
        try:
            a = WRITE_PARSERS[sub].parse_args(args)
        except ValueError as e:
            problems.append(f"{sub}: {e}")
            continue
        img = Path(a.gang_image_file if sub == "write_flash" else a.local_file)
        if not img.is_file():
            problems.append(f"{sub}: no file {img}")
            continue
        h = sha256(img)
        if sub == "write_flash":
            if h != sha:
                problems.append(f"write_flash: {img} is not the backup (SHA-256 {h})")
            else:
                notes.append(f"# write_flash {img}: the backup")
            continue
        if entries is None:
            entries = manifest_entries()
        sig = Path(a.signature) if a.signature else None
        hits = [(m, e) for m, e in entries if e["filename"] == a.cc_filename and str(e["digest"]).lower() == h]
        if not hits:
            problems.append(f"write_file: no OTA manifest under dumps/ lists {a.cc_filename} with SHA-256 {h}")
            continue
        why = [sig_problem(e, sig) for _, e in hits]
        if None not in why:
            problems.append(f"write_file {a.cc_filename}: {why[0]}")
            continue
        m, e = hits[why.index(None)]
        if sig:  # a signed write on a CC3220S (J-174): TI's close with the certificate, and no read-back of a secure file
            cert = os.environ.get("CCX_CERT", "")
            if not cc3220:
                problems.append(f"write_file {a.cc_filename}: a signed write needs --cc3220 (cc3200tool's own close puts "
                                "the signature at the wrong offset on a CC3220, J-174)")
            if cert != e.get("certificate"):
                problems.append(f"write_file {a.cc_filename}: --cert must be the manifest's certificate "
                                f"{e.get('certificate')!r}, not {cert!r}")
            if not a.no_verify:
                problems.append(f"write_file {a.cc_filename}: a secure file needs --no-verify (reading it back raises a "
                                "security alert, J-173)")
        notes.append(f"# write_file {img} -> {a.cc_filename}: SHA-256 {h} as in {m.relative_to(ROOT)}"
                     + (f", signature {sig} as in the manifest" if sig else ", unsecured"))
    return problems, notes


def secure_reads(rest):
    """Why a read_file in this command line would touch a secure file (see the module docstring), as a list."""
    names = SECURE_FILES | {str(e["filename"]) for _, e in manifest_entries() if str(e.get("secured")) == "1"}
    why = []
    for sub, args in sections(rest):
        if sub != "read_file":
            continue
        try:
            name = READ_PARSER.parse_args(args).cc_filename
        except ValueError as e:
            why.append(f"read_file: {e}")
            continue
        if name in names:
            why.append(f"read_file {name}: a secure file; asking for it without its token raises a security alert "
                       "(J-173)")
    return why


def main() -> int:
    parsed = split_args(sys.argv[1:])
    if parsed is None:
        print(__doc__)
        return 0
    venv, write, sha, cc3220, rest = parsed
    err = lambda msg: print(f"ccx: {msg}", file=sys.stderr) or 2  # noqa: E731
    if sha is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", sha):
        return err("--backup-sha256 must be 64 hex digits")
    if write and sha is None:
        return err("--write needs --backup-sha256 <sha256 of the dump, read twice with the same hash>")
    if os.environ.get("CCX_ROM_ONLY") == "1" and (any(t in SUBCOMMANDS for t in rest) or write
                                                or os.environ.get("CCX_STATUS") == "1"):
        return err("--rom-only is a connect-only run: no subcommand, no --write, no --status")
    if os.environ.get("CCX_STATUS") == "1" and not cc3220:
        return err("--status needs --cc3220 (the queries go to the network processor's boot loader)")
    secure = secure_reads(rest)
    if secure:
        return err("refused, nothing sent:\n  " + "\n  ".join(secure))
    why = refusals(rest)
    if why and not write:
        return err("refused (read-only run): " + "; ".join(why) + ". Add --write --backup-sha256 <hash> on purpose.")
    checked = []
    if why:
        problems, checked = preflight(rest, sha.lower(), cc3220)
        if problems:
            return err("refused (pre-flight check), nothing sent:\n  " + "\n  ".join(problems))
    if not venv:
        return err("no virtual environment: give --venv DIR or set CC3200TOOL_VENV")
    python = Path(venv) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        return err(f"no Python in the virtual environment: {python}")
    cmd = [str(python), "-I", "-u", "-c", CHILD_CC3220 if cc3220 else CHILD, *rest]
    label = next((t for t in rest if t in SUBCOMMANDS), "help" if {"-h", "--help"} & set(rest) else "connect")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}_{label}.log"
    console = [sys.stdout.buffer]  # emptied when the console goes away (a closed pipe); the file keeps everything
    with path.open("ab") as f:

        def tee(data: bytes) -> None:
            f.write(data)
            f.flush()
            for out in console:
                try:
                    out.write(data)
                    out.flush()
                except OSError:
                    console.clear()
                    os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())

        def note(text: str) -> None:
            tee((text + "\n").encode("utf-8", errors="replace"))

        note(f"# ccx {dt.datetime.now().isoformat(timespec='milliseconds')}  cwd={os.getcwd()}")
        note(f"# cmd {subprocess.list2cmdline(cmd)}")
        note(f"# write={'yes' if write else 'no'}  backup-sha256={(sha or '-').lower()}")
        for line in checked:
            note(line)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            while chunk := proc.stdout.read1(4096):
                tee(chunk)
        except KeyboardInterrupt:
            note("# interrupted (Ctrl+C)")
        rc = proc.wait()
        rc = rc - (1 << 32) if rc > 0x7FFFFFFF else rc  # cc3200tool exits -1..-4 on errors; Windows reports them unsigned
        note(f"\n# exit {rc} at {dt.datetime.now().isoformat(timespec='milliseconds')}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
