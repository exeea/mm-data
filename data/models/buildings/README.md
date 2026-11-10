# Modular building kits

Store a modelled kit as `<family>/<name>.glb`, for example `fuel_tanks/fuel_tank_light.glb`, and a generated kit as
a JSON file beside its pieces GLB: the standard kits as `standard/<class>-<weight>.json` with
`<class>-<weight>-pieces.glb` (classes `building`, `fortress`, `hangar`, `gun-emplacement`; weights `light`, `medium`,
`heavy`, `hard`), a look's kit as `<look>/<look>.json`, for example `heritage/heritage.json`.
An asset `buildings/<family>/<name>` names its file here. Generic buildings select the standard kit by gameplay class
and weight (`TilesetScenery.genericBuilding`), including when imported from a legacy `.board`. Old roof artwork is no
longer a 3D design. A fuel tank selects `buildings/fuel_tanks/fuel_tank_<weight>` the same way
(`TilesetScenery.genericFuelTank`); the kit follows the hex's connections.

Each file contains one building: an identity `<name>-lod0` group and, normally, optional `<name>-lod1`.
Author no more than two levels for this work; simple kits (especially under 200 triangles) can use just `lod0`.
This is an asset budget: if an existing kit supplies `<name>-lod2`, the loader uses that additional level.
Each group contains mesh nodes ending in `-base#`, `-floor#`, and `-roof#`, with at least one variant of each.
Number variants from 0; sparse numbers are also supported. Roles must match across LODs.
For N levels, the runtime chooses one base, N-1 independently chosen floors (including `floor0`), and one roof. A kit
with `topN` modules draws one of them, in place of a floor, as the storey under the roof of a building two or more
levels tall: the storey that ends a wall's windows, under an arch or a beam.
Choices are stable for each placement; changing height preserves the base, roof, and existing lower floors.

Base and floor meshes are exactly 18 units high in authoring Z-up space. Enterable buildings have hollow walls.
Author all modules and LODs relative to the same XY origin, with LODs superimposed rather than offset sideways.
The loader preserves authored XY coordinates and derives only each module's vertical base from geometry when
assembling one base, N-1 floors and a roof. Modules may be stacked vertically for display; their saved Z placement
is discarded. Asymmetric details do not change a module's horizontal placement. For enterable buildings,
the full roof projection intersected with the selected modules' closed mid-storey wall sections defines generated
interior floors and struts (a storey whose walls close nothing, a hex open towards connected neighbours, keeps the
roof projection). Keep notches and courtyards in those surfaces.

## Editor palette and legacy import

**Buildings**, **Fortresses**, **Hangars**, **Gun Emplacements** and **Walls** each expose Civilian, Light, Medium,
Heavy, Hardened and Castle Brian directly. **Looks** holds
Lunar habitat, Glass dome and Biodome; **Specials** holds authored buildings; **Utilities** holds elevators.
All twenty-four building class/weight combinations have kits, including the diagnostic placeholders described below.
The light, medium, heavy and hardened hangars are finished kits (`standard/hangar-<weight>.json`, below).

Legacy `.board` import preserves a building's weight, class, height and construction factor while discarding
its old roof-art choice. Lunar buildings use the current lunar looks; the old Mars/volcano sealed look becomes
Glass dome. The seven retired DropShip selectors (`building:4:69` through `building:4:75`) are omitted entirely,
including their building rule state. Ground elevation, pavement and other terrain remain.
The removed legacy GLBs and artwork galleries are not required by this conversion.

## Connected kits

Generic buildings select a modular kit by gameplay weight and class even with no connections; single-hex artwork is
an explicit look. An isolated building can pivot about Z in the editor. Any incoming or outgoing building connection
disables the pivot. A core-only authored GLB (base/floor/roof nodes without side tags) switches to the generic modular
kit for that building's weight/class when connected. The editor keeps this change in the connection's undo step.
The `debug/debug-authored.glb` asset under **Specials** uses the authored-volume path, like the HPG.
At default scale and rotation, its connected, notched wings occupy exactly two hexes: an orange two-level
wing and a blue four-level tower, with roofs labelled 2 and 4. Closed `building_volumes` helpers follow both
outlines. The shell has no baked interior floors; the runtime slices it by hex and creates floors that preserve
the notches. This is a fixed model, without repeatable base/floor modules. Only the walls receive tint.

