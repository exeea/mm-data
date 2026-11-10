"""The Heritage authored buildings, built from the modular kit's own bays (heritage_kit) as kit_blocks lays them: the
landmarks the kit cannot stand in for. The parts the kit lacks are modelled here in the same finishes: steep slate roofs
with dormers under copper ridges, gables, towers in stages (tall lancets, a louvred belfry, pinnacles) under slate
spires or battlements, great arched windows with stone mullions between stepped buttresses, glass vaults on iron ribs,
clock faces, stairs and planters; for the cathedral, gabled portals, blind arcades, a rose, flying buttresses. The kit's own roofs (its mansard, parapet and battlement) run round the lower blocks.

Run: blender -b --factory-startup --python heritage_buildings.py -- <name> [sheet folder]
Writes data/models/buildings/authored/heritage-<name>.glb, front (the entrance) to -y. Where a sheet's views disagree,
its ISO view wins. No banners or arms: the sheets' are left out.
"""
import math
import random
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import civic_habitat as h
import frontier_buildings as f
import heritage_kit as hk
import imperial_kit as ik
import kit_blocks as kb
import authored_examples as shared
import theme_kits as k
import utopia_buildings as u
from civic_habitat import LOUVRE, PAINT, PALE_GLASS, SLATS, add, cuboid, round_prism
from heritage_kit import BRICK, BRICK_TONE, COURSE, DRESSING, IRON, LEAD, NAVY, PILASTER, PILASTER_OUT, PLINTH, RUSTIC, SLATE, STONE, WALL
from kit_blocks import block, distinct, facing, run, volume
from theme_kits import LEVEL, W, back_wall, facade

VERDIGRIS = (.33, .42, .39)  # Copper rolls and caps too thin for the roofing's seams.
PAVERS, DECK_TONE = h.PANELS, (.60, .60, .60)  # Flat roofs: concrete pavers.
GLASS_ROOF = (1, .86, .81)  # A glazed roof: the pale glass greyed.
FACE = (.86, .83, .74)  # A clock's face.
HALL_GLASS = (.80, .88, .92)  # The halls' great windows and lancets: pale glass.
# Stained glass, dark from outside by day: deep blues, then ruby, a little amber and green. At night most panes glow
# in their own tone (finish).
BLUE, RUBY = ((.09, .13, .32), (.07, .10, .26)), ((.30, .07, .06), (.24, .06, .08))
JEWELS = (*BLUE, *BLUE, *BLUE, *RUBY, (.30, .20, .07), (.08, .21, .14))
LIT_PANES = .9  # The share of a stained window's panes that glow at night.
steps = partial(kb.steps, stone=(STONE, DRESSING))
planter = partial(kb.planter, stone=(STONE, DRESSING))
screen = partial(kb.screen, louvre=hk.PALE_LOUVRE)


def paving(x0, x1, y0, y1, z=.4, colour=(.84, .83, .80)):
    kb.paving(x0, x1, y0, y1, STONE, colour, z)


# -- Walls ------------------------------------------------------------------------------------------

def fill(length, base, accent=False, kind=None):
    """A stretch of the look's pier with its course and foot, or of the roof a wall carries: a wall's end carried on
    past its corner for the mitre to trim. Beside a lancet's foot the pier runs on up, without the course."""
    if kind in ('mansard', 'mansard-plain'):
        return hk.mansard_rows(0, length)
    if kind in ('battlement', 'parapet'):
        return hk.battlement_corner(None, length, merlons=kind == 'battlement')
    open_top = kind in ('lancet-low', 'stained-low')
    cuboid('pier', 0, length, -PILASTER_OUT, 0, PLINTH if base else 0.0, LEVEL if open_top else COURSE, STONE, RUSTIC if base else DRESSING,
           omit='b' if open_top else 'bt')
    if base:
        cuboid('pier foot', 0, length, -PILASTER_OUT-.3, 0, 0, PLINTH, STONE, RUSTIC, omit='b')
    if not open_top:
        hk.course(length)


def lit_glass(name, verts, rng, lit=.7, warm=0.0):
    """A pane (named `name` glass) of the landmarks' glass: pale, the odd one bright with the sky, most lit at night; a `warm` share show
    their lit hall and glow faintly all day."""
    if rng.random() < warm:
        add(name+' glass', PAINT, ik.WARM_ROOM, verts, [tuple(range(len(verts)))], light=ik.SHOP_GLOW)
    else:
        add(name+' glass', PALE_GLASS, ik.SKY_PANE if rng.random() < .2 else HALL_GLASS, verts, [tuple(range(len(verts)))],
            light='night' if rng.random() < lit else 'off')


def crown_of(x, cx, half, spring, pointed):
    """An arch's height over x."""
    return spring+(math.sqrt(max(0.0, (2*half)**2-(abs(x-cx)+half)**2)) if pointed else math.sqrt(max(0.0, half**2-(x-cx)**2)))


def glazing(name, cx, half, sill, spring, outline, rng, depth, pointed=False, fan=False):
    """An arch's glass behind stone mullions and a transom at its springing: small panes in iron bars, the head one
    pane (round and `fan`, behind bars from the springing's middle)."""
    x0, x1, top = cx-half, cx+half, max(z for _, _, z in outline)
    add(name+' back', PAINT, k.DARK_BACK, [(x0, depth, sill), (x1, depth, sill), (x1, depth, top), (x0, depth, top)], [(0, 1, 2, 3)])
    lights, rows = max(2, round(2*half/4.6)), max(1, round((spring-sill)/5.6))
    for row in range(rows):
        z0, z1 = sill+(spring-sill)*row/rows+.12, sill+(spring-sill)*(row+1)/rows-.12
        for i in range(lights):
            a, b = x0+2*half*i/lights+.12, x0+2*half*(i+1)/lights-.12
            lit_glass(name, [(a, depth-.06, z0), (b, depth-.06, z0), (b, depth-.06, z1), (a, depth-.06, z1)], rng, warm=.35)
        if row:
            cuboid(name+' bar', x0, x1, depth-.3, depth-.05, z0-.24, z0, PAINT, IRON, omit='bk', detail=True)
    lit_glass(name, outline, rng, 1.0, warm=1.0)
    stone = {round(lights/3), round(2*lights/3)} if half > 5 else set()  # Two stone posts, up into the head.
    for i in range(1, lights):
        x = x0+2*half*i/lights
        if i in stone:
            cuboid(name+' stone post', x-.4, x+.4, depth-1.0, depth-.1, sill, crown_of(x, cx, half, spring, pointed)-.2, STONE, DRESSING, omit='bkt')
        else:
            cuboid(name+' bar', x-.14, x+.14, depth-.3, depth-.05, sill, spring, PAINT, IRON, omit='bkt', detail=True)
    if spring-sill > 2:
        cuboid(name+' stone rail', x0, x1, depth-1.0, depth-.1, spring-.35, spring+.35, STONE, DRESSING, omit='bk')
    if fan and not pointed:
        for turn in (30, 60, 90, 120, 150):
            px, pz = cx+(half-.2)*math.cos(math.radians(turn)), spring+(half-.2)*math.sin(math.radians(turn))
            wx, wz = -math.sin(math.radians(turn))*.3, math.cos(math.radians(turn))*.3
            verts = [(cx-wx, depth-.5, spring-wz), (cx+wx, depth-.5, spring+wz), (px+wx, depth-.5, pz+wz), (px-wx, depth-.5, pz-wz)]
            add(name+' ray', STONE, DRESSING, verts, [k.facing(verts, (0, -1, 0))])


def great(rng, length, storeys, half, sill, spring, pointed=False, brick=False, doors=0, fan=False, flank=False):
    """A hall's great window, its bay as tall as the hall: one arch of small panes behind stone mullions, deep in its
    wall between stepped buttresses; doors, timber leaves in round arches at its foot; flank, a tall lancet either side
    of it."""
    height, cx, depth = storeys*LEVEL, length/2, 2.4
    eave = height-(LEVEL-COURSE)
    key, colour = (BRICK, BRICK_TONE) if brick else (STONE, WALL)
    door_half, door_spring = 4.0, 6.4
    door_at = [cx+(i-(doors-1)/2)*(2*door_half+3.6) for i in range(doors)]
    holes = [hk.arch_hole(cx, half, sill, spring, pointed)]+[hk.arch_hole(x, door_half, 0, door_spring) for x in door_at]
    side_at = [cx-(half+length/2)/2+.6, cx+(half+length/2)/2-.6] if flank else []
    side_half, side_sill, side_spring = 2.8, sill+2.0, spring-5.0
    holes += [hk.arch_hole(x, side_half, side_sill, side_spring, True) for x in side_at]
    facade('wall', holes, 0, eave, length, colour, du=12, dv=9, key=key)
    for x in side_at:
        outline = hk.arch('side lancet', x, side_half, side_sill, side_spring, key, colour, 1.2, pointed=True)
        add('side lancet back', PAINT, k.DARK_BACK, [(x-side_half, 1.2, side_sill), (x+side_half, 1.2, side_sill),
                                                    (x+side_half, 1.2, side_spring+6), (x-side_half, 1.2, side_spring+6)], [(0, 1, 2, 3)])
        lit_glass('side lancet', [(x-side_half+.1, 1.14, side_sill+.1), (x+side_half-.1, 1.14, side_sill+.1), (x+side_half-.1, 1.14, side_spring),
                                        (x-side_half+.1, 1.14, side_spring)], rng, warm=.5)
        lit_glass('side lancet', outline, rng, warm=.5)
    for x0, x1, inner in ((0, 3.0, 'l'), (length-3.0, length, 'r')):
        # A buttress in two steps under a gabled cap.
        low, high = eave*.56, eave-4.0
        cuboid('buttress', x0, x1, -2.8, 0, 0, low, STONE, DRESSING, omit='bk'+inner)
        cuboid('buttress', x0, x1, -1.5, 0, low, high, STONE, DRESSING, omit='bk'+inner)
        verts = [(x0, -2.8, low), (x1, -2.8, low), (x1, -1.5, low+2.2), (x0, -1.5, low+2.2)]
        add('buttress', STONE, DRESSING, verts, [k.facing(verts, (0, -1, 1))])
        verts = [(x0, -1.5, high), (x1, -1.5, high), (x1, 0, high+2.6), (x0, 0, high+2.6)]
        add('buttress', STONE, DRESSING, verts, [k.facing(verts, (0, -1, 1))])
    cuboid('course', 0, length, -PILASTER_OUT-.4, 0, eave, height, STONE, DRESSING, omit='klr')
    outline = hk.arch('great window', cx, half, sill, spring, key, colour, depth, ring=1.6, pointed=pointed, shade=hk.SHADE)
    glazing('great window', cx, half, sill, spring, outline, rng, depth, pointed, fan)
    for x in door_at:
        hk.arch('door', x, door_half, 0, door_spring, key, colour, depth, ring=.9, shade=hk.SHADE)
        back = depth-.06
        add('door back', PAINT, k.DARK_BACK, [(x-door_half, depth, 0), (x+door_half, depth, 0), (x+door_half, depth, door_spring+door_half),
                                              (x-door_half, depth, door_spring+door_half)], [(0, 1, 2, 3)])
        for a, b in ((x-door_half+.2, x-.06), (x+.06, x+door_half-.2)):
            add('door leaf', PAINT, hk.TIMBER, [(a, back, .1), (b, back, .1), (b, back, door_spring), (a, back, door_spring)], [(0, 1, 2, 3)])
        fanlight = [(px, back, pz) for px, pz in hk.arc(x, door_spring+.15, door_half-.2, 0, 180, hk.ARC)]
        add('door fanlight', PAINT, ik.WARM_ROOM, fanlight, [tuple(range(len(fanlight)))], light=ik.SHOP_GLOW)
    back_wall(length, 0, height, depth+.1)


def blank(rng, base, length):
    """A plain stretch of wall between pilasters."""
    hk.frame(length, [], base)


