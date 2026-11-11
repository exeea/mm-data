"""Reads the outlines the pool models were first made to (water, coping, deck; the deck slabs' land), from the pool GLBs
of the commit given, into pool_outlines.json beside this file: pool_props.py builds the pools to them, so the layouts
that place the pools (scenery/layouts.json) keep fitting.

Run: python pool_outlines.py <commit>     (the last commit that held the first pools: 002cda1be9)
"""
import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NAMES = ['freeform', 'rectangular-no-deck', 'rectangular', 'round-no-deck', 'sport-1-deck', 'sport-1-main', 'sport-1-wading', 'sport-2',
         'sport-3-deck', 'sport-3-main', 'sport-3-wading', 'sport-4', 'sport-5']


def load(data):
    n = struct.unpack('<I', data[12:16])[0]
    off = 20+n
    m = struct.unpack('<I', data[off:off+4])[0]
    return json.loads(data[20:20+n]), data[off+8:off+8+m]


def accessor(js, binary, i):
    a = js['accessors'][i]
    view = js['bufferViews'][a['bufferView']]
    start = view.get('byteOffset', 0)+a.get('byteOffset', 0)
    n = {'VEC3': 3, 'VEC2': 2, 'SCALAR': 1, 'VEC4': 4}[a['type']]
    kind = {5126: '<f4', 5123: '<u2', 5125: '<u4', 5121: 'u1'}[a['componentType']]
    stride = view.get('byteStride', 0)
    if stride and stride != np.dtype(kind).itemsize*n:
        return np.array([np.frombuffer(binary, kind, n, start+k*stride) for k in range(a['count'])])
    return np.frombuffer(binary, kind, a['count']*n, start).reshape(a['count'], n)


def loops(triangles):
    """The boundary loops of triangles given as 2D points."""
    edges = {}
    for t in triangles:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if a == b:
                continue
            if (b, a) in edges:
                del edges[(b, a)]
            else:
                edges[(a, b)] = 1
    following = {}
    for a, b in edges:
        following.setdefault(a, []).append(b)
    out = []
    while following:
        start = next(iter(following))
        loop, at = [start], start
        while at in following:
            b = following[at].pop()
            if not following[at]:
                del following[at]
            if b == start:
                break
            loop.append(b)
            at = b
        out.append(loop)
    return out


def area(loop):
    return .5*sum(loop[i][0]*loop[(i+1) % len(loop)][1]-loop[(i+1) % len(loop)][0]*loop[i][1] for i in range(len(loop)))


def simplify(loop, tolerance=.12):
    out, changed = list(loop), True
    while changed and len(out) > 8:
        changed = False
        for i in range(len(out)):
            a, b, c = out[i-1], out[i], out[(i+1) % len(out)]
            d = abs((c[0]-a[0])*(a[1]-b[1])-(a[0]-b[0])*(c[1]-a[1]))/max(1e-6, ((c[0]-a[0])**2+(c[1]-a[1])**2)**.5)
            if d < tolerance:
                del out[i]
                changed = True
                break
    return out


def outlines(js, binary):
    groups = {}
    for mesh in js['meshes']:
        if 'lod1' in mesh.get('name', ''):
            continue
        for primitive in mesh['primitives']:
            v = accessor(js, binary, primitive['attributes']['POSITION'])
            material = js['materials'][primitive['material']].get('name', '?')
            for t in accessor(js, binary, primitive['indices']).reshape(-1, 3):
                points = v[t]
                if np.cross(points[1]-points[0], points[2]-points[0])[1] <= 1e-6:
                    continue  # Upward faces only.
                key = material if material != 'scenery' else 'land@%.1f' % round(float(points[:, 1].mean()), 1)
                groups.setdefault(key, []).append([(round(float(q[0]), 2), round(float(-q[2]), 2)) for q in points])
    result = {}
    for key, triangles in groups.items():
        loop = max(loops(triangles), key=lambda l: abs(area(l)))
        result[key.replace('pool-', '')] = simplify(loop if area(loop) > 0 else loop[::-1])
    return result


if __name__ == '__main__':
    found = {}
    for name in NAMES:
        data = subprocess.run(['git', '-C', str(REPO), 'show', f'{sys.argv[1]}:data/models/board/scenery/pools/{name}.glb'],
                              capture_output=True, check=True).stdout
        found[name] = outlines(*load(data))
    (HERE/'pool_outlines.json').write_text(json.dumps(found, indent=1)+'\n', encoding='utf-8')
    print({name: {key: len(loop) for key, loop in entry.items()} for name, entry in found.items()})
