"""The Imperial look as a connected building kit: its pieces GLB and kit JSON.

Run: blender -b --factory-startup --python imperial_kit.py
Writes data/models/buildings/imperial/imperial-pieces.glb and imperial.json, for the game's bays kit (GeneratedKit,
BayKit), as theme_kits writes the other looks' (its piece frame, levels of detail and export).

Imperial: warm stone cladding over a dark granite plinth, dark teal glass in bronze-dark frames, red lacquer columns and
portals, wall lanterns, and charcoal standing-seam roofs whose eaves flare out past the walls to a bronze lip. Every bay
runs between half piers (stone, or red lacquer columns); every storey ends in a stone course; a facet cuts each convex
corner, a stone pier on the walls. The roof module is the eave: a seamed skirt from the bronze lip up to a bronze-capped
curb round a deck of paving, and on each corner's facet the piece that runs the eave out and up to a tip, so a roof of
any outline reads as hipped with upturned corners. Variants name what the sheets' buildings are: offices, tower (glass
from pier to pier), habitat (loggias between red columns), commercial (shopfronts), medical, industrial and a hangar's
hall; two more take the authored buildings' forms, their roofs' corners drawn out to swept-up points: pavilion (an
arcade under glass between lacquer columns, lacquer posts at its corners) and residence (paper screens behind dark
lattices).
"""
import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import authored_examples as shared
import civic_blocks as c
import civic_habitat as h
import theme_kits as k
from civic_blocks import HAZARD, TEAL_GLASS
from civic_habitat import CAST, LOUVRE, PAINT, PALE_GLASS, SLATS, add, cuboid, deck, disc
from glb_geometry import display
from theme_kits import LEVEL, W, back_wall, facade, front, glass, mullions, recess

STONE = 'structures/imperial/stone-cladding'  # Warm beige limestone in its albedo: drawn near white.
SEAMED = 'structures/imperial/standing-seam'  # Charcoal in its albedo; eight seams a repeat, laid down the slope.
STONE_REPEAT, SEAM_REPEAT = 18.0, 16.0  # Panels 9 by 6; a seam every 2.
WALL, PIER_TONE, COURSE_TONE = (1, 1, 1), (.95, .94, .92), (.90, .89, .87)
GRANITE = (.46, .45, .44)  # The plinth: cast concrete drawn dark, under half the stone's value.
LACQUER = (.62, .30, .25)
BRONZE = (.55, .44, .26)
DARK = (.15, .16, .16)  # Window frames, sign bands, door leaves.
SPANDREL = (.20, .27, .27)
STEEL_GREY = (.50, .51, .52)
PALE_LOUVRE = (.84, .85, .84)  # Roof plant's screens: pale boxes on the dark roofs.
LANTERN = (.95, .80, .55)
TEAL = (.05, .45, .42)
SKY_PANE = (1, 1, 1)  # One pane in four shows the sky, one in seven a warm room: never one flat tone.
WARM_ROOM = (.40, .34, .27)  # A warm pane by day: the room behind it, on paint (the glass's own blue cannot be tinted warm).
SHOP_GLOW = (.34, .27, .17)  # A shopfront glows faintly by day too: under a deep eave its glass would be a black band.
panes = itertools.count()
PALE_PANE = (1, 1, .96)  # Roof glass: lanterns, monitors, tiers.
NIGHT = tuple(display(v) for v in (.12, .05, .012))  # Lit rooms: amber, a share of the windows.
SOFFIT = (.40, .39, .37)
PLINTH = 5.6  # The ground storey's granite course.
COURSE = 16.8  # Where a storey's stone course starts: the line between storeys.
PIER, PIER_OUT = 2.4, 1.2  # Half the stone pier between two bays, and how far it stands out of the wall: a shadow a bay.
COLUMN, COLUMN_OUT = 1.5, 2.0  # Half a red lacquer column likewise.
EAVE_OUT = 6.0  # How far the eave flares out past the wall.
SKIRT, SKIRT_TOP = 10.0, 6.0  # How far in from the wall the roof's skirt ends in its curb (no farther than the kit carries a
# wall's pieces on past an inside corner, KitOutline.EXTEND: two skirts meet there in a valley), and how high.
DECK = 3.0  # The roof deck inside the skirt: a shallow well of grey paving.
ROOF_DECK = 'structures/imperial/roof-pavers'
# The skirt's section (out of the wall negative, up from the roof's line): flatter at the eave, steeper to the curb.
EAVE = [(-EAVE_OUT, -1.2), (-3.0, -.2), (.5, 1.2), (4.2, 3.2), (7.8, 5.3), (SKIRT-1.2, SKIRT_TOP)]
FASCIA = 1.4  # The eave's bronze edge, tall enough to stay a line at the board's zoom.
TIP_OUT, TIP_UP = 3.2, 3.0  # A corner's eave runs out and turns up to a tip.
CORNER = 6.0  # The facet that cuts a convex corner (the kit's cornerRadius): wide enough that its trims cross at the curb.
REACH = 10.0  # How far the kit carries a facet's piece on past both its ends (KitOutline.EXTEND).
# A pointed corner's eave, each side of the corner's line: (how far from it along the facet, out past the eave, up).
POINT = [(4.6, 0.0, 0.0), (3.4, .6, .3), (2.2, 1.6, 1.0), (1.1, 3.0, 2.0), (.5, 4.0, 2.75), (0.0, 5.0, 3.4)]
RIB = (.20, .21, .22)  # A pointed corner's hip: the roof's own dark.
SHOE = (.36, .29, .17)  # The tip's bronze shoe: facing the sky, drawn darker than the eave's edge to match it.
PAPER = (.86, .82, .71)  # A screen's paper panes: ivory, about the stone's own value.
TIMBER = (.30, .22, .16)  # A screen's lower panel.


def pane(name, x0, x1, z0, z1, y, lit, shop=False, dark=TEAL_GLASS, room=WARM_ROOM):
    """A pane: dark glass (teal, or another look's `dark`), or bright with the sky, or the warm room behind it (`room`),
    chosen pane by pane; a lit room behind it at night or none. A shop's is always its warm room, glowing faintly all
    day."""
    pick = next(panes)*7 % 20
    quad = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    if shop:
        add(name, PAINT, WARM_ROOM, quad, [(0, 1, 2, 3)], light=SHOP_GLOW)
    elif pick < 3:
        add(name, PAINT, room, quad, [(0, 1, 2, 3)], light='night' if lit else 'off')
    else:
        glass(name, x0, x1, z0, z1, y, lit, SKY_PANE if pick < 8 else dark, PALE_GLASS)


def window(name, x0, x1, z0, z1, rng, lights=3, warm=.5, depth=.8, transom=2.6, **tones):
    """A window in a dark frame: its reveal, panes (some lit) with a dark line between, bars and a transom."""
    recess(name, x0, x1, z0, z1, depth, DARK, PAINT)
    for i in range(lights):
        pane(name+' glass', x0+(x1-x0)*i/lights+.1, x0+(x1-x0)*(i+1)/lights-.1, z0+.1, z1-.1, depth-.06, rng.random() < warm, **tones)
    mullions(name, x0, x1, z0, z1, depth-.1, lights, DARK, PAINT)
    if transom:
        cuboid(name+' transom', x0, x1, depth-.25, depth-.05, z1-transom-.15, z1-transom+.15, PAINT, DARK, omit='bk', detail=True)


