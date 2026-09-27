"""Run in Blender after :megamek:exportBridgeShapes. Bake one complete bridge per exit mask.

Curves and junction outlines come from BoardRoad, not a second Python path algorithm.
Each GLB has a single LOD0 group and references the shared road/concrete textures.
"""
from pathlib import Path
import json
import math
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_geometry import write_glb
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


def inside(point, loops):
    x, y = point
    result = False
    for loop in loops:
        for a, b in zip(loop, loop[1:] + loop[:1]):
            if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0]) * (y-a[1]) / (b[1]-a[1]) + a[0]:
                result = not result
    return result


def triangles(loops):
    points, edges = [], []
    for loop in loops:
        start = len(points)
        points.extend(Vector(p) for p in loop)
        edges.extend((start+i, start+(i+1) % len(loop)) for i in range(len(loop)))
    points, _, faces, *_ = delaunay_2d_cdt(points, edges, [], 1, 1e-5)
    for face in faces:
        a, b, c = (points[i] for i in face)
        if not inside((a+b+c)/3, loops):
            continue
        cross = (b.x-a.x)*(c.y-a.y) - (b.y-a.y)*(c.x-a.x)
        if abs(cross) > 1e-7:
            yield (a, b, c) if cross > 0 else (a, c, b)


def build(root):
    out = root / 'data/models/board'
    shapes = json.loads((root / 'tools/board-models/bridge-shapes.json').read_text())
    assert sorted(shape['exits'] for shape in shapes) == list(range(64))
    stats = {}
    for shape in shapes:
        packed, unique = [], {}
        parts = {'bridge-deck': [], 'bridge-structure': []}
        repeat = 84 / 5

        def vertex(p, z, normal, uv, role):
            value = tuple(round(v, 6) for v in (p[0], p[1], z, *normal, 1, 1, 1, 1, *uv))
            if value not in unique:
                unique[value] = len(packed) // 12
                packed.extend(value)
            parts[role].append(unique[value])

        def cap(loops, z, up, role):
            for face in triangles(loops):
                for p in face if up else face[::-1]:
                    vertex(p, z, (0, 0, 1 if up else -1), (p[0]/repeat, -p[1]/repeat), role)

        def walls(loops, low, high):
            for loop in loops:
                distance = 0
                for a, b in zip(loop, loop[1:] + loop[:1]):
                    dx, dy = b[0]-a[0], b[1]-a[1]
                    length = math.hypot(dx, dy)
                    if length < 1e-5:
                        continue
                    normal = (-dy/length, dx/length, 0)
                    points = [(a, low, distance), (a, high, distance),
                              (b, high, distance+length), (b, low, distance+length)]
                    for i in (0, 1, 2, 0, 2, 3):
                        p, z, u = points[i]
                        vertex(p, z, normal, (u/repeat, -z/repeat), 'bridge-structure')
                    distance += length

        cap(shape['deck'], 0, True, 'bridge-deck')
        cap(shape['slab'], -1.5, False, 'bridge-structure')
        walls(shape['slab'], -1.5, 0)
        cap(shape['rails'], 2.5, True, 'bridge-structure')
        walls(shape['rails'], 0, 2.5)
        asset = shape['asset']
        file = out / (asset + '.glb')
        materials = []
        for role, filename in {'bridge-deck': 'roads/asphalt.png', 'bridge-structure': 'sculpt/concrete.png'}.items():
            texture = os.path.relpath(out / 'textures' / filename, file.parent).replace('\\', '/')
            materials.append({'id': role, 'diffuse': [1, 1, 1], 'textures': [
                {'id': role, 'filename': texture, 'type': 'DIFFUSE', 'wrapS': 10497, 'wrapT': 10497}]})
        model = {'id': Path(asset).name, 'version': [0, 1], 'materials': materials,
                 'meshes': [{'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': packed,
                             'parts': [{'id': role, 'type': 'TRIANGLES', 'indices': indices} for role, indices in parts.items()]}],
                 'nodes': [{'id': Path(asset).name, 'parts': [{'meshpartid': role, 'materialid': role} for role in parts]}]}
        write_glb(file, levels={0: model})
        stats[asset] = {'triangles': sum(map(len, parts.values())) // 3,
                        'vertices': len(packed) // 12, 'bridge_exits': shape['exits']}
    manifest_file = out / 'manifest.json'
    manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
    manifest.update(stats)
    manifest_file.write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'bridge_models': len(stats), 'max_triangles': max(s['triangles'] for s in stats.values())}), flush=True)
    return stats


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1])
