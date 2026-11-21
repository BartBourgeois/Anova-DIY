# 9. The cooker's flash, examined

**Input:** the verified pair of [page 8](08-cooker-backup.md), `dumps/cooker/<date>/u15_clip_1.bin`. Everything here
is offline and read-only. The dump is never changed: the tools read it and write their output elsewhere.

## 9.1 The file system
```
py -3.13 -I tools/sflash/sffs.py dumps/cooker/<date>/u15_clip_1.bin
py -3.13 -I tools/sflash/sffs.py dumps/cooker/<date>/u15_clip_1.bin --manifest dumps/ota/<date>/<package>/ota.cmd
```
First answers (each with its evidence in the journal):
1. **Is the allocation table intact?** Which copy is active (0 or 1), its revision, the number of files. A missing
   or broken table means the file system itself was hit: chapter 5's full image (option C) becomes the route.
2. **Every file's copies.** For a mirrored file, both copies' sequence numbers and lengths. A file with only one valid
   copy, or a newer copy with a bad header, is where a write stopped.
3. **The mode** (development or production), with the byte found on [page 6](06-launchpad-files.md#63-where-the-mode-is-kept).

## 9.2 What the update left behind
The questions from the update package's analysis and the recovery strategy's hypotheses H1/H2:
- **The application image:** the two copies' sequence numbers and lengths. The 75 % (`guess`: 75 % of the update's
  bytes) would fall inside the application image. A newer copy that is short, or whose header is missing, fits that.
  Its content is ciphertext (this chip's key), so only the structure can be judged.
- **The Bluetooth chip's image** (plain): its SHA-256 against the package's copy. Equal = that part of the update
  finished, and the Bluetooth chip's own flash (H2) becomes the next question.
- **The service pack** and the **certificate catalogue**: their copies, as above.
- **The application's state files** (plain): the update record, the set temperature, the cooking state. The
  update record may say where the update was when it stopped.
- **Files nobody expected:** any name not in the LaunchPad's list. An update's temporary file, say.

## 9.3 Recover the readable files
```
py -3.13 -I tools/sflash/sffs.py dumps/cooker/<date>/u15_clip_1.bin --extract dumps/cooker/<date>/extract
```
- **Plain** (entropy well below 8, a readable structure): the state files, the sounds, the certificates, the
  device's identity file if it was stored plain (`guess`), the network settings. These are what a repair by full
  image (option C) carries over, so the cooker keeps its sounds, settings and identity.
- **Secure** (entropy about 8): the application image, the service pack, the catalogue, perhaps the identity file.
  Ciphertext: kept as it is, for the record and the undo.
- Compare with the LaunchPad's production dump (page 6): the same file names should appear, plus the cooker's own.

## 9.4 Compare, and decide
- `blockdiff.py blocks` between the cooker's dump and itself after any later write (the undo check): which files
  changed.
- The structure against the LaunchPad's production dump: the same layout? The same reserved blocks?
- With 9.1-9.3 answered, the repair decision of chapter 5 can be made on facts: options B (factory restore, if a
  factory image exists in this dump) or C (full image plus the plain files from 9.3). The undo is this backup,
  written back by clip.

## 9.5 Handle it as a secret
The dump is the cooker's whole memory:
- its **cloud identity** (the device's ID and credential), and
- most likely **your home Wi-Fi profile**: network name and passphrase. Whether the network processor stores the
  profile encrypted on a CC3220S is `unverified`.

So:
- the dump, its extracts and the copies stay in the gitignored `dumps/` and on the private off-machine copy, nowhere
  else
- the journal records names, sizes, sequence numbers, hashes and entropy, **never** an SSID, a passphrase, a
  credential or an identity file's content (rule 8)
- whether your Wi-Fi passphrase lies in clear can be checked locally: search the dump for your network's name
  (`findstr /m /c:"<your SSID>" <dump>` on the PC). Found = the profile is stored plain. Record only "found / not
  found"
- before the board ever leaves your hands (a repair service, a sale), the passphrase counts as known to anyone who
  reads that flash. If it is found in clear, changing the Wi-Fi passphrase is the safe end of it