def piers(length, base, red=False):
    """A bay's ends: half the stone pier it shares with the next bay, or half a red lacquer column standing clear of the
    storey's course; on the ground its granite foot."""
    width, out = (COLUMN, COLUMN_OUT) if red else (PIER, PIER_OUT)
    foot = PLINTH if base else 0.0
    for x0, x1, inner in ((0, width, 'l'), (length-width, length, 'r')):
        if red:
            cuboid('column', x0, x1, -out, 0, foot, LEVEL, PAINT, LACQUER, omit='bk')
        else:
            cuboid('pier', x0, x1, -out, 0, foot, COURSE, STONE, PIER_TONE, omit='bkt'+inner)
        if base:
            cuboid('pier foot', x0, x1, -out-.3, 0, 0, foot, CAST, GRANITE, omit='bk'+('' if red else inner))


def course(length):
    """The stone course that ends a storey."""
    cuboid('course', 0, length, -PIER_OUT-.4, 0, COURSE, LEVEL, STONE, COURSE_TONE, omit='klr')


def plinth(length, gaps=()):
    """The granite course along the ground storey, its top weathered back to the wall; open at gaps (x0, x1)."""
    edges = sorted({0.0, length, *[min(max(v, 0.0), length) for gap in gaps for v in gap]})
    for x0, x1 in zip(edges, edges[1:]):
        if not any(gap[0] <= x0+1e-6 and gap[1] >= x1-1e-6 for gap in gaps):
            c.extrude('plinth', [(0, 0), (.6, 0), (.6, PLINTH-.4), (0, PLINTH)], front, x0, x1, CAST, GRANITE)


def frame(length, holes, base, red=False, back=3.0):
    """A bay's wall: stone less holes (x0, x1, z0, z1) between its half piers, the storey's course, on the ground the
    granite plinth, open where a hole reaches the ground."""
    facade('wall', holes, PLINTH if base else 0.0, COURSE, length, WALL, du=12, dv=9, key=STONE)
    piers(length, base, red)
    course(length)
    if base:
        plinth(length, [hole[:2] for hole in holes if hole[2] < PLINTH])
    back_wall(length, 0, LEVEL, back)


def lantern(x, z, y=0.0):
    """A wall lantern, a storey's quarter tall: a warm lamp between dark caps, always lit."""
    cuboid('lantern', x-.5, x+.5, y-.8, y, z, z+4.4, PAINT, LANTERN, omit='k', light=c.AMBER_LIGHT)
    for z0, z1 in ((z-.4, z), (z+4.4, z+4.8)):
        cuboid('lantern cap', x-.7, x+.7, y-1.0, y, z0, z1, PAINT, DARK, omit='k', detail=True)


def windows(kind, length):
    """A bay's windows as (x0, x1, lights): one about 5 a light, a pair, a ribbon nearly from pier to pier, a slit, a
    clerestory strip."""
    a, b, mid = PIER, length-PIER, length/2
    spans = {'window': [(a+2, b-2, 5)], 'pair': [(a+1.4, mid-.8, 3.7), (mid+.8, b-1.4, 3.7)], 'ribbon': [(a+.6, b-.6, 3.6)],
             'slit': [(mid-1.4, mid+1.4, 9)], 'clerestory': [(a+1, b-1, 3.44)]}.get(kind, ())
    return [(x0, x1, max(1, round((x1-x0)/light))) for x0, x1, light in spans]


def bay(rng, kind, base=False, length=W):
    """A stretch of wall between stone half piers: a window of three lights, a pair, a ward's ribbon, a slit, a plain
    panel, a louvre, a tall louvred slot (storey on storey, one slit up a wall), or a hall's clerestory strip over a louvre
    band."""
    sill, head = (10.8 if kind == 'clerestory' else PLINTH+1.2 if base else 4.8), 14.8
    spans = windows(kind, length)
    frame(length, [(x0, x1, sill, head) for x0, x1, _ in spans], base)
    for x0, x1, lights in spans:
        window('window', x0, x1, sill, head, rng, lights, transom=0 if kind in ('clerestory', 'slit') else 2.6)
    if kind == 'louvre':
        half = min(5.5, length/2-PIER-.8)
        c.louvre('louvre', front, length/2-half, length/2+half, sill+.6, 13.4)
    elif kind == 'grille':
        c.louvre('louvre', front, PIER+.8, length-PIER-.8, PLINTH+1.4 if base else 2.0, 15.2)
    elif kind == 'slot':
        c.louvre('louvre', front, length/2-1.7, length/2+1.7, PLINTH+1.6 if base else 1.0, 15.8)
    elif kind == 'clerestory':
        c.louvre('louvre', front, PIER+1, length-PIER-1, (PLINTH+1.2 if base else 3.6), 9.0)
    elif kind == 'slit' and base:
        lantern(length/2-5.6, 7.8)


def curtain(rng, base=False, length=W, pier=PIER, banded=True, red=False):
    """Glass from pier to pier, two rows of panes a storey over dark spandrels: the tower's skin; on the ground, a lobby's
    tall panes over the plinth. Not banded (no storey course), the glass runs on from storey to storey behind a dark spandrel, between
    piers `pier` wide: a tower's face. Red, between lacquer columns: a hall's glazed wall."""
    x0, x1, depth = pier, length-pier, .7
    low, head = (PLINTH if base else 0.0), (COURSE if banded else LEVEL)
    for a, b, inner in ((0, pier, 'l'), (length-pier, length, 'r')):
        if red:
            cuboid('column', a, b, -COLUMN_OUT, 0, low, LEVEL, PAINT, LACQUER, omit='bk')
        else:
            cuboid('pier', a, b, -PIER_OUT, 0, low, head, STONE, PIER_TONE, omit='bkt'+inner)
        if base:
            cuboid('pier foot', a, b, -PIER_OUT-.3, 0, 0, low, CAST, GRANITE, omit='bk'+inner)
    if banded:
        course(length)
    if base:
        plinth(length)
    if banded:
        recess('curtain', x0, x1, low, head, depth, DARK, PAINT)
    else:
        # The glass runs on into the storeys above and below: reveals and a back, no sill or soffit between them.
        add('curtain reveal', PAINT, DARK, [(x0, 0, low), (x0, depth, low), (x0, depth, head), (x0, 0, head)], [(0, 1, 2, 3)])
        add('curtain reveal', PAINT, DARK, [(x1, depth, low), (x1, 0, low), (x1, 0, head), (x1, depth, head)], [(0, 1, 2, 3)])
        add('curtain back', PAINT, k.DARK_BACK, [(x0, depth, low), (x1, depth, low), (x1, depth, head), (x0, depth, head)], [(0, 1, 2, 3)])
    panes = max(1, round((x1-x0)/6.4))
    for z0, z1 in ([(low+.4, COURSE-.4)] if base else [(1.9, 8.2), (10.3, 16.6)]):
        for i in range(panes):
            pane('curtain glass', x0+(x1-x0)*i/panes+.1, x0+(x1-x0)*(i+1)/panes-.1, z0, z1, depth-.06, rng.random() < (.6 if base else .4))
    if not base:
        for z0, z1 in ((.1, 1.8), (8.3, 10.2))+(() if banded else ((16.7, LEVEL),)):
            add('curtain spandrel', PAINT, SPANDREL, [(x0, depth-.08, z0), (x1, depth-.08, z0), (x1, depth-.08, z1), (x0, depth-.08, z1)],
                [(0, 1, 2, 3)])
    mullions('curtain', x0, x1, low, head, depth-.1, panes, DARK, PAINT)
    back_wall(length, 0, LEVEL)


