# cc32xx

`ccx.py` runs **cc3200tool** (the open-source client for the CC32xx ROM bootloader's UART protocol, in the
[toniebox-reverse-engineering fork](https://github.com/toniebox-reverse-engineering/cc3200tool)) **read-only by
default**, and keeps a log of every run. cc3200tool is what the CC3220's UARTLOAD mode (SOP2 high) talks to: it
reads the version info, dumps the serial flash, lists the SimpleLink filesystem, and, when told to, writes.

## Install (once)
cc3200tool is untrusted third-party code: it lives in **a virtual environment outside the repository**, whose path
is given with `--venv` or the `CC3200TOOL_VENV` environment variable, and it is never run from inside its clone.
```sh
py -3.13 -m venv <venv>
git clone https://github.com/toniebox-reverse-engineering/cc3200tool <venv>/src
<venv>/Scripts/python.exe -m pip install <venv>/src        # pulls pyserial
```
Record the clone's commit hash in the journal. The wrapper starts `<venv>/Scripts/python.exe -I -u` (`bin/python`
elsewhere) and calls `cc3200tool.cc:main()`, the console script's entry point, so nothing from the current
directory can be imported.

## Usage
```sh
py -3.13 tools/cc32xx/ccx.py --venv <venv> -p COM7 --reset prompt                       # connect, version info only
py -3.13 tools/cc32xx/ccx.py --venv <venv> -p COM7 --reset prompt read_flash dumps/<unit>/u15_a.bin
py -3.13 tools/cc32xx/ccx.py --venv <venv> --cc3220 -p COM7 --reset none read_flash a.bin read_flash b.bin  # CC3220S
py -3.13 tools/cc32xx/ccx.py --venv <venv> --cc3220 --status -p COM7 --reset none  # Uniflash's device status panel
py -3.13 tools/cc32xx/ccx.py --venv <venv> --rom-only -p COM7 --reset prompt         # alive? the ROM's version, nothing else
py -3.13 tools/cc32xx/ccx.py --venv <venv> -if dumps/<unit>/u15_a.bin -d cc32xx list_filesystem --extended
py -3.13 tools/cc32xx/ccx.py --venv <venv> list_filesystem --help                      # a subcommand's help
py -3.13 tools/cc32xx/ccx.py --venv <venv> -- --help                                   # cc3200tool's global help
py -3.13 tools/cc32xx/ccx.py --help                                                    # this wrapper's help
```
Wrapper options come first (`--venv DIR`, `--write`, `--backup-sha256 HEX`); everything else, or everything after
`--`, goes to cc3200tool unchanged.

**The gate.** Only `list_filesystem`, `read_file`, `read_all_files`, `read_flash` and a run without a subcommand
pass. `write_file`, `write_all_files`, `write_flash`, `format_flash`, `erase_file`, `dll_data_test`, an unknown
subcommand and `--reboot-to-app` (it can pulse the reset line) are refused with exit code 2 before the port opens,
unless `--write --backup-sha256 <64 hex>` is given: the SHA-256 of the flash dump that was read twice with the same
hash (rule 1 of the project). The hash is written into the log. cc3200tool chains subcommands
(`list_filesystem read_flash x.bin` is two commands in one run), so every token is checked, not just the first.

**The pre-flight check.** With `--write`, the wrapper also checks the inputs before the port opens, and refuses the
run (exit code 2, "nothing sent", each problem on its own line) unless:
- **the backup is there twice:** at least two files under `dumps/` that are whole 4 KiB blocks hash to
  `--backup-sha256` (the two reads of rule 1, e.g. `u15_bl_1.bin` and `u15_bl_2.bin`);
- **every `write_file` sends a file from an update manifest:** a TI OTA manifest (`ota.cmd`) under `dumps/` lists the
  same device path with the same SHA-256. A secured entry needs `--signature`, a file of **exactly 256 bytes equal
  to that entry's `signature_base64`**; an unsecured entry takes none. This matters because cc3200tool reads only the
  first 256 bytes of the signature file and checks the length at the close, after it has erased the old file and
  uploaded the new one: a wrong signature file would leave the device without the file;
- **every `write_flash` sends the backup itself** (its SHA-256 is `--backup-sha256`): the raw write is the undo, and
  nothing else.

What it matched (the backup's copies, the manifest file and entry) goes into the run's log. `format_flash`,
`erase_file` and `write_all_files` carry no image: for them only the backup is checked.

**Run it from PowerShell, not Git Bash.** Git Bash rewrites an argument that starts with `/` into a Windows path, so
`/sys/mcuimg.bin` reaches cc3200tool as `<Git's install folder>/sys/mcuimg.bin` (seen 2026-11-05; the pre-flight
check refuses it, since no manifest lists that path). If Git Bash it must be, set `MSYS_NO_PATHCONV=1` for the command.

**The log.** `.capture/cc32xx/<YYYYMMDD-HHMMSS>_<subcommand>.log` (gitignored): PC time, the exact command line,
the write flag and hash, then the child's stdout and stderr merged as they appear (also on the console), and the
exit code. Refused runs are not logged: nothing ran.

**`--rom-only`**: the break and one version query to the ROM boot loader, then stop. It can't give the
mode or the MAC: this boot loader ACKs those queries but doesn't answer them. No switch, so the
network processor never starts and can't write; no RAM upload (cc3200tool's own switch would upload a DLL
and run it on a boot loader of version 4 and up). No subcommand, no `--write`, no `--status`. For a chip whose
flash has no backup yet.

**`--status`** (with `--cc3220`; `--fs-usage` is the old name): after the switch, three reads that make Image Creator's
"Device status" panel (device type, MAC, hardware version, mode, capacities, free space, flash ID, security alerts):
GET_STORAGE_INFO of the serial flash (0x31), GET_DEVICE_PARAM (0x3A) with parameter 0, the default MAC, and TI's
GET_FS_USAGE (0x37), the read behind the mode and the alert count. The reply is 36 bytes, big-endian: seven 16-bit block counts (block size, capacity, allocated,
reserved, reserved for system files, largest gap, free for user files), two bytes of padding, seven 8-bit file-system
fields (the development flag among them), one byte of padding, then the alert count, its threshold (32-bit each) and a
16-bit FAT write counter. Uniflash's command line (`dslite --mode cc32xx device info`) gives the MAC but not
the mode or the alerts, so this is where they come from on a plain serial adapter.

## Development mode against production mode
Everything above was proven on a CC3220S with a **development** image. On the same LaunchPad with a **production**
image of the same files (the "production twin"), the boot loader behaves differently:

| | development | production |
|---|---|---|
| connect, the version queries, `--cc3220`'s switch, storage list and info | works | works |
| Uniflash's device info (MAC, mode, alert count) | works | works |
| `--status` (GET_FS_USAGE 0x37, storage info 0x31, GET_DEVICE_PARAM 0x3A: Uniflash's device status) | | works |
| `read_flash` (raw read, 0x2C) | works | **refused** from the first 4 KiB chunk, any offset, also right after a power cycle |
| `read_file` (file info 0x2A) | works for plain files | **refused** |
| `write_file` (open for write 0x21) | works (with TI's close) | **refused** |
| security alerts from these refusals | | none (0 / 15 afterwards) |

A refusal shows as "timed out while waiting for ack", then "No ack for packet opcode=0x2c" (or 0x2a, 0x21).
cc3200tool counts nothing on the console then: the dots in its log lines are not progress ( corrects a count
that took them for blocks). For a production-mode chip, the flash is read with a clip, not through this tool.

## The break timing series
`break_series.py` reproduces 's measurement: connect-only sessions, each after a reset through the XDS110,
with chosen break windows, and when the network processor's ACK arrived. It reads and writes nothing, but each
missed break lets the network processor rewrite `/tmp/phy.cal`, so only on a board with a backup:
```sh
py -3.13 tools/cc32xx/break_series.py --venv <venv> --port COM11 --probe <XDS110 serial> \n    --reset-tool <Uniflash>/simplelink/imagecreator/bin/xds110reset.exe --trials 5 --out series.json
```

## What cc3200tool sends (read from its `cc.py`, 1 666 lines, v1.3.0)
Opening the port (`serial.Serial(port, 921600)`) asserts **DTR and RTS** (pyserial's defaults); nothing else
touches them unless `--sop2`/`--reset` name a pin. Then `connect()`:
1. `--sop2 dtr|rts` asserts that modem line (pyserial `dtr=True`; a TTL adapter's DTR pin then usually sits low,
   which is what the `~` prefix is for); `none` (default) does nothing.
2. `--reset dtr|rts` pulses that pin for 100 ms; `prompt` prints "Reset the device with SOP2 asserted and press
   Enter" and waits; `none` (default) does nothing. Then it waits `--reset-wait` ms (1000).
3. Up to 5 times: a **200 ms break** on TX, then up to 1 s for the ROM's ACK `00 CC`.
4. `GET_VERSION_INFO` (0x2F): a 28-byte reply, printed as five 4-byte tuples: bootloader, NWP, "mac" (a version
   field, **not** the MAC address), PHY, chip type.
5. Only if chip type byte 0 has bit 0x10 set (the tool calls that a CC3200): the NWP-bootloader switch
   (`SWITCH_2_APPS` 0x33, a DLL written to SRAM with 0x2D, `EXEC_FROM_RAM` 0x32), and only for boot-loader version
   byte 1 ≥ 4; below 3 it stops with "Unsupported device" after a second version query, nothing else sent.
   **Corrected 2026-11-05:** TI's SWPA230A (table 10, section 5.3) says the 0x10 bit means the **CC3220
   family** (0x18 = CC3220S, 0x19 = CC3220SF), and the switch is TI's step 3 for the CC3220 ("Switch UART to APPS
   MCU", 0x33 with delay 26666667, then a break), followed by a boot-loader patch in SRAM (steps 4-7). The
   LaunchPad's CC3220S reports chip type `0x18`, boot loader 0.1.0.3, so this tool version refuses it.
   **`--cc3220`** (a wrapper option) runs TI's step 3 alone in place of the tool's switch: no SRAM patch, no flash
   operation. The step lives in [`cc3220_connect.py`](cc3220_connect.py), loaded into cc3200tool's process:
   - the switch (0x33, delay 26666667), then **the break held** from `--break-lead` to `--break-lead` +
     `--break-hold` seconds after the switch's ACK (default 0.5 to 2.0 s), whatever arrives meanwhile
   - every byte received in that time is logged with its time (`+0.968 s rx 00 cc`)
   - the version query must then come back from the **network processor's** boot loader (`1.1.0.3` on the
     LaunchPad; the ROM's is `0.1.0.3`)
   - no ACK, or the ROM answering, is an error that needs a reset, never a retry

   **Why the window:** when the network processor misses the break it boots its own firmware, which wrote two
   blocks of the LaunchPad's flash. Measured on the LaunchPad (20 sessions, 20 caught): with the
   break already on, the network processor answers **0.96-0.99 s** after the switch's ACK; with cc3200tool's own
   timing (a 200 ms break from 1.0 s) it still answered at 1.04-1.11 s, so a little more delay misses it. During the
   switch's delay the ROM doesn't answer a break, so an early break can't be mistaken for the network processor's
   answer.

   `--cc3220` also replaces cc3200tool's reading of GET_FILE_INFO (0x2A): a CC3220S answers 36 bytes, flags in
   bytes 0-1, the file's length in bytes 4-7, its allocation in 8-11, all zeros for a missing, secure or system
   file. cc3200tool wants byte 0 == 1 (the CC3200's form), so without the fix every `read_file` says "does not exist". With it, `read_file` returns ordinary files in plain text (the boot loader decrypts them); secure files
   such as `/sys/mcuimg.bin` stay hidden.

**Writing a signed file on a CC3220S.** `--cc3220` writes the way TI's Image Creator does (its installed
`slbootloader` module, read): open (0x21), the data in chunks (0x24), then a close (0x22) carrying **the certificate's
file name zero-padded to 180 bytes, the 256-byte signature and a flags byte**; no file-info query and no erase before.
cc3200tool's own close puts 63 zero bytes where the name goes, so on a CC3220 the signature lands at the wrong offset:
a failed signature test, which raises a security alert. The pre-flight check therefore refuses a signed `write_file`
unless `--cc3220`, `--cert <the manifest's certificate>` and `--no-verify` are all given:
```
py -3.13 tools/cc32xx/ccx.py --venv <venv> --cc3220 --cert pro-code-cert.der --write --backup-sha256 <hash> -p COM7 --reset none write_file <mcuimg.bin> /sys/mcuimg.bin --signature <mcuimg.bin.sig> --file-size 262144 --no-verify
```

**Secure files are never asked for.** On a CC3220S an operation on a secure file without its token raises a
**security alert** (TI SWRU455M section 8.14: implicit alerts; at the threshold, 3 by default or what Image Creator
set, the device locks until it is reprogrammed or restored to factory). On the LaunchPad a single GET_FILE_INFO of
`/sys/mcuimg.bin` took the counter from 0 to 1, while plain-file reads and raw flash reads added nothing.
`ccx.py` refuses, with or without `--write` and before the port opens, a `read_file` of `SECURE_FILES`
(`/sys/mcuimg.bin`, `/sys/mcuimg1-3.bin`, `/sys/servicepack.ucf`, `/sys/certstore.lst`, `/sys/factory.img`) or of
anything an OTA manifest under `dumps/` marks `secured`. Names it can't know about may be secure too.

The ROM boot loader takes one session per reset: after a run, breaks go unanswered until the next reset (SOP2 on).
The reset can come from the PC through the XDS110 (LaunchPad): `xds110reset.exe -a toggle -d 200 -s <serial>`
from Uniflash's `simplelink/imagecreator/bin/`, then 2 s before the session.
So chain what one session should do (`read_flash a.bin read_flash b.bin`).

Then the subcommands. Every packet is `len(2) csum(1) data`, ACKed with `00 CC` both ways.
- `read_flash <file> [--offset N] [--size N]`: `GET_STORAGE_LIST` (0x27), `GET_STORAGE_INFO` (0x31) for storage 2
  (serial flash), then `RAW_STORAGE_READ` (0x2C) in 4096-byte chunks. The size defaults to block size x block count
  **as the ROM reports it**; a dump is read twice and compared (`--no-verify True` skips that). `--ignore-max-size
  True --size N` reads past the reported size. Note both of those options take a value (`type=bool`).
- `list_filesystem`: storage info, the two FAT copies (raw reads), the name table (raw read). **`-d cc32xx` is only
  applied in the offline path** (`-if dump.bin`): over the serial link the CC3200 FAT offsets are used whatever `-d`
  says. So: `read_flash` first, then list the dump offline with `-d cc32xx`.
- `read_file <name> <file>` by name: `GET_FILE_INFO` (0x2A), then the file is **opened for read with 0x21** (the
  "start upload" opcode doubles as open; flags 0 = read), `READ_FILE_CHUNK` (0x2B), and closed with **0x22** (a
  dummy 256-byte signature, as Uniflash does). No block is written, but these two opcodes do go out. With
  `--file-id N` the file is pulled by raw reads of its blocks instead. `read_all_files` loops `read_file` by name
  and skips `/sys/servicepack.ucf`.
- No read subcommand sends `FILE_CHUNK` (0x24), `FORMAT` (0x28), `RAW_STORAGE_WRITE` (0x2D), `ERASE_FILE` (0x2E),
  `RAW_STORAGE_ERASE` (0x30), 0x32 or 0x33.
- `write_file --signature f.sig`: the first 256 bytes of the file are the signature; flags become
  COMMIT|SECURE|PUBLIC_WRITE; an existing file is erased first (0x2E); the length check (exactly 256) happens at
  close, after the data went up.
- Output files (`read_file`, `read_flash`) are created and truncated **while the arguments are parsed**, before the
  port opens: never point them at an existing dump.
- Exit codes: 2 argument error (argparse), -1 no command, -2 port, -3 connect, -4 verify mismatch (the output file
  is deleted). The wrapper logs and returns them as they are (signed; PowerShell's `$LASTEXITCODE` shows -2 for a
  missing port).
