"""Blender integration check for visual browsing, assignment, cache invalidation and rendering."""
import addon_utils
import bmesh
from pathlib import Path
import sys
import tempfile
import time

import bpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MATERIAL_COUNT = sum(1 for _ in (ROOT / 'data/models/board/textures').rglob('*.tres'))
sys.path.insert(0, str(HERE))
addon_utils.enable('mm_materials', default_set=True)
import mm_materials as addon
from mm_materials import palette

bpy.context.preferences.addons['mm_materials'].preferences.root = str(ROOT)
state = bpy.context.scene.mm_materials
settings = bpy.context.scene.mm_palette
assert bpy.ops.mm_materials.catalog() == {'FINISHED'}
cached = palette.library(bpy.context)
assert len(cached['items']) == len(state.materials) == MATERIAL_COUNT
assert all(not item['error'] and item['name'] in cached['icons'] for item in cached['items'])
# Every material remains reachable while each page has a bounded tile count.
for size, (_, capacity, _) in palette.PAGE_LAYOUTS.items():
    settings.size = size
    visited = []
    _, _, pages, total = palette.page_items(bpy.context)
    for page in range(pages):
        settings.page = page
        items, current, _, count = palette.page_items(bpy.context)
        assert current == page and count == total and len(items) <= capacity
        visited.extend(item['name'] for item in items)
    assert visited == [item['name'] for item in cached['items']]
    bpy.ops.mm_materials.palette_page(direction=1)
    assert settings.page == pages - 1
settings.size = 'MEDIUM'
assert settings.page == 0
settings.page = 10
settings.search = 'painted steel'
assert settings.page == 0
assert {item['name'] for item in palette.filtered_items(bpy.context)} == {'structures/common/painted-steel.tres'}
settings.search = ''
settings.folder = 'structures/common'
assert all(item['folder'] == 'structures/common' for item in palette.filtered_items(bpy.context))
settings.search = 'no such material exists'
assert not palette.filtered_items(bpy.context)
assert palette.page_items(bpy.context) == ([], 0, 1, 0)
assert bpy.ops.mm_materials.palette_page(direction=-1) == {'FINISHED'}
settings.search = ''

cube = bpy.context.object
original_material = cube.active_material
settings.assign_on_click = False
assert bpy.ops.mm_materials.palette_pick(material='structures/common/painted-steel.tres') == {'FINISHED'}
assert cube.active_material == original_material
settings.assign_on_click = True
assert bpy.ops.mm_materials.palette_pick(material='structures/common/painted-steel.tres') == {'FINISHED'}
assert cube.active_material['_mm_tres'] == 'structures/common/painted-steel.tres'
bpy.ops.object.mode_set(mode='EDIT')
mesh = bmesh.from_edit_mesh(cube.data)
mesh.faces.ensure_lookup_table()
for face in mesh.faces:
    face.select_set(False)
mesh.faces[0].select_set(True)
assert bpy.ops.mm_materials.palette_pick(material='structures/common/chrome.tres') == {'FINISHED'}
assert cube.material_slots[mesh.faces[0].material_index].material['_mm_tres'] == 'structures/common/chrome.tres'
assert all(cube.material_slots[f.material_index].material['_mm_tres'] == 'structures/common/painted-steel.tres'
           for f in list(mesh.faces)[1:])
bpy.ops.object.mode_set(mode='OBJECT')
cube.select_set(False)
assert bpy.ops.mm_materials.palette_pick(material='structures/common/cast-concrete.tres') == {'FINISHED'}
assert state.material == 'structures/common/cast-concrete.tres'
assert bpy.ops.mm_materials.catalog() == {'FINISHED'}
assert state.material == 'structures/common/cast-concrete.tres', 'Refresh must retain the chosen material'
print('PALETTE_BROWSE_AND_ASSIGN_OK')

# Exercise the worker through the UI operator on a small real-material sample.
state.materials.clear()
for name in ('structures/common/chrome.tres', 'structures/common/cast-concrete.tres', 'structures/common/painted-steel.tres'):
    state.materials.add().name = name
cached = palette.refresh(bpy.context)
before_objects = set(bpy.data.objects.keys())
before_materials = set(bpy.data.materials.keys())
assert bpy.ops.mm_materials.palette_render() == {'FINISHED'}
deadline = time.monotonic() + 180
while palette._job and time.monotonic() < deadline:
    palette.poll_render()
    time.sleep(.1)
assert palette._job is None, 'Thumbnail render timed out'
if bpy.app.timers.is_registered(palette.poll_render):
    bpy.app.timers.unregister(palette.poll_render)
cached = palette.library(bpy.context)
assert all(item['rendered'] and item['target'].is_file() for item in cached['items']), bpy.data.texts['MegaMek Palette Report'].as_string()
assert set(bpy.data.objects.keys()) == before_objects
assert set(bpy.data.materials.keys()) == before_materials
print('PALETTE_BACKGROUND_RENDER_OK')

with tempfile.TemporaryDirectory(prefix='palette-test-', dir=ROOT / '.tmp') as temp:
    root = Path(temp)
    textures = root / 'data/models/board/textures'
    textures.mkdir(parents=True)
    image = bpy.data.images.new('Palette fixture', width=4, height=4)
    image.filepath_raw = str(textures / 'test_albedo.png')
    image.file_format = 'PNG'
    image.save()
    resource = textures / 'test.tres'
    resource.write_text('[gd_resource type="StandardMaterial3D" format=3]\n'
                        '[ext_resource type="Texture2D" path="test_albedo.png" id="1"]\n'
                        '[resource]\nalbedo_texture = ExtResource("1")\n')
    first, _ = palette.thumbnail_path(resource, textures)
    resource.write_text(resource.read_text() + 'roughness = 0.15\n')
    second, _ = palette.thumbnail_path(resource, textures)
    assert first != second
    image.pixels[0] = .2
    image.save()
    third, _ = palette.thumbnail_path(resource, textures)
    assert third != second
    state.root = str(root)
    assert not state.materials and not state.material and settings.folder == 'ALL'
    bpy.ops.mm_materials.catalog()
    assert [item['name'] for item in palette.library(bpy.context)['items']] == ['test.tres']
    resource.write_text(resource.read_text().replace('test_albedo.png', 'missing.png'))
    bpy.ops.mm_materials.catalog()
    assert 'Missing material dependency' in palette.library(bpy.context)['items'][0]['error']
    bpy.data.images.remove(image)
state.root = str(ROOT)
bpy.ops.mm_materials.catalog()
assert len(palette.library(bpy.context)['items']) == MATERIAL_COUNT
addon_utils.disable('mm_materials', default_set=True)
assert not palette._libraries
print('PALETTE_CACHE_ROOT_SWITCH_AND_CLEANUP_OK')
