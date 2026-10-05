"""Build four open-ground industrial kits in Blender and export the shared rigid GLB format.

Run through Blender MCP with __file__ set to this file. Existing scenes are preserved.
Each kit has two bases, four repeatable 18-unit segments and two equipment caps, at two LODs.
There are no rooms, stairs or full-width decks. Module names describe assembly, not playable floors.
"""
from pathlib import Path
from math import sin, cos, pi, sqrt
import json
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from unit_model_geometry import Geometry, normal, cross, sub
from glb_geometry import write_glb, linear

SOURCE = ROOT / 'tools/buildings/heavy-industrial'
OUT = ROOT / 'data/models/buildings/misc'
LEVEL = 18
PORTS = [(0, 36), (31.5, 18), (31.5, -18), (0, -36), (-31.5, -18), (-31.5, 18)]
RISERS = [(x, y) for x in (-32, 32) for y in (-12, 12)] + [(x, y) for x in (-10, 10) for y in (-30, 30)]
PALETTE = {
    'ivory': (.69, .68, .60), 'teal': (.24, .39, .40), 'steel': (.38, .42, .43),
    'dark': (.14, .18, .20), 'rust': (.59, .29, .13), 'yellow': (.85, .62, .16),
    'black': (.10, .12, .13), 'concrete': (.43, .44, .41), 'silver': (.57, .61, .61),
}
# The clear centre is deliberate: equipment occupies the sides, never a solid building footprint.
VESSELS = {
    'a': [(-18, 0, 8), (18, 0, 8)],
    'b': [(-18, 0, 12), (20, -17, 4.7), (20, 17, 4.7)],
    'c': [(-19, 0, 6.4), (19, 0, 6.4)],
    'd': [(-18, 0, 5.5), (18, 0, 5.5)],
}
ROLES = ['base0', 'base1', 'floor0', 'floor1', 'floor2', 'floor3', 'roof0', 'roof1']
SOURCE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

# A small packed grayscale steel texture supplies weathering; all tint is vertex colour, one material per kit.
rng = np.random.default_rng(1607)
w = 512
yy, xx = np.mgrid[0:w, 0:w]
grain = rng.normal(0, .024, (w, w))
streaks = np.repeat(rng.uniform(-.05, .035, (1, w)), w, axis=0)
wear = .86 + grain + streaks + .035 * np.sin(xx * .095 + np.sin(yy * .021))
for _ in range(110):
    x, y, length = int(rng.integers(w)), int(rng.integers(w)), int(rng.integers(3, 45))
    wear[y:min(w, y + length), x:x + 1] -= rng.uniform(.06, .22)
pixels = np.ones((w, w, 4), dtype=np.float32)
corrosion = (np.sin(xx*.031+np.sin(yy*.026)*2) + np.sin(yy*.077+xx*.025)
             + rng.normal(0, .35, (w,w))) > 1.48
pixels[:, :, :3] = np.clip(wear, .45, 1)[:, :, None]
pixels[corrosion, :3] *= (.62,.39,.23)
texture = bpy.data.images.new('Industrial brushed weathered steel', width=w, height=w, alpha=False)
texture.pixels.foreach_set(pixels.ravel())
texture.filepath_raw = str(SOURCE / 'industrial-steel.png')
texture.file_format = 'PNG'
texture.save()
texture.pack()
material = bpy.data.materials.new('Industrial shared weathered metal')
material.use_nodes = True
nodes = material.node_tree.nodes
bsdf = nodes.get('Principled BSDF')
bsdf.inputs['Roughness'].default_value = .76
bsdf.inputs['Metallic'].default_value = .25
tex = nodes.new('ShaderNodeTexImage')
tex.image = texture
col = nodes.new('ShaderNodeVertexColor')
col.layer_name = 'Tint'
mul = nodes.new('ShaderNodeMixRGB')
mul.blend_type = 'MULTIPLY'
mul.inputs[0].default_value = 1
material.node_tree.links.new(tex.outputs['Color'], mul.inputs[1])
material.node_tree.links.new(col.outputs['Color'], mul.inputs[2])
material.node_tree.links.new(mul.outputs[0], bsdf.inputs['Base Color'])


def box(g, p, size, mat='dark'):
    g.box(p, size, group='root', material=mat)


