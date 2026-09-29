"""Author the modular fortress in Blender, using the existing rigid geometry exporter.

Run inside Blender: exec(compile(Path(__file__).read_text(), __file__, 'exec')).
No existing scene or object is replaced. The saved library contains only this asset's scenes.
"""
from pathlib import Path
from collections import defaultdict
from math import atan2, hypot, sin, cos
import json
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from unit_model_geometry import Geometry, normal, cross, sub
from glb_geometry import write_glb, linear

NAME = 'fortress_light_a_52'
OUT = ROOT / 'data/models/buildings/fortress_light'
SOURCE = ROOT / 'tools/buildings'
LEVEL = 18
# Trace the structural envelope, excluding the source tile's shadow and small roof merlons.
PIXELS = [(0, 35), (20, 1), (26, 0), (84, 36), (63, 72), (43, 60), (25, 72), (20, 71)]
RING = [(x - 42, 36 - y) for x, y in reversed(PIXELS)]
MATERIALS = {
    'fortress-concrete': ((.61, .592, .552), 'concrete.png', .95),
    'fortress-trim': ((.73, .705, .66), 'concrete.png', .85),
    'fortress-roof': ((.61, .595, .57), 'roof.png', .97),
    'fortress-plinth': ((.50, .49, .46), 'concrete.png', .95),
    'fortress-steel': ((.16, .18, .17), None, .62),
    'fortress-dark': ((.085, .095, .091), None, .96),
    'fortress-glass': ((.055, .074, .075), None, .24),
    'fortress-facade': ((1, 1, 1), 'facade-lod1.png', .95),
}
TEXTURES = {
    'concrete.png': SOURCE / 'concrete-albedo.png',
    'roof.png': SOURCE / 'roof-albedo.png',
    'facade-lod1.png': SOURCE / 'facade-lod1.png',
}
FACADE_WIDTH, FACADE_HEIGHT, FACADE_PAD = 256, 128, 8
scene = bpy.data.scenes.new('Modular fortress authoring')
scene.unit_settings.system = 'METRIC'
scene['source_tile'] = 'saxarba/fortress_light/fortress_light_a_52.png'
scene['level_height'] = LEVEL
scene['format'] = 'Authored as a readable three-story building. Runtime derives each module base/center from its bounds, discards display offsets, and generates slabs/struts.'
bpy.context.window.scene = scene

def box(g, center, size, role='fortress-concrete', bevel=0):
    g.box(center, size, group='root', material=role, bevel=bevel)

def opening(ground, edge_index, bays, bay_width, index):
    door = ground and edge_index in (1, 2, 4) and index == bays//2 and bay_width > 6
    width = min(bay_width*.72, 7.2) if door else min(bay_width*.27, 2.4)
    bottom, top = (0.3, 8.8) if door else (5.2, 13.8)
    return door, width, bottom, top

