"""Blender background integration: walls, helpers, emission and the real engine test panel."""
import addon_utils
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
addon_utils.enable('mm_materials', default_set=True)
import mm_materials as addon
from mm_materials import testing

bpy.context.preferences.addons['mm_materials'].preferences.root = str(ROOT)
bpy.context.preferences.addons['mm_materials'].preferences.engine = str(ROOT.parent / 'megamek_temp')


def topology(doc):
    nodes = doc['nodes']
    return sorted((node.get('name', ''), tuple(sorted(nodes[i].get('name', '') for i in node.get('children', []))))
                  for node in nodes)


def emissions(doc):
    return {m['name']: m['emissiveFactor'] for m in doc.get('materials', []) if any(m.get('emissiveFactor', []))}


def close_scene(scene):
    bpy.context.window.scene = bpy.data.scenes['Scene']
    for obj in list(scene.objects):
        mesh = obj.data if obj.type == 'MESH' else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.data.scenes.remove(scene)


def check_ui():
    assert bpy.ops.mm_materials.test_run() == {'FINISHED'}
    deadline = time.monotonic() + 90
    while testing._job and time.monotonic() < deadline:
        testing.poll_job()
        time.sleep(.1)
    assert testing._job is None, 'Engine test timed out'
    if bpy.app.timers.is_registered(testing.poll_job):
        bpy.app.timers.unregister(testing.poll_job)