def tube(g, a, b, radius=.8, mat='rust', lod=0):
    if (Vector(b)-Vector(a)).length < .001:
        return
    group = 'pipe@' + '@'.join(str(c) for p in (a,b) for c in p)
    g.beam(a, b, radius * 2, group=group, material=mat, sides=10 if lod == 0 else 6)


def cylinder(g, x, y, r, bottom, top, mat='ivory', lod=0):
    sides = 20 if lod == 0 else 10
    ring = [(x + r*cos(i*2*pi/sides), y + r*sin(i*2*pi/sides)) for i in range(sides)]
    g.prism(ring, bottom, top, group=f'cylinder@{x}@{y}', material=mat)


def flange(g, a, b, radius=1.2, lod=0):
    tube(g, a, b, radius, 'silver', lod)


def route(g, points, radius=.8, mat='rust', lod=0):
    points = [Vector(p) for i,p in enumerate(points) if i == 0 or (Vector(p)-Vector(points[i-1])).length > .001]
    if len(points) < 2:
        return
    swept = [points[0]]
    for before, corner, after in zip(points, points[1:], points[2:]):
        incoming, outgoing = corner-before, after-corner
        bend = min(radius*1.7, incoming.length*.3, outgoing.length*.3)
        a, b = corner-incoming.normalized()*bend, corner+outgoing.normalized()*bend
        swept.append(a)
        for index in range(1, (4 if lod == 0 else 2)+1):
            t = index/(4 if lod == 0 else 2)
            swept.append((1-t)**2*a + 2*(1-t)*t*corner + t*t*b)
    swept.append(points[-1])
    for a, b in zip(swept, swept[1:]):
        tube(g, a, b, radius, mat, lod)
    if lod == 0:
        for a, b in zip(points, points[1:]):
            d = np.array(b) - a
            length = np.linalg.norm(d)
            if length > 2:
                p = np.array(a) + d * .28
                q = p + d / length * .55
                flange(g, tuple(p), tuple(q), radius*1.35, lod)


def band(g, x, y, r, z, width=.5, lod=0, hazard=False):
    if not hazard:
        cylinder(g, x, y, r + .22, z, z + width, 'steel', lod)
        return
    n = 20 if lod == 0 else 10
    for i in range(n):
        a, b = i*2*pi/n, (i+1)*2*pi/n
        g.face([(x+(r+.25)*cos(a), y+(r+.25)*sin(a), z),
                (x+(r+.25)*cos(b), y+(r+.25)*sin(b), z),
                (x+(r+.25)*cos(b), y+(r+.25)*sin(b), z+width),
                (x+(r+.25)*cos(a), y+(r+.25)*sin(a), z+width)],
               group='root', material='yellow' if i % 2 else 'black')


def manifold(g, base, cap, family, lod):
    # Continuous service spines, attached to vessels, replace unsupported pipes on every upper segment.
    for x,y in RISERS:
        tube(g, (x,y,0), (x,y,3 if cap else LEVEL), .85, 'steel', lod)
        if base:
            box(g, (x,y,.5), (2.5,2.5,1), 'concrete')
        if cap:
            cylinder(g,x,y,1.1,3,3.4,'dark',lod)
        vx,vy,r = min(VESSELS[family], key=lambda vessel:(vessel[0]-x)**2+(vessel[1]-y)**2)
        z = 1.4 if cap else 13.8
        end = (vx,vy,z)
        route(g, [(x,y,z), ((x+end[0])*.5,(y+end[1])*.5,z), end], .65,'rust',lod)
        if not cap:
            # Visible clamps tie the riser to its feed line and vessel.
            flange(g,(x,y,13.2),(x,y,13.65),1.05,lod)
    if not base:
        return
    # Six standard ground-level docking flanges connect adjacent hexes. All inward ends join a service riser.
    z = 4
    for x, y in PORTS:
        length = sqrt(x*x+y*y)
        dx, dy = x/length, y/length
        start = (x-dx*8, y-dy*8, z)
        end = (x, y, z)
        tube(g, start, end, 1.05, 'rust', lod)
        flange(g, (x-dx*.85, y-dy*.85, z), (x-dx*.3, y-dy*.3, z), 1.45, lod)
        rx,ry = min(RISERS,key=lambda p:(p[0]-start[0])**2+(p[1]-start[1])**2)
        route(g, [start,(rx,start[1],z),(rx,ry,z)],1.05,'rust',lod)
        bx,by = x-dx*4,y-dy*4
        box(g,(bx,by,.5),(2.6,2.6,1),'concrete')
        box(g,(bx,by,1.9),(.8,.8,2),'dark')