def wall(g, a, b, variant, lod, edge_index):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = hypot(dx, dy)
    if length < .01:
        return
    local = Geometry()
    ground = variant == 0
    bays = max(1, round(length / 10))
    bay_width = length / bays
    if lod == 1:
        # Flat walls retain textured faces on both sides, without thickness or edge caps.
        plane = [(0,0,0),(length,0,0),(length,0,LEVEL),(0,0,LEVEL)]
        local.face(plane, 'root','fortress-facade')
        local.face(list(reversed(plane)), 'root','fortress-concrete')
        # Window, door and slab-band colours are baked into the exterior atlas. No
        # nearly coplanar accent geometry can fight with the wall's depth buffer.
        g.extend(local, offset=(*a, 0), angle=atan2(dy, dx), group=str(edge_index))
        return
    for i in range(bays):
        left, right = i*bay_width, (i+1)*bay_width
        mid = (left+right)/2
        door, width, bottom, top = opening(ground, edge_index, bays, bay_width, i)
        # Four structural pieces around a real recessed opening; inner faces are present.
        side = (bay_width-width)/2
        for panel_x in (left+side/2, right-side/2):
            if lod == 0:
                # Cast panels with real recessed joints, backed by the continuous inner wall.
                box(local, (panel_x, 1.17, 9), (side, .26, 18))
                for z0, z1 in ((0,5.78),(5.86,11.66),(11.74,18)):
                    box(local, (panel_x, .53, (z0+z1)/2), (side-.045, 1.06, z1-z0), bevel=.065)
            else:
                box(local, (panel_x, .65, 9), (side, 1.3, 18))
        box(local, (mid, .65, bottom/2), (width, 1.3, bottom))
        box(local, (mid, .65, (top+18)/2), (width, 1.3, 18-top))
        box(local, (mid, .91, (bottom+top)/2), (width, .14, top-bottom),
            'fortress-steel' if door else 'fortress-glass')
        if lod == 0:
            # Recessed metal frame, sill, lintel and a center mullion. No painted facade windows.
            for x in (mid-width/2+.10, mid+width/2-.10):
                box(local, (x, .65, (bottom+top)/2), (.18, .43, top-bottom), 'fortress-steel', .12)
            for z in (bottom+.12, top-.12):
                box(local, (mid, .57, z), (width, .60, .24), 'fortress-steel', .12)
            if not door:
                box(local, (mid, .71, (bottom+top)/2), (.11, .22, top-bottom), 'fortress-steel')
                box(local, (mid, .55, bottom-.18), (width+.8, 1.1, .35), 'fortress-trim', .09)
            else:
                # Canopy and ribbed industrial door only on floor0.
                box(local, (mid, -.85, top+.6), (width+1.7, 2.4, .55), 'fortress-trim', .1)
                for rib in range(1, 25):
                    z = .3 + rib*.34
                    box(local, (mid, .78, z), (width-.3, .14, .045), 'fortress-dark')
                box(local, (mid+width/2+.55, -.11, 4.2), (.48, .30, .9), 'fortress-steel', .1)
                box(local, (mid+width/2+1.2, -.09, 2.7), (.74, .28, 1.25), 'fortress-steel', .1)
                box(local, (mid-.7, .73, 4.3), (.16, .28, 1.1), 'fortress-trim')
                box(local, (mid, -.2, .2), (width+1, 1.7, .4), 'fortress-trim')
                for z in (2.25,2.55,2.85,3.15):
                    box(local, (mid+width/2+1.2,-.25,z), (.60,.08,.09), 'fortress-dark')
            # Expansion joints and formwork ties give the concrete real architectural scale.
            for z in (5.8, 11.7):
                for x0, x1 in ((left+.1, mid-width/2-.12), (mid+width/2+.12, right-.1)):
                    if x1 > x0:
                        box(local, ((x0+x1)/2, -.02, z), (x1-x0, .055, .065), 'fortress-dark')
            if variant == 2 and i % 3 == 1:
                box(local, (mid+width/2+side*.48, -.11, 8.5), (min(1.4,side*.6), .24, 1.9), 'fortress-steel')
                for z in (7.9, 8.3, 8.7, 9.1):
                    box(local, (mid+width/2+side*.48, -.26, z), (min(1.2,side*.55), .12, .09), 'fortress-dark')
        # Pilasters and slab edge are below the story boundary; there is no stretch/overlap between levels.
        box(local, (left+.17, .65, 9), (.34, 1.3, 18), 'fortress-trim')
    if lod == 0:
        box(local, (length/2, .75, 17.68), (length, 1.5, .64), 'fortress-trim')
        box(local, (length/2, .73, .25), (length, 1.46, .5), 'fortress-plinth' if ground else 'fortress-concrete')
    if ground and lod == 0 and length > 12:
        # Raised perimeter base course, service grilles and conduit at human scale.
        for i in range(bays):
            x = (i+.18)*bay_width
            box(local,(x,.12,1.05),(min(1.8,bay_width*.24),.25,1.5),'fortress-steel',.1)
            for z in (.5,.78,1.06,1.34,1.62):
                box(local,(x,-.02,z),(min(1.6,bay_width*.20),.065,.07),'fortress-dark')
            if i % 3 == 0:
                box(local,(x+1.35,.03,2.5),(.11,.13,5),'fortress-trim')
    g.extend(local, offset=(*a, 0), angle=atan2(dy, dx), group='root')

def floor(variant, lod):
    g = Geometry()
    for index, (a, b) in enumerate(zip(RING, RING[1:]+RING[:1])):
        wall(g, a, b, variant, lod, index)
    return g

