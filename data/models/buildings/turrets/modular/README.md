# Modular turret GLBs

Six weaponless heads, two wall casemates (`head-casemate`, `-twin`), three shared mounts and 52 weapon modules.
Each GLB contains
`-lod0` and `-lod1` groups. Armor plates and covers are the unit `paint` role on the painted steel
plate `structures/turret/turret-paint`: the player's camouflage paints them, shaded by the plate's light
and dark over its satin metal finish; without camouflage the plate itself shows. Mechanical parts, gun
steel and worn bevels are the board materials `structures/turret/turret-dark`, `structures/common/steel` and
`structures/turret/turret-edge` (Material Maker projects in `tools/materials/structures`): a GLB references only the
albedo map, and the `.tres` beside it gives the finish and normal map. Draw one LOD at a time.
The adjacent schema 2 JSON describes bounds, joints, hardpoints and effect emitters.

| GLB | LOD0 triangles | LOD1 triangles |
| --- | ---: | ---: |
| `arrow-iv.glb` | 1,244 | 548 |
| `artillery-heavy.glb` | 3,732 | 820 |
| `artillery-light.glb` | 3,732 | 820 |
| `artillery.glb` | 3,724 | 820 |
| `atm-12.glb` | 1,708 | 724 |
| `atm-3.glb` | 1,186 | 526 |
| `atm-6.glb` | 1,360 | 592 |
| `atm-9.glb` | 1,534 | 658 |
| `autocannon-10.glb` | 3,784 | 772 |
| `autocannon-2.glb` | 3,776 | 772 |
| `autocannon-20.glb` | 3,420 | 772 |
| `autocannon-5.glb` | 3,776 | 772 |
| `autocannon-compact.glb` | 2,552 | 704 |
| `flamer-heavy.glb` | 1,180 | 520 |
| `flamer.glb` | 1,180 | 520 |
| `gauss-heavy.glb` | 3,252 | 988 |
| `gauss-light.glb` | 3,680 | 1,064 |
| `gauss.glb` | 3,596 | 1,048 |
| `hag-20.glb` | 3,144 | 980 |
| `hag-30.glb` | 3,260 | 1,008 |
| `hag-40.glb` | 2,992 | 1,008 |
| `head-casemate-twin.glb` | 400 | 224 |
| `head-casemate.glb` | 358 | 210 |
| `head-center.glb` | 3,332 | 1,148 |
| `head-mixed.glb` | 3,416 | 1,176 |
| `head-pillar.glb` | 2,984 | 1,024 |
| `head-pods.glb` | 3,246 | 1,106 |
| `head-shoulder.glb` | 3,784 | 1,404 |
| `head-twin.glb` | 3,330 | 1,134 |
| `laser-large.glb` | 1,042 | 398 |
| `laser-medium.glb` | 1,042 | 398 |
| `laser-small.glb` | 1,042 | 398 |
| `lrm-10.glb` | 1,592 | 680 |
| `lrm-15.glb` | 1,882 | 790 |
| `lrm-20.glb` | 2,172 | 900 |
| `lrm-5.glb` | 1,302 | 570 |
| `machine-gun.glb` | 716 | 388 |
| `mml-3.glb` | 1,186 | 526 |
| `mml-5.glb` | 1,302 | 570 |
| `mml-7.glb` | 1,418 | 614 |
| `mml-9.glb` | 1,534 | 658 |
| `mortar-1.glb` | 958 | 482 |
| `mortar-2.glb` | 1,016 | 504 |
| `mortar-4.glb` | 1,132 | 548 |
| `mortar-8.glb` | 1,364 | 636 |
| `mount-arm.glb` | 684 | 172 |
| `mount-pedestal.glb` | 328 | 144 |
| `mount-post.glb` | 382 | 92 |
| `mrm-10.glb` | 1,592 | 680 |
| `mrm-20.glb` | 2,172 | 900 |
| `mrm-30.glb` | 2,752 | 1,120 |
| `mrm-40.glb` | 3,332 | 1,340 |
| `plasma-cannon.glb` | 2,508 | 788 |
| `plasma-rifle.glb` | 2,396 | 788 |
| `ppc-heavy.glb` | 4,012 | 764 |
| `ppc-light.glb` | 3,364 | 748 |
| `ppc.glb` | 3,828 | 748 |
| `rotary-2.glb` | 3,356 | 1,140 |
| `rotary-5.glb` | 3,356 | 1,140 |
| `srm-2.glb` | 1,128 | 504 |
| `srm-4.glb` | 1,244 | 548 |
| `srm-6.glb` | 1,360 | 592 |
| `thunderbolt.glb` | 1,070 | 482 |

The fixed collar belongs to the head. Head mounting datum is glTF Y=0, with a 0.45-unit underside
embed. Authoring/JSON coordinates are Z-up and +Y forward; exported glTF is Y-up and
-Z forward. The loader converts once.

