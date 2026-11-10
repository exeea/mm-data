"""Authored buildings laid with a look's own kit bays: what the looks' building files share (imperial_buildings,
heritage_buildings). A block is a box whose walls are laid with the kit's bays at their real widths, a pier closing
every corner; a volume stays behind its walls; the hexes a building's volumes cover are its footprint in the game
(hex centres 62.34 apart across, 72 along a column, odd columns 36 up; printed as HEX lines).

A look names its pieces with use(): piece(kind, base, rng, length), the builder of one bay; fill(length, base, accent,
kind), a stretch of its pier beside a bay of that kind; accent, the bay kinds whose ends take the look's accent pier
(Imperial's lacquer columns); downpipes(p, q, spec, z0, z1).
"""
import math
import random
import re
from types import SimpleNamespace

import bpy

import authored_examples as shared
import civic_blocks as c
import civic_habitat as h
import frontier_buildings as f
import theme_kits as k
import utopia_buildings as u
from civic_habitat import PAINT, SLATS, add, cuboid, deck, disc
from glb_geometry import write_glb
from theme_kits import LEVEL
from utopia_buildings import LAWN_REPEAT, TURF

EXTEND = 8.0  # How far a wall's pier goes on past its end, for the corner's mitre to trim.
BEHIND = 2.4  # How far inside its walls a block's volume stays: the game's floors never show in a recess.
volumes = []  # (outline, top) of every volume, for the hexes' report.
theme = SimpleNamespace(piece=None, fill=None, accent=(), downpipes=None)


def use(piece, fill, accent=(), downpipes=None):
    """Names the look whose bays run() and block() lay."""
    theme.piece, theme.fill, theme.accent, theme.downpipes = piece, fill, accent, downpipes


# -- Walls ------------------------------------------------------------------------------------------

def widths(spec, length):
    """A wall's bays as (kind, width): kinds, or (kind, width) pairs; the kinds without a width share what is left."""
    spec = [spec] if isinstance(spec, str) else spec
    free = sum(1 for item in spec if isinstance(item, str))
    share = (length-sum(item[1] for item in spec if not isinstance(item, str)))/free if free else 0.0
    bays = [(item, share) if isinstance(item, str) else item for item in spec]
    assert abs(sum(width for _, width in bays)-length) < .01 and all(width > 0 for _, width in bays), (spec, length)
    return bays


def run(p, q, spec, storeys=1, z0=0.0, keeps=(), seed=0, lift=1.0, corners=(False, False), ground=None, red=None):
    """Lays a wall from p to q, the building on its left: per storey its bays (`spec`, or spec(storey)) at their own
    widths, and at each end that is a corner the look's pier carried on past it (its fill): its accent pier where `red`
    says so for that end, else where the wall's own end bay is one of the look's accent kinds."""
    along, length = f.unit(p, q), math.dist(p, q)
    rng = random.Random(seed)
    for storey in range(storeys):
        z = z0+storey*LEVEL*lift
        base = (z0 == 0 and storey == 0) if ground is None else ground and storey == 0
        bays = widths(spec(storey) if callable(spec) else spec, length)
        at = 0.0
        for kind, width in bays:
            f.lay(theme.piece(kind, base, rng, width), (p[0]+along[0]*at, p[1]+along[1]*at), along, z, 1.0, keeps, lift)
            at += width
        for end, (kind, _) in enumerate((bays[0], bays[-1])):
            if corners[end] and kind != 'skip':
                start = (p[0]-along[0]*EXTEND, p[1]-along[1]*EXTEND) if end == 0 else q
                accent = kind in theme.accent if red is None else red[end]
                f.lay(lambda: theme.fill(EXTEND, base, accent, kind), start, along, z, 1.0, keeps, lift)


def block(ring, faces, storeys, z0=0.0, hidden=(), butt=(), seed=0, lift=1.0, default='window', ground=None, pipes=()):
    """A box of the building: its outline (counter-clockwise) laid with bays, faces[edge] a spec (see run); edges hidden
    inside another block left out; a wall's end in `butt` (edge, 0 its start or 1 its end) dies square into another
    block's wall (a dict gives the storeys it does so for, from the ground), every other end is a corner, mitred with
    its pier: the look's accent pier where either wall's end bay is an accent kind. Edges in `pipes` take downpipes."""
    n = len(ring)

    def spec(i, storey):
        value = faces.get(i, default)
        return value(storey) if callable(value) else value

    def ends(i, storey):
        return [kind for kind, _ in widths(spec(i, storey), math.dist(ring[i], ring[(i+1) % n]))]

    def square(i, end, storey):
        return (i, end) in butt and (not isinstance(butt, dict) or storey < butt[i, end])

    for i in range(n):
        if i in hidden:
            continue
        p, q = ring[i], ring[(i+1) % n]
        normal = f.outward(p, q)
        before, after = (i-1) % n, (i+1) % n
        for storey in range(storeys):
            kinds = ends(i, storey)
            keeps, corners, red = [], [not square(i, 0, storey), not square(i, 1, storey)], [kinds[0] in theme.accent, kinds[-1] in theme.accent]
            if corners[0]:
                keeps.append(f.mitre(p, f.outward(ring[before], p), normal, q))
                red[0] = red[0] or before not in hidden and ends(before, storey)[-1] in theme.accent
            if corners[1]:
                keeps.append(f.mitre(q, normal, f.outward(q, ring[(i+2) % n]), p))
                red[1] = red[1] or after not in hidden and ends(after, storey)[0] in theme.accent
            base = (z0 == 0 and storey == 0) if ground is None else bool(ground) and storey == 0
            run(p, q, spec(i, storey), 1, z0+storey*LEVEL*lift, keeps, seed*101+i*7+storey, lift, corners, base, red)
        if i in pipes:
            theme.downpipes(p, q, spec(i, storeys-1), 0.0, z0+storeys*LEVEL*lift)