def roof(lod):
    g = Geometry()
    polygon = [Vector((x, y, 0)) for x, y in RING]
    # Actual manifold underside is also the runtime volume detector's source, never a bounding rectangle.
    for indices in tessellate_polygon([polygon]):
        tri = [polygon[i] if isinstance(i, int) else i for i in indices]
        g.face(list(reversed(tri)), 'root', 'fortress-concrete')
        g.face([(v.x, v.y, .65) for v in tri], 'root', 'fortress-roof')
    for a, b in zip(RING, RING[1:]+RING[:1]):
        g.face([(*a,0), (*b,0), (*b,.65), (*a,.65)], 'root', 'fortress-trim')
    inset = []
    for i, p in enumerate(RING):
        a = Vector(RING[i-1]); b = Vector(p); c = Vector(RING[(i+1)%len(RING)])
        u = (b-a).normalized(); v = (c-b).normalized()
        n1 = Vector((-u.y,u.x)); n2 = Vector((-v.y,v.x))
        bisector = n1+n2
        inward = bisector * (1.2/max(.1, bisector.dot(n1)))
        inset.append(tuple(b+inward))
    for i, (a,b) in enumerate(zip(RING,RING[1:]+RING[:1])):
        ia,ib = inset[i],inset[(i+1)%len(RING)]
        g.face([(*a,.65),(*b,.65),(*b,1.75),(*a,1.75)],'root','fortress-trim')
        g.face([(*ia,1.75),(*ib,1.75),(*ib,.65),(*ia,.65)],'root','fortress-trim')
        g.face([(*a,1.75),(*b,1.75),(*ib,1.75),(*ia,1.75)],'root','fortress-trim')
    # The distinct diagonal row of concrete crenellations follows the original tile.
    a, b = (42, 0), (-16, 36)
    length = hypot(b[0]-a[0], b[1]-a[1])
    crenels = Geometry()
    for i in range(5):
        mid = (i+.5)*length/5
        # One continuous hollow coping; joined corners have no artificial box seams.
        outside = [(mid-4.675,0),(mid+4.675,0),(mid+4.675,4.2),(mid-4.675,4.2)]
        inside = [(mid-3.925,.8),(mid+3.925,.8),(mid+3.925,3.4),(mid-3.925,3.4)]
        for j in range(4):
            a0,a1=outside[j],outside[(j+1)%4]
            b0,b1=inside[j],inside[(j+1)%4]
            crenels.face([(*a0,.65),(*a1,.65),(*a1,4.15),(*a0,4.15)],'root','fortress-trim')
            if lod == 0:
                crenels.face([(*b0,4.15),(*b1,4.15),(*b1,.65),(*b0,.65)],'root','fortress-trim')
            crenels.face([(*a0,4.15),(*a1,4.15),(*b1,4.15),(*b0,4.15)],'root','fortress-trim')
        if lod == 0:
            box(crenels, (mid, 2.1, .74), (7.85, 2.6, .16), 'fortress-dark')
        else:
            crenels.face([(*point,4.15) for point in inside],'root','fortress-dark')
    g.extend(crenels, offset=(*a, 0), angle=atan2(b[1]-a[1],b[0]-a[0]), group='root')
    if lod == 0:
        for x, y in ((-20, -9), (17, -12), (6, 15)):
            box(g, (x, y, 1.04), (3.5, 3.1, .78), 'fortress-steel', .1)
            for offset in (-1, -.5, 0, .5, 1):
                box(g, (x+offset, y, 1.46), (.18, 2.7, .07), 'fortress-dark')
        # Narrow irregular bitumen repair seams, modeled so they survive the real GLB export.
        paths = [[(-31,-5),(-22,-4),(-15,-7),(-6,-4),(3,-6),(12,-1),(21,0),(33,3)],
                 [(-6,-4),(-8,4),(-3,11),(-5,19),(1,24),(0,29)],
                 [(3,-6),(6,-13),(4,-19),(9,-27)]]
        for points in paths:
            for a,b in zip(points,points[1:]):
                d=Vector((b[0]-a[0],b[1]-a[1])).normalized()
                n=Vector((-d.y,d.x))*.045
                g.face([(a[0]-n.x,a[1]-n.y,.662),(b[0]-n.x,b[1]-n.y,.662),
                        (b[0]+n.x,b[1]+n.y,.662),(a[0]+n.x,a[1]+n.y,.662)],'root','fortress-dark')
    return g

