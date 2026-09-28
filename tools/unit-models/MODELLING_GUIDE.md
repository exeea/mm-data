# Unit model authoring guide

This guide is for anyone building a 3D unit model for MegaMek: a named Mek such as the Atlas, a named vehicle
such as the Manticore, or one of the generic family bodies the game falls back to. Every unit follows the same
rules for file format, coordinates, materials, joints, weapon mounting and triangle budget.

Related documents in this folder:

- [NEW_CHASSIS_BRIEF.md](NEW_CHASSIS_BRIEF.md) walks through adding one new Mek chassis step by step.
- [UNIT_REVIEW_PROCESS.md](UNIT_REVIEW_PROCESS.md) describes the review loop, the review sheet and how weapon
  sockets are placed.
- [PRE_BUILD_CHECKLIST.md](PRE_BUILD_CHECKLIST.md) lists what to gather and ask before building a Mek.
- [MODULAR_MODELS_PLAN.md](MODULAR_MODELS_PLAN.md) is the design record for the runtime assembly.

When this guide and the code disagree, the code wins; please fix the guide.

## 1. How a unit model is made

The game never loads a finished "Atlas AS7-D with its weapons". It loads a bare Atlas body, then fits the
weapons the unit actually carries onto that body while the game runs. So a modeller authors two things: a bare
body with named attachment points, and (only when the look is new) a reusable weapon or equipment piece.

1. **Identify the real unit.** Note the chassis, a reference variant, the movement type and the weight class from
   the unit file. Gameplay data decides the equipment, troop counts and conversions; the model never does.
2. **Gather references.** Use the north-facing game sprite for the top silhouette and weapon positions, plus a
   clear miniature or line-art image for depth and joints. Separate fixed body features from optional
   equipment. Settle big silhouette and proportion questions before adding detail. Record what you shaped the
   body from in the recipe's `silhouette` note (see the existing entries in `chassis.json`).
3. **Write the bare body and its recipe.** A Mek is a builder function in `tools/unit_mek_chassis.py` plus an
   entry in `tools/unit-models/chassis.json`. A named vehicle is a builder in `tools/unit_vehicle_chassis.py`
   plus an entry in `tools/unit-models/vehicles.json`. Generic family bodies live in
   `tools/unit_family_models.py`. Split moving parts and damage locations while you build. Never bake a loadout,
   a casualty count, a terrain-specific leg length or a preassembled troop group.
4. **Export.** `python tools/build_modular_unit_models.py` runs in plain Python and writes one `.glb` per
   component with its `.json` descriptor. Blender is optional, for inspection only. Nothing in Python or
   Blender runs when a map loads; MegaMek's Java code assembles the unit, and the same code draws the game and
   the review images.
5. **Review.** Compare bare and assembled silhouettes from front, back, side and top, a same-family size lineup,
   and real animation on terrain. Check weapon clearance, damage, camouflage and both cameras.
6. **Register and stage.** Point the chassis at its descriptor in `data/images/units/mekset.txt`, then stage the
   data into MegaMek (section 12).

### Work on related chassis together

Prefer a missing chassis with many variants, because one bare body serves every loadout. Before you start,
search the unit files and `mekset.txt` for related chassis names, including numbered successors, IIC and LAM
designs, and author those relatives in the same batch. They may share builder helpers, but each chassis gets its
own body file and its own mekset line. The Phoenix Hawk and Phoenix Hawk IIC are separate bodies; so are the
Thunderbolt and Thunderbolt IIC. Never pick relatives by fuzzy name matching, and never treat a relative as a
reskin without checking its weight, proportions and topology.

A numbered model such as King Crab KGC-001 is usually just a loadout variant of the chassis and uses the chassis
body. A variant that genuinely needs its own spot for a weapon gets a `variants` entry in the chassis recipe
(the Thunderbolt TDR-60-RLA is an example); the build then writes a variant body that draws the chassis's mesh
with its own hardpoints.

### Who owns what

Python authors shape only. On the MegaMek side, `MekTileset` picks a model for a unit, `UnitModelState` captures
what is visible on the unit, `GpuUnitModels` and the family assemblers share mesh buffers, and each displayed
instance owns its pose and materials. `UnitAnimator` and `UnitPlayback` run one timeline for both cameras. Do not
add a second loadout resolver, animation clock or copy of game state to an authoring tool.