def red_window(rng, length=W):
    """A tall window of four lights from one red lacquer column to the next."""
    x0, x1 = COLUMN+.8, length-COLUMN-.8
    frame(length, [(x0, x1, 3.6, 14.8)], False, red=True)
    window('window', x0, x1, 3.6, 14.8, rng, max(1, round((x1-x0)/4.85)), warm=.5)


def balcony(rng, length=W):
    """A loggia between red lacquer columns: glass doors at its back, a rail along its edge."""
    depth, x0, x1, floor, top = 3.6, COLUMN, length-COLUMN, .7, 15.4
    frame(length, [(x0, x1, floor, top)], False, red=True, back=depth+.1)
    recess('loggia', x0, x1, floor, top, depth, PIER_TONE, STONE)
    for a, b in ((x0+.8, length/2-.8), (length/2+.8, x1-.8)):
        for i in range(2):
            pane('loggia glass', a+(b-a)*i/2+.1, a+(b-a)*(i+1)/2-.1, floor+.3, 12.6, depth-.06, rng.random() < .5)
    cuboid('loggia rail', x0, x1, -.4, -.05, floor+3.1, floor+3.5, PAINT, PALE_LOUVRE, omit='b')
    for i in range(1, 6):
        x = x0+(x1-x0)*i/6
        cuboid('loggia rail post', x-.12, x+.12, -.32, -.12, floor, floor+3.1, PAINT, PALE_LOUVRE, omit='bt', detail=True)


def lattice(rng, base=False, length=W, lit=False):
    """A screen from pier to pier: leaves of pale paper over a timber panel behind a dark lattice; lit, its two middle
    leaves glow from their room at night."""
    x0, x1, depth = PIER+1.0, length-PIER-1.0, .7
    sill, head = (PLINTH+1.2 if base else 3.4), 14.8
    frame(length, [(x0, x1, sill, head)], base)
    recess('screen', x0, x1, sill, head, depth, DARK, PAINT)
    leaves = max(2, round((x1-x0)/4.4))
    for i in range(leaves):
        a, b = x0+(x1-x0)*i/leaves+.15, x0+(x1-x0)*(i+1)/leaves-.15
        add('screen paper', PAINT, PAPER, [(a, depth-.06, sill+.15), (b, depth-.06, sill+.15), (b, depth-.06, head-.15), (a, depth-.06, head-.15)],
            [(0, 1, 2, 3)], light='night' if lit and abs(i-(leaves-1)/2) < 1 else 'off')
        panel = sill+(head-sill)*.28
        add('screen panel', PAINT, TIMBER, [(a, depth-.1, sill+.15), (b, depth-.1, sill+.15), (b, depth-.1, panel), (a, depth-.1, panel)], [(0, 1, 2, 3)])
        # A lattice of two by two over the panel, its bars broad: thin ones break into dashes at the board's zoom.
        for p, q, z0, z1 in (((a+b)/2-.4, (a+b)/2+.4, panel, head-.15), (a, b, (panel+head)/2-.4, (panel+head)/2+.4)):
            add('screen lattice', PAINT, DARK, [(p, depth-.14, z0), (q, depth-.14, z0), (q, depth-.14, z1), (p, depth-.14, z1)], [(0, 1, 2, 3)])
    for i in range(1, leaves):
        x = x0+(x1-x0)*i/leaves
        cuboid('screen post', x-.3, x+.3, depth-.25, depth-.05, sill, head, PAINT, DARK, omit='bk')


def arcade(rng, length=W):
    """An arcade's bay on the ground, as the Commercial Center's: lacquer columns standing clear of a shopfront set deep
    behind them, its glass lit over a granite stall, a dark sign band over it, a lantern hanging in the opening."""
    x0, x1, top, depth = COLUMN, length-COLUMN, 13.4, 4.4
    frame(length, [(x0, x1, 0, top)], True, red=True, back=depth+.1)
    recess('arcade', x0, x1, 0, top, depth, PIER_TONE, STONE)
    back, head, band = depth-.06, top-2.6, top-4.4
    # The arcade's own paving: the kit's floor starts behind the shopfront.
    cuboid('arcade floor', x0, x1, -.2, depth, 0, .45, STONE, COURSE_TONE, omit='bk')
    cuboid('shop stall', x0, x1, depth-.5, depth, .45, 1.6, CAST, GRANITE, omit='bk')
    count = max(1, round((x1-x0)/5.25))
    for i in range(count):
        a, b = x0+(x1-x0)*i/count+.1, x0+(x1-x0)*(i+1)/count-.1
        pane('shop glass', a, b, 1.6, band-.1, back, True)
        pane('shop glass', a, b, band+.1, head, back, True, shop=True)  # Its lit band: the glow kept high.
        cuboid('shop mullion', a-.25, a+.05, depth-.3, depth-.05, 1.6, head, PAINT, DARK, omit='bk')
    cuboid('shop mullion', x0, x1, depth-.3, depth-.05, band-.1, band+.1, PAINT, DARK, omit='bk')
    cuboid('shop sign', x0, x1, depth-.5, depth, head, top, PAINT, DARK, omit='bk')
    cuboid('shop sign line', x0, x1, depth-.58, depth-.5, head, head+.2, PAINT, BRONZE, omit='bk', detail=True)
    mid = length/2
    cuboid('lantern', mid-.6, mid+.6, .9, 2.1, top-5.2, top-1.6, PAINT, LANTERN, omit='', light=c.AMBER_LIGHT)
    cuboid('lantern cap', mid-.8, mid+.8, .7, 2.3, top-1.6, top, PAINT, DARK, omit='t', detail=True)


