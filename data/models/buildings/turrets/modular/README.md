# Modular turret GLBs

Six weaponless heads and fifty-two weapon modules/installation variants. Each GLB contains
`-lod0` and `-lod1` groups. Their textured materials are the board materials
`structures/turret/turret-armor`, `-dark`, `-steel`, `-edge` and `-pale` (Material Maker projects in
`tools/materials/structures/turret`): a GLB references only the albedo map, and the `.tres` beside
it gives the tint, finish and normal map. Draw one LOD at a time.
The adjacent schema 2 JSON describes bounds, joints, hardpoints and effect emitters.

| GLB | LOD0 triangles | LOD1 triangles |
| --- | ---: | ---: |
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
| `ppc-exposed.glb` | 4,976 | 944 |
| `ppc-heavy-exposed.glb` | 5,160 | 960 |
| `ppc-heavy.glb` | 2,488 | 272 |
| `ppc-light-exposed.glb` | 4,560 | 944 |
| `ppc-light.glb` | 1,848 | 272 |
| `ppc.glb` | 2,328 | 272 |
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

The fixed collar belongs to the head. Head mounting datum is glTF Y=0, with a 0.45-unit underside
embed. Authoring/JSON coordinates are Z-up and +Y forward; exported glTF is Y-up and
-Z forward. The loader converts once.

`turret.json` is an explicit assembly recipe. The shared equipment catalogue has
331 optional turret-profile mappings covering AC, MG, laser, PPC,
LRM 5/10/15/20 and SRM 2/4/6. Autocannons map by rack size to four calibre tiers
(`autocannon-2/5/10/20`): longer, slimmer barrels for light calibres, shorter and wider
bores for heavy ones; crowded heads use `autocannon-compact`. PPCs map by name to light
(light, snub-nose, support), standard and heavy tiers (`ppc-light`, `ppc`, `ppc-heavy`).
The other families share one mesh per size, not bespoke meshes for every subtype. Gauss, rotary cannons and other unsupported families
retain the previous model path. Existing Mek/vehicle defaults are unchanged.

All supported families have a complete exposed installation: `encased: false`
selects `turret-exposed`. Guns use substantial shoulder supports with protected
ammunition/power feeds through their side bearings; missiles use roof-seated cradles.
Autocannon receivers ride on two armored trunnion cheeks with an armored feed chute into
the right bearing, recuperators and a recoil clamp; PPCs ride on the same cheeks with a power duct, a capacitor housing, arching power
cables and a radiator-finned accelerator; MG receivers include feed couplings; laser/PPC
modules expose their power/cooling bodies. No front carrier plates are used for these
external weapons. `encased: true` uses an armored front bay; the stacked shoulder
head has deep receiver housings behind its upper panels.

SRM/LRM default to exposed. Exposed launchers ride side arms (`-arm-left/-right.glb`, each
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
recoil joints; their receivers and cradles stay fixed during recoil. Laser/PPC/
launcher modules have no mechanical recoil.
Muzzle and launcher emitters follow their owning joint. Energy apertures are unlit.

Complete assembly counts are recorded in the authoring kit's
`renders/turret-palette-counts.csv`.
Capacities: roof cradles hold two exposed guns (a third moves into a front bay); the
pillar holds four arm launchers and one roof yoke; a broad head holds one launcher per
flank plus up to four roof yokes when no gun is on the roof. Further launchers sit 75%
encased in front bays. The lower auxiliary mounts remain available.
Dense batteries exceed the initial
5,000/2,000 target. LOD2 reuses LOD1. Automatic gameplay selection and wall/support
placement are not yet connected to this recipe.