## 2. Files and format

- **Every component is one `.glb` file beside its `.json` descriptor.** That covers Mek bodies, vehicle bodies,
  troops, transports and every weapon or equipment piece. G3DJ is gone: MegaMek no longer reads it and the
  exporter no longer writes it.
- **Levels of detail live inside that one file** as top-level groups named after the file: `atlas.glb` holds a
  group `atlas-lod0`, and `phoenix-hawk.glb` holds `phoenix-hawk-lod0` and `phoenix-hawk-lod1`. Each group is an
  empty node with an identity transform; the rig hangs beneath it. `-lod0` is required. MegaMek refuses a unit
  GLB whose levels are not named this way, with the message "Name the levels of X as groups X-lod0 ...", and
  also refuses unknown or duplicate group names, a group with a transform, skins, animations and external
  buffers (`RigidGlb.loadLods`).
- **Descriptors are schema 2.** A descriptor names its mesh relative to itself, and the mesh must end in `.glb`.
  Kinds are `body`, `equipment`, `troop`, `family`, `formation`, and the Mek descriptors under `meks/`. Paths must
  stay inside the model folder. You rarely write these by hand; the exporter does.
- **Where the output goes.** The default output is `data/models/units/modular/`: `bodies/`, `meks/`,
  `families/`, `troops/`, `transports/`, `battle-armor/`, `equipment/`, plus `equipment.json` and `manifest.json`.
  The manifest records, per component, the triangle and vertex counts, a checksum and a `lods` list with each
  level's group name and triangle count. It is the place to check what a build actually produced.
- The board scatter kit (`scatter.glb`) follows a different rule: it holds many shapes in one file, each named
  `<shape>-lodN`. That is correct for scatter and does not apply to units.

## 3. Levels of detail

MegaMek chooses a level by how tall the unit is on screen, so a Mek seen across the map costs far less to draw
than one filling the view.

| Unit | LOD0 (full detail) | LOD1 | LOD2 |
|---|---|---|---|
| Meks, vehicles and other units | taller than 96 px | 32 to 96 px | shorter than 32 px |
| Infantry and battle armour (one figure measured) | taller than 48 px | 16 to 48 px | shorter than 16 px |

What each level is for:

- **LOD0** is the model as designed: panel lines, vents, weapon detail. Every component has it.
- **LOD1** keeps the silhouette and the joints but drops the detail that no longer reads at a hand's width on
  screen, roughly halving the count. The Phoenix Hawk's LOD0 is 1,824 triangles and its LOD1 is 954.
- **LOD2** is a blocky stand-in for a unit that is a few dozen pixels tall. Suggested sizes: a Mek 150 to 250
  triangles, a weapon 10 to 30, a battle armour suit 40 to 60, an infantry figure 20 to 40.

LOD1 and LOD2 are optional. A missing level uses the next more detailed one, so a body with only LOD0 simply
draws LOD0 at every distance. Level switches use a small margin so a unit sitting on a boundary does not flicker.

Current state: MegaMek switches between LOD0 and LOD1 today (`FormationLod`). LOD2 for units is still being
added by the renderer author; you can already author a `-lod2` group, but do not expect to see it in the game
yet. Separately, a fitted weapon smaller than about 4 pixels on screen is hidden (`GpuUnitInstance`), whatever
level the body is at.

### Giving a Mek a LOD1 body

Set `"bodyLod1": true` in the chassis recipe and teach the builder a `far=True` mode that draws the simpler shape.
The Phoenix Hawk and Phoenix Hawk IIC do this today. The build exports the simpler shape as `bodies/<id>-lod1`,
holds it to the LOD1 budget, and packs it into `bodies/<id>.glb` as the `-lod1` group. Two rules apply:

- The LOD1 body must have every node the LOD0 body's rig names (pelvis, CT, arms, shins, feet and so on). The
  build stops with "the far body lacks nodes the near body has" if one is missing.
