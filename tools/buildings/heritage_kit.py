"""The Heritage look as a connected building kit: its pieces GLB and kit JSON.

Run: blender -b --factory-startup --python heritage_kit.py
Writes data/models/buildings/heritage/heritage-pieces.glb and heritage.json, for the game's bays kit (GeneratedKit,
BayKit), as theme_kits writes the other looks' (its piece frame, levels of detail and export).

Heritage: pale limestone ashlar over a channelled ground storey, brick with stone dressings on its works, round-arched
windows under keystones, tall sashes, iron balconies, deep ground arcades, timber doors under a columned porch; against
them the modern hand, glass oriels in steel frames, and the plant of a working building on the roofs. Every bay runs
between half pilasters and every storey ends in a string course. Three roofs. The mansard: a stone cornice, a tall
skirt of slate with dormers up to a copper curb round a deck of paving. The parapet: a coped stone wall round a flat
roof; the battlement, that with merlons. A facet cuts each convex corner: on it a pier of quoins, or a round turret that
stands out of both walls and ends over the roof in a bell-cast copper cone (on a battlement, in merlons of its own). The
turrets are drawn only: the game stands units on the roof's deck, which they leave out. Variants name what the
buildings are: habitat (arcades, balconies, turrets), tower, offices, commercial, medical, industrial and a hangar's
hall (brick under parapets), and armoury (stone, battlements, turrets).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import civic_blocks as c
import civic_habitat as h
import imperial_kit as ik
import theme_kits as k
from civic_blocks import HAZARD
from civic_habitat import CAST, PAINT, PALE_GLASS, SLATS, add, cuboid, deck, disc, round_prism
from theme_kits import LEVEL, W, back_wall, facade, front, mullions, recess

STONE = 'structures/heritage/limestone'  # Pale warm ashlar in its albedo, blocks 6 by 3: drawn near white.
BRICK = 'structures/heritage/brick'
SLATE = 'structures/heritage/slate'  # Blue-grey slates in level courses.
COPPER = 'structures/heritage/copper'  # Verdigris, seams down the slope.
ROOF_DECK = ik.ROOF_DECK  # Grey pavers: roofs and pavements.
REPEAT, SLATE_REPEAT, COPPER_REPEAT = 18.0, 12.0, 16.0
WALL, DRESSING, RUSTIC = (.94, .93, .91), (1, 1, 1), (.84, .82, .79)  # Ashlar, its dressings, the ground storey.
BRICK_TONE = (1, 1, 1)
REVEAL = (.72, .70, .66)  # Stone in an opening's shade.
SHADE = (.46, .44, .41)  # Stone deep in an arcade.
JOINT, QUOIN_JOINT = (.30, .27, .23), (.56, .53, .49)  # A joint's shadow line: the ground storey's channels, a quoin's.
IRON = (.13, .14, .15)  # Frames, rails, lamps, finials.
LEAD = (.26, .28, .29)
TIMBER = (.36, .22, .13)
AWNING, STRIPE = (.46, .17, .14), (.86, .80, .66)
NAVY = (.42, .52, .62)  # A dark pane.
# The modern bays' panes, on paint (the glass material stays near black off the sun), and the stone-grey band at each floor.
ORIEL, SPANDREL = (.44, .54, .60), (.60, .58, .54)
ROOM = (.20, .17, .15)  # A pane that shows its room by day: dark, not the boarded brown a warm tone makes on pale stone.
LAMP = (.82, .72, .54)
PALE_LOUVRE = (.80, .81, .80)
SOFFIT = (.38, .37, .35)
COURSE = 16.4  # Where a storey's string course starts.
PLINTH = 1.6
PILASTER, PILASTER_OUT = 1.3, 1.0  # Half the pilaster between two bays, and how far it stands out of the wall.
ARC = 6  # An arch's segments, side to side.
LIT = .35  # The share of windows lit at night.
CORNER, TURRET_CORNER = 6.0, 15.0  # The facet that cuts a convex corner (the kit's cornerRadius): for quoins, for a turret.
REACH = 10.0  # How far the kit carries a facet's piece on past both its ends (KitOutline.EXTEND).
# The mansard's section (out of the wall negative, up from the roof's line): its two slate slopes, then the copper curb.
SKIRT, DECK = 7.2, 9.0  # How far in the curb ends, and the deck inside it (half a level up: a unit stands on it).
SLOPE = [(-.6, 1.2), (4.4, 9.6), (6.0, 10.4)]
CORNICE_OUT, CORNICE = 2.6, 1.2
PARAPET, PARAPET_DEEP, MERLON = 3.6, 1.5, 3.0  # The parapet's height and thickness, a battlement's merlons over it.
# A turret's radius, how far out of the facet its middle stands, its sides. Its eave (EAVE wider) must stay inside the
# wedge the kit trims a facet's piece to: the facet's width, widening a quarter of the way out.
TURRET, TURRET_OUT, SIDES, EAVE = 6.4, 2.2, 16, 1.5
TURRET_SPAN = 18.1+2*REACH  # The stretch a turret's piece is drawn for: a facet between a hex's (15) and a square's (21.2).
DRUM, CONE = 12.0, 20.0  # A turret over the roof: its drum to the cone's eave, and the cone.


def pane(name, x0, x1, z0, z1, y, lit, shop=False):
    ik.pane(name, x0, x1, z0, z1, y, lit, shop, dark=NAVY, room=ROOM)


def window(name, x0, x1, z0, z1, rng, lights=2, depth=.8, transom=2.6):
    ik.window(name, x0, x1, z0, z1, rng, lights, LIT, depth, transom, dark=NAVY, room=ROOM)


# -- Walls ------------------------------------------------------------------------------------------

def pilasters(length, base, top=COURSE):
    """A bay's ends: half the pilaster it shares with the next bay."""
    colour = RUSTIC if base else DRESSING
    for x0, x1, inner in ((0, PILASTER, 'l'), (length-PILASTER, length, 'r')):
        cuboid('pilaster', x0, x1, -PILASTER_OUT, 0, PLINTH if base else 0.0, top, STONE, colour, omit='bkt'+inner)


def course(length):
    """The string course that ends a storey: a band standing out of the wall, a shadow line under it."""
    cuboid('course', 0, length, -PILASTER_OUT-.4, 0, COURSE, LEVEL, STONE, DRESSING, omit='klr')
    add('course shadow', PAINT, JOINT, [(0, -.02, COURSE-.35), (length, -.02, COURSE-.35), (length, -.02, COURSE), (0, -.02, COURSE)], [(0, 1, 2, 3)],
        detail=True)


def plinth(length, gaps=()):
    """The ground storey's foot, open at gaps (x0, x1)."""
    edges = sorted({0.0, length, *[min(max(v, 0.0), length) for gap in gaps for v in gap]})
    for x0, x1 in zip(edges, edges[1:]):
        if not any(gap[0] <= x0+1e-6 and gap[1] >= x1-1e-6 for gap in gaps):
            c.extrude('plinth', [(0, 0), (PILASTER_OUT+.3, 0), (PILASTER_OUT+.3, PLINTH-.3), (0, PLINTH)], front, x0, x1, STONE, RUSTIC)


def frame(length, holes, base, brick=False, back=3.0):
    """A bay's wall less holes (x0, x1, z0, z1) between its half pilasters: ashlar (the ground storey's with
    channelled joints) or brick, the storey's string course, on the ground the plinth."""
    key, colour = (BRICK, BRICK_TONE) if brick else (STONE, RUSTIC if base else WALL)
    facade('wall', holes, 0.0, COURSE, length, colour, du=12, dv=9, key=key)
    if base and not brick:
        for z in (4.6, 7.6, 10.6, 13.6):  # Channelled joints: the rustication's lines, broken by the openings.
            xs = sorted({PILASTER, length-PILASTER, *[v for hole in holes if hole[2] < z < hole[3] for v in hole[:2]]})
            for x0, x1 in zip(xs[::2], xs[1::2]):
                add('channel', PAINT, JOINT, [(x0, -.03, z-.12), (x1, -.03, z-.12), (x1, -.03, z+.12), (x0, -.03, z+.12)], [(0, 1, 2, 3)], detail=True)
    pilasters(length, base)
    course(length)
    if base:
        plinth(length, [hole[:2] for hole in holes if hole[2] < PLINTH])
    back_wall(length, 0, LEVEL, back)


def arc(cx, z, radius, a0, a1, steps):
    """Points (x, z) round (cx, z) from angle a0 to a1, in degrees."""
    return [(cx+radius*math.cos(math.radians(a0+(a1-a0)*i/steps)), z+radius*math.sin(math.radians(a0+(a1-a0)*i/steps))) for i in range(steps+1)]


