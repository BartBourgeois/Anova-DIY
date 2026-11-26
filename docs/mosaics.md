# Microscope mosaics

The stitched microscope mosaics at full resolution, about 229 px/mm. Scroll or pinch to zoom, drag to pan; **1:1**
jumps to 100 % (one mosaic pixel per screen pixel). The readout shows the zoom and the mosaic pixel under the pointer,
the same coordinates as the `box` and `redact` entries in
[crops.json](../annotations/crops.json). Spots the tiles didn't cover are transparent. The production label's Data
Matrix is greyed out, as in every published image.

**Schema** (the tick box above the board) lays the board's schema over the photo, read-only: every part, pad, test
point and via as raptox boxed them on this mosaic in his bench navigator, the top-layer copper he traced over it, and
the beeps. Click a pad, a part or a trace to see its net: everything else on it lights up and the panel lists it, with
the part, the pin's datasheet name (for J8, its function from the [J8 pin table](hardware/j8.md)) and how sure each of
those is. **Find** jumps to a name (`U7.29`, `TP33`, `J8`), and a link to `#schema:U7.29` opens the page on it.
How sure: the traces are `likely` (each one seen on the mosaic and approved as drawn, not measured), the beeps
`confirmed` (measured), a part's identity as in the [components list](hardware/components.md), and a name `confirmed`
where it is printed beside the part, else `likely` or `guess` as boxed. The top layer stops at vias, so a net may go on
through another layer and two nets may be one. The same nets as a table: [nets-top.md](hardware/nets-top.md). The
layer is generated from the navigator's export, never hand-edited.

The viewer tiles and the lossless downloads are generated from the local mosaic by
[deepzoom.py](../tools/deepzoom.py), never hand-edited. Set details, scale and hashes are in the
[photo log](photos.md).

## Main board, component side (2026-11-03)

<div class="mosaic-viewer" data-dzi="../../images/mosaics/2026-11-03_main_component-side.dzi"
     data-schema="../../images/mosaics/2026-11-03_main_component-side.schema.json"></div>

22635x16731 px at 229.4 px/mm, from 335 tiles ([set details](photos.md#2026-11-03-microscope-mosaic-main-board-component-side)).
**Lossless original:**
[2026-11-03_main_component-side_mosaic.png](https://github.com/BartBourgeois/Anova-DIY/releases/download/mosaics/2026-11-03_main_component-side_mosaic.png)
(PNG with alpha, 430 MB, SHA-256 `ea6f871d…9623`), the same pixels without the viewer's WebP compression, for measuring
and tracing offline. It is too big for most image viewers and browsers; GIMP, Krita or KiCad's image import cope.

<script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/5.0.1/openseadragon.min.js"></script>
<script src="../../_web/mosaic-viewer.js"></script>