def slit(rng, base, length):
    """A shaft's storey: one narrow window."""
    cx = length/2
    hk.frame(length, [(cx-.9, cx+.9, 5.0, 12.6)], base)
    hk.window('slit', cx-.9, cx+.9, 5.0, 12.6, rng, 1, depth=.6, transom=0)


def stained(name, verts, rng):
    """A pane (named `name` stained glass): a dark jewel tone from outside by day, glowing at night (finish)."""
    facing(name+' stained glass', PAINT, rng.choice(JEWELS), verts, (0, -1, 0), light='night' if rng.random() < LIT_PANES else 'off')


def lancet(rng, length, part, glass=lit_glass):
    """A tower's tall pointed window, two storeys high: `low`, its foot (the opening runs on up through the storey's top,
    which has no course); `high`, its head; `one`, a window of one storey over a sill. glass: what lays a pane (name, verts, rng)."""
    half, depth = min(2.8, length/2-PILASTER-1.4), 1.0
    centres = [length/2] if length < 20 else [PILASTER+(length-2*PILASTER)*.27, PILASTER+(length-2*PILASTER)*.73]
    z0, z1 = {'low': (6.0, LEVEL), 'high': (0.0, 8.6), 'one': (4.6, 9.2)}[part]
    if part == 'low':
        facade('wall', [(cx-half, cx+half, z0, LEVEL) for cx in centres], 0, LEVEL, length, WALL, du=12, dv=9, key=STONE)
        for a, b, inner in ((0, PILASTER, 'l'), (length-PILASTER, length, 'r')):
            cuboid('pilaster', a, b, -PILASTER_OUT, 0, 0, LEVEL, STONE, DRESSING, omit='bkt'+inner)
    else:
        hk.frame(length, [hk.arch_hole(cx, half, z0, z1, True) for cx in centres], False)
    for cx in centres:
        x0, x1 = cx-half, cx+half
        if part == 'low':
            cuboid('lancet foot', x0-.5, x1+.5, -.6, depth, z0-.6, z0, STONE, DRESSING, omit='k')
            for x, inner in ((x0, 1), (x1, -1)):
                verts = [(x, 0, z0), (x, depth, z0), (x, depth, z1), (x, 0, z1)]
                add('lancet reveal', STONE, hk.REVEAL, verts, [k.facing(verts, (inner, 0, 0))])
        else:
            glass('lancet', hk.arch('lancet', cx, half, z0, z1, STONE, WALL, depth, pointed=True), rng)
        top = z1+(0 if part == 'low' else 6)
        add('lancet back', PAINT, k.DARK_BACK, [(x0, depth, z0), (x1, depth, z0), (x1, depth, top), (x0, depth, top)], [(0, 1, 2, 3)])
        for a, b in ((x0+.1, cx-.3), (cx+.3, x1-.1)):
            rows = 2 if glass is stained else 1  # Stained lights change tone up their height.
            for row in range(rows):
                za, zb = z0+.1+(z1-z0-.2)*row/rows, z0+.1+(z1-z0-.2)*(row+1)/rows
                glass('lancet', [(a, depth-.06, za), (b, depth-.06, za), (b, depth-.06, zb), (a, depth-.06, zb)], rng)
        cuboid('lancet stone post', cx-.3, cx+.3, depth-.6, depth-.1, z0, z1, STONE, DRESSING, omit='bkt')
    back_wall(length, 0, LEVEL)


def belfry(rng, length):
    """A tower's belfry stage: two pointed openings filled with louvres."""
    half, sill, spring, depth = 2.6, 3.0, 8.4, 1.0
    centres = (PILASTER+(length-2*PILASTER)*.27, PILASTER+(length-2*PILASTER)*.73)
    hk.frame(length, [hk.arch_hole(cx, half, sill, spring, True) for cx in centres], False)
    for cx in centres:
        outline = hk.arch('belfry', cx, half, sill, spring, STONE, WALL, depth, pointed=True)
        add('belfry louvre', SLATS, LOUVRE, [(cx-half, depth-.06, sill), (cx+half, depth-.06, sill), (cx+half, depth-.06, spring),
                                            (cx-half, depth-.06, spring)], [(0, 1, 2, 3)])
        add('belfry louvre', SLATS, LOUVRE, outline, [tuple(range(len(outline)))])


def piece(kind, base, rng, length):
    """The kit's bay of kind as a builder, `length` wide: a kit bay, its roof along a wall, an entrance (the kit's
    width), a tower's stage, a stretch of pier, or nothing where another block stands."""
    if kind in hk.WALLS:
        builder, more = hk.WALLS[kind]
        return lambda: builder(rng, base, length, **more)
    if kind in ('entrance', 'entrance-med'):
        assert abs(length-W) < 1e-6, (kind, length)
    return {'gothic': lambda: hk.arches(rng, base, length, pointed=True), 'brick-gothic': lambda: hk.arches(rng, base, length, True, True),
            'balcony': lambda: hk.balcony(rng, length), 'arcade': lambda: hk.arcade(rng, 'plain', length),
            'shop': lambda: hk.arcade(rng, 'shop', length), 'service': lambda: hk.panel(rng, True, length, kind='service'),
            'entrance': lambda: hk.entrance(rng), 'entrance-med': lambda: hk.entrance(rng, 'med'),
            'blank': lambda: blank(rng, base, length), 'slit': lambda: slit(rng, base, length), 'belfry': lambda: belfry(rng, length),
            'lancet-low': lambda: lancet(rng, length, 'low'), 'lancet-high': lambda: lancet(rng, length, 'high'),
            'stained-low': lambda: lancet(rng, length, 'low', stained), 'stained-high': lambda: lancet(rng, length, 'high', stained),
            'stained-one': lambda: lancet(rng, length, 'one', stained),
            'mansard': lambda: hk.mansard(rng, length), 'mansard-plain': lambda: hk.mansard(rng, length, dormers=False),
            'battlement': lambda: hk.battlement(rng, length), 'parapet': lambda: hk.battlement(rng, length, merlons=False),
            'gallery': lambda: gallery(rng, length, BUTTRESS), 'pier': lambda: fill(length, base), 'skip': lambda: None}[kind]


def downpipes(p, q, spec, z0, z1):
    """A lead downpipe on the pilaster between each two bays of a wall from p to q."""
    along, length = f.unit(p, q), math.dist(p, q)
    nx, ny = f.outward(p, q)
    spans, at = kb.widths(spec, length), 0.0
    for (kind, width), (after, _) in zip(spans, spans[1:]):
        at += width
        if 'skip' in (kind, after):
            continue
        x, y = p[0]+along[0]*at+nx*(PILASTER_OUT+.3), p[1]+along[1]*at+ny*(PILASTER_OUT+.3)
        kb.bar('downpipe', [(x, y, z0+.2), (x, y, z1-.4)], .2, (.42, .44, .45), fine=True)


def bays(kind, length, about=W):
    """A wall's worth of one kind, about `about` wide each."""
    return [kind]*max(1, round(length/about))


def tower(name, ring, stages, faces=None, z0=0.0, seed=0, ground=None):
    """A tower laid in stages, a kind a storey; faces[edge](storey, kind) gives an edge its own spec where another
    block hides part of it. Gives its walls' top."""
    block(ring, {i: (lambda s, i=i: faces[i](s, stages[s]) if faces and i in faces else stages[s]) for i in range(len(ring))}, len(stages), z0=z0,
          seed=seed, ground=ground)
    return z0+len(stages)*LEVEL


def pinnacles(name, ring, z, half=1.5, shaft=3.6, tip=5.4, inset=1.0):
    """A stone pinnacle on each corner of a tower's top."""
    for x, y in (f.inset(ring, inset) if inset else ring):
        cuboid(name+' pinnacle', x-half, x+half, y-half, y+half, z, z+shaft, STONE, DRESSING, omit='b')
        peak = [(x-half-.2, y-half-.2, z+shaft), (x+half+.2, y-half-.2, z+shaft), (x+half+.2, y+half+.2, z+shaft), (x-half-.2, y+half+.2, z+shaft),
                (x, y, z+shaft+tip)]
        add(name+' pinnacle', STONE, DRESSING, peak, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)])


# -- Roofs ------------------------------------------------------------------------------------------

def kit_roof(name, ring, z, kind='mansard', hidden=(), butt=(), seed=0, spans=None):
    """The kit's own roof round a block: its mansard (with dormers, or plain), parapet or battlement along every wall
    but those hidden (`spans` gives an edge its own spec), and the deck inside. Gives the deck's height."""
    faces = {i: bays(kind, math.dist(ring[i], ring[(i+1) % len(ring)])) for i in range(len(ring))}
    faces.update(spans or {})
    block(ring, faces, 1, z0=z, hidden=hidden, butt=butt, seed=seed, ground=False)
    inset, height = (hk.SKIRT, hk.DECK) if kind.startswith('mansard') else (hk.PARAPET_DEEP, .6)
    f.cap(name+' deck', inset_edges(ring, [0 if i in hidden else inset-.05 for i in range(len(ring))]), z+height, PAVERS, DECK_TONE)
    return z+height


def inset_edges(ring, depths):
    """A convex counter-clockwise ring with its edge i moved depths[i] inside."""
    lines = []
    for i, depth in enumerate(depths):
        p, q = ring[i], ring[(i+1) % len(ring)]
        nx, ny = f.outward(p, q)
        lines.append(((p[0]-nx*depth, p[1]-ny*depth), (q[0]-p[0], q[1]-p[1])))
    result = []
    for i in range(len(ring)):
        (p, d), (q, e) = lines[i-1], lines[i]
        t = ((q[0]-p[0])*e[1]-(q[1]-p[1])*e[0])/(d[0]*e[1]-d[1]*e[0])
        result.append((p[0]+d[0]*t, p[1]+d[1]*t))
    return result


def cornice(name, ring, z, out=hk.CORNICE_OUT, height=hk.CORNICE):
    """A stone cornice round walls' top."""
    outer = f.inset(ring, -out)
    f.wall_ring(name+' cornice', outer, z, z+height, STONE, DRESSING)
    for i in range(len(ring)):
        j = (i+1) % len(ring)
        facing(name+' cornice soffit', PAINT, hk.SOFFIT, [(*outer[i], z), (*outer[j], z), (*ring[j], z), (*ring[i], z)], (0, 0, -1))
    f.cap(name+' cornice top', outer, z+height-.02, STONE, DRESSING)
    return outer


def roof_dormer(rng, pitch, at=2.4, wide=4.6, tall=5.4, crown=2.4):
    """A dormer on a pitched roof, in a frame laid along its eave (y in from the eave, z up from it): a stone face round
    a lit window, slate cheeks and a slate gable back to the slope."""
    half, foot = wide/2, pitch*at
    top = foot+tall
    add('dormer', STONE, DRESSING, [(-half, at, foot-.8), (half, at, foot-.8), (half, at, top), (-half, at, top)], [(0, 1, 2, 3)])
    add('dormer', STONE, DRESSING, [(-half-.3, at, top), (half+.3, at, top), (0, at, top+crown)], [(0, 1, 2)])
    add('dormer glass', PALE_GLASS, NAVY, [(-half+.7, at-.06, foot+.6), (half-.7, at-.06, foot+.6), (half-.7, at-.06, top-.6), (-half+.7, at-.06, top-.6)],
        [(0, 1, 2, 3)], light='night' if rng.random() < .5 else 'off')
    for side in (-1, 1):
        verts = [(side*half, at, foot-.8), (side*half, at, top), (side*half, top/pitch, top)]
        add('dormer cheek', SLATE, (.9, .9, .9), verts, [k.facing(verts, (side, 0, 0))])
        verts = [(side*(half+.5), at-.5, top-.2), (0, at-.5, top+crown), (0, (top+crown)/pitch, top+crown), (side*(half+.5), (top-.2)/pitch, top-.2)]
        add('dormer roof', SLATE, (.86, .86, .86), verts, [k.facing(verts, (side, 0, 1))])