Building appearance stores a tint in colour slot 0, using the editor's existing colour picker. White restores the
original artwork; another colour multiplies only materials marked `mmBuildingPaint` in linear light. Windows,
roof slabs and equipment keep their own finishes. Mixed atlases' `.tres` set `metadata/mmPaintMask` to protect their unpainted regions.
Connected hexes share the chosen tint. `.board2` version
3 stores rotation, tint, footprint and kit variant under `components.building.appearance`.

Window emission uses the same day/night control as authored buildings. Shared window `.tres` resources carry
`metadata/mmEmission = "night"`; their emission fades out in daylight without changing their albedo. A model's material overrides this with `mmEmission` (`always`, `night` or `off`). Mixed
wall/window atlases emit only through their window mask, independently of wall tint. The light building's far
window mask is baked from the near windows via Blender MCP (`tools/buildings/bake_light_paint_mask.py`) into the
`light-far` Material Maker project's sources. Diagnostic kits without windows remain unlit.

`tools/buildings/debug_placeholders.py` supplies flat diagnostic kits for the missing medium/heavy/hardened buildings
and fortresses, all gun emplacements, and the civilian and Castle Brian weight of every class (`standard/`). They use the light building's spec and inexpensive
box panels: bay indices 0–5 are red, orange, yellow, green, cyan and violet; alternate base/floor modules are lighter.
Roofs are yellow and floor/sidewalk slabs grey. These are placeholders, not weight-specific finished artwork. Each
kit has its own JSON and pieces GLB so artists can replace it independently. The script preserves existing asset
UIDs, and registers new kit IDs once. It leaves the original light building, light fortress and lunar habitat intact.

Buildings and fuel tanks connect across the hexsides their exits name. A neighbour of the same structure (building or
fuel tank) that connects back and stands lower ends the connection at its top. A kit that changes shape with its
connections tags its mesh nodes after the module:
`<name>-lod0-<module>[-<tag>[-<tag>]]`, each tag `link-<dir>` or `end-<dir>`, `dir` one of `n`, `ne`, `se`, `s`,
`sw`, `nw` (clockwise from north), for example `pier-lod0-floor0-link-n`.

- A node without tags is the core and always draws. `link-<dir>` draws where the hex connects towards `dir`,
  `end-<dir>` where it does not; both tags of a two-tag node must hold. A module may have tagged nodes only.
- A whole-hex node tags all six directions: it stands alone, in place of its module's other pieces, for exactly those
  connections, on the levels that keep the ground level's connections (above, the corner pieces follow the falling
  connections). Every module carries the kit's whole-hex nodes; a symmetric kit authors each once, turned for the rest.
- A linkless corner roof node (two `end-` tags) may have a `-bend` twin, for example
  `kit-lod0-roof0-end-s-end-sw-bend`: it stands in for the plain one where the hex connects across just the two
  hexsides opposite it (behind a 60-degree bend), so a roof's plating can mitre along the bend's two arms.
- Each piece stacks through the levels where its tags hold: a base on the ground (a floor where it starts higher),
  then its own roof where it stops, below the top or on it.
- A symmetric kit tags `n` only (one-tag pieces) or `n` and `ne` (corner pieces, in all four link/end states);
  the runtime turns them by exact 60-degree steps for the other directions. Any other kit tags all six directions
  for every piece.
- A generated kit's slabs (their `repeat` in the JSON, units a repeat) are textured from the board position, along the
  board's axes, whatever their UVs: a turned or neighbouring piece's floors and roofs run on without a seam.
- Every variant of a module type (base, floor, roof) and every LOD has the same tagged pieces. A type may have none:
  a fuel tank's ground pipes stand in its base only. Base and floor modules, tagged pieces included, are exactly
  18 units high; a module stands on its lowest point over all its pieces.
- The board's hex is regular: 72 across its flats, 83.125 across its corners (the regular 83.138 to a 32nd), every
  edge midpoint 36 from the centre within 0.005 (Blender: X east, Y north, Z up, one unit per board unit). Every kit
  is drawn as authored on it. A one-tag `link` piece ends on its edge line, within one unit.
- Names are checked when the kit loads: Blender's `.001` suffixes and unknown tags are errors.

