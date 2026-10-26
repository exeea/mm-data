# Modular turret GLBs

Six weaponless heads, two wall casemates (`head-casemate`, `-twin`) and 154 weapon modules/installation
variants. Each GLB contains
`-lod0` and `-lod1` groups. Armor plates and covers are the unit `paint` role on the painted steel
plate `structures/turret/turret-paint`: the player's camouflage paints them, shaded by the plate's light
and dark over its satin metal finish; without camouflage the plate itself shows. Mechanical parts, gun
steel and worn bevels are the board materials `structures/turret/turret-dark`, `structures/common/steel` and
`structures/turret/turret-edge` (Material Maker projects in `tools/materials/structures`): a GLB references only the
albedo map, and the `.tres` beside it gives the finish and normal map. Draw one LOD at a time.
The adjacent schema 2 JSON describes bounds, joints, hardpoints and effect emitters.

| GLB | LOD0 triangles | LOD1 triangles |
| --- | ---: | ---: |
| `arrow-iv-arm-left.glb` | 1,800 | 672 |
| `arrow-iv-arm-right.glb` | 1,800 | 672 |
| `arrow-iv-pod.glb` | 1,720 | 692 |
| `arrow-iv.glb` | 1,156 | 508 |
| `artillery-exposed.glb` | 4,532 | 908 |
| `artillery-heavy-exposed.glb` | 4,492 | 908 |
| `artillery-heavy.glb` | 1,752 | 340 |
| `artillery-light-exposed.glb` | 4,540 | 908 |
| `artillery-light.glb` | 1,752 | 340 |
| `artillery.glb` | 1,752 | 340 |
| `atm-12-arm-left.glb` | 2,264 | 848 |
| `atm-12-arm-right.glb` | 2,264 | 848 |
| `atm-12-pod.glb` | 2,184 | 868 |
| `atm-12.glb` | 1,620 | 684 |
| `atm-3-arm-left.glb` | 1,742 | 650 |
| `atm-3-arm-right.glb` | 1,742 | 650 |
| `atm-3-pod.glb` | 1,662 | 670 |
| `atm-3.glb` | 1,098 | 486 |
| `atm-6-arm-left.glb` | 1,916 | 716 |
| `atm-6-arm-right.glb` | 1,916 | 716 |
| `atm-6-pod.glb` | 1,836 | 736 |
| `atm-6.glb` | 1,272 | 552 |
| `atm-9-arm-left.glb` | 2,090 | 782 |
| `atm-9-arm-right.glb` | 2,090 | 782 |
| `atm-9-pod.glb` | 2,010 | 802 |
| `atm-9.glb` | 1,446 | 618 |
| `autocannon-10-exposed.glb` | 4,592 | 860 |
| `autocannon-10.glb` | 1,792 | 292 |
| `autocannon-2-exposed.glb` | 4,656 | 860 |
| `autocannon-2.glb` | 1,792 | 292 |
| `autocannon-20-exposed.glb` | 4,180 | 860 |
| `autocannon-20.glb` | 1,440 | 292 |
| `autocannon-5-exposed.glb` | 4,632 | 860 |
| `autocannon-5.glb` | 1,792 | 292 |
| `autocannon-compact-exposed.glb` | 3,676 | 820 |
| `autocannon-compact.glb` | 592 | 224 |
| `flamer-exposed.glb` | 1,532 | 664 |
| `flamer-heavy-exposed.glb` | 1,532 | 664 |
| `flamer-heavy.glb` | 588 | 188 |
| `flamer.glb` | 588 | 188 |
| `gauss-exposed.glb` | 4,356 | 1,136 |
| `gauss-heavy-exposed.glb` | 3,988 | 1,076 |
| `gauss-heavy.glb` | 1,756 | 496 |
| `gauss-light-exposed.glb` | 4,488 | 1,152 |
| `gauss-light.glb` | 2,084 | 556 |
| `gauss.glb` | 2,084 | 556 |
| `hag-20-exposed.glb` | 3,952 | 1,068 |
| `hag-20.glb` | 1,572 | 488 |
| `hag-30-exposed.glb` | 4,068 | 1,096 |
| `hag-30.glb` | 1,704 | 516 |
| `hag-40-exposed.glb` | 3,752 | 1,096 |
| `hag-40.glb` | 1,480 | 516 |
| `head-casemate-twin.glb` | 400 | 224 |
| `head-casemate.glb` | 358 | 210 |
| `head-center.glb` | 3,332 | 1,148 |
| `head-mixed.glb` | 3,416 | 1,176 |
| `head-pillar.glb` | 2,984 | 1,024 |
| `head-pods.glb` | 3,246 | 1,106 |
| `head-shoulder.glb` | 3,784 | 1,404 |
| `head-twin.glb` | 3,330 | 1,134 |
| `laser-large-exposed.glb` | 1,462 | 574 |
| `laser-large.glb` | 954 | 358 |
| `laser-medium-exposed.glb` | 1,462 | 574 |
| `laser-medium.glb` | 954 | 358 |
| `laser-small-exposed.glb` | 1,462 | 574 |
| `laser-small.glb` | 954 | 358 |
| `lrm-10-arm-left.glb` | 2,148 | 804 |
| `lrm-10-arm-right.glb` | 2,148 | 804 |
| `lrm-10-pod.glb` | 2,068 | 824 |
| `lrm-10.glb` | 1,504 | 640 |
| `lrm-15-arm-left.glb` | 2,438 | 914 |
| `lrm-15-arm-right.glb` | 2,438 | 914 |
| `lrm-15-pod.glb` | 2,358 | 934 |
| `lrm-15.glb` | 1,794 | 750 |
| `lrm-20-arm-left.glb` | 2,728 | 1,024 |
| `lrm-20-arm-right.glb` | 2,728 | 1,024 |
| `lrm-20-pod.glb` | 2,648 | 1,044 |
| `lrm-20.glb` | 2,084 | 860 |
| `lrm-5-arm-left.glb` | 1,858 | 694 |
| `lrm-5-arm-right.glb` | 1,858 | 694 |
| `lrm-5-pod.glb` | 1,778 | 714 |
| `lrm-5.glb` | 1,214 | 530 |
| `machine-gun-exposed.glb` | 1,136 | 564 |
| `machine-gun.glb` | 124 | 56 |
| `mml-3-arm-left.glb` | 1,742 | 650 |
| `mml-3-arm-right.glb` | 1,742 | 650 |
| `mml-3-pod.glb` | 1,662 | 670 |
| `mml-3.glb` | 1,098 | 486 |
| `mml-5-arm-left.glb` | 1,858 | 694 |
| `mml-5-arm-right.glb` | 1,858 | 694 |
| `mml-5-pod.glb` | 1,778 | 714 |
| `mml-5.glb` | 1,214 | 530 |
| `mml-7-arm-left.glb` | 1,974 | 738 |
| `mml-7-arm-right.glb` | 1,974 | 738 |
| `mml-7-pod.glb` | 1,894 | 758 |
| `mml-7.glb` | 1,330 | 574 |
| `mml-9-arm-left.glb` | 2,090 | 782 |
| `mml-9-arm-right.glb` | 2,090 | 782 |
| `mml-9-pod.glb` | 2,010 | 802 |
| `mml-9.glb` | 1,446 | 618 |
| `mortar-1-arm-left.glb` | 1,514 | 606 |
| `mortar-1-arm-right.glb` | 1,514 | 606 |
| `mortar-1-pod.glb` | 1,434 | 626 |
| `mortar-1.glb` | 870 | 442 |
| `mortar-2-arm-left.glb` | 1,572 | 628 |
| `mortar-2-arm-right.glb` | 1,572 | 628 |
| `mortar-2-pod.glb` | 1,492 | 648 |
| `mortar-2.glb` | 928 | 464 |
| `mortar-4-arm-left.glb` | 1,688 | 672 |
| `mortar-4-arm-right.glb` | 1,688 | 672 |
| `mortar-4-pod.glb` | 1,608 | 692 |
| `mortar-4.glb` | 1,044 | 508 |
| `mortar-8-arm-left.glb` | 1,920 | 760 |
| `mortar-8-arm-right.glb` | 1,920 | 760 |
| `mortar-8-pod.glb` | 1,840 | 780 |
| `mortar-8.glb` | 1,276 | 596 |
| `mrm-10-arm-left.glb` | 2,148 | 804 |
| `mrm-10-arm-right.glb` | 2,148 | 804 |
| `mrm-10-pod.glb` | 2,068 | 824 |
| `mrm-10.glb` | 1,504 | 640 |
| `mrm-20-arm-left.glb` | 2,728 | 1,024 |
| `mrm-20-arm-right.glb` | 2,728 | 1,024 |
| `mrm-20-pod.glb` | 2,648 | 1,044 |
| `mrm-20.glb` | 2,084 | 860 |
| `mrm-30-arm-left.glb` | 3,308 | 1,244 |
| `mrm-30-arm-right.glb` | 3,308 | 1,244 |
| `mrm-30-pod.glb` | 3,228 | 1,264 |
| `mrm-30.glb` | 2,664 | 1,080 |
| `mrm-40-arm-left.glb` | 3,888 | 1,464 |
| `mrm-40-arm-right.glb` | 3,888 | 1,464 |
| `mrm-40-pod.glb` | 3,808 | 1,484 |
| `mrm-40.glb` | 3,244 | 1,300 |
| `plasma-cannon-exposed.glb` | 3,656 | 984 |
| `plasma-cannon.glb` | 1,016 | 312 |
| `plasma-rifle-exposed.glb` | 3,568 | 984 |
| `plasma-rifle.glb` | 904 | 312 |
| `ppc-exposed.glb` | 4,976 | 944 |
| `ppc-heavy-exposed.glb` | 5,160 | 960 |
| `ppc-heavy.glb` | 2,488 | 272 |
| `ppc-light-exposed.glb` | 4,560 | 944 |
| `ppc-light.glb` | 1,848 | 272 |
| `ppc.glb` | 2,328 | 272 |
| `rotary-2-exposed.glb` | 4,212 | 1,228 |
| `rotary-2.glb` | 1,380 | 660 |
| `rotary-5-exposed.glb` | 4,164 | 1,228 |
| `rotary-5.glb` | 1,380 | 660 |
| `srm-2-arm-left.glb` | 1,684 | 628 |
| `srm-2-arm-right.glb` | 1,684 | 628 |
| `srm-2-pod.glb` | 1,604 | 648 |
| `srm-2.glb` | 1,040 | 464 |
| `srm-4-arm-left.glb` | 1,800 | 672 |
| `srm-4-arm-right.glb` | 1,800 | 672 |
| `srm-4-pod.glb` | 1,720 | 692 |
| `srm-4.glb` | 1,156 | 508 |
| `srm-6-arm-left.glb` | 1,916 | 716 |
| `srm-6-arm-right.glb` | 1,916 | 716 |
| `srm-6-pod.glb` | 1,836 | 736 |
| `srm-6.glb` | 1,272 | 552 |
| `thunderbolt-arm-left.glb` | 1,626 | 606 |
| `thunderbolt-arm-right.glb` | 1,626 | 606 |
| `thunderbolt-pod.glb` | 1,546 | 626 |
| `thunderbolt.glb` | 982 | 442 |

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

