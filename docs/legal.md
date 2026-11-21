# Legal: the bounds we work within

This page states what this project does, what it refuses to do, and why the author believes the first is lawful. It
is the author's understanding, written by an engineer, not legal advice. The author is in Belgium. Anova is a US
company (the FCC grantee is Anova Applied Electronics, Inc., part of the Electrolux group), the repository is hosted
by GitHub in the US, and the site is served from US and EU infrastructure. The United States comes first below for
that reason.

## What this project is
A repair of a device the author owns, documented in public: the hardware examined, the findings written down with
their sources, the attempts to get it working again, and the manufacturer's answers on the record. It is not
affiliated with, endorsed by or sponsored by Anova. "Anova" and "Precision Cooker" are Anova's trademarks and are
used here only to name the product.

## United States
- **Reverse engineering is lawful.** The Defend Trade Secrets Act states that "reverse engineering" of a product is
  not an improper means of acquiring information (18 U.S.C. §1839(6)(B)). Disassembling, photographing, probing and
  measuring a device the author owns, and publishing what was observed, rests on that.
- **Copyright (17 U.S.C.).** The photos, text and drawings here are the author's own work. Anova's firmware is
  Anova's copyrighted work and is **never reproduced**, not a byte of it. The FCC exhibits are public records of a
  federal agency, cited by exhibit number; the manual and test reports are linked, not copied. Anova's support replies
  are quoted word for word on the [correspondence](correspondence.md) page: short, routine customer-service messages,
  reproduced so that readers can judge the exchange for themselves, with the agent's name and every identifier
  removed. The author reads that as fair use (17 U.S.C. §107: factual content, documentation and criticism, no market
  for the messages). Any rights holder who disagrees can use GitHub's DMCA process (17 U.S.C. §512) or the procedure
  at the end of this page; the item comes down first and is discussed after.
- **Anti-circumvention (DMCA §1201).** Nothing here circumvents a technological protection measure, and no tool or
  method for doing so will ever be published. Reading one's own flash chip for a backup copies an encrypted blob
  without defeating anything; the recovery procedures described are the ones the chip's manufacturer documents for
  its own chips. If the project ever found a way around the device's signing or encryption, that finding would stay
  private. This is the line the author treats as absolute.
- **Trademarks (Lanham Act, nominative fair use).** The product is named because there is no other way to refer to
  it. No logo is used, no affiliation is implied, and this page and the README say so.
- **Defamation.** Every statement about Anova on this site is either a dated fact from the author's own
  correspondence, quoted word for word on the [correspondence](correspondence.md) page or paraphrased elsewhere, or an
  opinion marked as the author's. No motives are asserted. No employee is named.
- **Right to repair.** Several US states have repair laws aimed at manufacturers' obligations. Nothing here relies on
  them; the project needs no permission beyond ownership.

## Belgium and the European Union
- **Reverse engineering is lawful.** The Trade Secrets Directive (EU 2016/943, art. 3(1)(b)), transposed in the
  Belgian Code of Economic Law (Book XI), makes "observation, study, disassembly or testing" of a product lawfully in
  one's possession a lawful acquisition of whatever it reveals.
- **Copyright.** As above: own photos, own text, own drawings. The circuit itself is not a copyrightable work; a
  schematic drawn from observation is the author's own drawing, not a copy of Anova's (which is confidential in the
  FCC filing and has never been seen). Firmware is never reproduced. The support replies quoted on the
  [correspondence](correspondence.md) page are, in the author's reading, routine messages below the threshold of an
  "author's own intellectual creation". The quotation exception (Code of Economic Law, Book XI) is written for works
  already lawfully made public, which private e-mails are not, so the author relies on that reading and on the
  procedure at the end of this page, not on the exception.
- **Anti-circumvention.** Directive 2001/29/EC art. 6, transposed in the Code of Economic Law (Book XI), prohibits
  circumventing effective technological measures and distributing means to do so. Same line as under US law: not
  done, not published.
- **Defamation (laster en eerroof, Penal Code art. 443 and following).** Requires false allegations of fact made with
  intent to harm. This site publishes true, dated facts and labelled opinions, with sources.
- **Consumer law.** The legal guarantee under the Sale of Goods Directive (EU 2019/771) has lapsed for this unit. The
  Right to Repair Directive (EU 2024/1799) covers listed product categories, and a sous-vide cooker is, as far as the
  author can tell, not one of them. Nothing here relies on either.
- **Data protection (GDPR).** No personal data of anyone else is published: the support agent's name is removed from
  the quoted correspondence, and nothing left in it identifies them. The author appears under a handle. The unit's
  serial number, the order number and the support ticket number are withheld.

## Everywhere else
The author cannot know what is lawful where you are. Reverse engineering, publishing teardowns, modifying appliances
and even reading this site may be restricted in your jurisdiction. Whether you may read, download, reuse or apply any
of this is your responsibility, not the author's.

## What this project will never publish
- Anova firmware, flash dumps, or any fragment, excerpt, string listing or file reproduction of them. Structure may be
  described; content is never shown.
- Keys, certificates, credentials, tokens, or anything that gives access to Anova's servers or services.
- Any way around the device's signing, encryption or other protection, should one ever be found.
- Third-party documents: the user manual, test reports, datasheets. Links only.
- The unit's serial number, the order number, the support ticket number, names of Anova staff, or anyone's personal data.

## How this project writes about Anova
Dated facts from the author's own correspondence, quoted word for word on the [correspondence](correspondence.md)
page (names and identifiers removed) and paraphrased elsewhere; opinions marked as opinions; never motives; a public
source or nothing. Anova's help, if it comes, is credited in full.

## Images
All photos are the author's own unless marked otherwise. Every image from another source carries that source at
every use: in the image itself, in the caption, and in the data it was made from. Today the other sources are the
FCC filing for this product (FCC ID 2APBOAN600, internal-photos exhibit 3999178) and, since 6 Nov 2026, Espressif's
ESP32-DevKitC V4 pin layout from the ESP-IDF documentation, kept unchanged and under its own licence, the Apache
License 2.0, not this site's (see `images/third-party/`).

## Licence
Content under CC BY-SA 4.0, code under MIT, as stated in [LICENSE.md](../LICENSE.md). Reuse is welcome under
those terms. Nothing here grants any right to Anova's firmware or trademarks, which are not the author's to license.

## Safety
The power board carries mains voltage, which can kill. Opening the unit voids its warranty and its CE/FCC
certification, radio included; a modified unit is not a certified appliance. Nothing here is a recommendation to do
any of this; everything is at your own risk, without warranty or liability of any kind.

## If you object
If you hold rights in something published here and believe it shouldn't be, open an issue on the repository
stating what and why. The item is taken down first and discussed after. The repository itself stays online.

## Changes
This page is revised when the author learns better.

- 2026-11-02: first published.
- 2026-11-02, later the same day: the [correspondence](correspondence.md) page added; the copyright, defamation and
  data-protection notes extended to cover quoting Anova's replies word for word.
