"""Gives the board models that were only vertex-coloured (a flat `scenery` or `machinery` material) the board's own
materials, by the colour each face was painted: glass for the blues, cast concrete for a roof's pale masonry, weathered
paint for the rest. Shapes, UVs, tints and colour slots stay as they were.

Run: python rematerial.py     (standard library only; every listed file, each of its levels; a file already done is left alone)
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from glb_geometry import read_glb, write_glb

BOARD = TOOLS.parent/'data/models/board'
TEXTURES = BOARD/'textures'
STRIDE = 12  # POSITION 3, NORMAL 3, COLOR 4, TEXCOORD0 2.
FLAT = ('scenery', 'machinery')
PAINT, CONCRETE = 'structures/common/weathered-paint', 'structures/common/cast-concrete'
ROOF_GLASS = CAB_GLASS = 'structures/common/reflective-glass'  # Opaque, mirroring the sky.


def blue(colour):
    return colour[2] > colour[0]*1.3 and colour[2] > colour[1]*1.05


def pale(colour):
    return min(colour) > .5 and max(colour)-min(colour) < .1


# file: the material of a face by its colour.
FILES = {**{f'scenery/seaport/yard/{name}': lambda c: CAB_GLASS if blue(c) else PAINT
            for name in ('crane-boom', 'yard-gantry', 'yard-gantry-tall', 'quay-crane', 'yard-truck')},
         **{f'scenery/roofs/{name}': lambda c: ROOF_GLASS if blue(c) else CONCRETE if pale(c) else PAINT
            for name in ('bevel', 'skylight', 'glass-dome', 'glass-roof-wide')},
         'scenery/roofs/ledge': lambda c: CONCRETE,
         'scenery/maglev/platform': lambda c: ROOF_GLASS if blue(c) else CONCRETE if pale(c) else PAINT}


def material(key, depth):
    """A board material as the generators write it: the maps its folder holds."""
    textures = []
    for kind, suffix in (('DIFFUSE', 'albedo'), ('NORMAL', 'normal'), ('AMBIENT', 'orm'), ('METALLIC_ROUGHNESS', 'orm')):
        if (TEXTURES/f'{key}_{suffix}.png').is_file():
            textures.append({'id': key, 'type': kind, 'filename': f'{depth}textures/{key}_{suffix}.png', 'wrapS': 10497, 'wrapT': 10497,
                             'minFilter': 9987, 'magFilter': 9729})
    assert textures and textures[0]['type'] == 'DIFFUSE', key
    return {'id': key, 'diffuse': [1.0, 1.0, 1.0], 'roughness': 1.0, 'metallic': 1.0, 'textures': textures}


def remake(path, rule):
    depth = '../'*(len(path.split('/'))-1)
    levels, changed = {}, False
    for level in range(4):
        try:
            model = read_glb(BOARD/(path+'.glb'), level=level)
        except (KeyError, IndexError, ValueError):
            break  # No further level.
        node = model['nodes'][0]
        used = {}
        for mesh in model['meshes']:
            parts = []
            for part in mesh['parts']:
                owner = next(entry['materialid'] for entry in node['parts'] if entry['meshpartid'] == part['id'])
                if owner not in FLAT:
                    parts.append(part)
                    continue
                changed = True
                split = {}
                for i in range(0, len(part['indices']), 3):
                    triangle = part['indices'][i:i+3]
                    colour = mesh['vertices'][triangle[0]*STRIDE+6:triangle[0]*STRIDE+9]
                    split.setdefault(rule(colour), []).extend(triangle)
                for index in split.get(ROOF_GLASS, ()):  # The glass has its own colour: the blue it was painted would darken it.
                    mesh['vertices'][index*STRIDE+6:index*STRIDE+9] = [1.0, 1.0, 1.0]
                node['parts'] = [entry for entry in node['parts'] if entry['meshpartid'] != part['id']]
                for key, indices in split.items():
                    name = f"{part['id']}-{key.split('/')[-1]}"
                    parts.append({**part, 'id': name, 'indices': indices})
                    node['parts'].append({'meshpartid': name, 'materialid': key})
                    used[key] = material(key, depth)
            mesh['parts'] = parts
        model['materials'] = [entry for entry in model['materials'] if entry['id'] not in FLAT]+list(used.values())
        levels[level] = model
    if changed:
        write_glb(BOARD/(path+'.glb'), levels=levels, extras=levels[0].get('extras'))
    print(path, 'done' if changed else 'unchanged', sorted({entry['materialid'] for level in levels.values() for entry in level['nodes'][0]['parts']}))


if __name__ == '__main__':
    for file, by_colour in FILES.items():
        remake(file, by_colour)
