# 6. LaunchPad: the files in a production dump, and where the mode is kept

**Purpose.** Before the cooker's dump exists: learn on the LaunchPad's production dump what a clip read gives, and
which files come out readable. And find the one thing the cooker's chip can't be asked before its backup: **its
mode** (development or production). The first boot loader doesn't answer that question, but the file
system stores it, and a dump can show it.

All offline, on the PC, from the files of pages 3 and 5. Nothing is connected.

## 6.1 The file list
```
py -3.13 -I tools/sflash/sffs.py dumps/launchpad/<date>/u8_clip_prod_1.bin
py -3.13 -I tools/sflash/sffs.py dumps/launchpad/<date>/u8_clip_prod_1.bin --manifest dumps/ota/<date>/<package>/ota.cmd
```
What to expect (from the development dumps):
- the allocation table found (signature 0x634C), its revision, the file count
- each file: start block, size, mirrored or not, the copies with their sequence numbers, the length, the entropy
  (`H`, bits per byte)
- with `--manifest`: the update package's plain files marked `= package` (the certificates, the Bluetooth chip's
  image), the secure ones `!= package (encrypted or different)`: same plaintext, but stored encrypted with this
  chip's key

## 6.2 Recover the readable files
```
py -3.13 -I tools/sflash/sffs.py dumps/launchpad/<date>/u8_clip_prod_1.bin --extract dumps/launchpad/<date>/extract_prod
```
Each file's active copy lands under `extract_prod/` (gitignored, never committed). Then sort them:
- **plain**: entropy well below 8, readable (text, JSON, a known header such as a certificate's `30 82`): the
  application's state files, the certificates, the radio and network settings files
- **secure**: entropy about 8.0 and no structure: the application image, the service pack, the certificate catalogue.
  Ciphertext; this chip's key alone opens it
- **compare** against the development dump of page 3 (`--extract` it too): the plain files that both images write
  should be equal; a plain file that changed is a lead about what production mode changes

## 6.3 Where the mode is kept
```
py -3.13 -I tools/sflash/blockdiff.py fat --a <dev dumps> --b dumps/launchpad/<date>/u8_clip_prod_1.bin
py -3.13 -I tools/sflash/blockdiff.py blocks dumps/launchpad/<date>/u8_clip_ref_1.bin dumps/launchpad/<date>/u8_clip_prod_1.bin
```
- **Group A, the development dumps of the same project:** `u8_clip_ref_1.bin` (page 3), the earlier
  `u8_devfresh_1.bin` and `u8_ch340prog_1.bin`. **Group B:** the production dump. Only dumps of the same
  image set are comparable: a dump with other files (TI's demo) differs in every entry for that reason alone.
- `fat` lists the allocation-table bytes on which all development dumps agree, the production dump agrees with
  itself, and the two differ. With the same files on both sides, few bytes should be left. A flag in the header or a
  per-file flag that every file carries would point at the mode. `blocks` shows the other places that differ; the
  per-programming re-encryption makes most of them noise, so the table is the place to look first.
- Then the same on the TI out-of-box image (development) as a check: the candidate byte must say "development" there
  too.
- A candidate found → `sffs.py` gets a line that reports the mode, and the cooker's dump answers the question
  offline.

## 6.4 What a production dump holds that is private
A real device's flash also keeps its **Wi-Fi profiles** and per-device files. On the LaunchPad there are none (never
given credentials), so nothing here is private. The cooker's dump is different: [page 9](09-cooker-analysis.md#95-handle-it-as-a-secret).

## Records
Journal: FINDING (the file list in short: counts, which files plain, which secure; the mode candidate and its
check). Only names, sizes, sequence numbers, hashes and entropy go in the journal, never file contents beyond
what is needed (a state file's two bytes, say).
