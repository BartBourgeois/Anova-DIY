# References

## FCC filing `2APBOAN600` (Anova Applied Electronics, grantee code 2APBO)
Grant 2018-09-16, test lab Intertek Shanghai, model AN600 (tested as AN600-10, 120 V / 60 Hz, 1200 W).
Listing: <https://fccid.io/2APBOAN600>. The **block diagram, both schematics and the operational description are
confidential** (metadata only). Long-term confidentiality was granted.

Exhibits used (the PDFs are not redistributed here: download them from the listing above and compare the hashes),
with the SHA-256 recorded on 2026-11-01:

| File | Exhibit | SHA-256 | Notes |
|---|---|---|---|
| `cooker_pro_fcc.pdf` | Internal Photos (3999178) | `8102956afdabe47ac7844b4b330cc66a99d4b7dbc0ed7d3340897d4373e2ddd1` | Byte-identical to the FCC exhibit. Source for all board photos. |
| `fcc/2APBOAN600/External-Photo-3999177.pdf` | External Photos | `3cfbd3cdb83133fbc0f231f1170e682aebedd41c72f2aa7d9e2f4af5d5e05fb3` | |
| `fcc/2APBOAN600/Label-Location-3999179.pdf` | ID label / location | `16f8b704415a568fc58a0bd69ded2518c0dfc857dbc9d34e07f7f15ad614d9ae` | Label: `MODEL NUMBER: AN600-10`, S/N format `AN600-US00-YWWNNNNN` |
| `fcc/2APBOAN600/Test-Setup-3999187.pdf` | Test setup photos | `273b55e9cc7a82c2b42579cb605d1a2640b1251ce0c44dc66da8eaf233423b47` | |
| `fcc/2APBOAN600/User-Manual-3999188.pdf` | User manual | `08e6cd6256d6406dad2fbf38bc8b6e1c319502e0b303a70e09bdfa850dda21a5` | Generic; no error codes or reset procedure |
| `fcc/2APBOAN600/Report-BLE-3999184.pdf` | BLE test report | `cdaf05ee1b54cafa82194a529919eb8e0d7325860ab081b995a72cf72c522c57` | BLE 4.2, PCB antenna 2.21 dBi; test tool listed as "uEnergyTools" (CSR name, conflicts with the CC2640R2F) |
| `fcc/2APBOAN600/Report-WIFI-1-3999185.pdf` | Wi-Fi test report 1 | `62bbe4091f3f06655daa0a5eb7645f64f9a0805f0d40106e32a505dc1bfbfd5b` | 802.11b/g/n HT20, PCB antenna 2.45 dBi |
| `fcc/2APBOAN600/Report-WIFI-2-3999186.pdf` | Wi-Fi test report 2 (plots) | `ee86a46f3bff7f8a9397b523149fedfe6c030cd1045bb3a84a3fb0ac2a4c8a1c` | |
| `fcc/2APBOAN600/Report-FCC-MPE-ed1-3999181.pdf` | MPE / tune-up | `05ee4f2f95e1ab95d4e11937023bb39d98430a01c201ab7fd93792582c928143` | |
| `fcc/2APBOAN600/Confidentiality-3999175.pdf` | Cover letter | `d6f6d242e39027452ca5d9fb18b23a9c4ed966e8c3ee70f48cdd8eb138f2a71f` | |
| `fcc/2APBOAN600/FCC-Authority-Letters-3999176.pdf` | Cover letter | `a4b937e797f2e893b8aa71a4fd0c4aba17066718cb06d2083400563814e3c684` | |

Hashes computed with `sha256sum` on the downloaded files.

Other Anova FCC IDs under 2APBO that may be useful later:
- `2APBOAN625`: "Precision Cooker", applied 2026-06-30. Possibly a newer Pro generation.
- `2APBOAN500` / `AN500A`: Precision Cooker (non-Pro).
- `2APBOAN900` / `AN950`: Precision Ovens.

## TI CC3220 (Wi-Fi MCU)
- CC3220R/S/SF datasheet SWAS035C, *Sense-on-Power boot modes* (table 9-6):
  <https://www.ti.com/document-viewer/lit/html/SWAS035C/GUID-AB8250D3-80B6-4802-80F9-D8C1E415FCF4>
- Datasheet PDF: <https://www.ti.com/lit/ds/symlink/cc3220sf.pdf>. Rev. C (May 2021), 91 pages, downloaded 2026-11-04,
  SHA-256 `b982a744a2d763647993407ec5d3a5ed94a25208a2278d555a2dae5763a71d9e` (the same file is served as `cc3220r.pdf`).
  Pin diagram: figure 7-1, page 10 (top view, pin-1 mark at the bottom left). Pin descriptions: table 7-1, from page 11;
  pin attributes: page 15; pin multiplexing (UART0 options): pages 23-24. Used for [nets.md](hardware/nets.md).
