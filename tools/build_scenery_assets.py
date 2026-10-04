"""Build the tile scenery catalog in an isolated Blender scene through MCP.

The existing tileset image identity is also the mesh identity. All dimensions
are tile pixels, Z-up, with the supporting ground at Z=0. Original images and
existing Blender scenes are preserved. Run build() via execute_blender_code.
"""
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
from math import cos, sin, pi, radians
from pathlib import Path
import json
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_board_tiles import declarations
from glb_geometry import linear, read_glb, write_glb

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT/'data/models/board'
REVIEW = ROOT/'tools/board-models/scenery'
YELLOW = (.88, .62, .08)
STEEL = (.38, .43, .46)
DARK = (.12, .16, .19)
CONCRETE = (.59, .58, .53)
GLASS = (.13, .30, .50)
WHITE = (.80, .82, .79)
WOOD = (.43, .26, .13)
WATER = (.13, .49, .65)


class Mesh:
    def __init__(self):
        self.vertices, self.parts = [], defaultdict(list)
        self.materials = {'scenery': {'id': 'scenery', 'diffuse': [1, 1, 1]}}
        self.transform = Matrix.Identity(4)

    def face(self, points, color, role='scenery', uv=None):
        p = [self.transform @ Vector(v) for v in points]
        n = (p[1]-p[0]).cross(p[2]-p[0]).normalized()
        if n.length < .5: return
        start = len(self.vertices)//12
        for i, v in enumerate(p):
            self.vertices.extend([*v, *n, *color, 1, *(uv[i] if uv else (v.x/12, v.y/12))])
        for i in range(1, len(p)-1): self.parts[role].extend((start, start+i, start+i+1))

    def box(self, center, size, color, angle=0):
        x, y, z = center
        a, b, c = [v/2 for v in size]
        turn = radians(angle)
        points = [(x+u*cos(turn)-v*sin(turn), y+u*sin(turn)+v*cos(turn), z+w)
                  for u, v, w in ((-a,-b,-c),(a,-b,-c),(a,b,-c),(-a,b,-c),
                                  (-a,-b,c),(a,-b,c),(a,b,c),(-a,b,c))]
        for ids in ((3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)):
            self.face([points[i] for i in ids], color)

    def beam(self, a, b, width, color, sides=6):
        a, b = Vector(a), Vector(b)
        d = (b-a).normalized()
        side = d.cross(Vector((.173,.917,.317))).normalized()
        up = d.cross(side).normalized()
        rings = [[p+(side*cos(i*2*pi/sides)+up*sin(i*2*pi/sides))*width/2 for i in range(sides)] for p in (a,b)]
        self.face(list(reversed(rings[0])), color)
        self.face(rings[1], color)
        for i in range(sides):
            j = (i+1)%sides
            self.face([rings[0][i], rings[0][j], rings[1][j], rings[1][i]], color)

    def cylinder(self, x, y, z, radius, height, color, sides=16):
        # Upright caps and ring() share the same XY phase; beam() chooses an arbitrary radial basis.
        rings=[[(x+radius*cos(i*2*pi/sides),y+radius*sin(i*2*pi/sides),h)
                for i in range(sides)] for h in (z,z+height)]
        self.face(list(reversed(rings[0])),color)
        self.face(rings[1],color)
        for i in range(sides):
            j=(i+1)%sides
            self.face([rings[0][i],rings[0][j],rings[1][j],rings[1][i]],color)

    def ellipsoid(self, center, size, color, sides=10, rows=5, floor=None):
        x,y,z = center
        def p(a,b):
            height=z+size[2]*cos(b)
            return (x+size[0]*cos(a)*sin(b), y+size[1]*sin(a)*sin(b),
                    max(floor,height) if floor is not None else height)
        for row in range(rows):
            for i in range(sides):
                a,b=i*2*pi/sides,(i+1)*2*pi/sides
                u,v=row*pi/rows,(row+1)*pi/rows
                points=[p(a,u),p(a,v),p(b,v),p(b,u)]
                if row==0: points=points[:3]
                elif row==rows-1: points=[points[0],points[1],points[3]]
                self.face(points,color)

    def ring(self, x, y, z, outer, inner, height, color, sides=24):
        for i in range(sides):
            a,b=i*2*pi/sides,(i+1)*2*pi/sides
            def p(r,t,h):return (x+r*cos(t),y+r*sin(t),z+h)
            self.face([p(outer,a,0),p(outer,b,0),p(outer,b,height),p(outer,a,height)],color)
            self.face([p(inner,b,0),p(inner,a,0),p(inner,a,height),p(inner,b,height)],color)
            self.face([p(outer,a,height),p(outer,b,height),p(inner,b,height),p(inner,a,height)],color)

    def place(self, function, x=0, y=0, z=0, angle=0, scale=1, **kwargs):
        old=self.transform.copy()
        self.transform @= Matrix.Translation((x,y,z)) @ Matrix.Rotation(radians(angle),4,'Z') @ Matrix.Scale(scale,4)
        function(self, **kwargs)
        self.transform=old

    def tree(self, x, y, size=12, variant=0):
        # Reuse the shipped tree kit, including its source UVs/materials.
        data=library('tree-broad',2)
        values=data['meshes'][0]['vertices']
        positions=[values[i:i+3] for i in range(0,len(values),12)]
        low=min(p[2] for p in positions)
        height=max(p[2] for p in positions)-low
        transform=self.transform @ Matrix.Translation((x,y,-low*size/height)) @ Matrix.Rotation(variant*1.71,4,'Z') @ Matrix.Scale(size/height,4)
        normals=transform.to_3x3().inverted().transposed()
        start=len(self.vertices)//12
        for i in range(0,len(values),12):
            v=values[i:i+12]
            self.vertices.extend([*(transform @ Vector(v[:3])),*(normals @ Vector(v[3:6])).normalized(),*v[6:]])
        roles={p['meshpartid']:p['materialid'] for n in walk(data['nodes']) for p in n.get('parts',[])}
        for mat in data['materials']: self.materials[mat['id']]=mat
        for part in data['meshes'][0]['parts']:
            self.parts[roles[part['id']]].extend(start+i for i in part['indices'])

    def data(self, name):
        parts=[{'id':r,'type':'TRIANGLES','indices':indices} for r,indices in self.parts.items()]
        return {'id':name,'meshes':[{'attributes':['POSITION','NORMAL','COLOR','TEXCOORD0'],
                                    'vertices':self.vertices,'parts':parts}],
                'materials':deepcopy(list(self.materials.values())),
                'nodes':[{'id':name,'parts':[{'meshpartid':r,'materialid':r} for r in self.parts]}]}


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get('children',[]))


