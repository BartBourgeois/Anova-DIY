# Incident: Precision Cooker Pro dead after an interrupted OTA update

## Unit
| | |
|---|---|
| Model | Anova Precision Cooker Pro, type AN600-20 (EU, 220-240 V) |
| Serial number | AN600-EU10-… (withheld in the public repo) |
| Warranty | expired |
| History | Worked normally until the update. Never dropped, opened or damaged. |
| Status | **Cooking again since 6 Nov 2026** (the 6 Nov row below; [the story](../blog/posts/2026-11-06-it-cooks-again.md)) |
| Update path | Anova app 3.6.7 on a Pixel 10 Pro XL |

## Timeline (2026)
| Date | Event |
|---|---|
| 28 Oct | Firmware update started from the Anova app. Progress **stalled at 75%**, shown on the cooker's own display. Left plugged in overnight, it never finished. The home router recorded the unit's last Wi-Fi traffic at 17:52 CET. |
| 29 Oct (morning) | Unplugged, rested 2 h, plugged back in: **no beep, no display, no LEDs**. |
| 29 Oct | Support ticket #… (number withheld) opened. Anova suggested leaving it plugged in overnight. |
| 30 Oct | Overnight power-on made no difference. Still completely dead. |
| 1 Nov | Anova: out of warranty. Offered 10% off a new unit. |
| 1 Nov | Asked Anova for (1) a signed firmware image + recovery instructions, (2) a replacement main board at the owner's cost, (3) a mail-in reflash, or (4) a refurbished unit. Started this project in parallel. |
| 1 Nov | Head opened (glass cut free, 4 screws). Main board photographed; chip markings read. See [photos.md](photos.md). |
| 6 Nov | Both chips' flash backed up; the Wi-Fi chip found **locked** by its own security-alert counter (at its limit). Reprogrammed through its boot loader with the current firmware and the unit's own files. **It cooks again**: panel, Wi-Fi, app and a 54 °C test cook all work. See [timeline.md](timeline.md). |

The exchange with Anova support, word for word with names and identifiers removed: [correspondence.md](correspondence.md).

## Observations to keep in mind
- "Completely dead" means not even the power-on beep. That points to one of these:
  - the MCU that drives the UI/buzzer never starts its application
  - a logic supply rail is missing
  - the UI MCU is waiting in a ROM bootloader state
- The CC3220 OTA mechanism should roll back an uncommitted image after a reset. This unit did not recover, so either:
  - the update touched something without rollback (service pack, a second MCU, the filesystem metadata), or
  - the failure is not in the CC3220 image at all.

  See [firmware/recovery-strategy.md](firmware/recovery-strategy.md).
