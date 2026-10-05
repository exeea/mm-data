"""Reproducible Blender review scenes for the joined port cranes and geothermal props."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

import build_scenery_assets as kit


def review(kind):
    layouts=json.loads((kit.REVIEW/'layouts.json').read_text())
    scene=bpy.data.scenes.new('Scenery review / '+kind)
    bpy.context.window.scene=scene
    scene.world=bpy.data.worlds.new(kind+' studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.23,.26,.30,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'
    ground=kit.Mesh()
    if kind=='geysers':
        for i,state in enumerate(('water_off','water_on','magma')):
            name='saxarba/misc/geyser_'+state+'.png';location=((i-1)*50,0,0)
            kit.blender_mesh(scene,name,kit.build_mesh(name,layouts),location)
        target=Vector((0,0,7));camera_position=(65,-140,98);scale=170
        ground.box((0,0,-1),(157,55,2),(.37,.38,.34))
    elif kind=='demolition':
        names=['saxarba/misc/fortified.png']+['saxarba/misc/rubble_'+kind+'.png'
                for kind in ('light','medium','heavy','hardened','wall')]
        names+=['saxarba/rubble_'+kind+'_path.png' for kind in ('light','medium','heavy','hardened','wall')]
        for i,name in enumerate(names):
            kit.blender_mesh(scene,name,kit.build_mesh(name,layouts),((i%4)*85,-(i//4)*85,0))
        target=Vector((127,-85,3));camera_position=target+Vector((190,-320,330));scale=470
        ground.box((127,-85,-1.1),(370,260,2),(.40,.41,.39))
    else:
        for direction in range(1,7):
            name=next(n for n,v in layouts.items() if 'crane' in v and not v['crane']['tip']
                      and v['crane']['direction']==direction)
            c=layouts[name]['crane'];base=((direction-1)%3*210,-((direction-1)//3)*210,0)
            tip=tuple(base[i]+c['neighbor'][i] for i in (0,1))+(0,)
            tip_name='saxarba/SMV_Seaport/SeaportSystem-02-ShipToShoreGantryCrane-03-CraneTip-1-'+f'{direction:02d}.png'
            for source,location in ((name,base),(tip_name,tip)):
                kit.blender_mesh(scene,source,kit.build_mesh(source,layouts),location)
                x,y,_=location
                ground.face([(x+dx,y+dy,-.05) for dx,dy in ((42,0),(21,36),(-21,36),(-42,0),(-21,-36),(21,-36))],
                            (.54,.55,.52))
        target=Vector((210,-105,4));camera_position=target+Vector((250,-460,470));scale=710
    kit.blender_mesh(scene,'Terrain supports',ground,(0,0,0))
    camera_data=bpy.data.cameras.new(kind+' camera');camera_data.type='ORTHO';camera_data.ortho_scale=scale
    camera=bpy.data.objects.new(kind+' camera',camera_data);scene.collection.objects.link(camera)
    camera.location=camera_position;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera=camera
    light_data=bpy.data.lights.new(kind+' sun','SUN');light_data.energy=3;light_data.angle=.25
    light=bpy.data.objects.new(kind+' sun',light_data);scene.collection.objects.link(light)
    light.rotation_euler=(.45,-.35,-.4)
    bpy.data.libraries.write(str(kit.REVIEW/(kind+'-review.blend')),{scene},fake_user=True)
    return {'scene':scene.name,'objects':len(scene.objects)}
