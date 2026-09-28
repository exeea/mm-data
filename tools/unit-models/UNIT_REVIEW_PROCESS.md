# Unit review process

How a chassis is built, reviewed and signed off. [MODELLING_GUIDE.md](MODELLING_GUIDE.md) holds the house rules
for the artwork itself; this file holds the working loop and the review conventions agreed during real review
rounds. Treat them as binding. [NEW_CHASSIS_BRIEF.md](NEW_CHASSIS_BRIEF.md) walks through a new chassis end to
end, and [PRE_BUILD_CHECKLIST.md](PRE_BUILD_CHECKLIST.md) is the conversation to have before modelling starts.

## 1. The loop

Every unit component (a Mek body, a vehicle body, a weapon) is one `.glb` file beside a `.json` descriptor. The
GLB holds its levels of detail as named groups: the Atlas body is `bodies/atlas.glb`, with a group
`atlas-lod0` and, when the chassis has one, `atlas-lod1`. `-lod0` is required; MegaMek refuses a unit GLB whose
levels are not named groups. The exporter writes all of this for you.

| Step | What you do |
|---|---|
| Equipment catalog | From the megamek checkout: `gradlew :megamek:exportEquipmentModelCatalog -PunitModelDataRoot=<mm-data folder>`. Needed once, and again whenever MegaMek's equipment changes. |
| Author the body | In `tools/unit_mek_chassis.py`: a `def <id>(g)` plus an entry in the `builders` dict inside `build_chassis`. |
| Write the recipe | In `tools/unit-models/chassis.json`: hip, eight sockets, mount areas. |
| Export | From mm-data: `python tools/build_modular_unit_models.py`. |
| Review the bare body | `blender --background --factory-startup --python-exit-code 1 --python tools/render_modular_body.py -- --body <id> --turn 60` |
| Register | One `chassis` line in `data/images/units/mekset.txt`. |
| Stage | `gradlew :megamek:stageDataFiles` (see section 1a). |
| Validate | `gradlew :megamek:test --tests "*UnitModelDescriptorTest*"` |
| Review assembled | `gradlew :megamek:gpuBoardSmoke --tests "*GpuModularUnitModelsSmokeTest*"` |

Export and bare-body review are the iteration loop, well under a minute a round. Expect several rounds: the
Archer took five, the Rifleman seven. Send a sheet each round.

The launcher (`1 - MegaMek Python (Unified).bat`) wraps the same steps: main menu `M` opens the model work menu,
where `4` exports the catalog and then runs the exporter, and `5` stages game data. Main menu `7` opens any unit
GLB in Blender (type a body name such as `atlas`, type `LIST`, or drag a file in); its LOD1 and LOD2 groups start
hidden.

Assembled review images land in `megamek/build/gpu-board-review/`, named for the unit they show:
`runtime-new-Rifleman RFL-3N-full.png`.

The old baked-model tools (`build_unit_models.py`, `render_unit_variants.py`, `validate_unit_models.py` and
`build_unit_models.ps1`) were removed on 2026-09-28, along with the old baked reference models. Judge a body
against the miniature and the sprites, not against an earlier export.

### 1a. Staging: make sure the game sees your build

The exporter writes into mm-data's `data/models/units/modular`. MegaMek, and the Gradle review tests, read the
copy staged into the megamek checkout's `megamek/data`. `stageDataFiles` copies from the `mm-data` folder that
sits next to the megamek checkout. In a worktree under `Worktrees/`, that `mm-data` is a junction to the main
mm-data checkout, which may be on another branch. So either run from matching checkouts, or stage and then copy
your built `data/models/units/modular` folder over the staged one. `gpuBoardSmoke` stages again on every run, so
from a worktree it will review the junction's models, not yours, unless the two match.

## 2. The review sheets

### The renders to ask for

| Ask for | What it shows | Produced by |
|---|---|---|
| the chassis | bare body, six angles, no weapons | `render_modular_body.py` |
| the chassis with weapons | one variant assembled, six angles | `renderFullReview`, called from `GpuMekAssemblyReview` |
| the variant sheet | every variant of the chassis in a grid, one angle each, with triangle counts | `GpuVariantSheetReview` |
| the lineup | several bodies side by side, one camera, feet on one ground line | `render_modular_body.py --lineup` |

A **full render** means all six angles on one sheet: Front, Back, Left, Right, Above, Three-quarter, three across.