- The LOD1 body carries no weapon spots, vents or jump jet spots of its own. Weapons stay on the LOD0 body's
  sockets, which is why the node names must match.

Battle armour suits can have a LOD1 figure too: the Elemental and Elemental II suits are exported with a
`-standing-lod1` figure packed into the same GLB.

## 4. Triangle budgets

The budget covers the **whole assembled unit at each level**: the bare body plus every weapon fitted to it.

| Level | Whole-unit budget |
|---|---:|
| LOD0 | 5,000 |
| LOD1 | 2,000 |
| LOD2 | 500 |

These numbers are `LOD_TRIANGLE_BUDGETS` in `tools/unit_model_geometry.py` and `UNIT_TRIANGLE_BUDGETS` in
MegaMek's `UnitModelDescriptor`. In practice:

- **Bodies.** The exporter refuses a bare body over its level's whole budget: a LOD0 body over 5,000 triangles, or
  a `-lod1` body over 2,000, fails the build. Aim for a LOD0 body under about 4,000, so roughly 1,000 is left for
  weapons. For scale, the Atlas body is 767 triangles and the King Crab 1,496.
- **Weapons and equipment.** One piece over 250 triangles prints a "Weapon review:" line during the build; one
  over 1,000 fails it (`EQUIPMENT_TRIANGLE_TARGET` and `EQUIPMENT_TRIANGLE_LIMIT` in
  `tools/build_modular_unit_models.py`). Heavy pieces are allowed, but they eat the unit's budget, so make them a
  deliberate choice.
- **In the game.** A unit whose real loadout goes over its level's budget is still drawn in full. MegaMek writes a
  warning tagged `[UnitBudget]` to megamek.log naming the unit, the level, the body count and the fitted pieces
  (`UnitEquipmentAssembly.warnOverUnitBudget`). Search the log for that tag after a test game. Formations and
  squadrons are not covered by this warning.
- **Hard limits.** MegaMek's own ceiling of 1,000,000 triangles per asset is only a sanity check. The real
  technical limit is 65,535 vertices in one mesh (16-bit indices), about 21,000 flat-shaded triangles.

Report body, equipment and assembled totals separately when you hand a model in.

## 5. Coordinates, scale and proportions

**Axes.** Author with +x right, +y forward, +z up, in one model unit on every axis. The GLB itself is glTF Y-up;
the writer converts. The ground or sole of a land body is z = 0; naval bodies keep their authored waterline.
Pivots, sockets, emitters and support data move with the vertices. The exporter calls
`Geometry.export(..., z_scale=1, paint_uv=True)`; do not reintroduce the old divide-by-54 height scaling.

**Sprite coordinates.** Mek recipes place points in sprite pixels. `[pixelX, pixelY, height]` becomes
`[pixelX - 42, 36 - pixelY, height]` in model space (`build_chassis`). Exported hardpoints and emitters are local
to their parent's rest pivot; the helpers convert them for you, so do not subtract the pivot twice.

### Mek weight classes are authored, not scaled

Every Mek body carries its own size. There is no runtime enlargement by weight. The fallback bodies exist in five
classes (light, medium, heavy, assault, superheavy) for biped, tripod and quad layouts, plus the hybrid air-Mek.
A QuadVee uses its quad body in both modes. MegaMek picks the class from the unit's weight class, and the mekset
paths use a `{weightClass}` token, for example `units/modular/meks/fallback-tripod-{weightClass}.json`. Do not
repeat tonnage cutoffs in Python.

| Class | Proportion brief | Starting bare-body height, model units |
|---|---|---:|
| Light | Narrow chest and hips, thin limbs, compact shoulders; long scout legs are fine | 46 to 54 |
| Medium | Balanced torso and legs; visibly more volume than a light | 50 to 57 |
| Heavy | Broad chest and substantial limbs | 53 to 62 |
| Assault | Deep armour masses, thick thighs, broad planted feet | 55 to 66 |
| Superheavy | Clearly larger hull, supports and feet than a 100-ton assault | 68 to 84 |