def bake_facade():
    """Two padded atlas rows: ground-floor doors, then the shared upper-floor windows."""
    image = bpy.data.images.load(str(TEXTURES['concrete.png']), check_existing=True)
    source = np.empty(image.size[0]*image.size[1]*4, dtype=np.float32)
    image.pixels.foreach_get(source)
    source = source.reshape(image.size[1], image.size[0], 4)[..., :3]
    source = np.where(source <= .04045, source/12.92, ((source+.055)/1.055)**2.4)
    atlas = np.ones((2*FACADE_HEIGHT, len(RING)*FACADE_WIDTH, 4), dtype=np.float32)
    u = np.clip((np.arange(FACADE_WIDTH)+.5-FACADE_PAD)/(FACADE_WIDTH-2*FACADE_PAD), 0, 1)[None, :]
    z = np.clip((np.arange(FACADE_HEIGHT)+.5-FACADE_PAD)/(FACADE_HEIGHT-2*FACADE_PAD), 0, 1)[:, None]*LEVEL
    for row in range(2):
        for edge_index, (a,b) in enumerate(zip(RING, RING[1:]+RING[:1])):
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = hypot(dx, dy)
            x = u*length
            px, py = a[0]+u*dx, a[1]+u*dy
            texture_u = (px*(-dx/length)-py*(dy/length))/18
            tx = (np.mod(texture_u, 1)*image.size[0]).astype(int)
            ty = (np.mod(z/18, 1)*image.size[1]).astype(int)
            concrete = source[ty, tx]
            colors = concrete*np.array([linear(c) for c in MATERIALS['fortress-concrete'][0]])
            bays = max(1, round(length/10))
            bay_width = length/bays
            for i in range(bays):
                door, width, bottom, top = opening(row == 0, edge_index, bays, bay_width, i)
                mid = (i+.5)*bay_width
                mask = (abs(x-mid) <= width/2) & (z >= bottom) & (z <= top)
                role = 'fortress-steel' if door else 'fortress-glass'
                colors[mask] = [linear(c) for c in MATERIALS[role][0]]
            band = (x >= .1) & (x <= length-.1) & (z >= 17.4) & (z <= 17.9)
            trim = concrete*np.array([linear(c) for c in MATERIALS['fortress-plinth'][0]])
            colors[band] = trim[band]
            atlas[row*FACADE_HEIGHT:(row+1)*FACADE_HEIGHT,
                  edge_index*FACADE_WIDTH:(edge_index+1)*FACADE_WIDTH, :3] = np.where(
                      colors <= .0031308, colors*12.92, 1.055*colors**(1/2.4)-.055)
    baked = bpy.data.images.new('Fortress distant facade', width=atlas.shape[1], height=atlas.shape[0])
    baked.pixels.foreach_set(atlas.ravel())
    baked.filepath_raw = str(TEXTURES['facade-lod1.png'])
    baked.file_format = 'PNG'
    baked.save()

def facade_uv(p, edge_index, ground):
    a, b = RING[edge_index], RING[(edge_index+1) % len(RING)]
    dx, dy = b[0]-a[0], b[1]-a[1]
    u = ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)
    return ((edge_index*FACADE_WIDTH+FACADE_PAD+u*(FACADE_WIDTH-2*FACADE_PAD))/(len(RING)*FACADE_WIDTH),
            ((0 if ground else 1)*FACADE_HEIGHT+FACADE_PAD+p[2]/LEVEL*(FACADE_HEIGHT-2*FACADE_PAD))/(2*FACADE_HEIGHT))