All supported families have a complete exposed installation: `encased: false`
selects `turret-exposed`. Guns use substantial shoulder supports with protected
ammunition/power feeds through their side bearings; missiles use roof-seated cradles.
Autocannon receivers ride on two armored trunnion cheeks with an armored feed chute into
the right bearing, recuperators and a recoil clamp; PPCs ride on the same cheeks with a power duct, a capacitor housing, arching power
cables and a radiator-finned accelerator; MG receivers include feed couplings; laser/PPC
modules expose their power/cooling bodies. Artillery and rotary cannons use the autocannon
receivers and cheeks; Gauss rifles and HAGs ride the PPC's capacitor housing and power-duct cheeks with the
autocannon mantlet in front bays; plasma weapons use the PPC housings and flamers the MG receiver. No front carrier plates are used for these
external weapons. `encased: true` uses an armored front bay; the stacked shoulder
head has deep receiver housings behind its upper panels.

Launchers default to exposed. Exposed launchers ride side arms (`-arm-left/-right.glb`, each
module carries its own arm and trunnion) on the thin `head-pillar` (two, or four stacked)
or one per flank of a broad head; a lone launcher sits on the roof yoke (`-pod.glb`).
Encased, a standard cassette sits 75% inside a bay. Other weapons default to
the front bay and allow adjustable numeric insertion; their complete external
variants end in `-exposed.glb`. Zero insertion means flush with the bay, not an
external installation. Rack layouts and emitter spacing remain unchanged.
An external mount cannot be inserted into a bay. Its `elevation` joint turns about
local X, with a visual -20/+25 degree stop, while the turret bearing provides yaw.
Any mix assembles: front weapons fill bays by count, exposed guns ride roof cradles
(depression stops at 6 degrees above front bays), launchers take side arms, and what a
carrier cannot hold moves into front bays. Cannons/MGs have separate barrel/breech
recoil joints; their receivers and cradles stay fixed during recoil. Laser, PPC,
plasma, flamer and launcher modules have no mechanical recoil.
Muzzle and launcher emitters follow their owning joint. Energy apertures are unlit.

Complete assembly counts are recorded in the authoring kit's
`renders/turret-palette-counts.csv`.
Capacities: roof cradles hold two exposed guns (a third moves into a front bay); the
pillar holds four arm launchers and one roof yoke; a broad head holds one launcher per
flank plus up to four roof yokes when no gun is on the roof. Further launchers sit 75%
encased in front bays. The lower auxiliary mounts remain available.
Dense batteries exceed the initial
5,000/2,000 target. LOD2 reuses LOD1. Gun emplacements and advanced buildings with
turret-mounted weapons select this recipe through mekset.txt's `default_turret`; their
generic model is the fallback for a loadout without authored profiles.
