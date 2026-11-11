"""The park props: garden squares that fill a hex, a fountain, formal gardens, a grandstand, a bench, a picnic table and
a pillar. Lawn, stone, mulch and water are the board's own materials; shrubs, trees and flowers are cards of its plant
cutouts. Each keeps the name and the footprint the legacy park layouts (scenery/layouts.json) place it by.

Run: blender -b --factory-startup --python park_props.py -- [name ...]   (none: all)
Writes data/models/board/scenery/parks/<name>.glb, two levels of detail (the far one without the fine parts), standing
on the ground about its origin. A hex is 83 across corners and 72 across flats: 3 units to the metre.
"""
import math
import random
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(TOOLS), str(TOOLS/'buildings')]
import look_accessories as la
from look_accessories import PAINT, add, f, hk, kb, shared, u
from glb_geometry import write_glb

PARKS = la.SCENERY/'parks'
LEAF = 'terrain/surfaces/grassland-floor'  # An opaque leafy green: a clipped hedge's body, the foliage under flowers.
MULCH = 'terrain/surfaces/concrete-mulch'
GRAVEL = 'terrain/surfaces/scatter-stone'
LAWN = (.80, .92, .66)  # Mown, greener than the board's meadow.
BOXWOOD, BOXWOOD_TOP = (.62, .78, .44), (.84, .98, .58)
GRAVEL_TINT, FLAGS, FLAGS_DARK = (.92, .86, .74), (.90, .88, .83), (.70, .68, .64)
RED, YELLOW, WHITE, PINK, VIOLET = (.86, .22, .20), (1, .84, .26), (1, 1, 1), (.96, .62, .72), (.62, .48, .78)
TIMBER, TIMBER_PALE = hk.TIMBER, (.56, .40, .25)
TAU = math.tau
# Near-level triangle limits: a prop that fills a hex, a small one.
LIMITS = {'small': 700, 'hex': 2800}


def at(x, y, a, px, py):
    """The point (px, py) of a part turned by `a` degrees and moved to (x, y)."""
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return x+px*c-py*s, y+px*s+py*c