def hall(rng, kind, base=False, length=W, top=False):
    """A hall's bay: stone between lacquer columns, storey on storey without a course, so columns and strips run the
    hall's whole height. Up its middle one strip: glass in a dark frame, dark louvres, or a deep sunk panel of stone
    slabs; door, on the ground, a steel door under a lantern. The top storey ends its strip under a lacquer beam from
    column to column and a dark frieze under the eave."""
    low, mid = (PLINTH if base else 0.0), length/2
    head = LEVEL-3.2 if top else LEVEL
    half = {'glass': 4.6, 'louvre': 1.8, 'panel': length/2-COLUMN-2.6, 'door': 0}[kind]
    x0, x1 = mid-half, mid+half
    holes = [(x0, x1, low, head)] if kind in ('glass', 'panel') else [(4.8, 9.2, 0, 9.0)] if kind == 'door' else []
    facade('wall', holes, low, LEVEL, length, WALL, du=12, dv=9, key=STONE)
    for a, b in ((0, COLUMN), (length-COLUMN, length)):
        cuboid('column', a, b, -COLUMN_OUT, 0, low, LEVEL, PAINT, LACQUER, omit='bkt')
        if base:
            cuboid('pier foot', a, b, -COLUMN_OUT-.3, 0, 0, low, CAST, GRANITE, omit='bk')
    if base:
        plinth(length, [hole[:2] for hole in holes if hole[2] < PLINTH])
    if top:
        cuboid('hall beam', COLUMN, length-COLUMN, -COLUMN_OUT+.5, 0, head+.4, LEVEL-1.0, PAINT, LACQUER, omit='klr')
        cuboid('hall frieze', COLUMN, length-COLUMN, -.5, 0, LEVEL-1.0, LEVEL, PAINT, DARK, omit='klr')
    depth = .8 if kind == 'glass' else 1.1
    if kind in ('glass', 'panel'):
        tone, key = (DARK, PAINT) if kind == 'glass' else ((.66, .65, .63), STONE)
        add('hall reveal', key, tone, [(x0, 0, low), (x0, depth, low), (x0, depth, head), (x0, 0, head)], [(0, 1, 2, 3)])
        add('hall reveal', key, tone, [(x1, depth, low), (x1, 0, low), (x1, 0, head), (x1, depth, head)], [(0, 1, 2, 3)])
        if base:
            add('hall sill', key, tone, [(x0, 0, low), (x1, 0, low), (x1, depth, low), (x0, depth, low)], [(0, 1, 2, 3)])
        if top:
            add('hall soffit', key, tone, [(x0, 0, head), (x1, 0, head), (x1, depth, head), (x0, depth, head)], [(3, 2, 1, 0)])
    rows = [(low+.3, 12.0), (12.3, head)] if base else [(.3, 6.0), (6.3, 12.0), (12.3, head)]
    if kind == 'panel':
        add('hall panel', STONE, (.86, .85, .83), [(x0, depth, low), (x1, depth, low), (x1, depth, head), (x0, depth, head)], [(0, 1, 2, 3)])
        for z0, _ in rows:  # The slabs' open joints.
            add('hall joint', PAINT, (.42, .41, .39), [(x0, depth-.02, z0-.3), (x1, depth-.02, z0-.3), (x1, depth-.02, z0), (x0, depth-.02, z0)],
                [(0, 1, 2, 3)])
    elif kind == 'glass':
        add('hall back', PAINT, k.DARK_BACK, [(x0, depth, low), (x1, depth, low), (x1, depth, head), (x0, depth, head)], [(0, 1, 2, 3)])
        for z0, z1 in rows:
            for a, b in ((x0+.1, mid-.15), (mid+.15, x1-.1)):
                pane('hall glass', a, b, z0, z1, depth-.06, rng.random() < .35)
            cuboid('hall bar', x0, x1, depth-.3, depth-.05, z0-.3, z0, PAINT, DARK, omit='bk')
        cuboid('hall post', mid-.15, mid+.15, depth-.3, depth-.05, low, head, PAINT, DARK, omit='bkt')
    elif kind == 'louvre':
        c.louvre('louvre', front, x0, x1, low+.5, head-.5)
    else:
        recess('service', 4.8, 9.2, 0, 9.0, .5, DARK, PAINT)
        add('service door', PAINT, (.34, .35, .36), [(5.0, .44, .2), (9.0, .44, .2), (9.0, .44, 8.8), (5.0, .44, 8.8)], [(0, 1, 2, 3)])
        lantern(7.0, 10.2)
        for x, width, height in ((14.2, 2.6, 5.2), (17.8, 3.2, 4.2)):
            cuboid('service cabinet', x-width/2, x+width/2, -1.9, -.6, 0, height, PAINT, (.42, .43, .44), omit='bk')
    back_wall(length, 0, LEVEL)


def shop(rng, kind, length=W):
    """A shopfront between red lacquer columns: lit glass over a granite stall, a dark sign band with bronze lines over
    it; wide, two panes; door, glass doors in its middle."""
    x0, x1, top, depth = COLUMN, length-COLUMN, 11.4, 1.6
    frame(length, [(x0, x1, 0, top)], True, red=True)
    recess('shop', x0, x1, 0, top, depth, DARK, PAINT)
    back = depth-.06
    if kind == 'door':
        mid = length/2
        for a, b in ((x0+.1, mid-3.1), (mid+3.1, x1-.1)):
            pane('shop glass', a, b, 1.2, top-.2, back, True, shop=True)
            cuboid('shop stall', a-.1, b+.1, depth-.5, depth, 0, 1.2, CAST, GRANITE, omit='bk')
        for a, b in ((mid-2.9, mid-.05), (mid+.05, mid+2.9)):
            pane('shop door', a, b, .5, 8.8, back, True, shop=True)
        pane('shop transom', mid-2.9, mid+2.9, 9.2, top-.2, back, True, shop=True)
        cuboid('shop step', mid-3.6, mid+3.6, -1.6, depth-.5, 0, .45, STONE, COURSE_TONE, omit='bk')
    else:
        panes = max(1, round((x1-x0)/(10.5 if kind == 'wide' else 5.25)))
        cuboid('shop stall', x0, x1, depth-.5, depth, 0, 1.2, CAST, GRANITE, omit='bk')
        for i in range(panes):
            pane('shop glass', x0+(x1-x0)*i/panes+.1, x0+(x1-x0)*(i+1)/panes-.1, 1.2, top-.2, back, True, shop=True)
        mullions('shop', x0, x1, 1.2, top-.2, depth-.1, panes, DARK, PAINT)
    cuboid('shop sign', x0+1, x1-1, -.35, 0, 12.0, 14.6, PAINT, DARK, omit='bk')
    for z in (12.0, 14.4):
        cuboid('shop sign line', x0+1, x1-1, -.42, -.35, z, z+.2, PAINT, BRONZE, omit='bk', detail=True)


def canopy(x0, x1, out=5.6, top=16.4, edge=14.2):
    """A seamed canopy sloping out of the wall to a bronze edge."""
    c.extrude('canopy', [(0, top), (out, edge), (out, edge-.4), (0, top-1.0)], front, x0, x1, SEAMED, (1, 1, 1))
    cuboid('canopy edge', x0-.1, x1+.1, -out-.25, -out+.05, edge-.5, edge+.15, PAINT, BRONZE)


def entrance(rng, kind, canopied=True):
    """The entrance: glass doors deep in a red lacquer portal (two posts and a beam) under a seamed canopy, a lantern on
    each side, a stone step; MED, a lit teal cross in place of one lantern. Without its canopy where a porch stands over
    it (imperial_buildings)."""
    x0, x1, top, depth = 4.4, W-4.4, 13.0, 2.2
    frame(W, [(x0, x1, 0, top)], True)
    recess('entrance', x0, x1, 0, top, depth, DARK, PAINT)
    for a, b in ((x0-.2, x0+1.5), (x1-1.5, x1+.2)):
        cuboid('portal post', a, b, -.7, .5, 0, top-1.6, PAINT, LACQUER, omit='bt')
    cuboid('portal beam', x0-.2, x1+.2, -.7, .5, top-1.6, top+.3, PAINT, LACQUER)
    a, b, mid, back = x0+1.5, x1-1.5, W/2, depth-.06
    for p, q in ((a+.1, mid-2.9), (mid-2.7, mid-.05), (mid+.05, mid+2.7), (mid+2.9, b-.1)):
        pane('entrance glass', p, q, .5, 9.2, back, True)
    pane('entrance transom', a+.1, b-.1, 9.5, top-1.7, back, True)
    cuboid('entrance rail', a, b, depth-.3, depth-.05, 9.2, 9.5, PAINT, DARK, omit='bk', detail=True)
    cuboid('entrance step', x0-.8, x1+.8, -2.2, depth-.3, 0, .45, STONE, COURSE_TONE, omit='bk')
    if canopied:
        canopy(2.4, W-2.4)
    lantern(3.3, 6.6)
    if kind == 'med':
        cuboid('med sign', 19.7, 21.9, -.3, 0, 7.6, 9.8, PAINT, TEAL, omit='bk', light=(.10, .55, .50))
        for a0, a1, b0, b1 in ((20.1, 21.5, 8.45, 8.95), (20.55, 21.05, 8.0, 9.4)):
            add('med cross', PAINT, (.92, .92, .88), [(a0, -.34, b0), (a1, -.34, b0), (a1, -.34, b1), (a0, -.34, b1)], [(0, 1, 2, 3)],
                light=(.80, .80, .74))
    else:
        lantern(W-3.3, 6.6)


