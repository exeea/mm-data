"""Build the bedrock outcrop rock kit: rocks/outcrop-N.glb, N = 0..7.

Run in Blender, from the mm-data checkout:

    blender -b --factory-startup --python tools/build_outcrop_assets.py

Zero-gravity rough terrain shows these instead of loose boulders: without gravity nothing lies loose, so rough ground
is bedrock breaking the surface. Each formation is a rise of the ground itself: a geological height profile (cuesta,
stepped ledges, whaleback, split ridge, pavement, hogback, broken cuesta, knobs) over an irregular footprint whose skirt
flares concavely into the plain, cut by shallow joints and weathered to blunt summits. The profile is sampled densely
on a polar grid, closed with a flat base and reduced by Blender's quadric decimation to the kit's budgets, which leaves
the faceted planes of broken rock. Authoring units are metres, Z-up: strike along x, dip toward -y, scarps facing +y.
Like the rest of the rock kit, each file holds closed, flat-shaded solids named <shape>-lod0..2, with the base at zero
and the largest horizontal extent one; the material is named `geometry` and the renderer supplies the terrain's own
material.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, noise

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from glb_geometry import write_glb  # noqa: E402

OUT = TOOLS.parent / 'data/models/board/rocks'
COUNT = 8
LOD_TRIANGLES = (92, 44, 22)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def fbm(x, y, seed, octaves=3):
    total, amplitude, frequency = 0.0, 1.0, 1.0
    for _ in range(octaves):
        total += amplitude * noise.noise(Vector((x * frequency + seed, y * frequency - seed, seed * .37)),
                                         noise_basis='PERLIN_NEW')
        amplitude *= .5
        frequency *= 2.1
    return total


def outline(x, y, a, b, seed, rough=.16, flare=.5):
    """Irregular elliptical footprint: 1 inside, falling to the plain over the outer part of its radius, so the rock
    rises out of the ground through a concave flare instead of standing on it."""
    angle = math.atan2(y / b, x / a)
    r = math.hypot(x / a, y / b) * (1 + rough * noise.noise(Vector((math.cos(angle) * 1.7 + seed,
                                                                   math.sin(angle) * 1.7, seed))))
    return 1 - smoothstep(flare, 1.0, r)


def scarp(y, at, width):
    """1 before a scarp crest at y = at, falling over width metres."""
    return 1 - smoothstep(at, at + width, y)


def joints(x, y, seed, strength):
    """Shallow, broad cuts where a jointing field changes sign."""
    j = noise.noise(Vector((x * .2 + seed, y * .45 - seed, seed)), noise_basis='PERLIN_NEW')
    return 1 - strength * (1 - smoothstep(.0, .16, abs(j)))


def profile(index, x, y):
    """Height in metres of formation index above the plain at (x, y)."""
    s = index * 3.7 + 1.3
    if index == 0:  # cuesta: a dip slope rising out of the plain toward +y, broken off in a scarp
        h = 3.0 * smoothstep(-4.6, 1.2, y) * scarp(y, 1.2 + .5 * fbm(x * .3, 0, s), 1.1) * outline(x, y, 5.6, 4.6, s)
    elif index == 1:  # stepped ledges, each bed set back from the one below
        h = 0
        for step, (a, b, top, flare) in enumerate(((5.6, 3.8, 1.3, .45), (4.1, 2.7, 2.3, .7), (2.7, 1.9, 3.0, .72))):
            h = max(h, top * outline(x + .4 * step, y + .5 * step, a, b, s + step, .2, flare))
    elif index == 2:  # whaleback: a smoothed stoss dome, plucked steep on the lee (+y)
        r = math.hypot(x / 5.4, (y + .6) / 3.8)
        h = 3.0 * max(0.0, 1 - r * r) ** 1.3 * scarp(y, 1.2 + .4 * fbm(x * .4, 1, s), 1.1)
    elif index == 3:  # a ridge split by an open joint, on a shared flared foot
        ridge = smoothstep(-3.8, .8, y) * scarp(y, .8, 1.0)
        h = 3.1 * ridge * outline(x, y, 5.5, 4.2, s) * (1 - .7 * (1 - smoothstep(.2, .8, abs(x - .4 + .25 * y))))
        h = max(h, .8 * outline(x, y, 5.6, 4.0, s + 2, .2, .3))
    elif index == 4:  # a low pavement with one step
        h = max(1.1 * outline(x, y, 5.6, 4.1, s, .22, .4), 2.6 * outline(x - 1.4, y - .8, 3.0, 2.3, s + 3, .25, .7))
    elif index == 5:  # hogback: steeply dipping strata, a narrow crest and a lower parallel rib
        crest = .7 + .3 * fbm(x * .3, 2, s)
        h = 3.4 * smoothstep(-3.0, crest, y) * scarp(y, crest, 1.8) * outline(x, y, 5.6, 4.0, s, .12)
        h = max(h, 1.9 * smoothstep(-4.2, -2.8, y) * scarp(y, -2.8, 1.0) * outline(x + .6, y, 4.4, 4.6, s + 4))
    elif index == 6:  # broken cuesta: two segments offset along a joint, on a shared flared foot
        a = smoothstep(-3.8, .8, y) * scarp(y, .8, 1.0) * outline(x + 2.4, y, 3.4, 4.4, s, .16, .55)
        b = smoothstep(-3.4, 1.6, y) * scarp(y, 1.6, 1.0) * outline(x - 2.2, y - .7, 3.5, 4.4, s + 5, .16, .55)
        h = max(2.9 * max(a, b * .92), .7 * outline(x, y, 5.5, 4.0, s + 6, .2, .3))
    else:  # knobs on a shared low bed, the roots of a worn-down ridge
        h = 1.1 * outline(x, y, 5.6, 3.6, s, .2, .35)
        for k, (cx, cy, r, top) in enumerate(((-3.0, .2, 2.0, 3.0), (.1, -.4, 1.8, 2.6), (3.0, .3, 1.7, 2.3))):
            knob = max(0.0, 1 - (math.hypot(x - cx, y - cy) / r) ** 2) ** .6
            h = max(h, top * knob * outline(x - cx, y - cy, r * 1.4, r * 1.2, s + k, .25, .55))
    h *= joints(x, y, s, .15 if index not in (2, 4) else .08)
    # Weathered summits: above a knee the rock rises a third as fast, so crests stay blunt rather than fangs.
    h -= .65 * .25 * math.log1p(math.exp((h - 2.2) / .25))
    return max(0.0, h + fbm(x * .3, y * .3, s, 2) * .12 * smoothstep(.05, .6, h))


def reach(index, angle):
    """Outermost radius along a ray from the centre where the formation still stands above the plain."""
    c, s = math.cos(angle), math.sin(angle)
    r = 6.8
    while r > .2 and profile(index, r * c, r * s) <= .02:
        r -= .04
    return r + .12


def formation(index):
    """A closed solid on a polar grid: the profile over its footprint, its rim at zero, a flat base."""
    count, rings = 144, 36
    bm = bmesh.new()
    centre = bm.verts.new((0, 0, max(profile(index, 0, 0), .05)))
    reaches = [reach(index, 2 * math.pi * m / count) for m in range(count)]
    grid = []
    for k in range(1, rings + 1):
        ring = []
        for m in range(count):
            angle, r = 2 * math.pi * m / count, reaches[m] * k / rings
            x, y = r * math.cos(angle), r * math.sin(angle)
            ring.append(bm.verts.new((x, y, 0 if k == rings else max(profile(index, x, y), .05))))
        grid.append(ring)
    for m in range(count):
        bm.faces.new((centre, grid[0][m], grid[0][(m + 1) % count]))
    for k in range(rings - 1):
        for m in range(count):
            n = (m + 1) % count
            bm.faces.new((grid[k][m], grid[k + 1][m], grid[k + 1][n], grid[k][n]))
    bm.faces.new(list(reversed(grid[-1])))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(f'outcrop-{index}')
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f'outcrop-{index}', mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def normalised(obj):
    """Centred on its footprint, largest horizontal extent one; the base is already at zero."""
    mesh = obj.data
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    offset = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0))
    for v in mesh.vertices:
        v.co = (v.co - offset) / span
    mesh.update()


def decimated(obj, target):
    """Quadric decimation to the level's budget, kept on and inside the kit's unit footprint."""
    copy = obj.copy()
    copy.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(copy)
    modifier = copy.modifiers.new('lod', 'DECIMATE')
    modifier.decimate_type = 'COLLAPSE'
    modifier.use_collapse_triangulate = True
    modifier.ratio = min(1, target / len(copy.data.polygons))
    bpy.context.view_layer.objects.active = copy
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    for v in copy.data.vertices:
        v.co.x = max(-.5, min(.5, v.co.x))
        v.co.y = max(-.5, min(.5, v.co.y))
        v.co.z = max(v.co.z, 0)
    return copy


def triangles(obj):
    """Flat-shaded triangles, counter-clockwise from outside, in authoring Z-up coordinates."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    return [[tuple(mesh.vertices[i].co) for i in tri.vertices] for tri in mesh.loop_triangles]