`turret.json` is an explicit assembly recipe. The shared equipment catalogue has
665 optional turret-profile mappings (`tools/modular_turret_profiles.py`). The Mek weapon
rule book (`tools/unit-models/weapons.json`) says what each weapon is; the rack size picks the calibre or tube count:
- Autocannons and cannon-class rifles map by rack size to four calibre tiers (`autocannon-2/5/10/20`):
  longer, slimmer barrels for light calibres, shorter and wider bores for heavy ones; crowded heads use
  `autocannon-compact`. Rotary cannons map by rack size to `rotary-2/5`.
- Thumper, Sniper and Long Tom howitzers and cannons map to `artillery-light`, `artillery` and `artillery-heavy`.
- Gauss rifles map to `gauss-light` (light, AP, Magshot), `gauss` (standard, Silver Bullet) and `gauss-heavy`
  (heavy, improved heavy); hyper-assault Gauss rifles to the four-barrel `hag-20/30/40`.
- PPCs map to light (light, snub-nose, support), standard and heavy tiers; TSEMP uses `ppc-heavy`. Plasma weapons
  map to `plasma-rifle` and `plasma-cannon`.
- Lasers map by their rule-book size (Blazer, Bombast and Hyper lasers are large, Laser AMS small); other
  energy weapons such as chemical lasers use the medium laser. TAG and C3 masters show the small laser lens.
- Flamers map to `flamer` and `flamer-heavy`; machine guns, AMS, APDS and other small ballistic weapons to the
  machine gun.
- Launchers take the smallest `racks.py` rack holding their tubes: LRM and rocket launchers 5-20, SRM 2-6,
  MML 3-9, MRM 10-40, ATM and iATM 3-12, 'Mech mortars 1-8, Arrow IV (and cruise missiles) and Thunderbolt.
  Narc uses `srm-2`.
Infantry weapons and other equipment retain their previous model path. Existing Mek/vehicle defaults are unchanged.

Every weapon is one module for every installation, centred on its trunnion, with a trunnion
boss on each side; its `elevation` joint turns about local X (a visual -20/+25 degree stop)
while the turret bearing provides yaw. A gun carries its barrel or emitter and, where it has
them, the receiver that carries it on the roof and the mantlet that seals it in a front bay (the
lasers have neither, the MG no mantlet): a planned mount's `omit` leaves out the part its
installation does not show. Autocannon receivers have an armored feed
chute, recuperators and a recoil clamp; PPCs a capacitor housing, arching power cables and a
radiator-finned accelerator; MG receivers feed couplings; laser/PPC modules expose their
power/cooling bodies. Artillery and rotary cannons use the autocannon receivers; Gauss rifles
and HAGs the PPC's capacitor housing with the autocannon mantlet; plasma weapons the PPC
housings and flamers the MG receiver. A launcher is its rack.

In a front bay, on a lower pad or in a wall casemate a gun's barrel leaves the face at its
socket (its `face` point), the receiver left out inside the head, at adjustable numeric
insertion (zero is flush with the bay); a launcher sits 75% encased (`encased: true`). Exposed
(`encased: false`), weapons ride the shared mounts, each with a trunnion pin that enters the
weapon's boss (its `trunnion` point): `mount-post` on the roof (a fork of two posts, the left
post turned half a turn, or one post on the inboard side), `mount-pedestal` on the roof (one
column under the weapon, which pitches about its hinge pin) and, for launchers, `mount-arm`
(the side-arm bracket, its left copy rolled half a turn; the launcher hangs outboard of its
pin). A roof socket marks the weapon's rear. The recipe's `roofMount` picks `posts` (the
default), `post` or `pedestal`. Launchers default to exposed: side arms on the thin
`head-pillar` (two, or four stacked) or one per flank of a broad head, others on the roof;
other weapons default to the front bay. Any mix assembles: front weapons fill bays by count,
exposed guns ride the roof (depression stops at 6 degrees above front bays), launchers take
side arms, and what a carrier cannot hold moves into front bays. Cannons/MGs have separate
barrel/breech recoil joints; their receivers and mounts stay fixed during recoil. Laser, PPC,
plasma, flamer and launcher modules have no mechanical recoil. Rack layouts and emitter
spacing are unchanged. Muzzle and launcher emitters follow their owning joint. Energy
apertures are unlit.

GpuBuildingTurretSmokeTest records complete assembly counts in `turret-palette-counts.csv` in
its screenshot folder.
Capacities: the roof holds two exposed guns (a third moves into a front bay); the
pillar holds four arm launchers and one roof launcher; a broad head holds one launcher per
flank plus up to four roof launchers when no gun is on the roof. Further launchers sit 75%
encased in front bays. The lower auxiliary mounts remain available.
Dense batteries exceed the initial
5,000/2,000 target. LOD2 reuses LOD1. Gun emplacements and armed advanced buildings select
this recipe through mekset.txt's `default_turret`; their generic model is the fallback for a
loadout without authored profiles.
