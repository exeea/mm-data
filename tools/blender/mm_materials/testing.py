"""Authoring UI for the engine's asset checks and connected-kit placements.

No connection or stacking rules live here. The engine returns display transforms
for a temporary export; a separate Blender scene displays that snapshot.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, IntVectorProperty, PointerProperty, StringProperty
from mathutils import Matrix, Vector

_job = None


def authoring_scene(context):
    return context.scene.mm_asset_test.source_scene or context.scene


def engine_root(context):
    from . import data_root
    prefs = context.preferences.addons[__package__].preferences
    if prefs.engine:
        root = Path(bpy.path.abspath(prefs.engine)).resolve()
    else:
        parent = data_root(context).parent
        root = next((parent / name for name in ('megamek_temp', 'megamek')
                     if (parent / name / 'gradlew.bat').is_file()), parent / 'megamek')
    if not (root / 'gradle/wrapper/gradle-wrapper.jar').is_file():
        raise ValueError('Set the MegaMek engine checkout (containing gradlew and gradle/wrapper)')
    return root


def runtime(context):
    root = engine_root(context)
    path = root / 'megamek/build/blender-preview.json'
    if not path.is_file():
        raise ValueError('Click Build / Refresh Engine first (requires the engine JDK and Gradle dependencies)')
    config = json.loads(path.read_text(encoding='utf-8'))
    return root, [config['java'], '-Djava.awt.headless=true', '-cp', config['classpath'],
                  'megamek.client.ui.clientGUI.boardview.gpu.BlenderAssetPreview']


def snapshot(context, folder):
    from . import save_glb, data_root
    scene = authoring_scene(context)
    settings = scene.mm_asset_test
    old = context.window.scene
    try:
        context.window.scene = scene
        model = folder / 'asset.glb'
        save_glb(context, model, selected=settings.selected, snapshot=True)
        request = dict(model=str(model), modelsRoot=str(data_root(context) / 'data/models'), kind=settings.kind,
                       lod=settings.lod, height=settings.height, reach=list(settings.reach),
                       rotation=settings.rotation, seed=settings.seed)
        (folder / 'request.json').write_text(json.dumps(request), encoding='utf-8')
        return request
    finally:
        context.window.scene = old


def remove_preview(scene):
    """Only delete the scene and unused datablocks created for this preview."""
    owned = json.loads(scene.get('_mm_test_owned', '{}'))
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    for category in ('meshes', 'materials', 'images', 'collections'):
        collection = getattr(bpy.data, category)
        for name in owned.get(category, []):
            block = collection.get(name)
            if block and block.users == 0:
                collection.remove(block)


def show_preview(context, source, folder, result, request):
    from . import open_glb, export_name
    previous = context.window.scene
    categories = ('meshes', 'materials', 'images', 'collections')
    before = {key: set(getattr(bpy.data, key).keys()) for key in categories}
    scene = None
    try:
        # Import the tested export, including applied modifiers, instead of guessing
        # how Blender's exporter transformed the live meshes.
        scene = open_glb(context, folder / 'asset.glb')
        scene.name = source.name + ' — Asset Test'
        scene.mm_asset_test.source_scene = source
        scene.mm_materials.source = ''
        scene.mm_asset_test.kind = request['kind']
        originals = list(scene.objects)
        context.view_layer.update()
        if request['kind'] == 'KIT':
            by_name = {export_name(obj): obj for obj in originals}
            for index, instance in enumerate(result['instances']):
                original = by_name[instance['node']]
                obj = bpy.data.objects.new(f'Test {index}: {instance["node"]}', original.data)
                scene.collection.objects.link(obj)
                # libGDX returns column-major matrices in the same Z-up space as Blender.
                m = instance['matrix']
                obj.matrix_world = Matrix([m[i:i + 4] for i in range(0, 16, 4)]).transposed() @ original.matrix_world
                obj.hide_select = True
            for obj in originals:
                bpy.data.objects.remove(obj, do_unlink=True)
        else:
            for obj in originals:
                root = obj
                while root.parent:
                    root = root.parent
                name = export_name(root)
                helper = name in ('cut', 'stands')
                obj.hide_set(not (name.endswith('-lod' + str(result['lod'])) or helper))
                if helper:
                    obj.display_type = 'WIRE'
                    obj.show_in_front = True
                    obj.hide_render = True
                    obj.empty_display_type = 'ARROWS'
                    obj.empty_display_size = 2
                obj.hide_select = True
        scene['_mm_test_owned'] = json.dumps({key: sorted(set(getattr(bpy.data, key).keys()) - before[key])
                                              for key in categories})
        context.view_layer.update()
        corners = [obj.matrix_world @ Vector(corner) for obj in scene.objects
                   if obj.type == 'MESH' and obj.visible_get() and obj.display_type != 'WIRE' for corner in obj.bound_box]
        if corners and context.screen:
            low = Vector([min(v[i] for v in corners) for i in range(3)])
            high = Vector([max(v[i] for v in corners) for i in range(3)])
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    view = area.spaces.active.region_3d
                    view.view_location = (low + high) / 2
                    view.view_distance = max(2, (high - low).length * 1.2)
        old_preview = source.mm_asset_test.preview_scene
        source.mm_asset_test.preview_scene = scene
        if old_preview:
            remove_preview(old_preview)
        return scene
    except Exception:
        context.window.scene = previous
        if scene:
            scene['_mm_test_owned'] = json.dumps({key: sorted(set(getattr(bpy.data, key).keys()) - before[key])
                                                  for key in categories})
            remove_preview(scene)
        raise


def report(scene, message):
    scene.mm_asset_test.status = message
    text = bpy.data.texts.get('MegaMek Asset Test Report') or bpy.data.texts.new('MegaMek Asset Test Report')
    text.clear()
    text.write(message)


def discard_preview(source, window):
    preview = source.mm_asset_test.preview_scene
    if preview:
        if window.scene == preview:
            window.scene = source
        remove_preview(preview)


def launch(scene, command, cwd, folder, *, request=None, temporary=None):
    global _job
    if _job:
        raise ValueError('An engine build or asset test is already running')
    log = (folder / 'engine.log').open('w', encoding='utf-8')
    try:
        process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except Exception:
        log.close()
        if temporary:
            temporary.cleanup()
        raise
    _job = dict(scene=scene, process=process, log=log, folder=folder, request=request, temporary=temporary,
                window=bpy.context.window)
    report(scene, 'Testing current edits…' if request else 'Building engine bridge…')
    bpy.app.timers.register(poll_job, first_interval=.2)


def poll_job():
    global _job
    job = _job
    if not job:
        return None
    if job['process'].poll() is None:
        return .2
    _job = None
    job['log'].close()
    scene = job['scene']
    try:
        try:
            scene.name
        except ReferenceError:
            return None
        if job['process'].returncode:
            raise ValueError((job['folder'] / 'engine.log').read_text(encoding='utf-8', errors='replace')[-6000:])
        if job['request']:
            result = json.loads((job['folder'] / 'result.json').read_text(encoding='utf-8'))
            if not result['ok']:
                raise ValueError(result['error'])
            with bpy.context.temp_override(window=job['window']):
                show_preview(bpy.context, scene, job['folder'], result, job['request'])
            report(scene, 'PASS: ' + result['summary'] + '. Snapshot of edits when Test was clicked.')
        else:
            report(scene, 'Engine ready. Click Test Current Edits.')
    except Exception as error:
        # Remove a previous successful display so a failed test cannot look like a pass.
        discard_preview(scene, job['window'])
        report(scene, 'FAIL: ' + str(error))
    finally:
        if job['temporary']:
            job['temporary'].cleanup()
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    return None


class MMTestState(bpy.types.PropertyGroup):
    source_scene: PointerProperty(type=bpy.types.Scene)
    preview_scene: PointerProperty(type=bpy.types.Scene)
    kind: EnumProperty(name='Test', items=[('KIT', 'Building / Connected Kit', 'Engine module, link/end, corner and height checks'),
                                         ('RIGID', 'Rigid Asset / Scenery', 'Engine GLB load, LOD, cut and stands inspection')])
    selected: BoolProperty(name='Selected objects only', description='For new meshes: select every part and authored LOD group')
    lod: IntProperty(name='LOD', min=0, max=3)
    height: IntProperty(name='Building levels', min=1, max=100, default=1)
    reach: IntVectorProperty(name='Connections', size=6, min=0, max=100, default=(1, 0, 0, 0, 0, 0),
                             description='Connected levels in this direction; 0 means no connection')
    rotation: IntProperty(name='Clockwise sixth-turns', min=0, max=5)
    seed: IntProperty(name='Variant seed', min=0)
    status: StringProperty(default='Test the current edits without saving over the GLB.')


class MM_OT_test_build(bpy.types.Operator):
    bl_idname = 'mm_materials.test_build'
    bl_label = 'Build / Refresh Engine'

    def execute(self, context):
        try:
            from . import data_root
            root = engine_root(context)
            java = shutil.which('java')
            if not java:
                candidate = Path(os.environ.get('JAVA_HOME', '')) / 'bin/java.exe'
                java = str(candidate) if candidate.is_file() else None
            if not java:
                raise ValueError('Install the engine JDK and put java on PATH, or set JAVA_HOME')
            folder = data_root(context) / '.tmp/blender-engine'
            folder.mkdir(parents=True, exist_ok=True)
            command = [java, '-cp', str(root / 'gradle/wrapper/gradle-wrapper.jar'),
                       'org.gradle.wrapper.GradleWrapperMain', ':megamek:prepareBlenderPreview', '--console=plain']
            launch(authoring_scene(context), command, root, folder)
            return {'FINISHED'}
        except Exception as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}


class MM_OT_test_run(bpy.types.Operator):
    bl_idname = 'mm_materials.test_run'
    bl_label = 'Test Current Edits'
    bl_description = 'Export a temporary snapshot, validate with the engine, and show its assembly in a separate scene'

    def execute(self, context):
        temporary = None
        try:
            from . import data_root
            if _job:
                raise ValueError('An engine build or asset test is already running')
            root, command = runtime(context)
            temporary = tempfile.TemporaryDirectory(prefix='.mm-test-', dir=data_root(context) / 'data/models')
            folder = Path(temporary.name)
            source = authoring_scene(context)
            request = snapshot(context, folder)
            launch(source, command + [str(folder / 'request.json'), str(folder / 'result.json')], root, folder,
                   request=request, temporary=temporary)
            return {'FINISHED'}
        except Exception as error:
            if temporary:
                temporary.cleanup()
            source = authoring_scene(context)
            discard_preview(source, context.window)
            report(source, 'FAIL: ' + str(error))
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}


class MM_OT_test_return(bpy.types.Operator):
    bl_idname = 'mm_materials.test_return'
    bl_label = 'Return to Authoring'

    def execute(self, context):
        preview = context.scene
        source = preview.mm_asset_test.source_scene
        if source:
            context.window.scene = source
            remove_preview(preview)
        return {'FINISHED'}


class MM_PT_test(bpy.types.Panel):
    bl_label = 'Asset Test'
    bl_idname = 'MM_PT_asset_test'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MegaMek'
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = authoring_scene(context).mm_asset_test
        prefs = context.preferences.addons[__package__].preferences
        controls = layout.column()
        controls.enabled = _job is None
        controls.prop(settings, 'kind')
        controls.prop(settings, 'selected')
        controls.prop(settings, 'lod')
        if settings.kind == 'KIT':
            controls.prop(settings, 'height')
            controls.label(text='Connected levels (0 = no connection)')
            for i, name in enumerate(('North', 'North-east', 'South-east', 'South', 'South-west', 'North-west')):
                controls.prop(settings, 'reach', index=i, text=name)
            controls.prop(settings, 'rotation')
            controls.prop(settings, 'seed')
        controls.operator('mm_materials.test_run', icon='PLAY')
        if context.scene.mm_asset_test.source_scene:
            controls.operator('mm_materials.test_return', icon='LOOP_BACK')
        box = layout.box()
        for line in textwrap.wrap(settings.status, width=max(28, int(context.region.width / 7)))[:16]:
            box.label(text=line)
        layout.label(text='Full result: Text Editor → MegaMek Asset Test Report')
        layout.label(text='Blender shading; game lighting may differ.')
        header, body = layout.panel('mm_engine_setup', default_closed=True)
        header.label(text='Engine Setup')
        if body:
            body.enabled = _job is None
            body.prop(prefs, 'engine', text='Checkout')
            if not prefs.engine:
                body.label(text='Auto: sibling MegaMek checkout')
            body.operator('mm_materials.test_build', icon='FILE_REFRESH')


_classes = (MMTestState, MM_OT_test_build, MM_OT_test_run, MM_OT_test_return, MM_PT_test)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mm_asset_test = PointerProperty(type=MMTestState)
    bpy.app.handlers.load_pre.append(stop_job)


@bpy.app.handlers.persistent
def stop_job(*args):
    global _job
    if _job:
        job = _job
        _job = None
        job['process'].terminate()
        try:
            job['process'].wait(timeout=2)
        except subprocess.TimeoutExpired:
            job['process'].kill()
            job['process'].wait(timeout=2)
        job['log'].close()
        if job['temporary']:
            job['temporary'].cleanup()
    if bpy.app.timers.is_registered(poll_job):
        bpy.app.timers.unregister(poll_job)


def unregister():
    stop_job()
    bpy.app.handlers.load_pre.remove(stop_job)
    del bpy.types.Scene.mm_asset_test
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