def volume(name, ring, z0, z1, behind=BEHIND):
    """A building volume kept `behind` its block's walls."""
    inner = f.inset(ring, behind) if behind else ring
    c.volume(name, inner, z0, z1)
    volumes.append((inner, z1))


# -- Shapes ----------------------------------------------------------------------------------------

def reach_of(ring):
    """How far a convex outline insets before it closes: half its least width."""
    least = 1e9
    for i in range(len(ring)):
        p, q = ring[i], ring[(i+1) % len(ring)]
        nx, ny = f.outward(p, q)
        least = min(least, max(-((v[0]-p[0])*nx+(v[1]-p[1])*ny) for v in ring))
    return least/2


def distinct(verts):
    """A face's corners without repeats: a quad whose top edge closed into a ridge's end is a triangle."""
    return [v for i, v in enumerate(verts) if all(math.dist(v, w) > 1e-4 for w in verts[:i])]


def facing(name, key, colour, verts, normal, **flags):
    """A face through verts, wound to face `normal`."""
    add(name, key, colour, verts, [k.facing(verts, normal)], **flags)


def bar(name, path, radius, colour, fine=True):
    """A thin square bar along a path; fine ones go at the far levels."""
    obj = u.tube(name, path, radius, PAINT, colour, sides=4)
    obj['detail'] = fine
    return obj


# -- Parts ------------------------------------------------------------------------------------------

BOXWOOD = (.34, .46, .22)


def screen(name, ring, z, height=5.0, units=(), louvre=(.84, .85, .84)):
    """Roof plant behind a louvred screen: a pale box of louvres standing on the deck, a steel rim on it, and fan units
    at (x, y, half length, half width)."""
    inner = f.inset(ring, .3)
    f.wall_ring(name+' screen', ring, z, z+height, SLATS, louvre)
    for i in range(len(inner)):
        (ax, ay), (bx, by) = inner[i], inner[(i+1) % len(inner)]
        add(name+' screen back', PAINT, (.50, .51, .51), [(bx, by, z), (ax, ay, z), (ax, ay, z+height), (bx, by, z+height)], [(0, 1, 2, 3)])
    f.frustum(name+' screen rim', f.inset(ring, -.15), z+height, inner, z+height, PAINT, (.78, .79, .78))
    f.cap(name+' plant deck', inner, z+.25, PAINT, (.45, .46, .46))
    for x, y, a, b in units:
        cuboid(name+' unit', x-a, x+a, y-b, y+b, z+.25, z+height-.8, PAINT, (.72, .73, .72), omit='b')
        for fan in ((-a/2,), (a/2,)) if a > 2*b*.8 else ((0,),):
            disc(name+' fan', x+fan[0], y, z+height-.75, min(a/2, b)*.72, 'z', h.GRILLE, (.62, .64, .66), 12)


def steps(x0, x1, y0, y1, z, count, stone):
    """Steps of `stone` (material, colour) from the ground at y0 up to z at y1 (towards +y)."""
    tread, riser = (y1-y0)/count, z/count
    for i in range(count):
        cuboid('step', x0, x1, y0+i*tread, y1, i*riser, (i+1)*riser, *stone, omit='bk')


def paving(x0, x1, y0, y1, key, colour, z=.4):
    """A stone apron."""
    cuboid('paving', x0, x1, y0, y1, 0, z, key, colour, omit='b')


def boxwood(x, y, z, size, rng):
    """A clipped ball of boxwood."""
    u.lump(x, y, z, size, size*.8, BOXWOOD, rng, sides=7)