def service(rng, length=W):
    """A service bay on the ground: a steel door under a lantern, a louvre, cabinets standing against the plinth."""
    x0, x1 = 4.8, 9.2
    frame(length, [(x0, x1, 0, 9.0)], True)
    recess('service', x0, x1, 0, 9.0, .5, DARK, PAINT)
    add('service door', PAINT, (.34, .35, .36), [(x0+.2, .44, .2), (x1-.2, .44, .2), (x1-.2, .44, 8.8), (x0+.2, .44, 8.8)], [(0, 1, 2, 3)])
    lantern((x0+x1)/2, 10.2)
    c.louvre('service louvre', front, 13, 20, 6.6, 12.6)
    for x, width, height in ((14.2, 2.6, 5.2), (17.8, 3.2, 4.2)):
        cuboid('service cabinet', x-width/2, x+width/2, -1.9, -.6, 0, height, PAINT, (.42, .43, .44), omit='bk')


def lip(x0, x1, y, z):
    """The eave's bronze edge along x at (y, z): a fascia from the soffit up to a lip standing over the roofing."""
    cuboid('eave edge', x0, x1, y-.35, y+.15, z-FASCIA, z+.35, PAINT, BRONZE, omit='lr')


def skirt_rows(x0, x1, first=1):
    """The skirt from row `first` up, along x: roofing, the curb's bronze cap and its inner face down to the deck."""
    for (y0, z0), (y1, z1) in zip(EAVE[first:], EAVE[first+1:]):
        add('eave roofing', SEAMED, (1, 1, 1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z1), (x0, y1, z1)], [(0, 1, 2, 3)])
    top = EAVE[-1]
    add('curb cap', PAINT, BRONZE, [(x0, top[0], top[1]), (x1, top[0], top[1]), (x1, SKIRT, top[1]), (x0, SKIRT, top[1])], [(0, 1, 2, 3)])
    add('curb', PAINT, DARK, [(x1, SKIRT, 0), (x1, SKIRT, top[1]), (x0, SKIRT, top[1]), (x0, SKIRT, 0)], [(3, 2, 1, 0)])


def hall_row(x0, x1):
    """A hall's eave from its second row up: the one row that carries the flare up to the roof that spans the hall."""
    (y0, z0), (y1, z1) = EAVE[1:3]
    add('eave roofing', SEAMED, (1, 1, 1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z1), (x0, y1, z1)], [(0, 1, 2, 3)])
    # Its back, down onto the roof: seen from the far side nothing shows through between the two.
    add('eave back', PAINT, DARK, [(x1, y1, 0), (x0, y1, 0), (x0, y1, z1), (x1, y1, z1)], [(0, 1, 2, 3)])


def eave(rng, length=W, hall=False):
    """The roof along a wall: a seamed skirt from the bronze-edged eave, over a soffit, up to the bronze-capped curb round
    the deck; a hall's, the flared eave alone, under the roof that spans it."""
    (y0, z0), (y1, z1) = EAVE[:2]
    add('eave roofing', SEAMED, (1, 1, 1), [(0, y0, z0), (length, y0, z0), (length, y1, z1), (0, y1, z1)], [(0, 1, 2, 3)])
    lip(0, length, y0, z0)
    add('eave soffit', PAINT, SOFFIT, [(0, y0, z0-FASCIA), (0, .3, -1.6), (length, .3, -1.6), (length, y0, z0-FASCIA)], [(0, 1, 2, 3)])
    hall_row(0, length) if hall else skirt_rows(0, length)


def eave_corner(rng, length=k.ROUND, hall=False):
    """The roof on the facet that cuts a convex corner: the skirt, its eave run out and turned up to a tip at the facet's
    middle. The kit stretches the piece over the facet and on past both its ends, where the walls' skirts trim it to a
    wedge that closes just past the curb: its curb joins the walls'."""
    (y0, z0), (y1, z1) = EAVE[:2]
    mid = length/2
    xs = [0.0, mid-1.0, mid, mid+1.0, length]
    low = [(x, y0-TIP_OUT*max(0.0, 1-abs(x-mid)), z0+TIP_UP*max(0.0, 1-abs(x-mid))) for x in xs]
    for i in range(len(xs)-1):
        a, b = low[i], low[i+1]
        add('eave roofing', SEAMED, (1, 1, 1), [a, b, (b[0], y1, z1), (a[0], y1, z1)], [(0, 1, 2, 3)])
        add('eave edge', PAINT, BRONZE, [(a[0], a[1], z0-FASCIA), (b[0], b[1], z0-FASCIA), (b[0], b[1], b[2]+.35), (a[0], a[1], a[2]+.35)], [(0, 1, 2, 3)])
        add('eave edge', PAINT, BRONZE, [(a[0], a[1], a[2]+.35), (b[0], b[1], b[2]+.35), (b[0], b[1]+.5, b[2]+.2), (a[0], a[1]+.5, a[2]+.2)], [(0, 1, 2, 3)])
        add('eave soffit', PAINT, SOFFIT, [(a[0], a[1], z0-FASCIA), (a[0], .3, -1.6), (b[0], .3, -1.6), (b[0], b[1], z0-FASCIA)], [(0, 1, 2, 3)])
    hall_row(0, length) if hall else skirt_rows(0, length)


