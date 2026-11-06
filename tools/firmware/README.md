# firmware

Read-only helpers for looking at the structure of a firmware image or a TI SimpleLink OTA bundle. They parse and
report; nothing here runs, flashes or modifies anything. Point them at files under `dumps/` (gitignored); firmware
blobs are never committed.

| Script | What |
|---|---|
| `fw_inspect.py <dir-with-ota.cmd> [file ...]` | verify each OTA file's SHA-256 against the `ota.cmd` manifest; for each given file print size, SHA-256, Shannon entropy (whole + per-4K-block, to tell plaintext from encrypted), the first words of the ARM vector table, and version/path-like strings. `--write-sigs DIR` also decodes each secured file's base64 signature from the manifest into `DIR/<name>.sig` (256 bytes expected) beside a copy of the file: the inputs for a file-level write through the boot loader ((private write chapter: names the vendor's firmware files and the signature handling, not published)) |
| `ccfg_parse.py <cc26xx-flash.bin>` | decode the CC26x0R2 CCFG (last 88 bytes): bootloader enable, JTAG/DAP enable, flash protection, image-valid |
| `disarm.py <file> <load_hex> <start_hex> [count]` | disassemble a window of a little-endian ARM **Thumb** image (needs `capstone`; install it in a throwaway venv, not system-wide) |
| `AnovaExport.java` | Ghidra headless post-script: writes the memory map, function count, the string→function map (resolved through Thumb literal-pool pointers), the most string-rich functions, and decompiled C for the keyword and string-rich functions |
| `AnovaDecompileAll.java <outDir>` | Ghidra headless post-script: decompiles **every** function into a browsable source tree — one `.c` per function under `functions/`, a concatenated `all.c`, `prototypes.h`, `index.csv` (address, size, name, call counts), `strings.txt`, and Ghidra's whole-program C/H export |
| `AnovaName.java <names.csv>` | Ghidra headless post-script (writes the DB — run **without** `-readOnly`): applies a curated `address,name,note` map, then auto-names RTOS threads by resolving each `Task_create` call site's name+function-pointer args; creates a Thumb function when a mapped address has none. Names propagate into every caller on the next decompile |

Run with isolated Python so nothing in the blob's directory can be imported:

```sh
py -3.13 -I tools/firmware/fw_inspect.py dumps/<pkg>/ota/0  dumps/<pkg>/ota/2/sys/mcuimg.bin
py -3.13 -I tools/firmware/ccfg_parse.py dumps/<pkg>/ota/2/sys/cc2640.bin
```

CCFG offsets are TI's public `hw_ccfg.h` for CC26x0R2. `0xC5` in a DAP/bootloader byte means enabled/allowed; any
other value means disabled/locked.

## Ghidra (decompilation / function map)
Ghidra 12.x needs a JDK 25; both are large downloads and are kept **outside** the repo (a scratch dir, not
committed). Flat Cortex-M images are imported with the right base and processor. The CC2640 flash image loads at
`0x0`; the CC3220 app image is a RAM image loaded at `0x20000000` (its reset vector is `0x200274b5`).

```sh
# <GH> = ghidra install, <JDK25> set in <GH>/support/launch.properties JAVA_HOME_OVERRIDE
<GH>/support/analyzeHeadless <proj_dir> anova -import cc2640.bin \
    -processor ARM:LE:32:Cortex -loader BinaryLoader -loader-baseAddr 0x0 \
    -scriptPath tools/firmware -postScript AnovaExport.java <out.txt> <keyword> [<keyword> ...]
#   mcuimg.bin: -loader-baseAddr 0x20000000
```
Ghidra's auto-analysis recovers only some string references on these flat images; `AnovaExport.java` adds its own
literal-pool pointer scan, and the decompiled C of the string-rich functions is where the useful map comes from.
Reports go under `dumps/` (firmware-derived, never committed).

To dump the **whole** decompilation as a readable source tree (one folder per image), run against the
already-analysed project with `-process` (no re-import, no re-analysis):

```sh
<GH>/support/analyzeHeadless <proj_dir> anova -process cc2640.bin -noanalysis -readOnly \
    -scriptPath tools/firmware -postScript AnovaDecompileAll.java dumps/<pkg>/ghidra/src/cc2640
#   mcuimg.bin -> dumps/<pkg>/ghidra/src/mcuimg
```
The output (`functions/*.c`, `all.c`, `index.csv`, …) is decompiled C of the firmware, so it stays under `dumps/`
and is never committed or published, exactly like the blobs. Names like `FUN_<addr>` are Ghidra's; the hex is the
function's entry address, so it cross-references the map in `docs/firmware/ghidra-map.md`.

To give functions meaningful names, write an `address,name,note` CSV (kept private under `dumps/` — the
address→role mapping is firmware-derived) and run `AnovaName.java` against the project **before** re-exporting:

```sh
<GH>/support/analyzeHeadless <proj_dir> anova -process cc2640.bin -noanalysis \
    -scriptPath tools/firmware -postScript AnovaName.java dumps/<pkg>/ghidra/names_cc2640.csv
# then re-run AnovaDecompileAll.java to regenerate the tree with the names applied
```
Name one function `Task_create` in the CSV and the script will walk its call sites to name the RTOS thread
entries automatically (and create any the auto-analysis never reached).
