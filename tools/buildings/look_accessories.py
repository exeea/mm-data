"""The looks' accessories: small props in each look's own finishes, to dress a district between its buildings. Pure
decoration: a placed prop is no building and blocks nothing; its lamps glow but light no ground.

Run: blender -b --factory-startup --python look_accessories.py -- [look[/name] ...]   (none: all)
Writes data/models/board/scenery/<look>/<name>.glb, two levels of detail (the far one without the fine parts), front
to -y, standing on the ground about its origin. A hex is 83 across and a level 18 tall: 3 units to the metre.
Each look's props are listed in the editor under its buildings (blueprint.json, section buildings/<look>-accessories);
a new prop takes its id from tools/move_model.py --stamp.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import authored_examples as shared
import civic_blocks as c
import civic_habitat as h
import frontier_buildings as f
import heritage_buildings as hb
import heritage_kit as hk
import imperial_buildings as ib
import imperial_kit as ik
import kit_blocks as kb
import theme_kits as k
import utopia_buildings as u
from civic_habitat import CAST, PAINT, PALE_GLASS, PANELS, SLATS, STEEL, add, cuboid, deck, disc, round_prism
from glb_geometry import write_glb
from kit_blocks import facing

SCENERY = k.DATA/'models/board/scenery'
WATER = 'scenery/pool-water'
STILL, POND = (.50, .62, .62), (.30, .40, .34)  # Its tints: a basin's water, a garden pond's (untinted, a swimming pool's blue).
FALLING = (.80, .88, .90)  # Falling water, on paint: glass would draw it dark.
CONCRETE, CONCRETE_DARK = (.86, .86, .83), (.56, .56, .54)
AMBER = (.95, .80, .50)
MAX_TRIANGLES = 1600


def ring_wall(name, ring, z0, z1, key, colour, thick=None, **flags):
    """Upright faces round a ring; with `thick`, a wall that thick: its inner faces and its top too."""
    f.wall_ring(name, ring, z0, z1, key, colour, **flags)
    if thick:
        inner = f.inset(ring, thick)
        for i in range(len(inner)):
            j = (i+1) % len(inner)
            facing(name, key, colour, [(*inner[i], z0), (*inner[j], z0), (*inner[j], z1), (*inner[i], z1)], (*f.outward(inner[j], inner[i]), 0))
        f.frustum(name, ring, z1, inner, z1, key, colour)


def pool(name, ring, z, key, colour, wall=1.0, height=1.6):
    """A basin: a kerb round still water."""
    ring_wall(name+' kerb', ring, z, z+height, key, colour, thick=wall)
    f.cap(name+' water', f.inset(ring, wall), z+height-.5, WATER, STILL)


def turned(name, profile, sides, key, colour, x=0.0, y=0.0, start=0.0, **flags):
    """A shape turned about an upright axis through (x, y): faces between the (radius, height) points of `profile`, a
    point where it ends at radius 0, a flat top where it does not."""
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        low = f.regular(x, y, r0, sides, start)
        if r1 <= 0:
            for i in range(sides):
                add(name, key, colour, [(*low[i], z0), (*low[(i+1) % sides], z0), (x, y, z1)], [(0, 1, 2)], **flags)
        else:
            f.frustum(name, low, z0, f.regular(x, y, r1, sides, start), z1, key, colour, **flags)
    if profile[-1][0] > 0:
        f.cap(name, f.regular(x, y, profile[-1][0], sides, start), profile[-1][1], key, colour, **flags)


def rock(x, y, size, rng, colour=(.50, .49, .47)):
    """A garden rock: a squat faceted lump of granite, no two alike."""
    low = [(x+size*rng.uniform(.8, 1.15)*math.cos(a), y+size*rng.uniform(.7, 1.05)*math.sin(a)) for a in (math.tau*i/8 for i in range(8))]
    mid = f.scaled(low, rng.uniform(.8, .9), (x+rng.uniform(-.15, .15)*size, y))
    high = f.scaled(low, rng.uniform(.35, .5), (x+rng.uniform(-.25, .25)*size, y+rng.uniform(-.2, .2)*size))
    tall = size*rng.uniform(.7, 1.0)
    f.frustum('rock', low, 0, mid, tall*.6, CAST, colour)
    f.frustum('rock', mid, tall*.6, high, tall, CAST, tuple(v*1.06 for v in colour))
    f.cap('rock', high, tall, CAST, tuple(v*1.12 for v in colour))


def mound(name, x, y, z, radius, height, colour, sides=7, key=PAINT, rng=None):
    """A low faceted mound: moss, a clump of flowers, a clipped shrub."""
    spin = rng.uniform(0, 360) if rng else 0
    turned(name, [(radius, z), (radius*.8, z+height*.6), (radius*.4, z+height), (0, z+height*1.05)], sides, key, colour, x, y, spin)


def lens(name, x0, x1, y0, y1, z0, z1, colour=AMBER, glow='night', **flags):
    """A lamp's lit body, seen from every side."""
    cuboid(name, x0, x1, y0, y1, z0, z1, PAINT, colour, light=glow, **flags)


# -- Imperial ---------------------------------------------------------------------------------------

def torii_gate(rng):
    """A lacquer gate: two round posts on granite feet leaning a little inwards, a tie beam through them, a lintel
    under a charcoal cap that sweeps up to its ends."""
    half, top = 9.0, 17.0
    for side in (-1, 1):
        cuboid('gate foot', side*(half+.5)-1.7, side*(half+.5)+1.7, -1.7, 1.7, 0, 1.6, CAST, ik.GRANITE, omit='b')
        u.tube('gate post', [(side*(half+.5), 0, 1.6), (side*(half-.3), 0, top)], 1.05, PAINT, ik.LACQUER, sides=8)
        cuboid('gate wedge', side*half-1.5, side*half+1.5, -.5, .5, 12.6, 13.2, PAINT, ik.DARK, omit='b', detail=True)
    cuboid('gate tie', -half-2.2, half+2.2, -.45, .45, 13.2, 14.6, PAINT, ik.LACQUER)
    cuboid('gate strut', -.5, .5, -.4, .4, 14.6, top, PAINT, ik.LACQUER, omit='bt')
    xs = [-half-5.0, -half-2.0, -4.0, 4.0, half+2.0, half+5.0]
    ups = [1.5, .5, 0, 0, .5, 1.5]
    for part, wide, z0, z1, colour in (('gate lintel', .7, top, top+1.4, ik.LACQUER), ('gate cap', 1.2, top+1.4, top+2.3, ib.RIB)):
        for (x0, a), (x1, b) in zip(zip(xs, ups), zip(xs[1:], ups[1:])):
            trim = .8 if part == 'gate lintel' else 0  # The lintel stops short of the cap's ends.
            x0, x1 = max(x0, xs[0]+trim), min(x1, xs[-1]-trim)
            verts = [(x0, -wide, z0+a), (x1, -wide, z0+b), (x1, wide, z0+b), (x0, wide, z0+a), (x0, -wide, z1+a), (x1, -wide, z1+b), (x1, wide, z1+b),
                     (x0, wide, z1+a)]
            ends = ([(3, 0, 4, 7)] if x0 <= xs[0]+trim else [])+([(1, 2, 6, 5)] if x1 >= xs[-1]-trim else [])
            add(part, PAINT, colour, verts, [(4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 2, 1, 0)]+ends)


