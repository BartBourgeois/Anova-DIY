# apk

Read-only helpers for looking inside an Android app package: the Hermes bytecode of a React Native app and the
string pools of its DEX files. Nothing here runs or modifies the app.

| Script | What |
|---|---|
| `hbc_strings.py <bundle> <out.tsv>` | the string table of a Hermes bytecode file (header layout of version 96), one `index<TAB>repr` per line |
| `dex_strings.py <out.tsv> <classes.dex> [...]` | the string pool of each DEX file, one `file<TAB>index<TAB>repr` per line |
| `hasm_xref.py xref\|strs\|dump <hasm> ...` | which functions use which strings, in a disassembly listing from [hermes-dec](https://github.com/P1sec/hermes-dec) |

## How it's used
The package and everything taken out of it stay outside git, in `apk/<app>-<version>/` (gitignored): the package as
downloaded under `original/` (hash checked), the unpacked splits beside it, the dumps under `analysis/`. The
package is untrusted input: run the scripts from elsewhere with `py -3.13 -I`, paths as arguments.

```sh
py -3.13 -I tools/apk/hbc_strings.py apk/<app>/base/assets/index.android.bundle apk/<app>/analysis/hbc_strings.tsv
py -3.13 -I tools/apk/dex_strings.py apk/<app>/analysis/dex_strings.tsv apk/<app>/base/classes*.dex
```

For the bytecode itself, hermes-dec (0.1.8 handles version 96) goes into its own virtual environment, outside the
repo and outside the package's directory:

```sh
py -3.13 -m venv <somewhere>/venv-hermesdec
<somewhere>/venv-hermesdec/Scripts/python -m pip install hermes-dec
<somewhere>/venv-hermesdec/Scripts/hbc-disassembler apk/<app>/base/assets/index.android.bundle apk/<app>/analysis/bundle.hasm
<somewhere>/venv-hermesdec/Scripts/hbc-decompiler   apk/<app>/base/assets/index.android.bundle apk/<app>/analysis/bundle.js
py -3.13 -I tools/apk/hasm_xref.py xref apk/<app>/analysis/bundle.hasm "(?i)firmware"
```

The function numbers `hasm_xref.py` prints (`#NNNNN`) are the ones in the decompiled `bundle.js`
(`_funNNNNN`), which is easier to read.