These are review starting points, not rules. A tall thin Locust can be as tall as a hunched heavy; it must still
read as much lighter through width, depth and armour volume. Weapons and antennas must not be used to make a body
look heavier; review with equipment hidden as well as attached. The current biped fallbacks stand about 47, 52,
54, 56 and 70 units tall, light to superheavy (from the manifest); their proportions are `FALLBACK_PROPORTIONS`
in `tools/unit_mek_models.py`. After changing a fallback recipe, rebuild every layout and compare the whole
five-class lineup. Moving a hull's cockpit or armour plates means moving its hardpoints and searchlight socket
too.

Reference weights from the unit files: Locust LCT-1V is 20 tons (light); Warhammer WHM-6R and Archer ARC-2R are
70 tons (heavy); Marauder MAD-3R is 75 tons (heavy); Atlas AS7-D and King Crab KGC-000 are 100 tons (assault).

### Board scale

Author and compare with every family scale at 1.0. The board's scale sliders are fine-tuning, not a fix for a
body with the wrong proportions. At unit scale 1 the Atlas's bare standing height of about 54.9 model units spans
two terrain levels (`GpuUnitModel`), and every other single-hex body is drawn with that same conversion, so
relative sizes are preserved. Do not normalise each body to two levels. Multi-hex units are fitted to their
footprint; the multi-hex unit scale defaults to 1.0. Movement and size both use
`GpuUnitModel.horizontalScale()` and `verticalScale()`; do not recreate those formulas in a family class.

Non-Mek fallback families use a small size table in `FamilyVisual` for their game size. Do not apply it again in
the generator.

**Infantry** is authored at real size in the same units (`MODEL_UNITS_PER_METRE`): a standing soldier is 1.8 m
(`TROOP_SCALE`) and battle armour is 1.5 times that, 2.7 m (`BATTLE_ARMOR_SIZE`). Scale a figure evenly, never
by height alone. On the board MegaMek draws infantry at 2.0 and battle armour at 1.8 by default
(`UnitFamilyScale`) so they read at play distance, and draws infantry transports at twice their authored size
(`InfantryVisual`); do not copy either factor into the vertices. ProtoMeks are authored 6 m tall and drawn at
1.3 by default.

## 6. Materials and surfaces

- Colour with the shared `PALETTE` in `tools/unit_model_geometry.py`. The exporter sorts every face into one of
  three material roles: `paint` and `edge` colours become the **paint** role, which camouflage tints; `bark` is
  the **bark** role, used by tree-like shapes; everything else (metal, glass, weapon tips, skin, lamp) becomes the
  **detail** role, which keeps its authored colour. More roles can be requested from the renderer author. PBR
  materials are not implemented.
- Colours are authored in display space and stored linear by the writer.
- Keep the weapon-tip colours: red laser, blue PPC, green TAG, orange plasma. Cockpits use glass.
- Paint UVs and damage projection stay in rest space so markings do not crawl as the unit moves. Damage overlays
  blend over the opaque surface; never make a mesh transparent to fake scratches.
- Use flat-shaded broad shapes, consistent winding and valid normals. No degenerate faces, duplicate surfaces,
  hidden ornamental shells or extra materials. Cap any cut surface that a removable part exposes.

## 7. Joints, rigs and anatomy

Every independently moving part has a stable node, a rest pivot at its physical joint (not its bounding-box
centre) and a parent. Reuse the family's existing rig roles. Child geometry and equipment follow the same joint,
including while damaged or hidden. Instances never change a shared source mesh.

### Mek damage locations must be real regions

Every Mek, fallbacks included, must be physically split into drawable `HD`, `CT`, `LT` and `RT` regions plus its
arms and legs, even when the reference shows one continuous carapace. The seam can be invisible, but the
triangles must belong to separate location nodes, because damage is drawn per location. Empty nodes, token
triangles or colour changes do not count. Every visible surface needs the right owner.

Example: on the King Crab, `HD` is the whole visor band with its glass and framing. The roof behind it is split
into centre, left and right torso shells. Losing HD removes the visor without taking the torsos, and damage to one
torso does not stain the others. The helper `split_torso_locations()` can split an old joined shell, but new
builders should label regions explicitly. Before accepting a Mek, look at a colour-coded ownership render and
damage HD, CT, LT and RT one at a time, then remove HD alone.

