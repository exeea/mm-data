# Paperdolls

The location regions that the GPU battle HUD's unit panel draws as its paperdoll: one platform-neutral JSON file per
unit family and view, with filled regions, their outlines and one label anchor per location. The game reads these files
with libGDX's JSON reader; it never reads the SVG art, Batik or AWT. Only location polygons, outline rings, anchors,
value boxes, a neutral hull and the shield variants are kept: no pips, pip areas, transfer arrows or decorations.

## Format

Coordinates are SVG units of the source, y down, rounded to 0.01.

- `bounds`: `[x, y, width, height]` of every region and the hull.
- `locations`: MegaMek locations in paint order. Each has `abbr` (MegaMek's abbreviation), `layer` (`armor`,
  `structure` or `shield`), `z` (paint order), `anchor` (`[x, y, r]`: the label point and the radius of the largest
  circle around it inside the region; the HUD fits the number to it), `vertices`, `triangles` (indices into the
  vertex pairs) and `rings` (outline rings, outer rings and holes).
- `boxes`: value boxes of aerospace and capital units (`SI`, `KF`, `SAIL`, `DC`), in the same form with layer
  `structure`.
- `hull` (optional): the art that belongs to no location, such as a vehicle's inner hull, drawn neutral.
- `shieldVariants` (biped and tripod front armor): per arm (`LA`, `RA`) the regions that differ when that arm mounts a
  shield: the capacity panel `DC{arm}` and absorption strip `DA{arm}` (layer `shield`), and the arm itself when the art
  redraws it over the shield (biped only). `outline` is the shield's one-shape outline, `split` the segment between
  panel and strip, `z` the paint order they follow and `bounds` the frame the variant adds. `panelAnchors` are two
  anchors in the halves of the capacity panel (the half away from the split first): where the strip is too thin for
  its number, as on the unit card, both numbers go there. A unit with two shields merges both variants; the converter
  checks that they never touch each other's regions.