def equipment(g, family, variant, base, lod):
    if family == 'a':
        generator(g,variant,base,lod)
        return
    if family == 'c':
        chemical(g,variant,base,lod)
        return
    for index, (x, y, r) in enumerate(VESSELS[family]):
        mat = 'teal' if (index + ord(family)) % 3 == 0 else 'ivory'
        cylinder(g, x, y, r, 1 if base else 0, LEVEL, mat, lod)
        band(g, x, y, r, 17.4, .4, lod)
        if base:
            cylinder(g, x, y, r + .6, 0, 1, 'concrete', lod)
            if lod == 0:
                for ang in (0, pi/2, pi, 3*pi/2):
                    bx, by = x + (r+.6)*cos(ang), y + (r+.6)*sin(ang)
                    box(g, (bx, by, 1.8), (.6, .6, 2.2), 'dark')
        detail = (variant + index) % 4
        # Exterior machinery changes; cylinder radii and the vertical service risers never move.
        outward = -1 if x < 0 else 1
        ox = x + outward*(r+.7)
        if detail == 0:
            band(g, x, y, r, 4, .9, lod, True)
            route(g, [(x, y-2.5, 3), (ox, y-2.5, 3), (ox, y-2.5, 12),
                      (ox, y+2.5, 12), (ox, y+2.5, 5), (x, y+2.5, 5)],
                  .55, 'rust', lod)
        elif detail == 1:
            for z in (5, 10, 14):
                tube(g, (x, y, z), (ox+.6*outward, y, z), 1.1, 'steel', lod)
                flange(g, (ox+.6*outward, y, z), (ox+1*outward, y, z), 1.65, lod)
        elif detail == 2:
            box(g, (ox, y, 9), (2, 4, 6), 'teal')
            if lod == 0:
                for z in (7, 8, 9, 10, 11):
                    box(g, (ox+.7*outward, y, z), (.2, 3.4, .25), 'dark')
            band(g, x, y, r, 12.5, .8, lod, True)
        else:
            for offset in (-2, 0, 2):
                route(g, [(x, y+offset, 2), (ox, y+offset, 2),
                          (ox, y+offset, 13), (x, y+offset, 13)],
                      .45, 'silver', lod)
            band(g, x, y, r, 6, .8, lod, True)
        if lod == 0:
            # Small flush identification panel; no ladders or walkable balconies.
            box(g, (x, y-r-.2, 9), (2.2, .25, 1.3), 'yellow')
        if family == 'd':
            turns = 2 if variant % 2 else 3
            steps = (24 if lod == 0 else 10)*turns
            points = [(x+(r+.7)*cos(i*turns*2*pi/steps), y+(r+.7)*sin(i*turns*2*pi/steps),
                       3+11*i/steps) for i in range(steps+1)]
            for a,b in zip([(x,y,3),*points], [*points,(x,y,14)]):
                tube(g,a,b,.28,'rust' if variant<2 else 'silver',1)
    if family == 'd':
        # Open steel bracing along the sides, never full-width storeys or enclosed walls.
        for x in (-25, 25):
            for y in (-22, 22):
                box(g, (x, y, 9), (1, 1, LEVEL), 'dark')
            for z in (1, 16.8):
                box(g, (x, 0, z), (1, 45, 1), 'steel')
            for y in (-22, 0):
                tube(g, (x, y, 2), (x, y+22, 15.8), .32, 'steel', lod)
                if lod == 0:
                    tube(g, (x, y, 15.8), (x, y+22, 2), .32, 'steel', lod)
    if base:
        # Pumps sit in the side pockets. The middle of the hex remains open to units.
        for x, y in ((-18, -27), (18, 27)):
            box(g, (x, y, .6), (7, 4, 1.2), 'concrete')
            tube(g, (x-2, y, 3), (x+2, y, 3), 1.8, 'teal' if variant == 0 else 'rust', lod)
            rx,ry = (-10,-30) if x<0 else (10,30)
            route(g, [(x+2, y, 3), (x+4, y, 3), (rx,ry,3)], .6, 'silver', lod)
            if lod == 0:
                # A real pump control wheel, mounted on a stem rather than floating beside the pipe.
                tube(g,(rx,ry,3),(rx,ry,5.5),.22,'dark',lod)
                ring = [(rx+1.35*cos(i*pi/8),ry+1.35*sin(i*pi/8),5.5) for i in range(17)]
                for a,b in zip(ring,ring[1:]):
                    tube(g,a,b,.15,'rust',lod)
                for angle in (0,pi/2):
                    tube(g,(rx-1.35*cos(angle),ry-1.35*sin(angle),5.5),
                         (rx+1.35*cos(angle),ry+1.35*sin(angle),5.5),.12,'rust',lod)