def pitched(name, ring, z, pitch=1.0, top=None, key=SLATE, omit=(), ridge=True, dormers=None, seed=0):
    """A hipped roof of slate over walls: a stone cornice, every side rising at `pitch` to a ridge under a copper roll,
    or stopping `top` in (the ring there and its height are returned, for a flat top or a lantern); sides in `omit`
    are left out where another roof covers them; dormers[side], where along that side (0 to 1) a dormer stands."""
    eave = f.inset(cornice(name, ring, z), .5)
    z0 = z+hk.CORNICE
    depth = min(top, kb.reach_of(eave)) if top is not None else kb.reach_of(eave)
    upper, z1 = f.inset(eave, depth), z0+pitch*depth
    rng = random.Random(seed)
    for i in range(len(eave)):
        j = (i+1) % len(eave)
        quad = distinct([(*eave[i], z0), (*eave[j], z0), (*upper[j], z1), (*upper[i], z1)])
        if i not in omit and len(quad) >= 3:
            add(name+' roofing', key, (1, 1, 1), quad, [tuple(range(len(quad)))])
        kb.bar(name+' hip', distinct([(*eave[i], z0+.15), (*upper[i], z1+.15)]), .36, VERDIGRIS, fine=False)
        along = f.unit(eave[i], eave[j])
        for t in (dormers or {}).get(i, ()):
            origin = (eave[i][0]+(eave[j][0]-eave[i][0])*t, eave[i][1]+(eave[j][1]-eave[i][1])*t)
            f.lay(lambda: roof_dormer(rng, pitch), origin, along, z0)
    line = distinct([(*p, z1+.15) for p in upper])
    if ridge and len(line) == 2:
        kb.bar(name+' ridge', line, .45, VERDIGRIS, fine=False)
        for x, y, zz in line:
            finial(name, x, y, zz, 3.0)
    elif ridge and len(line) == 1:
        finial(name, *line[0], 4.0)
    return upper, z1


def finial(name, x, y, z, height=3.0):
    """A plain iron spike on a roof's point."""
    cuboid(name+' finial', x-.22, x+.22, y-.22, y+.22, z-.3, z+height, PAINT, IRON, omit='b')


def flat_top(name, ring, z, curb=1.2):
    """A truncated roof's top or a flat roof: a lead curb round a deck of pavers. Gives the deck's height."""
    inner = f.inset(ring, curb)
    f.frustum(name+' curb', ring, z, inner, z, PAINT, LEAD)
    for i in range(len(inner)):
        j = (i+1) % len(inner)
        facing(name+' curb face', PAINT, IRON, [(*inner[i], z-.4), (*inner[j], z-.4), (*inner[j], z), (*inner[i], z)],
               (*f.outward(inner[j], inner[i]), 0))
    f.cap(name+' deck', inner, z-.4, PAVERS, DECK_TONE)
    return z-.4


def gabled(name, x0, x1, y0, y1, z, pitch=1.0, fronts=('front',), along='y', key=SLATE, window=False):
    """A gabled slate roof over a box, its ridge along y (or x): two slopes, a stone gable with a coping at each end in
    `fronts` ('front' the low end of the axis, 'back' the high), a copper ridge; `window`, a lit lancet in each gable.
    Gives the ridge's height."""
    if along == 'x':
        to = lambda a, b, c: (b, a, c)
        x0, x1, y0, y1 = y0, y1, x0, x1
    else:
        to = lambda a, b, c: (a, b, c)
    mid, top, over = (x0+x1)/2, z+pitch*(x1-x0)/2, .8
    for side, edge in ((-1, x0-over), (1, x1+over)):
        low = z-pitch*over
        verts = [to(edge, y0, low), to(edge, y1, low), to(mid, y1, top), to(mid, y0, top)]
        facing(name+' roofing', key, (1, 1, 1), verts, to(side, 0, 1))
    for end, y, way in (('front', y0, -1), ('back', y1, 1)):
        if end not in fronts:
            continue
        verts = [to(x0, y, z), to(x1, y, z), to(mid, y, top)]
        facing(name+' gable', STONE, WALL, verts, to(0, way, 0))
        for a, b in ((x0-over, mid), (x1+over, mid)):
            za = z-pitch*over
            verts = [to(a, y+way*.5, za+.1), to(b, y+way*.5, top+.1), to(b, y+way*.5, top+1.3), to(a, y+way*.5, za+1.3)]
            facing(name+' coping', STONE, DRESSING, verts, to(0, way, 0))
            verts = [to(a, y+way*.5, za+1.3), to(b, y+way*.5, top+1.3), to(b, y-way*.9, top+1.3), to(a, y-way*.9, za+1.3)]
            facing(name+' coping', STONE, DRESSING, verts, to(0, 0, 1))
        finial(name, *to(mid, y+way*.2, top+1.2)[:2], top+1.2, 3.4)
        if window and top-z > 13:
            low, spring = z+2.6, z+2.6+(top-z)*.28
            for half, out, key_, colour, light in ((2.5, .1, STONE, DRESSING, None), (1.7, .2, PALE_GLASS, HALL_GLASS, 'night')):
                pad = .8 if light is None else 0
                verts = [to(mid-half, y+way*out, low-pad), to(mid+half, y+way*out, low-pad), to(mid+half, y+way*out, spring),
                         to(mid, y+way*out, spring+half*1.5+pad), to(mid-half, y+way*out, spring)]
                facing(name+' gable window', key_, colour, verts, to(0, way, 0), **({'light': light} if light else {}))
    kb.bar(name+' ridge', [to(mid, y0, top+.15), to(mid, y1, top+.15)], .45, VERDIGRIS, fine=False)
    return top


def spire(name, ring, z, height, key=SLATE):
    """A pyramid roof on a tower: a cornice, its faces up to a point under an iron finial."""
    eave = cornice(name, ring, z)
    z0 = z+hk.CORNICE
    cx, cy = sum(p[0] for p in ring)/len(ring), sum(p[1] for p in ring)/len(ring)
    for i in range(len(eave)):
        j = (i+1) % len(eave)
        add(name+' roofing', key, (1, 1, 1), [(*eave[i], z0), (*eave[j], z0), (cx, cy, z0+height)], [(0, 1, 2)])
        kb.bar(name+' hip', [(*eave[i], z0+.15), (cx, cy, z0+height+.1)], .32, VERDIGRIS, fine=False)
    finial(name, cx, cy, z0+height, 4.5)


def clock(name, x, y, z, radius, normal):
    """A clock on a wall facing `normal` (an axis): a pale face in a broad iron ring, softly lit at night, its hands."""
    nx, ny = normal
    tx, ty = -ny, nx

    def at(a, b, out):
        return x+tx*a+nx*out, y+ty*a+ny*out, z+b
    for part, r, out, colour, light in ((' ring', radius+.9, .25, IRON, None), (' face', radius, .35, FACE, 'dim')):
        verts = [at(r*math.cos(i*math.tau/12), r*math.sin(i*math.tau/12), out) for i in range(12)]
        facing(name+part, PAINT, colour, verts, (nx, ny, 0), **({'light': light} if light else {}))
    for angle, length, wide in ((60, radius*.55, .3), (-30, radius*.8, .22)):
        ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        verts = [at(-sa*wide, ca*wide, .42), at(sa*wide, -ca*wide, .42), at(ca*length+sa*wide, sa*length-ca*wide, .42),
                 at(ca*length-sa*wide, sa*length+ca*wide, .42)]
        facing(name+' hand', PAINT, IRON, verts, (nx, ny, 0))


def glass_vault(name, x0, x1, y0, y1, z, rise, segments=8, bay=12.0, ends=('front', 'back'), monitor=False):
    """A barrel vault of grey glass along y on iron ribs and purlins, lit from below at night; a glazed lunette behind
    iron bars closes each end in `ends`; `monitor`, a raised strip of glass along its ridge."""
    cx, half = (x0+x1)/2, (x1-x0)/2
    curve = [(cx-half*math.cos(math.pi*i/segments), z+rise*math.sin(math.pi*i/segments)) for i in range(segments+1)]
    count = max(1, round((y1-y0)/bay))
    tones = random.Random(round(x0*7+y0*3))
    for (ax, az), (bx, bz) in zip(curve, curve[1:]):
        for i in range(count):
            ya, yb = y0+(y1-y0)*i/count, y0+(y1-y0)*(i+1)/count
            pick = tones.random()
            tint = ik.SKY_PANE if pick < .22 else tuple(v*.84 for v in GLASS_ROOF) if pick < .4 else GLASS_ROOF
            facing(name+' glass', PALE_GLASS, tint, [(ax, ya, az), (bx, ya, bz), (bx, yb, bz), (ax, yb, az)], ((ax+bx)/2-cx, 0, 1), light='dim')
    for i in range(count+1):
        y = y0+(y1-y0)*i/count
        kb.bar(name+' rib', [(x, y, zz+.1) for x, zz in curve], .34, IRON, fine=False)
    for x, zz in curve[1:-1]:
        kb.bar(name+' purlin', [(x, y0, zz+.12), (x, y1, zz+.12)], .24, IRON, fine=False)
    if monitor:
        wide, up = half*.16, 2.2
        top = z+rise
        for side in (-1, 1):
            verts = [(cx+side*wide, y0+3, top-.4), (cx+side*wide, y1-3, top-.4), (cx+side*wide, y1-3, top+up), (cx+side*wide, y0+3, top+up)]
            facing(name+' monitor glass', PALE_GLASS, ik.SKY_PANE, verts, (side, 0, 0), light='dim')
            verts = [(cx+side*(wide+.6), y0+2.4, top+up), (cx+side*(wide+.6), y1-2.4, top+up), (cx, y1-2.4, top+up+1.4), (cx, y0+2.4, top+up+1.4)]
            facing(name+' monitor glass', PALE_GLASS, GLASS_ROOF, verts, (side, 0, 1), light='dim')
        for y, way in ((y0+3, -1), (y1-3, 1)):
            verts = [(cx-wide, y, top-.4), (cx+wide, y, top-.4), (cx+wide, y, top+up), (cx, y, top+up+1.4), (cx-wide, y, top+up)]
            facing(name+' monitor', PAINT, LEAD, verts, (0, way, 0))
    for end, y, way in (('front', y0, -1), ('back', y1, 1)):
        if end in ends:
            verts = [(x, y, zz) for x, zz in curve]
            facing(name+' lunette', PALE_GLASS, GLASS_ROOF, verts, (0, way, 0), light='dim')
            for i in range(1, 6):
                x = cx-half+2*half*i/6
                crown = z+rise*math.sqrt(max(0.0, 1-((x-cx)/half)**2))
                kb.bar(name+' lunette post', [(x, y+way*.1, z), (x, y+way*.1, crown)], .26, IRON, fine=False)
            kb.bar(name+' lunette foot', [(x0, y+way*.1, z+.2), (x1, y+way*.1, z+.2)], .3, IRON, fine=False)
    return z+rise


def iron_post(x, y, z0, z1, half=.7):
    """An iron post on a stone foot."""
    cuboid('post foot', x-half*1.6, x+half*1.6, y-half*1.6, y+half*1.6, z0, z0+1.6, STONE, DRESSING, omit='b')
    cuboid('post', x-half, x+half, y-half, y+half, z0+1.6, z1, PAINT, IRON, omit='bt')


def plant_deck(name, ring, z, rng, units=2, more=('tank', 'duct')):
    """A flat roof's plant: fan units behind a pale louvred screen in its middle, and the kit's own fittings (`more`)
    beside it."""
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    wide, deep = max(xs)-min(xs), max(ys)-min(ys)
    a, b = min(wide*.22, 5.0*units), min(deep*.2, 6.0)
    screen(name+' plant', f.rect(cx-a-1.5, cx+a+1.5, cy-b-1.5, cy+b+1.5), z, 4.8,
           [(cx+(i-(units-1)/2)*2*a/units, cy, a/units-.4, b-.6) for i in range(units)])
    spots = [(cx-wide*.33, cy), (cx+wide*.33, cy)] if wide >= deep else [(cx, cy-deep*.33), (cx, cy+deep*.33)]
    for kind, (x, y) in zip(more, spots):
        f.lay(lambda: getattr(hk, kind)(rng), (x, y), (1, 0) if wide >= deep else (0, 1), z)