def eave_point(rng, length=k.ROUND):
    """The roof on a corner's facet, pointed: the eave is drawn out along the corner's line and swept up to a tip
    (POINT), a dark hip running back from it up the skirt; the rows behind lift a little under it. At the facet's ends
    it meets the walls' eaves as eave_corner does."""
    (y0, z0), (y1, z1), (y2, z2) = EAVE[:3]
    mid, scale = length/2, length/(CORNER+2*REACH)  # Along the wall the kit stretches the piece: its parts that much narrower.
    half = [(CORNER/2+REACH, 0.0, 0.0)]+POINT
    columns = [(mid-x*scale, out, up) for x, out, up in half]+[(mid+x*scale, out, up) for x, out, up in half[-2::-1]]
    low = lambda p: (p[0], p[1], p[2]-FASCIA)
    lip = lambda p: (p[0], p[1], p[2]+.35)
    for (xa, oa, ua), (xb, ob, ub) in zip(columns, columns[1:]):
        a, b = (xa, y0-oa, z0+ua), (xb, y0-ob, z0+ub)
        ra, rb = (xa, y1, z1+ua*.3), (xb, y1, z1+ub*.3)
        # The tip itself is a bronze shoe: seen nearly edge on, seamed roofing there breaks up into teeth.
        add('eave roofing', *((PAINT, SHOE) if max(ua, ub) >= POINT[-1][2] else (SEAMED, (1, 1, 1))), [a, b, rb, ra], [(0, 1, 2, 3)])
        add('eave roofing', SEAMED, (1, 1, 1), [ra, rb, (xb, y2, z2), (xa, y2, z2)], [(0, 1, 2, 3)])
        add('eave edge', PAINT, BRONZE, [low(a), low(b), lip(b), lip(a)], [(0, 1, 2, 3)])
        add('eave edge', PAINT, BRONZE, [lip(a), lip(b), b, a], [(0, 1, 2, 3)])  # Its back, where it stands over the roofing.
        add('eave soffit', PAINT, SOFFIT, [low(a), (xa, .3, -1.6), (xb, .3, -1.6), low(b)], [(0, 1, 2, 3)])
    skirt_rows(0, length, first=2)
    tip_out, tip_up = POINT[-1][1:]
    path, wide = [(y0-tip_out+.3, z0+tip_up), (y1, z1+tip_up*.3), *EAVE[2:]], .18*scale
    for (ya, za), (yb, zb) in zip(path, path[1:]):
        for side in (-1, 1):
            verts = [(mid+side*wide, ya, za), (mid, ya, za+.5), (mid, yb, zb+.5), (mid+side*wide, yb, zb)]
            add('eave hip', PAINT, RIB, verts, [k.facing(verts, (side, 0, .2))])


def corner(rng, base=False, length=k.ROUND, red=False, banded=True):
    """A wall's corner facet: a stone pier with the storey's course, a slit of glass in a dark frame up its middle; on
    the ground its granite foot and a lantern in the slit's place. Red, a lacquer post on the pier, bronze at its foot
    and head. The kit
    stretches the piece nearly five times along the wall (over the facet and on past both its ends), so its parts are
    that much narrower here."""
    low, mid = (PLINTH if base else 0.0), length/2
    if red:
        top = COURSE if banded else LEVEL  # A hall's: without the course, post on post up the hall's height.
        cuboid('pier', 0, length, -PIER_OUT, 0, low, top, STONE, PIER_TONE, omit='bktlr')
        if base:
            cuboid('pier foot', 0, length, -PIER_OUT-.3, 0, 0, low, CAST, GRANITE, omit='bklr')
        half = COLUMN*length/(CORNER+2*REACH)  # As wide as a bay's column, on a facet the kit stretches.
        cuboid('column', mid-half, mid+half, -COLUMN_OUT, -PIER_OUT, low, top, PAINT, LACQUER, omit='bkt' if not banded else 'bk')
        if banded:
            for z in (low, COURSE-.8):
                cuboid('column band', mid-half*1.08, mid+half*1.08, -COLUMN_OUT-.12, -PIER_OUT, z, z+.8, PAINT, BRONZE, omit='bk', detail=True)
            course(length)
        back_wall(length, 0, LEVEL)
        return
    cuboid('pier', 0, length, -PIER_OUT, 0, low, COURSE, STONE, PIER_TONE, omit='bktlr')
    if base:
        cuboid('pier foot', 0, length, -PIER_OUT-.3, 0, 0, low, CAST, GRANITE, omit='bklr')
        cuboid('lantern', mid-.11, mid+.11, -PIER_OUT-.8, -PIER_OUT, low+1.6, low+6.0, PAINT, LANTERN, omit='k', light=c.AMBER_LIGHT)
    else:
        cuboid('corner slit', mid-.3, mid+.3, -PIER_OUT-.25, -PIER_OUT, 2.4, COURSE-2.0, PAINT, DARK, omit='k')
        cuboid('corner slit glass', mid-.17, mid+.17, -PIER_OUT-.4, -PIER_OUT-.25, 2.8, COURSE-2.4, PALE_GLASS, SKY_PANE, omit='k',
               light='night' if rng.random() < .4 else 'off')
    course(length)
    back_wall(length, 0, LEVEL)


def hipped(name, x0, x1, y0, y1, z, rise, over=1.2):
    """A hipped seamed roof over a box: its eaves `over` past the walls and bronze-edged, a dark soffit under them, its
    ridge along the longer side."""
    ex0, ex1, ey0, ey1 = x0-over, x1+over, y0-over, y1+over
    half = min(ex1-ex0, ey1-ey0)/2
    if ex1-ex0 >= ey1-ey0:
        r0, r1 = (ex0+half, (ey0+ey1)/2, z+rise), (ex1-half, (ey0+ey1)/2, z+rise)
    else:
        r0, r1 = ((ex0+ex1)/2, ey0+half, z+rise), ((ex0+ex1)/2, ey1-half, z+rise)
    e = [(ex0, ey0, z), (ex1, ey0, z), (ex1, ey1, z), (ex0, ey1, z)]
    along_x = ex1-ex0 >= ey1-ey0
    faces = ([(e[0], e[1], r1, r0), (e[1], e[2], r1), (e[2], e[3], r0, r1), (e[3], e[0], r0)] if along_x
             else [(e[0], e[1], r0), (e[1], e[2], r1, r0), (e[2], e[3], r1), (e[3], e[0], r0, r1)])
    for face in faces:
        verts = [p for i, p in enumerate(face) if p not in face[:i]]
        add(name+' roofing', SEAMED, (1, 1, 1), verts, [tuple(range(len(verts)))])
    add(name+' soffit', PAINT, SOFFIT, e[::-1], [(0, 1, 2, 3)])
    for a0, a1, b0, b1 in ((ex0-.15, ex1+.15, ey0-.15, ey0+.15), (ex0-.15, ex1+.15, ey1-.15, ey1+.15),
                           (ex0-.15, ex0+.15, ey0, ey1), (ex1-.15, ex1+.15, ey0, ey1)):
        cuboid(name+' edge', a0, a1, b0, b1, z-.4, z+.14, PAINT, BRONZE)


# Roof fittings: each stands on the deck about its origin.
def plant(rng):
    """Roof plant: two fan units behind a pale louvred screen."""
    for x in (-3.1, 3.1):
        cuboid('plant unit', x-2.5, x+2.5, -2.8, 2.8, 0, 3.6, PAINT, (.60, .61, .61), omit='b')
        disc('plant fan', x, 0, 3.62, 1.9, 'z', h.GRILLE, (.62, .64, .66), 12)
    for x0, x1, y0, y1 in ((-6.6, 6.6, -4.4, -4.1), (-6.6, 6.6, 4.1, 4.4), (-6.6, -6.3, -4.1, 4.1), (6.3, 6.6, -4.1, 4.1)):
        cuboid('plant screen', x0, x1, y0, y1, 0, 4.6, SLATS, PALE_LOUVRE, omit='b')


def tier(rng):
    """A second tier on a roof: a band of glass, lit from below at night, under its own hipped roof."""
    x, y = 4.8, 3.4
    cuboid('tier foot', -x, x, -y, y, 0, .9, PAINT, DARK, omit='bt')
    for quad in ([(-x, -y), (x, -y)], [(x, -y), (x, y)], [(x, y), (-x, y)], [(-x, y), (-x, -y)]):
        (ax, ay), (bx, by) = quad
        add('tier glass', PALE_GLASS, PALE_PANE, [(ax, ay, .9), (bx, by, .9), (bx, by, 3.8), (ax, ay, 3.8)], [(0, 1, 2, 3)], light='dim')
    hipped('tier', -x, x, -y, y, 3.8, 2.6, over=1.7)