def generator(g, variant, base, lod):
    """Angular generator housings, copper rotors and deep cooling ribs; no storage cylinders."""
    for x in (-18,18):
        g.box((x,0,9),(15,34,18),group='root',material='dark',bevel=.22)
        outward = -1 if x<0 else 1
        # Armoured end casings with alternating recessed rotor/heat-exchanger details.
        for y in (-18,18):
            g.box((x,y,9),(17,3,16),group='root',material='teal',bevel=.18)
            tube(g,(x,y,9),(x,y+(-2 if y<0 else 2),9),5.4,'steel',lod)
            flange(g,(x,y+(-2 if y<0 else 2),9),(x,y+(-2.6 if y<0 else 2.6),9),3.5,lod)
            tube(g,(x,y,9),(x,y+(-3 if y<0 else 3),9),1.5,'rust',lod)
        if variant in (0,2):
            if variant == 0:
                for y in range(-13,14,3 if lod==0 else 6):
                    box(g,(x+outward*8,y,9),(2.2,1,13),'silver')
                box(g,(x+outward*9.1,0,9),(.45,27,1),'rust')
            else:
                for z in (3,6,9,12,15):
                    g.box((x+outward*8,0,z),(3,27,1.3),group='root',material='teal',bevel=.15)
                box(g,(x+outward*9.6,0,9),(.5,3,14),'rust')
        else:
            for z in (4,8,12,16):
                route(g,[(x+outward*6,-14,z),(x+outward*9,-14,z),
                         (x+outward*9,14,z),(x+outward*6,14,z)],.75,'rust',lod)
            if variant == 3:
                box(g,(x+outward*9.3,0,9),(2.5,9,11),'teal')
                for y in (-2.5,2.5):
                    tube(g,(x+outward*9,y,9),(x+outward*12,y,9),1.1,'dark',lod)
                    for dx in (10,11,12):
                        tube(g,(x+outward*dx,y,9),(x+outward*(dx+.3),y,9),1.8,'ivory',lod)
        for y in (-11,11):
            box(g,(x-outward*7.8,y,10),(.7,5,6),'teal')
            if lod==0:
                for z in (8,9.5,11):
                    box(g,(x-outward*8.2,y,z),(.25,4,.35),'black')
        if base:
            for y in (-15,15):
                box(g,(x,y,.5),(18,6,1),'concrete')
                box(g,(x+outward*9,y,2),(2,3,2),'yellow')


def chemical(g, variant, base, lod):
    """Stackable horizontal reaction drums with saddles, end valves and exposed coolant coils."""
    for x in (-19,19):
        radius = 6.4
        count = 20 if lod==0 else 10
        rings = [[(x+r*cos(i*2*pi/count),y,9-r*sin(i*2*pi/count)) for i in range(count)]
                 for y,r in [(-22,.8),(-21,3.6),(-18,radius),(18,radius),(21,3.6),(22,.8)]]
        g.loft(rings,group='root',material='teal' if x<0 else 'ivory')
        for y in (-13,13):
            box(g,(x,y,1.5),(11,4,3),'concrete' if base else 'dark')
            tube(g,(x,y-.4,9),(x,y+.4,9),6.7,'steel',lod)
        # Continuous narrow steel legs carry the next machinery segment, without a floor sheet.
        for dx in (-8,8):
            for y in (-18,18):
                box(g,(x+dx,y,9),(.8,.8,18),'dark')
            box(g,(x+dx,0,17.4),(.8,37,.8),'steel')
        for y in (-22,22):
            route(g,[(x,y,9),(x,y+(-3 if y<0 else 3),9),
                     (10 if x>0 else -10,30 if y>0 else -30,9)],.85,'rust',lod)
        if variant in (1,3):
            for y in (-8,-4,0,4,8):
                points = [(x+6.7*cos(i*pi/8),y,9+6.7*sin(i*pi/8)) for i in range(17)]
                for a,b in zip(points,points[1:]):
                    tube(g,a,b,.25,'rust' if variant==1 else 'silver',lod)
        else:
            for y in ((0,) if variant==0 else (-8,8)):
                box(g,(x,y,15.4),(4,8,.7),'dark')
                cylinder(g,x,y,2.8,15.5,16.3,'silver',lod)
                if lod==0:
                    for a in range(8):
                        cylinder(g,x+2.2*cos(a*pi/4),y+2.2*sin(a*pi/4),.2,16.3,16.6,'rust',lod)
            if variant==2:
                route(g,[(x,-20,9),(x,-20,16.5),(x,20,16.5),(x,20,9)],.55,'rust',lod)


