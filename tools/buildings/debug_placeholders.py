"""Flat, colour-coded standard kits, laid out as the light building's spec.

Run with Python (standard library only): python tools/buildings/debug_placeholders.py
The existing light building, light fortress and lunar habitat are not overwritten.
Panel index 0..5 is red, orange, yellow, green, cyan, violet. Alternate base/floor
modules use lighter shades. Roof slabs are yellow; floors/sidewalks are grey.
The separate two-hex authored slicing demo is built in Blender by debug_authored.py.
"""
import copy
import json
import struct
import sys
import uuid
import zlib
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import kit_json
from glb_geometry import write_glb

DATA = TOOLS.parent / 'data'
BUILDINGS = DATA / 'models/buildings'
COLOURS = [(0.90, 0.20, 0.18), (1.0, 0.48, 0.10), (0.96, 0.82, 0.15),
           (0.18, 0.72, 0.28), (0.12, 0.68, 0.90), (0.64, 0.28, 0.88)]


def box(mesh, start, end, colour):
    """Closed, flat-shaded panel; winding is outward, in the writer's Z-up frame."""
    x0, y0, z0 = start
    x1, y1, z1 = end
    faces = [((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
             ((0, 1, 0), [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)]),
             ((-1, 0, 0), [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)]),
             ((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]),
             ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
             ((0, 0, -1), [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)])]
    for normal, corners in faces:
        first = len(mesh['vertices']) // 12
        for point, uv in zip(corners, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            mesh['vertices'].extend([*point, *normal, *colour, 1, *uv])
        mesh['parts'][0]['indices'].extend(first + i for i in (0, 1, 2, 0, 2, 3))


def geometry(name):
    return {'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': [],
            'parts': [{'id': name, 'type': 'TRIANGLES', 'indices': []}]}


def node(name, part, position=(0, 0, 0)):
    return {'id': name, 'translation': list(position),
            'parts': [{'meshpartid': part, 'materialid': 'structures/buildings/debug-panels'}]}


def model(meshes, nodes):
    return {'meshes': meshes, 'nodes': nodes,
            'materials': [{'id': 'structures/buildings/debug-panels', 'diffuse': [1, 1, 1], 'roughness': 1, 'metallic': 0,
                           'extras': {'mmBuildingPaint': True},
                           'textures': [{'type': 'DIFFUSE',
                                         'filename': '../../board/textures/structures/buildings/debug-panels_albedo.png'}]}]}


def panels(path):
    meshes, nodes = [], []
    for row, role in enumerate(('base0', 'base1', 'floor0', 'floor1', 'roof0')):
        for index, colour in enumerate(COLOURS):
            name = f'{role}-bay{index}-lod0'
            mesh = geometry(name)
            tint = tuple(c + (1 - c) * .22 for c in colour) if role.endswith('1') else colour
            box(mesh, (0, 0, 0), (24, 1.25, 1 if role == 'roof0' else 18), tint)
            meshes.append(mesh)
            nodes.append(node(name, name, (index * 30, row * 25, 0)))
    write_glb(path, levels={0: model(meshes, nodes)})


def main():
    # A board material's albedo identifies it, so each has its own image; one white pixel keeps the diagnostic
    # colours flat. Authored buildings' flat GLB materials use debug-white.png, which belongs to no material.
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 1, 1, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff\xff')) + chunk(b'IEND', b'')
    for image in ('debug-white', 'debug-floor_albedo', 'debug-panels_albedo', 'debug-roof_albedo'):
        (DATA / f'models/board/textures/structures/buildings/{image}.png').write_bytes(png)
    folder = BUILDINGS / 'standard'
    template = json.loads((folder / 'building-light.json').read_text())
    paths = []
    for family in ('building', 'fortress', 'gun-emplacement', 'hangar'):
        for weight in ('civilian', 'light', 'medium', 'heavy', 'hard', 'castle-brian'):
            # Finished kits: the light building and fortress, and the four hangars of the rules' weights (hangar_kits.py).
            if weight in ('light', 'medium', 'heavy', 'hard') and (family == 'hangar'
                                                                 or weight == 'light' and family in ('building', 'fortress')):
                continue
            name = f'{family}-{weight}'
            spec = copy.deepcopy(template)
            spec['pieces'] = f'{name}-pieces.glb'
            # A single flat LOD is sufficient for these diagnostic panels.
            for roof in spec['roofs'].values():
                roof['material'] = 'structures/buildings/debug-roof'
                roof['heights'] = roof['heights'][:1]
            for variant in spec['variants']:
                variant['floors']['material'] = 'structures/buildings/debug-floor'
                variant['floors']['inset'] = 0.6  # Meet the 1.25-unit solid panels.
                variant['floors']['heights'] = variant['floors']['heights'][:1]
                variant['sidewalk']['material'] = 'structures/buildings/debug-floor'
            for part in (*spec['roofs'].values(), *spec['variants']):
                for role in ('runs', *kit_json.ROLES):
                    for run in part.get(role, ()):
                        run.pop('far', None)
            (folder / f'{name}.json').write_text(kit_json.dumps(spec) + '\n', encoding='utf-8')
            panels(folder / f'{name}-pieces.glb')
            paths.append(f'buildings/standard/{name}')
    paths.append('buildings/debug/debug-authored')
    # Asset IDs are assigned once, never regenerated when a kit is rebuilt.
    index_path = DATA / 'models/board/uids.json'
    index = json.loads(index_path.read_text())
    registered = set(index.values())
    for path in paths + ['buildings/standard/building-light', 'buildings/standard/fortress-light',
                         'buildings/lunar_habitat/lunar_habitat']:
        if path in registered:
            continue
        identity = uuid.uuid4().hex[:8]
        while identity in index:
            identity = uuid.uuid4().hex[:8]
        index[identity] = path
        registered.add(path)
    index_path.write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'kits': paths, 'panelsPerKit': 30, 'trianglesPerPanel': 12}, indent=2))


if __name__ == '__main__':
    main()