- The chain is root, pelvis, then CT at the waist. Head, side torsos and shoulders follow CT; hips and legs follow
  the pelvis. Keep the upper and lower body cleanly separated through a 60-degree torso twist either way.
- Legs: bipeds use `LL` and `RL`, tripods add `CL`, quads use `FLL`, `FRL`, `RLL`, `RRL`. Each needs hip, shin
  and foot controls, and the feet must carry the model while the knees bend.
- Arms run shoulder to forearm, with optional `LA@hand`, `LA@wrist`, `LA@forearm` and `LA@elbow` (and the RA
  equivalents). The unit's actual actuators decide which parts show. A missing arm must not leave floating
  weapons.
- A detachable head or limb needs a capped cut. A destroyed side torso takes its arm with it.

### Leg bends

Author each leg as hip, knee, then ankle and foot, with pivots at the real joints and the sole at z = 0. A reverse
knee sits behind the hip-to-ankle line. If a chassis has reverse knees, say so in the recipe; the exporter copies
it into the body descriptor:

```json
"legBends": {"leftLeg": "reverse", "rightLeg": "reverse"}
```

Keys are rig roles, not node names: `leftLeg`, `rightLeg`, `CL` for bipeds and tripods; `FLL`, `FRL`, `RLL`,
`RRL` for quads. Legs without an entry bend forward. A reverse-knee rest shape alone is not enough: without
`legBends` the animator bends it forward as soon as it walks. The Locust and King Crab both declare reverse legs.
Never infer the bend from the chassis name or weight.

## 8. Family bodies

All sizes below come from the current manifest, in model units. Board fitting from section 5 still applies.

| Family | Source | What to get right |
|---|---|---|
| Biped Mek | `unit_mek_chassis.py` builders, `chassis.json` recipes, exported by `unit_mek_models.py` | Recognisable head, chest and limbs; waist, shoulder, elbow, hip, knee and foot controls. |
| Tripod Mek | `fallback_body('tripod')` in `unit_mek_models.py` | Three stable legs; the centre leg is separate and never kicks. Five weight classes. |
| Quad and QuadVee | `fallback_body('quad')` | Four articulated legs and a broad stance. A QuadVee folds its legs flat and keeps the same mesh. |
| LandAirMek | `air_mek_body()` | Hybrid with cockpit, wings, arms, reverse-knee legs and exhaust. Converts by rig joints; no baked fighter weapons. |
| Named vehicle | `unit_vehicle_chassis.py` builders, `vehicles.json` recipes, exported by `unit_vehicle_models.py` | Hull, drives and turret. Manticore: body 946 triangles, about 40 x 52 x 24. |
| Generic ground vehicle | `vehicle()` in `unit_family_models.py` | Tracked, wheeled, hover, WiGE and rail silhouettes. Turretless vehicles get no turret. |
| Conventional infantry | `person()` in `unit_infantry_shapes.py` | Standing soldier about 2.7 x 2.1 x 6.5 (1.8 m). Jump troops carry a small backpack with a jet emitter. |
| Battle armour | `person(armored=True)`, plus named suits such as `elemental()` | About 5.5 x 5.8 x 9.7 (2.7 m). Six living suits show six figures. |
| Infantry transports | `infantry_vehicle()` | Motorised, tracked, wheeled, hover; separate hull, wheel, boarding and cabin nodes. |
| VTOL and airship | `rotorcraft()` | Cockpit, tail, rotor and skids. An airship is its own elongated hull, not a big VTOL. |
| Fighter and aerodyne | `aircraft()` | Narrow nose, clear wings, engines. Landable aerodynes get landing supports (section 11). |
| Spheroid and small craft | `spheroid()` | Rounded faceted hull and separate supports. |
| JumpShip, WarShip, station | `capital()` | Long ship or radial station; no invented landing gear for space-only craft. |
| Naval, hydrofoil, submarine | `naval()` | Long hull and authored waterline; subtype foils or tower. |
| ProtoMek | `proto()`, quad and glider forms | Small articulated machine, 6 m tall; `proto-v1` joint roles, no Mek torso twist. |
| Emplacement, building, pod, missile | `static_body()` | Distinct static bodies with useful facing and ports. |
| Fighter squadron | `flight_fighter()` plus a squadron descriptor | One reusable 96-triangle member; the runtime lays out the squadron. |