def machine_caps(g, family, variant, lod):
    for x,_,_ in VESSELS[family]:
        if family=='a':
            g.box((x,0,1.2),(15,34,2.4),group='root',material='teal',bevel=.2)
            for y in (-10,10):
                cylinder(g,x,y,5.3,2.4,3,'dark',lod)
                band(g,x,y,5.3,2.9,.4,lod)
                for blade in range(6):
                    angle = blade*pi/3
                    u,v = Vector((cos(angle),sin(angle),0)),Vector((-sin(angle),cos(angle),0))
                    center = Vector((x,y,3.15))
                    points = [center+u*r+v*s for r,s in ((1,-.5),(4.7,-.4),(4.1,1.1),(1,.4))]
                    g.face(points,group='root',material='silver')
                cylinder(g,x,y,1,3.1,3.6,'rust',lod)
            if variant:
                box(g,(x,0,4),(5,7,5),'dark')
                for z in (3,4,5,6):
                    box(g,(x,0,z),(6,8,.35),'steel')
        else:
            # Roof modules cap the pipe/header system, not a room or walkable roof.
            tube(g,(x,-21,1.4),(x,21,1.4),1.35,'steel',lod)
            for y in (-16,16):
                box(g,(x,y,.4),(16,.8,.8),'dark')
                route(g,[(x,y,0),(x,y,4.5),(x+(-3 if x<0 else 3),y,4.5)],.9,'rust',lod)
                if variant:
                    cylinder(g,x,y,2.1,3,5.3,'dark',lod)


def caps(g, family, variant, lod):
    if family in ('a','c'):
        machine_caps(g,family,variant,lod)
        return
    for i, (x, y, r) in enumerate(VESSELS[family]):
        mat = 'teal' if (i + ord(family)) % 3 == 0 else 'ivory'
        cylinder(g, x, y, r, 0, .8, 'steel', lod)
        sides = 20 if lod == 0 else 10
        levels = [(r, .8), (r*.92, 2), (r*.65, 3.7), (r*.3, 4.8)] if variant == 0 else [
            (r, .8), (r*.96, 1.7), (r*.3, 2.8)]
        rings = [[(x+radius*cos(j*2*pi/sides), y+radius*sin(j*2*pi/sides), z)
                  for j in range(sides)] for radius, z in levels]
        g.loft(rings, group='root', material=mat)
        top = levels[-1][1]
        cylinder(g, x, y, 1.5, top, top+1.1, 'dark', lod)
        cylinder(g, x, y, 1.9, top+1.1, top+1.5, 'steel', lod)
        if variant == 1:
            route(g, [(x+r*.55, y, 1.3), (x+r*.55, y, 5.4), (x+r*.25, y, 5.4)],
                  .65, 'rust', lod)
        if family=='d':
            cylinder(g,x,y,1.7,top+1.5,top+5,'rust',lod)
            cylinder(g,x,y,2.6,top+4.5,top+5.2,'dark',lod)
        if lod == 0:
            for a in (0, pi/2, pi, 3*pi/2):
                tube(g, (x+r*.93*cos(a), y+r*.93*sin(a), 1.7),
                     (x+r*.29*cos(a), y+r*.29*sin(a), top+.05), .12, 'steel', lod)


def module(family, role, lod):
    g = Geometry()
    cap, base = role.startswith('roof'), role.startswith('base')
    variant = int(role[-1])
    manifold(g, base, cap, family, lod)
    if cap:
        caps(g, family, variant, lod)
    else:
        equipment(g, family, variant, base, lod)
    positions = np.array([p for tri, _, _ in g.faces for p in tri])
    lo, hi = positions.min(axis=0), positions.max(axis=0)
    assert abs(lo[2]) < 1e-5 and (cap or abs(hi[2] - LEVEL) < 1e-5), (family, role, lo, hi)
    # Symmetric manifold ends define the normalization centre, regardless of equipment variants.
    assert np.max(np.abs((hi + lo)[:2])) < 1e-4, (family, role, 'off-centre', lo, hi)
    return g


