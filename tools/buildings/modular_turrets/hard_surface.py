"""Native mesh helpers for layered weapon armor and routed service lines."""
import math
from mathutils import Vector


def section(w, h, cut):
    x, z = w / 2, h / 2
    c = min(cut, x * .65, z * .65)
    return [(-x+c,-z),(x-c,-z),(x,-z+c),(x,z-c),(x-c,z),(-x+c,z),(-x,z-c),(-x,-z+c)]


def shell(ref, name, rings, mat='armor'):
    return ref.loft(name, [[(x,y,z+cz) for x,z in section(w,h,c)] for y,w,h,c,cz in rings], mat)


def frame(ref, name, y, w, h, thickness, depth, mat='steel'):
    outer = section(w,h,min(w,h)*.16)
    inner = section(w-2*thickness,h-2*thickness,min(w,h)*.12)
    verts = [(x,yy,z) for yy,pts in ((y-depth,outer),(y,outer),(y,inner),(y-depth,inner)) for x,z in pts]
    faces=[]
    for a,b in ((0,8),(8,16),(16,24),(24,0)):
        for i in range(8): faces.append((a+i,a+(i+1)%8,b+(i+1)%8,b+i))
    return ref.mesh_obj(name,verts,faces,mat)


def side_panel(ref, name, x, outline, thickness=.12, mat='armor'):
    return ref.loft(name,[[(x+dx,y,z) for y,z in outline] for dx in (-thickness/2,thickness/2)],mat)


def pipe(ref, name, points, radius=.10, lod=0, mat='steel'):
    pts=[Vector(p) for p in points]; rings=[]; n=8 if lod==0 else 6
    for i,p in enumerate(pts):
        direction=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        u=direction.cross(Vector((0,0,1)))
        if u.length<.01: u=direction.cross(Vector((1,0,0)))
        u.normalize(); v=direction.cross(u).normalized()
        rings.append([tuple(p+radius*(u*math.cos(j*math.tau/n)+v*math.sin(j*math.tau/n))) for j in range(n)])
    return ref.loft(name,rings,mat)


def harden(ref, obj, width=.06):
    """LOD0 worn chamfers on every sharp edge, shaded with area-weighted normals."""
    if ref.LOD:
        return obj
    import bpy, bmesh
    me = obj.data
    if ref.MATS['edge'].name not in me.materials:
        me.materials.append(ref.MATS['edge'])
    bm = bmesh.new(); bm.from_mesh(me)
    sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(35)]
    if sharp:
        bmesh.ops.bevel(bm, geom=sharp, offset=width, segments=1, affect='EDGES', clamp_overlap=True,
                        material=me.materials.find(ref.MATS['edge'].name))
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    modifier = obj.modifiers.new('weighted', 'WEIGHTED_NORMAL'); modifier.weight = 100
    with bpy.context.temp_override(object=obj, active_object=obj):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def radial_bar(ref, name, angle, half, r0, r1, y0, y1, mat='dark'):
    """A bar between two radii around the Y axis: the ribs between slots of sleeves and brakes."""
    points = [(r * math.cos(a), y, r * math.sin(a)) for y in (y0, y1)
              for r, a in ((r0, angle - half), (r1, angle - half), (r1, angle + half), (r0, angle + half))]
    faces = [(0,1,2,3), (7,6,5,4), (0,4,5,1), (1,5,6,2), (2,6,7,3), (3,7,4,0)]
    return ref.mesh_obj(name, points, faces, mat)


def stud(ref, center, normal, radius=.1, mat='edge'):
    """Closed hexagonal bolt head standing .05 proud of a surface, facing e.g. (0, -1, 0)."""
    n = Vector(normal).normalized()
    u = n.cross(Vector((0, 0, 1)) if abs(n.z) < .9 else Vector((1, 0, 0))).normalized()
    v = n.cross(u)
    hexagon = [radius * (u * math.cos(i * math.pi / 3) + v * math.sin(i * math.pi / 3)) for i in range(6)]
    points = [tuple(Vector(center) + n * depth + p) for depth in (-.02, .05) for p in hexagon]
    faces = [tuple(range(5, -1, -1)), tuple(range(6, 12))] + [(i, (i + 1) % 6, 6 + (i + 1) % 6, 6 + i) for i in range(6)]
    return ref.mesh_obj('Captive bolt cap', points, faces, mat)


def hose(ref, name, points, radius=.15, lod=0, mat='black', section=None, rib=.8):
    """Corrugated hose (or, with a rectangular section, an articulated feed chute) along a smooth spline.

    section: cross-section as (u, v) multiples of the radius; u runs along X where the path allows.
    rib: radius factor of every other ring; 1 gives a smooth cable. LOD1 keeps the routing without ribs.
    """
    sides = 6 if lod == 0 else 4
    section = section or [(math.cos(j * math.tau / sides), math.sin(j * math.tau / sides)) for j in range(sides)]
    pts = [Vector(p) for p in points]
    ends = [pts[0], *pts, pts[-1]]
    path = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = ends[i:i + 4]
        steps = max(2, int((p2 - p1).length / (radius * 2.6 if lod == 0 else max(radius * 4, .7))))
        for k in range(steps):
            t = k / steps
            path.append(.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    path.append(pts[-1])
    rings, u = [], None
    for i, p in enumerate(path):
        d = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        # u starts across the path along X (flat against a side face); parallel transport keeps it from twisting.
        if u is None:
            axis = Vector((1, 0, 0)) if abs(d.x) < .9 else Vector((0, 0, 1))
            u = axis - d * axis.dot(d)
        else:
            u = u - d * u.dot(d)
        u.normalize(); v = d.cross(u)
        r = radius * (1 if i % 2 == 0 or lod else rib)
        rings.append([tuple(p + r * (u * a + v * b)) for a, b in section])
    obj = ref.loft(name, rings, mat)
    if len(section) > 4:
        for poly in obj.data.polygons: poly.use_smooth = True
    return obj


def side_vent(ref, x, cy, cz, length, height, lod):
    side='X' if x>0 else '-X'
    ref.flat_patch('Recessed cooling grille',(x,cy,cz),(length,height),side,'black')
    if lod==0:
        for i in range(6):
            y=cy-length*.42+length*.84*i/5
            ref.block('Cooling grille fin',(x,y,cz),(.045,.075,height*.85),'steel',cut=0,bevel=0)