For infantry, author members only. MegaMek compresses the head count into display slots; transports take one slot
when there are at most four, otherwise two. Troops board before a vehicle moves and unload after it stops. Their
final spacing and headings are decided at runtime, and members never shrink to fit a hex.

## 9. Hardpoints and Mek recipe fields

Every location that can carry a weapon needs a front and a rear mounting spot. Biped recipes cover
`HD CT LT RT LA RA LL RL`; tripods and quads use their own leg tags. Rear ports must actually clear the rear armour;
check the rear view. Java packs the weapons into each spot while the game runs; Python only says where the spots
are and how much room they have.

| Recipe field | What it does |
|---|---|
| `hip` | Waist reference in sprite coordinates; keep it on the centre line. |
| `sockets`, `rearSockets` | Front and rear spot for each location. Author rear spots wherever the default offset would bury a barrel. |
| `mountAreas` | Width and height available at each location for packing weapons. |
| `armSockets` | Hand, wrist and elbow spots matching the optional arm actuators. |
| `heldWeapons` | Arms whose gun is held in the hand; the build adds a housing that replaces the hand while the arm holds a gun. |
| `socketBanks` | Positions for one weapon family, including actuator keys such as `LA@wrist:ppc`. |
| `socketAim` | A replacement +y-forward direction by location or `LOC:family`; an arm gun follows its forearm. |
| `socketNodes` | Parent override by `LOC:family`, for example `"LL:jump-jet": "LL-shin"`. |
| `stackRows`, `rowWidth`, `stackGap` | Put weapons sharing a spot side by side, set how wide a row runs, and set the gap (negative nests rounded weapons; the Blackjack OmniMech uses -.5). |
| `weaponScale`, `missileScale`, `barrelLength`, `protrusion`, `lightProtrusion` | Fitting preferences. `lightProtrusion` applies only to small and medium lasers, so the Blackjack draws long large lasers and short medium ones from one spot. |
| `weaponOverrides` | Location, family and length adjustments. |
| `missileSockets`, `missileBayHeight`, `missileBayWidth`, `missileBayColumns`, `missileSlope` | Launcher placement and bay shape. |
| `missileStyle`, `missileBayStand` | Box or round drum launchers; stand the bay's launchers on the spot. |
| `exhaustSockets`, `jumpJetScale` | Jump jet positions by location, and a smaller jet size. Without an entry a leg's jet sits on the back of the calf. One jet graphic per location shows that it has jets, not how many. |
| `legBends` | Reverse knees, see section 7. |
| `searchlightSocket` | Where a lamp goes if the unit carries one. A socket never proves the unit has a lamp. |
| `ventSpares`, `ventDefaultSides` | Heat sink vents: spare vent count, and which faces keep vents on a variant without torso heat sinks. |
| `variants` | Per-variant overrides of any of the above, keyed by model, such as `"TDR-60-RLA"`. |
| `bodyLod1` | This chassis has a LOD1 body (section 3). |

Other fields (`bodyScale`, `locationScale`, `sharedFaces`, `slotSpacing`, `equipmentRules`) are read in
`build_meks` in `tools/unit_mek_models.py`; check the code and an existing recipe before using them.

Named vehicles use the generic vehicle hardpoints, placed from the body's size, plus their own recipe keys:
`turretSocket`, `turretSockets` per weapon family, `turretSocketScale`, `turretSocketStyle`,
`turretSocketLength`, `turretSocketProfile`, `turretRules` for named weapons, and `hullSockets` with
`stackRows`. The Manticore entry in `vehicles.json` uses all of them; the docstring of `hardpoints_and_mounts` in
`tools/unit_vehicle_models.py` explains each.

## 10. Weapons and equipment

`weapons.json` and `tools/unit_weapon_shapes.py` own the reusable weapon looks. Lasers have thin square barrels,
PPCs heavier emitters, and ballistic, rotary and gauss weapons must look different from each other. A physical
weapon's contact point is its striking edge, not its grip. Prefer a clear silhouette to surface detail.

