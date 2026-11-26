"""Print the hermes-dec function that encloses a line of a decompiled bundle, condensed.

hermes-dec's decompile (`bundle.js`) is register code: one function per `function(...) { // Original name: X`
line, its body indented one level deeper, closed by a `}` at the header's indent. This finds the innermost
function around a line (or around every match of a regex), and prints it with the noise left out: `case N:`
labels, jumps, register moves that carry no literal or name. What stays are string and number literals, property
reads (`.name`), calls, object literals and `Original name` headers, which is what an API map needs.

Read-only. The bundle is untrusted input: run with `py -3.13 -I`, paths as arguments.

    py -3.13 -I tools/apk/jsfunc.py <bundle.js> line 465201 [--full] [--outer N]
    py -3.13 -I tools/apk/jsfunc.py <bundle.js> grep "recipesAPIClient" [--full] [--max 40]
    py -3.13 -I tools/apk/jsfunc.py <bundle.js> names "(?i)^(get|post|put|patch|delete)"   # functions by name
"""
import argparse
import re
import sys

HDR = re.compile(r"^(\s*).*function\(([^)]*)\)\s*\{\s*//\s*(?:Original name:\s*([^,]+))?")
NOISE = re.compile(
    r"^\s*(case \d+:|_fun\d+_ip = \d+; continue _fun\d+;|_fun\d+: for\(var|if\(.*\) \{ _fun\d+_ip = \d+; continue)"
)
KEEP = re.compile(r"'[^']*'|\"[^\"]*\"|\.\w+|Original name|\{'|\bnew\b|return|throw")


def load(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().split("\n")


def headers(lines):
    """Indexes of function header lines with their indent."""
    out = []
    for i, ln in enumerate(lines):
        if "function(" in ln:
            m = HDR.match(ln)
            if m:
                out.append((i, len(m.group(1))))
    return out


def enclosing(lines, hdrs, idx, outer=0):
    """The innermost function around line idx (0-based), or `outer` levels further out: (start, end)."""
    found = []
    # walk headers backwards; a header encloses idx if its closing line is after idx
    import bisect

    pos = bisect.bisect_right([h[0] for h in hdrs], idx) - 1
    while pos >= 0:
        start, ind = hdrs[pos]
        end = close_of(lines, start, ind)
        if end >= idx:
            found.append((start, end))
            if len(found) > outer:
                return found[-1]
        pos -= 1
    return found[-1] if found else (max(0, idx - 20), idx + 20)


_close_cache = {}


def close_of(lines, start, ind):
    if start in _close_cache:
        return _close_cache[start]
    pat = " " * ind + "}"
    j = start + 1
    n = len(lines)
    while j < n:
        ln = lines[j]
        if ln.startswith(pat) and (len(ln) == len(pat) or ln[len(pat)] in ";),") and not ln[: ind].strip():
            break
        j += 1
    _close_cache[start] = j
    return j


def show(lines, start, end, full, out):
    out.write(f"--- lines {start + 1}-{end + 1}: {lines[start].strip()[:160]}\n")
    for k in range(start, end + 1):
        ln = lines[k]
        if not full:
            if NOISE.match(ln) or not KEEP.search(ln):
                continue
        out.write(f"{k + 1:>8}  {ln.rstrip()[:240]}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bundle")
    ap.add_argument("mode", choices=["line", "grep", "names"])
    ap.add_argument("arg")
    ap.add_argument("--full", action="store_true", help="print every line, not the condensed view")
    ap.add_argument("--outer", type=int, default=0, help="go this many enclosing functions further out")
    ap.add_argument("--max", type=int, default=60, help="at most this many functions (grep/names)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lines = load(a.bundle)
    hdrs = headers(lines)
    if a.mode == "line":
        s, e = enclosing(lines, hdrs, int(a.arg) - 1, a.outer)
        show(lines, s, e, a.full, sys.stdout)
        return
    if a.mode == "names":
        rx = re.compile(a.arg)
        n = 0
        for i, _ in hdrs:
            m = HDR.match(lines[i])
            name = (m.group(3) or "").strip()
            if name and rx.search(name):
                print(f"{i + 1:>8}  {name}")
                n += 1
                if n >= a.max:
                    break
        return
    rx = re.compile(a.arg)
    seen = set()
    for i, ln in enumerate(lines):
        if rx.search(ln):
            s, e = enclosing(lines, hdrs, i, a.outer)
            if (s, e) in seen:
                continue
            seen.add((s, e))
            show(lines, s, e, a.full, sys.stdout)
            if len(seen) >= a.max:
                print(f"... stopped at --max {a.max}")
                break


if __name__ == "__main__":
    main()
