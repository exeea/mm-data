"""Run with Blender --background --python tools/prepare_tree_lods.py -- [trees|impostors] [names...].

Leafy trees keep their authored trunks and crown envelopes, with alpha-tested
branch clusters replacing closed leaf shells. Three bounded mesh levels and the
impostor are generated offline; the renderer does not change tree placement.
Palms use curved frond strips; cacti keep their stem silhouettes with smooth
normals, mapped ribs and cutout flowers. Bare trees retain their visible near
triangles; their lower levels use collapse decimation or component hulls.

The impostor stage adds LOD3 to every plant with detail levels (trees, shrubs
and orchard trees): three textured cards carrying unlit renders of LOD0.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_geometry import read_glb, write_glb

import collections
import copy
import json
import math
import random
from pathlib import Path

import bmesh
import bpy
import numpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

BOARD = Path(__file__).resolve().parents[1] / 'data/models/board'
BUDGETS = (240, 96)
IMPOSTORS = 'textures/foliage/impostors'
# Pixels per card face; the game draws the cards only below TreeLod's smallest threshold.
PANEL = 128


def geometry(model):
    """Weld positions for topology only; retain the authored per-corner data."""
    vertices, shared, faces, corners = [], {}, [], []
    mesh = model['meshes'][0]
    source = mesh['vertices']
    for part in mesh['parts']:
        for offset in range(0, len(part['indices']), 3):
            attributes = [source[i * 12:i * 12 + 12] for i in part['indices'][offset:offset + 3]]
            face = []
            for vertex in attributes:
                # Simplification operates in the tree's original proportions.
                point = tuple(vertex[:3])
                if point not in shared:
                    shared[point] = len(vertices)
                    vertices.append(Vector(point))
                face.append(shared[point])
            faces.append(face)
            corners.append((part['id'], attributes))
    return vertices, faces, corners


def enclosed_faces(vertices, faces):
    adjacent = [set() for _ in vertices]
    for face in faces:
        for vertex in face:
            adjacent[vertex].update(face)
    components, visited = [], set()
    for start in range(len(vertices)):
        if start in visited:
            continue
        group, pending = set(), [start]
        while pending:
            vertex = pending.pop()
            if vertex not in group:
                group.add(vertex)
                pending.extend(adjacent[vertex] - group)
        visited.update(group)
        components.append([i for i, face in enumerate(faces) if face[0] in group])
    whole = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    hidden = set()
    for component in components:
        surface = [faces[i] for i in component]
        edges = collections.Counter((face[k], face[(k + 1) % 3]) for face in surface for k in range(3))
        # Open palm fronds must never be mistaken for enclosing volumes.
        if any(count != 1 or edges[b, a] != 1 for (a, b), count in edges.items()):
            continue
        shell = BVHTree.FromPolygons(vertices, surface, all_triangles=True)
        intersecting = {a for a, _ in whole.overlap(shell)} | set(component)
        triangles = [[vertices[i] for i in face] for face in surface]

        def inside(point):
            if shell.find_nearest(point)[3] < 0.0001:
                return False
            # Solid angle works for concave canopies too; no assumed ray direction.
            angle = 0
            for triangle in triangles:
                a, b, c = [vertex - point for vertex in triangle]
                denominator = (a.length * b.length * c.length + a.dot(b) * c.length
                               + b.dot(c) * a.length + c.dot(a) * b.length)
                angle += 2 * math.atan2(a.dot(b.cross(c)), denominator)
            return abs(angle) > 2 * math.pi

        for index, face in enumerate(faces):
            if index in intersecting or index in hidden:
                continue
            points = [vertices[i] for i in face]
            if inside(sum(points, Vector()) / 3) and all(inside(point) for point in points):
                hidden.add(index)
    return hidden


def pack(source, name, corners):
    model = copy.deepcopy(source)
    vertices, shared, parts = [], {}, {}
    for role, triangle in corners:
        indices = parts.setdefault(role, [])
        for vertex in triangle:
            key = tuple(vertex)
            if key not in shared:
                shared[key] = len(vertices) // 12
                vertices.extend(vertex)
            indices.append(shared[key])
    model['id'] = name
    model['meshes'] = [{'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': vertices,
                        'parts': [{'id': role, 'type': 'TRIANGLES', 'indices': indices}
                                  for role, indices in parts.items()]}]
    model['nodes'] = [{'id': name, 'parts': [{'meshpartid': role, 'materialid': role} for role in parts]}]
    return model


def decimated(vertices, faces, keys, budget):
    """Blender's collapse decimation of faces to about budget triangles, each as its corners, material key and normal."""
    mesh = bpy.data.meshes.new('Tree screen-size detail')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    order = {key: index for index, key in enumerate(dict.fromkeys(keys))}
    for role, color in order:
        mesh.materials.append(bpy.data.materials.new(role))
    for polygon, key in zip(mesh.polygons, keys):
        polygon.material_index = order[key]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new('Tree screen-size detail', 'DECIMATE')
    modifier.ratio = min(1, budget / len(faces))
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    mesh = obj.data
    mesh.calc_loop_triangles()
    keys = list(order)
    result = [([mesh.vertices[index].co.copy() for index in triangle.vertices], keys[triangle.material_index],
               triangle.normal.copy()) for triangle in mesh.loop_triangles]
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return result


def parts(count, faces):
    """The faces of each connected part of a plant: its trunk, a skirt of needles, a frond."""
    root = list(range(count))

    def find(vertex):
        while root[vertex] != vertex:
            root[vertex] = root[root[vertex]]
            vertex = root[vertex]
        return vertex

    for face in faces:
        for vertex in face[1:]:
            root[find(vertex)] = find(face[0])
    groups = {}
    for index, face in enumerate(faces):
        groups.setdefault(find(face[0]), []).append(index)
    return list(groups.values())