- **Bare body:** `render_modular_body.py` writes `<id>-review.png` into mm-data's `.work/body-review/`, labelled.
  It draws the body's LOD0 group.
- **Assembled:** `renderFullReview` writes `runtime-new-<unit>-full.png`, same order, **unlabelled**. Read it as
  front, back, left on the top row; right, above, three-quarter on the bottom.

Every sheet carries the chassis and model in its top right corner, so a render stays identifiable once it leaves
the build folder. A bare-body sheet uses the chassis name from the recipe.

To add a chassis to the assembled review, add rows to the `cases` array in `GpuMekAssemblyReview.java` as
`{ label, body descriptor id, unit file path }`; several rows may share one body, which is how the Rifleman shows
its 3N, 4D and 3C loadouts. For a variant sheet, add the chassis to the `sheets` list near the end of `verify`.
The variant sheet writes `variants-<Chassis>.png`, eight across, sorted by model, headed with the count and the
triangle range.

Give every test unit a full render, not just the chassis it was authored from. Each variant hangs a different
loadout on the same body, and that is the only way to see whether an arm pod suits a PPC as well as an
autocannon.

### The lineup

A lineup answers whether a body reads at the right weight beside its neighbours. Every body stands on the same
ground line at the same scale.

```bash
blender --background --factory-startup --python tools/render_modular_body.py -- --lineup heavy-lineup --body warhammer --tons 70 --body rifleman --tons 60 --body archer --tons 70
```

Run one for every new chassis against two neighbours of similar tonnage, and read it for **width, depth and limb
mass**, not height. Mass is carried by silhouette rather than by making light units small: the Rifleman at 53.0
units tall reads plainly lighter than the Warhammer at 52.0, and correctly so.

### Height is measured to the body, not to a wire

The rule that antennas must not inflate a body's weight class means **wire antennas**, such as the thin whips on
the Archer's head. A mast carrying a housing and a crossbar is body.

| Chassis | Measured | Actual body | Difference |
|---|---:|---:|---|
| Archer | 61.5 | 55.0 | 6.5 of wire antenna |
| Rifleman | 53.0 | 53.0 | none; the crossbar is structural |
| Warhammer | 52.0 | 52.0 | none |

Measure the tallest `paint` or `edge` part, not the overall bounds, before deciding a body misses its band.

### The waist-twist gate

`--turn <degrees>` adds a second sheet with the upper body turned about the recipe's hip point while hips and legs
stay put. Nothing above the waist may cut through the hips or legs, and no gap may open between them.

### Which side is which