def stone_lantern(rng):
    """A stone lantern: a stepped foot, a shaft, a platform, a fire box of four posts round lit paper panes, a wide
    flared cap and a knob."""
    stone, pale = ik.COURSE_TONE, (1, 1, 1)
    turned('lantern foot', [(2.6, 0), (2.6, .9), (1.9, .9), (1.9, 1.7), (.9, 1.7)], 6, ik.STONE, stone)
    turned('lantern shaft', [(.9, 1.7), (.75, 5.4), (2.3, 6.0), (2.3, 6.6)], 6, ik.STONE, stone)
    for x in (-1.25, 1.25):
        for y in (-1.25, 1.25):
            cuboid('lantern post', x-.3, x+.3, y-.3, y+.3, 6.6, 9.2, ik.STONE, pale, omit='bt')
    lens('lantern light', -1.05, 1.05, -1.05, 1.05, 6.6, 9.2, (.90, .78, .56), omit='bt')
    turned('lantern cap', [(1.7, 9.2), (3.4, 9.5), (3.4, 9.9), (1.2, 11.2), (.5, 11.4)], 6, CAST, ik.GRANITE)
    turned('lantern knob', [(.5, 11.4), (.75, 11.9), (0, 12.8)], 6, CAST, ik.GRANITE)


def roofed_gate(rng):
    ib.gate(-9, 9, 0)


def rock_garden(rng):
    """A dry garden: gravel raked in rings round three rocks on mounded moss, straight between them, in a stone kerb;
    clipped boxwood at a corner."""
    ring = f.rect(-17, 17, -11, 11)
    ring_wall('garden kerb', ring, 0, .9, ik.STONE, ik.COURSE_TONE, thick=1.0)
    f.cap('garden gravel', f.inset(ring, 1.0), .6, CAST, (.80, .78, .72))
    rocks = ((-8, 2, 3.2), (-1.5, -3.5, 1.9), (8, -1, 2.5))
    for i in range(9):  # The rake's straight lines, broken where the rings lie.
        y = -8.4+2.1*i
        edges = sorted([-15.0, 15.0]+[x+way*math.sqrt(max(0.0, (size*2.6)**2-(y-ry)**2)) for x, ry, size in rocks if abs(y-ry) < size*2.6
                                      for way in (-1, 1)])
        for x0, x1 in zip(edges[::2], edges[1::2]):
            deck('garden rake', x0, x1, y-.12, y+.12, .63, PAINT, (.62, .60, .55), detail=True)
    for x, y, size in rocks:
        for radius in (size*1.9, size*2.4):  # The rake's rings.
            outer, inner = f.regular(x, y, radius, 12), f.regular(x, y, radius-.24, 12)
            f.frustum('garden rake', outer, .64, inner, .64, PAINT, (.62, .60, .55))
        moss = [(x+size*rng.uniform(1.2, 1.6)*math.cos(a), y+size*rng.uniform(1.0, 1.5)*math.sin(a)) for a in (math.tau*i/9 for i in range(9))]
        f.frustum('garden moss', moss, .62, f.scaled(moss, .5, (x, y)), 1.0, PAINT, (.27, .33, .20))
        f.cap('garden moss', f.scaled(moss, .5, (x, y)), 1.0, PAINT, (.30, .36, .22))
        rock(x, y, size, rng)
    for dx, dy, size in ((0, 0, 4.2), (3.2, 1.0, 3.2)):
        ib.boxwood(11+dx, 6+dy, .5, size, rng)


def footbridge(rng):
    """An arched lacquer footbridge with bronze-capped posts."""
    half, wide, rise, steps = 14.0, 4.0, 4.6, 8
    xs = [-half+2*half*i/steps for i in range(steps+1)]
    zs = [rise*(1-(x/half)**2)+.4 for x in xs]
    for (x0, z0), (x1, z1) in zip(zip(xs, zs), zip(xs[1:], zs[1:])):
        verts = [(x0, -wide, z0), (x1, -wide, z1), (x1, wide, z1), (x0, wide, z0)]
        add('bridge deck', PAINT, (.42, .30, .22), verts, [(0, 1, 2, 3)])
        add('bridge soffit', PAINT, ik.SOFFIT, [(x, y, z-.6) for x, y, z in verts], [(3, 2, 1, 0)])
        for side in (-1, 1):
            y = side*wide
            verts = [(x0, y, z0-.6), (x1, y, z1-.6), (x1, y, z1+.1), (x0, y, z0+.1)]
            facing('bridge beam', PAINT, ik.LACQUER, verts, (0, side, 0))
            kb.bar('bridge rail', [(x0, y, z0+3.0), (x1, y, z1+3.0)], .22, ik.LACQUER, fine=False)
    for x, z in list(zip(xs, zs))[::2]:
        for side in (-1, 1):
            cuboid('bridge post', x-.3, x+.3, side*wide-.3, side*wide+.3, z-.6, z+3.4, PAINT, ik.LACQUER, omit='b')
            cuboid('bridge post cap', x-.4, x+.4, side*wide-.4, side*wide+.4, z+3.4, z+3.8, PAINT, ik.BRONZE, omit='b', detail=True)
    for side in (-1, 1):
        cuboid('bridge foot', side*half-1.2, side*half+1.2, -wide-.6, wide+.6, 0, .9, ik.STONE, ik.COURSE_TONE, omit='b')


def tea_pavilion(rng):
    """An open pavilion: four lacquer posts on a stone floor under a hipped seamed roof with upturned corners."""
    cuboid('pavilion floor', -9, 9, -9, 9, 0, 1.0, ik.STONE, ik.COURSE_TONE, omit='b')
    for x in (-7, 7):
        for y in (-7, 7):
            ib.post(x, y, 1.0, 12.0, half=.7, foot=1.6)
    for a0, a1, b0, b1 in ((-7.6, 7.6, -7.5, -6.5), (-7.6, 7.6, 6.5, 7.5), (-7.5, -6.5, -6.5, 6.5), (6.5, 7.5, -6.5, 6.5)):
        cuboid('pavilion beam', a0, a1, b0, b1, 10.6, 12.0, PAINT, ik.LACQUER)
    ib.hip('pavilion roof', f.rect(-11, 11, -11, 11), 12.2, pitch=.5, flare=(3.0, .25), lift=1.6, soffit=.6, fins=False)
    cuboid('pavilion bench', -5, 5, 5.0, 6.4, 1.0, 2.5, PAINT, (.42, .30, .22), omit='b')


