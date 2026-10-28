"""Blender --background --factory-startup --python-exit-code 1 --python tools/blender/test_new_mesh.py"""
import addon_utils
import json
from pathlib import Path
import struct
import sys
import tempfile

import bpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
addon_utils.enable('mm_materials', default_set=True)
import mm_materials as addon

# Start from Blender's own default scene, without opening any GLB.
state = bpy.context.scene.mm_materials
assert not state.source and not state.root
bpy.context.preferences.addons['mm_materials'].preferences.root = str(ROOT)
assert addon.data_root(bpy.context) == ROOT
assert bpy.ops.mm_materials.catalog() == {'FINISHED'}
assert 'structures/common/painted-steel.tres' in state.materials
state.material = 'structures/common/painted-steel.tres'
cube = bpy.context.object
assert cube.type == 'MESH' and not cube.data.color_attributes
assert bpy.ops.mm_materials.assign() == {'FINISHED'}
assert cube.active_material['_mm_tres'] == state.material

# Another work-in-progress mesh should neither block nor enter a selection export.
bpy.ops.mesh.primitive_cube_add(location=(20, 0, 0))
unrelated = bpy.context.object
unrelated.name = 'Unrelated unfinished mesh'
unrelated.shape_key_add(name='Basis')
unrelated.select_set(False)
cube.select_set(True)
bpy.context.view_layer.objects.active = cube

with tempfile.TemporaryDirectory(prefix='.mm-new-test-', dir=ROOT / 'data/models/board') as temp:
    target = Path(temp) / 'new-steel-cube.glb'
    # Exercise the actual UI operator, including a save from Edit Mode.
    bpy.ops.object.mode_set(mode='EDIT')
    assert bpy.ops.mm_materials.export_selected(filepath=str(target)) == {'FINISHED'}
    assert bpy.context.object.mode == 'EDIT'
    bpy.ops.object.mode_set(mode='OBJECT')
    assert not state.source, 'Exporting a selection must not bind the entire working scene to that file'
    assert state.export_path == str(target)
    doc, binary = addon.glb.read_glb(target)
    roots = [doc['nodes'][i] for i in doc['scenes'][0]['nodes']]
    assert len(roots) == 1 and roots[0]['name'] == target.stem + '-lod0'
    assert 'mesh' not in roots[0] and roots[0]['children']
    assert not any(n.get('name') == unrelated.name for n in doc['nodes'])
    assert sum(doc['accessors'][p['indices']]['count'] // 3 for m in doc['meshes'] for p in m['primitives']) == 12
    assert all('TEXCOORD_0' in p['attributes'] and 'NORMAL' in p['attributes'] for m in doc['meshes'] for p in m['primitives'])
    expected = ROOT / 'data/models/board/textures/structures/common/painted-steel_albedo.png'
    assert all('bufferView' not in image and addon.glb.image_path(target, image['uri']) == expected for image in doc['images'])
    # Game defaults to white when COLOR_0 is absent; exported colours must also be white.
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            index = primitive['attributes'].get('COLOR_0')
            if index is not None:
                accessor = doc['accessors'][index]
                view = doc['bufferViews'][accessor['bufferView']]
                code, width, white = {5126: ('f', 4, 1), 5123: ('H', 2, 65535), 5121: ('B', 1, 255)}[accessor['componentType']]
                offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
                for i in range(accessor['count']):
                    assert struct.unpack_from('<4' + code, binary, offset + i * view.get('byteStride', 4 * width)) == (white,) * 4
    addon.open_glb(bpy.context, target)
    assert bpy.context.object.active_material['_mm_tres'] == 'structures/common/painted-steel.tres'
    print('NEW_MESH_EXPORT_OK', json.dumps({'lod': roots[0]['name'], 'triangles': 12, 'external_images': len(doc['images'])}))

# Directory changes clear the old catalog instead of offering stale materials.
state.root = str(ROOT / 'nonexistent-library')
assert not state.materials and not state.material
print('LIBRARY_CONFIGURATION_OK')
