"""The Imperial authored buildings, built from the modular kit's own bays (imperial_kit): each block a box whose walls
are laid with the kit's bays at their real widths, a pier closing every corner; the parts the kit lacks modelled here in
the same finishes: hipped seamed roofs whose flared eaves run out to upturned tips, lanterns of glass along their ridges,
lacquer columns and roofed gates, stairs, stone lanterns, planters and the plant behind pale louvred screens.

Run: blender -b --factory-startup --python imperial_buildings.py -- <name> [sheet folder]
Writes data/models/buildings/authored/imperial-<name>.glb, its hexes those its volumes cover (hex centres 62.34 apart
across, 72 along a column, odd columns 36 up; printed as HEX lines), front (the entrance) to -y. Where a sheet's views
disagree, its ISO view wins.
"""
import math
import random
import re
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import authored_examples as shared
import civic_blocks as c
import civic_habitat as h
import frontier_buildings as f
import imperial_kit as ik
import theme_kits as k
import utopia_buildings as u
from civic_blocks import HAZARD
from civic_habitat import CAST, PAINT, PALE_GLASS, SLATS, add, cuboid, deck, disc, round_prism
from glb_geometry import write_glb
from imperial_kit import (BRONZE, COURSE, COURSE_TONE, DARK, GRANITE, LACQUER, PALE_LOUVRE, PALE_PANE, PIER, PIER_OUT, PIER_TONE, PLINTH,
                          SEAMED, SOFFIT, STONE)
from theme_kits import LEVEL, W, back_wall, facade, recess
from utopia_buildings import LAWN_REPEAT, TURF, TURF_TINT

EXTEND = 8.0  # How far a wall's pier goes on past its end, for the corner's mitre to trim.
BEHIND = 2.4  # How far inside its walls a block's volume stays: the game's floors never show in a recess.
RED = ('red-window', 'red-balcony', 'shop', 'shop-wide', 'shop-door')
BOXWOOD = (.34, .46, .22)
RIB = (.20, .21, .22)  # Hips and ridges: the roof's own dark. Bronze is for eaves, fins and frames.
PAVERS, DECK_TONE = h.PANELS, (.60, .60, .60)  # Flat roofs: concrete pavers, mid grey as the sheets' decks.
volumes = []  # (outline, top) of every volume, for the hexes' report.


# -- Walls ------------------------------------------------------------------------------------------

def fill(length, base, red=False, banded=True):
    """A stretch of pier (or lacquer column) with its course and granite foot: a wall's pier carried on past its end
    for the corner's mitre to trim, or a wall too short for a bay; not banded, a tower's pier, without the course."""
    out, key, colour, top = (ik.COLUMN_OUT, PAINT, LACQUER, LEVEL) if red else (PIER_OUT, STONE, PIER_TONE, COURSE if banded else LEVEL)
    foot = PLINTH if base else 0.0
    # Closed all round: at a corner the next wall's pier may stand less proud, and this one's back shows.
    cuboid('pier', 0, length, -out, 0, foot, top, key, colour, omit='b' if red or not banded else 'bt')
    if base:
        cuboid('pier foot', 0, length, -out-.3, 0, 0, foot, CAST, GRANITE, omit='b')
    if banded:
        ik.course(length)


def works_door(rng, length, storeys=3):
    """A hall's door bay, as tall as the hall: a sectional door with a row of panes under a red crane beam and its
    hoist, striped guard blocks at its jambs, a lantern on each pier, a clerestory strip under the eave."""
    x0, x1, top, height = 3.6, length-3.6, 30.0, storeys*LEVEL
    high = height-13.4, height-4.6
    facade('wall', [(x0, x1, 0, top), (x0, x1, *high)], PLINTH, height-1.2, length, ik.WALL, du=12, dv=9, key=STONE)
    for a, b, inner in ((0, PIER, 'l'), (length-PIER, length, 'r')):
        cuboid('pier', a, b, -PIER_OUT, 0, PLINTH, height-1.2, STONE, PIER_TONE, omit='bkt'+inner)
        cuboid('pier foot', a, b, -PIER_OUT-.3, 0, 0, PLINTH, CAST, GRANITE, omit='bk'+inner)
        ik.lantern((a+b)/2, 10.0, -PIER_OUT)
    cuboid('course', 0, length, -PIER_OUT-.4, 0, height-1.2, height, STONE, COURSE_TONE, omit='klr')
    ik.plinth(length, [(x0, x1)])
    recess('works door', x0, x1, 0, top, 1.0, DARK, PAINT)
    add('door leaf', k.SECTIONAL, (.52, .54, .56), [(x0, .94, 0), (x1, .94, 0), (x1, .94, top), (x0, .94, top)], [(0, 1, 2, 3)])
    panes = max(2, round((x1-x0)/7))
    for i in range(panes):
        a = x0+(x1-x0)*(i+.5)/panes
        add('door pane', h.DARK_GLASS, k.GLAZING, [(a-2, .88, 8.4), (a+2, .88, 8.4), (a+2, .88, 10.4), (a-2, .88, 10.4)], [(0, 1, 2, 3)], light='off')
    for a in (x0-4.4, x1+.4):
        cuboid('door guard', a, a+4, -PIER_OUT-1.4, 0, 0, 7.0, HAZARD, (1, 1, 1), omit='bk')
    mid = (x0+x1)/2
    cuboid('crane beam', x0-1.6, x1+1.6, -2.4, 0, top+.8, top+3.0, PAINT, LACQUER, omit='k')
    for a in (x0+2, x1-2):
        cuboid('crane bracket', a-.9, a+.9, -2.6, 0, top-.2, top+.8, PAINT, LACQUER, omit='k', detail=True)
    cuboid('crane hoist', mid-1.5, mid+1.5, -2.7, -.3, top-1.2, top+.8, PAINT, (.84, .66, .16))
    cuboid('crane hook', mid-.14, mid+.14, -1.6, -1.3, top-3.8, top-1.2, PAINT, DARK, detail=True)
    ik.window('clerestory', x0, x1, *high, rng, max(1, round((x1-x0)/3.4)), transom=0)
    back_wall(length, 0, height)


def piece(kind, base, rng, length):
    """The kit's bay of kind as a builder, `length` wide: a kit bay, an entrance (the kit's width), a tower's face of
    glass, a stretch of pier, a hall door, or nothing where another block stands."""
    if kind in ik.BAYS:
        return lambda: ik.bay(rng, kind, base, length)
    if kind in ('entrance', 'entrance-med', 'portal'):
        assert abs(length-W) < 1e-6, (kind, length)
    return {'curtain': lambda: ik.curtain(rng, base, length), 'tower': lambda: ik.curtain(rng, False, length, pier=4.4, banded=False),
            'red-window': lambda: ik.red_window(rng, length), 'red-balcony': lambda: ik.balcony(rng, length),
            'shop': lambda: ik.shop(rng, 'narrow', length), 'shop-wide': lambda: ik.shop(rng, 'wide', length),
            'shop-door': lambda: ik.shop(rng, 'door', length), 'service': lambda: ik.service(rng, length),
            'entrance': lambda: ik.entrance(rng, 'plain'), 'entrance-med': lambda: ik.entrance(rng, 'med'),
            'portal': lambda: ik.entrance(rng, 'plain', canopied=False), 'pier': lambda: fill(length, base),
            'works-door': lambda: works_door(rng, length), 'skip': lambda: None}[kind]


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
    widths, and at each end that is a corner the pier carried on past it: a lacquer column where `red` says so for that
    end, else where the wall's own end bay stands between columns."""
    along, length = f.unit(p, q), math.dist(p, q)
    rng = random.Random(seed)
    for storey in range(storeys):
        z = z0+storey*LEVEL*lift
        base = (z0 == 0 and storey == 0) if ground is None else ground and storey == 0
        bays = widths(spec(storey) if callable(spec) else spec, length)
        at = 0.0
        for kind, width in bays:
            f.lay(piece(kind, base, rng, width), (p[0]+along[0]*at, p[1]+along[1]*at), along, z, 1.0, keeps, lift)
            at += width
        for end, (kind, _) in enumerate((bays[0], bays[-1])):
            if corners[end] and kind != 'skip':
                start = (p[0]-along[0]*EXTEND, p[1]-along[1]*EXTEND) if end == 0 else q
                column = kind in RED if red is None else red[end]
                f.lay(lambda: fill(EXTEND, base, column, kind != 'tower'), start, along, z, 1.0, keeps, lift)