bake_facade()
materials = {}
for role, (color, texture, roughness) in MATERIALS.items():
    mat = bpy.data.materials.new(role)
    mat.use_nodes = True
    mat.use_backface_culling = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*[linear(c) for c in color], 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = .55 if role == 'fortress-steel' else 0
    vertex_color = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    vertex_color.layer_name = 'Weathering'
    tint = mat.node_tree.nodes.new('ShaderNodeMixRGB')
    tint.blend_type = 'MULTIPLY'
    tint.inputs[0].default_value = 1
    tint.inputs[1].default_value = (*[linear(c) for c in color],1)
    mat.node_tree.links.new(vertex_color.outputs['Color'], tint.inputs[2])
    mat.node_tree.links.new(tint.outputs[0], shader.inputs['Base Color'])
    if texture:
        image = bpy.data.images.load(str(TEXTURES[texture]), check_existing=True)
        image.pack()
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.extension = 'REPEAT'
        multiply = mat.node_tree.nodes.new('ShaderNodeMixRGB')
        multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = 1
        mat.node_tree.links.new(tex.outputs['Color'], multiply.inputs[1])
        mat.node_tree.links.new(tint.outputs[0], multiply.inputs[2])
        mat.node_tree.links.new(multiply.outputs[0], shader.inputs['Base Color'])
        # Blender review receives fine relief; the shipped runtime currently uses albedo + geometry.
        bump = mat.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .22
        bump.inputs['Distance'].default_value = .13
        mat.node_tree.links.new(tex.outputs['Color'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    materials[role] = mat

def appearance(p, n, role):
    # Baked vertex dirt beneath sills and near slab joints; deterministic and lighting-independent.
    weather = .88 + .065*sin(p[0]*.47+p[1]*.21) + .025*sin(p[0]*1.9+p[1]*.8+p[2]*.3)
    if role == 'fortress-concrete':
        weather *= .74 + .26*min(1, p[2]/4.2)
    if role == 'fortress-glass':
        weather *= .64 + .36*min(1,p[2]/14)
    repeat = 18 if role != 'fortress-roof' else 84
    if abs(n[2]) > .65:
        uv = (p[0]/repeat, p[1]/repeat)
    else:
        uv = ((p[0]*n[1]-p[1]*n[0])/repeat, p[2]/repeat)
    return max(.45, min(1, weather)), uv

def export_level(lod):
    vertices, unique, parts, nodes = [], {}, [], []
    group = bpy.data.objects.new(NAME+'-lod'+str(lod), None)
    scene.collection.objects.link(group)
    counts = {}
    for suffix, g in [('roof0',roof(lod)), ('floor0',floor(0,lod)), ('floor1',floor(1,lod)), ('floor2',floor(2,lod))]:
        node_id = NAME+'-lod'+str(lod)+'-'+suffix
        mesh_points, mesh_faces, mesh_uv, mesh_color, mesh_roles = [], [], [], [], []
        by_material = defaultdict(list)
        for tri, group_id, role in g.faces:
            n = normal(cross(sub(tri[1],tri[0]), sub(tri[2],tri[0])))
            start = len(mesh_points)
            for p in tri:
                shade, uv = appearance(p,n,role)
                if role == 'fortress-facade':
                    shade, _ = appearance(p,n,'fortress-concrete')
                    uv = facade_uv(p, int(group_id), suffix == 'floor0')
                # Concrete, coping and base-course tints share one albedo/material in the GLB.
                # Baking their tint into existing vertex colours avoids duplicate embedded images and draw parts.
                concrete = role in ('fortress-concrete','fortress-trim','fortress-plinth')
                rgb = tuple(shade*c for c in MATERIALS[role][0]) if concrete else (shade,shade,shade)
                value = tuple(round(v,6) for v in (*p,*n,*rgb,1,uv[0],-uv[1]))
                if value not in unique:
                    unique[value] = len(vertices)//12
                    vertices.extend(value)
                by_material['fortress-concrete' if concrete else role].append(unique[value])
                mesh_points.append(tuple(p))
                mesh_uv.append(uv)
                mesh_color.append((linear(shade),linear(shade),linear(shade),1))
            mesh_faces.append((start,start+1,start+2))
            mesh_roles.append(role)
        node_parts = []
        for role, indices in by_material.items():
            part_id = node_id+'-'+role
            parts.append({'id':part_id,'type':'TRIANGLES','indices':indices})
            node_parts.append({'meshpartid':part_id,'materialid':role})
        display_z = {'floor0':0, 'floor1':18, 'floor2':36, 'roof0':54}[suffix]
        nodes.append({'id':node_id,'translation':[lod*110,0,display_z],'parts':node_parts})
        mesh = bpy.data.meshes.new(node_id)
        mesh.from_pydata(mesh_points, [], mesh_faces)
        assert not mesh.validate(), node_id
        mesh.update()
        for mat in materials.values():
            mesh.materials.append(mat)
        uv_layer = mesh.uv_layers.new(name='UVMap')
        colors = mesh.color_attributes.new(name='Weathering',type='FLOAT_COLOR',domain='CORNER')
        for polygon, role in zip(mesh.polygons,mesh_roles):
            polygon.material_index = list(materials).index(role)
            for loop_index in polygon.loop_indices:
                index = mesh.loops[loop_index].vertex_index
                uv_layer.data[loop_index].uv = mesh_uv[index]
                colors.data[loop_index].color = mesh_color[index]
        obj = bpy.data.objects.new(node_id,mesh)
        scene.collection.objects.link(obj)
        obj.parent = group
        obj.location = (lod*110,0,display_z)
        obj['module'] = suffix
        obj['authored_height'] = LEVEL if suffix.startswith('floor') else 4.15
        obj.hide_render = lod != 0
        obj.hide_set(lod != 0)
        counts[suffix] = len(g.faces)
    group.hide_render = lod != 0
    model_materials = []
    for role, (color, texture, _) in MATERIALS.items():
        if role in ('fortress-trim','fortress-plinth'):
            continue
        mat = {'id':role,'diffuse':[1,1,1] if role == 'fortress-concrete' else list(color)}
        if texture:
            mat['textures'] = [{'id':role,'filename':texture,'type':'DIFFUSE'}]
        model_materials.append(mat)
    assert len(vertices)//12 <= 65535
    return {'id':NAME, 'meshes':[{'attributes':['POSITION','NORMAL','COLOR','TEXCOORD0'],
        'vertices':vertices,'parts':parts}], 'materials':model_materials, 'nodes':nodes}, counts

levels, stats = {}, {}
for lod in range(2):
    levels[lod], stats[lod] = export_level(lod)
OUT.mkdir(parents=True, exist_ok=True)
write_glb(OUT/(NAME+'.glb'), levels=levels,
          embedded_images={name:path.read_bytes() for name,path in TEXTURES.items()})

# Assemble a real preview from the authored modules. This scene is not exported into the GLB.
review = bpy.data.scenes.new('Modular fortress three floors')
review.render.engine = 'CYCLES'
review.cycles.samples = 96
review.cycles.use_denoising = True
review.render.resolution_x = 1536
review.render.resolution_y = 1200
review.render.resolution_percentage = 100
review.world = bpy.data.worlds.new('Fortress overcast studio')
review.world.use_nodes = True
review.world.node_tree.nodes['Background'].inputs[0].default_value = (.3,.33,.38,1)
review.world.node_tree.nodes['Background'].inputs[1].default_value = .45
review.view_settings.view_transform = 'AgX'
review.view_settings.look = 'AgX - Medium High Contrast'
for level, suffix in enumerate(('floor0','floor1','floor2','roof0')):
    source = next(o for o in scene.objects if o.name == NAME+'-lod0-'+suffix)
    obj = bpy.data.objects.new(suffix+'-preview-'+str(level),source.data)
    review.collection.objects.link(obj)
    obj.location.z = level*LEVEL
ground_mesh = bpy.data.meshes.new('Fortress review ground')
ground_mesh.from_pydata([(-1000,-1000,-.06),(1000,-1000,-.06),(1000,1000,-.06),(-1000,1000,-.06)],[],[(0,1,2,3)])
ground = bpy.data.objects.new('Fortress review ground',ground_mesh)
review.collection.objects.link(ground)
groundmat = bpy.data.materials.new('Fortress studio gray')
groundmat.diffuse_color = (.13,.14,.15,1)
ground.data.materials.append(groundmat)
camera_data = bpy.data.cameras.new('Fortress review camera')
camera = bpy.data.objects.new('Fortress review camera',camera_data)
review.collection.objects.link(camera)
camera.location = (40,-245,155)
target = Vector((0,0,28))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 125
review.camera = camera
for name, loc, energy, size in [('Key',(-80,-100,210),1200000,120),('Fill',(130,50,130),400000,100)]:
    light = bpy.data.lights.new('Fortress '+name,'AREA')
    light.energy=energy
    light.shape='DISK'
    light.size=size
    obj=bpy.data.objects.new('Fortress '+name,light)
    obj.location=loc
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
    review.collection.objects.link(obj)
bpy.context.window.scene = review
review.render.image_settings.file_format = 'PNG'
review.render.filepath = str(SOURCE/'fortress-three-floors.png')
# Save only this asset and its preview, preserving every previously open scene.
bpy.data.libraries.write(str(SOURCE/'modular-fortress.blend'), {scene,review}, path_remap='RELATIVE', fake_user=True)
(SOURCE/'asset-report.json').write_text(json.dumps({'asset':str(OUT/(NAME+'.glb')), 'triangles':stats,
    'footprint':RING,'floorHeight':LEVEL,'roofCapHeight':4.15,
    'reference':'fortress-reference.png','runtimeMaterials':'Embedded albedo and vertex weathering; no runtime PBR normal/roughness mapping.'},indent=2))
result = {'file':str(OUT/(NAME+'.glb')), 'triangles':stats, 'preview_scene':review.name, 'authoring_scene':scene.name}


if '--render' in sys.argv:
    bpy.ops.render.render(write_still=True, scene=review.name)
