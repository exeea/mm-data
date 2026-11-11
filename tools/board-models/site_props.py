"""Site and field props: construction materials and the excavation, the defence gun, the dragon's tooth and the
salvage limbs, the landing beacons and light, the roof's exhaust unit and chimney stack, the crossing signal. Steel is
the board's painted, weathered and rusted steel, concrete its cast concrete, earth its soil. Each keeps the name and
the footprint it is placed by. (Vehicles and machines are photographic: tools/vehicle-assets.)

Run: blender -b --factory-startup --python site_props.py -- [name ...]   (none: all)
Writes data/models/board/<folder>/<name>.glb, two levels of detail (the far one without the fine parts). 3 units to
the metre; a prop's long axis is y.
"""
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'parks'))
import park_props as pp
from park_props import PAINT, TAU, add, at, box, f, hk, kb, la, polar, shared, u
from glb_geometry import write_glb

BOARD = la.SCENERY.parent
CAST = la.CAST
RUST = 'structures/common/rusted-steel'
PLATE = 'structures/common/diamond-plate'
STRIPES = 'structures/common/hazard-stripes'
SHEET = 'structures/common/corrugated'
MATTE, FAN = 'structures/common/matte-steel', 'structures/industrial/fan'
EARTH, EARTH_DARK = 'terrain/surfaces/dirt-ground', 'terrain/surfaces/biome-soil'
RUBBLE, SLAB = 'scenery/rubble-debris-concrete', 'scenery/rubble-slab'
ARMOUR, ARMOUR_DARK, ARMOUR_EDGE = 'structures/turret/turret-paint', 'structures/turret/turret-dark', 'structures/turret/turret-edge'
WHITE, DARK = (1, 1, 1), (.17, .18, .19)
CONCRETE, CONCRETE_DARK = la.CONCRETE, la.CONCRETE_DARK
RED_LENS = (.86, .12, .08)



def cyl(name, p, q, radius, sides, key, colour, end=None, caps='ab', bore=False, **flags):
    """A round bar from p to q (radius `end` at q when given); `caps` names the ends closed (a at p, b at q); a `bore`
    is seen from inside."""
    ax = [q[i]-p[i] for i in range(3)]
    length = math.sqrt(sum(v*v for v in ax))
    ax = [v/length for v in ax]
    side = (0, 0, 1) if abs(ax[2]) < .9 else (1, 0, 0)
    e1 = [ax[1]*side[2]-ax[2]*side[1], ax[2]*side[0]-ax[0]*side[2], ax[0]*side[1]-ax[1]*side[0]]
    norm = math.sqrt(sum(v*v for v in e1))
    e1 = [v/norm for v in e1]
    e2 = [ax[1]*e1[2]-ax[2]*e1[1], ax[2]*e1[0]-ax[0]*e1[2], ax[0]*e1[1]-ax[1]*e1[0]]
    rings = []
    for centre, r in ((p, radius), (q, radius if end is None else end)):
        rings.append([tuple(centre[i]+r*(math.cos(TAU*k/sides)*e1[i]+math.sin(TAU*k/sides)*e2[i]) for i in range(3)) for k in range(sides)])
    verts = rings[0]+rings[1]
    faces = [(k, (k+1) % sides, sides+(k+1) % sides, sides+k) for k in range(sides)]
    if bore:
        faces = [face[::-1] for face in faces]
    if 'a' in caps:
        faces.append(tuple(range(sides-1, -1, -1)))
    if 'b' in caps:
        faces.append(tuple(range(sides, 2*sides)))
    add(name, key, colour, verts, faces, **flags)