def koi_pond(rng):
    """A garden pond: still water in a rim of rocks, stepping stones across it, moss and a lantern-sized rock at its
    side: what the footbridge crosses."""
    shore = [(15*rng.uniform(.82, 1.0)*math.cos(a), 10*rng.uniform(.8, 1.0)*math.sin(a)) for a in (math.tau*i/14 for i in range(14))]
    f.frustum('pond bank', f.scaled(shore, 1.12), 0, shore, .5, PAINT, (.27, .33, .20))
    f.cap('pond water', shore, .45, WATER, POND)
    for i in range(0, 14, 2):
        x, y = shore[i]
        rock(x*1.04, y*1.04, rng.uniform(1.2, 2.2), rng)
    for x, y in ((-7, -2.5), (-3.2, -.6), (.8, .4), (4.6, -.4), (8.0, 1.6)):
        turned('pond stone', [(1.5, .3), (1.5, .62), (1.2, .7)], 7, CAST, (.62, .61, .58), x, y, rng.uniform(0, 50))
    for x, y in ((-3, 5), (5, -5.5)):  # Lily pads.
        disc('pond lily', x, y, .34, 1.1, 'z', PAINT, (.24, .38, .20), 7, detail=True)


IMPERIAL = {'torii-gate': torii_gate, 'stone-lantern': stone_lantern, 'roofed-gate': roofed_gate, 'rock-garden': rock_garden,
            'footbridge': footbridge, 'tea-pavilion': tea_pavilion, 'koi-pond': koi_pond}


# -- Heritage ---------------------------------------------------------------------------------------

LAMP_GLASS = (.66, .62, .50)  # A lantern's pane by day: unlit.


def lantern(x, y, z, half=.6, tall=1.8):
    """An iron lantern: lit panes under a pointed cap."""
    lens('lamp', x-half, x+half, y-half, y+half, z, z+tall, LAMP_GLASS, omit='b')
    turned('lamp cap', [(half*1.5, z+tall), (0, z+tall+.9)], 4, PAINT, hk.IRON, x, y, 45)


def fountain(rng):
    """A stone fountain: an octagonal basin of water, a pedestal carrying a bowl that spills in four sheets, a jet."""
    pool('fountain', f.regular(0, 0, 9.0, 8, 22.5), 0, hk.STONE, hk.DRESSING, wall=1.1, height=2.4)
    turned('fountain pedestal', [(1.6, 1.9), (1.2, 2.6), (1.0, 5.0), (1.5, 5.4)], 8, hk.STONE, hk.WALL, start=22.5)
    turned('fountain bowl', [(1.5, 5.4), (4.2, 6.6), (4.2, 7.1), (3.7, 7.1)], 8, hk.STONE, hk.DRESSING, start=22.5)
    f.cap('fountain bowl water', f.regular(0, 0, 3.7, 8, 22.5), 6.95, WATER, STILL)
    turned('fountain spout', [(.5, 6.95), (.4, 8.6), (.7, 8.9)], 6, hk.STONE, hk.WALL)
    turned('fountain jet', [(.3, 8.9), (.2, 10.2), (0, 10.8)], 5, PAINT, FALLING)
    for i in range(4):  # The bowl's spill: a thin sheet from under four of its lips, down to the basin.
        a = math.radians(45+90*i)
        cx, cy, tx, ty = 3.8*math.cos(a), 3.8*math.sin(a), -math.sin(a)*.8, math.cos(a)*.8
        verts = [(cx-tx, cy-ty, 1.9), (cx+tx, cy+ty, 1.9), (cx+tx, cy+ty, 6.4), (cx-tx, cy-ty, 6.4)]
        add('fountain fall', PAINT, FALLING, verts, [(0, 1, 2, 3), (3, 2, 1, 0)])


def street_lamp(rng):
    """An iron lamp post with two lanterns on a scrolled cross arm."""
    turned('lamp foot', [(1.1, 0), (.9, 1.2), (.45, 1.8)], 6, PAINT, hk.IRON)
    turned('lamp post', [(.38, 1.8), (.28, 12.2), (.5, 12.6), (.3, 13.4), (0, 14.6)], 6, PAINT, hk.IRON)
    cuboid('lamp arm', -3.0, 3.0, -.16, .16, 11.6, 12.0, PAINT, hk.IRON)
    for x in (-2.8, 2.8):
        kb.bar('lamp scroll', [(x*.3, 0, 10.4), (x, 0, 11.6)], .12, hk.IRON)
        lantern(x, 0, 12.0)


def park_bench(rng):
    """An iron bench with timber slats."""
    for x in (-3.2, 3.2):
        cuboid('bench end', x-.18, x+.18, -1.0, 1.0, 0, 1.5, PAINT, hk.IRON, omit='b')
        cuboid('bench end', x-.18, x+.18, .7, 1.0, 1.5, 3.3, PAINT, hk.IRON, omit='b')
        cuboid('bench arm', x-.22, x+.22, -1.0, .8, 2.3, 2.5, PAINT, hk.IRON)
    for y0, y1 in ((-1.0, -.5), (-.4, .1), (.2, .7)):
        cuboid('bench slat', -3.4, 3.4, y0, y1, 1.5, 1.7, PAINT, hk.TIMBER)
    for z0, z1 in ((2.1, 2.55), (2.75, 3.2)):
        cuboid('bench slat', -3.4, 3.4, .8, .98, z0, z1, PAINT, hk.TIMBER)


def stone_pier(x, y, tall, half=1.2):
    """A stone pier on a darker foot under a pointed cap."""
    cuboid('pier', x-half, x+half, y-half, y+half, 0, tall, hk.STONE, hk.WALL, omit='b')
    cuboid('pier foot', x-half-.3, x+half+.3, y-half-.3, y+half+.3, 0, 1.4, hk.STONE, hk.RUSTIC, omit='b')
    cuboid('pier cap', x-half-.3, x+half+.3, y-half-.3, y+half+.3, tall, tall+.6, hk.STONE, hk.DRESSING)
    turned('pier cap', [(half*1.3, tall+.6), (0, tall+1.8)], 4, hk.STONE, hk.DRESSING, x, y, 45)


def railings(p, q, z0, z1, count, name='fence'):
    """Iron railings from p to q: two rails, upright bars with spear heads over the top rail."""
    (px, py), (qx, qy) = p, q
    for z in (z0+.5, z1-.6):
        kb.bar(name+' rail', [(px, py, z), (qx, qy, z)], .16, hk.IRON, fine=False)
    for i in range(count):
        t = (i+.5)/count
        x, y = px+(qx-px)*t, py+(qy-py)*t
        kb.bar(name+' bar', [(x, y, z0), (x, y, z1+.5)], .11, hk.IRON, fine=i % 2 == 1)


def iron_fence(rng):
    """A run of iron railings on a stone plinth, a stone pier at its left end: runs set end to end share a pier."""
    stone_pier(-12, 0, 7.0)
    cuboid('fence plinth', -10.8, 12, -.5, .5, 0, 1.2, hk.STONE, hk.RUSTIC, omit='b')
    railings((-10.8, 0), (12, 0), 1.2, 6.4, 14)


