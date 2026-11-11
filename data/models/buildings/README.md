# Building kits

An asset `buildings/<family>/<name>` names its file here. A building without a look draws the standard kit of its
class and weight (`TilesetScenery.genericBuilding`), a fuel tank `fuel_tanks/fuel_tank_<weight>`
(`TilesetScenery.genericFuelTank`).

| Folder | Holds | Built by (`tools/buildings/`) |
| --- | --- | --- |
| `standard/` | `<class>-<weight>.json` and `<class>-<weight>-pieces.glb`: classes `building`, `fortress`, `hangar`, `gun-emplacement`; weights `civilian`, `light`, `medium`, `heavy`, `hard`, `castle-brian` | see [Kits](#kits) |
| `civic/`, `utopia/`, `frontier/`, `imperial/`, `heritage/`, `lunar_habitat/` | a look's kit, `<look>.json` and `<look>-pieces.glb` | see [Kits](#kits) |
| `fuel_tanks/` | `fuel_tank_<weight>.glb`, modelled connected kits, three levels of detail | `fuel_tanks.py [weight ...]` |
| `walls/` | wall kits by weight | `walls/README.md` |
| `authored/`, `debug/` | fixed models with `building_volumes` helpers; `debug/debug-authored.glb` is a two-hex demo (a two-level wing and a four-level tower) | `README-authored.md`, `debug_authored.py` |
| `fittings/` | `aviation-light.glb` | `aviation_light.py` |
| `multihex/` | `lunar-equipment.glb` | `lunar_equipment.py` |

There are two kinds of kit: **modelled** (every module a mesh in one GLB) and **generated** (a JSON spec that lays
pieces of a pieces GLB along the footprint's walls). Both are connected kits.

## Modelled kits

- One building a file: a group `<name>-lod0` and, normally, `<name>-lod1` (a `-lod2` is used when present). A kit
  under 200 triangles needs only `lod0`.
- Each group holds mesh nodes ending in `-base#`, `-floor#` and `-roof#`, at least one of each, numbered from 0 (gaps
  allowed), the same roles in every level of detail. Optional `-top#` modules are the storey under the roof.
- A building N levels tall draws one base, N-1 floors and one roof, each chosen by placement; with `top` modules, one
  replaces the highest floor of a building two or more levels tall. Changing the height keeps the storeys below.
- Base and floor modules are exactly 18 units high, Z up. All modules and levels of detail share one XY origin; a
  module's saved Z is ignored: it stands on its lowest point.
- Enterable buildings have hollow walls. Interior floors are generated from the roof's outline cut by the closed
  mid-storey walls, so keep notches and courtyards in those surfaces.
- Names are checked on load: Blender's `.001` suffixes and unknown tags are errors.

## Connections

Buildings and fuel tanks connect across the hexsides their exits name; a lower neighbour ends the connection at its
top. A kit that changes shape with its connections tags its nodes after the module:
`<name>-lod0-<module>[-<tag>[-<tag>]]`, each tag `link-<dir>` or `end-<dir>`, `dir` one of `n`, `ne`, `se`, `s`, `sw`,
`nw` (for example `pier-lod0-floor0-link-n`).

- A node without tags always draws. `link-<dir>` draws where the hex connects that way, `end-<dir>` where it does
  not; both tags of a two-tag node must hold.
- A node tagged for all six directions is a whole-hex piece: it stands alone, in place of its module's other pieces,
  for exactly those connections.
- A corner roof node with two `end-` tags may have a `-bend` twin, drawn where the hex connects only across the two
  hexsides opposite it, so a roof's plating can mitre along a 60-degree bend.
- A piece stacks through the levels where its tags hold: a base on the ground (a floor where it starts higher), then
  its own roof where it stops.
- A symmetric kit tags `n` only (one-tag pieces) or `n` and `ne` (corner pieces, in all four link/end states); the
  runtime turns them in 60-degree steps. Any other kit tags all six directions for every piece.
- Every variant of a module type and every level of detail has the same tagged pieces. A type may have none.
- The hex is 72 across its flats and 83.125 across its corners (Blender: X east, Y north, Z up, one unit a board
  unit). A one-tag `link` piece ends on its edge line, within one unit.

An isolated building can pivot about Z in the editor; any connection disables that. A core-only authored GLB switches
to the standard kit of its class and weight when connected.

## Footprints

A building kit has two footprints, chosen per connected building (editor: Footprint; hex appearance `footprint`):

- **Angled** (default): a linked hexside opens from corner to corner; an unlinked one closes with two walls meeting two
  thirds of the way to its midpoint. A lone hex and a hex with one link are whole-hex pieces.
- **Square** (generated kits only): a hex's core, the rectangle between its north and south hexsides as wide as a
  hexside, always stands; the cell beside each slanted hexside fills where the hex connects that way.

An isolated generated kit is a compact square (Square) or an inset hex (Angled), its details inside the hex; the
editor's padding shrinks it further.

## Generated kits

One JSON spec per pieces GLB (`GeneratedKit`). A field the style does not know is an error on load. Heritage, shortened:

```json
{
  "style": "bays",
  "pieces": "heritage-pieces.glb",
  "shared": {"bay": 12.0, "sidewalk": {"width": 4.0}},
  "roofs": {
    "mansard": {"material": "structures/heritage/slate", "runs": [{"bays": ["mansard"], "far": {"bays": ["mansard-far"]}}]},
    "parapet": {"material": "structures/heritage/slate", "runs": [{"bays": ["parapet"]}]},
    "vault": {"material": "structures/heritage/copper", "vault": {"shape": "bow", "rise": 9.0}, "runs": [{"bays": ["cornice"]}]}
  },
  "variants": [
    {"name": "habitat", "roof": "mansard", "base": [{"bays": ["shop"], "entrance": "porch"}], "floor": [{"bays": ["sash"]}]},
    {"name": "hangar", "class": "hangar", "roof": "parapet", "vaulted": "vault", "base": [{"bays": ["hall"]}], "floor": [{"bays": ["hall"]}]}
  ]
}
```

| Field | Meaning |
| --- | --- |
| `style` | `bays` (`BayKit`) or `habitat` (`HabitatKit`) |
| `pieces` | the pieces GLB beside the file |
| `variants` | the kit's named looks, the first the default. Editor: Variant; stored as the appearance's `kitVariant`; an unknown name draws the first |
| `shared` | written like a variant and lying under every variant: objects merge key by key, other values replace. A role's object (`base`, `floor`, `top`) lies under each of that role's runs |
| `roofs` | the kit's roofs by name |
| variant `roof`, `vaulted` | the roof it draws, and its other one for a hangar-class building (see [Vaults](#vaults)) |
| variant `class` | `hangar`, `fortress` or `gun-emplacement`: the variant a building of that class draws where its author chose none. Standard kits need none |

Colours are `tint`s written `#rrggbb` (sRGB). A surface is a board `material` with its `repeat` (units a repeat),
textured from the board position, so floors and roofs run on across pieces without a seam.

### `bays` variants

| Field | Meaning |
| --- | --- |
| `base`, `floor`, `top` | the storeys by role, each a list of runs the game picks among by placement: the ground storey, those above, and the storey under the roof of a building two or more levels tall |
| `lone`, `bandEnd` | the Angled lone hex's outline (counter-clockwise from its front) and the end of a one-link band |
| `floors` | the interior slab: `material`, `repeat`, `inset` off the walls, `heights` per level of detail |
| `sidewalk` | `width`, `kerb` along the ground storey |
| `varyBays` | lay a bay fewer or more by the wall's place where both stretch between 0.7 and 1.5 |
| `cornerRadius`, `cornerSegments` | round convex corners into facets, each laid with the run's `round` stretch |
| `wallInsets` | per level of detail, where facade skins sit behind the wall line (default 0) |
| `largeDoor` | see [Large doors](#large-doors) |

A roof has the slab fields of `floors`, its own `runs`, and optionally `underlay` (a surface just under a glass roof),
`fittings`, `aviationLights` and `vault`.

| Run field | Meaning |
| --- | --- |
| `bays`, `bay` | the pieces laid (several: chosen by the wall's place) and a bay's length; whole bays, the nearest count, stretched to fit each side of the outline |
| `margin`, `ends` | room kept at each end of a wall, and the stretch (`piece`, `length`) that fills it. A wall too short for a bay is laid with `ends` alone |
| `under` | one stretch along the whole wall |
| `planar` | materials textured along the wall's line (units a repeat) |
| `entrance` | the ground storey's piece in a hub face's first bay and beside the middle of a whole hex's front |
| `round`, `shallow` | the stretch at a rounded corner, and the one used where the walls turn less than 75 degrees |
| `joints` | for a kit of modules, one per hex's storey: `start` and `end` pieces (`length`) where a wall ends its module |
| `seam` | a roof run's stretch along each joint |
| `far` | the whole run the second level of detail lays; without one, every level lays the same |

Walls are split where they cross a corner piece's cut, each end a cut, joint, mitred corner, round or open end; bands
along a wall (sidewalk, skirt, parapet, eave) are mitred where it turns. A roof closes above lower neighbours
(`-closed-N`); where its edge meets the next hex at an inside corner it is mitred, meets in a valley (`-valley`) or
runs into the taller wall (`-wall`). A storey carries a sill (`-sill`) over a hex corner it turns only where it
closes links.

Roof `fittings` are a list of layouts, one drawn per hex by its place: each names pieces and where they stand
(`{"chimney": [[x, y], [x, y, turn in degrees]]}`; `{}` a bare roof); `{"square": [...], "angled": [...]}` where the
footprints differ. A kit without fittings or a vault has its Angled corner pieces built once and turned.

### `habitat` variants

`name`; board `materials` by role (`wall`, `roof`, `pier`, `concrete`); `cornerRadius` and `cornerSegments`; the roof:
a `parapet` (`height`, `width`), an `eave` (the rounded edge: `radius` and `segments` per level of detail) or a
`vault`; `skirt`; `piers`, their roof `tops` and `footings` (a `joint` and a `corner` piece each); the Angled `lone`
hex and single link band; the `storeys` above the ground (`windows` lit or dim, `shift`); and `fittings` per
footprint. In the pieces GLB a pier stands on its storey's floor at the wall line and is stretched to the storey; a
pier top likewise on the roof; a footing, hatch or vent stands as modelled.

### Vaults

A roof's `vault` spans its hall in place of the flat slab: a hexside wide, rising `rise` (at most 9, half a level) in
the `shape` of a `gable`, `bow`, `arch` or `plates`, in `segments` facets a side per level of detail.

- A Square hex's vault runs north to south along its column; columns side by side meet in level valleys. An Angled
  hex's runs out along each link: two links meet in a valley, unlinked sides are hipped. Three mutually linked hexes
  of one height keep the crown's height at their shared corner (`-crown`). A lone hex's runs north to south.
- Walls under it are filled up to it in the `gable` surface (`material`, which may carry `#paint`, `repeat`, `tint`),
  with a `verge` high band of the `trim` surface; ribs of the trim cross it every `ribPitch` (`ribWidth`,
  `ribHeight`).
- A variant's `vaulted` roof is drawn for a hangar-class building unless its author chooses the flat one
  (`building.appearance.roof`: `vaulted` or `flat`; editor: Roof). Other classes keep the variant's `roof`.

### Pieces GLB

- Each level of detail is a root `<name>-pieces-lod<n>` holding nodes `<piece>-lod<n>`. A node's position only lays
  the pieces out; its rotation and scale apply.
- A piece's x runs along its wall, left to right seen from outside; its facade faces -y, the wall line at y 0; z up
  from its storey's floor. Board units.
- Materials are named as board materials with their finish (`#paint`, `#emission-...`, `#night`, `#emission-off`);
  each finish draws as its own material. Vertex colours are linear shades.
- A cutout (alpha mode MASK) stays alpha tested. Glass on a blending board material is BLEND: drawn blended, casting
  no sun shadow.

## Kits

A kit's variants and roofs are those its JSON lists.

| Kit | Style | Built by |
| --- | --- | --- |
| `standard/building-light` | bays | hand-made art (`art/building_light_00.glb`) |
| the other `standard/building-<weight>` | bays | `standard_buildings.py`; medium, heavy and hardened from `art/building_<weight>-proposal.glb` |
| `standard/hangar-light`, `-medium`, `-heavy`, `-hard` | bays | `hangar_kits.py`, from `art/hangar_<weight>_a-proposal.glb` |
| `standard/fortress-light` | bays | hand-made art (`art/fortress_light_a_52.glb`) |
| the remaining `standard/` kits (fortresses, gun emplacements, civilian and Castle Brian hangars) | bays | `debug_placeholders.py`: diagnostic placeholders, flat panels in one colour a bay index |
| `civic/civic`, `utopia/utopia`, `frontier/frontier` | bays | `theme_kits.py` |
| `imperial/imperial` | bays | `imperial_kit.py` |
| `heritage/heritage` | bays | `heritage_kit.py` |
| `lunar_habitat/lunar_habitat` | habitat | the JSON alone |

Every surface is a board material (Material Maker projects in `tools/materials/structures/`).

## Tint and lights

- A building's tint is colour slot 0 of its appearance; it multiplies only materials marked `mmBuildingPaint`. A mixed
  atlas's `.tres` sets `metadata/mmPaintMask` to protect its unpainted regions. Connected hexes share the tint.
- `.board2` stores rotation, tint, footprint and kit variant under `components.building.appearance`.
- A window `.tres` carries `metadata/mmEmission = "night"`; a model's material overrides it with `mmEmission`
  (`always`, `night`, `off`, `blink`). Mixed wall and window atlases emit only through their window mask.
- `"aviationLights": true` (a bays roof, a habitat variant) stands `fittings/aviation-light.glb` on every outer corner
  of a roof 7 levels high or more (`ConnectedKit.LIT_LEVELS`), each roof twin's lights a node of their own
  (`<twin>-aol`).
- A unit on a generated kit's roof stands on the roof's own surface (parts keyed `<material>#deck`), up to half a
  level over the roof's game height; parapets, fittings and lights never raise it.

## Large doors

A building hex may have a large door on any hexside its building does not continue across
(`building.appearance.doors`: a height in levels by direction, `{"n": 3, "se": 2}`; `doorLinks`: each linked door's
group, `{"n": 1, "ne": 1}`). Only generated kits draw them (`KitDoors`); rules and the 2D views ignore them. A
hangar-class building has no interior floors by default.

- A door stands in the longest straight stretch of wall within its sixth of the hex, with up to 12.5 of wall beside
  it. Linked doors side by side along a straight wall are one wide door with jambs only at its ends.
- The hex's pieces are cut open from the ground to the door's top level less the `lintel`, through the wall's `depth`
  and 9 out of the wall line.
- A variant's `largeDoor` is its look, every value optional: `leaf` and `frame` surfaces (`material`, `repeat`,
  `tint`, `paint`, `glow`); the frame's `jamb`, `header`, `out` and `depth`; the leaf's `recess`, `panel` height and
  `section` width (joints in the `seam` surface); `lintel`; `margin`; a `stripe` of `stripeHeight`; `windows` (`glass`,
  `width`, `height`, `sill`, `pitch`); a `threshold` reaching `apron` out; and `pieces` standing in for the generated
  frame: `jamb`, `header` (in stretches of `headerLength`) and `crown`.

## Multi-hex buildings and lunar equipment

- `buildings/multihex/dome` and `biodome` are generated over a whole building (`BoardMultiHexBuilding`), with no model
  per hex. Their surfaces are the board materials in `structures/lunar/`.
- `multihex/lunar-equipment.glb` holds their support pieces, one node per piece and level (`<piece>-lod0`,
  `<piece>-lod1`), each on its origin with its front to +Y: `tanks`, `plant`, `airlock` and `pylon`.
- `lunar_equipment.py` also writes the board objects of the editor's Buildings > Rooftop
  (`board/scenery/roofs/`) and Buildings > Colony (`board/scenery/colony/`) sections; wall-mounted ones have their
  back on y = 0.

## Heavy industry

Heavy-industrial hexes are generated by `BoardIndustrial`, not by a kit: equipment with independent heights and pipes
to neighbouring industrial hexes, no interior floors. Its materials are `structures/industrial/paint`, `steel` and
`fan`.
