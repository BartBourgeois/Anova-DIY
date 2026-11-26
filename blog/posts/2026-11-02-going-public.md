---
date: 2026-11-02
categories:
  - Diary
authors:
  - raptox
---

# Day two: going public, and Any%

Day two was paperwork. Nothing got soldered, nothing got measured, and by the evening the whole project was public:
this website, the repository behind it, a roadmap, and every message exchanged with Anova support so far, word for
word.

<!-- more -->

## Why public

Because the next owner with a dead Pro deserves better than a forum thread that ends in "nvm, fixed it". Everything
learned goes here the day it's learned, dated, with a confidence label and its source. The
[timeline](../../docs/timeline.md) is the record. These posts are the story around it.

Mistakes get corrected in the open. The timeline has a corrections table, and its first entry is from today. I had
written that the update bricked the cooker. That's what I believe, but believing isn't measuring. It now says "died
after an interrupted update", and it stays that way until the first measurement on the bench rules out a
coincidental power-supply failure.

## Two cases

The [roadmap](../../docs/roadmap.md) plans for both outcomes. In case 1 Anova helps, with one of the four things I
asked for on day one (a firmware image with recovery instructions, a replacement main board at my cost, a mail-in
reflash, or a refurbished unit). In case 2 nobody helps and we do it ourselves, all the way: from a multimeter and a
phone up to a main board of our own. Some of those steps are insane for a kitchen appliance. That's the point.

There's also a point of no return. Even if Anova comes over the bridge tomorrow, the investment is made. Help would
change the repair. It wouldn't end the project.

## Word for word

The support exchange is published as it was sent, with names and identifiers removed:
[correspondence](../../docs/correspondence.md). A summary is always somebody's reading. This way you can do your
own.

## Any%

My cooker's display stopped at 75 %. Yours may have frozen on another number. And in speedrunning, Any% is the
category where all that counts is finishing, by whatever route works. So the project goes by Any%, and there's a
seven-segment logo to prove it.

## The working assumption

One thing did move on the hardware side, on paper. The working assumption is that the power board is fine and the
problem sits after the 30-pin flat cable that links it to the main board. One supply measurement at that connector
tests it. That needs a break-out board for the cable, due tomorrow.