def box(name, x, y, a, x0, x1, y0, y1, z0, z1, key, colour, omit='b', **flags):
    """A box in a part's own frame (turned by `a`, at (x, y)); `omit` names faces left out (b t f r k l)."""
    v = [(*at(x, y, a, px, py), z) for z in (z0, z1) for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    faces = {'b': (3, 2, 1, 0), 't': (4, 5, 6, 7), 'f': (0, 1, 5, 4), 'r': (1, 2, 6, 5), 'k': (2, 3, 7, 6), 'l': (3, 0, 4, 7)}
    add(name, key, colour, v, [face for k, face in faces.items() if k not in omit], **flags)


def flush_cards(detail):
    """Makes the plant cards placed so far one mesh, on the near level alone when `detail`."""
    count = len(shared.objects)
    u.flush_cards()
    for obj in shared.objects[count:]:
        obj['detail'] = detail


def polar(radius, degrees):
    return radius*math.cos(math.radians(degrees)), radius*math.sin(math.radians(degrees))


def ring_band(name, inner, outer, z, key, colour, **flags):
    """A flat band between two rings of as many points."""
    count = len(inner)
    for i in range(count):
        j = (i+1) % count
        add(name, key, colour, [(*inner[i], z), (*outer[i], z), (*outer[j], z), (*inner[j], z)], [(0, 1, 2, 3)], **flags)


# -- Parts ------------------------------------------------------------------------------------------

def bench(x, y, a):
    """A park bench, its back to +y in its own frame: iron ends, timber slats."""
    for side in (-3.0, 3.0):
        box('bench end', x, y, a, side-.16, side+.16, -1.0, 1.0, 0, 1.45, PAINT, hk.IRON)
        box('bench end', x, y, a, side-.16, side+.16, .72, 1.0, 1.45, 3.2, PAINT, hk.IRON, detail=True)
        box('bench arm', x, y, a, side-.22, side+.22, -1.0, .8, 2.25, 2.45, PAINT, hk.IRON, omit='', detail=True)
    for y0, y1 in ((-1.0, -.45), (-.35, .2), (.3, .75)):
        box('bench seat', x, y, a, -3.3, 3.3, y0, y1, 1.45, 1.65, PAINT, TIMBER, omit='')
    for z0, z1 in ((2.05, 2.5), (2.7, 3.15)):
        box('bench back', x, y, a, -3.3, 3.3, .8, .98, z0, z1, PAINT, TIMBER, omit='')


def lamp(x, y):
    """An iron lamp post under one lantern."""
    la.turned('lamp foot', [(.9, 0), (.7, 1.1), (.4, 1.6)], 6, PAINT, hk.IRON, x, y)
    la.turned('lamp post', [(.32, 1.6), (.24, 10.6), (.6, 10.9)], 6, PAINT, hk.IRON, x, y)
    la.lantern(x, y, 10.9)


def shrub(x, y, z, size, rng, body=True):
    """A round shrub: a leafy body under cards of real leaves."""
    if body:
        la.mound('shrub body', x, y, z, size*.42, size*.62, BOXWOOD, 7, key=LEAF, rng=rng)
    u.shrub(x, y, z, size, rng)


clumps = []


def drift(points, z, tint, rng, size=1.7):
    """Clumps in flower at these points, planted by plant_flowers."""
    for x, y in points:
        clumps.append((x+rng.uniform(-.3, .3), y+rng.uniform(-.3, .3), z, tint, size*rng.uniform(.85, 1.15)))


def plant_flowers(rng):
    """The drifts' clumps: three blooms on a low tuft of foliage each; every other one is on the near level alone."""
    for near in (True, False):
        for x, y, z, tint, size in clumps[0 if near else 1::2]:
            spin = rng.uniform(0, TAU)
            tuft = [(x+size*.55*math.cos(spin+TAU*k/5), y+size*.55*math.sin(spin+TAU*k/5), z) for k in range(5)]+[(x, y, z+size*.32)]
            add('flower foliage', LEAF, (.50, .66, .36), tuft, [(k, (k+1) % 5, 5) for k in range(5)], detail=near)
            for i in range(3):
                u.tilted(u.FLOWER, tint, x, y, z+size*.12, size, size, spin+i*TAU/3, math.radians(rng.uniform(58, 74)))
        flush_cards(near)
    clumps.clear()


def hedge(p, q, width, height, rng, name='hedge'):
    """A clipped hedge from p to q: a leafy block, lighter on top, its edges broken by sprigs on the near level."""
    (px, py), (qx, qy) = p, q
    length = math.hypot(qx-px, qy-py)
    a = math.degrees(math.atan2(qy-py, qx-px))
    box(name, px, py, a, 0, length, -width/2, width/2, 0, height, LEAF, BOXWOOD, omit='bt')
    box(name+' top', px, py, a, 0, length, -width/2, width/2, height-.01, height, LEAF, BOXWOOD_TOP, omit='bfrkl')
    for i in range(max(1, round(length/2.6))):
        x, y = at(px, py, a, (i+.5)*length/max(1, round(length/2.6)), rng.uniform(-.2, .2)*width)
        u.tilted(u.BUSH, rng.choice(u.BUSH_TINTS), x, y, height-.9, width*1.5, 1.7, rng.uniform(0, TAU), math.radians(rng.uniform(50, 70)))


def pier(x, y, tall=7.4, half=1.5):
    la.stone_pier(x, y, tall, half)


def square(lawn=True):
    """A garden square's base: the hex's stone kerb, and its lawn. Gives the lawn's level."""
    ring = f.regular(0, 0, 26, 6)
    la.ring_wall('kerb', ring, 0, 1.0, hk.STONE, hk.DRESSING, thick=1.5)
    if lawn:
        f.cap('lawn', f.inset(ring, 1.5), .7, u.TURF, LAWN)
    return .7


# -- Garden squares ---------------------------------------------------------------------------------

def plaza(rng):
    """A paved court in a lawn: flags round to a dark border course, benches and lamps facing the middle (where a
    fountain may stand), a shrub in each corner of the lawn."""
    z = square()
    court, border = f.regular(0, 0, 20.4, 24), f.regular(0, 0, 21.6, 24)
    f.cap('court', court, z+.06, hk.STONE, FLAGS)
    ring_band('court border', court, border, z+.06, hk.STONE, FLAGS_DARK)
    for a in (90, 210, 330):
        bench(*polar(18.2, a), a-90)
    for a in (30, 150, 270):
        lamp(*polar(19.4, a))
    for a in range(0, 360, 60):
        shrub(*polar(22.9, a), z, 3.4, rng)
    flush_cards(False)


def plaza_pillars(rng):
    """A railed lawn: a pier on each corner, iron railings between them but for the two gateways, a round bed with a
    clipped cone among flowers in the middle, two benches. No tree: the board's trees are placed as trees."""
    z = square()
    corners = [polar(24.0, a) for a in range(0, 360, 60)]
    for x, y in corners:
        pier(x, y)
    for i in range(6):
        if i not in (1, 4):
            la.railings(corners[i], corners[(i+1) % 6], 1.0, 4.6, 9, 'railing')
    la.ring_wall('bed kerb', f.regular(0, 0, 6.4, 12), z, z+.7, hk.STONE, hk.DRESSING, thick=.7)
    f.cap('bed', f.regular(0, 0, 5.7, 12), z+.45, MULCH, (1, 1, 1))
    la.turned('cone', [(1.9, z+.45), (2.1, z+1.6), (0, z+7.2)], 8, LEAF, BOXWOOD)
    drift([polar(3.9, a) for a in range(0, 360, 45)], z+.45, PINK, rng)
    plant_flowers(rng)
    for a in (0, 180):
        bench(*polar(11.5, a), a-90)


def plaza_hedge(rng):
    """A hedged lawn: a clipped hedge round it, open at two gateways; inside, a planted urn and two benches."""
    z = square()
    ring = f.regular(0, 0, 21.4, 6)
    for i in range(6):
        p, q = ring[i], ring[(i+1) % 6]
        if i in (1, 4):  # A gateway in the middle of the side.
            mid = lambda t: (p[0]+(q[0]-p[0])*t, p[1]+(q[1]-p[1])*t)
            hedge(p, mid(.34), 2.6, 4.2, rng)
            hedge(mid(.66), q, 2.6, 4.2, rng)
        else:
            hedge(p, q, 2.6, 4.2, rng)
    flush_cards(True)
    la.turned('urn', [(1.9, z), (1.9, z+.5), (1.0, z+1.0), (1.0, z+2.4), (2.3, z+3.6), (2.3, z+3.9), (1.9, z+3.9)], 8, hk.STONE, hk.DRESSING)
    shrub(0, 0, z+3.4, 4.6, rng, body=False)
    for a in (0, 180):
        shrub(*polar(12.5, a+90), z, 3.0, rng)
        bench(*polar(13.0, a), a-90)
    flush_cards(False)


def plaza_pond(rng):
    """A lily pond in a lawn: a six-sided stone basin in a flagged walk, reeds in two corners, two benches."""
    z = square()
    walk, basin = f.regular(0, 0, 16.2, 6), f.regular(0, 0, 12.6, 6)
    ring_band('pond walk', basin, walk, z+.06, hk.STONE, FLAGS)
    la.pool('pond', basin, z, hk.STONE, hk.DRESSING, wall=1.2, height=1.5)
    for _ in range(9):
        a, d = rng.uniform(0, TAU), rng.uniform(1.5, 8.5)
        x, y = d*math.cos(a), d*math.sin(a)
        add('lily pad', PAINT, (.26, .42, .22), [(x+.9*math.cos(TAU*k/6+a), y+.9*math.sin(TAU*k/6+a), z+1.02) for k in range(5)]+[(x, y, z+1.02)],
            [(k, k+1, 5) for k in range(4)], detail=True)
    for a in (40, 220):
        for _ in range(4):
            x, y = polar(rng.uniform(7.5, 9.5), a+rng.uniform(-14, 14))
            u.upright(u.SPIKE, (.74, .84, .56), x, y, z+.9, 2.2, 4.4, rng.uniform(0, TAU))
            u.tilted(u.FLOWER, WHITE, x+.8, y+.5, z+1.0, 1.3, 1.3, rng.uniform(0, TAU), math.radians(78))
    flush_cards(True)
    for a in (90, 270):
        bench(*polar(19.4, a), a-90)
    for a in range(0, 360, 60):
        shrub(*polar(23.2, a), z, 3.0, rng)
    flush_cards(False)


def flower_beds(z, rng):
    """A round bed and a ring of six beds round it, in mulch, each in one colour."""
    f.cap('bed', f.regular(0, 0, 5.4, 12), z+.08, MULCH, (1, 1, 1))
    drift([(0, 0)]+[polar(3.2, a) for a in range(0, 360, 60)], z+.08, YELLOW, rng, 2.0)
    for i in range(6):
        a0, a1 = i*60+7, i*60+53
        inner = [polar(10.2, a0+(a1-a0)*t/4) for t in range(5)]
        outer = [polar(16.4, a0+(a1-a0)*t/4) for t in range(5)]
        for k in range(4):
            add('bed', MULCH, (1, 1, 1), [(*inner[k], z+.08), (*outer[k], z+.08), (*outer[k+1], z+.08), (*inner[k+1], z+.08)], [(0, 1, 2, 3)])
        spots = [polar(r, a0+(a1-a0)*t) for r in (11.8, 14.8) for t in (.14, .38, .62, .86)]
        drift(spots, z+.08, (RED, WHITE, PINK)[i % 3], rng)
    plant_flowers(rng)


def plaza_flowers(rng):
    """A flower garden: beds of colour in a lawn."""
    flower_beds(square(), rng)


def plaza_flowers_pillars(rng):
    """The flower garden behind corner piers."""
    z = square()
    for a in range(0, 360, 60):
        pier(*polar(24.0, a))
    flower_beds(z, rng)


def garden_bed(rng):
    """A garden plot: a stone edging round a lawn, a long bed of shrubs and flowers down each side."""
    half_x, half_y = 20.5, 17.5
    ring = f.rect(-half_x, half_x, -half_y, half_y)
    la.ring_wall('edging', ring, 0, .9, hk.STONE, hk.DRESSING, thick=1.0)
    f.cap('lawn', f.inset(ring, 1.0), .6, u.TURF, LAWN)
    for side in (-1, 1):
        y0, y1 = sorted((side*8.4, side*15.6))
        add('bed', MULCH, (1, 1, 1), [(-18.4, y0, .68), (18.4, y0, .68), (18.4, y1, .68), (-18.4, y1, .68)], [(0, 1, 2, 3)])
        for i, x in enumerate((-14.5, 0, 14.5)):
            shrub(x, side*13.4, .68, 4.6 if i == 1 else 3.6, rng)
        drift([(x, side*10.2) for x in (-16, -12, -8, -4, 4, 8, 12, 16)], .68, (RED, YELLOW)[side > 0], rng)
        drift([(x, side*13.6) for x in (-9.5, -5.5, 5.5, 9.5)], .68, (WHITE, VIOLET)[side > 0], rng)
    flush_cards(False)
    plant_flowers(rng)


# -- Fountain ---------------------------------------------------------------------------------------

def fountain(rng):
    """A stone fountain on a flagged apron: a round basin, a pedestal under two bowls that spill, a jet."""
    apron, edge = f.regular(0, 0, 13.0, 16), f.regular(0, 0, 18.0, 16)
    ring_band('apron', apron, edge, .12, hk.STONE, FLAGS)
    f.wall_ring('apron edge', edge, 0, .12, hk.STONE, FLAGS_DARK)
    la.pool('basin', f.regular(0, 0, 13.0, 16), 0, hk.STONE, hk.DRESSING, wall=1.3, height=2.6)
    la.turned('pedestal', [(2.6, 2.0), (2.0, 2.9), (1.4, 3.4), (1.2, 6.2), (1.9, 6.7)], 8, hk.STONE, hk.WALL)
    la.turned('bowl', [(1.9, 6.7), (5.6, 8.0), (5.6, 8.5), (5.0, 8.5)], 12, hk.STONE, hk.DRESSING)
    f.cap('bowl water', f.regular(0, 0, 5.0, 12), 8.32, la.WATER, la.STILL)
    la.turned('stem', [(1.0, 8.3), (.8, 10.6), (1.3, 11.0)], 8, hk.STONE, hk.WALL)
    la.turned('top bowl', [(1.3, 11.0), (3.0, 11.9), (3.0, 12.3), (2.6, 12.3)], 10, hk.STONE, hk.DRESSING)
    f.cap('top water', f.regular(0, 0, 2.6, 10), 12.15, la.WATER, la.STILL)
    la.turned('finial', [(.5, 12.15), (.35, 13.4), (.6, 13.7)], 6, hk.STONE, hk.WALL)
    la.turned('jet', [(.28, 13.7), (.18, 15.2), (0, 15.9)], 5, PAINT, la.FALLING, detail=True)
    for radius, z0, z1, count, half in ((5.45, 2.1, 8.1, 8, .32), (2.9, 8.3, 12.0, 4, .22)):  # Each bowl's spill, in thin streams.
        for i in range(count):
            a = TAU*(i+.5)/count
            cx, cy, tx, ty = radius*math.cos(a), radius*math.sin(a), -math.sin(a)*half, math.cos(a)*half
            verts = [(cx-tx, cy-ty, z0), (cx+tx, cy+ty, z0), (cx+tx, cy+ty, z1), (cx-tx, cy-ty, z1)]
            add('fall', PAINT, la.FALLING, verts, [(0, 1, 2, 3), (3, 2, 1, 0)], detail=count == 4)


# -- Formal gardens ---------------------------------------------------------------------------------

def parterre(outline, beds, rng, radius=32.0):
    """A formal garden: a gravel floor to its stone edging, beds edged with low box hedges and filled with flowers, a
    round pool with a jet in the middle, a clipped cone at each bed's outer corner."""
    la.ring_wall('edging', outline, 0, .8, hk.STONE, hk.DRESSING, thick=1.2)
    f.cap('gravel', f.inset(outline, 1.2), .5, GRAVEL, GRAVEL_TINT)
    la.pool('pool', f.regular(0, 0, 6.2, 12), .5, hk.STONE, hk.DRESSING, wall=1.0, height=1.6)
    la.turned('jet', [(.5, 1.6), (.4, 3.0), (.25, 3.2), (.12, 5.0), (0, 5.6)], 5, PAINT, la.FALLING, detail=True)
    for i, bed in enumerate(beds):
        centre = (sum(p[0] for p in bed)/len(bed), sum(p[1] for p in bed)/len(bed))
        f.cap('bed', bed, .58, MULCH, (1, 1, 1))
        la.ring_wall('box edging', bed, .5, 2.3, LEAF, BOXWOOD, thick=1.2)
        for x, y in bed:  # A sprig at each corner breaks the clipped line.
            u.tilted(u.BUSH, rng.choice(u.BUSH_TINTS), x+(centre[0]-x)*.08, y+(centre[1]-y)*.08, 1.5, 2.2, 1.7, rng.uniform(0, TAU), math.radians(60))
        tint = (RED, YELLOW, WHITE)[i % 3]
        inner = f.scaled(bed, .5, centre)
        drift(inner+[centre]+[((p[0]+q[0])/2, (p[1]+q[1])/2) for p, q in zip(inner, inner[1:]+inner[:1])][::2], .58, tint, rng, 2.2)
        tip = max(bed, key=lambda p: math.hypot(*p))
        tx, ty = tip[0]*.9, tip[1]*.9
        la.turned('cone', [(1.5, .5), (1.6, 1.4), (0, 5.6)], 7, LEAF, BOXWOOD, tx+(centre[0]-tx)*.25, ty+(centre[1]-ty)*.25)
    flush_cards(True)
    plant_flowers(rng)


def sector(r0, r1, a0, a1, steps):
    """A bed between two radii and two angles, anticlockwise; with `steps` its sides follow the circle."""
    inner = [polar(r0, a0+(a1-a0)*t/steps) for t in range(steps+1)]
    outer = [polar(r1, a0+(a1-a0)*t/steps) for t in range(steps+1)]
    return outer+inner[::-1]


def formal_garden_hex(rng):
    """Six straight-sided beds inside a six-sided edging."""
    parterre(f.regular(0, 0, 32, 6), [sector(11.0, 24.5, i*60+9, i*60+51, 1) for i in range(6)], rng)


def formal_garden_round(rng):
    """Six curved beds inside a round edging."""
    parterre(f.regular(0, 0, 32, 24), [sector(11.0, 26.5, i*60+8, i*60+52, 2) for i in range(6)], rng)


def formal_garden_star(rng):
    """Six kite beds that make a star inside a round edging."""
    beds = [[polar(10.5, i*60), polar(17.5, i*60-19), polar(27.5, i*60), polar(17.5, i*60+19)] for i in range(6)]
    parterre(f.regular(0, 0, 32, 24), beds, rng)


# -- Small props ------------------------------------------------------------------------------------

def grandstand(rng):
    """A bleacher along y, facing -x: four rows of aluminium seats and footboards on a steel frame, a rail behind and at each end."""
    half, rows = 14.0, 4
    for row in range(rows):
        x, z = -3.4+row*1.75, 1.3+row*1.25
        box('seat', 0, 0, 0, x, x+.95, -half, half, z, z+.18, PAINT, (.80, .82, .83), omit='')
        box('footboard', 0, 0, 0, x-.85, x, -half, half, z-1.25, z-1.13, PAINT, (.58, .60, .61), omit='b')
        # The riser under each seat closes the stand: it reads as steps, not as a frame.
        add('riser', PAINT, (.44, .46, .47), [(x, -half, z-1.13), (x, half, z-1.13), (x, half, z), (x, -half, z)], [(3, 2, 1, 0)])
    for y in (-half, half):
        add('stand side', PAINT, (.40, .42, .43), [(-4.25, y, 0), (2.7, y, 0), (2.7, y, 5.05), (-4.25, y, .05)], [(0, 1, 2, 3), (3, 2, 1, 0)])
    add('stand back', PAINT, (.40, .42, .43), [(2.7, -half, 0), (2.7, half, 0), (2.7, half, 5.05), (2.7, -half, 5.05)], [(0, 1, 2, 3)])
    for y in (-half+.4, -half/3, half/3, half-.4):
        kb.bar('stand frame', [(-3.6, y, 0), (-3.6, y, 1.3), (2.7, y, 1.3+3*1.25), (2.7, y, 0)], .14, hk.IRON, fine=False)
        kb.bar('stand frame', [(-3.6, y, 0), (2.7, y, 0)], .12, hk.IRON)
        kb.bar('stand post', [(2.9, y, 0), (2.9, y, 8.2)], .13, hk.IRON, fine=False)
    for z in (6.4, 8.2):
        kb.bar('stand rail', [(2.9, -half+.4, z), (2.9, half-.4, z)], .11, hk.IRON, fine=z < 8)
    for y in (-half+.4, half-.4):
        kb.bar('stand rail', [(-3.6, y, 1.3), (-3.6, y, 3.6), (2.9, y, 8.2)], .11, hk.IRON)


def park_bench(rng):
    bench(0, 0, 0)


def picnic_table(rng):
    """A timber picnic table along y, a bench fixed to each side on its two A-frames."""
    box('table top', 0, 0, 0, -1.25, 1.25, -3.3, 3.3, 2.25, 2.45, PAINT, TIMBER_PALE, omit='')
    for side in (-1, 1):
        x0, x1 = sorted((side*1.75, side*2.6))
        box('table seat', 0, 0, 0, x0, x1, -3.3, 3.3, 1.35, 1.5, PAINT, TIMBER_PALE, omit='')
    for y in (-2.4, 2.4):
        for side in (-1, 1):
            kb.bar('table leg', [(side*2.5, y, 0), (side*.7, y, 2.25)], .16, TIMBER, fine=False)
        kb.bar('table tie', [(-2.4, y, 1.3), (2.4, y, 1.3)], .14, TIMBER, fine=False)
    for gap in (-.42, .42):  # The planks' gaps.
        add('table gap', PAINT, (.18, .12, .08), [(gap-.03, -3.3, 2.455), (gap+.03, -3.3, 2.455), (gap+.03, 3.3, 2.455), (gap-.03, 3.3, 2.455)],
            [(0, 1, 2, 3)], detail=True)


def pillar(rng):
    """A stone column: a square plinth, a round shaft that narrows, a moulded capital under a square slab."""
    box('plinth', 0, 0, 0, -3.4, 3.4, -3.4, 3.4, 0, 1.3, hk.STONE, hk.RUSTIC)
    la.turned('base', [(3.0, 1.3), (3.0, 1.7), (2.5, 2.2)], 12, hk.STONE, hk.DRESSING)
    la.turned('shaft', [(2.3, 2.2), (2.0, 6.2), (2.5, 6.6), (2.9, 7.0)], 12, hk.STONE, hk.WALL)
    box('abacus', 0, 0, 0, -3.1, 3.1, -3.1, 3.1, 7.0, 7.7, hk.STONE, hk.DRESSING, omit='')


PROPS = {'plaza': (plaza, 'hex'), 'plaza-pillars': (plaza_pillars, 'hex'), 'plaza-hedge': (plaza_hedge, 'hex'),
         'plaza-pond': (plaza_pond, 'hex'), 'plaza-flowers': (plaza_flowers, 'hex'), 'plaza-flowers-pillars': (plaza_flowers_pillars, 'hex'),
         'garden-bed': (garden_bed, 'hex'), 'fountain': (fountain, 'hex'), 'formal-garden-hex': (formal_garden_hex, 'hex'),
         'formal-garden-round': (formal_garden_round, 'hex'), 'formal-garden-star': (formal_garden_star, 'hex'),
         'grandstand': (grandstand, 'small'), 'bench': (park_bench, 'small'), 'picnic-table': (picnic_table, 'small'),
         'pillar': (pillar, 'small')}


def build(name):
    """Writes one prop in its two levels."""
    builder, size = PROPS[name]
    kb.build_scene(name, lambda: builder(random.Random(sum(map(ord, 'parks'+name)))), lambda obj: None, lambda obj: False)
    levels = {i: shared.export_model(shared.objects, f'{name}-lod{i}', level=i, exact=True) for i in (0, 1)}
    for level in levels.values():
        for material in level['materials']:
            for texture in material.get('textures', ()):
                # The exporter names textures from a building's folder; a prop's lies two under models/board.
                texture['filename'] = texture['filename'].replace('../../board/textures/', '../../textures/')
    triangles = [sum(len(part['indices'])//3 for mesh in level['meshes'] for part in mesh['parts']) for level in levels.values()]
    assert triangles[0] <= LIMITS[size], (name, triangles)
    out = Path(sys.argv[sys.argv.index('--out')+1]) if '--out' in sys.argv else PARKS
    out.mkdir(parents=True, exist_ok=True)
    write_glb(out/(name+'.glb'), levels=levels)
    print('RESULT', name, 'triangles', *triangles)


if __name__ == '__main__' and '--' in sys.argv:
    wanted = [arg for arg in sys.argv[sys.argv.index('--')+1:] if arg in PROPS]
    for name in PROPS:
        if not wanted or name in wanted:
            build(name)