@lru_cache(None)
def library(name, level=0): return read_glb(BOARD/(name+'.glb'),level)


def skylight(g, width=34, length=60, rows=5):
    g.box((0,0,.8),(width+2,length+2,1.6),CONCRETE)
    for x in range(2):
        for y in range(rows):
            px=(x-.5)*width/2
            py=(y-(rows-1)/2)*length/rows
            # A shallow pitched glass lantern with a central ridge, not photovoltaic cells.
            left=px-width/4+.4; right=px+width/4-.4
            def top(xx):return 2.0+(1-abs(xx)/(width/2))*3.4
            a,b=py-length/rows/2+.4,py+length/rows/2-.4
            g.face([(left,a,top(left)),(right,a,top(right)),(right,b,top(right)),(left,b,top(left))],
                   tuple(c*(.88+.07*((x+y)%3)) for c in GLASS))
    for x in (-width/2,0,width/2):
        z=2.0+(1-abs(x)/(width/2))*3.4
        g.beam((x,-length/2,z),(x,length/2,z),.6,WHITE,4)
    for y in range(rows+1):
        py=-length/2+y*length/rows
        for x in (-1,1):g.beam((0,py,5.4),(x*width/2,py,2.0),.65,STEEL,4)
    for y in (-length/2,length/2):
        g.face([(-width/2,y,1.5),(width/2,y,1.5),(width/2,y,2),(0,y,5.4),(-width/2,y,2)],GLASS)


def car(g, color=(.58,.22,.15)):
    g.box((0,0,1.5),(4.3,9.0,2),color)
    g.box((0,-.2,2.8),(3.8,4.3,1.6),GLASS)
    g.box((0,-.2,3.65),(3.9,2.6,.4),color)
    for y in (-2.8,2.8):
        for x in (-2.05,2.05):g.beam((x-.35,y,.9),(x+.35,y,.9),1.8,DARK,8)
    for x in (-1.5,1.5):
        g.box((x,4.52,1.8),(1.0,.15,.6),WHITE)
        g.box((x,-4.52,1.8),(.85,.15,.5),(.65,.06,.03))


def container(g, color=(.44,.19,.14)):
    g.box((0,0,3.2),(13.2,5.8,6.4),color)
    for x in range(-6,7,2):
        for y in (-2.95,2.95):g.box((x,y,3.3),(.25,.20,5.8),tuple(min(.9,c*1.18) for c in color))
    for y in (-1.7,1.7):g.beam((6.67,y,.6),(6.67,y,5.7),.22,STEEL,4)
    g.box((6.70,0,3.2),(.12,.15,6.1),DARK)


def crane(g, gantry=False, tip=False):
    if gantry or tip:
        if not tip:
            for x in (-10,10):
                for y in (-7,7):
                    g.box((x,y,1),(4,7,2),DARK)
                    g.beam((x,y,1),(x*.75,y,25),1.8,STEEL,4)
                g.beam((x,-7,20),(x,7,25),.9,YELLOW,4)
            g.box((0,0,25),(22,17,3),STEEL)
            g.box((-7,9,27),(5,5,5),WHITE)
            g.box((-7,11.6,27),(4,.1,2.4),GLASS)
        start,end,height=-32,34,28
        for x in (-4,4):
            g.beam((x,start,height),(x,end,height),1.0,YELLOW,4)
            g.beam((x,start,height+5),(x,end,height+5),.7,YELLOW,4)
            for y in range(-32,32,6):
                g.beam((x,y,height),(x,y+6,height+5),.5,YELLOW,4)
                g.beam((x,y,height+5),(x,y+6,height),.5,YELLOW,4)
        for y in range(-32,35,6):g.beam((-4,y,height),(4,y,height),.7,YELLOW,4)
        for x in (-2,2):g.beam((x,17,height),(x,17,13),.2,DARK)
        g.box((0,17,12.5),(6,4,1),YELLOW)
        return
    # Compact crawler-mounted construction crane with a triangular lattice boom.
    for x in (-4.5,4.5):
        g.box((x,0,1.3),(2.6,12,2.6),DARK)
        for y in (-4,-2,0,2,4):g.box((x,y,2.7),(2.8,.6,.3),STEEL)
    g.cylinder(0,0,2.3,4.8,1.5,STEEL)
    g.box((0,-1,6),(9,9,5),YELLOW)
    g.box((3,1,7.3),(3.1,4.2,3.2),GLASS)
    g.box((3,1,9),(3.6,4.6,.4),YELLOW)
    g.box((0,-5.6,6),(6,.25,2.5),DARK)
    points=[(-2,2,6),(2,2,6),(0,2,9)]
    end=[(-.7,29,16),(.7,29,16),(0,29,18)]
    for a,b in zip(points,end):g.beam(a,b,.7,YELLOW,4)
    for i in range(7):
        t,u=i/7,(i+1)/7
        for j in range(3):
            a=Vector(points[j]).lerp(Vector(end[j]),t)
            b=Vector(points[(j+1)%3]).lerp(Vector(end[(j+1)%3]),u)
            g.beam(a,b,.38,YELLOW,4)
    g.beam((0,29,17),(0,29,6),.20,DARK)
    g.box((0,29,5.5),(1.8,1.5,2),YELLOW)
    for i in range(5):
        a,b=(i-2)*pi/5,(i-1)*pi/5
        g.beam((sin(a),29,3.5-cos(a)),(sin(b),29,3.5-cos(b)),.4,STEEL)
    for i in range(3):g.box((-14+i*1.7,-9,.6),(1.3,12,1.2),(.65,.25,.08))