def gateway(rng):
    """A stone gateway: two tall piers under lanterns, iron gates standing open."""
    for side in (-1, 1):
        x = side*7.5
        stone_pier(x, 0, 11.0, half=1.6)
        lantern(x, 0, 12.8)
        hinge = side*5.2
        railings((hinge, -.3), (hinge, -5.9), .6, 8.6, 7, 'gate leaf')
        kb.bar('gate leaf frame', [(hinge, -.3, .6), (hinge, -.3, 9.4), (hinge, -5.9, 8.2), (hinge, -5.9, .6)], .16, hk.IRON, fine=False)


def bandstand(rng):
    """A bandstand: an octagonal stone plinth with steps, eight iron posts and a rail, a low copper roof to a finial,
    lanterns on its posts."""
    floor, eave = f.regular(0, 0, 10.0, 8, 22.5), f.regular(0, 0, 11.6, 8, 22.5)
    f.wall_ring('bandstand plinth', f.inset(floor, -.6), 0, 2.4, hk.STONE, hk.RUSTIC)
    f.cap('bandstand floor', f.inset(floor, -.6), 2.4, hk.STONE, hk.DRESSING)
    ring = f.inset(floor, .8)
    for x, y in ring:
        round_prism('bandstand post', x, y, 2.4, 12.0, .28, PAINT, hk.IRON, 6)
    for i in range(8):
        if i != 5:  # Open at its front, over the steps.
            (ax, ay), (bx, by) = ring[i], ring[(i+1) % 8]
            kb.bar('bandstand rail', [(ax, ay, 5.2), (bx, by, 5.2)], .18, hk.IRON, fine=False)
            kb.bar('bandstand rail', [(ax, ay, 3.6), (bx, by, 3.6)], .12, hk.IRON)
    f.wall_ring('bandstand fascia', eave, 11.6, 12.4, PAINT, hk.IRON)
    for i in range(8):
        facing('bandstand soffit', PAINT, hk.SOFFIT, [(*eave[i], 11.6), (*eave[(i+1) % 8], 11.6), (0, 0, 11.6)], (0, 0, -1))
    turned('bandstand roof', [(11.6, 12.4), (5.0, 15.6), (0, 17.6)], 8, hk.COPPER, (1, 1, 1), start=22.5)
    hb.finial('bandstand', 0, 0, 17.6, 2.6)
    for x, y in ring[::2]:  # A lantern on every second post, outside the rail.
        lantern(x*1.07, y*1.07, 6.0, half=.5, tall=1.4)
    kb.steps(-3.2, 3.2, -13.4, -9.6, 2.4, 4, stone=(hk.STONE, hk.DRESSING))


def obelisk(rng):
    """A memorial: a stone obelisk on a stepped plinth, unmarked."""
    for half, z0, z1 in ((5.0, 0, 1.0), (3.8, 1.0, 2.0), (2.6, 2.0, 5.0)):
        cuboid('obelisk plinth', -half, half, -half, half, z0, z1, hk.STONE, hk.DRESSING if z1 < 5 else hk.WALL, omit='b')
    cuboid('obelisk plinth cap', -3.0, 3.0, -3.0, 3.0, 5.0, 5.6, hk.STONE, hk.DRESSING)
    turned('obelisk', [(2.7, 5.6), (1.7, 22.0), (0, 24.2)], 4, hk.STONE, hk.WALL, start=45)


def balustrade(rng):
    """A stone balustrade: turned balusters between a plinth and a rail, a pier carrying an urn at its left end."""
    cuboid('balustrade pier', -12, -9.6, -1.2, 1.2, 0, 5.0, hk.STONE, hk.WALL, omit='b')
    cuboid('balustrade pier cap', -12.3, -9.3, -1.5, 1.5, 5.0, 5.5, hk.STONE, hk.DRESSING)
    turned('balustrade urn', [(.5, 5.5), (.4, 6.0), (1.1, 6.9), (1.2, 7.6), (.8, 8.0), (.95, 8.3)], 8, hk.STONE, hk.DRESSING, -10.8, 0)
    mound('balustrade urn planting', -10.8, 0, 8.2, .9, 1.1, (.30, .42, .22), rng=rng)
    cuboid('balustrade plinth', -9.6, 12, -.9, .9, 0, .9, hk.STONE, hk.RUSTIC, omit='b')
    cuboid('balustrade rail', -9.6, 12, -1.0, 1.0, 4.0, 4.7, hk.STONE, hk.DRESSING)
    for i in range(11):
        x = -8.7+2.0*i
        turned('baluster', [(.38, .9), (.6, 1.7), (.3, 2.6), (.42, 4.0)], 5, hk.STONE, hk.WALL, x, 0)


HERITAGE = {'fountain': fountain, 'street-lamp': street_lamp, 'park-bench': park_bench, 'iron-fence': iron_fence, 'gateway': gateway,
            'bandstand': bandstand, 'obelisk': obelisk, 'balustrade': balustrade}


# -- Civic ------------------------------------------------------------------------------------------

def bus_shelter(rng):
    """A concrete shelter: a slab roof on three fins, glazed bays at its back that glow at night, a bench with a back,
    a lit amber fascia."""
    for x in (-8.4, -.4, 7.6):
        cuboid('shelter fin', x, x+.8, -.6, 3.0, 0, 8.4, CAST, CONCRETE, omit='b')
    cuboid('shelter roof', -9.4, 9.4, -3.6, 3.6, 8.4, 9.3, CAST, CONCRETE)
    for x0, x1 in ((-7.6, -.4), (.4, 7.6)):
        add('shelter glass', PALE_GLASS, c.TEAL_GLASS, [(x0, 2.8, 1.4), (x1, 2.8, 1.4), (x1, 2.8, 8.0), (x0, 2.8, 8.0)], [(0, 1, 2, 3), (3, 2, 1, 0)], light='night')
        cuboid('shelter glass frame', x0, x1, 2.7, 2.95, 1.1, 1.4, STEEL, (.5, .52, .52))
        cuboid('shelter bench', x0+.6, x1-.6, 1.0, 2.3, 1.3, 1.7, CAST, CONCRETE_DARK)
        cuboid('shelter bench back', x0+.6, x1-.6, 2.3, 2.6, 1.7, 3.2, CAST, CONCRETE_DARK, omit='b')
    lens('shelter light', -9.0, 9.0, -3.66, -3.6, 8.5, 9.1, omit='k')
    lens('shelter sign', 8.4, 8.6, -.4, 2.0, 5.0, 8.0, (.30, .44, .44), (.02, .10, .09))


def concrete_planter(rng):
    """A long concrete planter of clipped shrubs."""
    kb.planter(-7, 7, -2.2, 2.2, 0, rng, stone=(CAST, CONCRETE), height=2.8, size=3.6)


def bollards(rng):
    """A row of five concrete bollards, a lit ring round each head."""
    for i in range(5):
        x = -8+4*i
        round_prism('bollard', x, 0, 0, 2.6, .7, CAST, CONCRETE, 8)
        round_prism('bollard light', x, 0, 2.6, 2.9, .72, PAINT, AMBER, 8, light='night')
        round_prism('bollard head', x, 0, 2.9, 3.3, .7, CAST, CONCRETE_DARK, 8)


