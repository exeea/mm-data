"""Build small, open wild bushes through Blender MCP or Blender --background --python.

The eight existing bush slots hold four dry and four meadow silhouettes. The
small scatter plant uses the same authoring with its own two biome exports.
Coordinates are metres, Z-up, with roots at zero; runtime scales them uniformly
and places them above tall grass but below half of a gameplay foliage level.
"""
from collections import defaultdict
import json
from math import cos, sin, pi
from pathlib import Path
from random import Random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_geometry import linear, write_glb
from build_foliage_assets import Plant, blender_mesh

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/models/board/scatter'
COLORS = {
    'bark': (.37, .27, .17),
    'dry-bark': (.46, .36, .24),
    'dry-leaf': (.49, .51, .33),
    'dry-tip': (.63, .59, .39),
    'green-leaf': (.27, .43, .14),
    'green-tip': (.43, .55, .23),
}


def leaf(plant, start, direction, length, width, role):
    """A folded lance-shaped leaf, two triangles and their explicit backs."""
    a = Vector(start)
    forward = Vector(direction).normalized()
    side = forward.cross(Vector((0, 0, 1))).normalized() * width
    b = a + forward * length
    middle = a.lerp(b, .45) - Vector((0, 0, width * .35))
    plant.face([a, middle + side, b], 0, role, back=True)
    plant.face([a, b, middle - side], 0, role, back=True)


def bush(dry, variant):
    rng = Random(4137 + variant * 177 + (901 if dry else 0))
    plant = Plant()
    stems = 5 if dry else 6
    bark = 'dry-bark' if dry else 'bark'
    foliage = 'dry-leaf' if dry else 'green-leaf'
    tip_color = 'dry-tip' if dry else 'green-tip'
    for i in range(stems):
        angle = i * 2*pi/stems + rng.uniform(-.27, .27)
        radial = Vector((cos(angle), sin(angle), 0))
        side = Vector((-sin(angle), cos(angle), 0))
        reach = rng.uniform(.34, .49)
        root = radial * rng.uniform(.015, .055)
        middle = radial * reach * .46 + side * rng.uniform(-.045, .045)
        middle.z = rng.uniform(.13, .22)
        tip = radial * reach + side * rng.uniform(-.08, .08)
        tip.z = rng.uniform(.32, .53) * (1 if dry else .85)
        plant.branch(root, middle, .015, role=bark)
        plant.branch(middle, tip, .008, role=bark, coarse=True)
        # Young shoots fill the lower crown without closing the gaps between branches.
        for center in (root.lerp(middle, .72), middle.lerp(tip, .25)):
            for sign in (-1, 1):
                aim = radial * .4 + side * sign + Vector((0, 0, rng.uniform(.12, .4)))
                leaf(plant, center, aim, .065 if dry else .10, .012 if dry else .031, foliage)
        # Forks break up the crown and expose the stems below the leaf sprays.
        for j, sign in enumerate((-1, 1, -1, 1)):
            start = middle.lerp(tip, .08 + j * .22)
            end = start + radial * .055 + side * sign * rng.uniform(.09, .16)
            end.z += rng.uniform(.045, .11)
            plant.branch(start, end, .0045, role=bark, coarse=True)
            direction = (end - start).normalized()
            for position in (.32, .72):
                center = start.lerp(end, position)
                for leaf_side in (-1, 1):
                    aim = direction * .55 + radial * leaf_side * .8 + Vector((0, 0, .25))
                    leaf(plant, center, aim, rng.uniform(.055, .08) if dry else rng.uniform(.085, .12),
                         .015 if dry else .032, foliage if rng.random() < .72 else tip_color)
            leaf(plant, end * .998 + start * .002, direction, .065 if dry else .095,
                 .012 if dry else .025, tip_color)
        # A few short leaves near the main tip keep the woody silhouette legible.
        for sign in (-1, 1):
            leaf(plant, middle.lerp(tip, .86), radial * .6 + side * sign + Vector((0, 0, .35)),
                 .07 if dry else .095, .013 if dry else .026, foliage)
    # All variants retain comparable size without stretching one axis alone.
    # Explicit back faces share their front's vectors: normalize each point only once.
    points = list({id(p): p for face, _, _ in plant.faces for p in face}.values())
    low = min(p.z for p in points)
    height = max(p.z for p in points) - low
    factor = 2.4 / height
    for p in points:
        p.z -= low
        p *= factor
        p.x *= .65
        p.y *= .65
    # Compact crowns leave space around units while their tips stand above the grass.
    assert max(Vector((p.x, p.y)).length for face, _, _ in plant.faces for p in face) <= 1.8
    assert len(plant.faces) <= 800
    return plant


def export_model(obj, name):
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices, shared, parts = [], {}, defaultdict(list)
    for tri in mesh.loop_triangles:
        role = mesh.materials[tri.material_index]['role']
        for vertex_index in tri.vertices:
            p = mesh.vertices[vertex_index].co
            vertex = tuple(round(v, 7) for v in (*p, *tri.normal, 1, 1, 1, 1, 0, 0))
            if vertex not in shared:
                shared[vertex] = len(vertices) // 12
                vertices.extend(vertex)
            parts[role].append(shared[vertex])
    model = {'id': name, 'meshes': [{'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'],
             'vertices': vertices, 'parts': [{'id': role, 'type': 'TRIANGLES', 'indices': indices}
                                           for role, indices in parts.items()]}],
             'materials': [{'id': role, 'diffuse': COLORS[role]} for role in parts],
             'nodes': [{'id': name + '-lod0', 'parts': [{'meshpartid': role, 'materialid': role}
                                                       for role in parts]}]}
    write_glb(OUT / (name + '.glb'), model)
    height = max(v.co.z for v in mesh.vertices) - min(v.co.z for v in mesh.vertices)
    return {'triangles': len(mesh.loop_triangles), 'height': round(height, 4),
            'radius': round(max(Vector((v.co.x, v.co.y)).length for v in mesh.vertices), 4)}


def build():
    scene = bpy.data.scenes.new('Scatter bushes')
    bpy.context.window.scene = scene
    scene.unit_settings.system = 'METRIC'
    materials = {}
    for role, color in COLORS.items():
        material = bpy.data.materials.new('scatter-' + role)
        material['role'] = role
        material.diffuse_color = (*[linear(c) for c in color], 1)
        material.use_nodes = True
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = material.diffuse_color
        shader.inputs['Roughness'].default_value = .9
        materials[role] = material
    summary = {}
    for i in range(10):
        dry = i < 4 or i == 9
        variant = i % 4 if i < 8 else 0
        name = f'bush-{i}' if i < 8 else 'plant' if i == 8 else 'plant-dry'
        obj = blender_mesh(scene, name + '-lod0', bush(dry, variant), materials)
        obj['biome'] = 'sand/rock' if dry else 'green fields'
        obj['cosmetic'] = True
        bpy.context.view_layer.update()
        summary[name] = export_model(obj, name)
        obj.location = ((i % 4) * 4.8, -(i // 4) * 4.5, 0)
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    scene.world = bpy.data.worlds.new('Scatter studio')
    scene.world.color = (.25, .25, .25)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 950
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'Standard'
    # Save an editable scene independent of the unrelated board asset scene.
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'tools/board-scatter.blend'), copy=True)
    report = ROOT / 'tools/board-models/scatter/mesh-report.json'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + '\n')
    return scene, summary


if __name__ == '__main__':
    scene, summary = build()
    print(json.dumps(summary))