def planter(x0, x1, y0, y1, z, rng, stone, height=2.6, size=3.6):
    """A stone planter of clipped boxwood: four walls round sunk soil."""
    for a0, a1, b0, b1 in ((x0, x1, y0, y0+.5), (x0, x1, y1-.5, y1), (x0, x0+.5, y0+.5, y1-.5), (x1-.5, x1, y0+.5, y1-.5)):
        cuboid('planter', a0, a1, b0, b1, z, z+height, *stone, omit='b')
    deck('planter soil', x0+.5, x1-.5, y0+.5, y1-.5, z+height-.5, h.SOIL, (.24, .22, .18))
    along_x = x1-x0 >= y1-y0
    length, across = (x1-x0, y1-y0) if along_x else (y1-y0, x1-x0)
    count = max(1, round((length-1)/(size*.95)))
    for i in range(count):
        t = (i+.5)/count
        px, py = (x0+length*t, (y0+y1)/2) if along_x else ((x0+x1)/2, y0+length*t)
        boxwood(px, py, z+height-.7, min(size, across-.8)*rng.uniform(.9, 1.08), rng)


# -- Export ----------------------------------------------------------------------------------------

def far_piece(obj, fine):
    """Whether a part stays at the farthest level: all but the fine lines and marks."""
    name = re.sub(r'\.\d+$', '', obj.name)
    return not any(word in name for word in fine)


def inside(ring, x, y):
    """Whether (x, y) lies in a convex counter-clockwise outline."""
    return all(f.cross((q[0]-p[0], q[1]-p[1]), (x-p[0], y-p[1])) >= 0 for p, q in zip(ring, ring[1:]+ring[:1]))


def hexes():
    """Each hex's share the volumes cover, and the roof that covers most of it: the building's footprint in the game."""
    shares = {}
    step = 2.0
    for i in range(-4, 5):
        for j in range(-4, 6):
            cx, cy = f.HEX_X*i, f.HEX_Y*j+(36 if i % 2 else 0)
            tops, total = {}, 0
            for a in range(-21, 22):
                for b in range(-18, 19):
                    dx, dy = a*step, b*step+step/2
                    if abs(dy) > 36 or abs(dx) > 41.5625-abs(dy)*20.78125/36:
                        continue
                    total += 1
                    best = max((top for ring, top in volumes if inside(ring, cx+dx, cy+dy)), default=None)
                    if best is not None:
                        tops[best] = tops.get(best, 0)+1
            if tops:
                shares[i, j] = sum(tops.values())/total, max(tops, key=tops.get)
    return shares


def build_scene(full, builder, finish, painted):
    """Builds `builder`'s building as the scene `full`: finish(obj) gives a part its look's night light and, without
    UVs, its roofing's; painted(obj) says which parts take a building's tint."""
    h.weathered_material.__defaults__[0].clear()
    shared.fresh(full)
    shared.role = ''
    h.bins.clear()
    h.fixtures.clear()
    volumes.clear()
    h.SHIFT_Y = 0
    u.LOD = 0
    builder()
    h.flush()
    u.flush_cards()
    for obj in shared.objects:
        finish(obj)
        if not obj.data.uv_layers and obj['board_material'] == TURF:
            layer = obj.data.uv_layers.new(name='UVMap')
            for loop in obj.data.loops:
                co = obj.data.vertices[loop.vertex_index].co
                layer.data[loop.index].uv = co.x/LAWN_REPEAT, co.y/LAWN_REPEAT
    for obj in shared.objects:
        if painted(obj) and not obj.get('building_emission') and not obj.get('building_emission_off'):
            obj['building_paint'] = True
    for obj in shared.volumes:
        obj.hide_set(True)
    bpy.context.view_layer.update()
    for obj in shared.objects:
        shared.project_uvs(obj)
    bpy.context.scene['asset_id'] = 'buildings/authored/'+full
    bpy.context.scene['hex_width'], bpy.context.scene['hex_height'], bpy.context.scene['level_height'] = 83.125, 72, LEVEL


def build(full, builder, finish, painted, fine):
    """Writes data/models/buildings/authored/<full>.glb: three levels (the farthest without the parts named in `fine`),
    its volumes and night lights; prints its hexes."""
    build_scene(full, builder, finish, painted)
    bpy.context.view_layer.update()
    levels = {i: shared.export_model([obj for obj in shared.objects if i < 2 or far_piece(obj, fine)], f'{full}-lod{i}', level=i, exact=True)
              for i in (0, 1, 2)}
    helpers = shared.export_model(shared.volumes, full, helper=True)
    stats = {i: {'vertices': sum(len(m['vertices'])//12 for m in level['meshes']),
                 'triangles': sum(len(p['indices'])//3 for m in level['meshes'] for p in m['parts'])} for i, level in levels.items()}
    assert all(s['vertices'] < 65535 for s in stats.values()), stats
    lights = [{'position': [x, z, -y], 'color': [1, .64, .29], 'power': .65, 'size': 13} for x, y, z in h.fixtures]
    write_glb(shared.DEST/(full+'.glb'), levels=levels, groups={'building_volumes': helpers}, extras={'mmNightLights': lights})
    for (i, j), (share, top) in sorted(hexes().items()):
        print(f'HEX {i:2d} {j:2d} {share:5.0%} {"in" if share >= .5 else "out":3s} top {top/LEVEL:.2f} levels')
    print('RESULT', full, stats, 'lights', len(lights))
    return stats