def hull(vertices, faces):
    """The triangulated convex hull of the corners of faces: its positions and triangles."""
    bm = bmesh.new()
    made = bmesh.ops.convex_hull(bm, input=[bm.verts.new(vertices[v]) for v in sorted({v for f in faces for v in f})])
    inside = {element for element in made['geom_interior'] + made['geom_unused'] if isinstance(element, bmesh.types.BMVert)}
    bmesh.ops.delete(bm, geom=list(inside), context='VERTS')
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    index = {vertex: i for i, vertex in enumerate(bm.verts)}
    result = [vertex.co.copy() for vertex in bm.verts], [[index[vertex] for vertex in face.verts] for face in bm.faces]
    bm.free()
    return result


def area(vertices, faces):
    return sum((vertices[f[1]] - vertices[f[0]]).cross(vertices[f[2]] - vertices[f[0]]).length for f in faces) / 2


# The board camera's views of a plant: from 35 degrees above on four sides, and from straight above.
OUTLINE = [Vector((math.cos(turn) * math.cos(math.radians(35)), math.sin(turn) * math.cos(math.radians(35)),
                   math.sin(math.radians(35)))) for turn in (0, math.pi / 2, math.pi, 3 * math.pi / 2)] + [Vector((0, 0, 1))]


def outline(triangles):
    """How much of a plant the board camera sees: the area its triangles turn toward the camera's views."""
    return sum(max(0, (b - a).cross(c - a).dot(view)) for a, b, c in triangles for view in OUTLINE) / 2


def keeps_outline(source, budget):
    """Whether collapse decimation to budget keeps two thirds of the plant's outline. The jagged skirts of pines and
    the fronds of palms lose half theirs, and the snow on them with it; broad crowns, trunks and cacti keep most."""
    vertices, faces, corners = geometry(source)
    keys = [(role, tuple(attributes[0][6:10])) for role, attributes in corners]
    kept = outline([points for points, key, normal in decimated(vertices, faces, keys, budget)])
    return kept >= outline([[vertices[v] for v in face] for face in faces]) * 2 / 3


def surface_keys(vertices, faces, keys, triangles):
    """Gives each new triangle the material of the original surface it replaces: the nearest original face turned the
    same way, at its centre and toward its corners, so a skirt's top keeps its snow and its underside its needles."""
    tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    normals = [(vertices[f[1]] - vertices[f[0]]).cross(vertices[f[2]] - vertices[f[0]]).normalized() for f in faces]
    reach = max(max(point[i] for point in vertices) - min(point[i] for point in vertices) for i in range(3)) * .15
    result = []
    for points, key, normal in triangles:
        centre = sum(points, Vector()) / 3
        votes = collections.Counter()
        for sample in [centre] + [(centre + point) / 2 for point in points]:
            near = sorted(tree.find_nearest_range(sample, reach), key=lambda hit: hit[3])
            hit = next((hit for hit in near if normals[hit[2]].dot(normal) > 0), None) or tree.find_nearest(sample)
            votes[keys[hit[2]]] += 1
        result.append((points, votes.most_common(1)[0][0], normal))
    return result