def closed(faces):
    edges = {}
    for tri in faces:
        for i in range(3):
            a, b = (tuple(round(c, 5) for c in tri[i]), tuple(round(c, 5) for c in tri[(i + 1) % 3]))
            edges[(a, b)] = edges.get((a, b), 0) + 1
    return all(count == 1 and edges.get((b, a)) == 1 for (a, b), count in edges.items())


def volume(faces):
    return sum(Vector(a).dot(Vector(b).cross(Vector(c))) / 6 for a, b, c in faces)


def export(name, levels):
    meshes, nodes = [], []
    for level, faces in enumerate(levels):
        vertices, indices = [], []
        for a, b, c in faces:
            n = (Vector(b) - Vector(a)).cross(Vector(c) - Vector(a)).normalized()
            for p in (a, b, c):
                indices.append(len(vertices) // 12)
                vertices.extend((*(round(v, 6) for v in p), *(round(v, 6) for v in n), 1, 1, 1, 1, 0, 0))
        part = f'{name}-lod{level}'
        meshes.append({'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': vertices,
                       'parts': [{'id': part, 'type': 'TRIANGLES', 'indices': indices}]})
        nodes.append({'id': part, 'parts': [{'meshpartid': part, 'materialid': 'geometry'}]})
    write_glb(OUT / f'{name}.glb', {'id': name, 'meshes': meshes, 'nodes': nodes,
                                    'materials': [{'id': 'geometry', 'diffuse': [1, 1, 1]}]})


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for index in range(COUNT):
        name = f'outcrop-{index}'
        obj = formation(index)
        normalised(obj)
        levels = [triangles(decimated(obj, target)) for target in LOD_TRIANGLES]
        for level, faces in enumerate(levels):
            assert closed(faces), (name, level, 'open or inconsistently wound')
            assert volume(faces) > .02, (name, level, 'volume', volume(faces))
            assert len(faces) <= 120, (name, level, len(faces))
            assert .2 < max(p[2] for tri in faces for p in tri) < 1.2, (name, level, 'height')
        export(name, levels)
        print(f'{name}: ' + ', '.join(str(len(faces)) for faces in levels) + ' triangles')


main()