What gets a model is one shared policy. Structure, armour and ammunition never get one. A weapon needs its own
visual or a family fallback. A physical weapon (`F_PHYSICAL_WEAPON`) needs a physical module. Optional
equipment such as ECM or a searchlight needs an explicit mapping and has no generic fallback. Grouped logical
weapons are not extra hardware.

To give new equipment a look, register it in the game's equipment system, refresh the catalog (section 12) and add
either a broad shape recipe or a mapping by internal name in `weapons.json`:

```json
{"models": {"ExampleWeaponInternalID": {"model": "units/modular/equipment/custom/example.json", "bankFamily": "laser"}}}
```

An explicit mapping beats the broad recipe, and mandatory exclusions beat both. Never edit the generated
`equipment.json` by hand. Keep each piece inside the equipment budget in section 4. When a rebuild stops using a
generated equipment file, the build moves it to `tools/unit-models/references/equipment-library/` rather than
deleting it.

## 11. Animation, effects and damage

**Animation.** Use the family's rig roles and the one runtime timeline. Leave enough joint clearance for walking,
running, jumping, idling, shooting, dying and the family's real conversion. A Mek punch or kick walks into reach,
plants, strikes, recovers and walks back. Review walk and run from the front and side, including backwards and
sideways movement, and check the planted foot does not slide and the knee never flips across the hip-to-ankle
line. Forced falls use the engine's fall side inside the occupied hex; never bake one fall direction into a body.

**Firing exits.** Each exit is an emitter with a node, a local position, a direction, a role and an effect such
as `laser`, `ppc`, `bullet`, `missile`, `cluster` or `flame`. Flame exits sit at the nozzle. Emitter count is not
ammunition count. Smoke, arcs, misses and laser rays are runtime effects, never baked geometry. Jump packs need
exhaust emitters.

**Damage.** Damage artwork is 128 x 128 RGBA in `data/models/units/textures/`. Meks show worn armour at half
armour loss, stripped armour at full loss, battered structure at half structure loss, then the destroyed-location
texture; other families show four stages at 25, 50, 75 and 100 percent combined loss (`UnitDamageDisplay`).
Intact paint shows through the holes. Infantry and battle armour get no overlays; their figure count shows damage.

### Landing supports for multi-hex aerospace units

Landable multi-hex aerospace bodies (spheroid DropShips, aerodynes) get legs that deploy when the unit is at
elevation 0 and disappear in flight. Space-only craft and buildings do not get them. The generic spheroid and small
spheroid have four supports (468 triangles each body) and the aerodyne three (312 triangles). The runtime rules
are in [MODULAR_MODELS_PLAN.md](MODULAR_MODELS_PLAN.md), under the landed multi-hex Aero supports addendum.

Build supports with `landing_support()` in `tools/unit_family_models.py`, which writes a compatible entry in the
body's `landingSupports` list:

- Each support has an `id`, a deployment `node`, a `shaft` and a `foot`, a `length`, a `contact` point local to the
  foot (usually `[0, 0, -halfFootThickness]`) and a `stowedOffset` that moves the deployment node into the hull.
- The shaft and foot are separate childless children of the deployment node. The shaft's pivot is at its top and
  its length runs down local -z; the foot's pivot is exactly `length` below. The shaft stretches only along z to
  reach uneven ground, and the foot moves down without changing size.
- `stowedOffset` must hide all support geometry, pad corners and braces included, inside the opaque hull.
- Supports count in the body's triangle budget. Never export a mesh per terrain height.

Review a new body on flat ground, on mixed-level ground under different feet, rotated, in flight, and through
takeoff and landing, in both cameras, including picking and shadows.

## 12. Build, stage and review

Sources and the exporter live in mm-data; the game code lives in the megamek checkout. Run each command from the
repository noted beside it.