def bulldozer(g):
    for x in (-5,5):g.box((x,0,1.6),(3.3,15,3.2),DARK)
    g.box((0,0,4.1),(9,10,4),YELLOW)
    g.box((-2,0,7.5),(5,5,4),GLASS)
    g.box((-2,0,9.6),(5.6,5.6,.5),YELLOW)
    for x in (-4,4):g.beam((x,0,2.5),(x,11,2.5),1,YELLOW,4)
    g.box((0,12,3.2),(16,2,5.7),YELLOW)
    g.box((0,13,1),(16,.8,1),STEEL)


def excavation(g):
    soil=(.51,.43,.18)
    g.box((-5,0,.3),(33,48,.6),(.28,.25,.13))
    for x in (-23,14):g.box((x,0,3),(6,54,6),soil)
    # End banks meet the side banks; overlapping coplanar tops would flicker at their corners.
    g.box((-4.5,24.5,3),(31,5,6),soil)
    g.box((-4.5,-24.5,1.5),(31,5,3),soil)
    for i in range(4):g.ellipsoid((22+i%2*3,-18+i*10,1.5),(8,7,4),soil,8,3,floor=0)
    for x,y in ((-13,15),(-6,20),(-18,22)):g.ring(x,y,.5,2.5,1.7,4,CONCRETE,12)
    for i in range(3):g.box((-14+i*2,-17,1),(1.3,12,1.3),(.7,.28,.07),35)


def shelter(g):
    for x in (-11,11):
        for y in (-4,4):g.beam((x,y,0),(x,y,7),.65,STEEL,4)
    g.box((0,0,.3),(26,12,.6),CONCRETE)
    g.box((0,0,7),(26,12,.7),WHITE)
    for x in range(-12,13,4):g.beam((x,-6,7.6),(x,6,7.6),.4,STEEL,4)
    g.box((0,2,1.8),(19,2,.5),WOOD)


def garden_bed(g):
    g.box((0,-18,.5),(39,34,1),(.22,.32,.10))
    for x in (-20,20):g.box((x,-18,1),(1,35,2),CONCRETE)
    for y in (-35,-1):g.box((0,y,1),(41,1,2),CONCRETE)


def curve(points, steps=6):
    """A closed authored Catmull-Rom outline, not the jagged boundary of individual sprite pixels."""
    result=[]
    for i in range(len(points)):
        a,b,c,d=[Vector(points[(i+j)%len(points)]) for j in (-1,0,1,2)]
        for k in range(steps):
            t=k/steps
            result.append(tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)))
    return result


def round_rectangle(width, length, radius=3):
    result=[]
    for x,y,start in ((width/2-radius,length/2-radius,0),(-width/2+radius,length/2-radius,90),
                      (-width/2+radius,-length/2+radius,180),(width/2-radius,-length/2+radius,270)):
        for i in range(9):
            a=radians(start+i*90/8)
            result.append((x+radius*cos(a),y+radius*sin(a)))
    return result


def pool_shape(variant):
    if variant==2:
        return curve([(-7,27),(8,28),(17,20),(13,10),(5,2),(6,-9),(9,-21),(1,-27),(-11,-22),(-16,-10),(-14,4),(-18,17)])
    points=[]
    for i in range(96):
        t=i*2*pi/96
        if variant==1:x,y=17*cos(t)+10*cos(2*t)-4,23*sin(t)
        elif variant==3:
            radius=21+4*cos(3*(t-pi/2));x,y=radius*cos(t),radius*sin(t)+3
        else:
            a,b=23*cos(t),17*sin(t)*(1+.5*cos(2*t))
            x,y=a*cos(-pi/5)-b*sin(-pi/5),a*sin(-pi/5)+b*cos(-pi/5)
        points.append((x,y))
    return points


