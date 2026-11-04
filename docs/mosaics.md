# Microscope mosaics

The stitched microscope mosaics at full resolution, about 229 px/mm. Scroll or pinch to zoom, drag to pan; **1:1**
jumps to 100 % (one mosaic pixel per screen pixel). The readout shows the zoom and the mosaic pixel under the pointer,
the same coordinates as the `box` and `redact` entries in
[crops.json](../annotations/crops.json). Spots the tiles didn't cover are transparent. The production label's Data
Matrix is greyed out, as in every published image.

The viewer tiles and the lossless downloads are generated from the local mosaic by
[deepzoom.py](../tools/deepzoom.py), never hand-edited. Set details, scale and hashes are in the
[photo log](photos.md).

## Main board, component side (2026-11-03)

<div class="mosaic-viewer" data-dzi="../../images/mosaics/2026-11-03_main_component-side.dzi"></div>

22635x16731 px at 229.4 px/mm, from 335 tiles ([set details](photos.md#2026-11-03-microscope-mosaic-main-board-component-side)).
**Lossless original:**
[2026-11-03_main_component-side_mosaic.png](https://github.com/BartBourgeois/Anova-DIY/releases/download/mosaics/2026-11-03_main_component-side_mosaic.png)
(PNG with alpha, 430 MB, SHA-256 `ea6f871d…9623`), the same pixels without the viewer's WebP compression, for measuring
and tracing offline. It is too big for most image viewers and browsers; GIMP, Krita or KiCad's image import cope.

<script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/5.0.1/openseadragon.min.js"></script>
<script>
document.querySelectorAll(".mosaic-viewer").forEach(function (el) {
  var viewer = OpenSeadragon({
    element: el,
    tileSources: el.dataset.dzi,
    prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/5.0.1/images/",
    showNavigator: true,
    maxZoomPixelRatio: 4,
    visibilityRatio: 0.5,
    gestureSettingsMouse: { clickToZoom: false }
  });
  var vp = viewer.viewport, pointer = null;
  var bar = document.createElement("div");
  bar.className = "mosaic-readout";
  var oneToOne = document.createElement("button");
  oneToOne.textContent = "1:1";
  oneToOne.title = "Zoom to 100 %";
  oneToOne.onclick = function () { vp.zoomTo(vp.imageToViewportZoom(1)); };
  var text = document.createElement("span");
  bar.append(oneToOne, text);
  viewer.addControl(bar, { anchor: OpenSeadragon.ControlAnchor.BOTTOM_LEFT });

  function show() {
    if (!viewer.world.getItemCount()) return;
    var s = Math.round(vp.viewportToImageZoom(vp.getZoom(true)) * 100) + " %";
    if (pointer) {
      var p = vp.viewerElementToImageCoordinates(pointer);
      s = "x " + Math.round(p.x) + "  y " + Math.round(p.y) + " px  ·  " + s;
    }
    text.textContent = s;
  }
  viewer.addHandler("open", show);
  viewer.addHandler("animation", show);
  new OpenSeadragon.MouseTracker({
    element: viewer.canvas,
    moveHandler: function (e) { pointer = e.position; show(); },
    leaveHandler: function () { pointer = null; show(); }
  });
});
</script>