def mast_light(rng):
    """A street light: a tapered steel mast on a concrete foot, an arm, a head whose lens hangs lit below it."""
    cuboid('light foot', -1.1, 1.1, -1.1, 1.1, 0, 1.4, CAST, CONCRETE_DARK, omit='b')
    turned('light mast', [(.8, 1.4), (.4, 18.0)], 6, STEEL, (.62, .64, .65))
    cuboid('light arm', -.25, .25, -5.0, .25, 17.5, 18.0, STEEL, (.62, .64, .65))
    cuboid('light head', -1.0, 1.0, -6.6, -3.6, 17.3, 17.8, PAINT, (.30, .31, .32))
    lens('light lens', -.8, .8, -6.4, -3.8, 16.9, 17.3, (.90, .86, .74), omit='t')


def kiosk(rng):
    """A concrete kiosk: a serving hatch under a roller shutter, a deep canopy with a lit fascia, a door at its side, a
    louvre at its back, a blank sign band."""
    cuboid('kiosk', -5.0, 5.0, -3.6, 3.6, 0, 9.0, PANELS, CONCRETE, omit='b')
    cuboid('kiosk canopy', -6.0, 6.0, -6.6, -3.6, 8.2, 9.0, CAST, CONCRETE)
    add('kiosk hatch', PAINT, ik.WARM_ROOM, [(-3.8, -3.64, 3.2), (3.8, -3.64, 3.2), (3.8, -3.64, 6.4), (-3.8, -3.64, 6.4)], [(0, 1, 2, 3)], light=ik.SHOP_GLOW)
    add('kiosk shutter', SLATS, c.SHUTTER, [(-3.8, -3.66, 6.4), (3.8, -3.66, 6.4), (3.8, -3.66, 7.8), (-3.8, -3.66, 7.8)], [(0, 1, 2, 3)])
    cuboid('kiosk counter', -4.2, 4.2, -4.4, -3.6, 2.8, 3.2, CAST, CONCRETE_DARK)
    lens('kiosk light', -5.6, 5.6, -6.66, -6.6, 8.3, 8.9, omit='k')
    add('kiosk door', PAINT, (.30, .33, .34), [(5.04, -1.6, 0), (5.04, 1.2, 0), (5.04, 1.2, 6.6), (5.04, -1.6, 6.6)], [(0, 1, 2, 3)])
    add('kiosk louvre', SLATS, h.LOUVRE, [(3.0, 3.64, 5.0), (-3.0, 3.64, 5.0), (-3.0, 3.64, 7.6), (3.0, 3.64, 7.6)], [(0, 1, 2, 3)])
    cuboid('kiosk sign', -5.0, 5.0, -3.9, -3.5, 9.0, 10.4, PAINT, (.30, .44, .44), omit='b', light=(.02, .10, .09))


def plaza_bench(rng):
    """A concrete bench: a seat cantilevered from a board-marked wall, a strip of light under it."""
    cuboid('bench wall', -5.0, 5.0, .6, 1.4, 0, 3.6, PANELS, CONCRETE, omit='b')
    cuboid('bench seat', -5.0, 5.0, -1.6, .6, 1.3, 1.9, CAST, CONCRETE)
    lens('bench light', -4.6, 4.6, -1.6, -1.4, 1.0, 1.3, omit='t')


def monolith(rng):
    """A plaza's monolith: two leaning slabs of cast concrete on a low plinth, amber lights at their feet."""
    cuboid('monolith plinth', -4.6, 4.6, -3.4, 3.4, 0, .8, CAST, CONCRETE_DARK, omit='b')
    for x0, x1, lean, tall, colour in ((-3.4, -.6, 1.0, 17.0, CONCRETE), (.6, 3.4, -1.4, 13.0, tuple(v*.92 for v in CONCRETE))):
        low = f.rect(x0, x1, -2.2, 2.2)
        high = [(x+lean, y*.8) for x, y in low]
        f.frustum('monolith', low, .8, high, tall, PANELS, colour)
        f.cap('monolith', high, tall, CAST, colour)
    for x in (-4.0, 0.0, 4.0):
        lens('monolith light', x-.35, x+.35, -3.0, -2.5, .8, 1.3)


CIVIC = {'bus-shelter': bus_shelter, 'planter': concrete_planter, 'bollards': bollards, 'street-light': mast_light, 'kiosk': kiosk,
         'bench': plaza_bench, 'monolith': monolith}


# -- Utopia -----------------------------------------------------------------------------------------

WHITE, SHADE = k.STONE_TINT, k.STONE_SHADE
FLOWERS = ((.72, .50, .55), (.80, .72, .46), (.86, .85, .80), (.58, .50, .68))


def arc_points(radius, a0, a1, steps, cy=0.0):
    return [(radius*math.cos(math.radians(a0+(a1-a0)*i/steps)), cy+radius*math.sin(math.radians(a0+(a1-a0)*i/steps))) for i in range(steps+1)]


def arc_band(name, inner, outer, a0, a1, z0, z1, key, colour, steps=8, cy=0.0, **flags):
    """A curved slab between two radii from angle a0 to a1: its top, its two faces and its ends."""
    ins, outs = arc_points(inner, a0, a1, steps, cy), arc_points(outer, a0, a1, steps, cy)
    for i in range(steps):
        facing(name, key, colour, [(*ins[i], z1), (*ins[i+1], z1), (*outs[i+1], z1), (*outs[i], z1)], (0, 0, 1), **flags)
        mx, my = (outs[i][0]+outs[i+1][0])/2, (outs[i][1]+outs[i+1][1])/2-cy
        facing(name, key, colour, [(*outs[i], z0), (*outs[i+1], z0), (*outs[i+1], z1), (*outs[i], z1)], (mx, my, 0), **flags)
        facing(name, key, colour, [(*ins[i], z0), (*ins[i+1], z0), (*ins[i+1], z1), (*ins[i], z1)], (-mx, -my, 0), **flags)
    for end, way in ((0, -1), (steps, 1)):
        a = math.radians(a0 if end == 0 else a1)
        facing(name, key, colour, [(*ins[end], z0), (*outs[end], z0), (*outs[end], z1), (*ins[end], z1)], (-way*math.sin(a), way*math.cos(a), 0), **flags)


def garden_pavilion(rng):
    """A round garden pavilion: a white floor, a ring of slim columns under a shallow dome, curved screens of warm
    glass in three of its bays."""
    turned('pavilion floor', [(10.4, 0), (10.4, .8), (9.6, .8)], 16, u.STONE, WHITE)
    f.cap('pavilion floor', f.regular(0, 0, 9.6, 16), .8, u.STONE, SHADE)
    for i in range(8):
        a = math.radians(22.5+45*i)
        round_prism('pavilion column', 8.4*math.cos(a), 8.4*math.sin(a), .8, 10.0, .42, u.STONE, WHITE, 6)
    turned('pavilion roof', [(10.6, 10.0), (10.6, 10.8), (7.6, 12.6), (3.6, 13.6), (0, 13.9)], 16, u.STONE, WHITE)
    for i in range(16):
        ring = f.regular(0, 0, 10.6, 16)
        facing('pavilion soffit', PAINT, (.70, .70, .68), [(*ring[i], 10.0), (*ring[(i+1) % 16], 10.0), (0, 0, 10.0)], (0, 0, -1))
    for bay in (0, 3, 5):  # Screens in three bays round the ring: one faces every view.
        glass = arc_points(8.4, 22.5+45*bay, 67.5+45*bay, 3)
        for (ax, ay), (bx, by) in zip(glass, glass[1:]):
            add('pavilion glass', PAINT, (.70, .64, .52), [(ax, ay, .8), (bx, by, .8), (bx, by, 10.0), (ax, ay, 10.0)], [(0, 1, 2, 3), (3, 2, 1, 0)],
                light='night')
    arc_band('pavilion bench', 6.2, 7.6, 40, 140, .8, 2.3, u.STONE, WHITE, steps=6)