Walls (`walls/README.md`), fuel tanks (`fuel_tanks/`), the lunar habitat (`lunar_habitat/`) and every
generated kit (`standard/` and the looks') are connected kits.

A building kit comes in two footprints, chosen per connected building in the board editor's Footprint row and stored
as the hex appearance `footprint` (`HexAppearance.Footprint`):

- **Angled**, the default and the classic exits art's: a linked hexside opens from corner to corner; an unlinked one
  closes with two walls meeting two thirds of the way to its midpoint, where the neighbouring arms' walls cross. Every
  wall of a corner piece runs 24 from an axis point to an axis point or a hex corner. A lone hex and a hex with one
  link are whole-hex pieces: the kit's lone block, and a band a hexside wide running through.
- **Square** (generated kits): right-angled blocks. A hex's core, the rectangle between its north and south hexsides
  as wide as a hexside, always stands; the cell beside each slanted hexside fills where the hex connects that way, so
  connected neighbours' cells meet in one rectangle.

A generated kit (`GeneratedKit`) builds both footprints from its JSON spec, one file per pieces GLB (Heritage, shortened):

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

- `style` dresses the footprint's walls: `bays` (`BayKit`) or `habitat` (`HabitatKit`). `pieces` names the pieces GLB
  beside the file. A field the style does not know is an error when the kit loads.
- `variants` are the kit's named looks, the first the default (a kit with one look lists one, `default`). The editor's
  Variant row (shown where a kit has more than one) gives a connected building one, stored in its hexes' appearance
  (`kitVariant`); a name the spec no longer lists draws the first.
- `shared` is written like a variant and lies under every variant: a variant states only what differs. Objects merge
  key by key, any other value replaces the shared one. A storey role's object in `shared` (`base`, `floor`, `top`) lies
  under each of that role's runs, and `planar` and `bay` in `shared` are every run's where it states none.
- `roofs` are the kit's roofs by name. A variant's `roof` names the one it draws; its `vaulted` names its other one
  (below).
- A variant's `class` (`hangar`, `fortress`, `gun-emplacement`) makes it the one a building of that class draws where its
  author chose none: a look's hall for hangars, its armoury for fortresses. Standard kits need none: the class chooses
  the file.
- Colours are `tint`s written `#rrggbb` (sRGB).

The walls are split where they cross a corner piece's cut, each end a cut, joint, corner (mitred), round or
open end; bands along a wall (sidewalk, skirt, parapet, eave) are mitred where it turns. Where a cut runs slanted across a
straight wall, both pieces show the same bays there: each lays on, past its cut, the bays the other lays.

A pieces GLB holds the modelled pieces, edited in Blender: each level of detail a root `<name>-pieces-lod<n>` holding
nodes `<piece>-lod<n>`; a node's position only lays the pieces out side by side, its rotation and scale apply. Board
units, Z up in the board's terms (glTF Y up), materials named as board materials with their finish (`#paint`,
`#emission-...`, `#night`, `#emission-off`, as the exporter names them), vertex colours linear shades. The kit draws each
finish as its own material: lit and dark glass can share one board material. A cutout (alpha mode MASK) stays
alpha tested, as in an authored GLB, though its board material blends: leaves keep the hover cutaway. Glass on a board
material that blends is BLEND (the exporter writes it for a transparent `.tres` that is no cutout): drawn blended, casting
no sun shadow, in kits and authored GLBs alike. A piece's x runs along its wall, left to right seen from outside, from the piece's start; its facade faces -y (Blender's
front view), the wall line at y 0; z up from its storey's floor.