def downpipes(p, q, spec, z0, z1):
    """A bronze downpipe on the pier between each two bays of a wall from p to q, from the eave to the ground."""
    along, length = f.unit(p, q), math.dist(p, q)
    nx, ny = f.outward(p, q)
    bays, at = widths(spec, length), 0.0
    for (kind, width), (after, _) in zip(bays, bays[1:]):
        at += width
        if 'skip' in (kind, after):
            continue
        x, y = p[0]+along[0]*at+nx*(PIER_OUT+.45), p[1]+along[1]*at+ny*(PIER_OUT+.45)
        bar('downpipe', [(x, y, z0+.2), (x, y, z1-1.6)], .34, BRONZE, fine=False)
        cuboid('downpipe head', x-.7, x+.7, y-.7, y+.7, z1-2.6, z1-1.6, PAINT, BRONZE, detail=True)


def block(ring, faces, storeys, z0=0.0, hidden=(), butt=(), seed=0, lift=1.0, default='window', ground=None, pipes=()):
    """A box of the building: its outline (counter-clockwise) laid with bays, faces[edge] a spec (see run); edges hidden
    inside another block left out; a wall's end in `butt` (edge, 0 its start or 1 its end) dies square into another
    block's wall (a dict gives the storeys it does so for, from the ground), every other end is a corner, mitred with
    its pier: a lacquer column where either wall's end bay stands between columns. Edges in `pipes` take downpipes."""
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
            keeps, corners, red = [], [not square(i, 0, storey), not square(i, 1, storey)], [kinds[0] in RED, kinds[-1] in RED]
            if corners[0]:
                keeps.append(f.mitre(p, f.outward(ring[before], p), normal, q))
                red[0] = red[0] or before not in hidden and ends(before, storey)[-1] in RED
            if corners[1]:
                keeps.append(f.mitre(q, normal, f.outward(q, ring[(i+2) % n]), p))
                red[1] = red[1] or after not in hidden and ends(after, storey)[0] in RED
            base = (z0 == 0 and storey == 0) if ground is None else bool(ground) and storey == 0
            run(p, q, spec(i, storey), 1, z0+storey*LEVEL*lift, keeps, seed*101+i*7+storey, lift, corners, base, red)
        if i in pipes:
            downpipes(p, q, spec(i, storeys-1), 0.0, z0+storeys*LEVEL*lift)


def volume(name, ring, z0, z1, behind=BEHIND):
    """A building volume kept `behind` its block's walls."""
    inner = f.inset(ring, behind) if behind else ring
    c.volume(name, inner, z0, z1)
    volumes.append((inner, z1))


# -- Roofs ------------------------------------------------------------------------------------------

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


def bar(name, path, radius, colour=BRONZE, fine=True):
    """A thin square bar along a path; fine ones go at the far levels."""
    obj = u.tube(name, path, radius, PAINT, colour, sides=4)
    obj['detail'] = fine
    return obj


def hip(name, eave, z, pitch=.3, top=None, flare=(6.0, .28), lift=2.0, ribs=True, soffit=1.4, level=(), fins=True, omit=()):
    """A hipped seamed roof over a convex outline, `eave` its eave line at z: every side rises at `pitch`, flatter over
    the first flare[0] (at flare[1]); at its corners (but those in `level`) the eave turns up `lift` and runs out to a
    tip; a bronze lip round the eave, its fascia `soffit` tall down to a flat soffit, dark ribs up the hips and along the ridge, a bronze fin at each
    end of a long ridge (one spike on a short one or a point). Sides in `omit` are left out, where another roof's plane
    covers them; `ribs` may name the corners that take one. It closes in a ridge, or stops `top` in from the eave: the
    ring there and its height are returned (for a flat top, a lantern or another tier)."""
    reach = reach_of(eave)
    d_top = min(top, reach) if top is not None else reach
    d_flare = min(flare[0], d_top)
    rise = lambda d: flare[1]*min(d, d_flare)+pitch*max(0.0, d-d_flare)
    n = len(eave)
    mid, z_mid = f.inset(eave, d_flare), z+rise(d_flare)
    upper, z_top = (f.inset(eave, d_top), z+rise(d_top)) if d_top > d_flare+1e-6 else (mid, z_mid)
    # Each lifted corner runs out along its hip: the tip of the eave.
    tips = []
    for i in range(n):
        out = math.dist(eave[i], mid[i]) or 1.0
        reach_out = 0.0 if i in level else lift*.55/out
        tips.append((eave[i][0]+(eave[i][0]-mid[i][0])*reach_out, eave[i][1]+(eave[i][1]-mid[i][1])*reach_out))
    zone, outline = 12.0, []
    for i in range(n):
        j = (i+1) % n
        a, b, length = tips[i], tips[j], math.dist(tips[i], tips[j])
        normal = f.outward(eave[i], eave[j])
        marks = [mark for mark in (2, 5, 9, zone) if mark < length/2]
        stops = sorted({0.0, 1.0, *[mark/length for mark in marks], *[1-mark/length for mark in marks]})
        turned = lambda t: max(0.0 if i in level else lift*max(0.0, 1-t*length/zone)**2,
                               0.0 if j in level else lift*max(0.0, 1-(1-t)*length/zone)**2)
        # Between the tips the eave keeps to its line: only the last stretch runs out to a tip.
        line = lambda t: (eave[i][0]+(eave[j][0]-eave[i][0])*t, eave[i][1]+(eave[j][1]-eave[i][1])*t)
        low = [((a if t == 0 else b if t == 1 else line(t)) + (z+turned(t),)) for t in stops]
        high = [(mid[i][0]+(mid[j][0]-mid[i][0])*t, mid[i][1]+(mid[j][1]-mid[i][1])*t, z_mid) for t in stops]
        outline += [point[:2] for point in low[:-1]]
        if i in omit:
            continue
        for s in range(len(stops)-1):
            p, q = low[s], low[s+1]
            add(name+' roofing', SEAMED, (1, 1, 1), [p, q, high[s+1], high[s]], [(0, 1, 2, 3)])
            # The bronze lip: a fascia from the soffit up past the roofing, its top, and its back down onto the roofing.
            back = [tuple(e[m]+(g[m]-e[m])*.5/d_flare for m in range(3)) for e, g in ((p, high[s]), (q, high[s+1]))]
            facing(name+' eave edge', PAINT, BRONZE, [(*p[:2], z-soffit), (*q[:2], z-soffit), (*q[:2], q[2]+.4), (*p[:2], p[2]+.4)], (*normal, 0))
            facing(name+' eave edge', PAINT, BRONZE, [(*p[:2], p[2]+.4), (*q[:2], q[2]+.4), (*back[1][:2], back[1][2]+.3), (*back[0][:2], back[0][2]+.3)],
                   (0, 0, 1))
            facing(name+' eave edge', PAINT, BRONZE, [(*back[0][:2], back[0][2]+.3), (*back[1][:2], back[1][2]+.3), back[1], back[0]],
                   (-normal[0], -normal[1], 0))
        if upper is not mid:
            quad = distinct([(*mid[i], z_mid), (*mid[j], z_mid), (*upper[j], z_top), (*upper[i], z_top)])
            if len(quad) >= 3:
                add(name+' roofing', SEAMED, (1, 1, 1), quad, [tuple(range(len(quad)))])
    add(name+' soffit', PAINT, SOFFIT, [(x, y, z-soffit) for x, y in outline][::-1], [tuple(range(len(outline)))])
    if ribs is not False:
        for i in range(n) if ribs is True else ribs:
            tip_z = z+(0.0 if i in level else lift)
            path = distinct([(*tips[i], tip_z+.15), (*mid[i], z_mid+.15), (*upper[i], z_top+.15)])
            bar(name+' hip rib', path, .32, RIB, fine=False)
        ridge = distinct([(*p, z_top+.15) for p in upper])
        if len(ridge) == 2:
            bar(name+' ridge', ridge, .4, RIB, fine=False)
            if fins and math.dist(ridge[0], ridge[1]) >= 12:
                for end, other in ((ridge[0], ridge[1]), (ridge[1], ridge[0])):
                    fin(name, end, f.unit(other[:2], end[:2]))
            elif fins:
                spike(name, tuple((ridge[0][m]+ridge[1][m])/2 for m in range(3)))
        elif len(ridge) == 1 and fins:
            spike(name, ridge[0])
    return upper, z_top


