"""Assemble the MkDocs source tree and build the static site.

The repo's Markdown lives at the root (README.md), in docs/ and in blog/, with images under images/.
MkDocs wants one source directory, so this script builds site-src/ (gitignored) from the repo:
  - README.md            -> site-src/index.md (links to public/LICENSE.md become LICENSE.md)
  - docs/**, blog/**     -> copied; links to ../README.md become ../index.md
  - images/**            -> copied, except images/own/ (the 12 MP originals, too big for the
                            Static Web Apps free tier); links to them, and to tools/ and
                            annotations/ files, point at the GitHub copies
  - web/static/**        -> site-src/_web/ (logo, extra.css); web/overrides/ is the theme custom_dir
  - LICENSE.md           -> from public/LICENSE.md if present, else LICENSE.md
  - staticwebapp.config.json -> written, for the 404 page and the Deep Zoom .dzi type on Azure Static Web Apps
Then `mkdocs build` runs (with --strict, broken links fail the build).

Usage:  python tools/build_site.py [--strict] [--no-build]
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "site-src"
GITHUB_BLOB = "https://github.com/BartBourgeois/Anova-DIY/blob/main/"

README_LINK = re.compile(r"\]\(((?:\.\./)*)README\.md(#[^)]*)?\)")
OVERLAY_LINK = re.compile(r"\]\(((?:\.\./)*)public/")
# Repo files that aren't pages (scripts, annotation JSON, the 12 MP originals): link to GitHub instead.
REPO_FILE_LINK = re.compile(r"\]\(((?:\.\./)*)((?:tools|annotations|images/own)/[^)]+)\)")


def rewrite(text: str) -> str:
    text = README_LINK.sub(r"](\1index.md\2)", text)
    text = OVERLAY_LINK.sub(r"](\1", text)
    text = REPO_FILE_LINK.sub(lambda m: f"]({GITHUB_BLOB}{m.group(2)})", text)
    return text


def copy_tree(src: Path, dst: Path, skip: tuple[str, ...] = ()) -> int:
    n = 0
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if not p.is_file() or any(part in skip for part in rel.parts):
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".md":
            out.write_text(rewrite(p.read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copy2(p, out)
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strict", action="store_true", help="broken links fail the build")
    ap.add_argument("--no-build", action="store_true", help="only assemble site-src/")
    args = ap.parse_args()

    if SRC.exists():
        shutil.rmtree(SRC)
    SRC.mkdir()

    (SRC / "index.md").write_text(rewrite((ROOT / "README.md").read_text(encoding="utf-8")), encoding="utf-8")
    n = 1
    n += copy_tree(ROOT / "docs", SRC / "docs")
    n += copy_tree(ROOT / "blog", SRC / "blog")
    n += copy_tree(ROOT / "images", SRC / "images", skip=("own",))
    n += copy_tree(ROOT / "web" / "static", SRC / "_web")  # theme assets: logo, extra.css
    license_src = ROOT / "public" / "LICENSE.md" if (ROOT / "public" / "LICENSE.md").exists() else ROOT / "LICENSE.md"
    shutil.copy2(license_src, SRC / "LICENSE.md")
    n += 1
    # A real 404 status for unknown URLs (no navigationFallback: that would serve the page with a 200).
    (SRC / "staticwebapp.config.json").write_text(json.dumps({
        "responseOverrides": {"404": {"rewrite": "/404.html", "statusCode": 404}},
        "mimeTypes": {".dzi": "application/xml"},  # mosaic viewer descriptors (tools/deepzoom.py)
    }, indent=2) + "\n", encoding="utf-8")
    print(f"site-src: {n} files assembled")
    if args.no_build:
        return 0

    cmd = [sys.executable, "-m", "mkdocs", "build", "--clean"] + (["--strict"] if args.strict else [])
    return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