def simplified(source, name, budget, hulled):
    vertices, faces, corners = geometry(source)
    keys = [(role, tuple(attributes[0][6:10])) for role, attributes in corners]
    if not hulled:
        triangles = decimated(vertices, faces, keys, budget)
    else:
        # Each compact part (a pine skirt, a palm frond) keeps its outline as its decimated convex hull, which holds
        # the tips decimation files away. Parts whose hull would bloat (trunks, branches) decimate together.
        triangles, rest = [], []
        for part in parts(len(vertices), faces):
            part_faces = [faces[i] for i in part]
            positions, shell = hull(vertices, part_faces)
            if area(positions, shell) < 1.3 * area(vertices, part_faces):
                share = max(4, budget * len(part) // len(faces))
                # Any key will do: the surface decides each hull triangle's material below.
                triangles += decimated(positions, shell, [keys[part[0]]] * len(shell), share)
            else:
                rest += part
        triangles = surface_keys(vertices, faces, keys, triangles)
        if rest:
            triangles += decimated(vertices, [faces[i] for i in rest], [keys[i] for i in rest],
                                   budget * len(rest) // len(faces))
    result = []
    low = Vector(tuple(min(point[i] for point in vertices) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in vertices) for i in range(3)))
    for points, (role, color), normal in triangles:
        n = normal.normalized()
        attributes = []
        for point in points:
            # All levels share the near model's coordinate system and bounds.
            point = Vector(tuple(max(low[i], min(high[i], point[i])) for i in range(3)))
            if abs(normal.z) >= max(abs(normal.x), abs(normal.y)):
                uv = (point.x, point.y)
            else:
                uv = (point.x if abs(normal.y) > abs(normal.x) else point.y, point.z)
            repeat = 4 if role.startswith('bark') else 8 if name.startswith('birch') else 12
            attributes.append(tuple(round(v, 6) for v in
                                    (point.x, point.y, point.z, *n, *color, uv[0] / repeat, uv[1] / repeat)))
        result.append((role, attributes))
    assert len(result) <= budget, (name, len(result), budget)
    return pack(source, name, result)


def counts(model):
    mesh = model['meshes'][0]
    return {'triangles': sum(len(part['indices']) // 3 for part in mesh['parts']),
            'vertices': len(mesh['vertices']) // 12}


def stem_section(vertices, faces, height):
    """Centre of the authored stem at a height, including its bends, not its overall bounding box."""
    low = min(p.z for p in vertices)
    high = max(p.z for p in vertices)
    z = max(low + .0001, min(high - .0001, height))
    crossing = []
    for face in faces:
        for i in range(3):
            a, b = vertices[face[i]], vertices[face[(i + 1) % 3]]
            if min(a.z, b.z) <= z <= max(a.z, b.z) and abs(a.z - b.z) > 1e-6:
                crossing.append(a.lerp(b, (z - a.z) / (b.z - a.z)))
    assert crossing, ('Stem has no section', height)
    return Vector(((min(p.x for p in crossing) + max(p.x for p in crossing)) / 2,
                   (min(p.y for p in crossing) + max(p.y for p in crossing)) / 2, height))


def cutout_material(role, texture):
    return {'id': role, 'diffuse': [1, 1, 1], 'alphaTest': .5, 'textures': [
        {'id': role, 'type': 'DIFFUSE', 'filename': f'textures/foliage/{texture}.png',
         'wrapS': 33071, 'wrapT': 33071}]}


def append_cutout(result, role, points, uvs, triangles, normals=None, tint=1):
    for indices in triangles:
        normal = (points[indices[1]] - points[indices[0]]).cross(points[indices[2]] - points[indices[0]])
        if normal.length < 1e-6:
            continue
        normal.normalize()
        attributes = [tuple(round(v, 6) for v in
                            (*points[j], *(normals[j] if normals else normal), tint, tint, tint, 1, *uvs[j]))
                      for j in indices]
        result.append((role, attributes))
        # Explicit backs retain the same botanical normal, as the existing canopy lighting expects.
        result.append((role, list(reversed(attributes))))


def branch_crowns(source, name):
    """Replace closed leaf shells with bounded branch cards, keeping the authored trunk and crown envelopes.

    All three mesh levels use the same source silhouette and seed. The original
    CC0 authoring file stays untouched. Explicit backs work in every existing
    depth/shadow pass. Standard glTF MASK materials keep every level opaque.
    """
    if not name.startswith(('tree', 'pine', 'birch', 'willow')) or name.startswith('tree-dead'):
        return None
    vertices, faces, corners = geometry(source)
    leaves = [face for face, (role, _) in zip(faces, corners) if not solid(role)]
    if not leaves:
        return None
    envelopes = []
    for group in parts(len(vertices), leaves):
        points = [vertices[i] for j in group for i in leaves[j]]
        low = Vector(tuple(min(p[k] for p in points) for k in range(3)))
        high = Vector(tuple(max(p[k] for p in points) for k in range(3)))
        if (high - low).length > .5:
            envelopes.append(((low + high) / 2, (high - low) / 2))
    low = Vector(tuple(min(p[k] for face in leaves for p in (vertices[i] for i in face)) for k in range(3)))
    high = Vector(tuple(max(p[k] for face in leaves for p in (vertices[i] for i in face)) for k in range(3)))
    bark = pack(source, name, [corner for corner in corners if solid(corner[0])])
    stem_vertices, stem_faces, _ = geometry(bark)
    pine = name.startswith('pine')
    texture = ('conifer' if pine else 'broadleaf') + ('-snow' if name.endswith('-snow') else '') + '-cutout'
    role = 'canopy-snow-cutout' if name.endswith('-snow') else 'canopy-cutout'
    material = cutout_material(role, texture)
    seed = sum((i + 1) * ord(c) for i, c in enumerate(name.removesuffix('-snow')))
    levels = {}
    for level, (budget, cards) in enumerate(((480, 88), (240, 42), (96, 15))):
        rng = random.Random(seed)
        model = simplified(bark, f'{name}-lod{level}', budget - cards * 4, False)
        _, _, result = geometry(model)
        for i in range(cards):
            if pine:
                t = (i + .5) / cards
                angle = i * 2.399963 + rng.uniform(-.12, .12)
                radius = max(high.x - low.x, high.y - low.y) * .49 * (1 - t) ** .75
                outward = Vector((math.cos(angle), math.sin(angle), 0))
                right = Vector((-outward.y, outward.x, rng.uniform(-.55, .55))).normalized()
                up = (outward + Vector((0, 0, .25 + t * .7))).normalized()
                length = radius * 1.15 + .8
                centre = stem_section(stem_vertices, stem_faces, low.z + t * (high.z - low.z))
                centre += up * length * .4
                width = length * (1.05 if level == 0 else 1.4 if level == 1 else 2.2)
                normal = (outward * .45 + Vector((0, 0, .8))).normalized()
            else:
                centre, extent = rng.choices(envelopes, weights=[e.length_squared for _, e in envelopes])[0]
                angle = i * 2.399963
                z = rng.uniform(-.85, .95)
                radial = Vector((math.cos(angle) * math.sqrt(1 - z * z),
                                 math.sin(angle) * math.sqrt(1 - z * z), z))
                centre = centre + Vector(tuple(radial[k] * extent[k] * .65 for k in range(3)))
                normal = (radial + Vector((0, 0, .45))).normalized()
                right = Vector((-math.sin(angle), math.cos(angle), rng.uniform(-.3, .3))).normalized()
                up = normal.cross(right).normalized()
                # Broadleaf sprays form lobes; willow cards droop from those same authored lobes.
                if name.startswith('willow'):
                    up = Vector((radial.x * .25, radial.y * .25, -1)).normalized()
                width = max(2.5, extent.length * (.8 if level == 0 else 1.05 if level == 1 else 1.5))
                length = width * (1.25 if name.startswith(('willow', 'birch')) else .95)
            # Fewer distant branches cover the same envelope; length as well as width must bridge their gaps.
            if pine and level == 2:
                length *= 1.3
            points = [centre + right * x * width + up * y * length
                      for x, y in ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5))]
            # Never expand foliage beyond the captured source bounds or its route/structure clearance.
            points = [Vector(tuple(max(low[k], min(high[k], p[k])) for k in range(3))) for p in points]
            tint = rng.uniform(.88, 1.0)
            append_cutout(result, role, points, ((0, 1), (1, 1), (1, 0), (0, 0)),
                          ((0, 1, 2), (0, 2, 3)), [normal] * 4, tint)
        model['materials'] = [m for m in source['materials'] if solid(m['id'])] + [material]
        model['nodes'] = [{'id': f'{name}-lod{level}', 'parts': [
            {'meshpartid': m['id'], 'materialid': m['id']} for m in model['materials']]}]
        levels[level] = pack(model, f'{name}-lod{level}', result)
        # A clipped branch tip must not shorten the normalized catalog height, which placement uses at every LOD.
        data = levels[level]['meshes'][0]['vertices']
        bottom = min(data[2::12])
        scale = high.z / (max(data[2::12]) - bottom)
        for vertex in range(0, len(data), 12):
            data[vertex + 2] = (data[vertex + 2] - bottom) * scale
        assert counts(levels[level])['triangles'] <= budget
    return levels


def palm_crowns(source, name):
    """Curved, folded fronds attach to the original palm's terminal stem, including the leaning palm."""
    vertices, faces, corners = geometry(source)
    leaves = [face for face, (role, _) in zip(faces, corners) if not solid(role)]
    bark = pack(source, name, [corner for corner in corners if solid(corner[0])])
    stem_vertices, stem_faces, _ = geometry(bark)
    root = stem_section(stem_vertices, stem_faces, max(p.z for p in stem_vertices) - .15)
    low = Vector(tuple(min(p[k] for p in vertices) for k in range(3)))
    high = Vector(tuple(max(p[k] for p in vertices) for k in range(3)))
    fronds = []
    for group in parts(len(vertices), leaves):
        points = [vertices[i] for j in group for i in leaves[j]]
        tip = max(points, key=lambda p: (p - root).length_squared).copy()
        along = Vector((tip.x - root.x, tip.y - root.y, 0)).normalized()
        right = Vector((-along.y, along.x, 0))
        width = max(1.5, max(abs((p - root).dot(right)) for p in points) * 2.2)
        control = (root + tip) / 2
        control.z = 2 * max(p.z for p in points) - (root.z + tip.z) / 2
        fronds.append((math.atan2(along.y, along.x), tip, right, width, control))
    fronds.sort(key=lambda f: f[0])
    material = cutout_material('canopy-cutout', 'palm-frond-cutout')
    levels = {}
    for level, budget in enumerate((480, 240, 96)):
        selected = fronds if level < 2 else [fronds[i * len(fronds) // 7] for i in range(7)]
        segments, columns = (3, 3) if level == 0 else (3, 2) if level == 1 else (2, 2)
        leaf_budget = len(selected) * segments * (columns - 1) * 4
        model = simplified(bark, f'{name}-lod{level}', budget - leaf_budget, False)
        _, _, result = geometry(model)
        for _, tip, right, width, control in selected:
            points, uvs, triangles = [], [], []
            width *= 1.65 if level == 2 else 1
            for row in range(segments + 1):
                t = row / segments
                centre = (1 - t) ** 2 * root + 2 * t * (1 - t) * control + t * t * tip
                for column in range(columns):
                    u = column / (columns - 1)
                    p = centre + right * ((u - .5) * width)
                    if columns == 3 and column == 1:
                        p.z += .10 * width * math.sin(math.pi * t)
                    points.append(Vector(tuple(max(low[k], min(high[k], p[k])) for k in range(3))))
                    uvs.append((u, 1 - t))
            for row in range(segments):
                for column in range(columns - 1):
                    a = row * columns + column
                    triangles.extend(((a, a + 1, a + columns + 1), (a, a + columns + 1, a + columns)))
            append_cutout(result, material['id'], points, uvs, triangles)
        model['materials'] = [m for m in source['materials'] if solid(m['id'])] + [material]
        model['nodes'] = [{'id': f'{name}-lod{level}', 'parts': [
            {'meshpartid': m['id'], 'materialid': m['id']} for m in model['materials']]}]
        levels[level] = pack(model, f'{name}-lod{level}', result)
        data = levels[level]['meshes'][0]['vertices']
        scale = high.z / max(data[2::12])
        for offset in range(2, len(data), 12):
            data[offset] *= scale
        assert counts(levels[level])['triangles'] <= budget
    return levels


def cactus_levels(source, name):
    """Keep stem topology, wrap ribs around each arm, and replace angular flower shells with shallow cutout cups."""
    vertices, faces, corners = geometry(source)
    body = pack(source, name, [corner for corner in corners if corner[0] == 'cactus'])
    flower_faces = [face for face, (role, _) in zip(faces, corners) if role != 'cactus']
    flowers = []
    for group in parts(len(vertices), flower_faces):
        points = [vertices[i] for j in group for i in flower_faces[j]]
        low = Vector(tuple(min(p[k] for p in points) for k in range(3)))
        high = Vector(tuple(max(p[k] for p in points) for k in range(3)))
        # Each original flower has overlapping inner and outer petal shells.
        overlap = next((i for i, (a, b) in enumerate(flowers)
                        if all(a[k] <= high[k] and low[k] <= b[k] for k in range(3))), None)
        if overlap is None:
            flowers.append((low, high))
        else:
            a, b = flowers[overlap]
            flowers[overlap] = (Vector(tuple(min(a[k], low[k]) for k in range(3))),
                                Vector(tuple(max(b[k], high[k]) for k in range(3))))
    materials = [{'id': 'cactus', 'diffuse': [1, 1, 1], 'textures': [
        {'id': 'cactus', 'type': 'DIFFUSE', 'filename': 'textures/foliage/cactus-skin.png'},
        {'id': 'cactus-normal', 'type': 'NORMAL', 'filename': 'textures/foliage/cactus-skin-normal.png'}]}]
    if flowers:
        materials.append(cutout_material('flower-cutout', 'cactus-flower-cutout'))
    levels = {}
    for level, budget in enumerate((480, 240, 96)):
        petals = (8, 6, 4)[level]
        body_budget = budget - len(flowers) * petals * 2
        if level == 0:
            vs, fs, cs = geometry(body)
            hidden = enclosed_faces(vs, fs)
            model = pack(body, f'{name}-lod{level}', [c for i, c in enumerate(cs) if i not in hidden])
        else:
            model = simplified(body, f'{name}-lod{level}', body_budget, False)
        round_cactus(model)
        vs, fs, cs = geometry(model)
        result = []
        for group in parts(len(vs), fs):
            arm_faces = [fs[i] for i in group]
            arm_points = [vs[i] for face in arm_faces for i in face]
            arm_low = min(p.z for p in arm_points)
            arm_high = max(p.z for p in arm_points)
            # Sections follow the existing elbow and upright stem, keeping bark/ribs attached to the arm.
            section_vertices = arm_points
            section_faces = [list(range(i, i + 3)) for i in range(0, len(arm_points), 3)]
            for index in group:
                attributes, us = [], []
                for vertex in cs[index][1]:
                    p = Vector(vertex[:3])
                    centre = stem_section(section_vertices, section_faces, max(arm_low, min(arm_high, p.z)))
                    u = math.atan2(p.y - centre.y, p.x - centre.x) / (2 * math.pi)
                    us.append(u)
                    attributes.append([*vertex[:6], 1, 1, 1, 1, u * 2, p.z / 4])
                # Do not interpolate across the cylindrical UV seam through the middle of a face.
                if max(us) - min(us) > .5:
                    for vertex, u in zip(attributes, us):
                        if u < 0:
                            vertex[10] += 2
                result.append(('cactus', [tuple(v) for v in attributes]))
        for low, high in flowers:
            centre = (low + high) / 2
            centre.z = low.z
            points, uvs = [centre], [(.5, .5)]
            for i in range(petals):
                angle = 2 * math.pi * i / petals
                p = Vector((centre.x + (high.x - low.x) * .5 * math.cos(angle),
                            centre.y + (high.y - low.y) * .5 * math.sin(angle),
                            low.z + (high.z - low.z) * .4))
                points.append(p)
                uvs.append((.5 + .5 * math.cos(angle), .5 + .5 * math.sin(angle)))
            append_cutout(result, 'flower-cutout', points, uvs,
                          [(0, i + 1, (i + 1) % petals + 1) for i in range(petals)])
        model['materials'] = materials
        model['nodes'] = [{'id': f'{name}-lod{level}', 'parts': [
            {'meshpartid': m['id'], 'materialid': m['id']} for m in materials]}]
        levels[level] = pack(model, f'{name}-lod{level}', result)
        if flowers:
            data = levels[level]['meshes'][0]['vertices']
            scale = max(p.z for p in vertices) / max(data[2::12])
            for offset in range(2, len(data), 12):
                data[offset] *= scale
        assert counts(levels[level])['triangles'] <= budget
    return levels


def prepare(only=None):
    """Rebuild the detail levels of every tree, or only of the named ones."""
    manifest = json.loads((BOARD / 'manifest.json').read_text())
    old_scene = bpy.context.window.scene
    scene = bpy.data.scenes.new('MegaMek tree detail levels')
    bpy.context.window.scene = scene
    try:
        for name, entry in manifest.items():
            if 'source' not in entry or only is not None and name not in only:
                continue
            source_path = BOARD.parents[2] / 'tools/board-models/foliage' / (name + '.glb')
            source = read_glb(source_path)
            for material in source['materials']:
                for texture in material.get('textures', []):
                    texture['filename'] = (source_path.parent / texture['filename']).resolve().relative_to(BOARD).as_posix()
            crowns = (cactus_levels(source, name) if name.startswith('cactus') else
                      palm_crowns(source, name) if name.startswith('palm') else branch_crowns(source, name))
            if crowns is not None:
                entry['mesh'] = name + '.glb'
                entry['lods'] = [{'node': f'{name}-lod{level}', **counts(model)} for level, model in crowns.items()]
                write_glb(BOARD / (name + '.glb'), levels=crowns)
                print(name, 'plant surfaces', [lod['triangles'] for lod in entry['lods']], flush=True)
                continue
            vertices, faces, corners = geometry(source)
            hidden = enclosed_faces(vertices, faces)
            near_name = name + '-lod0'
            near = pack(source, near_name, [corner for index, corner in enumerate(corners) if index not in hidden])
            entry['mesh'] = name + '.glb'
            entry['lods'] = [{'node': near_name, **counts(near)}]
            levels = {0: near}
            budgets = [min(budget, entry['triangles'] // (2 if level == 1 else 5))
                       for level, budget in enumerate(BUDGETS, 1)]
            # Decided once from the farthest level, so every level of a plant keeps one shape.
            hulled = not keeps_outline(source, budgets[-1])
            for level, budget in enumerate(budgets, 1):
                asset = f'{name}-lod{level}'
                # Simplify the closed original, so enclosed surfaces cannot leave
                # holes when the distant canopy changes shape.
                model = simplified(source, asset, budget, hulled)
                levels[level] = model
                entry['lods'].append({'node': asset, **counts(model)})
            write_glb(BOARD / (name + '.glb'), levels=levels)
            # The complete authoring source remains available for geometry and visual review.
            print(name, entry['triangles'], '->',
                  [lod['triangles'] for lod in entry['lods']], flush=True)
        (BOARD / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    finally:
        bpy.context.window.scene = old_scene
        bpy.data.scenes.remove(scene)


def round_cactus(model):
    """Shade the cactus's round stems smoothly; retain every joint, silhouette and texture seam."""
    mesh = model['meshes'][0]
    data, normals = mesh['vertices'], {}
    for part in mesh['parts']:
        if part['id'] != 'cactus':
            continue
        for offset in range(0, len(part['indices']), 3):
            indices = part['indices'][offset:offset + 3]
            points = [Vector(data[i * 12:i * 12 + 3]) for i in indices]
            normal = (points[1] - points[0]).cross(points[2] - points[0])
            for point in points:
                normals.setdefault(tuple(point), Vector())
                normals[tuple(point)] += normal
        for index in set(part['indices']):
            start = index * 12
            normal = normals[tuple(Vector(data[start:start + 3]))].normalized()
            data[start + 3:start + 6] = list(normal)


def solid(role):
    """Roles the game lights as solid rather than as a canopy (GpuTerrain.foliage)."""
    return role.startswith('bark') or role in ('cactus', 'fruit')


def unlit_material(role, filename, images):
    """The game's albedo before lighting: the raw detail texel times the vertex colour, snow neutral."""
    material = bpy.data.materials.new(role)
    material.use_nodes = True
    material.use_backface_culling = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    if filename not in images:
        images[filename] = bpy.data.images.load(str(BOARD / filename), check_existing=True)
        images[filename].colorspace_settings.name = 'Non-Color'
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = images[filename]
    texture.interpolation = 'Linear'
    color = nodes.new('ShaderNodeVertexColor')
    color.layer_name = 'Color'
    product = nodes.new('ShaderNodeVectorMath')
    product.operation = 'MULTIPLY'
    links.new(texture.outputs['Color'], product.inputs[0])
    links.new(color.outputs['Color'], product.inputs[1])
    albedo = product.outputs[0]
    if role in ('snow', 'canopy-snow-cutout'):
        grey = nodes.new('ShaderNodeRGBToBW')
        links.new(albedo, grey.inputs['Color'])
        tint = nodes.new('ShaderNodeVectorMath')
        tint.operation = 'MULTIPLY'
        tint.inputs[1].default_value = (.97, .98, 1.02)
        links.new(grey.outputs['Val'], tint.inputs[0])
        albedo = tint.outputs[0]
    emission = nodes.new('ShaderNodeEmission')
    links.new(albedo, emission.inputs['Color'])
    output = nodes.new('ShaderNodeOutputMaterial')
    if role.endswith('-cutout'):
        threshold = nodes.new('ShaderNodeMath')
        threshold.operation = 'GREATER_THAN'
        threshold.inputs[1].default_value = .5
        links.new(texture.outputs['Alpha'], threshold.inputs[0])
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')
        links.new(threshold.outputs[0], mix.inputs[0])
        links.new(transparent.outputs[0], mix.inputs[1])
        links.new(emission.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], output.inputs['Surface'])
        if hasattr(material, 'surface_render_method'):
            material.surface_render_method = 'DITHERED'
        elif hasattr(material, 'blend_method'):
            material.blend_method = 'CLIP'
    else:
        links.new(emission.outputs[0], output.inputs['Surface'])
    return material


def unlit_mesh(model, name, images):
    """LOD0 with one vertex per corner, so every authored colour and texture coordinate survives."""
    mesh = model['meshes'][0]
    source = mesh['vertices']
    textures = {material['id']: material['textures'][0]['filename'] for material in model['materials']}
    vertices, faces, colors, uvs, roles = [], [], [], [], []
    for part in mesh['parts']:
        for offset in range(0, len(part['indices']), 3):
            faces.append((len(vertices), len(vertices) + 1, len(vertices) + 2))
            roles.append(part['id'])
            for index in part['indices'][offset:offset + 3]:
                vertex = source[index * 12:index * 12 + 12]
                vertices.append(vertex[:3])
                # terrain-foliage.frag multiplies the texel by the display-space colour before converting to linear;
                # the float attribute and the Raw render pass it through unchanged, so it stays display-space here.
                colors.append(vertex[6:10])
                uvs.append((vertex[10], 1 - vertex[11]))
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    color = data.color_attributes.new('Color', 'FLOAT_COLOR', 'CORNER')
    uv = data.uv_layers.new(name='UV')
    for polygon in data.polygons:
        for loop in polygon.loop_indices:
            color.data[loop].color = colors[data.loops[loop].vertex_index]
            uv.data[loop].uv = uvs[data.loops[loop].vertex_index]
    materials = {}
    for polygon, role in zip(data.polygons, roles):
        if role not in materials:
            materials[role] = len(data.materials)
            data.materials.append(unlit_material(role, textures[role], images))
        polygon.material_index = materials[role]
    data.update()
    return data


def bounds(model):
    vertices = model['meshes'][0]['vertices']
    return [min(vertices[i::12]) for i in range(3)], [max(vertices[i::12]) for i in range(3)]


def crown(model, low, high):
    """Height of the cap: the canopy's mean height, or the middle of a plant without one."""
    mesh = model['meshes'][0]
    heights = [mesh['vertices'][index * 12 + 2] for part in mesh['parts'] if not solid(part['id'])
               for index in part['indices']]
    return sum(heights) / len(heights) if heights else (low[2] + high[2]) / 2


# The board camera looks down at trees, so the vertical cards show the plant from this elevation: the canopy then
# covers the trunk as it would in three dimensions, while the cap alone shows from straight above.
ELEVATION = math.radians(30)
# The turns that bring each card's face toward a camera at -y: the front and side faces, each turned about the
# plant's axis before it tips toward the camera (tipping first would roll the side view), then the top.
FACES = tuple((Matrix.Rotation(ELEVATION, 3, 'X') @ Matrix.Rotation(turn, 3, 'Z')).to_euler()
              for turn in (0, -math.pi / 2)) + (Euler((math.pi / 2, 0, 0)),)


def framing(turn, low, high):
    """The square panel framing the turned plant: its size and centre, in the camera's right and up axes."""
    rotation = turn.to_matrix()
    corners = [rotation @ Vector((x, y, z)) for x in (low[0], high[0]) for y in (low[1], high[1])
               for z in (low[2], high[2])]
    lowest = Vector((min(c.x for c in corners), 0, min(c.z for c in corners)))
    highest = Vector((max(c.x for c in corners), 0, max(c.z for c in corners)))
    # A little margin keeps the dilated rim inside its own panel.
    return max(highest.x - lowest.x, highest.z - lowest.z) * 1.04, (lowest + highest) / 2


def dilate(rgba, passes=8):
    """Spread edge colours into transparent texels, so filtering and mipmaps never darken the cutout's rim."""
    rgb, filled = rgba[..., :3].copy(), rgba[..., 3] > 0
    for _ in range(passes):
        if filled.all():
            break
        for shift in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            take = ~filled & numpy.roll(filled, shift, (0, 1))
            rgb[take] = numpy.roll(rgb, shift, (0, 1))[take]
            filled |= take
    return numpy.concatenate([rgb, rgba[..., 3:]], axis=2)


def render_faces(scene, model, name, images, panels):
    """One render of LOD0 turned toward the camera three times, each face filling its own square panel."""
    data = unlit_mesh(model, name, images)
    objects = []
    for panel, (turn, (size, centre)) in enumerate(zip(FACES, panels)):
        obj = bpy.data.objects.new(f'{name}-face{panel}', data)
        scene.collection.objects.link(obj)
        obj.rotation_euler = turn
        obj.scale = (1 / size,) * 3
        obj.location = (panel - 1 - centre.x / size, 0, -centre.z / size)
        objects.append(obj)
    path = BOARD / IMPOSTORS / (name + '.png')
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for material in data.materials:
        bpy.data.materials.remove(material)
    bpy.data.meshes.remove(data)
    rendered = bpy.data.images.load(str(path))
    rendered.colorspace_settings.name = 'Non-Color'
    pixels = numpy.array(rendered.pixels[:], dtype=numpy.float32).reshape(PANEL, 3 * PANEL, 4)
    bpy.data.images.remove(rendered)
    pixels = numpy.concatenate([dilate(pixels[:, i * PANEL:(i + 1) * PANEL]) for i in range(3)], axis=1)
    atlas = bpy.data.images.new(name + '-impostor', 3 * PANEL, PANEL, alpha=True)
    atlas.colorspace_settings.name = 'Non-Color'
    atlas.pixels = pixels.ravel().tolist()
    atlas.filepath_raw = str(path)
    atlas.file_format = 'PNG'
    atlas.save()
    bpy.data.images.remove(atlas)


def shown_normal(model, toward):
    """The mean lighting normal of the surfaces LOD0 turns toward a camera, weighted by their projected area."""
    mesh = model['meshes'][0]
    vertices = mesh['vertices']
    total = Vector()
    for part in mesh['parts']:
        for offset in range(0, len(part['indices']), 3):
            corners = [vertices[i * 12:i * 12 + 12] for i in part['indices'][offset:offset + 3]]
            a, b, c = (Vector(corner[:3]) for corner in corners)
            shown = (b - a).cross(c - a).dot(toward) / 2
            if shown > 0:
                total += sum((Vector(corner[3:6]) for corner in corners), Vector()) * shown
    return total.normalized()


# The sun directions the board's lighting spans: three elevations all round.
SUNS = [Vector((math.cos(turn) * math.cos(elevation), math.sin(turn) * math.cos(elevation), math.sin(elevation)))
        for elevation in map(math.radians, (30, 50, 70)) for turn in (i * math.pi / 4 for i in range(8))]


def lighting(model, toward):
    """How the surfaces LOD0 shows toward a camera take the sun, as terrain-foliage.frag lights them over the board's
    sun directions: the share of direct light that gets past the plant's own leaves and branches, and the share of
    what shows that is bark, cactus or snow, which take light straight on where leaves scatter it around. A card
    standing inside its crown cannot take that shade from the shadow map, which would shade it with its own cards."""
    vertices, faces, corners = geometry(model)
    tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    cutouts = {}
    for material in model['materials']:
        if not material['id'].endswith('-cutout'):
            continue
        image = bpy.data.images.load(str(BOARD / material['textures'][0]['filename']), check_existing=True)
        pixels = numpy.empty(len(image.pixels), dtype=numpy.float32)
        image.pixels.foreach_get(pixels)
        cutouts[material['id']] = pixels.reshape(image.size[1], image.size[0], 4)[:, :, 3]

    def covered(index, point):
        role, attributes = corners[index]
        if role not in cutouts:
            return True
        a, b, c = (vertices[v] for v in faces[index])
        ab, ac, ap = b - a, c - a, point - a
        denominator = ab.dot(ab) * ac.dot(ac) - ab.dot(ac) ** 2
        if abs(denominator) < 1e-9:
            return False
        u = (ac.dot(ac) * ap.dot(ab) - ab.dot(ac) * ap.dot(ac)) / denominator
        v = (ab.dot(ab) * ap.dot(ac) - ab.dot(ac) * ap.dot(ab)) / denominator
        uv = [attributes[0][k] * (1 - u - v) + attributes[1][k] * u + attributes[2][k] * v for k in (10, 11)]
        alpha = cutouts[role]
        x = max(0, min(alpha.shape[1] - 1, int(uv[0] * alpha.shape[1])))
        y = max(0, min(alpha.shape[0] - 1, int((1 - uv[1]) * alpha.shape[0])))
        return alpha[y, x] > .5

    def blocked(point, direction):
        # Offline alpha-aware rays prevent transparent card rectangles from darkening the distant impostor.
        for _ in range(len(faces)):
            hit, _, index, _ = tree.ray_cast(point, direction)
            if hit is None:
                return False
            if covered(index, hit):
                return True
            point = hit + direction * .002
        return False

    lit = total = hard = seen = 0
    for index, (face, (role, attributes)) in enumerate(zip(faces, corners)):
        a, b, c = (vertices[i] for i in face)
        normal = (b - a).cross(c - a)
        shown = normal.dot(toward) / 2
        if shown <= 0:
            continue
        normal.normalize()
        leaves = not solid(role) and role not in ('snow', 'canopy-snow-cutout')
        for u, v in ((1 / 3, 1 / 3), (2 / 3, 1 / 6), (1 / 6, 2 / 3), (1 / 6, 1 / 6)):
            point = a + (b - a) * u + (c - a) * v + normal * .01
            # A point behind the plant's nearer parts does not show on the card.
            if not covered(index, point) or blocked(point, toward):
                continue
            seen += shown
            hard += 0 if leaves else shown
            for sun in SUNS:
                weight = shown * max(0, .6 * normal.dot(sun) + .4 if leaves else normal.dot(sun))
                total += weight
                if weight and not blocked(point, sun):
                    lit += weight
    return (lit / total if total else 1), (hard / seen if seen else 0)


def impostor(scene, model, name, images):
    """LOD3: two crossed vertical cards and a horizontal cap through the crown, textured with unlit orthographic
    renders of LOD0 from the front, the side and above. Fixed in the plant's frame, it draws, shadows and picks like
    any mesh; seen from above, only the cap shows. Each face has a back, as the game culls back faces."""
    low, high = bounds(model)
    cap = crown(model, low, high)
    panels = [framing(turn, low, high) for turn in FACES]
    render_faces(scene, model, name, images, panels)
    vertices, indices = [], []
    corners = (((low[0], 0, low[2]), (high[0], 0, low[2]), (high[0], 0, high[2]), (low[0], 0, high[2])),
               ((0, low[1], low[2]), (0, high[1], low[2]), (0, high[1], high[2]), (0, low[1], high[2])),
               ((low[0], low[1], cap), (high[0], low[1], cap), (high[0], high[1], cap), (low[0], high[1], cap)))
    for panel, (quad, turn, (size, centre)) in enumerate(zip(corners, FACES, panels)):
        rotation = turn.to_matrix()
        # Each side is lit like the surfaces its render shows, by their mean normal: not straight up (a sky-facing
        # card outshines a cactus's walls) and constant across the side (a normal that varied across a flat card
        # would darken the half turned from the light while it stays in view). The back shows the same render
        # mirrored, so its normal mirrors through the card.
        toward = rotation.transposed() @ Vector((0, -1, 0))
        front = shown_normal(model, toward)
        # The colour carries how the card takes the sun: the share its plant's own leaves let through, and how much of
        # what it shows is bark, cactus or snow.
        sunlit, hard = lighting(model, toward)
        plane = (Vector(quad[1]) - Vector(quad[0])).cross(Vector(quad[2]) - Vector(quad[0])).normalized()
        for side, normal in enumerate((front, front - 2 * front.dot(plane) * plane)):
            base = len(vertices) // 12
            for point in quad:
                # Each corner maps to where the render placed it, in the camera's right and up axes.
                seen = rotation @ Vector(point)
                u = (panel + .5 + (seen.x - centre.x) / size) / 3
                v = .5 - (seen.z - centre.z) / size
                vertices.extend(round(value, 6) for value in (*point, *normal, sunlit, hard, 1, 1, u, v))
            indices.extend((base, base + 2, base + 1, base, base + 3, base + 2) if side
                           else (base, base + 1, base + 2, base, base + 2, base + 3))
    asset = f'{name}-lod3'
    return {'id': asset,
            'meshes': [{'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': vertices,
                        'parts': [{'id': 'impostor', 'type': 'TRIANGLES', 'indices': indices}]}],
            'nodes': [{'id': asset, 'parts': [{'meshpartid': 'impostor', 'materialid': 'impostor'}]}],
            'materials': [{'id': 'impostor', 'diffuse': [1, 1, 1], 'alphaTest': .5, 'textures': [
                {'id': 'impostor', 'type': 'DIFFUSE', 'filename': f'{IMPOSTORS}/{name}.png',
                 'wrapS': 33071, 'wrapT': 33071}]}]}


def impostors(only=None):
    """Add or refresh LOD3 of every plant with detail levels, keeping its other levels as they are."""
    manifest = json.loads((BOARD / 'manifest.json').read_text())
    old_scene = bpy.context.window.scene
    scene = bpy.data.scenes.new('MegaMek plant impostors')
    bpy.context.window.scene = scene
    try:
        camera = bpy.data.objects.new('Impostor camera', bpy.data.cameras.new('Impostor camera'))
        scene.collection.objects.link(camera)
        camera.data.type = 'ORTHO'
        camera.data.sensor_fit = 'HORIZONTAL'
        camera.data.ortho_scale = 3
        camera.data.clip_end = 1000
        camera.location = (0, -100, 0)
        camera.rotation_euler = (math.pi / 2, 0, 0)
        scene.camera = camera
        scene.render.engine = 'BLENDER_EEVEE'
        scene.render.resolution_x, scene.render.resolution_y = 3 * PANEL, PANEL
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = True
        scene.render.filter_size = 1.0
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.image_settings.color_depth = '8'
        # Texels store what the game's shader multiplies before lighting, so no display transform applies.
        scene.view_settings.view_transform = 'Raw'
        scene.view_settings.look = 'None'
        if hasattr(scene, 'eevee'):
            scene.eevee.taa_render_samples = 16
        images = {}
        for name, entry in manifest.items():
            if 'lods' not in entry or only is not None and name not in only:
                continue
            path = BOARD / (name + '.glb')
            levels = {level: read_glb(path, level) for level in range(min(3, len(entry['lods'])))}
            for model in levels.values():
                model['materials'] = [material for material in model['materials'] if material['id'] != 'impostor']
            levels[3] = impostor(scene, levels[0], name, images)
            entry['lods'] = entry['lods'][:3] + [{'node': f'{name}-lod3', **counts(levels[3])}]
            write_glb(path, levels=levels)
            print(name, [lod['triangles'] for lod in entry['lods']], flush=True)
        (BOARD / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    finally:
        bpy.context.window.scene = old_scene
        bpy.data.scenes.remove(scene)


if __name__ == '__main__':
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    stage = arguments[0] if arguments else 'all'
    only = set(arguments[1:]) or globals().get('ONLY')
    if stage in ('all', 'trees'):
        prepare(only)
    if stage in ('all', 'impostors'):
        impostors(only)