# -- Government Hall: a hall between two towers, a glass wing (sheet 1) --------------------------------------------

def government_hall():
    """The hall on a low base, three storeys of pointed windows under a steep slate roof with dormers; in the middle of
    its front a gabled bay, the great pointed window deep between stepped buttresses over three doors, at the head of a
    broad stair; at each front corner a tower in stages (a tall lancet, a louvred belfry, pinnacles) under a slate
    spire; a stone wing to the west under the kit's mansard, the modern glass wing to the east under a flat roof with
    its plant."""
    rng = random.Random(21)
    base, storeys = 5.0, 3
    top = base+storeys*LEVEL
    hall = f.rect(-56, 56, -14, 80)
    front = ['gothic', 'lancet-low', 'lancet-high']  # Over a base storey, lancets two storeys tall.
    faces = {
        0: lambda s: [('skip', 12), (front[s], 24), ('skip', 40), (front[s], 24), ('skip', 12)],
        1: lambda s: [('skip', 72), ('panel', 22)] if s < 2 else [('skip', 16), ('gothic', 26), ('gothic', 26), ('gothic', 26)],
        2: lambda s: ['service', 'sash', 'sash', 'sash', 'service'] if s == 0 else ['sash']*5,
        3: lambda s: [('panel', 34), ('skip', 60)] if s < 2 else [('gothic', 26), ('gothic', 26), ('gothic', 26), ('skip', 16)],
    }
    block(hall, faces, storeys, z0=base, seed=21, ground=True, pipes={2})
    pitched('hall roof', hall, top, pitch=.85, dormers={1: (.42, .68), 2: (.22, .5, .78), 3: (.32, .58)}, seed=21)
    # The gabled bay with the great window.
    bay = f.rect(-20, 20, -26, -14)
    block(bay, {0: [('skip', 40)], 1: [('pier', 12)], 3: [('pier', 12)]}, storeys, z0=base, hidden={2}, seed=22, ground=True)
    f.lay(lambda: great(rng, 40, storeys, 12.0, 15.0, 24.0, pointed=True, doors=3), (-20, -26), (1, 0), base)
    gabled('bay roof', -20, 20, -26, 20, top, pitch=1.15, window=True)
    for side in (-1, 1):
        pinnacles('bay', [(side*18.4, -24.4)], top-.6, inset=0, shaft=5.0, tip=6.0)
    # The towers: a base storey, a lancet two storeys tall, a plain stage over the hall's eave, the belfry.
    stages = ['gothic', 'lancet-low', 'lancet-high', 'blank', 'belfry']
    for side in (-1, 1):
        ring = f.rect(*sorted((side*44, side*70)), -28, 2)
        inner = 1 if side < 0 else 3
        faces = {inner: lambda s, kind, inner=inner: kind if s >= storeys else ([(kind, 14), ('skip', 16)] if inner == 1 else [('skip', 16), (kind, 14)]),
                 2: lambda s, kind, side=side: kind if s >= storeys else ([('skip', 12), ('blank', 14)] if side < 0 else [('blank', 14), ('skip', 12)])}
        z = tower('tower', ring, stages, faces, z0=base, seed=23+side, ground=True)
        spire('tower spire', ring, z, 40.0)
        pinnacles('tower', ring, z+hk.CORNICE)
        volume('tower %d' % side, ring, 0, len(stages)*LEVEL)
    # The wings: stone to the west, glass to the east.
    west = f.rect(-112, -56, -2, 46)
    block(west, {0: ['arch', 'sash'], 2: ['sash', 'sash'], 3: ['arch', 'arch']}, 2, z0=base, hidden={1}, butt={(0, 1), (2, 0)}, seed=25, ground=True)
    kit_roof('west wing', west, base+2*LEVEL, hidden={1}, butt={(0, 1), (2, 0)}, seed=26)
    east = f.rect(56, 128, 2, 58)
    block(east, {0: ['glass']*3, 1: ['glass']*2, 2: ['glass', 'louvre', 'glass']}, 2, z0=base, hidden={3}, butt={(0, 0), (2, 1)}, seed=27, ground=True)
    deck = kit_roof('east wing', east, base+2*LEVEL, 'parapet', hidden={3}, butt={(0, 0), (2, 1)}, seed=28)
    plant_deck('east wing', east, deck, rng, 3)
    for part in (hall, bay, west, east, *[f.rect(*sorted((side*44, side*70)), -28, 2) for side in (-1, 1)]):
        f.wall_ring('base', f.inset(part, -1.4), 0, base, STONE, RUSTIC)
        f.frustum('base', f.inset(part, -1.4), base, part, base, STONE, RUSTIC)
    # The stair, its cheeks and planters.
    steps(-17, 17, -54, -26, base, 9)
    for side in (-1, 1):
        a, b = sorted((side*17, side*27))
        cuboid('stair cheek', a, b, -48, -26, 0, base, STONE, DRESSING, omit='b')
        planter(a+1.2, b-1.2, -46, -36, base, rng, height=1.6, size=3.2)
        hk.lamp(side*18.5, base+6.0, -28.8)  # On the bay's buttresses.
        h.fixtures.append((side*18.5, -31, base+8))
    paving(-80, 80, -60, -14, .3)
    volume('hall', hall, 0, storeys*LEVEL)
    volume('west wing', west, 0, 2*LEVEL)
    volume('east wing', east, 0, 2*LEVEL)


# -- Transit Terminal: a station house between battlemented towers, a glass train shed (sheet 3) ---------------------

def transit_terminal():
    """The station house under a steep slate roof with dormers, in its gabled middle the great fan window over three
    doors; a battlemented tower in stages at each front corner; behind it the train shed, a vault of grey glass on
    iron ribs with a monitor along its ridge, between low stone arcades; a glazed platform canopy on iron posts down
    each side."""
    rng = random.Random(31)
    house = f.rect(-64, 64, -6, 46)
    top = 2*LEVEL
    faces = {
        0: lambda s: [('skip', 14), ('arch', 22), ('skip', 56), ('arch', 22), ('skip', 14)],
        1: lambda s: ['service', 'arch'] if s == 0 else ['arch', 'sash'],
        # The shed opens into its ground storey; over it the wall closes the vault's end.
        2: lambda s: [('panel', 24), ('skip', 80), ('panel', 24)] if s == 0 else [('panel', 24), ('blank', 80), ('panel', 24)],
        3: lambda s: ['arch', 'service'] if s == 0 else ['sash', 'arch'],
    }
    block(house, faces, 2, seed=31)
    pitched('house roof', house, top, pitch=.8, dormers={0: (.2, .8), 1: (.5,), 3: (.5,)}, seed=31)
    bay = f.rect(-28, 28, -16, -6)
    block(bay, {0: [('skip', 56)], 1: [('pier', 10)], 3: [('pier', 10)]}, 2, hidden={2}, seed=32)
    f.lay(lambda: great(rng, 56, 2, 20.0, 11.6, 12.6, doors=3, fan=True), (-28, -16), (1, 0), 0)
    gabled('bay roof', -28, 28, -16, 22, top, pitch=.62)
    stages = ['arch', 'lancet-low', 'lancet-high', 'blank', 'belfry']
    for side in (-1, 1):
        ring = f.rect(*sorted((side*50, side*76)), -18, 8)
        inner = 1 if side < 0 else 3
        faces = {inner: lambda s, kind, inner=inner: kind if s >= 2 else ([(kind, 12), ('skip', 14)] if inner == 1 else [('skip', 14), (kind, 12)]),
                 2: lambda s, kind, side=side: kind if s >= 2 else ([('skip', 14), ('blank', 12)] if side < 0 else [('blank', 12), ('skip', 14)])}
        z = tower('tower', ring, stages, faces, seed=33+side)
        kit_roof('tower top', ring, z, 'battlement', seed=35+side)
        volume('tower %d' % side, ring, 0, len(stages)*LEVEL)
        # A glazed canopy over the house's side door.
        verts = [(side*64, 12, 14.5), (side*76, 12, 11.5), (side*76, 40, 11.5), (side*64, 40, 14.5)]
        facing('side canopy', PALE_GLASS, GLASS_ROOF, verts, (0, 0, 1), light='dim')
        for y in (13, 39):
            iron_post(side*75, y, 0, 11.5, half=.5)
        kb.bar('side canopy beam', [(side*75, 12, 11.7), (side*75, 40, 11.7)], .3, IRON, fine=False)
    # The train shed.
    y0, y1, half, spring = 46.0, 226.0, 40.0, 20.0
    for side in (-1, 1):
        p, q = ((side*half, y1), (side*half, y0)) if side < 0 else ((side*half, y0), (side*half, y1))
        run(p, q, bays('arch', y1-y0, 30), 1, seed=36+side, ground=True)
        cuboid('shed plate', side*half-1.2, side*half+1.2, y0, y1, LEVEL, spring, STONE, DRESSING, omit='b')
        # A platform canopy outside the arcade.
        a, b = sorted((side*(half+1.2), side*(half+22)))
        near, far = side*(half+1.2), side*(half+22)
        verts = [(near, y0+6, spring-2), (far, y0+6, spring-5.4), (far, y1-6, spring-5.4), (near, y1-6, spring-2)]
        facing('canopy glass', PALE_GLASS, GLASS_ROOF, verts, (0, 0, 1), light='dim')
        for y in [y0+12+30*i for i in range(6)]:
            iron_post(side*(half+20), y, .6, spring-5.4)
        kb.bar('canopy beam', [(side*(half+20), y0+6, spring-5.3), (side*(half+20), y1-6, spring-5.3)], .4, IRON, fine=False)
        cuboid('platform', a-(2 if side < 0 else 0), b+(2 if side > 0 else 0), y0, y1, 0, .6, STONE, (.80, .79, .76), omit='b')
    glass_vault('shed', -half, half, y0, y1, spring, 18.0, bay=15.0, ends=('back',), monitor=True)
    cuboid('shed floor', -half, half, y0, y1, 0, .6, STONE, (.80, .79, .76), omit='b')
    for x in (-20, 20):  # The platforms' edges, lit along their length at night.
        cuboid('platform edge', x-.5, x+.5, y0+4, y1-4, .6, .8, PAINT, (.86, .76, .46), omit='b', light='night')
    paving(-70, 70, -30, -6, .3)
    for side in (-1, 1):
        planter(*sorted((side*32, side*46)), -22, -17, .3, rng, size=3.2)
    h.fixtures.extend([(0, -20, 12), (0, 100, 30), (0, 180, 30)])
    volume('house', house, 0, top)
    volume('shed', f.rect(-half, half, y0, y1), 2*LEVEL-1, 2*LEVEL, behind=0)


# -- Administrative Offices: a brick hall, a clock tower, glass office wings (sheet 4) -------------------------------