def monitor(rng):
    """A roof light: a long hipped monitor of glass on a dark kerb, lit from below at night, its ridge bronze."""
    x, y, kerb, rise = 6.0, 2.6, 1.4, 2.0
    cuboid('monitor kerb', -x, x, -y, y, 0, kerb, PAINT, DARK, omit='bt')
    e = [(-x, -y, kerb), (x, -y, kerb), (x, y, kerb), (-x, y, kerb)]
    r0, r1 = (-x+y, 0, kerb+rise), (x-y, 0, kerb+rise)
    for face in ((e[0], e[1], r1, r0), (e[1], e[2], r1), (e[2], e[3], r0, r1), (e[3], e[0], r0)):
        add('monitor glass', PALE_GLASS, TEAL_GLASS, list(face), [tuple(range(len(face)))], light='dim')
    cuboid('monitor ridge', r0[0]-.2, r1[0]+.2, -.2, .2, kerb+rise-.1, kerb+rise+.2, PAINT, BRONZE, omit='b', detail=True)


def pavilion(rng):
    """A stair pavilion: a stone box with a door and a louvre under its own hipped, bronze-edged roof."""
    cuboid('pavilion', -4.6, 4.6, -3.4, 3.4, 0, 6.4, STONE, PIER_TONE, omit='bt')
    add('pavilion door', PAINT, (.34, .35, .36), [(-3.6, -3.44, 0), (-.8, -3.44, 0), (-.8, -3.44, 5.4), (-3.6, -3.44, 5.4)], [(0, 1, 2, 3)])
    add('pavilion louvre', SLATS, LOUVRE, [(.8, -3.44, 2), (3.8, -3.44, 2), (3.8, -3.44, 5), (.8, -3.44, 5)], [(0, 1, 2, 3)])
    hipped('pavilion', -4.6, 4.6, -3.4, 3.4, 6.4, 3.0, over=1.0)


def hatch(rng):
    cuboid('hatch kerb', -2.6, 2.6, -2.6, 2.6, 0, 1.2, PAINT, DARK, omit='b')
    deck('hatch lid', -2.2, 2.2, -2.2, 2.2, 1.22, PAINT, (.42, .43, .44))


def vent(rng):
    cuboid('vent', -2.4, 2.4, -1.8, 1.8, 0, 3.2, PAINT, STEEL_GREY, omit='b')
    for y, flip in ((-1.82, False), (1.82, True)):
        quad = [(-1.9, y, .6), (1.9, y, .6), (1.9, y, 2.7), (-1.9, y, 2.7)]
        add('vent louvre', SLATS, LOUVRE, quad[::-1] if flip else quad, [(0, 1, 2, 3)])


def roof_uvs(obj, repeat=SEAM_REPEAT):
    """Seamed roofing with its seams down each face's slope: across, along the face's level line; up, its slope."""
    uv = obj.data.uv_layers.new(name='UVMap')
    verts = obj.data.vertices
    world = obj.matrix_world
    turn = world.to_3x3()
    for face in obj.data.polygons:
        n = (turn @ face.normal).normalized()
        flat = math.hypot(n.x, n.y)
        t = (-n.y/flat, n.x/flat, 0.0) if flat > 1e-4 else (1.0, 0.0, 0.0)
        s = (n.y*t[2]-n.z*t[1], n.z*t[0]-n.x*t[2], n.x*t[1]-n.y*t[0])
        for li in face.loop_indices:
            co = world @ verts[obj.data.loops[li].vertex_index].co
            uv.data[li].uv = (co.x*t[0]+co.y*t[1])/repeat, (co.x*s[0]+co.y*s[1]+co.z*s[2])/repeat


def warm(obj):
    """A lit pane glows amber at night, not the shared windows' white."""
    if obj.get('building_night_emission') and tuple(obj['building_emission']) != tuple(h.DIM_LIGHT):
        shared.emissive(obj, NIGHT, night=True)


def finished(builder, roofing={SEAMED: SEAM_REPEAT}):
    """builder's piece as theme_kits.build takes it, its roofing (material: repeat) laid down the slopes: the kit lays a
    wall's roofing along the wall (its planar materials); fittings and viewers of the pieces GLB take these."""
    def build(rng):
        before = len(shared.objects)
        builder(rng)
        h.flush()
        for obj in shared.objects[before:]:
            if obj['board_material'] in roofing:
                roof_uvs(obj, roofing[obj['board_material']])
            warm(obj)
    return build


BAYS = ('window', 'pair', 'ribbon', 'slit', 'panel', 'louvre', 'grille', 'slot', 'clerestory')
PIECES = {name: finished(builder) for name, builder in {
    **{kind: (lambda rng, kind=kind: bay(rng, kind)) for kind in BAYS},
    **{'base-'+kind: (lambda rng, kind=kind: bay(rng, kind, base=True)) for kind in BAYS},
    'curtain': curtain, 'base-curtain': lambda rng: curtain(rng, base=True),
    'red-curtain': lambda rng: curtain(rng, pier=COLUMN, red=True), 'lattice': lattice, 'base-lattice': lambda rng: lattice(rng, base=True),
    'lattice-lit': lambda rng: lattice(rng, lit=True), 'base-lattice-lit': lambda rng: lattice(rng, base=True, lit=True),
    'base-arcade': arcade, 'eave-point': eave_point,
    'corner-red': lambda rng: corner(rng, red=True), 'corner-red-base': lambda rng: corner(rng, base=True, red=True),
    'red-window': red_window, 'red-balcony': balcony,
    **{'hall-'+kind: (lambda rng, kind=kind: hall(rng, kind)) for kind in ('glass', 'louvre', 'panel')},
    **{'base-hall-'+kind: (lambda rng, kind=kind: hall(rng, kind, base=True)) for kind in ('glass', 'louvre', 'panel', 'door')},
    **{'hall-top-'+kind: (lambda rng, kind=kind: hall(rng, kind, top=True)) for kind in ('glass', 'louvre', 'panel')},
    'hall-corner': lambda rng: corner(rng, red=True, banded=False), 'hall-corner-base': lambda rng: corner(rng, base=True, red=True, banded=False),
    'base-shop': lambda rng: shop(rng, 'narrow'), 'base-shop-wide': lambda rng: shop(rng, 'wide'), 'base-service': service,
    'entrance': lambda rng: entrance(rng, 'plain'), 'entrance-med': lambda rng: entrance(rng, 'med'),
    'entrance-shop': lambda rng: shop(rng, 'door'),
    'eave': eave, 'eave-corner': eave_corner, 'hall-eave': lambda rng: eave(rng, hall=True), 'hall-eave-corner': lambda rng: eave_corner(rng, hall=True),
    'corner': corner, 'corner-base': lambda rng: corner(rng, base=True),
    'plant': plant, 'tier': tier, 'monitor': monitor, 'pavilion': pavilion, 'hatch': hatch, 'vent': vent,
}.items()}

