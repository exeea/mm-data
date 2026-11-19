# Road tunnel portal

Three GLBs share the same portal geometry:

- `data/models/board/scenery/road/road-tunnel.glb`: the short wing walls as first made, 309 triangles.
- `data/models/board/scenery/road/road-tunnel-long-wings.glb`: long wing walls, 309 triangles.
- `data/models/board/scenery/road/road-tunnel-bridge.glb`: no wing walls, 293 triangles.

`BoardTunnel` picks the ground portal: the long wings on the height field (`-Dmegamek.gpu.terrainField`), where the
tunnel enters natural ground and its scree lies along their tops, unless a road or rail leaves the road hex at a side
beside the tunnel's (a long wing would stand on it); the short wings everywhere else and with the field off.

All are written by `road_tunnel.py` (standard library only; `python road_tunnel.py`): the portals as commit
434f9b8e00 held them, plus a concrete HEADWALL on the shell's front: the front face carried up from the roof slab
(Z 22.08) to Z 25.4, 1.5 units thick (Y -0.05 to 1.45), under a cap from Z 25.4 to 26 that stands 0.3 proud in front
and at the ends (X 22.55, Y -0.35 to 1.75), a drip edge. The cap's top and back and the wall's back carry a dust tint
in the vertex colours on the ground portals (where the height field's scree lies against them); the bridge portal's
are plain. The generator also keeps the portals' triangle and vertex counts in `manifest.json`. The headwall hides the slab's back edge;
the field piles scree behind it (the portal's join). The generator that first made the portals was
`tools/build_tunnel_asset.py`, removed in a5703e7a06 (2026-10-15).

Both use one LOD0. The bridge portal has no `tunnel-wings` part; the arch, deep
shell and lining are identical.

The ground portals' headwall, cap, shell front and wing walls take `scenery/tunnel-portal`: one 1024 picture of
weathered board-formed concrete (`tools/materials/portal_sources.py` from two ImageGen studies in its project's
`sources/`), each face mapped into its region by `road_tunnel.py` (`photo`, regions from `sources/regions.json`),
clamped. Its export into `data/models/board/textures/scenery` is pending (Material Maker). The bridge portal keeps the
plain material: the photo reads darker and dirtier than the clean cast walls it is set in.

The bridge portal and every lining take the shared `scenery/tunnel-concrete` material: cast concrete
with continuous fine aggregate and pores, without panels or tie-hole patterns. Their base colour
names its albedo (`../../textures/scenery/tunnel-concrete_albedo.png`) and its `.tres` gives the
normal map (Material Maker project `tools/materials/scenery/tunnel-concrete/`); the retaining walls
and dragon's teeth use the same material. The GLBs embed no images. The floor names
`roads/asphalt`; at runtime it receives its approach's
road material (asphalt, gravel or dirt), including the existing normal/surface
maps and world-space texture alignment. Concrete repeats every 24 units across
and up the portal, and the lining unwraps continuously around the arch.
The outer side walls and roof extend the full 36-unit tunnel depth, allowing
the portal to be embedded in a sloping face. The lining and piers do not have
overlapping inner faces. The floor's and lining's vertex colours follow
`BoardTunnel.light`: full light at the hex edge (Y=3), falling off to a dark end
cap at Y=36; a road's verges and markings carried into the tunnel darken alike.

The 30-unit carriageway, an ordinary road's, continues through the entrance to
Y=36. Runtime placement stretches only the lateral dimension for a wider route:
the shared road/rail corridor's full clearance width for a rail portal, which
also follows the enlarged conventional ballast. The arch cut and roadside
clearance use the same inverse transform. Concrete verges fill the remaining
opening width. The floor begins at Y=2.75,
slightly before the shared hex edge at Y=3, with a 0.02-unit recessed lip. This
small underlap seals the lattice's oblique edges without coplanar fighting.

Coordinates: Z up, +Y into the cliff, opening at Y=0, base at Z=0. Opening is
35 units wide, with vertical piers to Z=6.9 and a 16-segment half ellipse rising
10.925 more. The shell is 44.5 units wide and its roof reaches Z=22.1. The short wing
walls flare from 21.4 to 27.4 units either side over the 6 units in front of the
opening, falling from 9.2 to 4 units high. The long ones, 1.75 thick, run from inside the headwall (Y 0.3) to 21.4
units in front of the opening, their outer faces flaring 0.4 a unit from X 21.44 (30.12 at their ends), their tops
falling from the cap's underside (Z 25.4) at 45 degrees to 4 units (`BoardTunnel.Wings`). The headwall's cap reaches Z 26 between Y -0.35 and 1.75. `BoardTunnel` uses these dimensions when clipping
the existing terrain for the opening. Update that contract if these change.

Generated reference: `road-tunnel-reference.png`, made with the built-in imagegen
tool. Prompt requested a realistic low-poly concrete portal in a natural cliff,
a thick arched rim, flared wing walls, a deep dark lining, and a two-lane road
width, viewed from the front and three-quarter angle.

This is a visual entrance only; it does not add a traversable tunnel or change
board elevations, exits or movement rules.

`BoardTunnel` places bridge portals at the actual deck elevation, independent
of the terrain family beneath or beside the bridge. The opening must fit in
the facing dry cliff. Ground roads keep the existing grading decisions.
Bridge-deck portals stand on `unofficial/Derv_Maps/35x35 Quatre Belle.board` (for example the deck at 0409
entering its concrete column; `GpuTunnelSmokeTest` uses that board). The bridge portal keeps a plain cap: its
headwall carries no dust, which reads as a dark strip on clean cast walls.

Whole decorative rocks are excluded from the shell, wing walls and immediate
road approach. Formations above the portal and beside its cleared footprint
remain. `BoardTunnel.obstructs` defines this small visual clearance.

The shared plain concrete albedo was generated with the built-in imagegen tool.
Its original prompt is saved in `road-tunnel-texture-prompt.json`.