with tempfile.TemporaryDirectory(prefix='.mm-contract-test-', dir=ROOT / 'data/models') as temporary:
    folder = Path(temporary)
    for path in sorted((ROOT / 'data/models/buildings/walls').rglob('*.glb')):
        original, _ = addon.glb.read_glb(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        scene = addon.open_glb(bpy.context, path)
        target = folder / 'wall.glb'
        addon.save_glb(bpy.context, target, snapshot=True)
        saved, _ = addon.glb.read_glb(target)
        assert topology(saved) == topology(original), path
        assert emissions(saved).keys() == emissions(original).keys(), path
        for name, factors in emissions(original).items():
            assert max(abs(a - b) for a, b in zip(factors, emissions(saved)[name])) < 1e-6, name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        assert scene.mm_materials.source == str(path), 'Snapshot changed the authoring save destination'
        close_scene(scene)
    print('PASS: all 18 walls retain hierarchy, link names and lamp emission')

    # Ground cut primitives can have positions only. Marker transforms and repeated
    # part-N names under different LOD/cut parents must survive Blender name collisions.
    for name in ('fortification', 'trench'):
        path = ROOT / f'data/models/board/scenery/military/{name}.glb'
        original, _ = addon.glb.read_glb(path)
        scene = addon.open_glb(bpy.context, path)
        target = folder / (name + '.glb')
        addon.save_glb(bpy.context, target, snapshot=True)
        saved, _ = addon.glb.read_glb(target)
        assert topology(saved) == topology(original), name
        scene.mm_asset_test.kind = 'RIGID'
        scene.mm_asset_test.lod = 1
        check_ui()
        assert scene.mm_asset_test.status.startswith('PASS:'), scene.mm_asset_test.status
        assert bpy.context.scene.mm_asset_test.source_scene == scene
        assert any(o.display_type == 'WIRE' for o in bpy.context.scene.objects if o.type == 'MESH')
        bpy.ops.mm_materials.test_return()
        close_scene(scene)
    print('PASS: cut, stands, part-N and engine scenery checks')

    path = ROOT / 'data/models/buildings/walls/heavy/pier.glb'
    scene = addon.open_glb(bpy.context, path)
    settings = scene.mm_asset_test
    settings.height = 3
    settings.reach = (1, 3, 0, 2, 0, 0)
    settings.rotation = 2
    settings.lod = 1
    source_names = {o.name for o in scene.objects}
    check_ui()
    assert settings.status.startswith('PASS:'), settings.status
    preview = bpy.context.scene
    assert preview.mm_asset_test.source_scene == scene
    assert {o.name for o in scene.objects} == source_names
    assert len(preview.objects) > 10
    try:
        addon.save_glb(bpy.context, folder / 'do-not-export-preview.glb')
        raise AssertionError('Preview export was allowed')
    except ValueError as error:
        assert 'Return to Authoring' in str(error)
    bpy.ops.mm_materials.test_return()
    assert bpy.context.scene == scene and not settings.preview_scene
    check_ui()
    assert bpy.context.scene.mm_asset_test.source_scene == scene
    # The engine, not a duplicate Python regexp, reports a malformed kit node.
    mesh = next(o for o in scene.objects if o.type == 'MESH' and '-lod0-' in addon.export_name(o))
    mesh.name = addon.export_name(mesh) + '-bad-tag'
    check_ui()
    assert settings.status.startswith('FAIL:') and 'Expected -baseN' in settings.status, settings.status
    assert bpy.context.scene == scene and not settings.preview_scene, 'A failed retest retained a stale successful preview'
    close_scene(scene)
    print('PASS: engine assembly, uneven connection heights, rotation, LOD, isolated preview and invalid tags')

    # A synthetic corner kit supplies every link/end combination for both tags,
    # across all module roles and two LODs. No shipped asset currently uses end tags.
    scene = bpy.data.scenes.new('Corner authoring test')
    bpy.context.window.scene = scene
    scene.mm_materials.root = str(ROOT)
    corner_material = bpy.data.materials.new('Corner test material')
    for lod in range(2):
        root = bpy.data.objects.new(f'corner-lod{lod}', None)
        scene.collection.objects.link(root)
        for role in ('base0', 'floor0', 'roof0'):
            for first, second in (('link', 'link'), ('link', 'end'), ('end', 'link'), ('end', 'end')):
                bpy.ops.mesh.primitive_cube_add(size=1)
                obj = bpy.context.object
                obj.data.materials.append(corner_material)
                obj.name = f'corner-lod{lod}-{role}-{first}-n-{second}-ne'
                obj.parent = root
                obj.dimensions = (4, 4, 2 if role == 'roof0' else 18)
                obj.location = (0, 15, obj.dimensions.z / 2)
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    engine, command = testing.runtime(bpy.context)
    settings = scene.mm_asset_test
    for mask in (0, 1, 3, 21, 63):
        settings.reach = [1 if mask & (1 << i) else 0 for i in range(6)]
        settings.lod = 1
        request = testing.snapshot(bpy.context, folder)
        subprocess.run(command + [str(folder / 'request.json'), str(folder / 'result.json')], cwd=engine, check=True)
        result = json.loads((folder / 'result.json').read_text())
        assert result['ok'], result
        assert len(result['instances']) == 12, (mask, result)
        expected = []
        for direction in range(6):
            first = 'link' if mask & (1 << direction) else 'end'
            second = 'link' if mask & (1 << ((direction + 1) % 6)) else 'end'
            expected.extend(f'corner-lod1-{role}-{first}-n-{second}-ne' for role in ('base0', 'roof0'))
        assert sorted(i['node'] for i in result['instances']) == sorted(expected)
    preview = testing.show_preview(bpy.context, scene, folder, result, request)
    centers = [obj.matrix_world.translation for obj in preview.objects if '-base0-' in obj.name]
    assert len(centers) == 6
    assert all(abs(point.z - 9) < 1e-4 and abs(point.xy.length - 15) < 1e-4 for point in centers), centers
    tops = [obj.matrix_world @ Vector(corner) for obj in preview.objects for corner in obj.bound_box]
    assert abs(max(point.z for point in tops) - 20) < 1e-4
    bpy.ops.mm_materials.test_return()
    close_scene(scene)
    print('PASS: two-tag corners and link/end conjunctions across five connection masks')

    # A single GLB mixes a library material, a packed custom emissive texture and
    # an imported model-level emissive map on a shared material.
    scene = addon.open_glb(bpy.context, ROOT / 'data/models/board/scenery/road/road-tunnel.glb')
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 50))
    obj = bpy.context.object
    obj.name = 'embedded-lamp'
    root = next(o for o in scene.objects if addon.export_name(o).endswith('-lod0'))
    obj.parent = root
    mat = bpy.data.materials.new('custom-emissive')
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Emission Color'].default_value = (1, .012, .003, 1)
    shader.inputs['Emission Strength'].default_value = 1
    image = bpy.data.images.new('Embedded lamp map', width=4, height=4)
    image.generated_color = (1, 0, 0, 1)
    image.pack()
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    mat.node_tree.links.new(tex.outputs['Color'], shader.inputs['Emission Color'])
    obj.data.materials.append(mat)
    target = folder / 'mixed.glb'
    addon.save_glb(bpy.context, target, snapshot=True)
    doc, binary = addon.glb.read_glb(target)
    assert any('uri' in image for image in doc['images'])
    assert any('bufferView' in image for image in doc['images'])
    local = next(m for m in doc['materials'] if m['name'] == 'custom-emissive')
    assert 'emissiveTexture' in local
    linked = next(m for m in doc['materials'] if m['name'] != 'custom-emissive')
    linked['emissiveTexture'] = local['emissiveTexture']
    linked['emissiveFactor'] = [.3, .02, .01]
    addon.glb.write_glb(target, doc, binary)
    close_scene(scene)
    scene = addon.open_glb(bpy.context, target)
    managed = next(m for m in bpy.data.materials if m.get('_mm_model_emission'))
    assert managed.get('_mm_emission_image')
    addon.save_glb(bpy.context, folder / 'mixed-again.glb', snapshot=True)
    saved, _ = addon.glb.read_glb(folder / 'mixed-again.glb')
    linked_again = next(m for m in saved['materials'] if m['name'] == linked['name'])
    assert 'emissiveTexture' in linked_again
    assert max(abs(a - b) for a, b in zip(linked_again['emissiveFactor'], linked['emissiveFactor'])) < 1e-6
    close_scene(scene)
    print('PASS: mixed external / packed images, emission and shared-material model emission')

print('ALL ASSET TESTS PASSED')