PLANAR = {STONE: STONE_REPEAT, SEAMED: SEAM_REPEAT}  # Panels run on from bay to bay; seams run down the skirt.
FITTINGS = [
    {'tier': [[0, 0, 0]]},
    {'plant': [[0, 0, 0]]},
    {'pavilion': [[0, 3, 0]], 'vent': [[2, -8, 0]]},
    {'tier': [[0, 3, 0]], 'hatch': [[2, -8, 0]]},
    {'monitor': [[0, 0, 0]]},
    {'plant': [[0, 4, 0]], 'vent': [[0, -6, 0]]},
]
HALL_FITTINGS = [
    {'monitor': [[0, 0, 0]]},
    {'vent': [[-3, 5, 0]], 'hatch': [[3, -6, 0]]},
    {'plant': [[0, 0, 0]]},
    {'monitor': [[0, 4, 0]], 'vent': [[0, -7, 0]]},
    {'tier': [[0, 0, 0]]},
    {'hatch': [[0, 0, 0]]},
]
# The sheets' works door: a grey sectional leaf with a row of panes and hazard marks in a red lacquer frame.
DOOR = k.door((k.SECTIONAL, (.50, .52, .54)), (PAINT, LACQUER), jamb=2.0, header=2.6, out=1.0, depth=3.2, recess=.8, lintel=LEVEL-COURSE+1.8,
              panel=3.0, section=12.0, seam=(PAINT, DARK), stripe=(HAZARD, (1, 1, 1), 4.0), stripeHeight=1.4,
              windows=k.door_windows(3.4, 1.2, 7.4, 6.0), threshold=(CAST, (.46, .46, .46)), apron=4.0)


def eave(corner):
    """The look's roof: a flared eave round a deck, the `corner` piece on its corners."""
    return {'material': ROOF_DECK, 'repeat': 18.0, 'inset': SKIRT-.1, 'heights': [DECK], 'aviationLights': True,
            'runs': [k.run(['eave'], PLANAR, round_piece=corner)]}


ROOFS = {
    'eave': eave('eave-corner'),
    'pointed-eave': eave('eave-point'),  # The authored buildings': its corners pointed.
    # A hall's roof: charcoal standing seam bowed over the hall on dark ribs over the flared eave alone, its gable ends dark
    # as the roof (the eave runs round them too: stone there would read as a gap in it).
    'vault': {'material': SEAMED, 'repeat': SEAM_REPEAT, 'inset': 0.0, 'heights': [0.3], 'aviationLights': True,
              'vault': k.vault('bow', 8.0, (1, 1, 1), ('structures/common/painted-steel', (.26, .27, .28)),
                               ('structures/common/painted-steel', (.20, .21, .22)), rib=(1.4, .5)),
              'runs': [k.run(['hall-eave'], PLANAR, round_piece='hall-eave-corner')]},
}


HALL_BAYS = ['hall-glass', 'hall-panel', 'hall-glass', 'hall-louvre']
HALL_TOPS = [bay.replace('hall-', 'hall-top-') for bay in HALL_BAYS]  # The storey under the eave: the strips' heads under a beam.


def variant(name, bases, floors, door, layouts=FITTINGS, corners=('corner-base', 'corner'), roof='eave', hall=False):
    """bases, floors: the runs its storeys pick among, as bay lists. roof: its roof's name. hall: the look's hall
    (theme_kits' hall_roof)."""
    based = lambda bays: [bay if bay.startswith('base-') else 'base-'+bay for bay in bays]
    return {
        'name': name, **k.hall_roof(hall), 'roof': roof, 'lone': k.LONE, 'bandEnd': 1.75,
        'cornerRadius': CORNER, 'cornerSegments': 1,
        'floors': {'material': STONE, 'repeat': STONE_REPEAT, 'inset': 3.0, 'heights': [0.05]},
        'sidewalk': {'material': STONE, 'repeat': STONE_REPEAT, 'width': 5.0, 'kerb': 0.4},
        'fittings': layouts,
        'varyBays': True,
        'largeDoor': DOOR,
        'base': [k.run(based(bays), PLANAR, door, corners[0]) for bays in bases],
        'floor': [k.run(bays, PLANAR, round_piece=corners[1]) for bays in floors],
        **({'top': [k.run(HALL_TOPS, PLANAR, round_piece=corners[1])]} if hall else {}),
    }


VARIANTS = [
    variant('offices', (['window', 'pair', 'window', 'slit'], ['pair', 'window', 'window', 'louvre']),
            (['window', 'pair', 'window', 'window'], ['pair', 'window', 'pair', 'window']), 'entrance'),
    variant('tower', (['curtain', 'curtain', 'window'], ['curtain', 'window', 'curtain']), (['curtain'],), 'entrance'),
    variant('habitat', (['pair', 'window', 'pair', 'slit'], ['window', 'pair', 'pair', 'window']),
            (['red-balcony', 'pair', 'red-balcony', 'pair'], ['pair', 'red-balcony', 'pair', 'red-balcony']), 'entrance'),
    variant('commercial', (['shop', 'shop-wide', 'shop'], ['shop-wide', 'shop', 'shop']),
            (['red-window', 'window', 'red-window', 'pair'], ['window', 'red-window', 'pair', 'red-window']), 'entrance-shop'),
    variant('medical', (['ribbon', 'window', 'ribbon', 'slit'], ['window', 'ribbon', 'ribbon', 'louvre']),
            (['ribbon', 'ribbon', 'window'], ['ribbon', 'window', 'ribbon']), 'entrance-med'),
    variant('industrial', (['service', 'louvre', 'clerestory', 'panel'], ['clerestory', 'service', 'panel', 'louvre']),
            (['clerestory', 'louvre', 'clerestory', 'panel'], ['panel', 'clerestory', 'clerestory', 'louvre']), 'entrance', HALL_FITTINGS),
    # A hall: lacquer columns and strips of glass, louvres and sunk panels up its whole height (every storey lays the
    # same bays, so they stack). A hangar-class building draws it unless told otherwise, under a seamed roof that spans
    # it unless it chooses the look's eave and deck.
    variant('hangar', (HALL_BAYS,), (HALL_BAYS,), 'base-hall-door', HALL_FITTINGS, corners=('hall-corner-base', 'hall-corner'),
            hall=True),
    # The authored buildings' forms, under roofs with pointed corners.
    variant('pavilion', (['arcade', 'arcade', 'lattice', 'arcade'], ['lattice-lit', 'arcade', 'arcade', 'shop-wide']),
            (['red-curtain', 'lattice', 'red-curtain', 'red-balcony'], ['lattice-lit', 'red-curtain', 'red-balcony', 'red-curtain']), 'entrance',
            corners=('corner-red-base', 'corner-red'), roof='pointed-eave'),
    variant('residence', (['lattice', 'pair', 'lattice-lit', 'slit'], ['pair', 'lattice', 'window', 'lattice']),
            (['lattice', 'red-balcony', 'lattice', 'pair'], ['red-balcony', 'lattice-lit', 'pair', 'lattice']), 'entrance', roof='pointed-eave'),
]


def build():
    k.KITS['imperial'] = (PIECES, ROOFS, VARIANTS)
    # Stone takes a building's tint; granite, lacquer, bronze, glass and roofs keep theirs.
    k.build('imperial', painted=lambda obj: obj['board_material'] == STONE)


if __name__ == '__main__' and '--' in sys.argv:
    build()