def fin(name, end, way, length=2.8, height=2.2, half=.3):
    """A bronze fin at a ridge's end, swept up and out along `way`: the ridge's finial, kept abstract."""
    x, y, z = end
    wx, wy = way
    px, py = -wy*half, wx*half
    profile = [(-length*.6, 0.0), (length*.4, 0.0), (length*.75, height), (length*.3, height*.5)]
    sides = [[(x+wx*a+px*side, y+wy*a+py*side, z+b) for a, b in profile] for side in (1, -1)]
    facing(name+' finial', PAINT, BRONZE, sides[0], (px, py, 0))
    facing(name+' finial', PAINT, BRONZE, sides[1], (-px, -py, 0))
    centre = (sum(a for a, _ in profile)/4, sum(b for _, b in profile)/4)
    for i in range(4):
        j = (i+1) % 4
        (a0, b0), (a1, b1) = profile[i], profile[j]
        out = ((a0+a1)/2-centre[0], (b0+b1)/2-centre[1])
        facing(name+' finial', PAINT, BRONZE, [sides[0][i], sides[0][j], sides[1][j], sides[1][i]], (wx*out[0], wy*out[0], out[1]))


def spike(name, at, height=2.6, half=.9):
    """A squat bronze cap on a roof's point."""
    x, y, z = at
    ring = [(x+dx, y+dy, z) for dx, dy in ((half, half), (-half, half), (-half, -half), (half, -half))]
    add(name+' finial', PAINT, BRONZE, ring+[(x, y, z+height)], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)])


def under(z, over=5.0, flare=(6.0, .28)):
    """The eave height of a roof whose eaves stand `over` past walls z tall: its roofing clears the walls' top course,
    which stands out of them, by a hand."""
    return z+.4+flare[1]*(PIER_OUT+.4)-flare[1]*min(over, flare[0])


def roof(name, ring, z, over=6.0, **more):
    """A hipped roof over walls: `ring` their line, z their top; its eaves `over` past them."""
    return hip(name, f.inset(ring, -over), under(z, over, more.get('flare', (6.0, .28))), **more)


def flat_top(name, ring, z, sink=.3, cap=1.0, colour=DECK_TONE):
    """A truncated roof's top: a bronze-capped curb round a deck of pavers. Gives the deck's outline and height."""
    inner = f.inset(ring, cap)
    f.frustum(name+' curb cap', ring, z, inner, z, PAINT, BRONZE)
    for i in range(len(inner)):
        (ax, ay), (bx, by) = inner[i], inner[(i+1) % len(inner)]
        add(name+' curb', PAINT, DARK, [(bx, by, z-sink), (ax, ay, z-sink), (ax, ay, z), (bx, by, z)], [(0, 1, 2, 3)])
    f.cap(name+' deck', inner, z-sink, PAVERS, colour)
    return inner, z-sink


def roof_lantern(name, ring, z, wall=4.6, rise=3.0, lit='dim'):
    """A lantern of glass on a roof: upright panes in bronze frames under a hipped glass roof with its glazing bars, lit
    from below at night; `ring` its outline, z its foot (inside the roof it stands on)."""
    f.wall_ring(name+' glass', ring, z, z+wall, PALE_GLASS, PALE_PANE, light=lit)
    f.wall_ring(name+' frame', f.inset(ring, -.15), z+wall-.7, z+wall, PAINT, BRONZE)
    eave = f.inset(ring, -.8)
    upper = f.inset(eave, reach_of(eave))
    n = len(eave)
    for i in range(n):
        j = (i+1) % n
        low, high = [(*eave[i], z+wall), (*eave[j], z+wall)], [(*upper[i], z+wall+rise), (*upper[j], z+wall+rise)]
        quad = distinct([low[0], low[1], high[1], high[0]])
        if len(quad) >= 3:
            add(name+' glass', PALE_GLASS, PALE_PANE, quad, [tuple(range(len(quad)))], light=lit)
        (ax, ay), (bx, by) = eave[i], eave[j]
        nx, ny = f.outward(eave[i], eave[j])
        facing(name+' frame', PAINT, BRONZE, [(ax, ay, z+wall-.4), (bx, by, z+wall-.4), (bx, by, z+wall+.1), (ax, ay, z+wall+.1)], (nx, ny, 0))
        bar(name+' hip bar', distinct([(*eave[i], z+wall+.12), (*upper[i], z+wall+rise+.12)]), .22, BRONZE, fine=False)
        count = max(1, round(math.dist(ring[i], ring[j])/6))
        for s in range(1, count):
            t = s/count
            x, y = ring[i][0]+(ring[j][0]-ring[i][0])*t, ring[i][1]+(ring[j][1]-ring[i][1])*t
            bar(name+' mullion', [(x+nx*.1, y+ny*.1, z), (x+nx*.1, y+ny*.1, z+wall)], .16, DARK)
            foot, head = [tuple(a[m]+(b[m]-a[m])*t for m in range(3)) for a, b in ((low[0], low[1]), (high[0], high[1]))]
            if math.dist(foot, head) > 1:
                bar(name+' glazing bar', [(foot[0], foot[1], foot[2]+.1), (head[0], head[1], head[2]+.1)], .14, DARK)
    for i in range(n):
        j = (i+1) % n
        facing(name+' soffit', PAINT, SOFFIT, [(*eave[i], z+wall-.4), (*eave[j], z+wall-.4), (*ring[j], z+wall-.4), (*ring[i], z+wall-.4)], (0, 0, -1))
    ridge = distinct([(*p, z+wall+rise+.12) for p in upper])
    if len(ridge) == 2:
        bar(name+' ridge', ridge, .28, BRONZE, fine=False)


def screen(name, ring, z, height=5.0, units=()):
    """Roof plant behind a louvred screen: a pale box of louvres standing on the deck, a steel rim on it, and fan units
    at (x, y, half length, half width)."""
    inner = f.inset(ring, .3)
    f.wall_ring(name+' screen', ring, z, z+height, SLATS, PALE_LOUVRE)
    for i in range(len(inner)):
        (ax, ay), (bx, by) = inner[i], inner[(i+1) % len(inner)]
        add(name+' screen back', PAINT, (.50, .51, .51), [(bx, by, z), (ax, ay, z), (ax, ay, z+height), (bx, by, z+height)], [(0, 1, 2, 3)])
    f.frustum(name+' screen rim', f.inset(ring, -.15), z+height, inner, z+height, PAINT, (.78, .79, .78))
    f.cap(name+' plant deck', inner, z+.25, PAINT, (.45, .46, .46))
    for x, y, a, b in units:
        cuboid(name+' unit', x-a, x+a, y-b, y+b, z+.25, z+height-.8, PAINT, (.72, .73, .72), omit='b')
        for fan in ((-a/2,), (a/2,)) if a > 2*b*.8 else ((0,),):
            disc(name+' fan', x+fan[0], y, z+height-.75, min(a/2, b)*.72, 'z', h.GRILLE, (.62, .64, .66), 12)


# -- Parts ------------------------------------------------------------------------------------------

def column(x, y, z0, z1, radius=3.0, foot=5.5):
    """A round lacquer column on a granite foot, bronze at its base and head."""
    cuboid('column foot', x-radius*1.45, x+radius*1.45, y-radius*1.45, y+radius*1.45, z0, z0+foot, CAST, GRANITE, omit='b')
    round_prism('column collar', x, y, z0+foot, z0+foot+1.0, radius*1.2, PAINT, BRONZE, 12)
    round_prism('column', x, y, z0+foot+1.0, z1-1.6, radius, PAINT, LACQUER, 12)
    round_prism('column head', x, y, z1-1.6, z1, radius*1.25, PAINT, BRONZE, 12)