author = bpy.data.scenes.new('Heavy industrial / modular library')
author.unit_settings.system = 'METRIC'
author['contract'] = 'Height-only cover; ground access; no occupiable floors. 18 units per base/floor.'
author['ports'] = 'Six base edge midpoints, radius 1.05, height 4; same ground elevation and zero board padding.'
mesh_library = {}
report = {}


def export_family(family):
    name = 'heavy_industrial_' + family
    exported, stats = {}, {}
    for lod in (0, 1):
        vertices, unique, parts, objects = [], {}, [], []
        group = bpy.data.objects.new(name + '-lod' + str(lod), None)
        author.collection.objects.link(group)
        counts = {}
        for role_index, role in enumerate(ROLES):
            g = module(family, role, lod)
            node_name = f'{name}-lod{lod}-{role}'
            coords, faces, colors, uvs, indices, normals = [], [], [], [], [], []
            for tri, surface, paint in g.faces:
                n = normal(cross(sub(tri[1], tri[0]), sub(tri[2], tri[0])))
                start = len(coords)
                for p in tri:
                    shading = n
                    if surface.startswith('cylinder@') and abs(n[2]) < .01:
                        _,cx,cy = surface.split('@')
                        shading = normal((p[0]-float(cx),p[1]-float(cy),0))
                    elif surface.startswith('pipe@'):
                        values = [float(v) for v in surface.split('@')[1:]]
                        a,b = Vector(values[:3]),Vector(values[3:])
                        axis = (b-a).normalized()
                        if abs(Vector(n).dot(axis)) < .5:
                            offset = Vector(p)-a
                            shading = tuple((offset-axis*offset.dot(axis)).normalized())
                    if abs(n[2]) > .65:
                        uv = (p[0]/16, p[1]/16)
                    else:
                        uv = ((p[0]*n[1]-p[1]*n[0])/16, p[2]/18)
                    shade = .88 + .09*sin(p[0]*.17+p[1]*.23+p[2]*.07)
                    rgb = tuple(c*shade for c in PALETTE[paint])
                    vertex = tuple(round(float(v), 6) for v in (*p, *shading, *rgb, 1, uv[0], -uv[1]))
                    if vertex not in unique:
                        unique[vertex] = len(vertices)//12
                        vertices.extend(vertex)
                    indices.append(unique[vertex])
                    coords.append(p)
                    normals.append(shading)
                    colors.append((*[linear(c) for c in rgb], 1))
                    uvs.append(uv)
                faces.append((start, start+1, start+2))
            mesh = bpy.data.meshes.new(node_name)
            clearance = BVHTree.FromPolygons(coords, faces, all_triangles=True)
            for x in (-5,0,5):
                for y in (-20,0,20):
                    assert clearance.ray_cast(Vector((x,y,30)),Vector((0,0,-1)))[0] is None, (node_name,x,y)
            mesh.from_pydata(coords, [], faces)
            assert not mesh.validate(), node_name
            mesh.update()
            mesh.normals_split_custom_set_from_vertices(normals)
            mesh.materials.append(material)
            color = mesh.color_attributes.new(name='Tint', type='FLOAT_COLOR', domain='CORNER')
            texcoord = mesh.uv_layers.new(name='UVMap')
            for poly in mesh.polygons:
                for loop in poly.loop_indices:
                    vertex = mesh.loops[loop].vertex_index
                    color.data[loop].color = colors[vertex]
                    texcoord.data[loop].uv = uvs[vertex]
            obj = bpy.data.objects.new(node_name, mesh)
            author.collection.objects.link(obj)
            obj.parent = group
            # A library rack: each variant is independently inspectable, not overlapping its siblings.
            obj.location = ((ord(family)-97)*400 + lod*180, role_index*90, 0)
            obj['module'] = role
            obj['gameplay'] = 'Industrial cover, not an occupiable building'
            mesh_library[(family, lod, role)] = mesh
            parts.append({'id':node_name, 'type':'TRIANGLES', 'indices':indices})
            objects.append({'id':node_name, 'translation':list(obj.location),
                            'parts':[{'meshpartid':node_name, 'materialid':'industrial-surface'}]})
            counts[role] = len(g.faces)
        assert len(vertices)//12 <= 65535, (name, lod, len(vertices)//12)
        exported[lod] = {'id':name, 'meshes':[{'attributes':['POSITION','NORMAL','COLOR','TEXCOORD0'],
            'vertices':vertices,'parts':parts}], 'materials':[{'id':'industrial-surface', 'diffuse':[1,1,1],
            'textures':[{'id':'industrial-steel','filename':'industrial-steel.png','type':'DIFFUSE'}]}], 'nodes':objects}
        stats[lod] = {'triangles':counts, 'vertices':len(vertices)//12}
    write_glb(OUT / (name + '.glb'), levels=exported,
              embedded_images={'industrial-steel.png':(SOURCE / 'industrial-steel.png').read_bytes()})
    report[name] = stats


for family in VESSELS:
    export_family(family)


def assembly(scene, family, origin, levels, variant=0):
    roles = ['base'+str(variant % 2)] + ['floor'+str((i+variant) % 4) for i in range(levels-1)] + ['roof'+str(variant % 2)]
    for level, role in enumerate(roles):
        obj = bpy.data.objects.new(f'{family}-{origin}-{level}-{role}', mesh_library[(family, 0, role)])
        scene.collection.objects.link(obj)
        obj.location = (origin[0], origin[1], level*LEVEL)


review = bpy.data.scenes.new('Heavy industrial / four open-ground kits')
for index, family in enumerate(VESSELS):
    assembly(review, family, (index*112, 0), 4, index)
# Two real neighboring hex centres, with every shared pipe end meeting its counterpart.
assembly(review, 'a', (104, 145), 7, 1)
assembly(review, 'c', (167, 181), 3, 0)
ground = bpy.data.meshes.new('Industrial review ground')
ground.from_pydata([(-400,-350,-.12),(700,-350,-.12),(700,550,-.12),(-400,550,-.12)], [], [(0,1,2,3)])
obj = bpy.data.objects.new('Industrial review ground', ground)
review.collection.objects.link(obj)
mat = bpy.data.materials.new('Industrial studio floor')
mat.diffuse_color = (.12,.135,.145,1)
ground.materials.append(mat)
review.world = bpy.data.worlds.new('Industrial studio world')
review.world.use_nodes = True
review.world.node_tree.nodes['Background'].inputs[0].default_value = (.36,.40,.44,1)
review.world.node_tree.nodes['Background'].inputs[1].default_value = .35
target = Vector((164, 70, 44))
cam_data = bpy.data.cameras.new('Industrial review camera')
cam = bpy.data.objects.new('Industrial review camera', cam_data)
review.collection.objects.link(cam)
cam.location = (target.x+250,target.y-430,target.z+330)
cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 520
review.camera = cam
for name, location, power, size in [('Key',(-80,-180,380),2200000,180),('Fill',(400,80,280),1000000,180)]:
    light = bpy.data.lights.new('Industrial '+name, 'AREA')
    light.energy, light.shape, light.size = power, 'DISK', size
    ob = bpy.data.objects.new('Industrial '+name, light)
    review.collection.objects.link(ob)
    ob.location = location
    ob.rotation_euler = (target-ob.location).to_track_quat('-Z','Y').to_euler()
review.render.engine = 'CYCLES'
review.cycles.samples = 48
review.cycles.use_denoising = True
review.render.resolution_x, review.render.resolution_y = 2000, 1300
review.render.resolution_percentage = 100
review.render.image_settings.file_format = 'PNG'
review.render.filepath = str(SOURCE / 'review.png')
review.view_settings.view_transform = 'AgX'
bpy.context.window.scene = review
bpy.context.view_layer.update()
bpy.data.libraries.write(str(SOURCE / 'heavy-industrial.blend'), {author, review}, path_remap='RELATIVE', fake_user=True)
(SOURCE / 'asset-report.json').write_text(json.dumps({'kits':report, 'levelHeight':LEVEL, 'ports':PORTS,
    'portHeight':4, 'clearGroundLane':{'halfWidth':5,'yMin':-20,'yMax':20}, 'concept':'concept.png'}, indent=2))
result = {'files':[str(OUT / ('heavy_industrial_'+family+'.glb')) for family in VESSELS],
          'report':report, 'scene':review.name, 'blend':str(SOURCE / 'heavy-industrial.blend')}