def administrative_offices():
    """The hall of brick and stone, in each gable a lancet, its front the great pointed window over a stone porch of
    three arches; a clock tower at the west end, a shaft of slit windows up to the clock, a louvred belfry and
    pinnacles under a slate spire; office wings of glass oriels under the kit's mansard; a rear block with the plant
    on its flat roof."""
    rng = random.Random(41)
    hall = f.rect(-30, 30, 0, 74)
    top = 3*LEVEL
    block(hall, {0: [('skip', 60)], 1: [('skip', 60), ('brick-panel', 14)], 2: lambda s: [('skip', 60)] if s < 2 else ['brick-sash', 'brick-sash'],
                 3: [('brick-panel', 14), ('skip', 60)]}, 3, seed=41)
    f.lay(lambda: great(rng, 60, 3, 12.0, 20.0, 27.0, pointed=True, brick=True, flank=True), (-30, 0), (1, 0), 0)
    gabled('hall roof', -30, 30, 0, 74, top, pitch=1.0, fronts=('front', 'back'), window=True)
    porch = f.rect(-36, 36, -16, 0)
    block(porch, {0: ['arcade']*3, 1: [('pier', 16)], 3: [('pier', 16)]}, 1, hidden={2}, seed=42)
    kit_roof('porch', porch, LEVEL, 'parapet', hidden={2}, butt={(1, 1), (3, 0)}, seed=43)
    # The clock tower: its shaft, the clock's stage, the belfry.
    ring = f.rect(-112, -86, -6, 20)
    stages = ['gothic', 'slit', 'slit', 'slit', 'blank', 'belfry']
    z = tower('clock tower', ring, stages, {1: lambda s, kind: kind if s >= 3 else [(kind, 8), ('skip', 18)]}, seed=44)
    for nx, ny, x, y in ((0, -1, -99, -6), (0, 1, -99, 20), (-1, 0, -112, 7), (1, 0, -86, 7)):
        clock('clock', x, y, 4*LEVEL+8.4, 5.4, (nx, ny))
    spire('clock tower spire', ring, z, 30.0)
    pinnacles('clock tower', ring, z+hk.CORNICE)
    volume('clock tower', ring, 0, len(stages)*LEVEL)
    # The office wings. The west one ends against the tower for its first 18, and in a wall of its own beyond.
    west = f.rect(-86, -30, 0, 62)
    block(west, {0: ['glass', 'glass'], 2: ['glass', 'glass'], 3: [('glass', 42), ('skip', 20)]}, 3, hidden={1}, butt={(0, 0), (0, 1), (2, 0)}, seed=45)
    deck = kit_roof('west wing', west, top, 'mansard', hidden={1}, butt={(0, 0), (0, 1), (2, 0)}, seed=46,
                    spans={3: [('mansard', 42), ('skip', 20)]})
    f.cap('west wing deck', f.rect(-86, -86+hk.SKIRT, hk.SKIRT, 20), deck, PAVERS, DECK_TONE)
    east = f.rect(30, 106, 0, 60)
    block(east, {0: ['glass', 'glass', 'arch'], 1: ['sash', 'sash'], 2: ['glass', 'glass', 'sash']}, 3, hidden={3}, butt={(0, 0), (2, 1)}, seed=47)
    deck = kit_roof('east wing', east, top, 'mansard', hidden={3}, butt={(0, 0), (2, 1)}, seed=48)
    plant_deck('east wing', f.inset(east, 10), deck, rng)
    rear = f.rect(-30, 64, 74, 112)
    block(rear, {0: [('skip', 60), ('brick-sash', 34)], 1: ['brick-sash', 'brick-louvre'], 2: ['brick-sash', 'works', 'brick-louvre', 'brick-sash'],
                 3: ['brick-louvre', 'brick-sash']}, 2, seed=49)
    deck = kit_roof('rear', rear, 2*LEVEL, 'parapet', seed=50)
    plant_deck('rear', rear, deck, rng, 3)
    paving(-40, 40, -30, -16, .3)
    for side in (-1, 1):
        planter(*sorted((side*40, side*52)), -12, -4, 0, rng, size=3.4)
    h.fixtures.append((0, -20, 10))
    volume('hall', hall, 0, top)
    volume('west wing', west, 0, top)
    volume('east wing', east, 0, top)
    volume('rear', rear, 0, 2*LEVEL)
    volume('porch', porch, 0, LEVEL)


# -- Commercial Center: a baroque hall between modern glass wings (sheet 5) -----------------------------------------

def commercial_center():
    """The hall, three storeys of arched windows under a great slate roof with dormers and a glass lantern on its flat
    top; in the middle of its front the frontispiece, a tall round-arched portal between column pairs under a
    pediment; a belvedere tower rising from its back corner, a louvred top stage under a slate spire; a wing of glass
    oriels each side under a flat roof with the plant."""
    rng = random.Random(51)
    hall = f.rect(-44, 44, -16, 80)
    top = 3*LEVEL
    faces = {
        0: lambda s: [('arch', 24), ('skip', 40), ('arch', 24)] if s else [('shop', 24), ('skip', 40), ('shop', 24)],
        1: lambda s: [('pier', 16), ('skip', 58), ('panel', 22)],
        2: lambda s: ['service', 'sash', 'sash', 'service'] if s == 0 else ['sash']*4,
        3: lambda s: [('panel', 22), ('skip', 58), ('pier', 16)],
    }
    block(hall, faces, 3, seed=51, pipes={2})
    upper, z = pitched('hall roof', hall, top, pitch=1.1, top=18, dormers={0: (.12, .88), 1: (.3, .55), 2: (.2, .4), 3: (.45, .7)}, seed=51)
    deck = flat_top('hall roof', upper, z)
    lantern = f.inset(upper, 4)
    xs, ys = [p[0] for p in lantern], [p[1] for p in lantern]
    far = min(max(ys), 49.0)  # Clear of the belvedere.
    cuboid('lantern kerb', min(xs), max(xs), min(ys), far, deck, deck+2.0, STONE, DRESSING, omit='b')
    glass_vault('lantern', min(xs)+.4, max(xs)-.4, min(ys)+.4, far-.4, deck+2.0, 10.0, bay=7.0, monitor=True)
    front = f.rect(-20, 20, -24, -16)
    block(front, {0: [('skip', 40)], 1: [('pier', 8)], 3: [('pier', 8)]}, 3, hidden={2}, seed=52)
    f.lay(lambda: great(rng, 40, 3, 11.0, 0.0, 26.0, fan=True), (-20, -24), (1, 0), 0)
    gabled('pediment', -22, 22, -27, 0, top+2.4, pitch=.5)
    # Column pairs carrying the pediment.
    cuboid('entablature', -22, 22, -27, -24, top-1.2, top+2.4, STONE, DRESSING, omit='k')
    for x in (-18.4, -13.6, 13.6, 18.4):
        cuboid('column foot', x-1.7, x+1.7, -27.4, -24, 0, 2.4, STONE, DRESSING, omit='bk')
        round_prism('column', x, -25.7, 2.4, top-2.4, 1.25, STONE, DRESSING, 10)
        cuboid('column head', x-1.6, x+1.6, -27.3, -24, top-2.4, top-1.2, STONE, DRESSING, omit='bk')
    # The doors in the portal's foot: a dark screen with timber leaves under a lit band.
    cuboid('portal screen', -11, 11, -22.0, -21.6, 0, 11.0, PAINT, IRON, omit='bk')
    for a, b in ((-8.6, -4.4), (-4.2, -.1), (.1, 4.2), (4.4, 8.6)):
        add('door leaf', PAINT, hk.TIMBER, [(a, -22.05, .2), (b, -22.05, .2), (b, -22.05, 8.4), (a, -22.05, 8.4)], [(0, 1, 2, 3)])
    add('door light', PAINT, ik.WARM_ROOM, [(-8.6, -22.05, 8.8), (8.6, -22.05, 8.8), (8.6, -22.05, 10.6), (-8.6, -22.05, 10.6)], [(0, 1, 2, 3)],
        light=ik.SHOP_GLOW)
    # The belvedere: a plain stage clear of the roof, an arched one, the louvred top.
    ring = f.rect(16, 44, 52, 80)
    stages = ['blank', 'arch', 'belfry']
    z = tower('belvedere', ring, stages, z0=top, seed=53, ground=False)
    spire('belvedere spire', ring, z, 16.0)
    pinnacles('belvedere', ring, z+hk.CORNICE, shaft=2.6, tip=4.2)
    volume('belvedere', ring, 0, (3+len(stages))*LEVEL)
    for side in (-1, 1):
        wing = f.rect(*sorted((side*44, side*104)), 0, 58)
        outer, inner = (3, 1) if side < 0 else (1, 3)
        block(wing, {0: ['glass']*2+['sash'] if side > 0 else ['sash']+['glass']*2, 2: ['glass', 'louvre', 'glass'], outer: ['glass', 'glass']}, 3,
              hidden={inner}, butt={(0, 1), (2, 0)} if side < 0 else {(0, 0), (2, 1)}, seed=54+side)
        deck = kit_roof('wing %d' % side, wing, top, 'parapet', hidden={inner}, butt={(0, 1), (2, 0)} if side < 0 else {(0, 0), (2, 1)}, seed=56+side)
        plant_deck('wing %d' % side, wing, deck, rng, 3, more=('tank', 'skylight') if side < 0 else ('duct', 'skylight'))
        volume('wing %d' % side, wing, 0, top)
        planter(*sorted((side*24, side*40)), -23, -18, 0, rng, size=3.2)
    steps(-17, 17, -34, -27.4, 1.2, 3)
    paving(-60, 60, -40, -16, .3)
    h.fixtures.append((0, -30, 12))
    volume('hall', hall, 0, top)


# -- Medical Center: a slim tower before a ward block, ward wings, a vaulted entrance (lineup) ----------------------