def post(x, y, z0, z1, half=1.2, foot=4.0, brackets=None):
    """A square lacquer post on a granite foot; with `brackets` (a unit way along its beam), a bracket arm under the
    beam on both sides."""
    cuboid('post foot', x-half*1.45, x+half*1.45, y-half*1.45, y+half*1.45, z0, z0+foot, CAST, GRANITE, omit='b')
    cuboid('post', x-half, x+half, y-half, y+half, z0+foot, z1, PAINT, LACQUER, omit='bt')
    if brackets:
        wx, wy = brackets
        thin = half*.6
        for way in (-1, 1):
            a, b = (x+way*wx*half, y+way*wy*half), (x+way*wx*(half+3.2), y+way*wy*(half+3.2))
            cuboid('post bracket', min(a[0], b[0])-abs(wy)*thin, max(a[0], b[0])+abs(wy)*thin, min(a[1], b[1])-abs(wx)*thin,
                   max(a[1], b[1])+abs(wx)*thin, z1-2.4, z1, PAINT, LACQUER, omit='t')


def steps(x0, x1, y0, y1, z, count):
    """Stone steps from the ground at y0 up to z at y1 (towards +y)."""
    tread, riser = (y1-y0)/count, z/count
    for i in range(count):
        cuboid('step', x0, x1, y0+i*tread, y1, i*riser, (i+1)*riser, STONE, COURSE_TONE, omit='bk')


def paving(x0, x1, y0, y1, z=.4, colour=COURSE_TONE):
    """A stone apron."""
    cuboid('paving', x0, x1, y0, y1, 0, z, STONE, colour, omit='b')


def boxwood(x, y, z, size, rng):
    """A clipped ball of boxwood."""
    u.lump(x, y, z, size, size*.8, BOXWOOD, rng, sides=7)


def planter(x0, x1, y0, y1, z, rng, height=2.6, size=3.6):
    """A stone planter of clipped boxwood: four walls round sunk soil."""
    for a0, a1, b0, b1 in ((x0, x1, y0, y0+.5), (x0, x1, y1-.5, y1), (x0, x0+.5, y0+.5, y1-.5), (x1-.5, x1, y0+.5, y1-.5)):
        cuboid('planter', a0, a1, b0, b1, z, z+height, STONE, COURSE_TONE, omit='b')
    deck('planter soil', x0+.5, x1-.5, y0+.5, y1-.5, z+height-.5, h.SOIL, (.24, .22, .18))
    along_x = x1-x0 >= y1-y0
    length, across = (x1-x0, y1-y0) if along_x else (y1-y0, x1-x0)
    count = max(1, round((length-1)/(size*.95)))
    for i in range(count):
        t = (i+.5)/count
        px, py = (x0+length*t, (y0+y1)/2) if along_x else ((x0+x1)/2, y0+length*t)
        boxwood(px, py, z+height-.7, min(size, across-.8)*rng.uniform(.9, 1.08), rng)


def handrail(a, b, height=3.2, posts=3):
    """A bronze handrail from a to b (points on the ground or the stairs)."""
    bar('handrail', [(a[0], a[1], a[2]+height), (b[0], b[1], b[2]+height)], .22, BRONZE, fine=False)
    for i in range(posts):
        t = i/(posts-1)
        x, y, z = (a[m]+(b[m]-a[m])*t for m in range(3))
        bar('handrail post', [(x, y, z), (x, y, z+height)], .16, BRONZE)


def stone_lantern(x, y, z=0.0):
    """A stone lantern, kept abstract: a foot, a shaft, a softly lit box under a wide granite cap."""
    cuboid('stone lantern', x-1.8, x+1.8, y-1.8, y+1.8, z, z+1.4, STONE, COURSE_TONE, omit='b')
    cuboid('stone lantern', x-.85, x+.85, y-.85, y+.85, z+1.4, z+4.6, STONE, COURSE_TONE, omit='bt')
    cuboid('stone lantern light', x-1.4, x+1.4, y-1.4, y+1.4, z+4.6, z+7.0, PAINT, ik.LANTERN, omit='bt', light=(.55, .40, .20))
    cap = [(x-2.7, y-2.7, z+7.0), (x+2.7, y-2.7, z+7.0), (x+2.7, y+2.7, z+7.0), (x-2.7, y+2.7, z+7.0), (x, y, z+9.2)]
    add('stone lantern cap', CAST, GRANITE, cap, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)])


def gate(x0, x1, y, height=15.0, half=1.1):
    """A roofed lacquer gate across x at y: two posts on granite feet, a beam between them and one over them, under a
    small hipped seamed roof with its bronze lip. A civic gate in the buildings' own forms."""
    for x in (x0, x1):
        post(x, y, 0, height, half=half, foot=3.0)
    cuboid('gate tie', x0+half, x1-half, y-half*.6, y+half*.6, height-4.6, height-3.2, PAINT, LACQUER, omit='lr')
    cuboid('gate beam', x0-half-1.2, x1+half+1.2, y-half*.9, y+half*.9, height, height+1.6, PAINT, LACQUER)
    hip('gate roof', f.rect(x0-4.5, x1+4.5, y-4.4, y+4.4), height+1.9, pitch=.42, flare=(2.0, .22), lift=1.0, fins=False, soffit=.6)


def porch(x0, x1, y0, y1, z, rise=.28):
    """A porch against a wall at y1: a hipped seamed roof whose ridge lies on the wall, on two lacquer posts and a beam
    at its front."""
    depth = y1-y0
    hip('porch', f.rect(x0, x1, y0, y1+depth), z, pitch=rise, flare=(3.0, .2), lift=1.2, fins=False, level=(2, 3))
    for x in (x0+3.4, x1-3.4):
        post(x, y0+3.4, 0, z-2.8)
    cuboid('porch beam', x0+1.6, x1-1.6, y0+2.4, y0+4.4, z-2.8, z-1.3, PAINT, LACQUER, omit='')


def great_portal(cx, y, rng, width=30.0, height=33.0, depth=5.0, top=2*LEVEL):
    """A two-storey entrance in a south wall at y: a lacquer frame of two posts and a beam to the eave, glass doors and
    the hall's lit glass deep in it, a lantern either side."""
    def build():
        inner = (3.0, width-3.0)
        recess('great portal', *inner, 0, height-3.4, depth, PIER_TONE, STONE)
        for a, b in ((0, 3), (width-3, width)):
            cuboid('portal post', a, b, -1.8, .6, 0, height-3.4, PAINT, LACQUER, omit='b')
        cuboid('portal beam', -.8, width+.8, -2.1, .6, height-3.4, height, PAINT, LACQUER)
        cuboid('portal head', 0, width, -PIER_OUT-.4, 0, height, top, STONE, COURSE_TONE, omit='bk')
        back, span = depth-.06, inner[1]-inner[0]
        for i in range(4):
            a, b = inner[0]+span*i/4+.12, inner[0]+span*(i+1)/4-.12
            ik.pane('portal glass', a, b, .5, 9.4, back, True)
            ik.pane('portal glass', a, b, 10.0, height-3.9, back, rng.random() < .75)
        k.mullions('portal', *inner, .5, height-3.9, depth-.1, 4, DARK, PAINT)
        cuboid('portal rail', *inner, depth-.3, depth-.05, 9.4, 10.0, PAINT, DARK, omit='bk', detail=True)
        for x in (-2.6, width+2.6):
            ik.lantern(x, 7.0, -PIER_OUT)
        back_wall(width, 0, top, depth+.1)
    f.lay(build, (cx-width/2, y), (1, 0))


# -- Commercial Center: one hall of shops behind a lacquer arcade (3 hexes) ----------------------------

