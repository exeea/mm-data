"""Run in Blender: blender -b --factory-startup --python tools/board-models/scatter_lods.py -- [names...]

The scatter bushes' far levels: each bush's lod0, as authored in data/models/board/scatter/bush-N.glb (read, never
written: the scatter kit's readers want its one root node), with a lod1 of about 80 and a lod2 of about 32 triangles,
written as scatter/bush-N-levels.glb, which the scatter stand draws. Each level is a group `bush-N-lodK` holding one node
`bush-N-lodK-mesh`, every node and mesh part named apart. A bush is a cloud of loose leaf, tip
and bark triangles, each with its explicit back face, which an edge-collapse decimation empties; its levels thin the
cloud instead: every material keeps its share of the budget's front/back pairs, picked by farthest-point sampling of
their centres (evenly over the bush), and each kept triangle grows about its centre until the level covers what the
nearer one covers where the game switches to it (`SWITCHES`, the bush's projected diameter in pixels), from above and
from the isometric view all round (alien_lods.silhouettes, at four times the pixels). A rebuild reads the same lod0 and
reproduces the levels file; the manifest keeps its counts.
"""
import json
import math
import sys
from pathlib import Path

import numpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from alien_lods import diagonal, silhouettes  # noqa: E402
from glb_geometry import read_glb, write_glb  # noqa: E402

BOARD = HERE.parents[1] / 'data/models/board'
MANIFEST = HERE / 'manifest.json'
NAMES = tuple(f'bush-{n}' for n in range(8))
# Triangles per far level (with fewer than 32 so few leaves are left that the bush thins or thickens by its side),
# and the projected diameter (pixels) at which the game takes it over from the nearer one.
BUDGETS = {1: 80, 2: 32}
SWITCHES = {1: 20, 2: 8}
# Coverage is counted at this many times the switch's pixels, standing in for the game's antialiasing.
SUPER = 4
GROWTHS = numpy.arange(.6, 1.81, .02)


def triangles(model):
    """Every triangle of the model's mesh: its three vertex indices and its part."""
    return [(tuple(part['indices'][i:i + 3]), part['id']) for part in model['meshes'][0]['parts']
            for i in range(0, len(part['indices']), 3)]


def pairs(model):
    """The front/back twins: triangles with the same corners, grouped, with their centre, area and part."""
    vertices = model['meshes'][0]['vertices']
    corner = lambda v: tuple(round(c, 5) for c in vertices[v * 12:v * 12 + 3])
    groups = {}
    for corners, part in triangles(model):
        groups.setdefault((part, tuple(sorted(corner(v) for v in corners))), []).append(corners)
    result = []
    for (part, key), members in groups.items():
        points = numpy.array(key)
        area = numpy.linalg.norm(numpy.cross(points[1] - points[0], points[2] - points[0])) / 2
        result.append((part, members, points.mean(0), area))
    return result


def sample(group, count):
    """Farthest-point sampling of `count` pairs by centre, from the one nearest the group's middle."""
    if count >= len(group):
        return list(group)
    centres = numpy.array([g[2] for g in group])
    chosen = [int(numpy.argmin(numpy.linalg.norm(centres - centres.mean(0), axis=1)))]
    distance = numpy.linalg.norm(centres - centres[chosen[0]], axis=1)
    while len(chosen) < count:
        chosen.append(int(numpy.argmax(distance)))
        distance = numpy.minimum(distance, numpy.linalg.norm(centres - centres[chosen[-1]], axis=1))
    return [group[i] for i in sorted(chosen)]


def thinned(model, budget):
    """The pairs a level of `budget` triangles keeps, each material its share; and their area growth."""
    groups = pairs(model)
    per = sum(len(g[1]) for g in groups) / len(groups)
    keep = max(1, round(budget / per))
    kept = []
    for part in dict.fromkeys(g[0] for g in groups):
        members = [g for g in groups if g[0] == part]
        kept += sample(members, max(1, round(keep * len(members) / len(groups))))
    return kept, math.sqrt(sum(g[3] for g in groups) / sum(g[3] for g in kept))


def level(model, kept, scale, index, name):
    """A level of the model from its kept pairs, every triangle grown `scale` times about its centre."""
    source = model['meshes'][0]['vertices']
    vertices, parts = [], {}
    for part, members, centre, _ in kept:
        for corners in members:
            for v in corners:
                row = list(source[v * 12:v * 12 + 12])
                row[:3] = [centre[i] + (row[i] - centre[i]) * scale for i in range(3)]
                parts.setdefault(part, []).append(len(vertices) // 12)
                vertices.extend(row)
    node = f'{name}-lod{index}'
    original = {p['meshpartid']: p['materialid'] for p in model['nodes'][0]['parts']}
    return {'id': node, 'extras': model.get('extras') or {},
            # A file's mesh parts are named apart across its levels (<node>-<part>, as alien_lods.py's).
            'meshes': [{'attributes': model['meshes'][0]['attributes'], 'vertices': vertices,
                        'parts': [{'id': f'{node}-{part}', 'type': 'TRIANGLES', 'indices': indices}
                                  for part, indices in parts.items()]}],
            'nodes': [{'id': f'{node}-mesh',
                       'parts': [{'meshpartid': f'{node}-{part}', 'materialid': original[part]} for part in parts]}],
            'materials': [m for m in model['materials'] if m['id'] in {original[p] for p in parts}]}


def covered(model, scale):
    mesh = model['meshes'][0]
    return silhouettes(mesh['vertices'], [i for part in mesh['parts'] for i in part['indices']], scale)


def build(name):
    near = read_glb(BOARD / f'scatter/{name}.glb', 0, linear_colors=True)
    near['id'], near['nodes'][0]['id'] = f'{name}-lod0', f'{name}-lod0-mesh'
    levels, previous = {0: near}, near
    for index in (1, 2):
        kept, area = thinned(near, BUDGETS[index])
        scale = SUPER * SWITCHES[index] / diagonal(near['meshes'][0]['vertices'])
        target = covered(previous, scale)
        best = None
        for growth in GROWTHS:
            candidate = level(near, kept, area * growth, index, name)
            # The worst view decides: every view keeps the nearer level's coverage as closely as it can.
            error = max(abs(math.log(max(1, a) / max(1, b))) for a, b in zip(covered(candidate, scale), target))
            if best is None or error < best[0]:
                best = (error, candidate, growth)
        levels[index] = previous = best[1]
        print(f'{name} lod{index}: {sum(len(p["indices"]) for p in previous["meshes"][0]["parts"]) // 3} triangles, '
              f'growth {area * best[2]:.2f}, worst view {math.exp(best[0]) - 1:+.1%} at {SWITCHES[index]} px', flush=True)
    write_glb(BOARD / f'scatter/{name}-levels.glb', levels=levels, linear_colors=True)
    counts = [{'node': f'{name}-lod{i}', 'triangles': sum(len(p['indices']) for p in levels[i]['meshes'][0]['parts']) // 3,
               'vertices': len(levels[i]['meshes'][0]['vertices']) // 12} for i in range(3)]
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    entry = manifest.setdefault(f'scatter/{name}-levels', {'mesh': f'scatter/{name}-levels.glb'})
    entry['lods'] = counts
    entry.update(source='tools/board-models/scatter_lods.py', triangles=counts[0]['triangles'],
                 vertices=counts[0]['vertices'])
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for name in arguments or NAMES:
        build(name)