def pergola(rng):
    """A white pergola: six slim posts, two beams and slats over a walk."""
    for x in (-8, 0, 8):
        for y in (-3.6, 3.6):
            cuboid('pergola post', x-.35, x+.35, y-.35, y+.35, 0, 9.0, u.STONE, WHITE, omit='b')
    for y in (-3.6, 3.6):
        cuboid('pergola beam', -9.4, 9.4, y-.3, y+.3, 9.0, 9.7, u.STONE, WHITE)
    for i in range(10):
        x = -9+2*i
        cuboid('pergola slat', x-.2, x+.2, -4.6, 4.6, 9.7, 10.2, u.STONE, SHADE)


def reflecting_pool(rng):
    """A long oval pool in a white stone kerb."""
    ring = [(13*math.cos(a), 6.5*math.sin(a)) for a in (math.tau*i/24 for i in range(24))]
    pool('pool', ring, 0, u.STONE, WHITE, wall=.9, height=1.2)


def flowers(x0, x1, y0, y1, z, rng, count):
    """Drifts of flowers: each a low mound of foliage with small flat clumps of one colour on it."""
    for _ in range(count):
        x, y, radius, colour = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(1.1, 1.6), rng.choice(FLOWERS)
        mound('foliage', x, y, z, radius, .5, (.28, .40, .22), 7, rng=rng)
        for _ in range(4):
            a, d = rng.uniform(0, math.tau), rng.uniform(0, radius*.6)
            turned('flowers', [(rng.uniform(.4, .6), z+.42), (0, z+.72)], 5, PAINT, colour, x+d*math.cos(a), y+d*math.sin(a), rng.uniform(0, 70))


def flower_bed(rng):
    """A raised bed in a white kerb, in flower."""
    ring = [(8*math.cos(a), 3.6*math.sin(a)) for a in (math.tau*i/16 for i in range(16))]
    ring_wall('bed kerb', ring, 0, 1.8, u.STONE, WHITE, thick=.7)
    f.cap('bed soil', f.inset(ring, .7), 1.5, PAINT, (.26, .36, .20))
    flowers(-5.4, 5.4, -1.6, 1.6, 1.5, rng, 7)


def ring_garden(rng):
    """A round lawn in flower inside a floating white bench ring, open at its front."""
    f.cap('garden lawn', f.regular(0, 0, 6.4, 16), .5, u.TURF, u.TURF_TINT)
    ring_wall('garden kerb', f.regular(0, 0, 6.9, 16), 0, .7, u.STONE, WHITE, thick=.5)
    flowers(-3.6, 3.6, -3.6, 3.6, .5, rng, 6)
    mound('garden shrub', 0, 0, .5, 2.2, 2.6, (.30, .44, .24), 8, rng=rng)
    arc_band('garden bench foot', 8.3, 9.3, -60, 240, 0, 1.2, u.STONE, SHADE, steps=14)
    arc_band('garden bench', 7.8, 9.8, -62, 242, 1.2, 1.8, u.STONE, WHITE, steps=14)


def curved_bench(rng):
    """A white stone bench on a quarter circle: a seat floating on a recessed foot, a low back along its outside."""
    arc_band('bench foot', 7.5, 8.5, 230, 310, 0, 1.2, u.STONE, SHADE, steps=6, cy=9)
    arc_band('bench seat', 7.0, 9.0, 225, 315, 1.2, 1.8, u.STONE, WHITE, steps=6, cy=9)
    arc_band('bench back', 8.7, 9.0, 225, 315, 1.8, 3.2, u.STONE, WHITE, steps=6, cy=9)


def light_column(rng):
    """A slim white column, its head a band of warm light."""
    round_prism('column', 0, 0, 0, 9.0, .55, u.STONE, WHITE, 8)
    round_prism('column light', 0, 0, 9.0, 11.0, .6, PAINT, (.90, .84, .70), 8, light='night')
    round_prism('column cap', 0, 0, 11.0, 11.4, .8, u.STONE, WHITE, 8)


UTOPIA = {'garden-pavilion': garden_pavilion, 'pergola': pergola, 'reflecting-pool': reflecting_pool, 'flower-bed': flower_bed,
          'ring-garden': ring_garden, 'curved-bench': curved_bench, 'light-column': light_column}


# -- Frontier ---------------------------------------------------------------------------------------

STEEL_PALE = (.84, .85, .84)


def lattice(name, base, top, z0, z1, stages):
    """A lattice mast: four legs tapering from half width `base` to `top`, a ring and diagonals a stage."""
    for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        kb.bar(name+' leg', [(x*base, y*base, z0), (x*top, y*top, z1)], .16, k.FRAME, fine=False)
    for i in range(stages):
        za, zb = z0+(z1-z0)*i/stages, z0+(z1-z0)*(i+1)/stages
        a, b = base+(top-base)*i/stages, base+(top-base)*(i+1)/stages
        kb.bar(name+' ring', [(-b, -b, zb), (b, -b, zb), (b, b, zb), (-b, b, zb), (-b, -b, zb)], .1, k.FRAME, fine=i % 2 == 0)
        for (ax, ay), (bx, by) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            kb.bar(name+' brace', [(ax*a, ay*a, za), (bx*b, by*b, zb)], .08, k.FRAME)


def cabinet(x, y, wide=2.4, deep=1.6, tall=4.4):
    """An equipment cabinet in the look's plating, an orange stripe and a lit teal lamp on its door."""
    cuboid('cabinet', x-wide/2, x+wide/2, y-deep/2, y+deep/2, 0, tall, k.PLATING, (1, 1, 1), omit='b')
    cuboid('cabinet stripe', x-wide/2-.03, x+wide/2+.03, y-deep/2-.03, y+deep/2+.03, tall-1.0, tall-.6, PAINT, k.ORANGE, omit='bt', detail=True)
    lens('cabinet lamp', x-.2, x+.2, y-deep/2-.1, y-deep/2, tall-2.0, tall-1.6, k.TEAL, k.TEAL_LIGHT, omit='k')


