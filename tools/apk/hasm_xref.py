"""Cross-references in a hermes-dec disassembly listing (hbc-disassembler output). Read-only.
  py -3.13 -I hasm_xref.py xref <hasm> <regex>      functions whose string operands match regex, with the matches
  py -3.13 -I hasm_xref.py strs <hasm> <fn#> [...]  the distinct strings each function uses, in order
  py -3.13 -I hasm_xref.py dump <hasm> <fn#> [...]  the listing of functions by number
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

FN = re.compile(r'^=> \[Function #(\d+) "([^"]*)"')
STR = re.compile(r"# String: '((?:[^'\\]|\\.)*)'")


def functions(path):
    cur, name, lines = None, None, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = FN.match(line)
            if m:
                if cur is not None:
                    yield cur, name, lines
                cur, name, lines = int(m.group(1)), m.group(2), []
            lines.append(line.rstrip("\n"))
    if cur is not None:
        yield cur, name, lines


def strings(lines):
    seen = []
    for line in lines:
        for s in STR.findall(line):
            if s not in seen:
                seen.append(s)
    return seen


cmd, path = sys.argv[1], sys.argv[2]
if cmd == "xref":
    rx = re.compile(sys.argv[3])
    for n, name, lines in functions(path):
        hits = [s for s in strings(lines) if rx.search(s)]
        if hits:
            print(f"#{n} {name!r} ({len(lines)} lines): " + " | ".join(h[:80] for h in hits))
elif cmd in ("dump", "strs"):
    want = {int(x) for x in sys.argv[3:]}
    for n, name, lines in functions(path):
        if n in want:
            print("\n".join(lines) if cmd == "dump" else f"#{n} {name!r}: " + " | ".join(strings(lines)))
else:
    sys.exit(__doc__)