def mound_of(name, x, y, half_x, half_y, height, key, colour, rng, sides=9):
    """A low heap: an uneven foot, a shoulder, a crown off its middle."""
    spin = rng.uniform(0, TAU)
    foot = [(x+half_x*rng.uniform(.85, 1.1)*math.cos(spin+TAU*k/sides), y+half_y*rng.uniform(.85, 1.1)*math.sin(spin+TAU*k/sides)) for k in range(sides)]
    cx, cy = x+rng.uniform(-.15, .15)*half_x, y+rng.uniform(-.15, .15)*half_y
    shoulder = f.scaled(foot, .58, (cx, cy))
    f.frustum(name, foot, 0, shoulder, height*.72, key, colour)
    verts = [(*p, height*.72) for p in shoulder]+[(cx, cy, height)]
    add(name, key, colour, verts, [(k, (k+1) % sides, sides) for k in range(sides)])


# -- Construction -----------------------------------------------------------------------------------

def pipe_section(x, y, a, length=5.4, radius=2.2, wall=.3):
    """A concrete pipe section on its side along the part's x, on two timber chocks."""
    lift = radius+.25
    p, q = (*at(x, y, a, -length/2, 0), lift), (*at(x, y, a, length/2, 0), lift)
    cyl('pipe', p, q, radius, 12, CAST, CONCRETE, caps='')
    cyl('pipe bore', p, q, radius-wall, 12, CAST, CONCRETE_DARK, caps='', bore=True)
    for end, sign in ((p, -1), (q, 1)):
        outer = [tuple(end[i]+c for i, c in enumerate((*[v*radius for v in rot(a, 0, math.cos(TAU*k/12))], radius*math.sin(TAU*k/12)))) for k in range(12)]
        inner = [tuple(end[i]+c for i, c in enumerate((*[v*(radius-wall) for v in rot(a, 0, math.cos(TAU*k/12))], (radius-wall)*math.sin(TAU*k/12)))) for k in range(12)]
        for k in range(12):
            j = (k+1) % 12
            quad = [outer[k], outer[j], inner[j], inner[k]]
            add('pipe rim', CAST, CONCRETE, quad, [(0, 1, 2, 3), (3, 2, 1, 0)])
    for px in (-length/2+.9, length/2-.9):
        box('pipe chock', x, y, a, px-.35, px+.35, -radius*.8, radius*.8, 0, .28, PAINT, pp.TIMBER, detail=True)


def rot(a, px, py):
    """A part-frame offset turned by `a` degrees."""
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return px*c-py*s, px*s+py*c


def concrete_pipe(rng):
    pipe_section(0, 0, 90)


