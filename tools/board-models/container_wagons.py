"""Loads the container wagons with the yard's own containers (scenery/seaport/yard/container): the wagon as it was
first made, without the plain boxes it carried, and two containers on its deck, each in a colour slot of its own.

Run: python container_wagons.py     (standard library only; the first wagons come from the commit below)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from glb_geometry import read_glb, write_glb

REPO = TOOLS.parent
BOARD = REPO/'data/models/board'
FIRST = '002cda1be9'  # The last commit that held the wagons with their boxes.
STRIDE = 12  # POSITION 3, NORMAL 3, COLOR 4, TEXCOORD0 2.
# wagon: (its boxes' slots, its deck's height, the two containers' places along it, their slots as (number, name, colour))
WAGONS = {'scenery/rail/container-wagon': ((2,), 4.4, (-7.3, 7.3), ((2, 'Container 1', '#d6ccab'), (3, 'Container 2', '#783b3b'))),
          'scenery/maglev/colony-containers': ((1, 2), 5.0, (-7.4, 7.4), ((1, 'Container 1', '#243357'), (2, 'Container 2', '#dbd1b2')))}


def colour(text):
    return [int(text[i:i+2], 16)/255 for i in (1, 3, 5)]


def first(path, level):
    """A wagon's level as the first commit held it."""
    data = subprocess.run(['git', '-C', str(REPO), 'show', f'{FIRST}:data/models/board/{path}.glb'], capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory() as folder:
        file = Path(folder)/(path.split('/')[-1]+'.glb')
        file.write_bytes(data)
        return read_glb(file, level=level)


def without(mesh, slots, above):
    """The mesh without the triangles that belong wholly to these slots above the deck."""
    for part in mesh['parts']:
        kept = []
        for i in range(0, len(part['indices']), 3):
            triangle = part['indices'][i:i+3]
            if not all(mesh['slots'][v] in slots and mesh['vertices'][v*STRIDE+2] >= above-.01 for v in triangle):
                kept.extend(triangle)
        part['indices'] = kept
    return mesh


def placed(container, tag, y, z, half_turn, slot, tint, own):
    """The container's mesh at its place on the deck, its paint in the wagon's slot and that slot's colour."""
    meshes, parts = [], []
    for mesh in container['meshes']:
        vertices = list(mesh['vertices'])
        for v in range(len(vertices)//STRIDE):
            base = v*STRIDE
            sign = -1 if half_turn else 1
            vertices[base], vertices[base+1], vertices[base+2] = sign*vertices[base], sign*vertices[base+1]+y, vertices[base+2]+z
            vertices[base+3], vertices[base+4] = sign*vertices[base+3], sign*vertices[base+4]
            if mesh['slots'][v]:
                for k in range(3):
                    vertices[base+6+k] = min(1.0, vertices[base+6+k]*tint[k]/own[k])
        renamed = [{**part, 'id': f"{part['id']}-{tag}"} for part in mesh['parts']]
        meshes.append({'attributes': mesh['attributes'], 'vertices': vertices, 'parts': renamed, 'slots': [slot if s else 0 for s in mesh['slots']]})
    for node in container['nodes']:
        parts += [{'meshpartid': f"{part['meshpartid']}-{tag}", 'materialid': part['materialid']} for part in node['parts']]
    return meshes, parts


def load(path):
    drop, deck, places, slots = WAGONS[path]
    depth = '../'*(len(path.split('/'))-1)
    levels = {}
    for level in (0, 1):
        wagon = first(path, level)
        container = read_glb(BOARD/'scenery/seaport/yard/container.glb', level=level)
        own = colour(container['extras']['mmColourSlots'][0]['colour'])
        presets = container['extras']['mmColourSlots'][0]['presets']
        meshes = [without(mesh, drop, deck) for mesh in wagon['meshes']]
        node = wagon['nodes'][0]
        for index, (y, (slot, _, tint)) in enumerate(zip(places, slots)):
            more, parts = placed(container, 'ab'[index], y, deck, index == 1, slot, colour(tint), own)
            meshes += more
            node['parts'] += parts
        materials = list(wagon['materials'])
        for material in container['materials']:
            if any(part['materialid'] == material['id'] for part in node['parts']):
                for texture in material.get('textures', ()):
                    texture['filename'] = texture['filename'].replace('../../../textures/', depth+'textures/')
                materials.append(material)
        kept = [entry for number, entry in enumerate(wagon['extras']['mmColourSlots'], 1) if number not in [slot for slot, _, _ in slots]]
        defined = {number: entry for number, entry in enumerate(wagon['extras']['mmColourSlots'], 1) if entry in kept}
        for slot, name, tint in slots:
            defined[slot] = {'name': name, 'colour': tint, 'presets': presets}
        extras = {**wagon['extras'], 'mmColourSlots': [defined[number] for number in sorted(defined)]}
        assert sorted(defined) == list(range(1, len(defined)+1)), defined.keys()
        levels[level] = {'id': wagon['id'], 'meshes': meshes, 'nodes': [node], 'materials': materials}
    write_glb(BOARD/(path+'.glb'), levels=levels, extras=extras)
    print(path, [sum(len(part['indices'])//3 for mesh in level['meshes'] for part in mesh['parts']) for level in levels.values()],
          [entry['name'] for entry in extras['mmColourSlots']])


if __name__ == '__main__':
    for wagon in WAGONS:
        load(wagon)