def comms_mast(rng):
    """A communications mast: a steel lattice 32 tall, two dishes and a whip, a cabinet at its foot."""
    cuboid('mast foot', -2.6, 2.6, -2.6, 2.6, 0, .8, CAST, CONCRETE_DARK, omit='b')
    lattice('mast', 2.0, .6, .8, 32.0, 6)
    for z, turn in ((23.0, -30), (28.0, 40)):
        a = math.radians(turn-90)
        dx, dy = math.cos(a), math.sin(a)
        rim = [(dx*1.6-dy*2.2*math.cos(t), dy*1.6+dx*2.2*math.cos(t), z+2.2*math.sin(t)) for t in (math.tau*i/10 for i in range(10))]
        for i in range(10):
            verts = [rim[i], rim[(i+1) % 10], (dx*.8, dy*.8, z)]
            add('mast dish', PAINT, STEEL_PALE, verts, [(0, 1, 2), (2, 1, 0)])
        kb.bar('mast dish arm', [(0, 0, z), (dx*.8, dy*.8, z)], .2, k.FRAME, fine=False)
    kb.bar('mast whip', [(0, 0, 32.0), (0, 0, 38.0)], .1, k.FRAME, fine=False)
    lens('mast lamp', -.3, .3, -.3, .3, 32.0, 32.6, (.80, .30, .22), (.50, .08, .04))
    cabinet(4.4, 0)


def cargo_container(rng):
    """A plated cargo container on skids: orange doors at one end, steel frames at both, ribs along its roof."""
    cuboid('container', -10, 10, -4, 4, .6, 8.6, k.PLATING, (1, 1, 1), omit='b')
    for x in (-8.5, 8.5):
        cuboid('container skid', x-.5, x+.5, -4, 4, 0, .6, PAINT, k.DARK, omit='bt')
    for a0, a1 in ((-10.08, -9.5), (9.5, 10.08)):
        cuboid('container frame', a0, a1, -4.08, 4.08, .6, 8.68, k.MATTE, k.FRAME, omit='b')
    for y0, y1 in ((-3.5, -.1), (.1, 3.5)):
        add('container door', PAINT, k.ORANGE, [(-10.1, y1, 1.2), (-10.1, y0, 1.2), (-10.1, y0, 8.0), (-10.1, y1, 8.0)], [(0, 1, 2, 3)])
    add('container end', PAINT, (.34, .37, .40), [(10.1, -3.5, 1.2), (10.1, 3.5, 1.2), (10.1, 3.5, 8.0), (10.1, -3.5, 8.0)], [(0, 1, 2, 3)])
    for x in (-6, -2, 2, 6):
        cuboid('container rib', x-.2, x+.2, -4.04, 4.04, .6, 8.66, k.MATTE, k.BEVEL, omit='b', detail=True)
    cuboid('container door bar', -10.24, -10.1, -.7, -.5, 1.2, 8.0, PAINT, k.DARK, omit='r', detail=True)


def crate(x, y, z, half, colour, key=PAINT):
    """A crate with a steel frame along its edges and a lid."""
    cuboid('crate', x-half, x+half, y-half, y+half, z, z+2*half, key, colour, omit='b')
    for z0 in (z, z+2*half-.3):
        cuboid('crate frame', x-half-.08, x+half+.08, y-half-.08, y+half+.08, z0, z0+.3, k.MATTE, k.FRAME, omit='b')
    for cx, cy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        cuboid('crate frame', x+cx*half-.14, x+cx*half+.14, y+cy*half-.14, y+cy*half+.14, z, z+2*half, k.MATTE, k.FRAME, omit='bt', detail=True)


def drum(x, y, colour):
    turned('drum', [(1.2, 0), (1.2, 3.4), (1.0, 3.4)], 10, PAINT, colour, x, y)
    f.cap('drum', f.regular(x, y, 1.0, 10), 3.25, PAINT, tuple(v*.8 for v in colour))
    for z in (1.1, 2.3):
        round_prism('drum hoop', x, y, z, z+.2, 1.26, PAINT, k.DARK, 10, detail=True)


def supply_crates(rng):
    """Supplies on a pallet: framed crates, one under a strapped tarpaulin, drums standing in front."""
    cuboid('pallet', -5.4, 5.4, -2.8, 2.8, .5, .8, PAINT, (.52, .43, .30))
    for x in (-4.6, 0, 4.6):
        cuboid('pallet runner', x-.5, x+.5, -2.8, 2.8, 0, .5, PAINT, (.44, .36, .25), omit='bt')
    crate(-2.7, .3, .8, 2.2, (1, 1, 1), k.PLATING)
    crate(-2.7, .3, 5.2, 1.7, (.78, .80, .80), k.PLATING)
    low = f.rect(.4, 5.2, -2.2, 2.4)
    f.frustum('tarpaulin', low, .8, f.inset(low, .5), 5.0, PAINT, (.40, .44, .34))
    f.cap('tarpaulin', f.inset(low, .5), 5.0, PAINT, (.44, .48, .38))
    for x in (1.8, 3.8):
        cuboid('tarpaulin strap', x-.2, x+.2, -2.3, 2.5, .8, 5.06, PAINT, k.ORANGE, omit='b', detail=True)
    drum(-6.6, -4.2, k.TEAL)
    drum(-3.8, -4.6, (.72, .73, .72))


def storage_tank(rng):
    """A tank lying on two cradles: domed ends, an orange band, a ladder to a valve on its top."""
    sides, radius, half, up = 12, 3.4, 7.0, 4.6

    def hoop(x, r):
        return [(x, r*math.cos(math.tau*i/sides), up+r*math.sin(math.tau*i/sides)) for i in range(sides)]
    stations = [(-half-1.6, radius*.45), (-half-.9, radius*.82), (-half, radius), (half, radius), (half+.9, radius*.82), (half+1.6, radius*.45)]
    for (x0, r0), (x1, r1) in zip(stations, stations[1:]):
        a, b = hoop(x0, r0), hoop(x1, r1)
        for i in range(sides):
            j = (i+1) % sides
            verts = [a[i], b[i], b[j], a[j]]
            add('tank', PAINT, STEEL_PALE if r0 == r1 else (.76, .77, .76), verts, [k.facing(verts, ((r0-r1)*4, a[i][1]+a[j][1], a[i][2]+a[j][2]-2*up))])
    for x, r, way in ((stations[0][0], stations[0][1], -1), (stations[-1][0], stations[-1][1], 1)):
        add('tank end', PAINT, (.70, .71, .70), hoop(x, r), [k.facing(hoop(x, r), (way, 0, 0))])
    a, b = hoop(-.6, radius+.08), hoop(.6, radius+.08)
    for i in range(sides):
        j = (i+1) % sides
        verts = [a[i], b[i], b[j], a[j]]
        add('tank band', PAINT, k.ORANGE, verts, [k.facing(verts, (0, a[i][1]+a[j][1], a[i][2]+a[j][2]-2*up))])
    for x in (-4.4, 4.4):
        cuboid('tank cradle', x-.6, x+.6, -3.0, 3.0, 0, up-radius*.7, PAINT, k.DARK, omit='b')
    for x in (2.2, 3.2):
        kb.bar('tank ladder', [(x, -radius-.5, 0), (x, -radius-.5, up+1.0), (x, -1.2, up+radius+.2)], .09, k.FRAME, fine=False)
    for i in range(7):
        z = .8+i*1.0
        kb.bar('tank rung', [(2.2, -radius-.5, z), (3.2, -radius-.5, z)], .06, k.FRAME)
    turned('tank valve', [(.6, up+radius-.1), (.6, up+radius+1.0), (.9, up+radius+1.0), (.9, up+radius+1.3)], 6, PAINT, k.DARK, -2.4, 0)