def debris(rng):
    """A heap of broken concrete: rubble under tilted slabs and bent reinforcing bars."""
    mound_of('debris heap', 0, 0, 8.4, 4.6, 1.5, RUBBLE, WHITE, rng, 10)
    for _ in range(7):
        x, y, a = rng.uniform(-6, 6), rng.uniform(-3, 3), rng.uniform(0, 180)
        w, d, t = rng.uniform(1.6, 3.2), rng.uniform(1.2, 2.2), rng.uniform(.3, .5)
        lift, tilt = rng.uniform(.5, 1.3), rng.uniform(.2, .9)
        v = [(*at(x, y, a, px, py), lift+pz+(px/w)*tilt) for pz in (0, t) for px, py in ((-w, -d), (w, -d), (w, d), (-w, d))]
        add('debris slab', SLAB, tuple(rng.uniform(.8, 1) for _ in range(1))*3, v,
            [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    for _ in range(5):
        x, y, a = rng.uniform(-6, 6), rng.uniform(-3, 3), rng.uniform(0, TAU)
        kb.bar('debris bar', [(x, y, .6), (x+1.6*math.cos(a), y+1.6*math.sin(a), 2.0), (x+2.6*math.cos(a+.6), y+2.6*math.sin(a+.6), 1.7)], .07, (.42, .22, .14))


def site_excavation(rng):
    """An excavation: sheet piles round a dug floor, spoil banked outside them and heaped at one end, a ladder, pipe
    sections and reinforcing bars waiting, striped barriers at the open side."""
    x0, x1, y0, y1 = -22.0, 20.0, -21.0, 21.0
    pit = f.rect(x0, x1, y0, y1)
    berm = f.inset(pit, -4.6)
    f.frustum('spoil bank', berm, 0, f.inset(pit, -.6), 3.4, EARTH, (.84, .76, .64))
    pp.ring_band('spoil top', pit, f.inset(pit, -.6), 3.4, EARTH, (.84, .76, .64))
    for i in range(4):  # The piles' inner faces, down to the floor.
        p, q = pit[i], pit[(i+1) % 4]
        la.facing('sheet piles', SHEET, (.62, .46, .36), [(*q, .25), (*p, .25), (*p, 4.2), (*q, 4.2)], (*f.outward(q, p), 0))
        la.facing('sheet piles', SHEET, (.62, .46, .36), [(*p, 3.4), (*q, 3.4), (*q, 4.2), (*p, 4.2)], (*f.outward(p, q), 0))
    f.cap('dug floor', pit, .25, EARTH_DARK, (.74, .68, .60))
    for cx, cy, hx, hy, tall in ((27.0, 12.0, 4.4, 5.6, 5.0), (27.6, 0.5, 4.0, 5.0, 4.2), (26.8, -11.0, 4.6, 5.8, 5.6)):
        mound_of('spoil heap', cx, cy, hx, hy, tall, EARTH, (.86, .78, .66), rng)
    for k, (x, y) in enumerate(((-13.0, 11.0), (-13.0, 5.4), (-13.0, -.2))):
        pipe_section(x, y, 90, length=5.0, radius=2.0)
    for k in range(6):
        kb.bar('rebar', [(4.0+k*.45, -15.0, .5+.1*(k % 2)), (4.0+k*.45, 2.0, .5+.1*(k % 2))], .1, (.52, .24, .14), fine=k % 2 == 1)
    for z in range(8):
        kb.bar('ladder rung', [(8.0, y1-.3, .6+z*.55), (9.2, y1-.3, .6+z*.55)], .06, (.80, .80, .78))
    for px in (8.0, 9.2):
        kb.bar('ladder rail', [(px, y1-.1, .25), (px, y1-.5, 5.4)], .08, (.80, .80, .78), fine=False)
    for y in (-12.0, 0.0, 12.0):  # Barriers along the open side.
        box('barrier', 0, 0, 0, x0-4.0, x0-3.4, y-4.4, y+4.4, 1.6, 2.8, STRIPES, WHITE, omit='')
        for py in (y-3.8, y+3.8):
            box('barrier foot', 0, 0, 0, x0-4.4, x0-3.0, py-.3, py+.3, 0, 1.6, PAINT, (.92, .92, .90), detail=True)


# -- Military ---------------------------------------------------------------------------------------

def dragon_tooth(rng):
    """A concrete anti-tank tooth on its footing."""
    box("tooth footing", 0, 0, 0, -3.2, 3.2, -3.2, 3.2, 0, .5, CAST, CONCRETE_DARK)
    low, high = f.rect(-2.7, 2.7, -2.7, 2.7), f.rect(-.9, .9, -.9, .9)
    f.frustum('tooth', low, .5, high, 4.4, CAST, CONCRETE)
    f.cap('tooth', high, 4.4, CAST, CONCRETE)


def orbital_gun(rng):
    """A planetary defence gun: a concrete emplacement ring with a hazard band, an armoured house on its race ring,
    two heavy barrels in their cradles with muzzle brakes, vents, a ladder and a hatch."""
    la.turned('emplacement', [(24.0, 0), (24.0, 2.2), (22.6, 3.0), (17.6, 3.0)], 24, CAST, CONCRETE)
    pp.ring_band('emplacement band', f.regular(0, 0, 19.2, 24), f.regular(0, 0, 21.6, 24), 3.02, STRIPES, WHITE, detail=True)
    f.cap('emplacement floor', f.regular(0, 0, 17.6, 24), 1.6, PLATE, (.60, .61, .62))
    f.wall_ring('emplacement well', f.regular(0, 0, 17.6, 24)[::-1], 1.6, 3.0, CAST, CONCRETE_DARK)
    la.turned('race ring', [(12.4, 1.6), (12.4, 3.6), (11.2, 4.2)], 16, ARMOUR_DARK, WHITE)
    house = [(-9.5, -7.0), (9.5, -7.0), (11.0, -2.0), (11.0, 9.0), (8.0, 12.5), (-8.0, 12.5), (-11.0, 9.0), (-11.0, -2.0)]
    top = f.scaled(house, .86, (0, 2.5))
    f.wall_ring('gun house', house, 4.2, 8.6, ARMOUR, WHITE)
    f.frustum('gun house', house, 8.6, top, 11.0, ARMOUR, WHITE)
    f.cap('gun house', top, 11.0, ARMOUR, WHITE)
    f.wall_ring('gun house edge', house, 4.0, 4.5, ARMOUR_EDGE, WHITE, detail=True)
    for side in (-1, 1):
        x = side*4.6
        box('cradle', 0, 0, 0, x-2.3, x+2.3, -10.5, -6.6, 5.2, 9.6, ARMOUR_DARK, WHITE, omit='k')
        cyl('barrel', (x, -10.4, 7.4), (x, -23.0, 8.9), 1.25, 10, ARMOUR_DARK, WHITE, end=1.0, caps='')
        cyl('barrel sleeve', (x, -10.4, 7.4), (x, -14.6, 7.9), 1.7, 10, ARMOUR, WHITE, caps='b')
        cyl('muzzle brake', (x, -22.2, 8.8), (x, -25.2, 9.16), 1.5, 8, ARMOUR_DARK, (.7, .7, .7), caps='ab')
        add('house vent', la.SLATS, (.36, .36, .36), [(side*11.03, 1.0, 5.4), (side*11.03, 7.0, 5.4), (side*11.03, 7.0, 7.8), (side*11.03, 1.0, 7.8)],
            [(0, 1, 2, 3), (3, 2, 1, 0)], detail=True)
    box('range finder', 0, 0, 0, -12.6, 12.6, 3.0, 4.6, 9.2, 10.4, ARMOUR_DARK, WHITE, omit='')
    box('roof hatch', 0, 0, 0, -1.6, 1.6, 7.0, 10.0, 11.0, 11.4, ARMOUR_DARK, WHITE, detail=True)
    for z in range(6):
        kb.bar('gun ladder', [(-1.0, 12.55, 4.6+z*.9), (1.0, 12.55, 4.6+z*.9)], .08, (.74, .74, .72))
    cyl('gun mast', (7.0, 9.0, 11.0), (7.0, 9.0, 15.4), .14, 4, PAINT, DARK, caps='b', detail=True)


# -- Salvage ----------------------------------------------------------------------------------------
# A wrecked 'Mek limb stands along z, its torn joint down; the board lays it where it fell.

def torn(z, rng):
    """A torn joint's end: bent struts and a hanging actuator rod."""
    for a in (20, 140, 250):
        x, y = polar(1.1, a)
        kb.bar('torn strut', [(x, y, z+.8), (x*1.5+rng.uniform(-.4, .4), y*1.5+rng.uniform(-.4, .4), z-.9)], .14, (.44, .26, .18))


def salvage_arm(rng):
    """A 'Mek arm: a shoulder joint, an armoured upper arm, an elbow, a heavier forearm, a weapon's barrel in its cuff."""
    scorched = (.62, .60, .58)
    la.turned('arm shoulder', [(1.5, -.4), (2.6, .4), (2.8, 1.8), (2.1, 3.0)], 8, ARMOUR_DARK, WHITE)
    torn(-.3, rng)
    f.frustum('upper arm', f.rect(-2.4, 2.4, -2.0, 2.0), 3.0, f.rect(-2.0, 2.0, -1.7, 1.7), 10.2, ARMOUR, WHITE)
    box('arm plate', 0, 0, 0, 2.0, 2.75, -1.5, 1.5, 4.2, 9.2, ARMOUR, scorched, detail=True)
    cyl('elbow', (-2.6, 0, 11.3), (2.6, 0, 11.3), 1.7, 8, ARMOUR_DARK, WHITE)
    low, high = f.rect(-2.2, 2.2, -1.9, 1.9), f.rect(-3.0, 3.0, -2.4, 2.4)
    f.frustum('forearm', low, 12.4, high, 20.2, ARMOUR, WHITE)
    box('arm cuff', 0, 0, 0, -3.3, 3.3, -2.7, 2.7, 20.2, 21.2, ARMOUR_EDGE, WHITE, omit='')
    cyl('arm barrel', (0, 0, 21.2), (0, 0, 23.2), 1.15, 8, ARMOUR_DARK, WHITE, caps='')
    cyl('arm bore', (0, 0, 21.2), (0, 0, 23.2), .8, 8, PAINT, (.06, .06, .06), caps='a', bore=True)
    box('arm vent', 0, 0, 0, -3.05, -2.6, -1.4, 1.4, 14.0, 18.4, ARMOUR_DARK, scorched, detail=True)


def salvage_leg(rng):
    """A 'Mek leg: a hip joint, an armoured thigh, a knee under its cap, a shin, an ankle, a foot with two toes to -y."""
    la.turned('hip', [(1.4, 23.8), (2.8, 24.8), (2.8, 26.4), (1.6, 27.4)], 8, ARMOUR_DARK, WHITE)
    for a in (40, 170, 290):
        x, y = polar(1.0, a)
        kb.bar('torn strut', [(x, y, 26.8), (x*1.6, y*1.6, 27.7)], .14, (.44, .26, .18))
    f.frustum('thigh', f.rect(-3.0, 3.0, -2.6, 2.6), 15.6, f.rect(-3.4, 3.4, -3.0, 3.0), 24.0, ARMOUR, WHITE)
    cyl('knee', (-3.4, 0, 14.1), (3.4, 0, 14.1), 2.0, 8, ARMOUR_DARK, WHITE)
    box('knee cap', 0, 0, 0, -2.2, 2.2, -3.3, -2.0, 12.4, 15.8, ARMOUR_EDGE, WHITE, omit='')
    f.frustum('shin', f.rect(-2.6, 2.6, -2.4, 2.6), 3.2, f.rect(-3.2, 3.2, -2.8, 3.0), 12.6, ARMOUR, WHITE)
    box('shin plate', 0, 0, 0, -1.8, 1.8, -3.2, -2.5, 4.6, 11.0, ARMOUR, (.62, .60, .58), detail=True)
    cyl('ankle', (-2.9, 0, 2.2), (2.9, 0, 2.2), 1.5, 8, ARMOUR_DARK, WHITE)
    box('foot', 0, 0, 0, -3.6, 3.6, -4.6, 3.4, -1.8, 1.0, ARMOUR_DARK, WHITE, omit='')
    for x in (-1.9, 1.9):
        box('toe', 0, 0, 0, x-1.5, x+1.5, -7.7, -4.6, -1.8, .2, ARMOUR, WHITE, omit='')


# -- Airfield and rail ------------------------------------------------------------------------------

def lamp_head(x, y, z, radius, colour, light):
    """A beacon lamp: a steel collar, a lit lens under a wire guard."""
    la.turned('lamp collar', [(radius*1.25, z), (radius*1.25, z+radius*.5), (radius, z+radius*.7)], 8, PAINT, DARK, x, y)
    la.turned('lamp lens', [(radius*.92, z+radius*.7), (radius*.86, z+radius*1.5), (radius*.5, z+radius*2.0), (0, z+radius*2.15)], 8, PAINT, colour, x, y,
              light=light)
    for k in range(4):
        px, py = polar(radius*1.1, 45+90*k)
        kb.bar('lamp guard', [(x+px, y+py, z+radius*.5), (x+px*.8, y+py*.8, z+radius*1.9), (x, y, z+radius*2.45)], .07, DARK)


def landing_pad(ring):
    """A landing beacon's pad: a dark deck in a steel kerb with a hazard band, its beacon on a plinth in the middle."""
    la.ring_wall('pad kerb', ring, 0, 1.0, PAINT, DARK, thick=1.0)
    inner = f.inset(ring, 1.0)
    band = f.inset(ring, 3.4)
    pp.ring_band('pad band', band, inner, .8, STRIPES, WHITE)
    f.cap('pad deck', band, .8, PLATE, (.42, .43, .45))
    la.turned('beacon plinth', [(5.2, .8), (5.2, 1.8), (4.2, 2.4), (3.2, 2.4)], 12, CAST, CONCRETE)
    lamp_head(0, 0, 2.4, 2.1, RED_LENS, la.c.RED_LIGHT)


def landing_beacon_hex(rng):
    landing_pad(f.regular(0, 0, 22.0, 6))


def landing_beacon_round(rng):
    landing_pad(f.regular(0, 0, 22.0, 24))


def landing_light(rng):
    """A pad-edge light: a square concrete foot under a red lamp."""
    box('light foot', 0, 0, 0, -3.2, 3.2, -3.2, 3.2, 0, .7, CAST, CONCRETE_DARK)
    lamp_head(0, 0, .7, 1.5, RED_LENS, la.c.RED_LIGHT)


def panel(name, key, colour, corners, uvs):
    """A flat panel whose picture is laid out by hand: a fan in its frame, slats that count."""
    obj = u.add_mesh(name, key, colour, corners, [(0, 1, 2, 3)], smooth=None, uvs=uvs)
    obj['detail'] = False


def roof_vent(rng):
    """A rooftop exhaust unit: a galvanised housing on a concrete curb, louvred down both sides and at its ends, three
    fans in square frames on top, a service hatch and a conduit."""
    galvanised, slats = (.86, .87, .88), (.70, .71, .72)
    box('vent curb', 0, 0, 0, -7.5, 7.5, -11.0, 11.0, 0, .7, CAST, CONCRETE_DARK)
    box('vent housing', 0, 0, 0, -6.8, 6.8, -10.3, 10.3, .7, 5.0, MATTE, galvanised)
    box('vent flange', 0, 0, 0, -7.1, 7.1, -10.6, 10.6, 5.0, 5.3, MATTE, (.74, .75, .76), omit='')
    for side in (-1, 1):  # Louvres: three bays down each side, one at each end.
        x = side*6.84
        for y0, y1 in ((-9.5, -3.7), (-2.9, 2.9), (3.7, 9.5)):
            corners = [(x, y0, 1.3), (x, y1, 1.3), (x, y1, 4.5), (x, y0, 4.5)]
            panel('vent louvre', la.SLATS, slats, corners if side > 0 else corners[::-1], [(0, 0), (1, 0), (1, 4), (0, 4)] if side > 0 else [(0, 4), (1, 4), (1, 0), (0, 0)])
        y = side*10.34
        corners = [(-5.6, y, 1.3), (5.6, y, 1.3), (5.6, y, 4.5), (-5.6, y, 4.5)]
        panel('vent louvre', la.SLATS, slats, corners[::-1] if side > 0 else corners, [(0, 4), (1, 4), (1, 0), (0, 0)] if side > 0 else [(0, 0), (1, 0), (1, 4), (0, 4)])
        for px in (-6.6, 6.6):
            box('vent post', 0, 0, 0, px-.25, px+.25, side*10.3-.25, side*10.3+.25, .7, 5.0, MATTE, (.66, .67, .68), detail=True)
    for y in (-6.9, 0.0, 6.9):  # The fans, each in its square frame under a guard.
        box('fan frame', 0, 0, 0, -3.1, 3.1, y-3.1, y+3.1, 5.3, 6.3, MATTE, (.60, .61, .62))
        panel('fan', FAN, WHITE, [(-3.0, y-3.0, 6.32), (3.0, y-3.0, 6.32), (3.0, y+3.0, 6.32), (-3.0, y+3.0, 6.32)], [(0, 0), (1, 0), (1, 1), (0, 1)])
        for a in (45, 135):
            dx, dy = polar(3.9, a)
            kb.bar('fan guard', [(-dx, y-dy, 6.36), (0, y, 6.62), (dx, y+dy, 6.36)], .06, DARK)
    box('vent hatch', 0, 0, 0, 6.8, 6.95, -1.6, 1.6, .9, 1.25, MATTE, (.60, .61, .62), detail=True)
    cyl('vent conduit', (-7.15, -10.0, .95), (-7.15, 10.0, .95), .22, 6, MATTE, (.66, .67, .68), caps='ab', detail=True)


def shell(name, profile, sides, key, colour, **flags):
    """A shape turned about the upright axis, open at both ends: faces between the (radius, height) points of `profile`."""
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        f.frustum(name, f.regular(0, 0, r0, sides), z0, f.regular(0, 0, r1, sides), z1, key, colour, **flags)


def chimney_stack(rng):
    """A roof's chimney stack: a brick shaft on a concrete footing, steel bands round it, a corbelled concrete crown
    round its sooty flue, climbing rungs and a lightning rod."""
    brick, sooty = (1, .96, .92), (.50, .46, .43)
    la.turned('chimney footing', [(7.6, 0), (7.6, 1.2), (6.2, 1.9)], 8, CAST, CONCRETE_DARK, start=22.5)
    shell('chimney shaft', [(5.3, 1.9), (4.9, 9.2)], 12, hk.BRICK, brick)
    shell('chimney shaft', [(4.9, 9.2), (4.75, 11.6)], 12, hk.BRICK, sooty)  # Soot under the crown.
    shell('chimney crown', [(4.75, 11.6), (5.6, 12.2), (5.6, 13.4), (4.1, 14.0), (3.6, 14.0)], 12, CAST, (.66, .64, .61))
    f.wall_ring('chimney flue', f.regular(0, 0, 3.6, 12)[::-1], 11.0, 14.0, PAINT, (.07, .06, .06))
    f.cap('chimney flue', f.regular(0, 0, 3.6, 12), 11.0, PAINT, (.04, .04, .04))
    for z, radius in ((4.4, 5.22), (8.2, 5.0)):
        la.turned('chimney band', [(radius, z), (radius+.12, z+.1), (radius+.12, z+.5), (radius, z+.6)], 12, RUST, (.62, .50, .42), detail=True)
    for side in (-.7, .7):  # A ladder up the shaft: two rails and their rungs.
        kb.bar('chimney ladder', [(side, -5.75, 1.9), (side, -5.3, 11.4)], .07, (.30, .30, .31), fine=False)
    for k in range(8):
        z = 2.8+k*1.1
        y = -5.75+(z-1.9)*.047
        kb.bar('chimney rung', [(-.7, y, z), (.7, y, z)], .06, (.30, .30, .31))
    cyl('lightning rod', (4.3, 0, 13.4), (4.3, 0, 16.4), .08, 4, PAINT, DARK, caps='b', detail=True)


def crossing_signal(rng):
    """A level-crossing signal: a striped post, a pair of red lamps under hoods on a cross arm, a bell."""
    la.turned('signal foot', [(.7, 0), (.7, .5), (.3, .9)], 6, CAST, CONCRETE_DARK)
    cyl('signal post', (0, 0, .5), (0, 0, 10.2), .16, 6, PAINT, (.90, .90, .88), caps='b')
    cyl('signal band', (0, 0, 2.0), (0, 0, 3.4), .18, 6, PAINT, (.80, .16, .12), caps='', detail=True)
    box('signal arm', 0, 0, 0, -1.3, 1.3, -.12, .12, 7.6, 7.9, PAINT, DARK, omit='')
    for px in (-1.0, 1.0):
        cyl('signal lamp', (px, -.05, 7.75), (px, -.5, 7.75), .5, 8, PAINT, DARK, caps='a')
        add('signal lens', PAINT, RED_LENS, [(px+.36*math.cos(TAU*k/8), -.51, 7.75+.36*math.sin(TAU*k/8)) for k in range(8)], [tuple(range(8)), tuple(range(7, -1, -1))],
            light=la.c.RED_LIGHT)
        box('signal hood', 0, 0, 0, px-.55, px+.55, -.95, -.05, 8.25, 8.33, PAINT, DARK, omit='', detail=True)
    for a in (45, 135):  # The crossed boards, without lettering.
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        v = [(-1.5*c-.16*-s, .14, 9.3+-1.5*s-.16*c), (1.5*c-.16*-s, .14, 9.3+1.5*s-.16*c), (1.5*c+.16*-s, .14, 9.3+1.5*s+.16*c), (-1.5*c+.16*-s, .14, 9.3-1.5*s+.16*c)]
        add('signal board', PAINT, (.94, .94, .92), v, [(0, 1, 2, 3), (3, 2, 1, 0)])
    la.turned('signal bell', [(.34, 10.2), (.34, 10.5), (.2, 10.8), (0, 10.9)], 6, PAINT, (.60, .50, .22), detail=True)


# name: (builder, folder, near triangle limit)
PROPS = {'concrete-pipe': (concrete_pipe, 'scenery/construction', 400), 'debris-1': (debris, 'scenery/construction', 500),
         'debris-3': (debris, 'scenery/construction', 500), 'site-excavation': (site_excavation, 'scenery/construction', 1600),
         'dragon-tooth': (dragon_tooth, 'rough', 60), 'orbital-gun': (orbital_gun, 'scenery/military', 1600),
         'arm': (salvage_arm, 'salvage', 400), 'leg': (salvage_leg, 'salvage', 400),
         'landing-beacon-hex': (landing_beacon_hex, 'scenery/roofs', 700), 'landing-beacon-round': (landing_beacon_round, 'scenery/roofs', 900),
         'landing-light': (landing_light, 'scenery/roofs', 300), 'grille': (roof_vent, 'scenery/roofs', 300),
         'chimney-stack': (chimney_stack, 'scenery/roofs', 600), 'crossing-signal': (crossing_signal, 'scenery/rail', 400)}


def build(name):
    """Writes one prop in its two levels."""
    builder, folder, limit = PROPS[name]
    kb.build_scene(name, lambda: builder(random.Random(sum(map(ord, 'site'+name)))), lambda obj: None, lambda obj: False)
    levels = {i: shared.export_model(shared.objects, f'{name}-lod{i}', level=i, exact=True) for i in (0, 1)}
    depth = '../'*len(folder.split('/'))
    for level in levels.values():
        for material in level['materials']:
            for texture in material.get('textures', ()):
                texture['filename'] = texture['filename'].replace('../../board/textures/', depth+'textures/')
    triangles = [sum(len(part['indices'])//3 for mesh in level['meshes'] for part in mesh['parts']) for level in levels.values()]
    assert triangles[0] <= limit, (name, triangles)
    out = Path(sys.argv[sys.argv.index('--out')+1])/folder if '--out' in sys.argv else BOARD/folder
    out.mkdir(parents=True, exist_ok=True)
    write_glb(out/(name+'.glb'), levels=levels)
    print('RESULT', name, 'triangles', *triangles)


if __name__ == '__main__' and '--' in sys.argv:
    wanted = [arg for arg in sys.argv[sys.argv.index('--')+1:] if arg in PROPS]
    for name in PROPS:
        if not wanted or name in wanted:
            build(name)