- `standard/building-light.json` (`bays`): the light building, its pieces the hand-made art's window bays
  (`tools/buildings/art/building_light_00.glb`), six per module (`base0`, `base1`, `floor0`, `floor1`, `roof0`, the
  roof's carrying the cornice), one pier to pier per 24 of wall; a sidewalk along the ground storey.
- `civic/civic.json` and `utopia/utopia.json` (`bays`, built with their pieces by `tools/buildings/theme_kits.py`): the
  civic and Utopia buildings' looks as kits. Civic: brutalist concrete, shops under a deep canopy or a battered plinth at
  the ground, variants `galleries`, `ribbons` and `offices` (fins), heavy parapets, plant on the roof. Utopia: white
  stone with rounded corners, an arcade or a planted plinth at the ground, variants `terraces` (rounded slab edges with
  planters) and `bands` (white bands, fins and slats), roof gardens with skylights, trees, pergolas and pavilions.
- `frontier/frontier.json` (`bays`, `theme_kits.py`): the Frontier colony's prefab modules, one per hex's storey: blue-grey
  plating, every module edge bevelled in light steel (modules meet in V grooves at joints, between storeys and across
  the roof), chamfered steel corners, skids on the ground; variants `habitat` (numbered window modules, airlock),
  `medical` (teal stripe, MED airlock), `industrial` (louvres, pipes, a roll-up door) and `greenhouse` (dusty frontier glass over the biodome's planted bed);
  roofs with solar panels, radomes, HVAC units, hatches and beacons. Its `hangar` variant is a hall of strapped
  modules, those under its roof (`top`) with round-headed ports either side of the strap, under the modules' flat roofs
  or, vaulted, a lid of flat plating plates with steel hoops (`plates`), a module's bevel grown to a roof. Civic's and Utopia's `hangar`
  is a hall whose every storey lays the same bays, so its strips run from the ground to the storey under the roof
  (`top`), where they end in round arches: Civic's deep concrete fins every 6 from a battered foot, blank precast,
  louvres and dark glass between them, the fins joined in arches; Utopia's white stone round one tall opening a bay
  (white slats, glass between fins, a sunk panel) over a planted plinth. Under the look's flat roof or, vaulted, under a
  roof that spans it (a thin concrete shell; a white shell).
- `imperial/imperial.json` (`bays`, built with its pieces by `tools/buildings/imperial_kit.py`): the Imperial look. Warm
  stone cladding over a dark granite plinth, dark teal glass, red lacquer columns and portals, wall lanterns; every bay
  runs between half piers, and every storey ends in a stone course. Its convex corners are cut by one facet
  (`cornerRadius` 6): on the walls a stone pier with a slit of glass (a lantern on the ground), and on the roof the
  piece that runs the eave out and up to a tip. Its roof module is the eave: a charcoal standing-seam skirt flaring 6
  out past the walls to a bronze lip and rising to a bronze-capped curb 10 in (no farther than a wall's pieces go on
  past an inside corner, so two skirts meet there in a valley), round a deck of grey paving 3 over the roof's line (the
  slab's `inset` and height; a unit on the roof is drawn on the deck), so a roof of any outline reads as hipped with
  upturned corners. Variants `offices`, `tower` (glass from pier to pier),
  `habitat` (loggias between red columns), `commercial` (shopfronts), `medical`, `industrial`, `hangar` (a hall: lacquer columns and strips of glass, louvres and sunk panels up its whole height, every storey
  laying the same bays, the strips ending under a lacquer beam and a dark frieze in its `top` storey; under the look's
  eave or, vaulted, a charcoal seamed bow roof); `pavilion` (an arcade under glass between lacquer columns, a lacquer post on each
  corner) and `residence` (paper screens behind dark lattices) draw their roof corners out to swept-up points
  (`eave-point` in place of `eave-corner`). Roofs with a second tier of glass under its own hipped roof, fan units behind a pale
  louvred screen, glass monitors, stair pavilions, hatches and vents. Its panes differ one by one (dark teal, sky, a warm
  room); lit ones glow amber at night, and shopfronts glow faintly all day.
- `heritage/heritage.json` (`bays`, pieces from `tools/buildings/heritage_kit.py`): the Heritage look. Pale limestone
  ashlar over a channelled ground storey, brick with stone dressings on its works; bays of round-arched pairs, tall
  sashes, iron balconies, deep ground arcades (shops under awnings), blind arches, louvres, works windows of small panes
  and glass oriels in steel frames; the entrance under a columned porch. Three roofs: `mansard` (a stone cornice, a
  slate skirt 9 tall with dormers up to a copper curb round a deck of pavers half a level up; its run keeps the dormers
  off a wall's ends with `margin` 4 and plain `ends`), `parapet` (a coped wall round a flat roof) and `battlement`
  (that with merlons). A facet cuts each convex corner: a pier of quoins (`cornerRadius` 6) or, with `cornerRadius` 15, a
  round turret that stands out of both walls, storey on storey, and ends over the roof in a bell-cast copper cone
  (`mansard-turret`) or merlons of its own (`battlement-turret`); a turret stands only where the walls turn 75 degrees or
  more, a hex's own shallower corners taking the quoins (the runs' `shallow`). The turrets are drawn only: units stand on
  the deck, which they leave out. Variants `habitat` and `tower` (mansard, turrets), `offices`, `commercial` and `medical`
  (mansard, quoins), `industrial` (brick under a parapet), `hangar` (a brick hall: stone buttresses and strips of iron-framed windows, louvres and sunk brick panels up its whole
  height, the windows and panels ending in round arches in its `top` storey; under a parapet or, vaulted, a copper bow
  roof over a stone cornice), `armoury` (stone, battlement, turrets). Roofs
  carry two or three fittings a hex: chimney stacks, a copper cupola, skylights, fan units behind a louvred screen, duct
  runs, water tanks, ventilators, hatches.
- `standard/fortress-light.json` (`bays`): the light fortress, its storeys' stretches the art's wall rebuilt
  low-poly to its measurements (`tools/buildings/art/fortress_light_a_52.glb`: panel face, joints, band, window recess
  and frame, door, base course) in the dark wall concrete (`structures/buildings/fortress-wall`, the art's far facade's
  tone), plain masonry at each wall's ends, the art's merlons along the roof in the light concrete; far away one panel
  face per wall with its windows, and a plain parapet.

A `bays` variant: the Angled `lone` outline (counter-clockwise from its front) and `bandEnd`; its `floors` slab and
its roof's (a board material on the board's axes, its `repeat`, an `inset` off the walls, `heights` per level
of detail; a glass roof's `underlay`, the biodome's planted bed just under it; a roof's `aviationLights`, below; a
roof's `vault`, below); the ground storey's `sidewalk` (`width`, `kerb`; none without); and its storeys by role, each a
list of runs the game picks among by placement: `base` (the ground storey), `floor` (those above) and `top` (the storey
under the roof of a building two or more levels tall, where it lists any). A roof lists its own `runs`. A run's `far` is
the whole run its second level of detail lays (and any further); a run without one lays the same on every level.
A run lays whole `bay`s of its `bays` pieces (several: chosen by the wall's place)
stretched to fit between a `margin` at each end, along each whole side of the outline (the nearest count; with the
variant's `varyBays`, a bay fewer or more by the wall's place where both stretch between 0.7 and 1.5: civic, Imperial, the light
building and fortress, the placeholders; not Frontier or Utopia), a ground storey's `entrance` piece in a hub face's first bay and next to
the middle of a whole hex's front; with no margin a bay more goes on past an end where the wall goes on. Whole `ends`
stretches (`piece`, `length`) fill the margins, one `under` stretch lies along the whole wall, and `planar` materials
are textured along the wall's line (units a repeat). `cornerRadius` and `cornerSegments` round convex corners into
facets, each laid with the run's `round` stretch. A kit of modules (one per hex's storey) gives its wall runs `joints`
(`start` and `end` pieces, `length`): a wall ends its module, its joint piece there, where a linked hexside goes on past
it or its outline turns into a joint (Angled: each linked hexside; Square: a north or south link's hexside, and a
diagonal link's cell, a module of its own, along its column edges), and goes on along a joint that continues it; a
cap's wall leaves that room to the walls beside it. Its roof runs' `seam` stretch lies along each joint, the roof slab
kept its `inset` off it, and its roofs come closed above lower neighbours (`-closed-N`) rather than rimmed by caps.
Where a roof's edge closing one link ends at a hex corner against the hex across its other link, it goes on round that
inside corner (not a seamed, jointed or vaulted roof's): mitred with that hex's edge where the two roofs stand level,
eaves in a valley (`-valley`), or run on into that hex's wall where it stands taller (`-wall`).
A run's `shallow` names the piece a rounded corner takes in place of `round` where its walls turn less than 75 degrees.
A wall too short for one bay within its `margin`s is laid with its `ends` stretch alone.
A storey carries a sill (its `-sill`, a kit without joints) over each hex corner it turns only where it closes links,
drawn where the storey standing on it closes a link it keeps itself and rounds that corner, which would open the storey
to the roofs beside it. A run's `margin` keeps its bays that far off a wall's ends; whole `ends` stretches fill the
margins and the wall's going on past an inside corner (Utopia's, where a bay cut short would show through its recess).
Roof `fittings` are a list of layouts, one drawn per hex by its place: each names pieces of the pieces GLB and where
they stand on the roof (`{"chimney": [[x, y], [x, y, turn in degrees]]}`; `{}` a bare roof), and
each roof module comes once per layout. Where the two footprints lay differently, `fittings` holds a list for each
(`{"square": [...], "angled": [...]}`). A vaulted roof carries none. Bay kits without
fittings are turned: their Angled corner pieces are built once and turned by the runtime.
- `lunar_habitat/lunar_habitat.json`: the lunar habitat, a kit the game generates from this spec (`HabitatKit`, both
  footprints): facades, steel piers at corners and joints, a battered steel skirt, the roof's edge rounded down into
  the walls (variant `rounded`) or a parapet (`parapet`); convex corners rounded. A `habitat` variant's look is data: its
  `name`, board `materials` by role (`wall`, `roof`, `pier`, `concrete`),
  `cornerRadius` and `cornerSegments` (plan rounding), its roof (`parapet`: `height`, `width`; `eave`, the roof's
  rounded edge: `radius` and `segments` per level of detail; with a parapet it rounds the parapet's outer top edge,
  without one a rim curves from the wall onto the roof; neither: square; or a `vault`, below), `skirt`, the pieces at
  walls' joints and convex corners (`piers`, their roof `tops`, `footings`: a `joint` and a `corner` piece name each;
  none without), the Angled `lone` hex and single link band, the `storeys` above the ground (`windows` lit or dim,
  `shift` along) and the roofs' `fittings` per footprint (boxes on the Square roof, drums on the Angled). Its pieces stand in
  all six corners (not turned) because its roof fittings stand in the hex's middle; an Angled piece lays its plating
  along its building, mitred where arms meet (its linkless roof corners have `-bend` twins). The game reads a kit's
  JSON where no GLB of its name exists; the asset's `-square` names the Square footprint.
- `lunar_habitat/lunar_habitat-pieces.glb`: the habitat's pieces. A pier stands on its storey's floor at the wall line
  and is stretched to the storey (18 high); a pier top likewise on the roof, stretched to the parapet (or eave) and .6
  over it; a footing likewise on the ground, as modelled; a hatch or vent on the roof surface at its centre, as
  modelled.

- `standard/hangar-light.json`, `hangar-medium.json`, `hangar-heavy.json`, `hangar-hard.json` (`bays`, built with their pieces
  by `tools/buildings/hangar_kits.py`): halls, no storey showing rooms, each in two variants, which are its walls and
  doors. `default`: the designers' halls, their wall bays read from `tools/buildings/art/hangar_<weight>_a-proposal.glb`
  (bays between frames; the hardened one's ground frames battered buttresses) and dressed by the script in board
  materials, with kerbs, louvres, strip windows, side doors and a far level. `alternative`: a corrugated steel shed on
  portal frames with wind braces and daylight strips (light), insulated steel panels over a concrete plinth with a band
  and strip windows (medium), precast concrete between buttresses (heavy), a bunker with a battered ground storey and
  embrasures (hardened). Their walls take a building's tint. Each kit has two roofs, and either variant draws either
  (`shared` names both): `vault` (below), with frames running on over it as ribs, a low corrugated gable (light),
  bowstring roofs (medium, heavy), a concrete arch (hardened, a hardened aircraft shelter's); and `flat`, with the
  kit's roof fittings, a corrugated deck under an eave (light), a membrane roof under a fascia (medium), a dark roof
  under a parapet (heavy) or a burster slab (hardened).

A roof's `vault` (a habitat kit's in its roof material, in place of its flat roof, rim and pier tops) is a roof that spans its hall, as a hangar's does, in place of the flat slab: a hexside
wide, rising `rise` (half a level, 9, at the most) over the roof's height in the `shape` of a `gable`, a `bow` (a circle's segment, a bowstring roof),
an `arch` (half an ellipse, a barrel vault) or `plates` (a bow of flat plates, their edges hard), in `segments` facets a side per level of detail. It follows the hall. A
Square hex's runs north to south along its column: a column's hexes share one roof, and columns side by side meet in
level valleys, a hall of parallel bays. An Angled hex's runs out along each of its links: two links' roofs meet in a
valley, and round the hex's unlinked sides the roof turns in hipped facets, so it bends where the hall does and branches
at a tee. Where the hexes across two links are one building with it (three hexes round a corner, all linked, standing to
this roof's height), the corner keeps the crown's height in place of a valley (a roof corner piece's `-crown` twin,
`ConnectedKit.CROWN`): a cluster or a wide hall has one roof, vaulted along its edges and level inside. A lone hex's runs north to south. Every wall under the roof is filled up to it in the `gable` surface (a board
`material`, which may carry its pieces' finish as `...#paint` so it takes the building's tint with the walls, `repeat`,
a `tint`), a `verge` high band of the `trim` surface along its top; ribs of the trim surface cross the roof every
`ribPitch` along it (`ribWidth`, `ribHeight`), where a hall's wall bays meet; `tint` is the sheeting's. Such a kit's
pieces stand in all six corners (not turned). Doors in a gable end stand under the gable.

A kit variant's `vaulted` names its other roof among the kit's `roofs`, drawn for a hangar-class building unless its
author chooses the flat one (`building.appearance.roof` in a `.board2`, `vaulted` or `flat`; the board editor's Roof
choice, shown for the hangar class where the variant has both). Buildings of other classes keep the variant's `roof`.
Every look kit's `hangar` has one, and the lunar habitat's, and both variants of the light, medium, heavy and hardened
standard hangars: a variant and a roof are separate choices.

A unit on a generated kit's roof is drawn standing on the roof's own surface (the slab, plating or vault the generator
lays, its parts keyed `<material>#deck`), up to half a level over the roof's game height, where the unit plays. Parapets
and other roof run pieces, fittings and aviation lights never raise it: it stands among or through them. An authored
building's roof for a unit is its volumes' top, the game's height.

## Large doors

A building hex may have a large door on any hexside its building does not continue across, as a hangar has them
(`building.appearance.doors` in a `.board2`: a height in levels by direction, `{"n": 3, "se": 2}`, and
`building.appearance.doorLinks`: the link group of each linked door, `{"n": 1, "ne": 1}`; the board editor's building
designer and Hangar doors section, shown for the hangar class). A hangar-class building has no interior floors by default, and draws
its kit's variant of `class` `hangar` where the kit lists one (every look kit) unless the author chooses another. Only generated kits draw doors (`KitDoors`). Rules and the 2D views ignore them.

- A door stands in the footprint's wall towards its hexside: the longest straight stretch of wall within that sixth of
  the hex, with a remainder of the wall up to 12.5 beside it. Square footprints give long straight walls (a column's east
  wall is two doors a hex); an Angled hex's facets are 24 long.
- Linked doors (one group, so one height) side by side along a straight wall, in one hex or the next, are one wide
  door: jambs stand only at its ends, each hex's part is a leaf of its own. Doors that are not linked, and linked ones
  that meet at a bend of the wall, each keep their jambs.
- The hex's kit pieces are cut open over the door, from the ground to its top level's line less the `lintel`, through the
  wall's `depth` and 9 out of the wall line (canopies, planters, sidewalks), and the door is generated in the opening.
  Such a hex has a mesh of its own; when it falls, it falls in whole storeys.
- A kit variant's `largeDoor` is its look, every value optional (a plain steel door without): the `leaf` and `frame` surfaces
  (a board `material`, `repeat` units a repeat, a `tint`; `paint`: it takes the building's tint; `glow`: a linear
  colour it lights up in at night); the frame's `jamb` width, `header` height, how far it stands `out` of the wall line
  and its `depth` into the building; the leaf's `recess`; the `lintel`; the `margin` kept to a wall's corner; the leaf's
  `panel` height (grooves between) and the width of its vertical `section`s (joints in the `seam` surface); a `stripe`
  along its foot, `stripeHeight` high; `windows` (`glass`, `width`, `height`, `sill`, `pitch`: a row of panes in each
  leaf); a `threshold` plate reaching `apron` out; and `pieces` of the pieces GLB that stand in for the generated frame:
  a `jamb` (stretched to the opening's height, mirrored at the door's end), a `header` (laid across in stretches of
  `headerLength`) and a `crown` (on the header over each leaf's middle).
- `structures/common/sectional-door` (Material Maker, 256 px) is the shared leaf of sectional panels: four panels a
  repeat, one repeat over 12 units.

Aviation obstruction lights (`"aviationLights": true` in a bays kit's roof, in a habitat variant): every
modular kit's roofs but Utopia's; walls carry their own red lamps. They stand on hexes 7 levels high or more (about 40
m; `ConnectedKit.LIT_LEVELS`), each roof twin's lights a node of their own (`<twin>-aol`) beside it. A light stands on
each outer (convex) corner of a roof, never an inside one: 2.5 in from both walls, at a rounded corner's middle, and on an Angled roof's outer elbow
where a bend's corner pieces meet. Such roofs close above lower neighbours as twins (`-closed-N`), so those corners are
lit too. The light is `fittings/aviation-light.glb` (`python tools/buildings/aviation_light.py`, standard library
only): a 20-triangle steel stick from 5 under the deck, buried where an edge curves or bevels away, to a square red
lamp 6 over it, whose emission blinks (material extras `mmEmission: blink`, 1.5 s, half on).

Isolated generated kits use a compact square for Square and an inset hex for Angled, with facade details and curbs
contained inside the hex. Optional editor padding shrinks isolated buildings horizontally; connected pieces retain
their full joining reach. Bay and habitat kits share solid inward wall backing, closed exposed wall ends and roof
slabs. Bay specs may supply `wallInsets` per LOD when their facade skins sit behind the nominal wall line (default 0). Generated interior floors are solid slabs below their gameplay standing height, including authored multi-hex
buildings. No-floors and sealed buildings omit intermediate floor surfaces from drawing and picking.

Every surface is a board material (`structures/buildings/`, `structures/lunar/`, Material Maker projects in
`tools/materials/structures/`): the hand-made art's atlases as image projects, the roofs, floors and sidewalks
tileable on the board's axes (the kit JSON's `repeat`). The fuel tanks are generated:
`python tools/buildings/fuel_tanks.py [weight ...]`, after the designer's kits (sizes, paint, roof rings). Each kit is
authored stacked as built (floor at 18, roof at 36) with no coincident surfaces between its pieces. At full detail
the base carries a nozzle in all six directions; a `link-n` pipe runs from the north one to the edge, and an `end-n`
blind flange closes it where no pipe leaves. Painted pieces take the board's `weathered-paint`, the hard tank's
vents `vent-slots`, both tinted by vertex colour, and steel `rusted-steel`, by image URI; vertex colours also carry
contact shading and grime. Three levels of detail follow the props' rule (above 80 pixels on screen, down to 24,
below).

## Multi-hex buildings

The `buildings/multihex/dome` and `biodome` looks are generated over a whole building (`BoardMultiHexBuilding`), with
no model per hex: a dome is fitted into its footprint and cut along the hexsides, and a domed building's hexes outside
its podiums stand as rectangular blocks at their own heights, joined to the podium by wings. The lunar habitat look is
the connected kit generated from `lunar_habitat/lunar_habitat.json` (above). Their surfaces are board materials in `structures/lunar/` (Material Maker
projects in `tools/materials/structures/lunar/`); the dome glass is transparent by its `.tres`.

`multihex/lunar-equipment.glb` holds their support pieces, one node per piece and level (`<piece>-lod0`, `<piece>-lod1`),
each standing on its origin, its front towards +Y: `tanks`, `plant`, `airlock` (its back on y = 0, against a facade)
and `pylon` (a dome podium's corner block). It is modelled in Blender:
`blender -b --factory-startup --python tools/buildings/lunar_equipment.py`. The same script writes board objects, one
file each: roof props in `board/scenery/roofs/` (`radar-dish`, `capsule-tanks`, `generator-ring`, `generator-slit`, `twin-pipes`, `edge-spike`, `radar-station`,
`light-well`, `light-strip`, `solar-array`, `dish-antenna`, `sawtooth-skylight`), the editor's Buildings > Rooftop
section, and colony details in `board/scenery/colony/` (`pipe-run`, `vent-unit`, `wall-tanks`, `ladder-cage`,
`light-mast`, `airlock`, `radiator`, `vehicle-gate`; wall-mounted ones with their back on y = 0), the editor's
Buildings > Colony section. The 32x17 Lunar Base stands them
against its habitats' walls and on their roofs to break the blocks' outlines.

The four heavy-industrial terrain uses `BoardIndustrial` procedural generator. It assembles
different equipment families with independently chosen heights, distinct domed/conical/flat caps, and pipes
connected to actual neighboring industrial hexes. Industrial height is cover: there are no generated interior
floors, building cutaways, or elevated pointer selections. Ordinary buildings still use the modular contract above.

The active industrial materials are `models/board/textures/structures/industrial/paint.tres` and `steel.tres`
(Godot 4 Standard materials; a wider export widens their repeat). The shared `fan` material is an opaque 128x128
texture on a static quad, with mipmaps and no animation.
`tools/buildings/heavy-industrial/` preserves the first prototypes but are superseded by the runtime generator.