- UART flashing / embedded programming (SWPA230): <https://ti.com/document-viewer/lit/html/SWPA230A/setup-t4880149-140>.
  PDF **SWPA230A** (June 2018, 20 pages), downloaded 2026-11-05, SHA-256
  `a2ad5d94971abe9bb00df2360b8892b1ab2d1db2655e3991adfd9f8ef15bf30a`: message format and opcodes (section 4,
  table 10: Switch UART to APPS MCU 0x33, "applies only to CC3220"), target detection (chip type 0x10 = CC3220
  family, 0x18 = CC3220S, 0x19 = CC3220SF), the programming steps 1-12 (section 5.3; steps 8-10 write the boot-loader
  patch into the serial flash).
- Secure boot and encryption (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/887901/cc3220sf-boot-procedure-secure-boot-and-encryption>
- External flash security (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/983522/cc3220s-security-question-for-external-flash-and-the-secure-boot-flow>
- OTA rollback / pending commit (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/779805/launchcc3220modasf-rollback-of-firmware-after-ota>
- OTA broken after an interrupted update (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/982731/cc3220sf-cc3220sf-update-functionality-is-broken-after-update-is-interrupted-in-certain-position>
- Boot-loader UART on pins 55/57 (GPIO1/GPIO2), custom-board loading (TI E2E, read 2026-11-05 via a web summary, `likely`):
  <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/1098611/cc3220s-cc3220s-custom-board-firmware-loading-issue>
- The MAC address lives in a secure system file on the serial flash and is erased by a full program; keep it by
  replacing only the MCU image (TI E2E, read 2026-11-05 via a web summary, `likely`):
  <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/974031/cc3220mod-how-to-keep-a-programmed-mac-address-while-reprogramming>
- Returning to the factory image erases all content and rebuilds the file system (SWRU473A, read 2026-11-05 via a web summary, `likely`):
  <https://www.ti.com/document-viewer/lit/html/SWRU473A/returning-to-factory-image-x2398>
- Downloaded 2026-11-05 from `https://www.ti.com/lit/pdf/<number>`, kept privately with the other datasheets:
  - LaunchPad hardware user's guide **SWRU463C** (March 2020, 30 pages), SHA-256
    `387ac5da17a7da4337dbc5da777b6c32f57eb8993b512e01195abe71e3d481c5`. SOP jumper J13: table 7 and figure 12
    (page 16, the default is SOP1); JTAG IN J8 and the jumper block: table 1 (page 11); **XDS110 OUT J4** for an
    external 3.3 V target: figure 9 (page 12).
  - UniFlash ImageCreator user's guide **SWRU469H** (65 pages), SHA-256
    `f2e73ede3c873acc88818280f8b404c9090e28b448738865fadea297a1ec7ec4`.
  - CC3220 technical reference manual **SWRU465** (780 pages), SHA-256
    `07125b060cb1da322b523e9f5a89750847dc5d72998356e1800c5c4610984e8d`.
  - Network processor user's guide **SWRU455M** (327 pages), SHA-256
    `820506786dea93f31863e5fa22f4aa9119032ae1ba1ad85e37d4d8ba8adaac50`.
- To read: CC3x20 Built-In Security Features (SWRA567), OTA guide (SWRA510), out-of-box application (SWRU473).
  The LaunchPad design files (SPRCAG0A: schematic, layout, board outline) need a myTI login.

## XMC XM25QH64A (serial flash U15/U16)
- Elnec programmer device page (package code H = SOP-8 208 mil): <https://www.elnec.com/en/device/XMC/XM25QH64A%20[SOP8-208]%20(QuadSPI)>
- Linux spi-nor patch adding XM25QH64A (JEDEC ID 0x207017): <https://lists.infradead.org/pipermail/linux-mtd/2018-April/080447.html>
- XMC product pages: <https://www.xmcwh.com/en/site/product_con/936>
- Same-family datasheet (XM25QH128A, includes the SOP 208 mil package and 2.7-3.6 V spec): <https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1811072025_XMC-XM25QH128AHIG_C328463.pdf>
- XM25QH64A datasheet, rev. J (2018-08-06), 75 pages, from raptox's download (file `PFXM25QH64AHIG_0001.pdf`),
  SHA-256 `47e5eba84bf3b471e1ffeb57cfd2f4f3b79f39b85296082d14af48825897e16f`. SOP-8 pinout: figure 1, page 2; pin
  names: table 1, page 3; manufacturer and device ID (9Fh: `20h 7017h`): table 6, page 16; package drawing (SOP 208
  mil): page 71; ordering code: page 74. Used for [nets.md](hardware/nets.md) and the dump procedure.

## Lumissil IS31FL3737 (LED matrix driver U14)
- Datasheet **IS31FL3737** Rev. G (2024-10-28), 29 pages: <https://www.lumissil.com/assets/pdf/core/IS31FL3737_DS.pdf>. Downloaded 2026-11-11, kept privately,
  SHA-256 `49be09beefe26cefd9961e160241c016a1b1a558ba2bd0e340707e52b3e9043b`. Pin configuration (QFN-40, top view,
  pin-1 dot top left), page 3; pin description, page 4; I2C slave address by the ADDR pin (GND = `1010000` = 0x50),
  page 9; command register FDh and its write lock FEh (unlock with C5h), pages 11-12; PWM register map (16 bytes per
  SW row, CS1-CS6 at 0-5, CS7-CS12 at 8-D), page 15; package, page 27. No marking specification in it.
- Its later revision **IS31FL3737B** Rev. D (first released July 2019, page 30): <https://www.lumissil.com/assets/pdf/core/IS31FL3737B_DS.pdf>, SHA-256
  `2d0be6447d2eecaea40d891d6b1d51b9303546c6021186518a0487c2e23f3cb5`, kept for the comparison (same pinout and
  addresses).

## AKM AK4637 (audio codec U13)
- Datasheet **AK4637** (015010680-E-00, 2015/09), 96 pages, AKM's own copy: <https://www.akm.com/content/dam/documents/products/audio/audio-codec/ak4637en/ak4637en-en-datasheet.pdf>. Downloaded 2026-11-11, kept privately with the other datasheets, SHA-256
  `ab14896209d844ff12a78041ddf8df06b589e840a40ec84fe98b7a2819898162`. General description and package, page 1;
  supplies (AVDD 2.8-5.5 V, DVDD 1.6-1.98 V, TVDD 1.6-3.6 V) and interfaces, page 2; pin layout, figure 2, page 6;
  pin functions, page 9; I2C control interface (slave address `0010010` = 0x12), page 65; package drawing and the
  **marking** (`4637` over a 4-digit date code, a pin-1 dot), page 94; ordering guide (AK4637EN), page 95.
- Distributor listings (DigiKey, Arrow) mark the part obsolete (2026-11-11, unverified).

## TI ADS7924 (4-channel 12-bit I2C converter)
- Datasheet **SBAS482C** (Rev. C, September 2017), 51 pages: <https://www.ti.com/lit/ds/symlink/ads7924.pdf>.
  Downloaded 2026-11-13, kept privately with the other datasheets, SHA-256
  `f680e98ab6f72d72ea63c14e1031d3b051c70d4f0aef7a4a9738336a35dfbd95`. Used: the I2C address by the A0 pin (table 2,
  p. 21: 0x48 with A0 to ground), the pointer byte and its INC bit (p. 22), the register map (table 3, p. 26),
  MODECNTRL and its Manual-Single mode (figure 34, p. 27), the data registers (figures 36-43, p. 28), the pinout of
  the 16-pin 3 x 3 mm WQFN (p. 3).

## TI CC2640R2F (BLE MCU)
- Datasheet: <https://www.ti.com/lit/ds/symlink/cc2640r2f.pdf>. Downloaded 2026-11-06, kept privately with
  the other datasheets: **SWRS204C** (Rev. C, 74 pages), SHA-256
  `5e922a15baebca5b8c4d998b1d303fb721f264f877ed7c5b94fcabdd75530bfa`. The RGZ (7x7 VQFN-48) pinout, figure 7-1 and
  the signal table (pages 8-9): JTAG_TMSC pin 24, JTAG_TCKC pin 25, RESET_N pin 35 (no internal pull-up), DIO_16/TDO
  pin 26, DIO_17/TDI pin 27, VDDS 44, VDDS2 13, VDDS3 22, VDDS_DCDC 34, ground on the exposed pad.
- CC26xx serial bootloader interface (SWRA466): <https://www.ti.com/document-viewer/ja-jp/lit/html/SWRA466D/GUID-813A07F3-F86E-4862-A618-2A7E5B9A5F95>
- Bootloader backdoor (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/bluetooth-group/bluetooth/f/bluetooth-forum/704737/cc2640r2f-going-through-the-backdoor-of-the-bootloader>
- Debug lock via CCFG (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/bluetooth-group/bluetooth/f/bluetooth-forum/931512/cc2640r2f-debug-interface-is-locked>
- To read: CC13x0/CC26x0 Technical Reference Manual (SWCU117), CCFG chapter.

## Power
- onsemi NCP59800 **Rev. 3** (December 2022), 11 pages, from onsemi's own link this time (2026-11-11), kept
  privately: SHA-256 `01a40cd413e6e24609aa61a7c6f64c31e95f229b411bef9af929b8e3baf47379`. Marking diagram and pin
  connections, page 1; pin functions and absolute maximum ratings, page 2; output voltage setting, page 9; package
  (DFN8 3x3, 0.65 mm, case 506DB), page 10.
- onsemi NCP59800, 1 A low-noise LDO, DFN8 3x3 (U17): datasheet NCP59800/D rev. 2 (October 2019), 7 pages,
  SHA-256 `f2f627482917ef6c87f7bc83e60a8d56dc998dea59cd0dbbe72809d65283b890`, downloaded 2026-11-04 from a distributor
  copy, <https://static.chipdip.ru/lib/240/DOC041240174.pdf>. onsemi's own link refused the download (access denied):
  <https://www.onsemi.com/pdf/datasheet/ncp59800-d.pdf>. Used: page 1 (pinout, marking `59800 / ADJB`), page 2 (pin
  functions, absolute maximum ratings), pages 3-5 (operating range, dropout, feedback resistors, ordering). Used for
  [nets.md](hardware/nets.md#supply).
- CC3220 supply range and currents: SWAS035C (above), section 8.4 (VBAT 2.1-3.6 V, 3.3 V typical, page 29) and
  section 8.5 (TX up to 272 mA, calibration peak 450 mA at 3.3 V).

## Anova
- Developer docs (BLE API for A2/A3 cookers; the Pro may differ): <https://developer.anovaculinary.com/docs/devices/a2-a3/api-reference>
- The Android app as examined (version 3.6.7, code 2148, the one that ran the failed update), from APKPure, a
  mirror, not Google Play (its signature wasn't compared): <https://apkpure.com/anova-culinary/com.anovaculinary.android/download>.
  The package's SHA-256 and the analysis: kept privately.
- Pricing context for the README "Why" section (checked 2026-11-02):
  - Newsletter sign-up discount, 10 % off the first order, as listed by coupon aggregators
    (<https://simplycodes.com/store/anovaculinary.com>, <https://dealhack.com/coupons/anova-culinary>). The figure is
    not in the static HTML of anovaculinary.com (pop-up), so it is `likely`, not read from Anova's own page.
  - Precision Cooker Pro (1200 W) at $199 at Amazon US, "$200 off the going rate", Black Friday 2020: 9to5Toys,
    2020-11-23, <https://9to5toys.com/?p=639793>. `confirmed` (article read).
- Community repair report, Precision Cooker Pro head (glued glass, 4 screws, heat-staked board, speaker wires):
  <https://community.anovaculinary.com/t/defective-touch-sensors-and-solution/34678>
- Anova support: disassemble/reassemble the Pro (skirt + end cap only): <https://support.anovaculinary.com/hc/en-us/articles/360027636811>
- Community thread on FCC IDs / Wi-Fi modules (older models): <https://community.anovaculinary.com/t/fcc-id-wifi-frequency-wifi-output-data/666>

## Bench tools
- **cc3200tool**, toniebox-reverse-engineering fork: a Python client for the CC32xx ROM boot loader over UART (file
  list, file read/write, raw flash read/write; improved CC3220 support per its README). Used through
  [tools/cc32xx](../tools/cc32xx/README.md), read-only by default. <https://github.com/toniebox-reverse-engineering/cc3200tool>
  (the commit used is recorded in the journal).
- **TI software on the bench PC** (versions, hashes and signatures in the journal): Uniflash
  9.7.1.5912 (Image Creator 3.24.4.1, XDS110 drivers), SimpleLink CC32xx SDK 7.10.00.13 and 2.40.02.00 (the SDK
  Anova's 3.3.35 was built with), MSYS2's flashrom 1.8.0. How Image Creator talks to the boot loader was read
  from its own `slbootloader` module.
- Andonstar AD409-Pro user manual, Ver 01 (SHA-256 `ae97a7aa4924bd263acfcebb3a8629ee888f29490b9ec21a570becb8e1ad0af6`,
  read 2026-11-03): <https://electrokit.com/upload/quick/1a/a6/873e_AD409-pro_users_manual-Ver_01_1.pdf>. Reviews,
  the Novatek dashcam API and what was measured: [microscope.md](microscope.md#sources).

## TODO
- [x] Identify the unmarked-by-name chips: U17 = NCP59800, U13 = AKM AK4637, U14 = Lumissil
  IS31FL3737. Left: U2 `CG4`.
