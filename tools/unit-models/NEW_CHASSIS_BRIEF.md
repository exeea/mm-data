# Brief: author a new unit chassis

A standing brief for taking a chassis from a name to a reviewed model in the game. Read it with
[UNIT_REVIEW_PROCESS.md](UNIT_REVIEW_PROCESS.md) (the review loop and its rules),
[PRE_BUILD_CHECKLIST.md](PRE_BUILD_CHECKLIST.md) (the questions to settle first) and
[MODELLING_GUIDE.md](MODELLING_GUIDE.md) (the house rules for the artwork). It was first written after building
the Rifleman; every trap listed here cost real time.

**The deliverable is a reviewed model, not code.** The reviewer judges the artwork against the miniature. Get it
in front of them quickly and iterate.

## 1. What this pipeline is

MegaMek assembles each unit in the game from a **bare body** plus the **weapons its actual loadout carries**.
Nothing is made per variant: one Atlas body serves every Atlas variant, and each variant's own weapons are hung on
it when the unit is drawn.

Two repositories are involved:

| Repository | Holds |
|---|---|
| `mm-data` | the Python authoring tools, the recipes, the exported models, `mekset.txt` |
| `megamek` | the Java code that assembles and draws units, the catalog export, the review and validation tests |

**Geometry is written in Python, not modelled in Blender.** Bodies are boxes, beams and lofted cross-sections
written as code. Blender is used only to render review sheets and to look at finished files.

**What gets written.** Every component is one `.glb` file beside a `.json` descriptor, for example
`data/models/units/modular/bodies/atlas.glb` and `bodies/atlas.json`. Inside the GLB, each level of detail is a
named group: `atlas-lod0` is required, and `atlas-lod1` and `atlas-lod2` are optional. A missing level falls back
to the next more detailed one. MegaMek refuses a unit GLB whose levels are not named this way, but the exporter
does it for you. The old G3DJ format is gone.

**The budget** covers the whole assembled unit, body plus every weapon: 5,000 triangles at LOD0, 2,000 at LOD1 and
500 at LOD2. Aim for a LOD0 body under about 4,000 so there is room for the guns. Details are in section 8 of
UNIT_REVIEW_PROCESS.md.

Environment on the user's machine: Blender 5.2 at
`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, Python 3.13.

## 2. Prerequisites

**The equipment catalog.** The exporter needs `mm-data/.work/modular-models/equipment.json` (every equipment type
and how it is drawn). Without it the export stops with `FileNotFoundError`. Make it from the megamek checkout:

```bash
gradlew :megamek:exportEquipmentModelCatalog -PunitModelDataRoot=<your mm-data folder>
```

Without `-PunitModelDataRoot` it writes into the `mm-data` folder next to the megamek checkout, which from a
worktree is the main checkout, not yours. Re-run it when MegaMek's equipment changes.

**The Mek catalog, for research.** `gradlew :megamek:exportMekModelCatalog -PunitModelDataRoot=<your mm-data
folder>` writes `.work/mek-models/catalog.json`: every Mek, its loadout and its actuators. The exporter does not
need it, but the research queries below do.

Launcher shortcut: `1 - MegaMek Python (Unified).bat`, main menu `M`, then `4` exports the equipment catalog and
runs the exporter in one go.

The old baked-model tools (`build_unit_models.py`, `render_unit_variants.py`, `validate_unit_models.py`,
`build_unit_models.ps1`) were retired on 2026-09-28; ignore any older note that mentions them.

## 3. Research before you model

Do this before writing any geometry. It decides the design.

**Loadouts and actuators.** The highest-value query. It showed that no Rifleman variant has hands or lower arms,
so its arms are weapon pods rather than limbs, the single most important fact about that chassis. Run from
`mm-data`:

```bash
python -c "
import json
d=json.load(open('.work/mek-models/catalog.json'))
units=[u for u in d['units'] if u['chassis']=='<CHASSIS>']
print(len(units),'variants')
for u in sorted(units,key=lambda u:u['model'])[:15]:
    print('%-16s %5.0ft hands=%-8s lowerArms=%-8s' % (u['model'],u['mass'],
          ','.join(u['hands']) or '-', ','.join(u['lowerArms']) or '-'))
    for m in u['equipment']:
        if m['location'] in ('LA','RA') and m['family'] not in ('internal','none'):
            print('    %-3s %-28s %s' % (m['location'], m['name'][:28], m['family']))