def commercial_center():
    """Five shop bays, the market's doors in the wide middle one, behind an arcade of six free lacquer columns under the
    roof's deep front eave; stone sides and back with their service bays; a hipped roof up to a long lantern of glass."""
    rng = random.Random(6)
    x0, x1, y0, y1, top = -76.0, 76.0, -20.0, 62.0, 2*LEVEL
    ring = f.rect(x0, x1, y0, y1)
    front = lambda side, middle: [(side, 28), (side, 28), (middle, 40), (side, 28), (side, 28)]
    faces = {
        0: lambda s: front('shop', 'shop-door') if s == 0 else front('red-window', 'red-window'),
        1: lambda s: [('window', 27), ('window', 27), ('service' if s == 0 else 'louvre', 28)],
        2: lambda s: ['service', 'panel', 'window', 'window', 'panel', 'service'] if s == 0 else ['louvre', 'window', 'window', 'window', 'window', 'louvre'],
        3: lambda s: [('service' if s == 0 else 'louvre', 28), ('window', 27), ('window', 27)],
    }
    block(ring, faces, 2, seed=1)
    # The arcade: free columns 10 in front of the shops, a beam on them, the roof's eave over them.
    arcade = y0-10
    for x in (x0+2.1, -48, -20, 20, 48, x1-2.1):
        post(x, arcade, .4, top-3.4, half=2.1, foot=5.5)
        ik.lantern(x, 9.0, arcade-2.1)
    cuboid('arcade beam', x0, x1, arcade-1.3, arcade+1.3, top-3.4, top-1.4, PAINT, LACQUER, omit='')
    upper, z = hip('roof', f.rect(x0-6, x1+6, arcade-5, y1+6), under(top, 6), pitch=.3, top=39)
    inner, z_deck = flat_top('roof top', upper, z)
    roof_lantern('lantern', f.inset(inner, 1.6), z_deck-.2, wall=5.4, rise=3.4)
    paving(x0-6, x1+6, arcade-12, y0)
    for x in (-39, -11, 28):
        planter(x, x+10, arcade-9, arcade-4.5, .4, rng)
    for x in (-24, 24):
        stone_lantern(x, arcade-9, .4)
    h.fixtures.append((0, y0-6, 12))
    volume('hall', ring, 0, top)


# -- Industrial Works: two halls side by side, a plant tower, an entry pavilion (4 hexes) ---------------

def industrial_works():
    """Two halls three storeys tall under hipped roofs with a lantern along each ridge, a door bay each in front;
    louvres and clerestories down the sides; a plant tower at the back corner, its louvred head over the roofs; a small
    hipped entry pavilion at the front corner, clear of the doors."""
    rng = random.Random(7)
    x0, x1, y0, y1, storeys = -41.0, 104.0, -24.0, 126.0, 3
    top, mid = storeys*LEVEL, (x0+x1)/2
    ring = f.rect(x0, x1, y0, y1)
    narrow = lambda s: 'slot' if s < 2 else 'louvre'
    door = lambda s: 'works-door' if s == 0 else 'skip'
    side = lambda s: [('service', 37.5), 'panel', 'panel', ('service', 37.5)] if s == 0 else ['louvre']*4 if s == 1 else ['clerestory']*4
    faces = {
        0: lambda s: [(narrow(s), 12), (door(s), 46), (narrow(s), 14.5), (narrow(s), 12), (door(s), 46), (narrow(s), 14.5)],
        1: side,
        2: lambda s: (['panel', 'service', 'panel', 'service'] if s == 0 else ['panel', 'louvre', 'louvre', 'panel'] if s == 1
                      else ['clerestory']*4)+[('skip', 28)],
        3: lambda s: [('skip', 28)]+(['panel', 'service', 'panel'] if s == 0 else ['louvre', 'panel', 'louvre'] if s == 1 else ['clerestory']*3),
    }
    block(ring, faces, storeys, seed=2, pipes={1})
    for name, a, b, level in (('west hall', x0-6, mid, (1, 2)), ('east hall', mid, x1+6, (0, 3))):
        # Each roof runs on under the other's first slope: they meet in a valley over the halls' shared line.
        lap = 6 if a < mid else -6
        _, z = hip(name, f.rect(min(a, a+min(lap, 0)), max(b, b+max(lap, 0)), y0-6, y1+6), under(top, 6), pitch=.3, level=level)
        cx = (a+b)/2
        roof_lantern(name+' lantern', f.rect(cx-6, cx+6, y0+36, y1-36), z-2.2, wall=4.8, rise=2.8)
    # The plant tower at the back, west corner, 6 proud of both walls: the eaves die into it.
    tower, lift = f.rect(x0-6, x0+28, y1-28, y1+6), 1.2
    # Its faces over the halls start above their roofs; the 6 of them outside the halls' walls stand from the ground.
    over_halls = lambda s: 'panel' if s == 2 else 'grille'
    outer_face = lambda s: 'grille' if s == 3 else 'panel'
    block(tower, {0: lambda s: [('pier', 6), ('skip', 28)] if s < 2 else over_halls(s),
                  1: lambda s: [('skip', 28), ('pier', 6)] if s < 2 else over_halls(s), 2: outer_face, 3: outer_face}, 4, seed=3, lift=lift)
    ring_top, z = hip('tower eave', f.inset(tower, -3), 4*LEVEL*lift-.6, top=7, flare=(3.0, .25), lift=1.2)
    _, z_deck = flat_top('tower top', ring_top, z)
    cx, cy = x0+11, y1-11
    screen('tower plant', f.rect(cx-9, cx+9, cy-9, cy+9), z_deck, 4.4, [(cx, cy, 6.5, 5)])
    # The entry pavilion at the front, east corner, clear of the door.
    pavilion = f.rect(92, 122, y0-26, y0)
    block(pavilion, {0: [('pier', 3), ('portal', W), ('pier', 3)], 1: ['window'], 3: ['window']}, 1, hidden={2}, seed=4)
    roof('pavilion', pavilion, LEVEL, over=4, pitch=.45, flare=(4.0, .25))
    paving(x0-4, x1+22, y0-32, y0, colour=(.80, .79, .77))
    for x in (87.5, 123):
        planter(x, x+3.6, y0-32, y0-27, .4, rng, size=3.0)
    h.fixtures.extend([((x0+mid)/2-4, y0-8, 24), ((mid+x1)/2-8, y0-8, 24), (107, y0-32, 10)])
    volume('halls', ring, 0, top)
    volume('tower', tower, 0, 4*LEVEL)  # Level-aligned: its taller storeys lift the walls, not the floors.
    volume('pavilion', pavilion, 0, LEVEL)


# -- Administrative Offices: an octagonal tower on a podium (4 hexes) ----------------------------------

def administrative_offices():
    """A two-storey podium, a lobby of tall glass under a low eave, its entrance under a hipped porch on two lacquer
    posts; behind its middle the tower, six storeys of glass running on between broad stone piers at its corners, under
    a hipped crown with the plant on top."""
    rng = random.Random(8)
    x0, x1, y0, y1, top = -72.0, 72.0, -96.0, 36.0, 2*LEVEL
    podium = f.rect(x0, x1, y0, y1)
    faces = {
        0: lambda s: ([('curtain', 24), ('curtain', 24), ('curtain', 12), ('portal', W), ('curtain', 12), ('curtain', 24), ('curtain', 24)] if s == 0
                      else [('window', 24), ('window', 24), ('ribbon', 48), ('window', 24), ('window', 24)]),
        1: lambda s: ['curtain', 'window', 'service', 'louvre'] if s == 0 else ['window', 'window', 'pair', 'louvre'],
        2: lambda s: ['service', 'panel', 'louvre', 'louvre', 'panel', 'service'] if s == 0 else ['pair', 'window', 'pair', 'pair', 'window', 'pair'],
        3: lambda s: ['louvre', 'service', 'window', 'curtain'] if s == 0 else ['louvre', 'pair', 'window', 'window'],
    }
    block(podium, faces, 2, seed=5)
    # The podium's roof: a low seamed eave round a deck of pavers.
    upper, z = roof('podium eave', podium, top, over=5, top=13, pitch=.34)
    _, z_deck = flat_top('podium', upper, z)
    for way in (-1, 1):
        roof_lantern('podium monitor %d' % way, f.rect(*sorted((way*50, way*60)), -78, -44), z_deck-.2, wall=2.6, rise=2.4)
    apothem, cy, storeys = 44.0, -10.0, 6
    tower = f.regular(0, cy, apothem/math.cos(math.pi/8), 8, 22.5)
    block(tower, {}, storeys, z0=top, seed=6, default='tower')
    crown = top+storeys*LEVEL
    upper, z = roof('crown', tower, crown, over=8, pitch=.55, top=29, lift=2.4)
    inner, z_deck = flat_top('crown top', upper, z)
    screen('crown plant', f.inset(inner, 4.0), z_deck, 5.0, [(-6, cy, 4.5, 6), (6, cy, 4.5, 6)])
    # The porch over the entrance, its landing, step, planters and stone lanterns.
    porch(-34, 34, y0-20, y0, 14.2)
    cuboid('landing', -34, 34, y0-20, y0, 0, .45, STONE, COURSE_TONE, omit='b')
    cuboid('landing step', -30, 30, y0-22.5, y0-20, 0, .22, STONE, COURSE_TONE, omit='b')
    for side in (-1, 1):
        planter(*sorted((side*35, side*46)), y0-17, y0-10, 0, rng)
        stone_lantern(side*27, y0-26)
    h.fixtures.append((0, y0-12, 11))
    volume('podium', podium, 0, top)
    volume('tower', tower, 0, crown)