def medical_center():
    """The ward block, four storeys of tall sashes under a parapet with its plant; before its middle a slim tower, a
    strip of glass oriels storey on storey up its front to a plain top stage with the lit sign; a ward wing each
    side, three storeys under the kit's mansard; the entrance at the tower's foot under a vault of glass between
    stone walls, behind a stone arch; a modern glass block behind."""
    rng = random.Random(61)
    main = f.rect(-30, 30, -12, 52)
    faces = {0: lambda s: [('sash', 18), ('skip', 24), ('sash', 18)],
             1: lambda s: [('pier', 12), ('skip', 50), ('pier', 2)] if s < 3 else ['sash']*2+[('panel', 16)],
             2: lambda s: [('skip', 60)] if s < 2 else ['sash', 'sash'],
             3: lambda s: [('pier', 2), ('skip', 50), ('pier', 12)] if s < 3 else [('panel', 16)]+['sash']*2}
    block(main, faces, 4, seed=61)
    deck = kit_roof('main', main, 4*LEVEL, 'parapet', seed=62)
    plant_deck('main', f.rect(-30, 30, 4, 52), deck, rng, 2, more=('duct', 'tank'))
    # The tower: glass up its front, plain flanks with a slit a storey, the sign's stage.
    ring = f.rect(-12, 12, -22, 4)
    stages = ['glass']*6+['blank']
    flank = lambda s, kind: [('slit', 10), ('skip', 16)] if s < 4 else ('slit' if s < 6 else 'louvre')  # Its top stage: the plant room.
    faces = {0: lambda s, kind: 'entrance-med' if s == 0 else kind, 1: flank, 3: lambda s, kind: flank(s, kind)[::-1] if s < 4 else flank(s, kind),
             2: lambda s, kind: [('skip', 24)] if s < 4 else ('slit' if s < 6 else 'louvre')}
    z = tower('tower', ring, stages, faces, seed=63)
    deck = kit_roof('tower', ring, z, 'parapet', seed=64)
    f.lay(lambda: hk.plant(rng), (0, -7), (1, 0), deck)
    for dx in (-3, 3):
        kb.bar('mast', [(dx, -17, deck), (dx, -17, deck+8+abs(dx))], .22, IRON, fine=False)
    front = -22-PILASTER_OUT-.7
    cuboid('med sign', -4.2, 4.2, front, front+.4, 6*LEVEL+4.0, 6*LEVEL+12.4, PAINT, ik.TEAL, omit='bk', light=(.10, .55, .50))
    for a0, a1, b0, b1 in ((-2.8, 2.8, 7.3, 9.1), (-.9, .9, 5.4, 11.0)):
        add('med cross', PAINT, (.92, .92, .88), [(a0, front-.06, 6*LEVEL+b0), (a1, front-.06, 6*LEVEL+b0), (a1, front-.06, 6*LEVEL+b1),
                                                 (a0, front-.06, 6*LEVEL+b1)], [(0, 1, 2, 3)], light=(.80, .80, .74))
    for side in (-1, 1):
        wing = f.rect(*sorted((side*30, side*100)), 0, 50)
        outer, inner = (3, 1) if side < 0 else (1, 3)
        block(wing, {0: lambda s: ['arch', 'sash', 'sash'] if s == 0 else ['sash']*3, 2: lambda s: ['service', 'sash', 'sash'] if s == 0 else ['sash']*3,
                     outer: ['sash', 'sash']}, 3, hidden={inner}, butt={(0, 1), (2, 0)} if side < 0 else {(0, 0), (2, 1)}, seed=65+side, pipes={0})
        deck = kit_roof('wing %d' % side, wing, 3*LEVEL, hidden={inner}, butt={(0, 1), (2, 0)} if side < 0 else {(0, 0), (2, 1)}, seed=67+side)
        f.lay(lambda: hk.skylight(rng), (side*66, 25), (1, 0), deck)
        f.lay(lambda: hk.chimney(rng), (side*90, 25), (0, 1), deck)
        volume('wing %d' % side, wing, 0, 3*LEVEL)
        planter(*sorted((side*36, side*66)), -9, -4, 0, rng, size=3.4)
    rear = f.rect(-40, 40, 52, 96)
    block(rear, {0: [('glass', 10), ('skip', 60), ('glass', 10)], 1: ['glass', 'louvre'], 2: ['glass', 'glass', 'glass'], 3: ['louvre', 'glass']}, 2,
          seed=69)
    deck = kit_roof('rear', rear, 2*LEVEL, 'parapet', seed=70)
    plant_deck('rear', rear, deck, rng, 3)
    # The entrance: a glass vault between stone walls, a stone arch at its front.
    y0, y1, spring = -48.0, -22.0, 9.0
    for side in (-1, 1):
        a, b = sorted((side*12, side*14.4))
        cuboid('vault wall', a, b, y0, y1, 0, spring+.6, STONE, DRESSING, omit='b')
    glass_vault('entrance vault', -12, 12, y0+1, y1, spring, 7.0, bay=8.0, ends=())

    def arch_front():
        half, low, top = 11.4, 4.4, spring+8.4  # The arch as wide and as high as the vault behind it.
        facade('wall', [hk.arch_hole(14.4, half, 0, low)], 0, top, 28.8, WALL, du=12, dv=9, key=STONE)
        hk.arch('vault front', 14.4, half, 0, low, STONE, WALL, 1.6, ring=1.4, shade=hk.SHADE)
        cuboid('vault front cap', -.6, 29.4, -.8, 1.6, top, top+1.0, STONE, DRESSING)
        add('vault front back', STONE, hk.REVEAL, [(28.8, 1.6, low+half), (0, 1.6, low+half), (0, 1.6, top), (28.8, 1.6, top)], [(0, 1, 2, 3)])
    f.lay(arch_front, (-14.4, y0), (1, 0), 0)
    paving(-34, 34, -56, -12, .3)
    h.fixtures.extend([(0, -34, 8), (0, -26, 8)])
    volume('main', main, 0, 4*LEVEL)
    volume('tower', ring, 0, len(stages)*LEVEL)
    volume('rear', rear, 0, 2*LEVEL)


# -- Cathedral: a French Gothic great church, without a transept (after Bourges) -------------------------------------
BUTTRESS = 4.4  # How far along a tower's wall its corner buttress reaches.
FLECHE = (.37, .40, .42)  # The fleche's lead, paler than the slate it stands on.
def portal(length, half, spring, height, post=False):
    """A cathedral's door in a wall `height` tall: timber leaves deep in its wall
    in three orders on their shafts, a stone tympanum over them, under a steep open gable; post, a stone post between
    its leaves."""
    cx, depth = length/2, 3.2
    crown = spring+hk.rise(half, True)
    facade('wall', [hk.arch_hole(cx, half, 0, spring, True)], 0, height, length, WALL, du=12, dv=9, key=STONE)
    outline = hk.arch('portal', cx, half, 0, spring, STONE, WALL, depth, ring=2.0, pointed=True, shade=hk.SHADE)
    back = depth-.06
    add('portal back', PAINT, k.DARK_BACK, [(cx-half, depth, 0), (cx+half, depth, 0), (cx+half, depth, crown), (cx-half, depth, crown)], [(0, 1, 2, 3)])
    for a, b in ((cx-half+.2, cx-.3), (cx+.3, cx+half-.2)):
        add('portal leaf', PAINT, hk.TIMBER, [(a, back, .1), (b, back, .1), (b, back, spring), (a, back, spring)], [(0, 1, 2, 3)])
    add('portal tympanum', STONE, hk.REVEAL, outline, [tuple(range(len(outline)))])
    cuboid('portal lintel', cx-half, cx+half, depth-.6, depth-.05, spring-.45, spring+.45, STONE, DRESSING, omit='bk')
    for step in (1, 2):  # The inner orders: each an arch's face a step deeper and narrower, on a shaft each side.
        y, inner = step*1.05, half-step*1.1
        ring, grown = hk.arch_curve(cx, inner, spring, True), hk.arch_curve(cx, inner, spring, True, 1.25)
        for (a, b), (c, d) in zip(zip(ring, ring[1:]), zip(grown, grown[1:])):
            facing('portal order', STONE, DRESSING if step == 1 else WALL, [(a[0], y, a[1]), (b[0], y, b[1]), (d[0], y, d[1]), (c[0], y, c[1])], (0, -1, 0))
        for side in (-1, 1):
            x = cx+side*(inner+.6)
            cuboid('portal shaft', x-.5, x+.5, y-.7, y, 0, spring, STONE, DRESSING, omit='bk')
    if post:
        cuboid('portal post', cx-.55, cx+.55, depth-.9, depth-.05, 0, spring, STONE, DRESSING, omit='bk')
    foot, apex, wide, out, band = spring+1.2, min(crown+7.0, height-.6), half+3.4, 1.1, 1.3
    for side in (-1, 1):
        for i in range(2):  # Jamb shafts.
            x = cx+side*(half+1.0+i*1.6)
            cuboid('portal shaft', x-.45, x+.45, -1.0, -.1, 0, spring, STONE, DRESSING, omit='bk')
        cuboid('portal impost', *sorted((cx+side*(half+.3), cx+side*(half+3.3))), -1.2, 0, spring, spring+.8, STONE, DRESSING, omit='k')
        # The gable's raking coping, from the imposts up to its point over the arch.
        verts = [(cx+side*wide, -out, foot), (cx+side*(wide-band), -out, foot), (cx, -out, apex-band*1.6), (cx, -out, apex)]
        facing('portal gable', STONE, DRESSING, verts, (0, -1, 0))
        verts = [(cx+side*wide, -out, foot), (cx, -out, apex), (cx, 0, apex), (cx+side*wide, 0, foot)]
        facing('portal gable', STONE, DRESSING, verts, (side, 0, 1))
    back_wall(length, 0, height, depth+.1)


def gallery(rng, length, margin=0.0):
    """A storey of blind arcade: pointed arches shoulder to shoulder, deep in the wall, `margin` clear of its ends (a
    tower's corner buttresses stand there)."""
    count = max(2, round((length-2*PILASTER-2*margin)/6.4))
    pitch = (length-2*PILASTER-2*margin)/count
    half, sill, spring, depth = pitch/2-1.0, 2.6, 8.0, 1.1
    centres = [PILASTER+margin+(i+.5)*pitch for i in range(count)]
    hk.frame(length, [hk.arch_hole(cx, half, sill, spring, True) for cx in centres], False)
    for cx in centres:
        hk.arch('gallery', cx, half, sill, spring, STONE, WALL, depth, pointed=True)
        top = spring+hk.rise(half, True)
        add('gallery back', STONE, hk.SHADE, [(cx-half, depth, sill), (cx+half, depth, sill), (cx+half, depth, top), (cx-half, depth, top)], [(0, 1, 2, 3)])


def rose(rng, length, height, radius):
    """A west front's rose: a great round window deep in its wall, jewel glass that glows from within behind stone
    spokes, a hub and a ring."""
    cx, cz, depth, n, box = length/2, height/2, 2.6, 24, radius+2.2
    facade('wall', [(cx-box, cx+box, cz-box, cz+box)], 0, height, length, WALL, du=12, dv=9, key=STONE)
    at = lambda r, i, y: (cx+r*math.cos(math.tau*i/n), y, cz+r*math.sin(math.tau*i/n))

    def corner(i):  # The square's point a ring point looks at: the middle of a side, else its quadrant's corner.
        c, sn = math.cos(math.tau*i/n), math.sin(math.tau*i/n)
        return cx+(0 if abs(c) < 1e-6 else math.copysign(box, c)), 0, cz+(0 if abs(sn) < 1e-6 else math.copysign(box, sn))
    for i in range(n):
        facing('rose wall', STONE, WALL, distinct([corner(i), corner(i+1)])+[at(radius, i+1, 0), at(radius, i, 0)], (0, -1, 0))
        facing('rose ring', STONE, DRESSING, [at(radius, i, -.4), at(radius, i+1, -.4), at(radius+1.8, i+1, -.4), at(radius+1.8, i, -.4)], (0, -1, 0))
        verts = [at(radius, i, 0), at(radius, i+1, 0), at(radius, i+1, depth), at(radius, i, depth)]
        mid = at(radius, i+.5, 0)
        facing('rose reveal', STONE, hk.SHADE, verts, (cx-mid[0], 0, cz-mid[2]))
    add('rose back', PAINT, k.DARK_BACK, [(cx-radius, depth, cz-radius), (cx+radius, depth, cz-radius), (cx+radius, depth, cz+radius),
                                         (cx-radius, depth, cz+radius)], [(0, 1, 2, 3)])
    hub, ring, glass, stone = radius*.22, radius*.6, depth-.06, depth-.6
    pane = lambda verts: stained('rose', verts, rng)
    for i in range(n):  # Twelve petals round the hub, twenty-four round those, a spoke between each two.
        pane([at(ring, i, glass), at(radius, i, glass), at(radius, i+1, glass), at(ring, i+1, glass)])
        if i % 2 == 0:
            pane([at(hub, i, glass), at(ring, i, glass), at(ring, i+1, glass), at(ring, i+2, glass), at(hub, i+2, glass), at(hub, i+1, glass)])
        a, b = at(hub if i % 2 == 0 else ring, i, stone), at(radius, i, stone)
        reach = math.dist(a, b)
        wx, wz = -(b[2]-a[2])/reach*.32, (b[0]-a[0])/reach*.32
        facing('rose spoke', STONE, DRESSING, [(a[0]-wx, stone, a[2]-wz), (a[0]+wx, stone, a[2]+wz), (b[0]+wx, stone, b[2]+wz), (b[0]-wx, stone, b[2]-wz)],
               (0, -1, 0))
        for r in (hub, ring):
            facing('rose tracery', STONE, DRESSING, [at(r-.42, i, stone), at(r+.42, i, stone), at(r+.42, i+1, stone), at(r-.42, i+1, stone)], (0, -1, 0))
    facing('rose stained glass', PAINT, JEWELS[3], [at(hub-.4, i, glass) for i in range(0, n, 2)], (0, -1, 0), light='night')
    back_wall(length, 0, height, depth+.1)


def buttress(low, top, size=1.0):
    """A pier buttress standing out of an aisle's wall about x 0: two stages with weathered offsets, rising over the
    aisle's roof to `top` (to carry a flyer), under a pinnacle; `size` scales its plan."""
    a, b, out, back = 2.6*size, 2.2*size, 6.4*size, 4.4*size
    cuboid('buttress', -a, a, -out, 0, 0, low, STONE, DRESSING, omit='bk')
    facing('buttress', STONE, DRESSING, [(-a, -out, low), (a, -out, low), (b, -back, low+3.4*size), (-b, -back, low+3.4*size)], (0, -1, 1))
    cuboid('buttress', -b, b, -back, 1.0, low, top, STONE, DRESSING, omit='b')
    pinnacles('buttress', [(0, -1.7*size)], top, half=1.5*size, shaft=4.2*size, tip=7.5*size, inset=0)