Checked against geometry that exists on one side only (the Mackie's shield disc rings its right arm):

- **Front:** the unit faces you, so its right side is on the image left.
- **Back:** its right side is on the image right.
- **Above:** looking down, nose up the page, its right on the image right. That matches the 84x72 game sprite,
  so the two are directly comparable.
- Each cell is centred on its own posed bounds, so a plan view does not float against an elevation.

## 3. Markup conventions

Mark up the rendered sheet and send it back. Marks are located to the pixel and turned into authored numbers,
so rough boxes are fine.

A **red box is always a sizing change**, and may show both size and basic shape. With it:

- **Tapering stays.** A resize scales the taper, step or bevel already authored; it does not flatten it.
- **Two boxes on the same part from different views are one instruction.** Front and Back both measure width and
  height, so a pair is a cross-check; average them.
- **The edges a box shares with the part carry meaning.** A box whose bottom sits on the part's bottom edge
  means take the change off the top.

### Vocabulary

| You say | Control | Value |
|---|---|---|
| flush, recessed, flat against the body | `protrusion` for that location | `recessed` (0.06) |
| barely proud, stubby | `protrusion` | `short` (0.4) |
| standing out | `protrusion` | `medium` (0.7) |
| reaching well ahead | `protrusion` | `long` (1.0) |
| longer or shorter barrel than standard | `weaponOverrides` `length` for that location and family | authoring units, scaled by `weaponScale` |
| bigger or smaller guns overall | `weaponScale` | 0.83 (Atlas) to 0.95 (Mad Cat, Mackie, Rifleman) |
| closer to or further from a feature | the location's socket in `sockets` | sprite x, sprite y, height |

Flush and recessed mean the same thing. Add a row when a new term comes up.

### Measuring a marked box

Never eyeball it. Take the scale from a known size in the same render: measure the model's width in pixels on one
panel and divide by its width in authoring units (from the descriptor's `bounds`). Apply that figure to the box.

Worked example, the Rifleman arm pod: the Front panel measured 353 px across a known 41-unit width, which is 8.61
px per unit. The two boxes measured 72x99 and 66x104 px, or 8.4x11.5 and 7.7x12.1 units, averaging 8.0 x 11.8.
Against a pod then 10 x 15, that is a uniform 0.79 scale that keeps the pod's proportions.

## 4. How weapons are placed

### Deciding where a socket goes

Four steps, in order. Going straight to "what looks right in the render" produces a mount that is plausible from
one angle and wrong from every other.

1. **The unit file owns the location.** Put the weapon on the location it names. A location is a gameplay fact:
   it decides what is destroyed with that part. Move the socket within its own location, never to a neighbour.
   The BattleMaster's rear medium lasers are one in each side torso, not a pair in the centre torso, however much
   the artwork suggests a centred pair.
2. **Start at the centre of that location's own facing,** the area-weighted centre of the faces pointing the way
   the weapon fires. Measure it. A location's front and rear facings have different centres.
3. **Then read the count and the size.** Two medium lasers need different spacing from one large one. `mountAreas`
   decides the arrangement: a tall narrow area stacks weapons over-under, a wide one sets them abreast.
4. **Only then follow reference artwork,** and only within the location the unit file gave.

### Flush means the model sits on the surface

A flush mount puts the bottom of the equipment on top of the armour it mounts to: not sunk into it, not hovering
above it. Measure the surface and the model's own height and place the socket so the two meet. Guess, render and
nudge has repeatedly taken three rounds where one measurement would have done.

### What the game does with a socket

A socket names where a weapon leaves the armour, and `mountAreas` gives the facing it is laid out on. MegaMek then
places that location's weapons on the facing.

- **Weapons sharing a socket are centred on it as a group.** Their heights are summed with a 0.4 gap and the stack
  is centred, largest on top. A single weapon sits exactly on its socket.
- Missile bays arrange their own rows. A weapon that cannot fit is shrunk in fixed steps, and only then moved.
- **Left and right mirror; they never copy.** A crowded weapon steps toward the Mek's centre line, worked out for
  each face. Any rule with a direction is stated relative to the centre line, never as a fixed +x or -x, and is
  checked by measuring both sides. The BattleMaster's side-torso lasers once sat 12.9 px further out on one side
  because the packer always stepped the same way.

### Guns held in the hand

A recipe that lists an arm in `heldWeapons` (for example `"heldWeapons": ["LA", "RA"]`) makes that arm hold its
large weapons as a gun instead of growing them out of the forearm. Nothing about it is authored per chassis.

- **Which weapons:** the Mek-mountable PPCs, autocannons, Gauss rifles, large lasers and plasma weapons listed
  under `held` in `weapons.json`. Machine guns, small and medium lasers, flamers and launchers keep their ordinary
  shape.
- **The chassis supplies the gun body.** The exporter measures the chassis's own forearm end and hand and builds
  `<arm>@held` to fit. The arm needs `@forearm` and `@hand` parts; the export stops with an error if they are
  missing.
- **The weapon supplies the barrel,** sized from the weapon, so a Heavy PPC carries a bigger barrel than a Light
  PPC. Barrel length overrides do not stretch it.
- **In the game,** an arm holding a gun shows the gun body and loses its hand. Two held weapons in one hand stack
  over-under like a double-barrelled gun. An arm with no hand keeps its ordinary barrel.

Review one held barrel with `render_modular_body.py -- --equipment <name> --profile held`, or every distinct
held barrel side-on with `-- --held-all <sheet> --angle 120`. The held sheet's captions use weapon names from
the Mek catalog (`gradlew :megamek:exportMekModelCatalog`); without it they fall back to internal names.

### Other mount settings a recipe can use

- `hangingMounts`: the socket marks an underside, and the weapon hangs from it.
- `stackRows`: weapons sharing a socket sit side by side, a new row below when the face is full.
- `sharedFaces`: one location's weapons pack onto another location's face, as the Locust's head and centre torso
  share its chin turret.
- `equipmentRules`: one weapon drawn with another weapon's art at a spot of its own. The Atlas draws every LRM 20
  as an LRM 5 rack stood on end at the right of its waist. The weapon keeps its own location for damage.

## 5. Vents

Vents are the standard surface detail for a torso: a shaded recess behind three lit fins, drawn as flat panels in
the skin, eight triangles each.

- **At most two on the front and two on the back.** Back vents go on torso locations only.
- **Put them where the heat sinks are.** The Mek catalog records a location for every heat sink that takes a
  critical slot; count those across every variant and ignore engine sinks.

| Chassis | Slotted sinks by location | Vents go |
|---|---|---|
| Rifleman | LT 25, RT 24, LL 12, RL 10, CT 5 | LT and RT |
| BattleMaster | RT 37, LT 23, LA 20, RA 14, CT 7 | LT and RT |

- Keep them clear of the location's weapon socket. The Rifleman's side-torso lasers sit at z 37.9, so its vents
  sit low at 30.9 to 33.4.

**Weapons first, vents after.** The body cannot know where a variant's weapons go, so a vent on a modular body is a
spot, not armour. The vents you draw are the first choice, and `finish_vents` (in `unit_mek_vents.py`) adds up to
three spare spots on each torso face, mirrored left to right. In the game, MegaMek places the variant's weapons
first, then puts the vents in the torsos holding that variant's slotted heat sinks, each on the first spot no
weapon covers. A vent with no free spot is left off. Each decision is logged at debug level.

- **Legs, front only.** A chassis may draw vents on the front of its shins; a variant with leg heat sinks then gets
  them there (the Griffin GRF-1S).
- **No slotted sinks, no vents:** `"ventDefaultSides": []` leaves bare a variant whose sinks all sit in the engine
  (the Griffin).

Three surface traps, all learned on the Rifleman:

- **Follow the skin's slope.** A torso lofting from 13 deep to 14.5 over six units of height moves its face 0.125
  per unit; a panel at one fixed depth ends up half buried and half floating. Use `lofted_face`.
- **Stay inside the flat part of the face.** A bevel narrows the flat band: a `cut` of 0.3 on a 17-wide, 13.7-deep
  section leaves only about +/-6.4 flat.
- **Reverse the winding on the back** so the panels still face outward.

## 5a. Jump jets

**One jump jet graphic per location.** It says a location has jets; it does not count them. A location listing
three jets shows one nozzle. The extra jets share that nozzle, so every working jet still fires its exhaust from it,
and a destroyed extra jet never shows the drawn one as wrecked. MegaMek does this for every chassis
(`UnitEquipmentAssembly.shareJumpJets`).

Put `exhaustSockets` on the back of each torso location, clear of the back vents (jets are placed before vents).
Leg jets ride on the back of the calves and the exporter finds that spot itself. Before this rule the Griffin
GRF-4R's four right-torso jets ran in a column from shoulder to thigh. `jumpJetScale` draws a chassis's jets smaller
where the nozzle crowds the back.

## 6. Torso locations must be real

A body needs real, drawable `HD`, `CT`, `LT` and `RT` surface; a joined torso labelled `CT` is not allowed.

- **The export refuses a joined torso:** a centre section may not reach past 75 per cent of the torso's
  half-width. The Archer, Mad Cat, Marauder and King Crab all once shipped with a shoulder pod as their only `LT`
  geometry and the whole torso skin as `CT`, so the side torso could be destroyed while its armour stayed drawn.
- **A new body declares its seam:** `split_torso_locations(g, seam=4.2)`, where the seam is where the chest stops
  and the arm-carrying structure starts. Call it before authoring any `LT` or `RT` accessory.

## 7. Arms that flip

A Mek with no lower arm or hand actuators can flip its arms to fire behind it, and MegaMek shows it: each arm turns
about its shoulder's own left-right axis, up and over to point backwards. That axis never changes x, so an arm
buried inside its shoulder sweeps through solid armour halfway over. **A shoulder ends where its arm begins.**

```
right pod      x 12.75 .. 21.25
right shoulder x  3.25 .. 12.75   flush, gap 0.00
```

On the Rifleman the shoulder went from 3.5..18.5 to 3.25..12.75 while the pod stayed put: the same overall width,
and the pods now read as separate objects. The older chassis still bury their arm joints by 0.5 (Mackie) to 5.3
(Mad Cat); they look right at rest and show the arm passing through the shoulder when flipped.

## 8. Budget

The budget is for the **whole assembled unit**, bare body plus every fitted weapon, at each level of detail:

| Level | Whole unit | Shown when the unit is on screen at |
|---|---:|---|
| LOD0 | 5,000 triangles | more than 96 px |
| LOD1 | 2,000 triangles | 32 to 96 px |
| LOD2 | 500 triangles | under 32 px (being added to MegaMek now) |

(Infantry and battle armour switch at 48 and 16 px instead.)

- **Bodies.** The exporter refuses a bare body over its level's whole budget. Aim for a LOD0 body under about
  4,000, so roughly 1,000 is left for weapons. There is no virtue in coming in far under; spend it on the features
  that make the chassis read as itself.
- **Weapons.** One weapon or equipment piece over 250 triangles prints a `Weapon review:` line during export; over
  1,000 fails the build.
- **LOD1.** A chassis that asks for a LOD1 body (`"bodyLod1": true`, as the Phoenix Hawk does) must fit the whole
  unit in 2,000 at that level. A weapon with no LOD1 of its own counts at its LOD0 size, so leave room.
- **In the game,** a unit whose real loadout goes over its level's budget is still drawn in full, and megamek.log
  gets a warning tagged `[UnitBudget]` naming the body, the level and the counts. Formations and squadrons are not
  covered by that warning.

To report a unit, give body, weapons and assembled totals separately. The exporter prints warnings and a summary,
and `manifest.json` records each asset's triangles plus a `lods` list with each level's group name and triangles.
The variant sheet heads each chassis with its assembled triangle range, which is the quickest way to find the
heaviest loadout. That count is everything the sheet draws, so treat it as the LOD0 total only for a chassis
without a LOD1 body; for one with a LOD1 body, rely on the `[UnitBudget]` warning instead.

## 9. Calibration by tonnage

Legs are the easiest thing to overbuild. Check a new chassis against the existing ones before trusting your eye:

| Chassis | Tons | Hip x | Foot |
|---|---:|---|---|
| Warhammer | 70 | 7.5 | 9 x 12 |
| Archer | 70 | 8 | 11 x 15 |
| Rifleman | 60 | 7.5 | 9.5 x 13 |

A sixty-tonner with a wider stance and bigger feet than either seventy-tonner is wrong, however good it looks alone.

**Height by weight class.** The house convention is that scale 1.0 is 54 model units, two board levels. Measure to
the top of the armour, ignoring wire antennas, and keep every Mek of a class inside its band:

| Class | Scale | Model units | Set so far (scale) |
|---|---|---|---|
| Light | 0.75-0.80 | 40.5-43.2 | Locust 0.791, Panther 0.793 |
| Medium | 0.82-0.87 | 44.3-47.0 | |
| Heavy | 0.89-0.94 | 48.1-50.8 | Rifleman 0.914, Warhammer 0.924, Mad Cat 0.924, Archer 0.931, Marauder 0.933 |
| Assault | 0.95-1.00 | 51.3-54.0 | King Crab 0.966, BattleMaster 0.981, Mackie 0.985, Atlas 0.991 |

Within a band, order by the height of the official miniature: the tallest heavy mini lands near 0.94, the shortest
near 0.89. Those placings were taken from a spreadsheet of official miniature heights, `BTMmm.xlsx`, which is
**not in the repository**; ask the user for a copy. A chassis with no known mini is placed by eye (the Mackie sits
just under the Atlas).

Fix a body's height with the recipe's `bodyScale`, never by re-authoring it. The whole body scales evenly, and the
exporter scales the recipe's sockets, mount areas, weapon sizes and barrel lengths with it.

## 10. Per-chassis decisions

### Rifleman (60 t, `rifleman`)

**Signed off 2026-09-20 at 674 triangles, under the old per-body budget. Preserved in
[preserved/rifleman-final/](preserved/rifleman-final/README.md).** Treat it as the worked example for the rules
above; change it only against a new reference, not on taste.

- **No variant has a hand or a lower arm.** Every variant carries its weapons at the elbow, so each arm is a weapon
  pod rather than a limb. No forearm or fist is authored.
- **Every variant carries two weapons per arm.** The pod's mount area is taller than it is wide, so the pair stacks
  over-under, matching the line art.
- No variant mounts a rear-facing weapon; the jump jets ride in the calves.
- Radar: a swept blade on a short mast, centred. The game sprite puts a two-pronged array right of centre; the
  miniature and the approved artwork win.
- Barrels are lengthened in the recipe (`weaponOverrides`, ballistic 21, laser 18) because the standard shapes read
  as stubs on a design whose identity is its guns.
- The head runs the full length of the centre torso, which needs an `upright` loft because its front face moves
  with height.
- **Shoulders stop at 12.75, where the arm pods start** (section 7).
