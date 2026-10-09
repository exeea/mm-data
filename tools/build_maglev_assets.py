"""Render the palette thumbnail of the maglev train stamp from its rows in layouts.json.

Run with Blender's --background --factory-startup --python option, after build_scenery_assets.py,
which owns the maglev pieces and rows: each legacy maglev key (scenery/fluff/maglev*) decodes to a
route marker row, which carries the route's sides as "connections", and its platform, vehicle and
parked-car rows (see MAGLEV there); scenery/maglev/train is the palette's train stamp (a wagon, a
cab and their coupler). This script only renders scenery/maglev/train.png from those rows.
"""
import json
import sys
from math import radians
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from mathutils import Euler, Vector

from build_scenery_assets import BOARD


def thumbnail(rows, target):
    """A transparent 256x160 view of rows in vertex colours, the size of the editor's palette previews."""
    scene = bpy.context.scene
    for item in list(bpy.data.objects):
        bpy.data.objects.remove(item)
    # The rows turn as one, so the vehicle lies across the image with the cab's nose to the right.
    root = bpy.data.objects.new('rows', None)
    scene.collection.objects.link(root)
    root.rotation_euler = Euler((0, 0, radians(-90)))
    for row in rows:
        holder = bpy.data.objects.new(row['asset'], None)
        scene.collection.objects.link(holder)
        holder.parent = root
        holder.location = row['position']
        holder.rotation_euler = Euler((0, 0, radians(row['rotation'])))
        holder.scale = (row['scale'],) * 3
        bpy.ops.import_scene.gltf(filepath=str(BOARD / (row['asset'] + '.glb')))
        for item in bpy.context.selected_objects:
            if item.parent is None:
                item.parent = holder
    camera = bpy.data.objects.new('camera', bpy.data.cameras.new('camera'))
    scene.collection.objects.link(camera)
    camera.data.type = 'ORTHO'
    # The palette's three-quarter view: from the south-east, 40 degrees above the ground.
    camera.data.ortho_scale = 72
    camera.rotation_euler = Euler((radians(50), 0, radians(35)))
    camera.location = camera.rotation_euler.to_matrix() @ Vector((0, 0, 120))
    scene.camera = camera
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'VERTEX'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x, scene.render.resolution_y = 256, 160
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)


def build():
    catalog = json.loads((BOARD / 'scenery/layouts.json').read_text(encoding='utf-8'))
    thumbnail(catalog['scenery/maglev/train'], BOARD / 'scenery/maglev/train.png')


if __name__ == '__main__':
    build()
