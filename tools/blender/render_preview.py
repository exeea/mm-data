"""Optional visual QA: render a mesh with a material assigned through the add-on."""
from pathlib import Path
import sys
import addon_utils
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
addon_utils.enable('mm_materials', default_set=True)
import mm_materials as addon

bpy.context.scene.mm_materials.root = str(ROOT)
scene = addon.open_glb(bpy.context, ROOT / 'data/models/board/scenery/road/road-tunnel.glb')
obj = bpy.context.object
scene.mm_materials.material = 'structures/common/painted-steel.tres'
bpy.ops.mm_materials.assign()

scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 900, 650
scene.render.resolution_percentage = 100
scene.world = bpy.data.worlds.new('Material review world')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.16, .18, .22, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
for name, position, power, size in [('Key', (10, -25, 45), 30000, 25), ('Fill', (-35, -5, 20), 16000, 20)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy, light.shape, light.size = power, 'DISK', size
    light_obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(light_obj)
    light_obj.location = position
    light_obj.rotation_euler = (Vector((0, 10, 10)) - light_obj.location).to_track_quat('-Z', 'Y').to_euler()
camera = bpy.data.cameras.new('Review camera')
camera_obj = bpy.data.objects.new('Review camera', camera)
scene.collection.objects.link(camera_obj)
scene.camera = camera_obj
camera_obj.location = (65, -70, 50)
camera_obj.rotation_euler = (Vector((0, 10, 10)) - camera_obj.location).to_track_quat('-Z', 'Y').to_euler()
camera.type, camera.ortho_scale = 'ORTHO', 78
output = ROOT / '.tmp/blender-addon-preview.png'
output.parent.mkdir(exist_ok=True)
scene.render.filepath = str(output)
bpy.ops.render.render(write_still=True)
print('PREVIEW', output)
