# sflash

`sffs.py` lists and extracts the files of a **CC3220S serial-flash dump** (the SimpleLink file system), offline and
read-only: a clip read of the flash chip, or a boot-loader `read_flash`. It never talks to a device.

## Usage
```sh
py -3.13 -I tools/sflash/sffs.py <dump.bin>                          # the file list
py -3.13 -I tools/sflash/sffs.py <dump.bin> --manifest <ota.cmd>     # plus a SHA-256 check against an update package
py -3.13 -I tools/sflash/sffs.py <dump.bin> --extract <dir>          # plus each file's active copy into <dir>
```
Columns: entry index, start block, size in blocks, mirrored (fail-safe, two copies), the flag nibble, each copy's
block and sequence number (`-` = no valid header), the active copy's length in bytes, its entropy (bits/byte; about
8.0 means encrypted or compressed), the name, and with `--manifest` whether the content equals the package's file.

## The layout
- **Blocks 0 and 1:** two copies of the allocation table. Header `<revision u16><signature u16>`; a CC3220S writes
  signature **0x634C** (the CC3200's is 0x534C, which is why cc3200tool's parser calls a CC3220S table broken). The
  valid copy with the higher revision is active. Then 128 entries of 4 bytes: index, size in blocks, start block
  LSB, and a byte with the start block's MSB in the low nibble and flags in the high nibble (0x4 clear = mirrored).
- **The name table:** two blocks after the active table (block 2 or 3), `<offset u16><length u16>` per entry, the
  names from 0x3C0.
- **Each copy of a file:** `<length u32><sequence u16><0x634C>`, then the data. Of a mirrored pair, the copy with a
  valid header and the higher sequence is active.
- **Plain files lie in the flash as they are; secure files** (the application image, the service pack, the root
  catalogue) **are encrypted with the chip's own key**: their length is readable, their content is not.

Checked on the LaunchPad's dumps: every plain file of the 3.3.35 package equals the package's copy, and the
application's own `/sys/upgrade_state.bin` and `/sys/user_setpoint.bin` read the same as through the boot loader.