def east_roof(name, walls, y1, eave, ridge):
    """The slate roof over a polygonal east end, `walls` its ring from one side of the nave round to the other: a facet
    a side from the eave up to the nave's ridge at (0, y1), a copper roll on each hip."""
    top = [(x*(1+.8/math.hypot(x, y-y1)), y1+(y-y1)*(1+.8/math.hypot(x, y-y1))) for x, y in walls]
    for a, b in zip(top, top[1:]):
        facing(name+' roof', SLATE, (1, 1, 1), [(*a, eave-1.0), (*b, eave-1.0), (0, y1, ridge)], (*f.outward(a, b), 1))
    for point in top:
        kb.bar(name+' hip', [(*point, eave-.8), (0, y1, ridge+.15)], .32, VERDIGRIS, fine=False)


def lean_to(name, side, a, b, y0, y1, z, rise, ends=()):
    """A lean-to roof of slate along y from the wall at x side*a, `z` tall, up `rise` to the wall at side*b: a stone
    cornice, a lead flashing at its head, a stone end under it at each of `ends` (y, the way it faces)."""
    for y, way in ends:
        facing(name+' roof end', STONE, WALL, [(side*a, y, z), (side*(a+1.7), y, z+1.5), (side*b, y, z+rise), (side*b, y, z)], (0, way, 0))
    cuboid(name+' cornice', *sorted((side*a, side*(a+1.4))), y0, y1, z, z+1.4, STONE, DRESSING, omit='b')
    facing(name+' roof', SLATE, (1, 1, 1), [(side*(a+1.7), y0, z+1.5), (side*(a+1.7), y1, z+1.5), (side*b, y1, z+rise), (side*b, y0, z+rise)], (side, 0, 1))
    cuboid(name+' roof head', *sorted((side*b, side*(b+1.2))), y0, y1, z+rise-.2, z+rise+.8, PAINT, LEAD, omit='b')


def front_buttress(x0, x1, stages):
    """One of a tower's great buttresses, from x0 to x1 along its wall: stages (z0, z1, how far out), a weathered offset
    over each."""
    for (z0, z1, out), after in zip(stages, stages[1:]+[None]):
        cuboid('front buttress', x0, x1, -out, 0, z0, z1, STONE, DRESSING, omit='bt')
        back = after[2] if after else 0.0
        facing('front buttress', STONE, DRESSING, [(x0, -out, z1), (x1, -out, z1), (x1, -back, z1+(out-back)*1.6), (x0, -back, z1+(out-back)*1.6)], (0, -1, 1))
        for x, side in ((x0, -1), (x1, 1)):
            facing('front buttress', STONE, DRESSING, [(x, -out, z1), (x, -back, z1+(out-back)*1.6), (x, -back, z1)], (side, 0, 0))


def flyer(a, b, z0, z1, wide=2.2, rib=1.9):
    """A flying buttress from a pier at a up to the wall at b: a quarter arch springing at z0 on the pier to z1 on the
    wall, a stone rib `rib` deep along it, filled up to a straight raking top where that runs higher."""
    (ux, uy), length, n = f.unit(a, b), math.dist(a, b), 6
    at = lambda t, side, z: (a[0]+ux*length*t-uy*side*wide/2, a[1]+uy*length*t+ux*side*wide/2, z)
    under = lambda t: z1-rib-(z1-rib-z0)*(1-math.sqrt(1-(1-t)**2))
    over = lambda t: max(z0+9.0+(z1-z0-9.0)*t, under(t)+rib)
    for i in range(n):
        t0, t1 = i/n, (i+1)/n
        for side in (-1, 1):
            facing('flyer', STONE, DRESSING, [at(t0, side, under(t0)), at(t1, side, under(t1)), at(t1, side, over(t1)), at(t0, side, over(t0))],
                   (-uy*side, ux*side, 0))
        facing('flyer', STONE, DRESSING, [at(t0, -1, over(t0)), at(t0, 1, over(t0)), at(t1, 1, over(t1)), at(t1, -1, over(t1))], (-ux, -uy, 3))
        facing('flyer', STONE, hk.REVEAL, [at(t0, -1, under(t0)), at(t0, 1, under(t0)), at(t1, 1, under(t1)), at(t1, -1, under(t1))], (ux, uy, -3))


def fleche(x, y, z, height):
    """A slender lead spire astride a roof's ridge: a louvred stage, an open lantern of four posts, a plain iron point."""
    base = f.rect(x-3.2, x+3.2, y-3.2, y+3.2)
    f.wall_ring('fleche', base, z-7, z+10, PAINT, FLECHE)
    for (px, py), (qx, qy) in zip(base, base[1:]+base[:1]):
        nx, ny = f.outward((px, py), (qx, qy))
        mx, my = (px+qx)/2+nx*.06, (py+qy)/2+ny*.06
        tx, ty = (qx-px)/6.4*1.9, (qy-py)/6.4*1.9
        facing('fleche louvre', SLATS, LOUVRE, [(mx-tx, my-ty, z+2.4), (mx+tx, my+ty, z+2.4), (mx+tx, my+ty, z+8.6), (mx-tx, my-ty, z+8.6)], (nx, ny, 0))
    f.cap('fleche', base, z+10, PAINT, FLECHE)
    lantern = z+10+7.0
    for px, py in f.inset(base, .5):
        cuboid('fleche post', px-.5, px+.5, py-.5, py+.5, z+10, lantern, PAINT, FLECHE, omit='bt')
    eave = f.inset(base, -.7)
    for i in range(4):
        add('fleche', PAINT, FLECHE, [(*eave[i], lantern), (*eave[(i+1) % 4], lantern), (x, y, lantern+height)], [(0, 1, 2)])
    add('fleche soffit', PAINT, IRON, [(*point, lantern) for point in eave][::-1], [(0, 1, 2, 3)])
    finial('fleche', x, y, lantern+height, 5.5)


def front_gable(nave, face, high):
    """What ends a west front over its upper gallery (from `high` up a storey, between x -nave and nave at y face): a
    coping, the gallery's stone back and ends, a small gable under a pinnacle."""
    screen_top = high+LEVEL
    cuboid('screen coping', -nave, nave, face-1.6, face+3.4, screen_top, screen_top+1.0, STONE, DRESSING, omit='b')
    facing('screen back', STONE, WALL, [(-nave, face+2.4, high), (nave, face+2.4, high), (nave, face+2.4, screen_top), (-nave, face+2.4, screen_top)],
           (0, 1, 0))
    peak = screen_top+1.0+9.0
    for y, way in ((face-.6, -1), (face+2.4, 1)):
        facing('front gable', STONE, WALL, [(-11, y, screen_top+1.0), (11, y, screen_top+1.0), (0, y, peak)], (0, way, 0))
    for side in (-1, 1):
        facing('front gable', STONE, DRESSING, [(side*11.6, face-.9, screen_top+.8), (side*11.6, face+2.7, screen_top+.8), (0, face+2.7, peak+.5), (0, face-.9, peak+.5)],
               (side, 0, 1))
    pinnacles('front gable', [(0, face+.9)], peak-1.2, half=1.3, shaft=3.0, tip=6.0, inset=0)
    for side in (-1, 1):
        facing('screen end', STONE, WALL, [(side*nave, face, high), (side*nave, face+2.4, high), (side*nave, face+2.4, screen_top), (side*nave, face, screen_top)],
               (side, 0, 0))