# -- Medical Center: a main block and two wings round a court (5 hexes) --------------------------------

def medical_center():
    """The main block, three storeys of wards either side of a glazed atrium between lacquer pilasters; two long wings
    forward of it, two storeys, round a broad court with planters, a pool and a gate at its mouth; hipped roofs, the
    plant in pale screens along their ridges; the emergency entrance under a hipped porch at the east wing's end."""
    rng = random.Random(9)
    x0, x1, y0, y1, w0 = -94.0, 94.0, 22.0, 78.0, 44.0
    main = f.rect(x0, x1, y0, y1)
    atrium = lambda s: ([('window', 14), ('curtain', 18), ('portal', W), ('curtain', 18), ('window', 14)] if s == 0
                        else [('window', 14), ('curtain', 60), ('window', 14)])
    faces = {
        0: lambda s: ([('skip', 50)]+atrium(s)+[('skip', 50)] if s < 2 else ['window', 'window']+atrium(s)+['window', 'window']),
        1: lambda s: ['window', 'service' if s == 0 else 'louvre'],
        2: lambda s: ['service', 'window', 'window', 'panel', 'window', 'window', 'service'] if s == 0 else ['window']*7,
        3: lambda s: ['service' if s == 0 else 'louvre', 'window'],
    }
    # Its side walls run on into the wings' outer walls.
    block(main, faces, 3, butt={(1, 0): 2, (3, 1): 2}, seed=7, pipes={1, 2, 3})
    for storey in range(3):
        cuboid('atrium floor line', -27, 27, y0-.5, y0+.2, storey*LEVEL+8.6, storey*LEVEL+9.6, PAINT, ik.LANTERN, omit='bk', light='night')
    for side in (-1, 1):
        cuboid('atrium pilaster', side*30-1.6, side*30+1.6, y0-2.2, y0, 0, 3*LEVEL, PAINT, LACQUER, omit='bk')
        wing = f.rect(*sorted((side*w0, side*94)), -72, y0)
        front = lambda s, side=side: [('pier', 13), ('portal', W), ('pier', 13)] if s == 0 and side > 0 else ['window']
        block(wing, {0: front, 1: ['window']*3, 3: ['window']*3}, 2, hidden={2}, butt={(1, 1), (3, 0)}, seed=8+side)
        upper, z = hip('wing %d' % side, f.rect(*sorted((side*(w0-6), side*100)), -78, y0+12), under(2*LEVEL, 6), top=22, level=(2, 3))
        inner, z_deck = flat_top('wing %d top' % side, upper, z)
        cx = side*(w0+94)/2
        screen('wing %d plant' % side, f.rect(cx-6, cx+6, -52, -6), z_deck, 5.0, [(cx, -42, 4.2, 6), (cx, -27, 4.2, 6), (cx, -13, 4.2, 5)])
        volume('wing %d' % side, wing, 0, 2*LEVEL)
        planter(*sorted((side*22, side*29)), -62, -8, .3, rng, size=4.2)
        stone_lantern(side*25.5, -67, .3)
    upper, z = roof('main roof', main, 3*LEVEL, top=27)
    inner, z_deck = flat_top('main roof top', upper, z)
    screen('main plant', f.rect(-40, 28, 44.5, 55.5), z_deck, 5.4, [(-29, 50, 8, 4), (-8, 50, 8, 4), (14, 50, 8, 4)])
    # The court: paving, a pool in a kerb between the planters.
    paving(-w0, w0, -72, y0, .3)
    for a0, a1, b0, b1 in ((-8, 8, -64, -63), (-8, 8, -11, -10), (-8, -7, -63, -11), (7, 8, -63, -11)):
        cuboid('pool kerb', a0, a1, b0, b1, .3, 1.1, STONE, COURSE_TONE, omit='b')
    deck('pool water', -7, 7, -63, -11, .7, PALE_GLASS, (.34, .46, .46), light='off')
    # The emergency entrance: a hipped porch and the lit cross.
    cx = (w0+94)/2
    porch(cx-17, cx+17, -72-11, -72, 14.2)
    cuboid('med sign', cx+19, cx+23.4, -72.5, -72, 6.4, 10.8, PAINT, ik.TEAL, omit='bk', light=(.10, .55, .50))
    for a0, a1, b0, b1 in ((cx+19.8, cx+22.6, 8.1, 9.1), (cx+20.7, cx+21.7, 7.2, 10.0)):
        add('med cross', PAINT, (.92, .92, .88), [(a0, -72.56, b0), (a1, -72.56, b0), (a1, -72.56, b1), (a0, -72.56, b1)], [(0, 1, 2, 3)],
            light=(.80, .80, .74))
    paving(x0-4, x1+4, -92, -72, .3, (.80, .79, .77))
    gate(-15, 15, -78)
    h.fixtures.extend([(0, y0-8, 11), (cx, -80, 11)])
    volume('main', main, 0, 3*LEVEL)


# -- Courtyard Habitat: a tall block behind a court (8 hexes) -----------------------------------------

