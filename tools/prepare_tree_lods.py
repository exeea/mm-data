"""Run with Blender --background --python tools/prepare_tree_lods.py -- [trees|impostors] [names...].

Keep the near mesh's visible triangles and their exact attributes. Remove only
triangles strictly enclosed in another closed component, with no intersection
with that component's surface. Generate the smaller, textured meshes offline;
the renderer never simplifies geometry or changes tree placement.

The impostor stage adds LOD3 to every plant with detail levels (trees, shrubs
and orchard trees): three textured cards carrying unlit renders of LOD0.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_geometry import linear, read_glb, write_glb

import collections
import copy
import json
import math
from pathlib import Path

import bpy
import numpy
from mathutils import Euler, Vector
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


def simplified(source, name, budget):
    vertices, faces, corners = geometry(source)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    materials, roles = {}, []
    for polygon, (role, attributes) in zip(mesh.polygons, corners):
        key = (role, tuple(attributes[0][6:10]))
        if key not in materials:
            materials[key] = len(roles)
            roles.append(key)
            mesh.materials.append(bpy.data.materials.new(role))
        polygon.material_index = materials[key]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new('Tree screen-size detail', 'DECIMATE')
    modifier.ratio = min(1, budget / len(faces))
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    mesh = obj.data
    mesh.calc_loop_triangles()
    result = []
    low = Vector(tuple(min(point[i] for point in vertices) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in vertices) for i in range(3)))
    for triangle in mesh.loop_triangles:
        role, color = roles[triangle.material_index]
        normal = triangle.normal
        n = normal.normalized()
        attributes = []
        for index in triangle.vertices:
            point = mesh.vertices[index].co
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
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    assert len(result) <= budget, (name, len(result), budget)
    return pack(source, name, result)


def counts(model):
    mesh = model['meshes'][0]
    return {'triangles': sum(len(part['indices']) // 3 for part in mesh['parts']),
            'vertices': len(mesh['vertices']) // 12}


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
            vertices, faces, corners = geometry(source)
            hidden = enclosed_faces(vertices, faces)
            near_name = name + '-lod0'
            near = pack(source, near_name, [corner for index, corner in enumerate(corners) if index not in hidden])
            entry['mesh'] = name + '.glb'
            entry['lods'] = [{'node': near_name, **counts(near)}]
            levels = {0: near}
            for level, budget in enumerate(BUDGETS, 1):
                asset = f'{name}-lod{level}'
                budget = min(budget, entry['triangles'] // (2 if level == 1 else 5))
                # Simplify the closed original, so enclosed surfaces cannot leave
                # holes when the distant canopy changes shape.
                model = simplified(source, asset, budget)
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
    if role == 'snow':
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
                colors.append([linear(c) for c in vertex[6:9]] + [vertex[9]])
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
# The turns that bring each card's face toward a camera at -y: the front and side faces, then the top.
FACES = (Euler((ELEVATION, 0, 0)), Euler((ELEVATION, 0, -math.pi / 2)), Euler((math.pi / 2, 0, 0)))


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
        base = len(vertices) // 12
        rotation = turn.to_matrix()
        for point in quad:
            # Every card is lit as the top of one canopy: a normal that varied across a flat card would darken the
            # half turned from the light while it stays in view, and one within the card's plane grazes every light.
            normal = Vector((0, 0, 1))
            # Each corner maps to where the render placed it, in the camera's right and up axes.
            seen = rotation @ Vector(point)
            u = (panel + .5 + (seen.x - centre.x) / size) / 3
            v = .5 - (seen.z - centre.z) / size
            vertices.extend(round(value, 6) for value in (*point, *normal, 1, 1, 1, 1, u, v))
        indices.extend((base, base + 1, base + 2, base, base + 2, base + 3,
                        base, base + 2, base + 1, base, base + 3, base + 2))
    asset = f'{name}-lod3'
    return {'id': asset,
            'meshes': [{'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': vertices,
                        'parts': [{'id': 'impostor', 'type': 'TRIANGLES', 'indices': indices}]}],
            'nodes': [{'id': asset, 'parts': [{'meshpartid': 'impostor', 'materialid': 'impostor'}]}],
            'materials': [{'id': 'impostor', 'diffuse': [1, 1, 1], 'textures': [
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