```powershell
# megamek: refresh the equipment catalog the exporter reads. It writes
# <mm-data>/.work/modular-models/equipment.json; without the property it writes into ../mm-data.
.\gradlew.bat :megamek:exportEquipmentModelCatalog -PunitModelDataRoot=<mm-data folder>

# mm-data: build a candidate into a scratch folder first.
python tools/build_modular_unit_models.py --output .work/model-review/units/modular

# mm-data: after inspecting the candidate, rebuild the deployed library (default output data/models/units/modular).
python tools/build_modular_unit_models.py

# megamek: copy mm-data into the game data folder.
.\gradlew.bat :megamek:stageDataFiles
```

One build exports the Meks from `chassis.json`, the generic families, the named vehicles from `vehicles.json`,
troops, battle armour, transports and every equipment module. It then packs each component's levels into one GLB
and writes `manifest.json`. Watch the output for "Weapon review:" lines and for a body over budget, which stops
the build. `--catalog <file>` points at a catalog somewhere other than the default.

Staging copies from the `mm-data` folder next to the megamek checkout. In a worktree that folder is a junction to
the main mm-data checkout, which may be on a different branch; either run from matching checkouts, or stage and
then copy your built models over.

Tests in megamek that cover the models: `UnitModelDescriptorTest`, `RigidGlbTest`, `UnitEquipmentAssemblyTest`,
`UnitEquipmentModelsTest` and `UnitModelSelectionTest` in the normal test run, and
`GpuModularUnitModelsSmokeTest` and `GpuUnitModelBenchmarkSmokeTest` under the `gpuBoardSmoke` task, which needs
a real desktop graphics context. `GpuModularUnitModelsSmokeTest` calls `GpuMekAssemblyReview`, which assembles
real units with the game's own code and renders them.

Review tools in mm-data:

- `tools/render_modular_body.py` renders labelled Blender review sheets of deployed bare bodies, for example
  `blender --background --factory-startup --python-exit-code 1 --python tools/render_modular_body.py -- --body locust --body atlas --turn 60`.
- `tools/build_unit_review_gallery.py --frames <folder> --output <folder>` packages the review frames the GPU
  review tests write (by default under `build/gpu-board-review` in the megamek project).
- `tools/render_fallback_catalog.py` draws Blender contact sheets of the deployed generic bodies.
- The BattleTech Unit Viewer can build and review a single chassis with this same exporter, including its LOD1.

Retired: `build_unit_models.ps1`, `build_unit_models.py`, `render_unit_variants.py` and `validate_unit_models.py`
served the old baked model format and were removed on 2026-09-28.

### Registering a model

Add or change the chassis line in `data/images/units/mekset.txt`:

```text
chassis "Phoenix Hawk" "meks/PhoenixHawk.png" "units/modular/meks/phoenix-hawk.json"
chassis "Manticore Heavy Tank" "vehicles/Manticore.png" "units/modular/families/manticore.json"
```

Meks point at `meks/<id>.json`; vehicles and other families point at `families/<id>.json`. The loadout always
comes from the live unit, so one line covers every variant.

## 13. Acceptance checklist

- [ ] Reference sprite and a useful front or side image, with a short silhouette note in the recipe.
- [ ] Bare body, recipe, descriptor and manifest agree; no loadouts or troop groups baked into data.
- [ ] Same-family lineup at scale 1.0 shows the right weight and size; nothing is scaled twice.
- [ ] Body, equipment and assembled triangle counts reported for each level; the whole unit fits 5,000 / 2,000 /
      500 with a typical loadout, and a test game shows no `[UnitBudget]` warning for it.
- [ ] Every level is a named `-lodN` group; any LOD1 body keeps every rig node of LOD0.
- [ ] Meks: HD, CT, LT and RT are real regions. Checked with an ownership render, one-at-a-time damage and HD-only
      removal. Detached limbs leave no floating weapons.
- [ ] Stock and custom loadouts, including hand, wrist, elbow and rear mounts; no baked searchlights or hidden guns.
- [ ] Camouflage and every damage stage in the game shader; intact areas stay readable.
- [ ] Walk, run, jump, attack, idle and death as applicable, with feet planted and correct facing.
- [ ] Terrain, footprint, supports and shadows match in both cameras. Landable multi-hex aerospace units also
      pass the landing-support review.
- [ ] Rendered frames inspected, and remaining limitations written down honestly. A screenshot is not an animation
      test, and no performance gain is claimed without a measurement.