def courtyard_habitat():
    """The rear block, three storeys of loggias between lacquer columns; in front of it a court of lawns and boxwood
    inside two-storey ranges under one hipped roof (two sides and the front), their galleries open to the court, deep
    enough that every hex they stand in is the building's; a roofed walk on lacquer posts down the court's middle; the
    entrance a two-storey lacquer portal under its own hipped roof, a roofed gate on the path to it."""
    rng = random.Random(10)
    x0, x1, y0, y1, low, deep = -98.0, 98.0, -6.0, 54.0, 2*LEVEL, 46.0  # Past the ranges' eaves: they die into its front.
    rear = f.rect(x0, x1, y0, y1)
    court = ['red-balcony', 'pair', 'red-balcony']
    rear_faces = {
        0: lambda s: ([('pier', 6), ('skip', deep)]+court+[('skip', deep), ('pier', 6)] if s < 2
                      else ['pair', 'red-balcony', 'red-balcony', 'pair', 'red-balcony', 'red-balcony', 'pair']),
        1: lambda s: ['pair', 'window'],
        2: lambda s: ['service', 'pair', 'pair', 'window', 'pair', 'pair', 'service'] if s == 0 else ['pair']*7,
        3: lambda s: ['window', 'pair'],
    }
    block(rear, rear_faces, 3, seed=9, pipes={2})
    upper, z = roof('rear roof', rear, 3*LEVEL, top=26, pitch=.34)
    inner, z_deck = flat_top('rear roof top', upper, z)
    for cx in (-44, 44):
        screen('rear plant %d' % cx, f.rect(cx-13, cx+13, 19, 29), z_deck, 4.6, [(cx-6, 24, 5, 3.6), (cx+6.5, 24, 5, 3.6)])
    fy1 = -72.0
    fy0 = fy1-deep
    front = f.rect(-92, 92, fy0, fy1)
    front_faces = {
        0: lambda s: ['pair']*3+[('skip', 30)]+['pair']*3,
        1: ['window', 'window'], 3: ['window', 'window'],
        2: [('skip', deep)]+court+[('skip', deep)],
    }
    block(front, front_faces, 2, butt={(1, 1), (3, 0)}, seed=10)
    # One roof for the U: the ranges are as deep as each other, so the sides' roofs laid from the front eave lie in its
    # planes at the corners. Each plane is drawn once: the front roof keeps its two long slopes, the sides theirs.
    over = 5.0
    eave = under(low, over)
    hip('front roof', f.rect(-92-over, 92+over, fy0-over, fy1+over), eave, level=(2, 3), omit=(1, 3), ribs=(0, 1), fins=False)
    for side in (-1, 1):
        a, b = sorted((side*(92-deep), side*92))
        ring = f.rect(a, b, fy1, y0)
        # Galleries to the court, windows to the street.
        range_faces = {1: ['red-balcony']*2, 3: ['pair']*2} if side < 0 else {1: ['pair']*2, 3: ['red-balcony']*2}
        block(ring, range_faces, 2, hidden={0, 2}, butt={(1, 0), (1, 1), (3, 0), (3, 1)}, seed=11+side)
        hip('range %d roof' % side, f.rect(a-over, b+over, fy0-over, y0+deep), eave, level=(1, 2, 3) if side < 0 else (0, 2, 3),
            omit=(0,), ribs=(), fins=False)
        volume('range %d' % side, ring, 0, low)
    # The walk down the court's middle: a low seamed roof on lacquer posts, from the front range to the rear block.
    walk = LEVEL-2.0
    hip('walk roof', f.rect(-9, 9, fy1-12, y0+12), walk, pitch=.34, flare=(3.0, .22), level=(0, 1, 2, 3), fins=False, soffit=.6)
    for y in (fy1+9, fy1+25, fy1+41, fy1+57):
        for x in (-6.4, 6.4):
            post(x, y, .3, walk-.5, half=.8, foot=2.6)
    volume('walk', f.rect(-9, 9, fy1, y0), LEVEL-1, LEVEL, behind=0)  # Its roof counts for its hex; no floor under it.
    # The entrance: a two-storey lacquer portal in the front range, a cross roof over it, a roofed gate on its path.
    great_portal(0, fy0, rng, width=30.0, height=33.0, top=low)
    hip('entrance roof', f.rect(-21, 21, fy0-9, (fy0+fy1)/2+2), eave+2.2, pitch=.34, flare=(4.0, .24), level=(2, 3), fins=False)
    paving(-26, 26, fy0-34, fy0)
    gate(-13, 13, fy0-27)
    for side in (-1, 1):
        planter(*sorted((side*18, side*29)), fy0-13, fy0-8, .4, rng)
        stone_lantern(side*22, fy0-30, .4)
        # Half the court: pale paving, a lawn in a stone kerb, boxwood at its corners, a stone lantern in its middle.
        a, b = sorted((side*9, side*(92-deep)))
        paving(a, b, fy1, y0, .3, (1, 1, 1))
        cuboid('lawn kerb', a+7, b-7, fy1+12, y0-12, .3, .9, STONE, COURSE_TONE, omit='bt')
        deck('court lawn', a+7, b-7, fy1+12, y0-12, .9, TURF, TURF_TINT)
        for px, py in ((a+10, fy1+15), (b-10, fy1+15), (a+10, y0-15), (b-10, y0-15)):
            for dx, dy in ((0, 0), (3.6, .6), (.8, 3.4)):
                boxwood(px+dx*(1 if px < (a+b)/2 else -1), py+dy*(1 if py < (fy1+y0)/2 else -1), .7, rng.uniform(3.8, 4.8), rng)
        stone_lantern((a+b)/2, (fy1+y0)/2, .9)
    paving(-9, 9, fy1, y0, .3, (1, 1, 1))
    h.fixtures.append((0, fy0-10, 11))
    volume('rear', rear, 0, 3*LEVEL)
    volume('front', front, 0, low)


# -- Government Hall: a colonnaded hall under a two-tier roof, two wings (4 hexes) ---------------------

def government_hall():
    """The hall, four storeys on a granite base: its front six round lacquer columns under a stone lintel between two
    pylons, the glazed wall behind them at the head of a broad stair; a hipped roof stepping up over a band of glass to
    a second, the plant on its top; a two-storey wing either side under its own hipped roof."""
    rng = random.Random(11)
    x0, x1, y0, y1, storeys, base = -62.0, 62.0, -30.0, 78.0, 4, 3.0
    top = base+storeys*LEVEL
    main = f.rect(x0, x1, y0, y1)
    pylon = lambda s: 'slit' if s == 0 else 'slot'
    faces = {
        0: lambda s: [(pylon(s), 20), ('skip', 84), (pylon(s), 20)],
        # The wings stand against the sides' first 72 behind the front: no wall behind them on the ground.
        1: lambda s: ([('pier', 4), ('skip', 72), ('panel', 32)] if s == 0 else [('pier', 4), ('panel', 72), ('panel', 32)] if s == 1
                      else ['slot', 'panel', 'panel', 'slot']),
        2: lambda s: ['service', 'window', 'window', 'window', 'service'] if s == 0 else ['window']*5,
        3: lambda s: ([('panel', 32), ('skip', 72), ('pier', 4)] if s == 0 else [('panel', 32), ('panel', 72), ('pier', 4)] if s == 1
                      else ['slot', 'panel', 'panel', 'slot']),
    }
    block(main, faces, storeys, z0=base, seed=13, ground=True, pipes={1, 2, 3})
    ledge = f.inset(main, -1.6)
    f.wall_ring('base', ledge, 0, base, CAST, GRANITE)
    f.frustum('base', ledge, base, main, base, CAST, GRANITE)
    # The wall behind the columns, 7 back, the pylons' returns to it, and the lintel the columns carry.
    back = y0+7
    run((-42, back), (42, back), lambda s: ['window', 'curtain', 'curtain', 'curtain', 'window'] if s == 0 else ['ribbon']*5, storeys,
        z0=base, seed=14, ground=True)
    for way in (-1, 1):
        quad = [(way*42, y0-PIER_OUT, 0), (way*42, back, 0), (way*42, back, top), (way*42, y0-PIER_OUT, top)]
        add('pylon return', STONE, PIER_TONE, quad if way < 0 else quad[::-1], [(0, 1, 2, 3)])
    cuboid('lintel', -42, 42, y0-1.6, back, top-6.5, top, STONE, COURSE_TONE, omit='k')
    cuboid('lintel line', -42, 42, y0-1.9, y0-1.6, top-7.1, top-6.5, PAINT, BRONZE, omit='k')
    landing = base+PLINTH
    cuboid('landing', -42, 42, y0-8, back, 0, landing, STONE, COURSE_TONE, omit='b')
    for x in (-35, -21, -7, 7, 21, 35):
        column(x, y0+1.5, landing, top-6.5)
        ik.lantern(x, landing+1.4, y0+1.5-4.36)
    steps(-40, 40, y0-34, y0-8, landing, 12)
    for way in (-1, 1):
        a, b = sorted((way*40, way*54))
        cuboid('stair cheek', a, b, y0-21, y0-4, 0, landing, STONE, COURSE_TONE, omit='b')
        cuboid('stair cheek', a, b, y0-36, y0-21, 0, 3.6, STONE, COURSE_TONE, omit='b')
        planter(a+1.5, b-1.5, y0-34.5, y0-23, 3.6, rng, height=1.4)
        handrail((way*13, y0-34, 0), (way*13, y0-8, landing))
        handrail((way*53.6, y0-20.6, landing), (way*53.6, y0-4.4, landing))
        handrail((way*40.4, y0-20.6, landing), (way*53.6, y0-20.6, landing), posts=2)
        stone_lantern(way*47, y0-40)
        h.fixtures.append((way*26, y0-4, landing+10))
    # The roofs: the lower up to a band of glass, the upper over it, the plant on its top.
    upper, z = roof('lower roof', main, top, over=9, pitch=.36, top=31, lift=2.6)
    band = f.inset(upper, 2.0)
    f.cap('band foot', upper, z, PAINT, DARK)
    tall = 13.0
    f.wall_ring('band glass', band, z, z+tall, PALE_GLASS, PALE_PANE, light='dim')
    f.wall_ring('band frame', f.inset(band, -.15), z, z+.9, PAINT, BRONZE)
    for i in range(4):
        (ax, ay), (bx, by) = band[i], band[(i+1) % 4]
        count = max(1, round(math.dist(band[i], band[(i+1) % 4])/7))
        for s in range(count+1):
            x, y = ax+(bx-ax)*s/count, ay+(by-ay)*s/count
            bar('band mullion', [(x, y, z), (x, y, z+tall)], .32, DARK, fine=False)
    upper, z = roof('upper roof', band, z+tall, over=3.5, pitch=.42, top=20, lift=2.0)
    inner, z_deck = flat_top('upper roof top', upper, z)
    cx, cy = (x0+x1)/2, (y0+y1)/2
    screen('roof plant', f.rect(cx-16, cx+16, cy-9, cy+9), z_deck, 5.0, [(cx-8, cy, 6, 6), (cx+8, cy, 6, 6)])
    for way in (-1, 1):
        wing = f.rect(*sorted((way*62, way*122)), -26, 46)
        outer, inner_edge = (3, 1) if way < 0 else (1, 3)
        block(wing, {0: ['window']*3, 2: ['window']*3, outer: ['window']*3}, 2, hidden={inner_edge},
              butt={(0, 1), (2, 0)} if way < 0 else {(0, 0), (2, 1)}, seed=15+way)
        hip('wing %d roof' % way, f.rect(*sorted((way*48, way*128)), -32, 52), under(2*LEVEL, 6), level=(1, 2) if way < 0 else (0, 3))
        volume('wing %d' % way, wing, 0, 2*LEVEL)
    paving(-58, 58, y0-44, y0, .3, (.80, .79, .77))
    volume('hall', main, 0, storeys*LEVEL)  # Level-aligned: its base lifts the walls, not the floors.