def cathedral():
    """A great church in the French Gothic manner, with double aisles and five portals as Bourges has them, and no
    transept: its plan is one long vessel. The nave six levels tall under a steep slate roof, over an inner
    aisle of four and an outer aisle of two, each under its lean-to roof, each with its windows, a tier of flying
    buttresses over each aisle; a double ambulatory round the choir; the west front five bays wide, a portal in each,
    the towers over the outermost. It fills three columns of hexes. No figures, crosses or emblems."""
    rng = random.Random(81)
    nave, inner, outer, y0, y1 = 22.0, 46.0, 74.0, 10.0, 200.0  # Half the nave's width; the aisles' walls; the nave's ends.
    low, mid, high = 2*LEVEL, 4*LEVEL, 6*LEVEL  # The walls' tops: the outer aisles', the inner aisles', the nave's.
    rise, count, span = 12.0, 8, y1-y0  # How far a lean-to roof climbs.
    # The towers' front (a hex's middle row lies at y -36: a unit in a tower's hex stands on the apron before it); the
    # bays' between them; a tower's width.
    front, face, width = -20.0, -16.0, 30.0

    def upper(above):
        """A wall that shows over a lean-to roof from storey `above`: a plain storey behind the roof, windows over it."""
        return lambda s: [('skip', span)] if s < above else ['blank' if s == above else 'stained-high']*count

    def tiers(at, out, along):
        """A bay's two piers and flyers, `out` from the nave's wall through `at`, a point on its middle line."""
        for wall, to, z in ((outer, inner, low), (inner, nave, mid)):
            f.lay(lambda: buttress(z+4 if wall == outer else z-8, z+18), (at[0]+out[0]*wall, at[1]+out[1]*wall), along, 0)
            flyer((at[0]+out[0]*(wall-1.0), at[1]+out[1]*(wall-1.0)), (at[0]+out[0]*to, at[1]+out[1]*to), z+6, z+2*LEVEL-8)

    block(f.rect(-nave, nave, y0, y1), {1: upper(4), 3: upper(4)}, 6, hidden={0, 2}, butt={(1, 0), (1, 1), (3, 0), (3, 1)}, seed=81, ground=False)
    ridge = gabled('nave roof', -nave, nave, face+2.4, y1, high, pitch=1.25, fronts=())
    lancets = lambda s: ['stained-low' if s == 0 else 'stained-high']*count
    for side in (-1, 1):
        edge = 1 if side > 0 else 3
        walls = {'hidden': {0, 1, 2, 3}-{edge}, 'butt': {(edge, 0), (edge, 1)}}
        block(f.rect(*sorted((side*nave, side*inner)), y0, y1), {edge: upper(2)}, 4, seed=82+side, ground=False, **walls)
        block(f.rect(*sorted((side*inner, side*outer)), y0, y1), {edge: lancets}, 2, seed=84+side, ground=True, **walls)
        lean_to('outer aisle', side, outer, inner, y0, y1, low, rise)
        lean_to('inner aisle', side, inner, nave, y0, y1, mid, rise, ((y0, -1),))  # Its end shows over the front's inner bay.
        for i in range(1, count+1):
            tiers((0, y0+span*i/count), (side, 0), (0, side))
        # The nave's side between the front and its first bay, over the front's inner bay.
        cuboid('front return', *sorted((side*nave, side*(nave-2.4))), face, y0, mid, high, STONE, WALL, omit='b')
        volume('inner aisle %d' % side, f.rect(*sorted((side*nave, side*inner)), face, y1), 0, mid)
        volume('outer aisle %d' % side, f.rect(*sorted((side*inner, side*outer)), y0, y1), 0, low)
    fleche(0, y0+span*.72, ridge, 50.0)
    # The chevet: the choir's five sides over a double ambulatory.
    turns = [math.radians(36*i) for i in range(6)]
    ring = lambda r: [(r*math.cos(a), y1+r*math.sin(a)) for a in turns]
    grown = lambda points, by: [(x*by, y1+(y-y1)*by) for x, y in points]
    ends = {(0, 0), (4, 1)}
    for r, top, above in ((nave, 6, 4), (inner, 4, 2)):
        length = 2*r*math.sin(math.radians(18))
        spec = lambda s, above=above, length=length: [('skip', length)] if s < above else ('blank' if s == above else 'stained-high')
        block(ring(r), {i: spec for i in range(5)}, top, hidden={5}, butt=ends, seed=86+top, ground=False)
        volume('chevet %d' % top, ring(r), 0, top*LEVEL)
    block(ring(outer), {i: (lambda s: 'stained-low' if s == 0 else 'stained-high') for i in range(5)}, 2, hidden={5}, butt=ends, seed=89, ground=True)
    volume('ambulatory', ring(outer), 0, low)
    for r, to, z in ((outer, inner, low), (inner, nave, mid)):
        walk, eave, head = ring(r), grown(ring(r), 1+1.7/r), ring(to)
        for i in range(5):
            (ax, ay), (bx, by) = walk[i], walk[i+1]
            nx, ny = f.outward(walk[i], walk[i+1])
            facing('ambulatory roof', SLATE, (1, 1, 1), [(*eave[i], z+1.5), (*eave[i+1], z+1.5), (*head[i+1], z+rise), (*head[i], z+rise)], (nx, ny, 1))
            facing('ambulatory cornice', STONE, DRESSING, [(ax+nx*1.4, ay+ny*1.4, z), (bx+nx*1.4, by+ny*1.4, z), (bx+nx*1.4, by+ny*1.4, z+1.4),
                                                           (ax+nx*1.4, ay+ny*1.4, z+1.4)], (nx, ny, 0))
    east_roof('choir', ring(nave), y1, high, ridge)
    for a in turns[1:5]:
        tiers((0, y1), (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a)))
    # The west front: the towers over its outermost bays; between them the nave's bay and an inner bay each side.
    stages = ['blank', 'blank', 'gallery', 'slit', 'stained-low', 'stained-high', 'gallery', 'belfry', 'belfry']
    steps = [(0, 2*LEVEL, 6.0), (2*LEVEL, high, 4.2), (high, 8*LEVEL, 2.4)]
    for side in (-1, 1):
        near, far = side*(outer-width), side*outer
        tower_ring = f.rect(*sorted((near, far)), front, y0)
        # Its inner side stands behind the front's inner bay for four storeys; its back behind the outer aisle for two,
        # plain over that aisle's roof for two more, and behind the inner aisle (the last 2 of it) for all four.
        between = lambda s, kind, side=side: kind if s >= 4 else ([('pier', face-front), ('skip', y0-face)][::-side])
        behind = lambda s, kind, side=side: kind if s >= 4 else [('skip', width)] if s < 2 else [('blank', outer-inner), ('skip', inner-outer+width)][::side]
        faces = {0: lambda s, kind: [('skip', width)] if s < 2 else kind, 1 if side < 0 else 3: between, 2: behind}
        z = tower('west tower', tower_ring, stages, faces, seed=90+side, ground=False)
        f.lay(lambda: portal(width, 7.0, 9.5, 2*LEVEL), (tower_ring[0][0], front), (1, 0), 0)
        spire('west spire', tower_ring, z, 66.0)
        pinnacles('west tower', f.inset(tower_ring, -.6), z+hk.CORNICE, half=2.0, shaft=8.0, tip=11.0, inset=0)
        for x, inward in ((near, side), (far, -side)):
            f.lay(lambda: front_buttress(*sorted((-1.2*inward, BUTTRESS*inward)), steps), (x, front), (1, 0), 0)
        deep = y0-front
        origin, along = ((far, front), (0, 1)) if side > 0 else ((far, y0), (0, -1))
        for a, b in ((-1.2, BUTTRESS), (deep-BUTTRESS, deep)) if side > 0 else ((0, BUTTRESS), (deep-BUTTRESS, deep+1.2)):
            f.lay(lambda: front_buttress(a, b, steps), origin, along, 0)
        volume('west tower %d' % side, tower_ring, 0, len(stages)*LEVEL)
        # The inner bay: a portal, a gallery and a window under a coping, its roof a paved flat before the aisle's.
        x0, wide = min(side*nave, near), outer-width-nave
        f.lay(lambda: portal(wide, 5.5, 9.0, 2*LEVEL), (x0, face), (1, 0), 0)
        f.lay(lambda: gallery(rng, wide), (x0, face), (1, 0), 2*LEVEL)
        f.lay(piece('stained-high', False, rng, wide), (x0, face), (1, 0), 3*LEVEL)
        cuboid('bay coping', x0, x0+wide, face-1.6, face+1.6, mid, mid+1.0, STONE, DRESSING, omit='b')
        f.cap('bay roof', f.rect(x0, x0+wide, face, y0), mid-.05, PAVERS, DECK_TONE)
        f.lay(lambda: front_buttress(*sorted((-1.2*side, BUTTRESS*side)), steps[:2]), (side*nave, face), (1, 0), 0)
    f.lay(lambda: portal(2*nave, 10.0, 12.0, 2*LEVEL, post=True), (-nave, face), (1, 0), 0)
    f.lay(lambda: gallery(rng, 2*nave), (-nave, face), (1, 0), 2*LEVEL)
    f.lay(lambda: rose(rng, 2*nave, 3*LEVEL, 19.0), (-nave, face), (1, 0), 3*LEVEL)
    f.lay(lambda: gallery(rng, 2*nave), (-nave, face), (1, 0), high)
    front_gable(nave, face, high)
    paving(-88, 88, front-44, face+3.4, .3)  # In under the portals' leaves.
    for x in (-59, -33, 0, 33, 59):
        h.fixtures.append((x, front-6, 9))
    volume('nave', f.rect(-nave, nave, face, y1), 0, high)


# -- Church: a town church one hex wide, a single west tower --------------------------------------------------------

def church():
    """A town church in the cathedral's manner, one hex wide: a single tower before its nave, a gabled portal in its
    foot and a rose over it, tall lancets up its flanks, a blind arcade and a belfry under a slate spire between pinnacles; a nave of tall stained
    lancets over low aisles under lean-to roofs, small pier buttresses with pinnacles between their bays; a three-sided
    apse. No figures, crosses or emblems."""
    rng = random.Random(91)
    nave, aisle, y0, y1, half = 14.0, 29.0, -10.0, 100.0, 15.0  # Half the nave's width; the aisles' walls; the nave's ends; half the tower.
    low, high, rise, count = LEVEL, 4*LEVEL, 10.0, 5  # The aisles' walls; the nave's; the lean-to roofs' climb; the bays.
    front, span = y0-26.0, y1-y0  # The tower is 26 deep.
    block(f.rect(-nave, nave, y0, y1), {i: (lambda s: [('skip', span)] if s == 0 else ['blank', 'stained-low', 'stained-high'][s-1:s]*count) for i in (1, 3)},
          4, hidden={0, 2}, butt={(1, 0), (1, 1), (3, 0), (3, 1)}, seed=91, ground=False)
    ridge = gabled('nave roof', -nave, nave, y0, y1, high, pitch=1.25, fronts=())
    for side in (-1, 1):
        ring = f.rect(*sorted((side*nave, side*aisle)), y0, y1)
        # Its front beside the tower, its outer wall and its east end; the nave stands along its fourth side.
        west = [('skip', half-nave), ('stained-one', aisle-half)][::side]
        outer, inner = (1, 3) if side > 0 else (3, 1)
        block(ring, {0: west, outer: ['stained-one']*count, 2: 'stained-one'}, 1, hidden={inner}, butt={(0, 0), (2, 1)} if side > 0 else {(0, 1), (2, 0)},
              seed=92+side, ground=True)
        lean_to('aisle', side, aisle, nave, y0, y1, low, rise, ((y0, -1), (y1, 1)))
        for i in range(count+1):
            f.lay(lambda: buttress(low-5, low+8, .6), (side*aisle, y0+span*i/count), (0, side), 0)
        volume('aisle %d' % side, ring, 0, low)
    # The apse: three sides, a window low in each and the nave's lancets over it.
    turns = [math.radians(60*i) for i in range(4)]
    apse = [(nave*math.cos(a), y1+nave*math.sin(a)) for a in turns]
    block(apse, {i: (lambda s: ('stained-one', 'blank', 'stained-low', 'stained-high')[s]) for i in range(3)}, 4, hidden={3}, butt={(0, 0), (2, 1)}, seed=94,
          ground=False)
    east_roof('apse', apse, y1, high, ridge)
    for a in turns[1:3]:
        f.lay(lambda: buttress(2*LEVEL+4, 3*LEVEL+8, .6), (nave*math.cos(a), y1+nave*math.sin(a)), (-math.sin(a), math.cos(a)), 0)
    volume('apse', apse, 0, high)
    # The tower: the portal and the rose in its front, plain flanks, the arcade and the belfry clear of the nave's roof.
    ring = f.rect(-half, half, front, y0)
    stages = ['blank', 'slit', 'stained-low', 'stained-high', 'gallery', 'belfry']
    faces = {0: lambda s, kind: [('skip', 2*half)] if s < 4 else kind,
             2: lambda s, kind: kind if s > 4 else 'blank' if s == 4 else [('pier', half-nave), ('skip', 2*nave), ('pier', half-nave)]}
    z = tower('tower', ring, stages, faces, seed=95, ground=False)
    f.lay(lambda: portal(2*half, 6.0, 9.0, 2*LEVEL), (-half, front), (1, 0), 0)
    f.lay(lambda: rose(rng, 2*half, 2*LEVEL, 9.0), (-half, front), (1, 0), 2*LEVEL)
    spire('spire', ring, z, 70.0)
    pinnacles('tower', f.inset(ring, -.6), z+hk.CORNICE, half=1.6, shaft=6.0, tip=9.0, inset=0)
    steps, reach, deep = [(0, 2*LEVEL, 3.6), (2*LEVEL, high, 2.4), (high, 5*LEVEL, 1.4)], 3.6, y0-front
    for side in (-1, 1):  # A buttress each way at both front corners.
        f.lay(lambda: front_buttress(*sorted((-1.2*side, reach*side)), steps), (-side*half, front), (1, 0), 0)
        origin, along, at = (((half, front), (0, 1), (-1.2, reach)) if side > 0 else ((-half, y0), (0, -1), (deep-reach, deep+1.2)))
        f.lay(lambda: front_buttress(*at, steps), origin, along, 0)
    paving(-34, 34, front-22, front+3.4, .3)  # In under the portal's leaves.
    h.fixtures.append((0, front-6, 9))
    volume('nave', f.rect(-nave, nave, y0, y1), 0, high)
    volume('tower', ring, 0, len(stages)*LEVEL)


BUILDINGS = {'cathedral': cathedral, 'church': church, 'government-hall': government_hall, 'transit-terminal': transit_terminal, 'administrative-offices': administrative_offices,
             'commercial-center': commercial_center, 'medical-center': medical_center}
FINE = ('flyer', 'buttress pinnacle', 'portal shaft', 'portal order', 'rose tracery', 'rose spoke', 'fleche louvre', 'fleche post', 'mullion', 'transom', 'lamp cap', 'baluster', 'channel', 'course shadow', 'quoin', 'impost', 'fan', 'fanlight bar',
        'dormer bar', 'keystone', 'sill', 'downpipe', 'hand', 'duct foot', 'tank leg')


def finish(obj):
    """A part's amber night light, and roofing without UVs laid down its slope."""
    ik.warm(obj)
    if 'stained glass' in obj.name and obj.get('building_night_emission'):
        shared.emissive(obj, tuple(obj['pigment']), night=True)
    if not obj.data.uv_layers and obj['board_material'] in hk.ROOFING:
        ik.roof_uvs(obj, hk.ROOFING[obj['board_material']])


def build(name):
    # Limestone takes a building's tint, as the kit's.
    return kb.build('heritage-'+name, BUILDINGS[name], finish, lambda obj: obj['board_material'] == STONE, FINE)


kb.use(piece, fill, (), downpipes)

if __name__ == '__main__' and '--' in sys.argv:
    args = sys.argv[sys.argv.index('--')+1:]
    build(args[0])
    if len(args) > 1:
        u.sheet(args[0], args[1])
