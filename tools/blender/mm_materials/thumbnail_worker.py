"""Private background worker; launched by the material palette with a JSON request."""
import json
import os
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mm_materials.preview import build_preview


def render(folder):
    request = json.loads((folder / 'request.json').read_text())
    root = Path(request['root'])
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 160
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.32, .35, .4, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32)
    sphere = bpy.context.object
    for face in sphere.data.polygons:
        face.use_smooth = True
    colors = sphere.data.color_attributes.new('Color', 'FLOAT_COLOR', 'CORNER')
    colors.data.foreach_set('color', [1.0] * len(colors.data) * 4)
    material = bpy.data.materials.new('Palette sphere')
    sphere.data.materials.append(material)
    for name, position, power, size in [('Key', (-3, -4, 5), 500, 4), ('Rim', (3, 1, 3), 700, 2)]:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy, light.shape, light.size = power, 'DISK', size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (-obj.location).to_track_quat('-Z', 'Y').to_euler()
    camera = bpy.data.cameras.new('Palette camera')
    obj = bpy.data.objects.new('Palette camera', camera)
    scene.collection.objects.link(obj)
    obj.location = (2.6, -4, 2.2)
    obj.rotation_euler = (-obj.location).to_track_quat('-Z', 'Y').to_euler()
    camera.type, camera.ortho_scale = 'ORTHO', 2.35
    scene.camera = obj
    errors = []
    for item in request['materials']:
        target = Path(item['target'])
        staged = folder / 'sphere.png'
        try:
            build_preview(material, root / item['name'], root)
            # Only this process's disposable images are eligible for cleanup.
            for image in list(bpy.data.images):
                if image.users == 0:
                    bpy.data.images.remove(image)
            scene.render.filepath = str(staged)
            bpy.ops.render.render(write_still=True)
            os.replace(staged, target)
        except Exception as error:
            errors.append(item['name'] + ': ' + str(error))
    (folder / 'result.json').write_text(json.dumps(errors), encoding='utf-8')


if __name__ == '__main__':
    render(Path(sys.argv[sys.argv.index('--') + 1]))