def floodlight(rng):
    """A floodlight mast: a steel lattice post, a bank of four lit lamps."""
    cuboid('flood foot', -2.4, 2.4, -2.4, 2.4, 0, .8, CAST, CONCRETE_DARK, omit='b')
    lattice('flood', 1.8, .6, .8, 20.0, 4)
    cuboid('flood head', -3.4, 3.4, -.5, .5, 20.0, 22.6, PAINT, k.DARK)
    for i in range(4):
        x = -2.55+1.7*i
        lens('flood lamp', x-.65, x+.65, -.72, -.5, 20.3, 22.3, (.86, .84, .76), omit='k')
        cuboid('flood fin', x-.1, x+.1, .5, .9, 20.2, 22.4, PAINT, k.DARK, omit='f', detail=True)


def solar_array(rng):
    """Three solar panels tilted to the sun on a steel frame."""
    for x in (-9.4, -3.1, 3.1, 9.4):
        kb.bar('solar frame', [(x, -3.4, 0), (x, -3.4, 2.4), (x, 3.4, 7.2), (x, 3.4, 0)], .16, k.FRAME, fine=False)
    kb.bar('solar frame', [(-9.4, 3.4, 3.4), (9.4, 3.4, 3.4)], .12, k.FRAME)
    for i in range(3):
        x0, x1 = -9.2+6.3*i, -9.2+6.3*i+5.8
        verts = [(x0, -3.8, 2.3), (x1, -3.8, 2.3), (x1, 3.8, 7.7), (x0, 3.8, 7.7)]
        add('solar panel', k.SOLAR, (1, 1, 1), verts, [(0, 1, 2, 3)])
        add('solar panel back', PAINT, k.DARK, [(x, y, z-.12) for x, y, z in verts], [(3, 2, 1, 0)])
        for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
            kb.bar('solar panel edge', [verts[a], verts[b]], .1, k.FRAME)
    cabinet(-11.4, 2.0, 1.8, 1.4, 3.4)


def beacon_mast(rng):
    """A marker beacon: a steel post, an amber lamp in a cage, always lit."""
    turned('beacon foot', [(1.4, 0), (1.4, .8), (.5, 1.4)], 6, PAINT, k.DARK)
    turned('beacon post', [(.36, 1.4), (.28, 11.4), (.9, 11.8), (.9, 12.1)], 6, STEEL, k.FRAME)
    lens('beacon lamp', -.55, .55, -.55, .55, 12.1, 13.6, (.90, .66, .30), c.AMBER_LIGHT, omit='b')
    for x, y in ((-.75, -.75), (.75, -.75), (.75, .75), (-.75, .75)):
        kb.bar('beacon cage', [(x, y, 12.1), (x, y, 13.9)], .07, k.DARK)
    cuboid('beacon cap', -.95, .95, -.95, .95, 13.9, 14.2, PAINT, k.DARK)
    cuboid('beacon band', -.42, .42, -.42, .42, 6.0, 7.0, PAINT, k.ORANGE, omit='bt', detail=True)


def generator(rng):
    """A field generator on a skid: a plated housing with a louvred side, an exhaust stack, a control box with its lit
    lamp, fuel drums beside it."""
    for y in (-2.6, 2.6):
        cuboid('generator skid', -6.4, 6.4, y-.4, y+.4, 0, .7, PAINT, k.DARK, omit='b')
    cuboid('generator', -6.0, 3.6, -3.0, 3.0, .7, 6.4, k.PLATING, (1, 1, 1), omit='b')
    add('generator louvre', SLATS, h.LOUVRE, [(-5.0, -3.04, 1.8), (2.6, -3.04, 1.8), (2.6, -3.04, 5.4), (-5.0, -3.04, 5.4)], [(0, 1, 2, 3)])
    cuboid('generator roof', -6.2, 3.8, -3.2, 3.2, 6.4, 6.8, k.MATTE, k.FRAME)
    turned('generator stack', [(.5, 6.8), (.5, 10.2), (.7, 10.2), (.7, 10.8)], 8, PAINT, k.DARK, -4.0, 1.2)
    cuboid('generator panel', 3.6, 6.0, -2.4, 2.4, .7, 5.0, PAINT, k.ORANGE, omit='bl')
    lens('generator lamp', 4.5, 5.1, -2.5, -2.4, 3.6, 4.2, k.TEAL, k.TEAL_LIGHT, omit='k')
    add('generator dial', PAINT, k.DARK, [(4.0, -2.42, 1.6), (5.6, -2.42, 1.6), (5.6, -2.42, 3.0), (4.0, -2.42, 3.0)], [(0, 1, 2, 3)], detail=True)
    drum(8.4, -1.6, k.TEAL)
    drum(8.8, 1.4, (.72, .73, .72))


FRONTIER = {'solar-array': solar_array, 'comms-mast': comms_mast, 'beacon-mast': beacon_mast, 'cargo-container': cargo_container,
            'supply-crates': supply_crates, 'storage-tank': storage_tank, 'floodlight': floodlight, 'generator': generator}

LOOKS = {'imperial': (IMPERIAL, ib.finish), 'heritage': (HERITAGE, hb.finish), 'civic': (CIVIC, None), 'utopia': (UTOPIA, None),
         'frontier': (FRONTIER, None)}


def build(look, name):
    """Writes one prop in its two levels."""
    props, finish = LOOKS[look]
    kb.build_scene(name, lambda: props[name](random.Random(sum(map(ord, look+name)))), finish or (lambda obj: None), lambda obj: False)
    levels = {i: shared.export_model(shared.objects, f'{name}-lod{i}', level=i, exact=True) for i in (0, 1)}
    for level in levels.values():
        for material in level['materials']:
            for texture in material.get('textures', ()):
                # The exporter names textures from a building's folder; a prop's lies two under models/board.
                texture['filename'] = texture['filename'].replace('../../board/textures/', '../../textures/')
    triangles = [sum(len(part['indices'])//3 for mesh in level['meshes'] for part in mesh['parts']) for level in levels.values()]
    assert triangles[0] <= MAX_TRIANGLES, (look, name, triangles)
    folder = SCENERY/look
    folder.mkdir(parents=True, exist_ok=True)
    write_glb(folder/(name+'.glb'), levels=levels)
    print('RESULT', look, name, 'triangles', *triangles)


if __name__ == '__main__' and '--' in sys.argv:
    wanted = sys.argv[sys.argv.index('--')+1:]
    for look, (props, _) in LOOKS.items():
        for name in props:
            if not wanted or look in wanted or f'{look}/{name}' in wanted:
                build(look, name)
