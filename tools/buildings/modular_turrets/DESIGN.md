# Modular turret kit

The shared shell (`shell.py`) carries center, twin, shoulder, external, mixed and pillar
heads. Weapons are independently bound equipment modules; `tools/modular_turret_profiles.py`
picks each weapon's module from the Mek weapon rule book and its rack size.

Use the existing schema 2 equipment system for this kit and future Meks/vehicles.
The implemented contract is in [modular-weapon-assets.md](../../../../megamek_temp/docs/modular-weapon-assets.md).

## Installed behavior

- Six weaponless heads, two wall casemates, three shared mounts, 52 weapon modules, board-material textures, and two
  authored LODs. Each weapon is one module for the front bay, the roof and (launchers) the side arm, centred on its
  trunnion with a boss on each side; a gun's receiver shows only on the roof and its mantlet only in a bay. The shared
  mounts carry exposed weapons, their pins entering the bosses: the side-arm bracket (top-to-bottom symmetric, rolled
  for the left), the roof post (a fork of two, or one beside it) and the roof pedestal (the weapon pitches about its
  hinge). The head yaws, the weapon pitches.
- Center/shoulder optics and searchlights have physical supports; auxiliary pads have adapter webs.
- Cannons and machine guns have separate barrel/breech recoil geometry. Their receivers and mounts remain stationary.
- Laser/PPC apertures are neutral; the weapon's shape identifies it and firing effects provide color.
- LRM/SRM cassettes have armored housings and recessed cells with the actual rack count.
- On the roof a gun shows its receiver (AC feed chute and recuperators, PPC capacitor housing, MG feed); in a bay
  its mantlet seals the face and the receiver stays inside. The stacked shoulder carrier has deep receiver housings
  rather than unsupported front panels.
- SRM/LRM use two installations: exposed or 75% encased. Other ranged weapons keep
  adjustable insertion inside a bay. Caliber, cell spacing/count, equipment identity
  and emitters remain intact.
- Turret yaw remains at the last firing direction across idle frames and model/LOD rebinding.

## Layout and rules

The carrier is selected from the actual equipment snapshot: one main weapon uses the
center head, two use twin, and larger recessed batteries use shoulder bays. Roof-only
batteries use the bare core. The roof holds up to four launchers or two guns (a third
gun moves into a front bay); missile-led batteries take the pillar with stacked side
arms. Front main weapons share the head with roof weapons; a roof gun above them stops
depressing at 6 degrees.
Two small auxiliaries can occupy lower pads. Each mounted item keeps its equipment index and emitters.
An LRM 20 is one launcher; four LRM 5s remain four separately addressable weapons.

This art arrangement does not impose new gameplay hardpoint limits. Fixed weapons,
pintles, locked turrets and multiple roof turrets must use the existing game rules.
Every gun emplacement and armed building gets this turret (mekset.txt `default_turret`): a roof
turret per armed hex and a wall casemate for each wall weapon pair. The emplacement model stays the
fallback when a loadout cannot assemble.

The original rules/source audit is preserved in [research.json](research.json).
It covers seven legacy gun-emplacement loadouts plus an advanced-building example.
The Java smoke test reads the seven real gun-emplacement files from `unit_files.zip`.

## Authoring

The authoring script runs headless or through the local Blender MCP. `shell.py` holds the
turret shell every head builds on (fixed collar and yaw hull), the turret materials and the
modelling helpers. Armor plates and covers are the unit `paint` role on the painted steel plate
`structures/turret/turret-paint`: the player's camouflage paints them like every other unit, shaded by
the plate's light and dark over its satin metal finish. Mechanical parts, gun steel and worn bevels are the board materials
`structures/turret/turret-dark`, `-steel` and `-edge`, Material Maker projects in
`tools/materials/structures/turret`. GLBs reference their albedo maps only.

## Verified outputs

`GpuBuildingTurretSmokeTest` renders real loadouts with the game renderer at both LODs, with top
views: the turret palette and rear receiver views, every gun on the roof and in an armored bay,
insertion depths, launchers exposed and encased, the three roof mounts and every component. It
writes them and `turret-palette-counts.csv` (triangles per assembly) to its screenshot folder.
Recoil checks keep receivers and mounts fixed; elevation keeps the trunnions aligned with their
mount pins. `review/final_supported.py` audits roof and side-arm clearance on the exported meshes.

The asset README lists measured geometry against [geometry.json](geometry.json). Dense batteries
exceed the initial 5,000/2,000 assembled target. No frame-rate improvement is claimed. No separate
LOD2 has been authored.

Not built: support columns, and scale conversion into existing Mek/vehicle placements. Catalogue
profiles leave ordinary Mek/vehicle model selections intact.