def pool_basin(g, outline, deck=True, natural=False):
    """One continuous closed coping/deck shell, with bevels, inner walls and recessed water."""
    if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(outline,outline[1:]+outline[:1])) < 0:
        outline=list(reversed(outline))
    normals=[]
    for i,p in enumerate(outline):
        before=(Vector(p)-Vector(outline[i-1])).normalized()
        after=(Vector(outline[(i+1)%len(outline)])-Vector(p)).normalized()
        n1=Vector((before.y,-before.x));n2=Vector((after.y,-after.x))
        normal=(n1+n2).normalized()
        normals.append(normal/max(.5,normal.dot(n1)))
    # Offset samples share indices across every ring, so there are no separate rim pieces or open joins.
    profile=[(0,0),(0,1.25),(.25,1.55),(1.75,1.55),(2,1.25),(2,.38)]
    if deck:profile += [(5,.38),(5,0)]
    else:profile += [(2,0)]
    rings=[[(x+n.x*offset,y+n.y*offset,z) for (x,y),n in zip(outline,normals)] for offset,z in profile]
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for ring in rings:
        for i,a in enumerate(ring):
            b=ring[(i+1)%len(ring)]
            for j in range(i+2,len(ring)):
                if i==0 and j==len(ring)-1:continue
                c,d=ring[j],ring[(j+1)%len(ring)]
                if cross(a,b,c)*cross(a,b,d)<-1e-8 and cross(c,d,a)*cross(c,d,b)<-1e-8:
                    raise ValueError('Pool outline offset intersects itself')
    for role in ('pool-water','pool-coping','pool-deck','pool-wall'):
        g.materials.setdefault(role,{'id':role,'diffuse':[1,1,1]})
    # One shared opaque, mipmapped surface in the ordinary prop pass; no animated-water/depth pass.
    g.materials['pool-water']['textures']=[{'id':'pool-water','type':'DIFFUSE',
        'filename':'textures/pool-water.png','minFilter':9987,'magFilter':9729,'wrapS':10497,'wrapT':10497}]
    for band,first in enumerate(rings):
        second=rings[(band+1)%len(rings)]
        role='pool-wall' if band==0 else 'pool-coping' if band<4 else 'pool-deck'
        color=(.39,.46,.24) if natural else (.62,.76,.76) if band==0 else WHITE if band<4 else (.64,.60,.51)
        for i in range(len(outline)):
            j=(i+1)%len(outline)
            shade=1-.025*((i//4)%2) if band in (2,5) else 1
            g.face([first[i],second[i],second[j],first[j]],tuple(c*shade for c in color),role)
    water=[Vector((x,y,.75)) for x,y in outline]
    for indices in tessellate_polygon([water]):
        points=[water[i] for i in indices]
        if (points[1]-points[0]).cross(points[2]-points[0]).z<0:points.reverse()
        uv=[((g.transform @ p).x/84+.5,(g.transform @ p).y/84+.5) for p in points]
        g.face(points,(.58,.78,.67) if natural else (.88,.95,.98),'pool-water',uv)


def inside_outline(x,y,outline):
    inside=False
    for a,b in zip(outline,outline[1:]+outline[:1]):
        if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside


def ledge(g):
    # Tapered parapet at one hex edge; the adjacent variants rotate this exact profile.
    p=[(-37,-8,0),(37,-8,0),(21,-36,0),(-21,-36,0),(-37,-8,10),(37,-8,10),(30,-20,10),(-30,-20,10)]
    for ids in ((3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)):
        g.face([p[i] for i in ids],CONCRETE)
    g.beam((-37,-8,10.3),(37,-8,10.3),.8,WHITE,4)


def bevel(g):
    outer=[(-33,-13,1),(33,-13,1),(22,-32,1),(-22,-32,1)]
    inner=[(-29,-15,6),(29,-15,6),(20,-29,2),(-20,-29,2)]
    # Glazed trapezoid with a tall inner edge and sloping pane, matching the edge roof family.
    g.face(list(reversed(inner)),GLASS)
    for i in range(4):
        j=(i+1)%4
        g.face([outer[i],inner[i],inner[j],outer[j]],STEEL)
        g.beam(inner[i],inner[j],.7,WHITE,4)


def vents(g):
    g.box((-12,0,3),(15,22,6),STEEL)
    for y in range(-9,11,3):g.box((-12,y,6.3),(14,.8,.6),WHITE)
    g.ring(16,0,0,7.5,5.8,13,CONCRETE,8)
    g.ring(16,0,12.5,8,5.5,1.5,WHITE,8)
    g.cylinder(16,0,.1,5.7,.3,DARK,8)


def pool(g, circular=False, small=False):
    outline=[(18*cos(i*pi/32),18*sin(i*pi/32)) for i in range(64)] if circular else round_rectangle(25,45,2)
    pool_basin(g,outline,deck=not small)
    if small:g.cylinder(0,0,.75,2,7,CONCRETE)


def garden(g, variant=0, pillars=False):
    if not pillars:
        g.cylinder(0,0,.05,25,.8,(.22,.34,.12),6)
        g.ring(0,0,0,26,24,1.4,CONCRETE,6)
    if variant==0 and not pillars:g.place(pool,z=.9,circular=True,small=True)
    if variant==3 and not pillars:
        g.ring(0,0,.8,14,12,1.5,CONCRETE,6)
        g.cylinder(0,0,1,12,.2,WATER,6)
    for i in range(6):
        a=i*pi/3+pi/6
        x,y=25*cos(a),25*sin(a)
        if pillars or variant in (1,2,4):
            g.cylinder(x,y,0,2.4,7,CONCRETE,6)
            g.cylinder(x,y,7,2.9,.9,WHITE,6)
        elif variant==0:g.tree(x,y,8,i)
    if variant==2 and not pillars:g.ring(0,0,1,20,18,2.5,(.16,.27,.09),6)
    if variant in (4,5) and not pillars:
        for i in range(24):
            a=i*2.39996;r=5+(i%4)*4
            g.ellipsoid((r*cos(a),r*sin(a),1.4),(1.5,1.5,1),(.57,.12,.27) if i%2 else (.85,.63,.18),6,3)


def table(g):
    g.box((0,0,2.2),(4.5,4.5,.6),WHITE)
    for x in (-1.5,1.5):
        for y in (-1.5,1.5):g.beam((x,y,0),(x,y,2),.35,STEEL,4)
    for y in (-4,4):
        g.box((0,y,1),(4.5,1.4,.4),WOOD)
        for x in (-1.5,1.5):g.beam((x,y,0),(x,y,1),.4,STEEL,4)


def chicken(g, color=(.80,.76,.64), rooster=False):
    # Upright two-legged bird: a single head/neck, folded wings and a feathered tail.
    # It deliberately does not share the quadruped head, ears, horns or limb arrangement.
    feet=(.70,.47,.15)
    for x in (-.55,.55):
        g.beam((x,0,.25),(x,.10,1.7),.20,feet,6)
        for spread in (-.45,0,.45):g.beam((x,0,.18),(x+spread,.85,.12),.13,feet,5)
    g.ellipsoid((0,0,2.2),(1.05,1.65,1.25),color,12,7)
    wing=tuple(c*.78 for c in color)
    for x in (-.90,.90):g.ellipsoid((x,-.30,2.4),(.33,1.17,.77),wing,10,5)
    neck=(.66,.26,.10) if rooster else color
    g.ellipsoid((0,1.18,3.0),(.67,.67,1.1),neck,10,6)
    g.ellipsoid((0,1.52,3.90),(.57,.69,.63),color if not rooster else (.57,.17,.08),12,6)
    g.face([(-.28,2.03,3.85),(.28,2.03,3.85),(0,2.68,3.68)],feet)
    g.face([(.28,2.03,3.85),(-.28,2.03,3.85),(0,2.15,3.51)],feet)
    for side in (-1,1):
        g.ellipsoid((side*.47,1.75,4.03),(.075,.105,.105),(.035,.028,.02),8,4)
    for i in range(3):g.ellipsoid((0,1.18+i*.29,4.51),(.16,.23,.28 if rooster else .19),(.68,.035,.025),8,4)
    g.ellipsoid((0,2.0,3.41),(.23,.24,.38),(.68,.035,.025),8,4)
    tail=(.05,.16,.15) if rooster else wing
    for i in range(5):
        x=(i-2)*.27
        g.beam((x,-1.10,2.3),(x*1.8,-2.45,3.55 if rooster else 3.05),.45,tail,6)


def orbital_gun(g):
    g.cylinder(0,0,0,24,1.5,CONCRETE,32)
    g.ring(0,0,1.5,23,21,1.0,STEEL,32)
    g.cylinder(0,0,1.5,11,3,DARK,16)
    g.box((-2,0,7),(18,18,6),STEEL)
    g.box((-11,0,5),(8,13,7),DARK)
    for y in (-5,5):
        g.beam((3,y,8),(23,y,10),3.2,STEEL,8)
        g.beam((19,y,9.6),(25,y,10.2),3.8,DARK,8)
        g.box((2,y,10.5),(6,4,1),CONCRETE)
    for x in (-18,-13,-8):
        for y in (-13,13):
            g.box((x,y,3.8),(4,4,4),STEEL)
            for offset in (-1,0,1):g.box((x+offset,y,5.85),(.35,3,.1),DARK)
    for y in (-10,10):g.box((1,y,8),(5,.4,1.3),(.6,.10,.06))


@lru_cache(None)
def animal_poses():
    return json.loads((REVIEW/'animal-source/poses.json').read_text())['animals']


def animal(g, species='cattle', color=(.74,.72,.65), mane=(.12,.075,.045),
           pose='standing', pattern=None):
    """One faceted, static mesh pipeline for the matching CC0 livestock set."""
    source=animal_poses()[species][pose]
    palette={'Main':color, 'Hair':mane,
             'Main_Dark':tuple(c*.82 for c in color),
             'Main_Light':tuple(min(1,c*1.12) for c in color),
             'Muzzle':tuple(c*.55 for c in color), 'Hooves':(.20,.19,.17),
             'Horns':(.72,.68,.54), 'Eye_Black':(.025,.022,.018), 'Eye_White':(.65,.65,.59)}
    for a,b,c,material in source['faces']:
        points=[source['vertices'][i] for i in (a,b,c)]
        shade=palette[material]
        if material in ('Main','Main_Light'):
            x,y,z=[sum(p[k] for p in points)/3 for k in range(3)]
            patches=((-2.8,5.2,1.35,1.2),(.35,4.1,.8,1.0),(2.2,5.7,.9,.8))
            if species=='pigs':patches=((-2,2.5,1.1,.9),(.6,2.5,.9,.9))
            if pattern is not None and any(((y-py)/ry)**2+((z-pz)/rz)**2<1
                    for py,pz,ry,rz in patches):
                shade=pattern
            if species=='bison' and y>.2 and z>2:
                shade=tuple(v*.70 for v in color)
            if species=='pigs' and y>4.05:shade=tuple(v*.75 for v in color)
        g.face(points,shade)
    if species=='bison':
        muzzle={i for face in source['faces'] if face[3]=='Muzzle' for i in face[:3]}
        x,y,z=[sum(source['vertices'][i][k] for i in muzzle)/len(muzzle) for k in range(3)]
        # A short shaggy beard below the broad jaw, attached to the posed muzzle.
        crown=[(x+.55*cos(i*pi/4),y-.75+.6*sin(i*pi/4),z-.12) for i in range(8)]
        tip=(x,y-.6,max(.15,z-1.3));fur=tuple(c*.55 for c in color)
        g.face(crown,fur)
        for i in range(8):g.face([crown[i],tip,crown[(i+1)%8]],fur)
    if species=='pigs':
        surface=BVHTree.FromPolygons([Vector(p) for p in source['vertices']],
                                    [f[:3] for f in source['faces']],all_triangles=True)
        for side in (-1,1):
            eye,normal,_,_=surface.ray_cast(Vector((side*10,3.1,2.8)),Vector((-side,0,0)))
            if eye is not None:g.ellipsoid(eye+normal*.035,(.09,.12,.10),palette['Eye_Black'],4,2)


def rubble(g, variant=0, path=False):
    rng=random.Random(119+variant)
    color=(.55,.49,.39) if variant==0 else (.38,.42,.44) if variant==1 else (.43,.23,.16)
    for i in range(70):
        x,y=rng.uniform(-28,28),rng.uniform(-27,27)
        if x*x+y*y>29**2 or path and abs(x)<9:continue
        h=rng.uniform(.7,4)
        g.box((x,y,h/2),(rng.uniform(2,6),rng.uniform(1,3),h),tuple(c*rng.uniform(.8,1.2) for c in color),rng.uniform(0,180))
        if i%9==0:g.beam((x,y,h),(x+5,y+4,h+3),.45,STEEL,4)


def fortified(g):
    for i in range(6):
        a,b=i*pi/3,(i+1)*pi/3
        p,q=Vector((27*cos(a),27*sin(a),0)),Vector((27*cos(b),27*sin(b),0))
        for row in range(3):
            for n in range(6):
                v=p.lerp(q,(n+.5+(row%2)*.15)/6)
                g.box((v.x,v.y,.65+row*1.2),(4.5,2.8,1.3),(.52,.44,.29),i*60+120)


def maglev(g, station=False, train=False, variant=0):
    g.box((0,0,1.2),(17,72,2.4),CONCRETE)
    for x in (-6,6):g.box((x,0,3),(1.4,72,2),STEEL)
    g.box((0,0,2.45),(8,72,.3),DARK)
    if station:
        g.box((-15,0,1.5),(10,42,3),CONCRETE)
        for y in (-15,15):g.beam((-15,y,3),(-15,y,11),.7,STEEL,4)
        g.box((-15,0,11),(12,42,1),WHITE)
    if train:
        for y in (-17,17):
            g.box((0,y,7),(10,30,7),WHITE)
            g.box((0,y,10.8),(8,27,.5),STEEL)
            for x in (-5.1,5.1):
                for v in range(-10,12,4):g.box((x,y+v,8),(.2,2.8,2.5),GLASS)
        g.box((0,32.1,8),(7,.2,3),GLASS)
        g.box((0,0,6),(7,3,4),DARK)
    if station or train:
        for i in range(3):g.place(car,x=15,y=-18+i*15,scale=.75,color=(.15+i*.15,.38,.38-i*.1))


def build_mesh(name, layouts):
    g=Mesh(); stem=Path(name).stem; layout=layouts.get(name,{})
    if name.startswith('fluff/skylight'):
        g.place(skylight,x=-1,y=1,angle=-(int(stem[-1])-1)*30)
    elif 'GlassRoof' in name:
        n=int(stem[-2:]); group=int(stem.split('-')[-2])
        if group==3:
            g.cylinder(0,0,0,30,2,STEEL)
            g.ellipsoid((0,0,1.6),(29,29,9),GLASS,16,6)
            for a in range(0,360,45):
                for k in range(6):
                    u,v=k*pi/12,(k+1)*pi/12
                    g.beam((29*cos(u)*cos(radians(a)),29*cos(u)*sin(radians(a)),1.6+9*sin(u)),
                           (29*cos(v)*cos(radians(a)),29*cos(v)*sin(radians(a)),1.6+9*sin(v)),.6,STEEL,4)
        else:g.place(skylight,angle=(0,90,-60,60)[(n-1)%4],width=27 if group==1 else 34,length=58,rows=4)
    elif name.startswith('fluff/ledge'):g.place(ledge,angle=-(int(stem[-1])-1)*60)
    elif name.startswith('fluff/stack'):g.place(vents,angle=-(int(stem[-1])-1)*60)
    elif name.startswith('fluff/bevel'):g.place(bevel,angle=-(int(stem[-1])-1)*60)
    elif name.startswith('fluff/construction'):
        # The board already supplies the supporting terrain; export equipment/debris only.
        n=int(stem[-1])
        if n==1:g.place(crane,x=-5,y=-9,angle=-55)
        elif n==2:excavation(g)
        else:g.place(bulldozer,angle=-55)
        rng=random.Random(143+n)
        for i in range(35):
            x,y=rng.uniform(6,23),rng.uniform(-24,-14)
            g.ellipsoid((x,y,.65),(1.2,.8,.6),CONCRETE,5,3)
    elif name.startswith('fluff/cars'):
        # Only roadside objects belong in the GLB. The board's shared road engine supplies the road.
        for x,y,angle,color in layout['cars']:g.place(car,x=x,y=y,angle=angle,color=color,scale=.8)
        if stem in ('cars_7','cars_2b'):g.place(shelter,x=-7,y=-22,angle=-30)
        if stem in ('cars_8','cars_3b'):
            for y in (-11,11):g.beam((24,y,0),(24,y,3.5),.8,STEEL,4)
            g.box((24,0,3.5),(2,25,3),YELLOW)
            for y in range(-10,13,5):g.box((24, y,5.05),(2,2,.1),DARK,25)
    elif name.startswith('fluff/square'):garden(g,int(stem[-1])-1)
    elif name.startswith('fluff/pillars'):
        for x,y in layout['pillars']:
            g.cylinder(x,y,0,3.8,7,CONCRETE,6)
            g.cylinder(x,y,7,4.4,.9,WHITE,6)
    elif name.startswith('fluff/garden'):
        g.place(garden_bed,angle=-(int(stem[-1])-1)*60)
        a=radians(-(int(stem[-1])-1)*60)
        for i,(x,y) in enumerate(((-9,-6),(10,-10),(-7,-25),(11,-26),(-1,-18))):
            g.tree(x*cos(a)-y*sin(a),x*sin(a)+y*cos(a),9,i)
    elif name.startswith('fluff/pool'):
        pool_basin(g,pool_shape(1))
        for i,(x,y) in enumerate(layout['trees']):g.tree(x,y,9,i)
    elif name.startswith('fluff/suburb'):
        n=int(stem[-1])
        if n==1:
            g.place(pool,x=-10,y=4,scale=.75,circular=True)
            for i in range(4):g.box((20+i*1.8,6,1.5+i),(2,29,3+i*2),CONCRETE,30)
            for i in range(3):g.place(car,x=-4+i*7,y=-22+i*2,scale=.75,angle=30,
                                   color=((.5,.42,.1),(.15,.45,.5),(.65,.08,.04))[i])
        elif n==2:
            g.cylinder(0,-3,0,24,.6,CONCRETE,16)
            g.place(shelter,x=-11,y=18,angle=-30)
            for i,(x,y) in enumerate(layout['trees']):g.tree(x,y,9,i)
            for i in range(3):g.place(car,x=-12+i*5,y=6-i*6,scale=.65,angle=30,color=(.56,.13,.35))
        else:
            g.box((0,0,.4),(43,43,.8),(.56,.44,.25),30)
            g.place(pool,x=-8,y=0,z=.9,angle=30,scale=.5)
            for i in range(3):g.ring(10+i*4,-7+i*2,1,2.6,1.8,4,CONCRETE,12)
            g.place(car,x=5,y=22,angle=30,scale=.65,color=(.65,.08,.04))
    elif name.startswith('fluff/beacon'):
        g.cylinder(0,0,0,22,3,DARK,6 if stem[-1]=='1' else 24)
        g.ring(0,0,3,9,6,1.5,STEEL)
        g.ellipsoid((0,0,4),(6,6,3),(.85,.07,.025),16,5)
    elif name.startswith('fluff/maglev'):
        n=int(stem[-1]); angle=0 if n in (1,2,3) and 'train' in stem else (0,-60,60)[(n-1)%3]
        if 'track' in stem or 'station' in stem:angle=(0,-60,60)[(n-1)%3]
        g.place(maglev,angle=angle,station='station' in stem or 'train' in stem and n in (2,5),train='train' in stem,variant=n)
    elif name.startswith('fluff/chickens'):
        variants={1:[(-16,-3,20,(.87,.86,.79),False),(16,10,-45,(.66,.45,.22),False)],
                  2:[(-7,18,35,(.11,.12,.11),True),(-19,-1,85,(.83,.80,.69),False),
                     (16,0,-55,(.59,.28,.14),False),(2,-21,155,(.12,.13,.10),False)],
                  3:[(-16,12,50,(.70,.63,.40),True),(17,6,-45,(.76,.72,.49),False),
                     (0,-17,145,(.61,.29,.12),True)]}
        for x,y,angle,color,rooster in variants[int(stem[-1])]:
            g.place(chicken,x=x,y=y,angle=angle,color=color,rooster=rooster,scale=1.3)
    elif name.startswith('fluff/horses'):
        if stem=='horses1':
            # Four adults and their foal, with the source's coat colors and facing directions.
            placements=[(-17,15,-85,1,(.64,.55,.33),(.18,.14,.08)),
                        (16,19,85,1,(.76,.76,.72),(.29,.28,.26)),
                        (-18,-11,-85,1,(.48,.22,.12),(.16,.075,.04)),
                        (1,-16,-65,.62,(.59,.32,.16),(.28,.14,.07)),
                        (23,-10,90,1,(.64,.43,.23),(.10,.075,.045))]
            for i,(x,y,angle,scale,color,mane) in enumerate(placements):
                g.place(animal,species='horse',x=x,y=y,angle=angle,scale=scale,color=color,mane=mane,
                        pose='relaxed' if i in (1,4) else 'standing')
        else:
            g.place(animal,species='horse',x=-14,y=8,angle=-65,color=(.42,.26,.12),pose='running-a')
            g.place(animal,species='horse',x=15,y=-9,angle=75,color=(.20,.21,.20),mane=(.08,.085,.08),pose='running-b')
    elif name.startswith('fluff/') and any(s in stem for s in ('pigs','cattle','bison')):
        species=''.join(c for c in stem if c.isalpha()); n=int(stem[-1])
        if species=='cattle':
            placements=([(-18,4,-80,'standing'),(18,6,40,'standing')] if n<3 else
                        [(-13,16,-75,'grazing'),(15,0,85,'resting'),(-6,-19,-70,'resting')])
            for i,(x,y,angle,pose) in enumerate(placements):
                g.place(animal,species=species,x=x,y=y,angle=angle,pose=pose,
                        color=(.77,.75,.67),pattern=(.50,.32,.14) if n==1 else (.12,.105,.085))
        elif species=='bison':
            g.place(animal,species=species,x=-17,y=-5,angle=70,scale=.75,color=(.53,.37,.20))
            g.place(animal,species=species,x=16,y=8,angle=155,color=(.37,.23,.12))
        else:
            placements=[(-16,5,60),(4,21,-100),(20,-6,70),(-8,-20,-65)]
            if n==2:placements=[(-18,17,175),(17,11,110),(-20,-10,-65),(14,-20,-120)]
            for i,(x,y,angle) in enumerate(placements):
                g.place(animal,species=species,x=x,y=y,angle=angle,pose='relaxed' if i==1 else 'standing',
                        color=(.70,.56,.46) if i%2==0 else (.56,.42,.32),
                        pattern=(.23,.18,.14) if i in (0,3) else None)
    elif '/SMV_Seaport/' in name:
        for x,y,angle,color in layout.get('containers',[]):g.place(container,x=x,y=y,angle=angle,color=color)
        if 'CraneTip' in stem:g.place(crane,gantry=True,tip=True,angle=(int(stem[-2:])-1)*60)
        elif 'GantryCrane' in stem:
            # Four source layout orientations; one continuous-height crane system including the tip tiles.
            n=int(stem[-2:]);group=int(stem.split('-')[-2]);angle=(0,-60,60,90)[group-1]+(180 if n>6 else 0)
            g.place(crane,x=16 if n<=6 else -16,y=0,gantry=True,angle=angle)
        else:
            for x,y in layout.get('hoists',[])[:1]:
                for dx in (-3,3):g.beam((x+dx,y-5,0),(x+dx,y-5,8),.55,YELLOW,4)
                g.box((x,y-5,8),(7,2,1),YELLOW)
    elif 'road_trees' in stem:
        for i,(x,y) in enumerate(layout.get('trees',[])):g.tree(x,y,12,i)
    elif '/SMV_Fluff/' in name:
        if 'SwimmingPool' in stem:
            n=int(stem[-2:])
            if n==1:
                g.box((0,0,.15),(33,70,.3),CONCRETE)
                g.place(pool_basin,y=7,outline=round_rectangle(18,38,1.5),deck=False)
                g.place(pool_basin,y=-25,outline=round_rectangle(18,12,1.5),deck=False)
            elif n==3:
                g.cylinder(0,0,0,33,.3,CONCRETE,32)
                pool_basin(g,pool_shape(3),deck=False)
                g.place(pool_basin,y=-28,outline=[(4*cos(i*pi/20),4*sin(i*pi/20)) for i in range(40)],deck=False)
            else:pool_basin(g,round_rectangle(48,28,4) if n==5 else pool_shape(n))
        elif 'Lake' in stem:
            n=int(stem[-2:])
            g.place(pool_basin,outline=pool_shape(1 if n in (1,3,5) else n),natural=True,angle=(n-1)*30,scale=.85)
        elif 'Landscape' in stem:
            n=int(stem[-2:]);sides=6 if n==1 else 32
            g.cylinder(0,0,0,32,.8,(.18,.29,.11),sides)
            g.ring(0,0,.6,32,30,1.5,CONCRETE,sides)
            g.ring(0,0,.8,24,22,1.4,CONCRETE,sides)
            g.ring(0,0,.8,9,7,1.5,CONCRETE,24)
            g.cylinder(0,0,1,7,.2,WATER,24)
            for i in range(4 if n<4 else 8):
                a=i*360/(4 if n<4 else 8)
                g.box((19*cos(radians(a)),19*sin(radians(a)),.9),(23,3.8,.2),CONCRETE,a)
            for i in range(80):
                a=i*2.39996;r=12+(i%4)*4
                if abs(sin(a*2))<.3:continue
                g.ellipsoid((r*cos(a),r*sin(a),1.2),(.75,.75,.65),(.7,.16,.15) if i%2 else (.8,.7,.12),5,3)
        elif 'Garden' in stem:
            if 'Table' in stem:
                for x,y in layout['tables']:g.place(table,x=x,y=y,scale=.65)
        else:return None
        if 'Landscape' not in stem:
            for i,(x,y) in enumerate(layout.get('trees',[])):
                if 'SwimmingPool' in stem and int(stem[-2:])==3 and inside_outline(x,y,pool_shape(3)):
                    # The source's planted pool islands need dry support above the basin waterline.
                    g.ring(x,y,.1,3.8,3.2,1.5,WHITE,24)
                    g.cylinder(x,y,1.2,3.2,.4,(.23,.29,.12),24)
                    g.place(lambda mesh:mesh.tree(0,0,10,i),x=x,y=y,z=1.6)
                else:g.tree(x,y,10,i)
    elif '/orbitalguns/' in name:g.place(orbital_gun,angle={'E':0,'N':90,'S':-90,'W':180}[stem[-1]])
    elif 'rubble' in stem and 'cleared' not in stem:
        variant=0 if 'light' in stem else 1 if 'medium' in stem else 2
        rubble(g,variant,path='path' in stem)
    elif stem=='fortified':fortified(g)
    elif stem.startswith('geyser'):
        rng=random.Random(51)
        for i in range(14):
            a=i*2*pi/14;r=9+rng.random()*5
            g.ellipsoid((r*cos(a),r*sin(a),1.3),(4,2.5,2.5),CONCRETE,6,3)
        g.cylinder(0,0,.05,7,.5,WATER if 'water' in stem else (.91,.29,.02))
        if 'on' in stem:
            for i in range(9):
                a=i*2*pi/9
                for j in range(5):
                    t,u=j/5,(j+1)/5
                    def p(t):return (cos(a)*t*t*11,sin(a)*t*t*11,1+30*t*(1-.68*t))
                    g.beam(p(t),p(u),1.2,(.48,.72,.77),5)
    else:return None
    return g if g.vertices else None


def blender_mesh(scene, name, mesh, location):
    values=mesh.vertices; points=[values[i:i+3] for i in range(0,len(values),12)]
    faces=[indices[i:i+3] for indices in mesh.parts.values() for i in range(0,len(indices),3)]
    data=bpy.data.meshes.new(name);data.from_pydata(points,[],faces);data.update()
    colors=data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='POINT')
    colors.data.foreach_set('color',[v for i in range(0,len(values),12) for v in (*[linear(c) for c in values[i+6:i+9]],values[i+9])])
    uv=data.uv_layers.new(name='UVMap')
    for loop in data.loops:uv.data[loop.index].uv=values[loop.vertex_index*12+10:loop.vertex_index*12+12]
    offset=0
    for role,indices in mesh.parts.items():
        source=mesh.materials[role]
        material_name='Scenery '+role
        if source.get('textures'):material_name+=' / '+Path(source['textures'][0]['filename']).stem
        mat=bpy.data.materials.get(material_name)
        if mat is None:
            mat=bpy.data.materials.new(material_name);mat.use_nodes=True
            bsdf=mat.node_tree.nodes.get('Principled BSDF')
            vertex=mat.node_tree.nodes.new('ShaderNodeVertexColor');vertex.layer_name='Color'
            mat.node_tree.links.new(vertex.outputs['Color'],bsdf.inputs['Base Color'])
            bsdf.inputs['Roughness'].default_value=.68
            if source.get('textures'):
                texture=mat.node_tree.nodes.new('ShaderNodeTexImage')
                filename=source['textures'][0]['filename']
                if (BOARD/filename).exists():
                    texture.image=bpy.data.images.load(str(BOARD/filename),check_existing=True)
                    mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
                    mat.node_tree.links.new(vertex.outputs['Color'],mix.inputs[1]);mat.node_tree.links.new(texture.outputs['Color'],mix.inputs[2])
                    mat.node_tree.links.new(mix.outputs[0],bsdf.inputs['Base Color'])
        slot=len(data.materials);data.materials.append(mat)
        for polygon in data.polygons[offset:offset+len(indices)//3]:polygon.material_index=slot
        offset+=len(indices)//3
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=location
    return obj


def build(only=None):
    rows,_=declarations();layouts=json.loads((REVIEW/'layouts.json').read_text())
    scene=bpy.data.scenes.new('Board scenery / tileset catalog')
    bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC'
    stats={}
    for name in sorted({r['image'] for r in rows if r['image']}):
        if only is not None and not any(key in name for key in only):continue
        mesh=build_mesh(name,layouts)
        if mesh is None:continue
        asset='scenery/'+str(Path(name).with_suffix('')).replace('\\','/')
        target=BOARD/(asset+'.glb');target.parent.mkdir(parents=True,exist_ok=True)
        data=mesh.data(Path(name).stem)
        for mat in data['materials']:
            for texture in mat.get('textures',[]):
                if 'data' not in texture:
                    texture['filename']=os.path.relpath(BOARD/texture['filename'],target.parent).replace('\\','/')
        if len(mesh.vertices)//12>65000:raise ValueError('Scenery exceeds rigid mesh budget: '+name)
        write_glb(target,levels={0:data})
        index=len(stats)
        blender_mesh(scene,name,mesh,((index%12)*100,-(index//12)*100,0))
        stats[name]={'asset':asset,'vertices':len(mesh.vertices)//12,'triangles':sum(len(v)//3 for v in mesh.parts.values()),
                     'height':round(max(mesh.vertices[2::12])-min(mesh.vertices[2::12]),3)}
    REVIEW.mkdir(parents=True,exist_ok=True)
    (REVIEW/'model-inventory.json').write_text(json.dumps(stats,indent=2)+'\n')
    scene.world=bpy.data.worlds.new('Scenery studio world');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.25,.30,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.view_settings.view_transform='AgX'
    bpy.data.libraries.write(str(ROOT/'tools/board-scenery.blend'),{scene},fake_user=True)
    return {'scene':scene.name,'models':len(stats),'triangles':sum(v['triangles'] for v in stats.values()),
            'largest':max(stats.items(),key=lambda v:v[1]['vertices']) if stats else None}