# -- Transit Terminal: a station house and a long platform canopy (4 hexes) ----------------------------

def transit_terminal():
    """A platform under a long hipped canopy on lacquer posts with bracket heads, a lantern of glass along its ridge;
    at its front the station house, a tall ground storey and a low one of glass under a two-tier hipped roof, its
    entrance up a few steps, the canopy's first posts flanking its back."""
    deck_z, y_end = 3.0, 256.0
    cuboid('platform', -31, 31, -36, y_end, 0, deck_z-.3, CAST, GRANITE, omit='b')
    cuboid('platform top', -31.4, 31.4, -36.4, y_end+.4, deck_z-.3, deck_z, STONE, COURSE_TONE)
    for side in (-1, 1):
        a, b = sorted((side*28.6, side*30.6))
        cuboid('platform edge', a, b, 14, y_end-1, deck_z, deck_z+.16, PAINT, (.80, .66, .25), omit='b')
    house = f.rect(-24, 24, -36, 12)
    ground = {0: [('slit', 12), ('portal', W), ('slit', 12)], 1: ['window', 'service'], 2: [('panel', 12), ('curtain', W), ('panel', 12)],
              3: ['service', 'window']}
    block(house, ground, 1, z0=deck_z, seed=17, ground=True)
    block(house, {}, 1, z0=deck_z+LEVEL, seed=18, lift=.5, default='ribbon', ground=False)
    eave = deck_z+1.5*LEVEL
    upper, z = roof('house roof', house, eave, over=5, pitch=.26, top=14, lift=1.6)
    tier = f.inset(upper, 1.0)
    f.cap('tier foot', upper, z, PAINT, DARK)
    f.wall_ring('tier', tier, z, z+1.4, PAINT, DARK)
    roof('tier roof', tier, z+1.4, over=3.5, pitch=.26, flare=(3.0, .22), lift=1.0)
    steps(-18, 18, -45, -36, deck_z, 5)
    for side in (-1, 1):
        stone_lantern(side*27, -42)
    # The canopy: posts with bracket heads and a beam down each side, the roof over them, a lantern along its ridge.
    canopy = 2*LEVEL+4
    rows = [2]+[24+36*i for i in range(7)]
    for side in (-1, 1):
        for y in rows:
            post(side*27, y, deck_z, canopy-3.6, half=1.8, foot=6.0, brackets=(0, 1))
        cuboid('canopy beam', side*27-1.3, side*27+1.3, -2, y_end-4, canopy-3.6, canopy-1.6, PAINT, LACQUER, omit='')
    for y in rows[1:]:
        cuboid('canopy tie', -27, 27, y-.8, y+.8, canopy-3.4, canopy-1.9, PAINT, LACQUER, omit='lr', detail=True)
        for x in (-13, 13):
            light = [(x-3, y+17, canopy-2.0), (x-3, y+19, canopy-2.0), (x+3, y+19, canopy-2.0), (x+3, y+17, canopy-2.0)]
            add('canopy light', PAINT, (.95, .88, .70), light, [(0, 1, 2, 3)], light='night')
    _, z = hip('canopy', f.rect(-37, 37, -8, y_end+5), canopy-1.1, pitch=.3, lift=2.4, soffit=.7)
    roof_lantern('canopy lantern', f.rect(-7, 7, 60, 226), z-2.4, wall=5.2, rise=3.0)
    h.fixtures.extend([(0, -42, 12), (0, 80, 28), (0, 170, 28)])
    volume('house', house, 0, LEVEL)
    volume('canopy', f.rect(-31, 31, -36, y_end), 2*LEVEL-1, 2*LEVEL, behind=0)


BUILDINGS = {'administrative-offices': administrative_offices, 'government-hall': government_hall,
             'transit-terminal': transit_terminal, 'medical-center': medical_center, 'courtyard-habitat': courtyard_habitat,
             'commercial-center': commercial_center, 'industrial-works': industrial_works}
FINE = ('mullion', 'transom', 'lantern cap', 'rail', 'sign line', 'glazing bar', 'guard', 'hook', 'bracket', 'fan', 'canopy tie',
        'downpipe head')


def far_piece(obj):
    """Whether a part stays at the farthest level: all but the fine lines and marks."""
    name = re.sub(r'\.\d+$', '', obj.name)
    return not any(word in name for word in FINE)


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


def build_scene(name):
    full = 'imperial-'+name
    h.weathered_material.__defaults__[0].clear()
    shared.fresh(full)
    shared.role = ''
    h.bins.clear()
    h.fixtures.clear()
    volumes.clear()
    h.SHIFT_Y = 0
    u.LOD = 0
    BUILDINGS[name]()
    h.flush()
    u.flush_cards()
    for obj in shared.objects:
        ik.warm(obj)
        if obj.data.uv_layers:
            continue
        if obj['board_material'] == SEAMED:
            ik.roof_uvs(obj)
        elif obj['board_material'] == TURF:
            layer = obj.data.uv_layers.new(name='UVMap')
            for loop in obj.data.loops:
                co = obj.data.vertices[loop.vertex_index].co
                layer.data[loop.index].uv = co.x/LAWN_REPEAT, co.y/LAWN_REPEAT
    for obj in shared.objects:
        if obj['board_material'] == STONE and not obj.get('building_emission') and not obj.get('building_emission_off'):
            obj['building_paint'] = True  # Stone takes a building's tint, as the kit's.
    for obj in shared.volumes:
        obj.hide_set(True)
    bpy.context.view_layer.update()
    for obj in shared.objects:
        shared.project_uvs(obj)
    bpy.context.scene['asset_id'] = 'buildings/authored/'+full
    bpy.context.scene['hex_width'], bpy.context.scene['hex_height'], bpy.context.scene['level_height'] = 83.125, 72, LEVEL
    return full


def build(name):
    full = build_scene(name)
    bpy.context.view_layer.update()
    levels = {i: shared.export_model([obj for obj in shared.objects if i < 2 or far_piece(obj)], f'{full}-lod{i}', level=i, exact=True)
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


if __name__ == '__main__' and '--' in sys.argv:
    args = sys.argv[sys.argv.index('--')+1:]
    build(args[0])
    if len(args) > 1:
        u.sheet(args[0], args[1])