def arch_curve(cx, half, spring, pointed=False, grow=0.0):
    """An arch's curve (x, z) from its left springing over its crown to its right, `grow` outside it: round, or pointed
    (two arcs struck from the springings)."""
    if not pointed:
        return arc(cx, spring, half+grow, 180, 0, ARC)
    return arc(cx+half, spring, 2*half+grow, 180, 120, ARC//2)+arc(cx-half, spring, 2*half+grow, 60, 0, ARC//2)[1:]


def rise(half, pointed=False):
    """How far an arch's crown stands over its springing."""
    return half*(math.sqrt(3) if pointed else 1)


def arch_hole(cx, half, sill, spring, pointed=False):
    """What frame() leaves open for arch(): the box round it."""
    return cx-half, cx+half, sill, spring+rise(half, pointed)


def arch(name, cx, half, sill, spring, key, colour, depth=.8, ring=.9, pointed=False, shade=REVEAL):
    """An arch's stonework in a wall of key and colour, about cx: the spandrels that close the box frame() left open,
    an archivolt and keystone standing out of the wall, the reveal and intrados (in `shade`). Gives its head's outline
    at the glass, for arch_glass()."""
    x0, x1, top = cx-half, cx+half, spring+rise(half, pointed)
    curve = arch_curve(cx, half, spring, pointed)
    for corner, points in (((x0, top), curve[:ARC//2+1]), ((x1, top), curve[ARC//2:])):
        for (ax, az), (bx, bz) in zip(points, points[1:]):
            verts = [(corner[0], 0, corner[1]), (ax, 0, az), (bx, 0, bz)]
            add(name+' spandrel', key, colour, verts, [k.facing(verts, (0, -1, 0))])
    outer = arch_curve(cx, half, spring, pointed, ring)
    for (a, b), (p, q) in zip(zip(curve, curve[1:]), zip(outer, outer[1:])):
        verts = [(a[0], -.3, a[1]), (b[0], -.3, b[1]), (q[0], -.3, q[1]), (p[0], -.3, p[1])]
        add(name+' archivolt', STONE, DRESSING, verts, [k.facing(verts, (0, -1, 0))])
        verts = [(a[0], 0, a[1]), (b[0], 0, b[1]), (b[0], depth, b[1]), (a[0], depth, a[1])]
        add(name+' intrados', STONE, shade, verts, [k.facing(verts, (cx-(a[0]+b[0])/2, 0, spring-(a[1]+b[1])/2))], detail=depth < 2)
    cuboid(name+' keystone', cx-.7, cx+.7, -.6, 0, top-.3, top+ring+.5, STONE, DRESSING, omit='k', detail=True)
    for x, inner in ((x0, 1), (x1, -1)):
        verts = [(x, 0, sill), (x, depth, sill), (x, depth, spring), (x, 0, spring)]
        add(name+' reveal', STONE, shade, verts, [k.facing(verts, (inner, 0, 0))], detail=depth < 2)
    if sill > 0:
        cuboid(name+' sill', x0-.5, x1+.5, -.5, depth, sill-.5, sill, STONE, DRESSING, omit='k', detail=True)
    return [(x, depth-.06, z) for x, z in arch_curve(cx, half, spring, pointed, -.1)[::-1]]


def arch_glass(name, cx, half, sill, spring, head, rng, lights=2, lit=LIT, depth=.8):
    """An arched window's glass and bars: lights under a transom at the springing, the head (arch()'s outline) one
    dark pane."""
    x0, x1, top = cx-half, cx+half, max(z for _, _, z in head)
    add(name+' back', PAINT, k.DARK_BACK, [(x0, depth, sill), (x1, depth, sill), (x1, depth, top), (x0, depth, top)], [(0, 1, 2, 3)])
    for i in range(lights):
        pane(name+' glass', x0+(x1-x0)*i/lights+.1, x0+(x1-x0)*(i+1)/lights-.1, sill+.1, spring-.15, depth-.06, rng.random() < lit)
    add(name+' glass', PALE_GLASS, NAVY, head, [tuple(range(len(head)))], light='night' if rng.random() < lit else 'off')
    mullions(name, x0, x1, sill, top-.2 if lights % 2 == 0 else spring, depth-.1, lights, IRON, PAINT)
    cuboid(name+' transom', x0, x1, depth-.25, depth-.05, spring-.15, spring+.15, PAINT, IRON, omit='bk', detail=True)


def lamp(x, z, y=0.0):
    """A wall lamp on an iron bracket, always lit."""
    cuboid('lamp', x-.35, x+.35, y-1.1, y-.4, z, z+1.8, PAINT, LAMP, omit='', light=c.AMBER_LIGHT)
    cuboid('lamp cap', x-.5, x+.5, y-1.25, y, z+1.8, z+2.2, PAINT, IRON, omit='k', detail=True)


def arches(rng, base=False, length=W, brick=False, pointed=False):
    """Two arched windows under keystones: round, or pointed (the landmarks')."""
    half, sill, spring = 3.2, (4.2 if base else 3.4), (8.6 if pointed else 10.2)
    centres = (PILASTER+(length-2*PILASTER)*.27, PILASTER+(length-2*PILASTER)*.73)
    frame(length, [arch_hole(cx, half, sill, spring, pointed) for cx in centres], base, brick)
    wall = (BRICK, BRICK_TONE) if brick else (STONE, RUSTIC if base else WALL)
    for cx in centres:
        arch_glass('window', cx, half, sill, spring, arch('window', cx, half, sill, spring, *wall, pointed=pointed), rng)


def sashes(rng, base=False, length=W, brick=False):
    """Two tall sash windows under stone lintels, on stone sills."""
    half, sill, top = 2.6, (4.2 if base else 3.4), 13.4
    centres = (PILASTER+(length-2*PILASTER)*.27, PILASTER+(length-2*PILASTER)*.73)
    frame(length, [(cx-half, cx+half, sill, top) for cx in centres], base, brick)
    for cx in centres:
        window('window', cx-half, cx+half, sill, top, rng, 2, transom=(top-sill)/2)
        cuboid('lintel', cx-half-.7, cx+half+.7, -.5, 0, top, top+1.5, STONE, DRESSING, omit='k')
        cuboid('sill', cx-half-.5, cx+half+.5, -.6, 0, sill-.5, sill, STONE, DRESSING, omit='k')


def balcony(rng, length=W):
    """Two glazed doors onto a stone balcony with an iron rail."""
    half, sill, top, out = 2.6, .7, 13.4, 3.0
    centres = (PILASTER+(length-2*PILASTER)*.27, PILASTER+(length-2*PILASTER)*.73)
    frame(length, [(cx-half, cx+half, sill, top) for cx in centres], False)
    for cx in centres:
        window('window', cx-half, cx+half, sill, top, rng, 2, transom=3.0)
        cuboid('lintel', cx-half-.7, cx+half+.7, -.5, 0, top, top+1.5, STONE, DRESSING, omit='k')
    x0, x1 = PILASTER+.6, length-PILASTER-.6
    cuboid('balcony', x0, x1, -out, 0, 0, sill, STONE, DRESSING, omit='k')
    cuboid('balcony rail', x0, x1, -out, -out+.2, sill+2.9, sill+3.2, PAINT, IRON, omit='')
    for a0, a1, b0, b1 in ((x0, x0+.2, -out, 0), (x1-.2, x1, -out, 0)):
        cuboid('balcony rail', a0, a1, b0, b1, sill+2.9, sill+3.2, PAINT, IRON, omit='')
    count = max(2, round((x1-x0)/1.6))
    for i in range(count+1):
        x = x0+(x1-x0)*i/count
        cuboid('balcony baluster', x-.09, x+.09, -out+.02, -out+.18, sill, sill+2.9, PAINT, IRON, omit='bt', detail=True)


def arcade(rng, kind='plain', length=W):
    """The ground storey's arcade: one broad arch from pilaster to pilaster on stone imposts, open and deep in shadow,
    a glazed front set back at its end; shop, under an awning with a striped valance."""
    half, spring, depth = min(8.2, length/2-PILASTER-1.4), 5.6, 5.0
    cx = length/2
    frame(length, [arch_hole(cx, half, 0, spring)], True, back=depth+.1)
    head = arch('arcade', cx, half, 0, spring, STONE, RUSTIC, depth, shade=SHADE)
    for x in (cx-half, cx+half):
        cuboid('impost', x-.7, x+.7, -PILASTER_OUT-.2, 0, spring-.7, spring+.5, STONE, DRESSING, omit='k')
    # Its own paving: the kit's floor starts behind the glazed front.
    add('arcade floor', ROOF_DECK, (1, 1, 1), [(cx-half, 0, .42), (cx+half, 0, .42), (cx+half, depth, .42), (cx-half, depth, .42)], [(0, 1, 2, 3)])
    arch_glass('arcade', cx, half, .42, spring, head, rng, max(2, round(half/1.6)), .8, depth)
    if kind == 'shop':
        # A lit band over the shopfront: the glow kept to it, the glass dark.
        cuboid('shop band', cx-half+.2, cx+half-.2, depth-.35, depth-.1, spring-1.3, spring-.2, PAINT, ik.WARM_ROOM, omit='bk', light=ik.SHOP_GLOW)
        a, b, top, edge = cx-half-.4, cx+half+.4, spring+1.4, spring-.8
        verts = [(a, -.3, top), (b, -.3, top), (b, -3.8, edge), (a, -3.8, edge)]
        add('awning', PAINT, AWNING, verts, [k.facing(verts, (0, -.3, 1))])
        for z0, z1, colour in ((edge-1.2, edge, AWNING), (edge-1.5, edge-1.2, STRIPE)):
            add('awning valance', PAINT, colour, [(a, -3.8, z0), (b, -3.8, z0), (b, -3.8, z1), (a, -3.8, z1)], [(0, 1, 2, 3)])
    else:
        lamp(PILASTER+.6, 8.6, -PILASTER_OUT)


def glazed(rng, base=False, length=W):
    """The modern hand: a glass oriel in a steel frame, standing out of the wall between the pilasters; three rows of
    panes of one glass, a shade darker row by row."""
    x0, x1, out = PILASTER+1.4, length-PILASTER-1.4, 1.7
    low, top = (PLINTH+1.0 if base else .9), COURSE-1.0
    frame(length, [(x0, x1, low, top)], base)
    add('oriel back', PAINT, k.DARK_BACK, [(x0, 0, low), (x1, 0, low), (x1, 0, top), (x0, 0, top)], [(0, 1, 2, 3)])
    for z0, z1 in ((low-.5, low), (top, top+.6)):
        cuboid('oriel frame', x0-.3, x1+.3, -out-.25, 0, z0, z1, PAINT, IRON, omit='k')
    count, rows = max(2, round((x1-x0)/4.4)), 3
    add('oriel spandrel', PAINT, SPANDREL, [(x0, -out-.02, low), (x1, -out-.02, low), (x1, -out-.02, low+1.6), (x0, -out-.02, low+1.6)], [(0, 1, 2, 3)])
    for row in range(rows):
        z0, z1 = low+(top-low)*row/rows+.1, low+(top-low)*(row+1)/rows-.1
        z0 = max(z0, low+1.7)
        tint = tuple(v*(1-.08*(rows-1-row)) for v in ORIEL)
        for i in range(count):
            a, b = x0+(x1-x0)*i/count+.1, x0+(x1-x0)*(i+1)/count-.1
            sky = rng.random() < .25
            add('oriel glass', PALE_GLASS if sky else PAINT, ik.SKY_PANE if sky else tint, [(a, -out, z0), (b, -out, z0), (b, -out, z1), (a, -out, z1)],
                [(0, 1, 2, 3)], light='night' if rng.random() < LIT else 'off')
        for x, way in ((x0, -1), (x1, 1)):
            verts = [(x, -out, z0), (x, 0, z0), (x, 0, z1), (x, -out, z1)]
            add('oriel glass', PAINT, tint, verts, [k.facing(verts, (way, 0, 0))], light='off')
        if row:
            cuboid('oriel rail', x0-.1, x1+.1, -out-.12, 0, z0-.3, z0-.1, PAINT, IRON, omit='k')
    for i in range(count+1):
        x = x0+(x1-x0)*i/count
        cuboid('oriel post', x-.16, x+.16, -out-.12, -out+.1, low, top, PAINT, IRON, omit='bkt', detail=0 < i < count)


def panel(rng, base=False, length=W, brick=False, kind='plain'):
    """A plain stretch of wall with a blind arch sunk in it; louvre, a louvred opening under a stone lintel in its
    place; service, on the ground, a steel door under a lamp and a meter cabinet."""
    cx = length/2
    if kind == 'service':
        frame(length, [(4.6, 9.0, 0, 9.2)], True, brick)
        recess('service', 4.6, 9.0, 0, 9.2, .5, IRON, PAINT)
        add('service door', PAINT, (.30, .33, .32), [(4.8, .44, .2), (8.8, .44, .2), (8.8, .44, 9.0), (4.8, .44, 9.0)], [(0, 1, 2, 3)])
        cuboid('lintel', 3.9, 9.7, -.5, 0, 9.2, 10.6, STONE, DRESSING, omit='k')
        lamp(6.8, 11.2)
        c.louvre('service louvre', front, 13.2, 19.6, 6.4, 12.0)
        cuboid('service cabinet', 14.4, 17.6, -1.7, -.5, 0, 4.6, PAINT, (.38, .42, .40), omit='bk')
        return
    if kind == 'louvre':
        frame(length, [], base, brick)
        half = min(4.6, length/2-PILASTER-1)
        c.louvre('louvre', front, cx-half, cx+half, 5.0, 12.4)
        cuboid('lintel', cx-half-.8, cx+half+.8, -.5, 0, 12.6, 14.0, STONE, DRESSING, omit='k')
        cuboid('sill', cx-half-.6, cx+half+.6, -.6, 0, 4.0, 4.5, STONE, DRESSING, omit='k')
        return
    half, sill, spring, depth = min(5.0, length/2-PILASTER-1.4), (PLINTH+1.8 if base else 2.6), 8.6, 1.3
    key, colour = (BRICK, BRICK_TONE) if brick else (STONE, RUSTIC if base else WALL)
    frame(length, [arch_hole(cx, half, sill, spring)], base, brick)
    outline = arch('blind arch', cx, half, sill, spring, key, colour, depth, ring=.8)
    dark = tuple(v*.62 for v in colour)
    for x in (cx-half-.7, cx+half):
        cuboid('blind arch jamb', x, x+.7, -.3, 0, sill, spring, STONE, DRESSING, omit='bk')
    add('blind arch back', key, dark, [(cx-half, depth-.06, sill), (cx+half, depth-.06, sill), (cx+half, depth-.06, spring), (cx-half, depth-.06, spring)],
        [(0, 1, 2, 3)])
    add('blind arch back', key, dark, outline, [tuple(range(len(outline)))])


HALL_PLINTH, BUTTRESS, BUTTRESS_OUT = 5.2, 1.5, 1.4  # A hall's stone foot; half its buttress, and how far that stands out.
HALL_ROOM = (.16, .20, .25)  # A hall's pane that shows no sky: dark blue, never the black of a broken one.


def hall(rng, kind, base=False, length=W, top=False):
    """A hall's bay: brick over a stone foot between stone buttresses, storey on storey without a course, so buttresses
    and strips run the hall's whole height. Up its middle one strip: a window of small panes in an iron frame between
    stone jambs, louvres between stone jambs, or a sunk brick panel; door, on the ground, a steel door under a lamp.
    The top storey ends its strip under the eave: the window in a round arch under a keystone, the louvres under a
    stone lintel, the panel in the wall."""
    low, mid = (HALL_PLINTH if base else 0.0), length/2
    half = {'window': 4.2, 'louvre': 2.4, 'panel': length/2-BUTTRESS-2.4, 'door': 0}[kind]
    x0, x1 = mid-half, mid+half
    arched = top and kind in ('window', 'panel')
    spring = LEVEL-half-2.4  # An arched head's springing: its crown 2.4 under the eave.
    head = LEVEL-2.4 if top else LEVEL  # Where a top storey's other strips end.
    holes = ([arch_hole(mid, half, 0, spring)] if arched else [(x0, x1, low, head)] if kind in ('window', 'panel')
             else [(4.6, 9.0, 0, 9.2)] if kind == 'door' else [])
    facade('wall', holes, low, LEVEL, length, BRICK_TONE, du=12, dv=9, key=BRICK)
    if base:
        facade('foot', [hole for hole in holes if hole[2] < low], 0, low, length, RUSTIC, du=12, dv=9, key=STONE)
        cuboid('foot course', 0, length, -.5, 0, low-.7, low, STONE, DRESSING, omit='klr')
    shoulder = LEVEL-3.4 if top else LEVEL  # Under the eave a buttress weathers back into the wall.
    for a, b in ((0, BUTTRESS), (length-BUTTRESS, length)):
        cuboid('buttress', a, b, -BUTTRESS_OUT, 0, 0, shoulder, STONE, DRESSING, omit='bkt')
        if top:
            verts = [(a, -BUTTRESS_OUT, shoulder), (b, -BUTTRESS_OUT, shoulder), (b, 0, shoulder+2.2), (a, 0, shoulder+2.2)]
            add('buttress', STONE, DRESSING, verts, [k.facing(verts, (0, -1, 1))])
        if base:
            cuboid('buttress foot', a, b, -BUTTRESS_OUT-.5, 0, 0, low, STONE, RUSTIC, omit='bk')
    if kind in ('window', 'louvre'):
        for a in (x0-.8, x1):  # Stone jambs up the strip.
            cuboid('hall jamb', a, a+.8, -.4, 0, low, spring if arched else head, STONE, DRESSING, omit='bk' if top else 'bkt')
    depth = .8 if kind == 'window' else .5
    if kind in ('window', 'panel') and not arched:
        tone, key = (REVEAL, STONE) if kind == 'window' else (tuple(v*.8 for v in BRICK_TONE), BRICK)
        add('hall reveal', key, tone, [(x0, 0, low), (x0, depth, low), (x0, depth, head), (x0, 0, head)], [(0, 1, 2, 3)])
        add('hall reveal', key, tone, [(x1, depth, low), (x1, 0, low), (x1, 0, head), (x1, depth, head)], [(0, 1, 2, 3)])
        if base:
            add('hall sill', STONE, DRESSING, [(x0, 0, low), (x1, 0, low), (x1, depth, low), (x0, depth, low)], [(0, 1, 2, 3)])
        if top:
            add('hall soffit', key, tone, [(x0, 0, head), (x1, 0, head), (x1, depth, head), (x0, depth, head)], [(3, 2, 1, 0)])
    outline = arch('hall arch', mid, half, 0, spring, BRICK, BRICK_TONE, depth) if arched else None
    if kind == 'panel':
        dark = tuple(v*.66 for v in BRICK_TONE)
        top_z = spring if arched else head
        add('hall panel', BRICK, dark, [(x0, depth, low), (x1, depth, low), (x1, depth, top_z), (x0, depth, top_z)], [(0, 1, 2, 3)])
        if arched:
            add('hall panel', BRICK, dark, outline, [tuple(range(len(outline)))])
    elif kind == 'window':
        crown = spring+half if arched else LEVEL
        add('hall back', PAINT, k.DARK_BACK, [(x0, depth, low), (x1, depth, low), (x1, depth, crown), (x0, depth, crown)], [(0, 1, 2, 3)])
        rows = [(low+.25, 12.0), (12.25, LEVEL)] if base else [(.25, 6.0), (6.25, spring)] if arched else [(.25, 6.0), (6.25, 12.0), (12.25, LEVEL)]
        for z0, z1 in rows:
            for i in range(3):
                ik.pane('hall glass', x0+2*half*i/3+.1, x0+2*half*(i+1)/3-.1, z0, z1, depth-.06, rng.random() < .3, dark=NAVY, room=HALL_ROOM)
            cuboid('hall bar', x0, x1, depth-.3, depth-.05, z0-.25, z0, PAINT, IRON, omit='bk')
        for i in (1, 2):
            x = x0+2*half*i/3
            cuboid('hall post', x-.12, x+.12, depth-.3, depth-.05, low, spring if arched else LEVEL, PAINT, IRON, omit='bkt')
        if arched:
            add('hall glass', PALE_GLASS, NAVY, outline, [tuple(range(len(outline)))], light='night' if rng.random() < .5 else 'off')
            cuboid('hall bar', x0, x1, depth-.3, depth-.05, spring-.12, spring+.13, PAINT, IRON, omit='bk')
            for turn in (60, 120):  # The head's bars, from the springing's middle.
                px, pz = mid+(half-.15)*math.cos(math.radians(turn)), spring+(half-.15)*math.sin(math.radians(turn))
                verts = [(mid-.12, depth-.1, spring), (mid+.12, depth-.1, spring), (px+.12, depth-.1, pz), (px-.12, depth-.1, pz)]
                add('hall post', PAINT, IRON, verts, [k.facing(verts, (0, -1, 0))])
    elif kind == 'louvre':
        c.louvre('louvre', front, x0, x1, low+.5, head-.5)
        if top:
            cuboid('lintel', x0-1.0, x1+1.0, -.5, 0, head, head+1.3, STONE, DRESSING, omit='k')
    else:
        recess('service', 4.6, 9.0, 0, 9.2, .5, IRON, PAINT)
        add('service door', PAINT, (.30, .33, .32), [(4.8, .44, .2), (8.8, .44, .2), (8.8, .44, 9.0), (4.8, .44, 9.0)], [(0, 1, 2, 3)])
        cuboid('lintel', 3.9, 9.7, -.5, 0, 9.2, 10.6, STONE, DRESSING, omit='k')
        lamp(6.8, 11.4)
        cuboid('service cabinet', 14.4, 17.6, -1.7, -.5, 0, 4.6, PAINT, (.38, .42, .40), omit='bk')
    back_wall(length, 0, LEVEL)


def works(rng, base=False, length=W):
    """A works' bay of brick: one tall arched window of small panes in an iron frame, stone at its sill, springing and
    key."""
    half, sill, spring = min(6.4, length/2-PILASTER-1.6), (PLINTH+3.2 if base else 2.4), 8.4
    cx = length/2
    frame(length, [arch_hole(cx, half, sill, spring)], base, True)
    head = arch('works window', cx, half, sill, spring, BRICK, BRICK_TONE, depth=.7)
    arch_glass('works window', cx, half, sill, spring, head, rng, 4, .3, .7)
    for z in (sill+(spring-sill)/2, spring+half*.55):
        wide = half if z < spring else math.sqrt(max(0.0, half**2-(z-spring)**2))-.1
        cuboid('works bar', cx-wide, cx+wide, .45, .65, z-.1, z+.1, PAINT, IRON, omit='bk', detail=True)
    for x in (cx-half-.5, cx+half+.5):
        cuboid('impost', x-.7, x+.7, -.4, 0, spring-.6, spring+.6, STONE, DRESSING, omit='k', detail=True)


def entrance(rng, kind='plain'):
    """The entrance: timber doors and a lit fanlight deep in a stone portal, under a porch of two stone columns and a
    balustraded hood, up two broad steps, a lamp either side; med, a lit cross in a lamp's place."""
    half, spring, depth, cx = 4.6, 7.2, 2.4, W/2
    frame(W, [arch_hole(cx, half, 0, spring)], True, back=depth+.1)
    arch('portal', cx, half, 0, spring, STONE, RUSTIC, depth, ring=1.2, shade=SHADE)
    add('portal floor', ROOF_DECK, (1, 1, 1), [(cx-half, 0, .62), (cx+half, 0, .62), (cx+half, depth, .62), (cx-half, depth, .62)], [(0, 1, 2, 3)])
    wide, out, hood = half+2.6, 4.2, spring+half+1.5
    for i, (a, b) in enumerate(((wide+1.6, out+1.2), (wide+.6, out))):
        cuboid('portal step', cx-a, cx+a, -b, 0, .3*i, .3*(i+1), STONE, DRESSING, omit='bk')
    for x in (cx-wide+.4, cx+wide-.4):
        round_prism('porch column', x, -out+1.2, .6, hood, .95, STONE, DRESSING, 8)
        cuboid('porch column foot', x-1.3, x+1.3, -out-.1, -out+2.5, .6, 1.6, STONE, DRESSING, omit='b')
    cuboid('porch hood', cx-wide-.6, cx+wide+.6, -out-.3, 0, hood, hood+1.3, STONE, DRESSING, omit='k')
    cuboid('porch rail', cx-wide-.3, cx+wide+.3, -out, -out+.5, hood+1.3, hood+2.5, STONE, DRESSING, omit='b')
    back = depth-.06
    add('portal back', PAINT, k.DARK_BACK, [(cx-half, depth, 0), (cx+half, depth, 0), (cx+half, depth, spring+half), (cx-half, depth, spring+half)],
        [(0, 1, 2, 3)])
    for a, b in ((cx-half+.3, cx-.08), (cx+.08, cx+half-.3)):
        add('door leaf', PAINT, TIMBER, [(a, back, .6), (b, back, .6), (b, back, spring-.2), (a, back, spring-.2)], [(0, 1, 2, 3)])
        pane('door glass', a+1.0, b-1.0, 3.6, spring-1.0, back-.05, True, shop=True)
    fan = [(x, back, z) for x, z in arc(cx, spring+.2, half-.3, 0, 180, ARC)]
    add('fanlight', PAINT, ik.WARM_ROOM, fan, [tuple(range(len(fan)))], light=ik.SHOP_GLOW)
    for i in range(1, 4):
        x, z = arc(cx, spring+.2, half-.3, 0, 180, 4)[i]
        verts = [(cx-.1, back-.06, spring+.2), (cx+.1, back-.06, spring+.2), (x+.1, back-.06, z), (x-.1, back-.06, z)]
        add('fanlight bar', PAINT, IRON, verts, [k.facing(verts, (0, -1, 0))], detail=True)
    lamp(cx-wide-1.6, 7.4, -PILASTER_OUT)
    if kind == 'med':
        x = cx+wide+1.8
        cuboid('med sign', x-1.2, x+1.2, -PILASTER_OUT-.3, -PILASTER_OUT, 7.4, 9.8, PAINT, ik.TEAL, omit='bk', light=(.10, .55, .50))
        for a0, a1, b0, b1 in ((x-.75, x+.75, 8.35, 8.85), (x-.25, x+.25, 7.85, 9.35)):
            y = -PILASTER_OUT-.34
            add('med cross', PAINT, (.92, .92, .88), [(a0, y, b0), (a1, y, b0), (a1, y, b1), (a0, y, b1)], [(0, 1, 2, 3)], light=(.80, .80, .74))
    else:
        lamp(cx+wide+1.6, 7.4, -PILASTER_OUT)


# -- Corners ----------------------------------------------------------------------------------------

def quoins(rng, base=False, length=k.ROUND, banded=True):
    """A wall's corner facet: a pier of quoins, long and short by turns, a shadow in each joint, with the storey's
    course; a hall's, without the course: quoins up the hall's whole height."""
    low, top = (PLINTH if base else 0.0), (COURSE if banded else LEVEL)
    cuboid('pier', 0, length, -PILASTER_OUT, 0, low, top, STONE, tuple(v*.9 for v in (RUSTIC if base else WALL)), omit='bktlr')
    if base:
        cuboid('pier foot', 0, length, -PILASTER_OUT-.3, 0, 0, low, STONE, RUSTIC, omit='bklr')
    mid, tall = length/2, 2.4
    for i in range(int((top-low-.2)//tall)):
        half = length*(.34 if i % 2 else .2)
        cuboid('quoin', mid-half, mid+half, -PILASTER_OUT-.45, -PILASTER_OUT, low+.3+i*tall, low+tall+i*tall, STONE, DRESSING, omit='k')
        add('quoin joint', PAINT, QUOIN_JOINT, [(mid-half, -PILASTER_OUT-.46, low+.1+i*tall), (mid+half, -PILASTER_OUT-.46, low+.1+i*tall),
                                         (mid+half, -PILASTER_OUT-.46, low+.3+i*tall), (mid-half, -PILASTER_OUT-.46, low+.3+i*tall)], [(0, 1, 2, 3)],
            detail=True)
    if banded:
        course(length)
    back_wall(length, 0, LEVEL)


def ring(radius):
    """A turret's outline at radius, as (x, y) in the piece's frame: a circle about its middle, where the kit's stretch
    along the facet makes it round; from its back round its front (-y) to its back again."""
    scale = k.ROUND/TURRET_SPAN
    return [(k.ROUND/2+radius*math.sin(math.radians(180+360*i/SIDES))*scale, -TURRET_OUT+radius*math.cos(math.radians(180+360*i/SIDES)))
            for i in range(SIDES+1)]


def drum(name, radius, z0, z1, colour, key=STONE, behind=.6):
    """A turret's wall from z0 to z1: its sides but those behind the facet's line."""
    points = ring(radius)
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        if min(ay, by) > behind:
            continue
        verts = [(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)]
        add(name, key, colour, verts, [k.facing(verts, ((ax+bx)/2-k.ROUND/2, ((ay+by)/2+TURRET_OUT)*.2, 0))])


def ledge(name, inner, outer, z, colour, up=True, key=STONE):
    """A flat ring between two of a turret's radii at z (a disc from inner 0), facing up or down."""
    for (a, b), (p, q) in zip(zip(ring(inner), ring(inner)[1:]), zip(ring(outer), ring(outer)[1:])):
        verts = [(*a, z), (*b, z), (*q, z), (*p, z)] if inner else [(*a, z), (*q, z), (*p, z)]
        add(name, key, colour, verts, [k.facing(verts, (0, 0, 1 if up else -1))])


def slits(name, radius, z0, z1, rng, turns=(-52, 0, 52), lit=.5):
    """Narrow windows round a turret's front (turn 0, by degrees either way): a dark frame and its glass, flat on the
    drum."""
    scale = k.ROUND/TURRET_SPAN
    for turn in turns:
        angle = math.radians(180+turn)
        cx, cy = radius*math.sin(angle), radius*math.cos(angle)
        tx, ty = math.cos(angle), -math.sin(angle)
        for half, out, a, b, key, colour, light in ((.8, .06, z0, z1, PAINT, IRON, None),
                                                    (.55, .12, z0+.3, z1-.3, PALE_GLASS, NAVY, 'night' if rng.random() < lit else 'off')):
            px, py = cx*(1+out/radius), cy*(1+out/radius)
            verts = [(k.ROUND/2+(px-tx*half)*scale, -TURRET_OUT+py-ty*half, a), (k.ROUND/2+(px+tx*half)*scale, -TURRET_OUT+py+ty*half, a),
                     (k.ROUND/2+(px+tx*half)*scale, -TURRET_OUT+py+ty*half, b), (k.ROUND/2+(px-tx*half)*scale, -TURRET_OUT+py-ty*half, b)]
            add(name, key, colour, verts, [k.facing(verts, (cx, cy, 0))], **({'light': light} if light else {}))


def turret(rng, base=False, length=k.ROUND):
    """A round turret's storey on a corner's facet: its drum standing out of both walls, slit windows, the storey's
    course as a band round it, closed underneath; on the ground its foot."""
    colour = RUSTIC if base else WALL
    add('pier', STONE, colour, [(0, 0, 0), (length, 0, 0), (length, 0, LEVEL), (0, 0, LEVEL)], [(0, 1, 2, 3)])  # The facet behind it.
    drum('turret', TURRET, PLINTH if base else 0.0, COURSE, colour)
    drum('turret course', TURRET+.5, COURSE, LEVEL, DRESSING)
    ledge('turret course', TURRET, TURRET+.5, LEVEL, DRESSING)
    ledge('turret course', TURRET, TURRET+.5, COURSE, REVEAL, up=False)
    if base:
        drum('turret foot', TURRET+.5, 0, PLINTH, RUSTIC)
        ledge('turret foot', TURRET, TURRET+.5, PLINTH, RUSTIC)
        slits('turret slit', TURRET, 6.0, 11.6, rng, turns=(-52, 52), lit=LIT)
    else:
        ledge('turret underside', 0, TURRET, .02, REVEAL, up=False)
        slits('turret slit', TURRET, 4.4, 12.4, rng, lit=LIT)
    back_wall(length, 0, LEVEL)


def turret_top(rng, roof, length=k.ROUND):
    """A turret over the roof, on the roof's own facet piece (`roof`, which closes the roof behind it): its drum up to a
    ring of lit slits under a cornice, and a bell-cast copper cone, flared at its eave, to an iron finial on a collar;
    on a battlement, merlons in the cone's place."""
    crown = roof is battlement_corner
    roof(rng, length)
    top = 9.4 if crown else DRUM
    drum('turret', TURRET, 0, top-1.2, WALL, behind=TURRET)
    drum('turret cornice', TURRET+.6, top-1.2, top, DRESSING, behind=TURRET+1)
    ledge('turret cornice', TURRET, TURRET+.6, top-1.2, REVEAL, up=False)
    slits('turret slit', TURRET, top-6.8, top-2.4, rng, turns=(-104, -52, 0, 52, 104), lit=.7)
    mid, scale = k.ROUND/2, k.ROUND/TURRET_SPAN
    if crown:
        ledge('turret cornice', TURRET-1.2, TURRET+.6, top, DRESSING)
        ledge('turret floor', 0, TURRET-1.2, top-.9, REVEAL)
        inner = ring(TURRET-1.2)
        for (ax, ay), (bx, by) in zip(inner, inner[1:]):
            verts = [(ax, ay, top-.9), (bx, by, top-.9), (bx, by, top), (ax, ay, top)]
            add('turret wall', STONE, REVEAL, verts, [k.facing(verts, (mid-(ax+bx)/2, -TURRET_OUT-(ay+by)/2, 0))])
        outer, inner = ring(TURRET+.6), ring(TURRET-.8)
        for i in range(0, SIDES, 2):
            foot = [(*outer[i], top), (*outer[i+1], top), (*inner[i+1], top), (*inner[i], top)]
            block = foot+[(x, y, top+MERLON) for x, y, _ in foot]
            add('turret merlon', STONE, DRESSING, block, [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
        return
    # The cone, bell-cast: out over a dark eave band, in fast, then steep to its point.
    drum('turret eave', TURRET+EAVE, top-.9, top-.4, LEAD, key=PAINT, behind=TURRET+2)
    ledge('turret eave', TURRET+.6, TURRET+EAVE, top-.9, SOFFIT, up=False, key=PAINT)
    profile = [(TURRET+EAVE, top-.4), (TURRET*.74, top+4.6), (TURRET*.40, top+11.5), (0.0, top+CONE)]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        for (a, b), (p, q) in zip(zip(ring(r0), ring(r0)[1:]), zip(ring(r1), ring(r1)[1:])):
            verts = [(*a, z0), (*b, z0), (*q, z1), (*p, z1)] if r1 else [(*a, z0), (*b, z0), (mid, -TURRET_OUT, z1)]
            add('turret cone', COPPER, (1, 1, 1), verts, [k.facing(verts, (a[0]+b[0]-2*mid, a[1]+b[1]+2*TURRET_OUT, 1.0))])
    for half, z0, z1, detail in ((.75, top+CONE-2.2, top+CONE-1.2, True), (.28, top+CONE-1.4, top+CONE+3.0, False)):
        # A plain spike on its collar: a bar across it would make a cross of it.
        cuboid('turret finial', mid-half*scale, mid+half*scale, -TURRET_OUT-half, -TURRET_OUT+half, z0, z1, PAINT, IRON, omit='b', detail=detail)


# -- Roofs ------------------------------------------------------------------------------------------

def mansard_rows(x0, x1):
    """The mansard along x: its stone cornice over a shadowed soffit, the two slopes of slate, the copper curb and its
    leaded inner face down to the deck."""
    cuboid('cornice', x0, x1, -CORNICE_OUT, .2, 0, CORNICE, STONE, DRESSING, omit='klr')
    add('cornice soffit', PAINT, SOFFIT, [(x0, -CORNICE_OUT, 0), (x0, 0, 0), (x1, 0, 0), (x1, -CORNICE_OUT, 0)], [(0, 1, 2, 3)])
    for (y0, z0), (y1, z1) in zip(SLOPE, SLOPE[1:]):
        add('mansard roofing', SLATE, (1, 1, 1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z1), (x0, y1, z1)], [(0, 1, 2, 3)])
    y, z = SLOPE[-1]
    add('mansard curb', COPPER, (.9, .9, .9), [(x0, y, z), (x1, y, z), (x1, SKIRT, z), (x0, SKIRT, z)], [(0, 1, 2, 3)])
    add('mansard curb', PAINT, LEAD, [(x1, SKIRT, DECK-.2), (x1, SKIRT, z), (x0, SKIRT, z), (x0, SKIRT, DECK-.2)], [(3, 2, 1, 0)])


def slope_at(z):
    """How far in the lower slate slope stands at height z."""
    (y0, z0), (y1, z1) = SLOPE[:2]
    return y0+(y1-y0)*(z-z0)/(z1-z0)


def dormer(x, rng, half=2.1, sill=1.9, top=6.8, ridge=9.0):
    """A dormer on the slate skirt: a stone face flush with the wall round a lit window, slate cheeks back to the
    slope, a slate gable."""
    face = -.5
    for a0, a1, b0, b1 in ((x-half, x+half, CORNICE, sill), (x-half, x-half+.6, sill, top), (x+half-.6, x+half, sill, top)):
        add('dormer', STONE, DRESSING, [(a0, face, b0), (a1, face, b0), (a1, face, b1), (a0, face, b1)], [(0, 1, 2, 3)])
    add('dormer', STONE, DRESSING, [(x-half, face, top), (x+half, face, top), (x, face, ridge-.3)], [(0, 1, 2)])
    add('dormer glass', PALE_GLASS, NAVY, [(x-half+.6, face+.2, sill), (x+half-.6, face+.2, sill), (x+half-.6, face+.2, top), (x-half+.6, face+.2, top)],
        [(0, 1, 2, 3)], light='night' if rng.random() < LIT else 'off')
    cuboid('dormer bar', x-.1, x+.1, face+.05, face+.2, sill, top, PAINT, IRON, omit='bkt', detail=True)
    for side in (-1, 1):
        a = x+side*half
        verts = [(a, face, CORNICE), (a, face, top), (a, slope_at(top), top)]
        add('dormer cheek', SLATE, (.9, .9, .9), verts, [k.facing(verts, (side, 0, 0))])
        eave, crown = (a+side*.5, face-.5, top-.3), (x, face-.5, ridge)
        verts = [eave, crown, (x, slope_at(ridge), ridge), (a+side*.5, slope_at(top-.3), top-.3)]
        add('dormer roof', SLATE, (.86, .86, .86), verts, [k.facing(verts, (side, 0, 1))])


def mansard(rng, length=W, dormers=True):
    """The roof along a wall: the mansard, a dormer over each of the bay's two windows."""
    mansard_rows(0, length)
    for t in ((.27, .73) if dormers else ()):
        dormer(PILASTER+(length-2*PILASTER)*t, rng)


def mansard_corner(rng, length=k.ROUND):
    """The mansard on a corner's facet, its hip under a copper roll."""
    mansard_rows(0, length)
    mid, wide = length/2, .5*length/(CORNER+2*REACH)
    path = [(SLOPE[0][0]-.1, SLOPE[0][1]), *SLOPE[1:], (SKIRT, SLOPE[-1][1])]
    for (ya, za), (yb, zb) in zip(path, path[1:]):
        for side in (-1, 1):
            verts = [(mid+side*wide, ya, za), (mid, ya, za+.45), (mid, yb, zb+.45), (mid+side*wide, yb, zb)]
            add('mansard hip', COPPER, (.8, .8, .8), verts, [k.facing(verts, (side, 0, .2))])


def hall_eave(rng, length=W):
    """A hall's eave under the roof that spans it: a stone cornice along the wall's top, a copper gutter on it."""
    cuboid('cornice', 0, length, -2.6, .4, -1.0, .3, STONE, DRESSING, omit='lr')
    cuboid('cornice bed', 0, length, -1.4, 0, -2.0, -1.0, STONE, DRESSING, omit='klr')
    cuboid('gutter', 0, length, -2.3, -.5, .3, .7, PAINT, (.33, .42, .39), omit='blr')


def battlement(rng, length=W, merlons=True):
    """The roof along a wall: a corbelled stone parapet under a coping, round a flat roof; with merlons, a
    battlement."""
    cuboid('corbel', 0, length, -PILASTER_OUT-.5, 0, 0, .9, STONE, DRESSING, omit='klr')
    cuboid('parapet', 0, length, -PILASTER_OUT-.5, PARAPET_DEEP, .9, PARAPET, STONE, WALL, omit='blr')
    if not merlons:
        cuboid('coping', 0, length, -PILASTER_OUT-.8, PARAPET_DEEP+.3, PARAPET, PARAPET+.6, STONE, DRESSING, omit='lr')
        return
    count = max(1, round(length/8))
    for i in range(count):
        x = length*(i+.5)/count
        cuboid('merlon', x-2.1, x+2.1, -PILASTER_OUT-.5, PARAPET_DEEP, PARAPET, PARAPET+MERLON, STONE, DRESSING, omit='b')


def battlement_corner(rng, length=k.ROUND, merlons=True):
    """The parapet on a corner's facet: a block of it, taller than a battlement's merlons."""
    cuboid('corbel', 0, length, -PILASTER_OUT-.5, 0, 0, .9, STONE, DRESSING, omit='klr')
    cuboid('parapet', 0, length, -PILASTER_OUT-.5, PARAPET_DEEP, .9, PARAPET+(MERLON+.8 if merlons else 1.4), STONE, DRESSING, omit='blr')


def parapet_corner(rng, length=k.ROUND):
    battlement_corner(rng, length, merlons=False)


# Roof fittings: each stands on the deck about its origin.
def chimney(rng):
    """A stone stack under a cap, two pots on it."""
    cuboid('chimney foot', -2.6, 2.6, -1.8, 1.8, 0, 1.2, STONE, DRESSING, omit='b')
    cuboid('chimney', -2.2, 2.2, -1.4, 1.4, 1.2, 8.6, STONE, WALL, omit='bt')
    cuboid('chimney cap', -2.7, 2.7, -1.9, 1.9, 8.6, 9.4, STONE, DRESSING)
    for x in (-1.1, 1.1):
        round_prism('chimney pot', x, 0, 9.4, 11.2, .6, PAINT, (.46, .30, .24), 8)


def cupola(rng):
    """A copper-domed lantern on a stone drum, its windows lit."""
    round_prism('cupola drum', 0, 0, 0, 1.6, 3.6, STONE, DRESSING, 8)
    points = [(3.0*math.cos(i*math.tau/8), 3.0*math.sin(i*math.tau/8)) for i in range(8)]
    for (ax, ay), (bx, by) in zip(points, points[1:]+points[:1]):
        verts = [(ax, ay, 1.6), (bx, by, 1.6), (bx, by, 5.4), (ax, ay, 5.4)]
        add('cupola glass', PALE_GLASS, ik.PALE_PANE, verts, [k.facing(verts, (ax+bx, ay+by, 0))], light='dim')
    round_prism('cupola cornice', 0, 0, 5.4, 6.0, 3.5, STONE, DRESSING, 8)
    profile = [(3.3, 6.0), (2.9, 7.6), (1.9, 8.9), (.5, 9.6)]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        for i in range(8):
            a, b = i*math.tau/8, (i+1)*math.tau/8
            verts = [(r0*math.cos(a), r0*math.sin(a), z0), (r0*math.cos(b), r0*math.sin(b), z0), (r1*math.cos(b), r1*math.sin(b), z1),
                     (r1*math.cos(a), r1*math.sin(a), z1)]
            add('cupola dome', COPPER, (1, 1, 1), verts, [k.facing(verts, (math.cos((a+b)/2), math.sin((a+b)/2), .6))])
    cuboid('cupola finial', -.2, .2, -.2, .2, 9.4, 12.2, PAINT, IRON, omit='b')


def skylight(rng):
    """A roof light: a long hipped light of glass in an iron frame on a stone kerb."""
    x, y, kerb, up = 6.0, 2.8, 1.2, 2.2
    cuboid('skylight kerb', -x, x, -y, y, 0, kerb, STONE, DRESSING, omit='bt')
    e = [(-x, -y, kerb), (x, -y, kerb), (x, y, kerb), (-x, y, kerb)]
    r0, r1 = (-x+y, 0, kerb+up), (x-y, 0, kerb+up)
    for face in ((e[0], e[1], r1, r0), (e[1], e[2], r1), (e[2], e[3], r0, r1), (e[3], e[0], r0)):
        add('skylight glass', PALE_GLASS, NAVY, list(face), [tuple(range(len(face)))], light='off')
    cuboid('skylight ridge', r0[0]-.2, r1[0]+.2, -.18, .18, kerb+up-.1, kerb+up+.2, PAINT, IRON, omit='b', detail=True)


def plant(rng):
    """Roof plant: two fan units behind a pale louvred screen."""
    for x in (-3.1, 3.1):
        cuboid('plant unit', x-2.5, x+2.5, -2.8, 2.8, 0, 3.6, PAINT, (.60, .61, .61), omit='b')
        disc('plant fan', x, 0, 3.62, 1.9, 'z', h.GRILLE, (.62, .64, .66), 12)
    for x0, x1, y0, y1 in ((-6.6, 6.6, -4.4, -4.1), (-6.6, 6.6, 4.1, 4.4), (-6.6, -6.3, -4.1, 4.1), (6.3, 6.6, -4.1, 4.1)):
        cuboid('plant screen', x0, x1, y0, y1, 0, 4.6, SLATS, PALE_LOUVRE, omit='b')


def duct(rng):
    """A run of ducting on feet, an elbow down into the roof at one end, a louvred head at the other."""
    cuboid('duct', -5.4, 5.4, -1.1, 1.1, 1.2, 3.2, PAINT, (.58, .60, .60), omit='')
    for x in (-3.6, 0.0, 3.6):
        cuboid('duct foot', x-.3, x+.3, -1.3, 1.3, 0, 1.2, PAINT, IRON, omit='bt', detail=True)
    cuboid('duct elbow', -5.4, -3.4, -1.1, 1.1, 0, 1.2, PAINT, (.58, .60, .60), omit='bt')
    cuboid('duct head', 5.4, 7.4, -1.6, 1.6, .9, 3.6, SLATS, PALE_LOUVRE, omit='l')


def tank(rng):
    """A water tank: a staved drum on a steel frame under a low cone."""
    for x, y in ((-2.2, -2.2), (2.2, -2.2), (2.2, 2.2), (-2.2, 2.2)):
        cuboid('tank leg', x-.25, x+.25, y-.25, y+.25, 0, 2.2, PAINT, IRON, omit='bt', detail=True)
    round_prism('tank', 0, 0, 2.2, 7.4, 3.4, PAINT, (.44, .36, .30), 10)
    points = [(3.7*math.cos(i*math.tau/10), 3.7*math.sin(i*math.tau/10)) for i in range(10)]
    for (ax, ay), (bx, by) in zip(points, points[1:]+points[:1]):
        add('tank roof', PAINT, LEAD, [(ax, ay, 7.4), (bx, by, 7.4), (0, 0, 9.2)], [(0, 1, 2)])


def hatch(rng):
    cuboid('hatch kerb', -2.4, 2.4, -2.4, 2.4, 0, 1.2, STONE, DRESSING, omit='b')
    deck('hatch lid', -2.0, 2.0, -2.0, 2.0, 1.22, COPPER, (.8, .8, .8))


def vent(rng):
    """A ventilator: a round steel cowl on a square foot."""
    cuboid('vent foot', -1.6, 1.6, -1.6, 1.6, 0, 1.0, PAINT, (.42, .44, .44), omit='b')
    round_prism('vent', 0, 0, 1.0, 4.2, 1.1, PAINT, (.55, .57, .57), 8)
    round_prism('vent cowl', 0, 0, 4.2, 5.2, 1.8, PAINT, (.40, .42, .42), 8)


ROOFING = {SLATE: SLATE_REPEAT, COPPER: COPPER_REPEAT}
# A storey's bays: each a builder (rng, base, length) and what else it takes.
WALLS = {
    'arch': (arches, {}), 'sash': (sashes, {}), 'glass': (glazed, {}), 'panel': (panel, {}), 'louvre': (panel, {'kind': 'louvre'}),
    'brick-arch': (arches, {'brick': True}), 'brick-sash': (sashes, {'brick': True}), 'brick-panel': (panel, {'brick': True}),
    'brick-louvre': (panel, {'brick': True, 'kind': 'louvre'}), 'works': (works, {}),
}
PIECES = {name: ik.finished(builder, ROOFING) for name, builder in {
    **{name: (lambda rng, wall=wall: wall[0](rng, **wall[1])) for name, wall in WALLS.items()},
    **{'base-'+name: (lambda rng, wall=wall: wall[0](rng, True, **wall[1])) for name, wall in WALLS.items()},
    'balcony': balcony,
    **{'hall-'+kind: (lambda rng, kind=kind: hall(rng, kind)) for kind in ('window', 'louvre', 'panel')},
    **{'base-hall-'+kind: (lambda rng, kind=kind: hall(rng, kind, base=True)) for kind in ('window', 'louvre', 'panel', 'door')},
    **{'hall-top-'+kind: (lambda rng, kind=kind: hall(rng, kind, top=True)) for kind in ('window', 'louvre', 'panel')},
    'hall-quoins': lambda rng: quoins(rng, banded=False), 'hall-quoins-base': lambda rng: quoins(rng, True, banded=False),
    'base-arcade': arcade, 'base-shop': lambda rng: arcade(rng, 'shop'),
    'base-service': lambda rng: panel(rng, True, kind='service'), 'base-brick-service': lambda rng: panel(rng, True, brick=True, kind='service'),
    'entrance': entrance, 'entrance-med': lambda rng: entrance(rng, 'med'),
    'quoins': quoins, 'quoins-base': lambda rng: quoins(rng, True), 'turret': turret, 'turret-base': lambda rng: turret(rng, True),
    'mansard': mansard, 'mansard-plain': lambda rng: mansard(rng, dormers=False), 'mansard-corner': mansard_corner,
    'mansard-turret': lambda rng: turret_top(rng, mansard_corner),
    'battlement': battlement, 'battlement-corner': battlement_corner, 'battlement-turret': lambda rng: turret_top(rng, battlement_corner),
    'parapet': lambda rng: battlement(rng, merlons=False), 'parapet-corner': parapet_corner,
    'hall-eave': hall_eave, 'hall-eave-corner': lambda rng: hall_eave(rng, k.ROUND),
    'chimney': chimney, 'cupola': cupola, 'skylight': skylight, 'plant': plant, 'duct': duct, 'tank': tank,
    'hatch': hatch, 'vent': vent,
}.items()}

PLANAR = {STONE: REPEAT, BRICK: REPEAT, SLATE: SLATE_REPEAT, COPPER: COPPER_REPEAT}
# Roofs crowded as a working building's: two or three things a hex.
FITTINGS = [
    {'chimney': [[-7, 7, 0]], 'plant': [[0, -6, 0]], 'vent': [[8, 8, 0]]},
    {'cupola': [[0, 3, 0]], 'duct': [[0, -9, 0]]},
    {'skylight': [[0, 6, 0]], 'tank': [[-7, -7, 0]], 'vent': [[7, -6, 0]]},
    {'chimney': [[-7, 2, 90], [7, 2, 90]], 'hatch': [[0, -8, 0]], 'duct': [[0, 10, 0]]},
    {'plant': [[0, 6, 0]], 'vent': [[-6, -7, 0], [6, -7, 0]], 'hatch': [[0, -13, 0]]},
    {'tank': [[6, 5, 0]], 'chimney': [[-7, 5, 0]], 'duct': [[0, -8, 0]]},
]
HALL_FITTINGS = [
    {'skylight': [[0, 5, 0]], 'vent': [[-8, -7, 0], [0, -7, 0], [8, -7, 0]]},
    {'plant': [[0, -5, 0]], 'tank': [[0, 8, 0]]},
    {'duct': [[0, 6, 0], [0, -6, 0]], 'hatch': [[0, 13, 0]]},
    {'skylight': [[0, -6, 0]], 'plant': [[0, 6, 0]]},
    {'tank': [[-7, 4, 0]], 'vent': [[6, 6, 0], [6, -6, 0]], 'duct': [[0, -10, 0]]},
    {'plant': [[0, 5, 0]], 'chimney': [[7, -6, 0]], 'hatch': [[-7, -8, 0]]},
]
# A works door: a dark green sectional leaf with a row of panes in an iron frame.
DOOR = k.door((k.SECTIONAL, (.34, .42, .38)), (PAINT, IRON), jamb=2.0, header=2.6, out=1.0, depth=3.2, recess=.8, lintel=LEVEL-COURSE+1.8,
              panel=3.0, section=12.0, seam=(PAINT, IRON), stripe=(HAZARD, (1, 1, 1), 4.0), stripeHeight=1.4,
              windows=k.door_windows(3.4, 1.2, 7.4, 6.0), threshold=(CAST, (.46, .46, .46)), apron=4.0)
MANSARD = {'material': ROOF_DECK, 'repeat': 18.0, 'inset': SKIRT-.1, 'heights': [DECK], 'aviationLights': True}
FLAT = {'material': ROOF_DECK, 'repeat': 18.0, 'inset': PARAPET_DEEP-.1, 'heights': [.6], 'aviationLights': True}


def roof(slab, edge, turrets=False):
    """A roof of `slab`, the `edge` piece along its walls and `<edge>-corner` on its corners; with turrets, `<edge>-turret`
    on a square corner and the plain corner on a hex's own, shallower one (BayKit's `shallow`)."""
    run = k.run([edge], PLANAR, round_piece=edge+('-turret' if turrets else '-corner'))
    if edge == 'mansard':
        # Dormers keep off a wall's ends, where it turns a corner or runs on into another roof: those stretches are plain.
        run.update({'margin': 4.0, 'ends': {'piece': 'mansard-plain', 'length': 12.0}})
    if turrets:
        run['shallow'] = {'piece': edge+'-corner', 'length': k.ROUND}
    return {**slab, 'runs': [run]}


ROOFS = {
    'mansard': roof(MANSARD, 'mansard'),
    'mansard-turrets': roof(MANSARD, 'mansard', True),
    'parapet': roof(FLAT, 'parapet'),
    'battlement': roof(FLAT, 'battlement', True),
    # A hall's roof: verdigris copper bowed over the hall on iron ribs over a cornice, its gable ends in the walls' brick.
    'vault': {'material': COPPER, 'repeat': COPPER_REPEAT, 'inset': 0.0, 'heights': [0.3], 'aviationLights': True,
              'vault': k.vault('bow', 9.0, (1, 1, 1), (BRICK, BRICK_TONE, REPEAT), ('structures/common/painted-steel', IRON), rib=(1.2, .5)),
              'runs': [k.run(['hall-eave'], PLANAR, round_piece='hall-eave-corner')]},
}


HALL_BAYS = ['hall-window', 'hall-panel', 'hall-window', 'hall-louvre']
HALL_TOPS = [bay.replace('hall-', 'hall-top-') for bay in HALL_BAYS]  # The storey under the eave: the strips' heads.


def variant(name, bases, floors, door, roof='mansard', turrets=False, layouts=FITTINGS, hall=False, building_class=None):
    """bases, floors: the runs its storeys pick among, as bay lists. roof: its roof's name. turrets: on its square
    corners (its roof's too). hall: the look's hall (theme_kits' hall_roof): its corners a hall's quoins, without the
    storeys' course; the storey under its roof ends its strips: windows in round arches. building_class: the class of
    building that draws it unless told otherwise."""
    based = lambda bays: [bay if bay.startswith('base-') else 'base-'+bay for bay in bays]
    corner = 'turret' if turrets else 'hall-quoins' if hall else 'quoins'

    def run(bays, door=None, piece=corner, plain='quoins'):
        result = k.run(bays, PLANAR, door, piece)
        if turrets:
            # A turret stands on a square corner; a hex's own, shallower, takes the quoins (BayKit's `shallow`).
            result['shallow'] = {'piece': plain, 'length': k.ROUND}
        return result
    return {
        'name': name, **k.hall_roof(hall), **({'class': building_class} if building_class else {}), 'roof': roof,
        'lone': k.LONE, 'bandEnd': 1.75, 'cornerRadius': TURRET_CORNER if turrets else CORNER, 'cornerSegments': 1,
        'floors': {'material': STONE, 'repeat': REPEAT, 'inset': 3.0, 'heights': [0.05]},
        'sidewalk': {'material': ROOF_DECK, 'repeat': 18.0, 'width': 5.0, 'kerb': 0.4},
        'fittings': layouts,
        'varyBays': True,
        'largeDoor': DOOR,
        'base': [run(based(bays), door, corner+'-base', 'quoins-base') for bays in bases],
        'floor': [run(bays) for bays in floors],
        **({'top': [run(HALL_TOPS)]} if hall else {}),
    }


VARIANTS = [
    variant('habitat', (['arcade', 'arcade', 'sash', 'arcade'], ['arcade', 'sash', 'arcade', 'arcade']),
            (['balcony', 'sash', 'balcony', 'arch'], ['sash', 'balcony', 'arch', 'balcony']), 'entrance', 'mansard-turrets', True),
    variant('tower', (['arcade', 'arch', 'arcade'], ['arch', 'arcade', 'arch']), (['glass', 'arch', 'glass'], ['arch', 'glass', 'arch']), 'entrance',
            'mansard-turrets', True),
    variant('offices', (['arch', 'sash', 'arch', 'service'], ['sash', 'arch', 'arch', 'sash']),
            (['sash', 'arch', 'sash', 'glass'], ['arch', 'sash', 'glass', 'sash']), 'entrance'),
    # Stone storeys and brick ones by turns: never bay by bay.
    variant('commercial', (['shop', 'shop', 'arcade'], ['shop', 'arcade', 'shop']),
            (['arch', 'sash', 'arch', 'arch'], ['brick-arch', 'brick-sash', 'brick-arch', 'brick-arch']), 'entrance'),
    variant('medical', (['sash', 'arch', 'sash', 'service'], ['arch', 'sash', 'sash', 'louvre']),
            (['sash', 'glass', 'sash'], ['glass', 'sash', 'sash']), 'entrance-med'),
    variant('industrial', (['works', 'brick-panel', 'works', 'brick-service'], ['brick-panel', 'works', 'brick-service', 'works']),
            (['works', 'brick-louvre', 'works', 'brick-panel'], ['brick-panel', 'works', 'works', 'brick-louvre']), 'entrance',
            roof='parapet', layouts=HALL_FITTINGS),
    # A hall: stone buttresses and strips of iron-framed windows, louvres and sunk panels up its whole height (every
    # storey lays the same bays, so they stack; the top one ends them in round arches). A hangar-class building draws it
    # unless told otherwise, under a copper roof that spans it unless it chooses the flat roof and parapet.
    variant('hangar', (HALL_BAYS,), (HALL_BAYS,), 'base-hall-door', roof='parapet', layouts=HALL_FITTINGS, hall=True),
    variant('armoury', (['arch', 'panel', 'arch', 'service'], ['panel', 'arch', 'panel', 'arch']),
            (['arch', 'panel', 'sash', 'arch'], ['sash', 'arch', 'arch', 'panel']), 'entrance', roof='battlement', turrets=True,
            layouts=HALL_FITTINGS, building_class='fortress'),
]


def build():
    k.KITS['heritage'] = (PIECES, ROOFS, VARIANTS)
    # Limestone takes a building's tint; brick, slate, copper, iron and glass keep theirs.
    k.build('heritage', painted=lambda obj: obj['board_material'] == STONE)


if __name__ == '__main__' and '--' in sys.argv:
    build()