"
```

Then count weapon families per location and look for rear-facing mounts:

```bash
python -c "
import json, collections
d=json.load(open('.work/mek-models/catalog.json'))
units=[u for u in d['units'] if u['chassis']=='<CHASSIS>']
live=[m for u in units for m in u['equipment'] if m['family'] not in ('internal','none')]
print('families:', dict(collections.Counter(m['family'] for m in live)))
print('locations:', dict(collections.Counter(m['location'] for m in live)))
print('rear:', [(m['location'],m['name']) for m in live if m['rear']] or 'NONE')
"
```

What to take from it:

- **No hands and no lower arms on any variant** means arm weapons mount at the elbow. Author no forearm and no
  fist; the arm is the gun housing.
- **Weapons per arm** decides the mount area shape: tall and narrow to stack two over-under, wide to set them
  abreast.
- **Jump jets** in the legs ride on the back of the calves and the exporter finds that spot for you. Give torso
  jets an `exhaustSockets` spot on the back of each torso location. One graphic per location, however many jets
  the unit file lists (UNIT_REVIEW_PROCESS.md section 5a).
- **Rear mounts** need `rearSockets` that clear the hull. Author them even if no variant uses one, for custom
  refits, but do not spend review time on them.

**The game sprite** gives left-right and front-back placement. Dump it as text rather than squinting at an 84x72
image:

```bash
python -c "
from PIL import Image
im = Image.open('data/images/units/meks/<Sprite>.png').convert('LA'); w,h = im.size; px = im.load()
print('    ' + ''.join(str((x//10)%10) for x in range(w)))
print('    ' + ''.join(str(x%10) for x in range(w)))
for y in range(h):
    row = ''.join('.' if px[x,y][1]<40 else '#' if px[x,y][0]<60 else '+' if px[x,y][0]<140
                  else '-' if px[x,y][0]<210 else 'o' for x in range(w))
    if row.strip('.'): print('%3d ' % y + row)
"
```

The sprite centre is pixel (42, 36). Model x is sprite x minus 42, model y is 36 minus sprite y, and up on the
sprite is forward on the model.

**The per-variant sprites.** A chassis usually has one generic sprite in `data/images/units/meks/` plus one per
variant. Compare them against the generic one to see what the artists changed:

```bash
python -c "
from PIL import Image
from pathlib import Path
base = Path('data/images/units/meks')
ref = Image.open(base / '<Chassis>.png').convert('LA'); w, h = ref.size; a = ref.load()
def shape(px, x, y):
    lum, alpha = px[x, y]
    return lum if alpha >= 40 else None
for path in sorted(base.glob('<Chassis>*.png')):
    im = Image.open(path).convert('LA')
    if im.size != (w, h):
        print('%-24s other size' % path.name); continue
    b = im.load()
    rows = [y for y in range(h) if any(shape(a,x,y) != shape(b,x,y) for x in range(w))]
    print('%-24s %s' % (path.name, 'identical' if not rows else '%d..%d' % (min(rows), max(rows))))
"
```

- **Differences only in the weapon rows** (the top third) mean one body with different guns, and the barrel width
  tells you how thick that weapon should be. The generic Rifleman sprite draws 4-pixel barrels; the RFL-3C, with
  twin AC/10s, draws 5-pixel ones.
- **Differences running down to the legs** mean the artists drew a different machine for that era. The RFL-1N
  is the original 3025 design and shares almost nothing with the later body.

You cannot satisfy every sprite and are not meant to. In `mekset.txt`, a variant with only a sprite line inherits
the chassis model, so one body serves every design. Treat the generic sprite as the main reference and the variant
sprites as a weapon-sizing check, and say in review which design the body follows.

**The miniature** is what the model is judged against. Ask the reviewer for pictures. When sprite and miniature
disagree, the miniature usually wins, but say so and let the reviewer rule.

## 4. The three files a Mek touches

### 4.1 The builder: `tools/unit_mek_chassis.py`

Add `def <id>(g):` building the body, **and** add `'<id>': <id>` to the `builders` dict inside `build_chassis`.
A recipe without a builder entry crashes the export with a `KeyError`.

Geometry calls on `g` (see `unit_model_geometry.py`):

| Call | Makes |
|---|---|
| `g.box(center, size, group, material, bevel=0, taper=1)` | a box, optionally chamfered |
| `g.beam(start, end, width, depth, group, material, sides=4, taper=1)` | a beam between two points |
| `g.prism(ring, bottom, top, group, material, taper=1)` | an extruded polygon |
| `g.loft(rings, group, material)` | a skin through a list of rings |
| `g.face(points, group, material)` | one flat polygon; the winding sets which way it faces |
| `g.joint(name, pivot, parent)` | a rig pivot; geometry is stored relative to it |
| `g.emitter(position, direction, group, role, effect)` | a muzzle or exhaust point |

Helpers in `unit_mek_chassis.py`: `upright` (stack cross-sections upward), `forward` (loft front to back), `panel`
(a flat inset such as cockpit glass), `foot` and `toes`, `lofted_face` and `capped_face` (the surface of a lofted
torso, for flush detail), `vent`, and `split_torso_locations` (UNIT_REVIEW_PROCESS.md section 6).

Materials: `paint`, `edge`, `metal`, `dark`, `glass`, and the weapon tips `laser`, `ppc`, `tag`, `plasma` and
`lamp`. `metal` and `dark` read as near-black; use them sparingly on large faces. Camouflage tints `paint` and
`edge`; everything else stays its own colour.

A Mek body must produce these rig groups: `pelvis`, `CT`, `HD`, `LT`, `RT`, `LA`, `RA`, `LL`, `RL`, plus `-shin`
and `-foot` on each leg. Optional arm parts are tagged `LA@elbow`, `LA@forearm`, `LA@wrist` and `LA@hand`, and each
variant shows the ones its actuators call for.

Hips sit around z 29 to 31 and a tall Mek tops out near 55 before `bodyScale`. Check the calibration table in
UNIT_REVIEW_PROCESS.md section 9 before trusting your eye on leg mass: a 60-tonner was once authored heavier than
two 70-tonners.

**An optional LOD1 body.** For a chassis whose LOD0 body is detailed enough that it needs a simpler shape at a
distance, give the builder a `far=False` parameter that draws the simpler shape when true, and set
`"bodyLod1": true` in the recipe. The Phoenix Hawk and Phoenix Hawk IIC do this. The LOD1 body must carry every
rig node the LOD0 body has (the export stops and names any that are missing); its weapons, vents and jets use the
LOD0 body's spots. The whole unit must fit 2,000 triangles at LOD1, and weapons without a LOD1 of their own count
at full size. LOD2 for units is being added to MegaMek now; there is no recipe key for it yet.

### 4.2 The recipe: `tools/unit-models/chassis.json`

Append one recipe, matching the file's compact hand formatting (several keys per line). Do not rewrite the file
with `json.dumps(indent=2)`; that reformats every existing chassis and turns a ten-line change into a
thousand-line diff.

Required: `name`, `id`, `referenceVariant`, `sprite`, `illustration`, `hip`, `silhouette`, and `sockets` with all
eight of `HD CT LT RT LA RA LL RL`. A socket is `[sprite x, sprite y, height]`, placed where the barrel leaves the
armour.

Optional keys the exporter reads:

| Key | Purpose |
|---|---|
| `rearSockets` | rear-facing mounts; without one the front point is reused nine pixels back, usually inside the hull |
| `socketBanks` | exact spots for one family in one location, for example `"RA:hatchet"` or `"LA@wrist:ppc"` |
| `socketAim` | direction for a location's weapons, so a barrel follows its limb |
| `protrusion` | how far barrels stand out: `recessed`, `short`, `medium` or `long` |
| `mountAreas` | the facing weapons are laid out on: `{"width": ..., "height": ...}`, optional `center` |
| `armSockets` | attach points per arm form: `{"LA": {"elbow": [...], "wrist": [...], "hand": [...]}}` |
| `weaponOverrides` | per-weapon changes matched by `location`, `family`, `name`, `rear` |
| `missileSockets`, `missileBayHeight`, `missileBayColumns`, `missileBayWidth`, `missileScale`, `missileSlope` | launcher bays; `missileSlope` stands a bay upright |
| `barrelLength`, `weaponScale` | gun sizing; `weaponScale` runs 0.83 (Atlas) to 0.95 |
| `searchlightSocket` | the external lamp position |
| `exhaustSockets`, `jumpJetScale` | torso jump jet spots and their size |
| `heldWeapons`, `hangingMounts`, `stackRows`, `sharedFaces`, `equipmentRules`, `ventDefaultSides` | see UNIT_REVIEW_PROCESS.md sections 4 and 5 |
| `bodyScale` | sets the body's height for its weight class (section 9 of the process doc) |
| `bodyLod1` | builds a separate LOD1 body (section 4.1 above) |

**Keys that do nothing.** `slotSpacing`, `missileColumns` and `missileOrientation` still appear in some older
recipes, but the current exporter never reads them from a recipe, and setting them gives no warning. Do not copy
them into a new one. An upright launcher bay comes from `missileSlope`.

### 4.3 The registration: `data/images/units/mekset.txt`

One line, with the other chassis entries:

```text
chassis "<Name>" "meks/<Sprite>.png" "units/modular/meks/<id>.json"
```

For example `chassis "Atlas" "meks/Atlas.png" "units/modular/meks/atlas.json"`. A variant's sprite-only line
inherits the chassis model, so variant lines need no change.

## 5. Vehicles

Named vehicles are built in mm-data the same way. The recipe goes in `tools/unit-models/vehicles.json`, the
builder in `tools/unit_vehicle_chassis.py` with an entry in its `VEHICLE_BUILDERS` dict, and a builder must make a
`hull` joint. The exporter writes `bodies/<id>.glb` and a family descriptor `families/<id>.json`, registered in
`mekset.txt` like `chassis "Manticore Heavy Tank" "vehicles/Manticore.png" "units/modular/families/manticore.json"`.
The Manticore and Manticore II are the examples.

The BattleTech Unit Viewer (launcher main menu `6`) can draft a first version of a Mek or vehicle with Generate
MiniMek. It builds in a private sandbox and deploys only that chassis's three files (its Mek or family
descriptor, `bodies/<id>.json` and `bodies/<id>.glb`) plus its manifest entry. It never commits.

## 6. Build, review, validate

```bash
# from mm-data: exports every asset into data/models/units/modular
python tools/build_modular_unit_models.py

# bare body, six angles plus the waist-twist sheet, into .work/body-review/
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --factory-startup \
    --python-exit-code 1 --python tools/render_modular_body.py -- --body <id> --turn 60

# from megamek: stage the data, check the descriptors, then assemble real units and render them
gradlew :megamek:stageDataFiles
gradlew :megamek:test --tests "*UnitModelDescriptorTest*"
gradlew :megamek:gpuBoardSmoke --tests "*GpuModularUnitModelsSmokeTest*"
```

The first two commands are the iteration loop. Expect several rounds (the Archer took five, the Rifleman seven)
and send a sheet each round. Assembled images land in `megamek/build/gpu-board-review/`. Staging copies from the
`mm-data` folder beside the megamek checkout; from a worktree read UNIT_REVIEW_PROCESS.md section 1a first, or you
will review someone else's models.

While exporting, watch for `Weapon review:` lines (a weapon piece over 250 triangles) and for a refusal of a body
over its level's budget. After staging, playing the unit in MegaMek and checking `megamek.log` for `[UnitBudget]`
shows whether any real loadout goes over.

To add the chassis to the assembled review and the variant sheets, see UNIT_REVIEW_PROCESS.md section 2.

Other tests that cover the pipeline in megamek: `RigidGlbTest` (reading GLBs and their level groups),
`UnitEquipmentAssemblyTest` (fitting weapons and the budget warning), and the on-screen `GpuMekLodSmokeTest` and
`GpuUnitModelBenchmarkSmokeTest`.

## 7. Traps that cost real time

- **A stale edit is silent.** Replacing a recipe value that an earlier pass already changed does nothing, the build
  still succeeds, and the render looks unchanged for the wrong reason. Print the value back after every edit.
- **A bevel narrows the flat face.** A `cut` of 0.3 on a 17-wide, 13.7-deep section leaves only about +/-6.4 of
  flat face. Detail outside that band hangs off the chamfer.
- **A lofted face slopes.** Flush detail at one fixed depth ends up half buried. Use `lofted_face`.
- **Winding sets the facing.** A front panel and a back panel need opposite vertex order, or one is invisible.
- **Mount area axes:** `width` is left-right, `height` is vertical.
- **Positions in the GLB are relative to each part's node**, not to the unit.
- **Commits.** The person running the work decides whether and when to commit. Tools and agents never push.

## 8. Definition of done

- [ ] Whole unit within budget: LOD0 body under about 4,000 triangles, the heaviest-armed variant under 5,000,
      and no `[UnitBudget]` warning in megamek.log for the variants played (UNIT_REVIEW_PROCESS.md section 8).
      If the chassis has a LOD1 body, the same check against 2,000.
- [ ] No weapon piece over 250 triangles without the reviewer agreeing to it.
- [ ] Six-view bare sheet reviewed and accepted.
- [ ] Waist twist clean at 60 degrees: nothing above the waist cuts the hips or legs, and no gap opens.
- [ ] Rear view confirmed: rear weapons actually show rather than sitting inside the hull.
- [ ] `UnitModelDescriptorTest` passes.
- [ ] `GpuModularUnitModelsSmokeTest` passes, and the assembled render is reviewed for at least two loadouts of
      different weapon families, so a PPC and an autocannon are both seen in the same mount.
- [ ] Variant sheet rendered and reviewed.
- [ ] Lineup rendered against two neighbours of similar tonnage and read for width, depth and limb mass.
- [ ] Height inside the weight-class band, measured to the tallest structural part, not a wire antenna.
- [ ] Vents: at most two front and two back, back vents on torso locations only.
- [ ] Jump jets: one graphic per location that has any, on the back of the torso or calf.
- [ ] Registered in `mekset.txt` and present in the staged game data.

## 9. Worked example

The Rifleman is the reference build. Its decisions are in section 10 of UNIT_REVIEW_PROCESS.md, and its signed-off
state is kept in [preserved/rifleman-final/](preserved/rifleman-final/README.md). Its body is `rifleman` in
`unit_mek_chassis.py` and its recipe is in `chassis.json`. The arm-pod treatment for a chassis with no hands, and
the vent placement, both carry over directly. For a chassis with a LOD1 body, read `phoenix-hawk` instead.
