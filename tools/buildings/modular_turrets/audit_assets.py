"""Audit exported GLBs and reproduce the shipped geometry/coverage report."""
import collections
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASSETS = ROOT / 'data/models/buildings/turrets/modular'


def inspect(path):
    raw = path.read_bytes()
    assert raw[:4] == b'glTF'
    length = struct.unpack_from('<I', raw, 12)[0]
    data = json.loads(raw[20:20 + length])
    # Every image is a board material's albedo map, referenced beside its .tres, never embedded.
    albedos = set()
    for image in data.get('images', []):
        assert 'bufferView' not in image, path
        albedo = (path.parent / image['uri']).resolve()
        assert albedo.name.endswith('_albedo.png') and albedo.is_file(), (path, image['uri'])
        assert albedo.with_name(albedo.name[:-len('_albedo.png')] + '.tres').is_file(), (path, image['uri'])
        albedos.add(albedo.name)
    assert all('uri' not in buffer for buffer in data['buffers'])

    def triangles(index):
        node = data['nodes'][index]
        count = sum(triangles(child) for child in node.get('children', []))
        if 'mesh' in node:
            for part in data['meshes'][node['mesh']]['primitives']:
                assert part.get('mode', 4) == 4
                count += data['accessors'][part['indices']]['count'] // 3
        return count

    counts = []
    for lod in (0, 1):
        roots = [i for i, node in enumerate(data['nodes']) if node.get('name', '').endswith(f'-lod{lod}')]
        assert len(roots) == 1, (path, lod, roots)
        counts.append(triangles(roots[0]))
    assert counts[1] < counts[0]
    assert all(not material.get('doubleSided', False) for material in data.get('materials', []))
    return {'triangles': counts, 'albedoMaps': sorted(albedos), 'bytes': len(raw)}


def run():
    geometry = {path.stem: inspect(path) for path in sorted(ASSETS.glob('*.glb'))}
    assert len(geometry) == 63
    expected = json.loads((HERE / 'geometry.json').read_text())
    assert all(value['triangles'] == expected[name] for name, value in geometry.items())
    catalogue = json.loads((ROOT / 'data/models/units/modular/equipment.json').read_text())['equipment']
    covered = collections.Counter()
    for internal_name, item in catalogue.items():
        profile = item.get('profiles', {}).get('turret')
        if profile:
            covered[Path(profile).stem] += 1
            for role, asset in item['profiles'].items():
                if role.startswith('turret'):
                    assert (ROOT / 'data/models' / asset).is_file(), (internal_name, role)
    rows = '\n'.join(f'| `{name}.glb` | {v["triangles"][0]:,} | {v["triangles"][1]:,} |'
                     for name, v in geometry.items())
    readme = f'''# Modular turret GLBs

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
{rows}

The fixed collar belongs to the head. Head mounting datum is glTF Y=0, with a 0.45-unit underside
embed. Authoring/JSON coordinates are Z-up and +Y forward; exported glTF is Y-up and
-Z forward. The loader converts once.

`turret.json` is an explicit assembly recipe. The shared equipment catalogue has
{sum(covered.values())} optional turret-profile mappings (`tools/modular_turret_profiles.py`). The Mek weapon
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
'''
    (ASSETS / 'README.md').write_text(readme, encoding='utf-8')
    print(json.dumps({'assets': len(geometry), 'profiles': sum(covered.values()),
                      'albedoMaps': sorted({name for item in geometry.values() for name in item['albedoMaps']}),
                      'megabytes': round(sum(item['bytes'] for item in geometry.values()) / 1e6, 1)}))


if __name__ == '__main__':
    run()
