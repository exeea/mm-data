"""Render actual exports, never the authoring meshes, in isolated review scenes."""
import bpy, json, importlib.util
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[2]/'data/models/buildings/turrets/modular'
spec=importlib.util.spec_from_file_location('turret_shell',ROOT/'shell.py')
ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)

def load(name,lod):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(OUT/(name+'.glb')))
    added=set(bpy.context.scene.objects)-before
    root=next(o for o in added if o.parent is None and o.name.split('.')[0].endswith(f'-lod{lod}'))
    keep={root,*root.children_recursive}
    for obj in added-keep: bpy.data.objects.remove(obj,do_unlink=True)
    return root

def render(fixture,lod=0):
    label='Modular review '+fixture['name']+f' LOD{lod}'
    if label in bpy.data.scenes:
        scene=bpy.data.scenes[label]
        for obj in list(scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.scenes.remove(scene)
    scene=bpy.data.scenes.new(label);bpy.context.window.scene=scene
    name='head-'+fixture['head'];load(name,lod)
    desc=json.loads((OUT/(name+'.json')).read_text())
    sockets={p['id']:p for p in desc['hardpoints']}
    for sid,module in fixture['modules']:
        point=sockets[sid];root=load(module,lod)
        md=json.loads((OUT/(module+'.json')).read_text())
        dims=[hi-lo for hi,lo in zip(md['bounds']['max'],md['bounds']['min'])]
        scale=min(1,point['size'][0]/dims[0],point['size'][2]/dims[2])
        root.scale=(scale,)*3
        root.location=Vector(point['position'])+Vector((0,0,2.8))
    ref.studio();scene.cycles.samples=24
    scene.render.resolution_x=1100;scene.render.resolution_y=900
    ref.camera('Review',(43,55,37),(0,5,8),52)
    path=ROOT/'renders'/f'{fixture["name"]}-lod{lod}.png'
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    return str(path)
