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
  SHA-256 `b982a744a2d763647993407ec5d3a5ed94a25208a2278d555a2dae5763a71d9e`. Pin descriptions: table 7-1, from page 11;
  pin multiplexing (UART0 options): page 23. Used for [nets.md](hardware/nets.md).
- UART flashing / embedded programming (SWPA230): <https://ti.com/document-viewer/lit/html/SWPA230A/setup-t4880149-140>
- Secure boot and encryption (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/887901/cc3220sf-boot-procedure-secure-boot-and-encryption>
- External flash security (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/983522/cc3220s-security-question-for-external-flash-and-the-secure-boot-flow>
- OTA rollback / pending commit (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/779805/launchcc3220modasf-rollback-of-firmware-after-ota>
- OTA broken after an interrupted update (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/wi-fi-group/wifi/f/wi-fi-forum/982731/cc3220sf-cc3220sf-update-functionality-is-broken-after-update-is-interrupted-in-certain-position>
- To read: CC3x20 Programmer's Guide (SWRU455), CC3x20 Built-In Security Features (SWRA567), OTA guide (SWRA510), Uniflash / Image Creator user guide (SWRU469).

## XMC XM25QH64A (serial flash U15/U16)
- Elnec programmer device page (package code H = SOP-8 208 mil): <https://www.elnec.com/en/device/XMC/XM25QH64A%20[SOP8-208]%20(QuadSPI)>
- Linux spi-nor patch adding XM25QH64A (JEDEC ID 0x207017): <https://lists.infradead.org/pipermail/linux-mtd/2018-April/080447.html>
- XMC product pages: <https://www.xmcwh.com/en/site/product_con/936>
- Same-family datasheet (XM25QH128A, includes the SOP 208 mil package and 2.7-3.6 V spec): <https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1811072025_XMC-XM25QH128AHIG_C328463.pdf>
- TODO: the exact XM25QH64A datasheet.

## TI CC2640R2F (BLE MCU)
- Datasheet: <https://www.ti.com/lit/ds/symlink/cc2640r2f.pdf>
- CC26xx serial bootloader interface (SWRA466): <https://www.ti.com/document-viewer/ja-jp/lit/html/SWRA466D/GUID-813A07F3-F86E-4862-A618-2A7E5B9A5F95>
- Bootloader backdoor (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/bluetooth-group/bluetooth/f/bluetooth-forum/704737/cc2640r2f-going-through-the-backdoor-of-the-bootloader>
- Debug lock via CCFG (TI E2E): <https://e2e.ti.com/support/wireless-connectivity/bluetooth-group/bluetooth/f/bluetooth-forum/931512/cc2640r2f-debug-interface-is-locked>
- To read: CC13x0/CC26x0 Technical Reference Manual (SWCU117), CCFG chapter.

## Anova
- Developer docs (BLE API for A2/A3 cookers; the Pro may differ): <https://developer.anovaculinary.com/docs/devices/a2-a3/api-reference>
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
- Andonstar AD409-Pro user manual, Ver 01 (SHA-256 `ae97a7aa4924bd263acfcebb3a8629ee888f29490b9ec21a570becb8e1ad0af6`,
  read 2026-11-03): <https://electrokit.com/upload/quick/1a/a6/873e_AD409-pro_users_manual-Ver_01_1.pdf>. Reviews,
  the Novatek dashcam API and what was measured: [microscope.md](microscope.md#sources).

## TODO
- [ ] Identify U14 `T3018` (QFN-40), U13 `4637 / 638A` (QFN-20), U17 `S9800`? (DFN-8).
