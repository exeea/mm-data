"""The four hangars as connected building kits: their pieces GLBs and kit JSONs.

Run: blender -b --factory-startup --python hangar_kits.py -- [light|medium|heavy|hard ...]
Writes data/models/buildings/hangar_<weight>/hangar_<weight>_a-pieces.glb and hangar_<weight>_a.json, for the game's bays
kit (GeneratedKit, BayKit), as theme_kits writes the looks' (its piece frame, levels of detail and export).

A hangar is a hall: no storey of it has windows of rooms. Each kit has two variants. `default`, the designers' halls
(art/hangar_<weight>_a-proposal.glb, their wall bays between frames; the hardened one's frames battered buttresses),
dressed here in the board's materials with kerbs, louvres, strip windows, side doors and a far level, under a roof that
spans the hall as a hangar's does (BayKit's vault: a low gable, a bowstring roof, a concrete arch), the frames running on
over it as ribs. `alternative`: a corrugated steel shed on portal frames (light),
insulated steel panels over a concrete plinth (medium), precast concrete between buttresses (heavy), a battered bunker
under a burster slab (hardened). Each variant's `door` in the JSON is its large doors' look (KitDoors.Style): the game
cuts them into these walls where the board's author puts them.
"""
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import civic_blocks as c
import civic_habitat as h
import theme_kits as k
from civic_habitat import CAST, PAINT, PANELS, SLATS, STEEL, add, cuboid, deck, round_prism
from theme_kits import LEVEL, W, facade, front, glass, recess

CORRUGATED = 'structures/common/corrugated-painted'
SHEET = 'structures/common/painted-steel'
MATTE = 'structures/common/matte-steel'
BUNKER = 'structures/buildings/fortress-concrete'
DARK_ROOF = 'structures/buildings/fortress-roof'
TIN_ROOF = 'structures/common/corrugated'
DOOR = k.SECTIONAL
HAZARD = 'structures/common/hazard-stripes'
YELLOW = 'structures/common/safety-yellow'
ARMOUR = 'structures/buildings/fortress-steel'
GLASS = k.DOOR_GLASS
FRAME = (.34, .36, .37)  # Portal frames, girts and trims.
DARK = (.20, .21, .22)
KERB = (.70, .70, .67)
SAGE = (.74, .79, .76)  # The light shed's sheeting.
PALE = (.84, .86, .86)  # The medium hangar's panels.
BAND = (.36, .47, .58)  # Its band under the eave.
PRECAST = (.90, .89, .85)
RAW = (.97, .95, .91)  # Bunker concrete: its albedo is dark already.
WORK_LIGHT = (.50, .42, .26)


def columns(z0, out, width, key=MATTE, colour=FRAME, top=LEVEL):
    """A frame's half at each end of a bay: its neighbour's half makes it whole."""
    cuboid('column', 0, width, -out, 0, z0, top, key, colour, omit='bkl')
    cuboid('column', W-width, W, -out, 0, z0, top, key, colour, omit='bkr')


def work_light(x, z, y=-.7):
    add('work light', PAINT, WORK_LIGHT, [(x-.9, y, z-.3), (x+.9, y, z-.3), (x+.9, y, z+.3), (x-.9, y, z+.3)], [(0, 1, 2, 3)], light=c.AMBER_LIGHT)
    cuboid('work light hood', x-1.1, x+1.1, y, 0, z+.3, z+.5, MATTE, DARK, omit='k', detail=True)


def vent(name, x0, x1, z0, z1, frame=DARK):
    cuboid(name+' frame', x0-.4, x1+.4, -.25, 0, z0-.4, z1+.4, PAINT, frame, omit='bk')
    add(name, SLATS, h.LOUVRE, [(x0, -.27, z0), (x1, -.27, z0), (x1, -.27, z1), (x0, -.27, z1)], [(0, 1, 2, 3)])


def strip_window(name, x0, x1, z0, z1, rng, panes, lit=.25, depth=.8):
    """A strip of dim glass in a dark reveal: a hall's daylight, some panes lit by the lamps inside."""
    recess(name, x0, x1, z0, z1, depth, DARK, PAINT)
    for i in range(panes):
        a, b = x0+(x1-x0)*i/panes, x0+(x1-x0)*(i+1)/panes
        glass(name, a+.12, b-.12, z0, z1, depth-.06, rng.random() < lit)


# -- Light: a corrugated steel shed -----------------------------------------------------------------

def light_bay(rng, kind, base):
    z0 = 1.4 if base else 0.0
    holes = [(3, 21, 10.5, 14.5)] if kind == 'daylight' else []
    facade('wall sheeting', holes, z0, LEVEL, colour=SAGE, du=6, dv=6, key=CORRUGATED)
    if base:
        cuboid('kerb', 0, W, -.5, 0, 0, z0, CAST, KERB, omit='bklr')
    columns(z0, .7, .55)
    cuboid('girt', .55, W-.55, -.3, 0, 8.7, 9.3, MATTE, FRAME, omit='bklr', detail=True)
    if kind == 'vent':
        vent('wall louvre', 7, 17, 3.2 if base else 10.5, 7.4 if base else 14.7)
    elif kind == 'daylight':
        strip_window('daylight', 3, 21, 10.5, 14.5, rng, 3, lit=.35)
    elif kind == 'door':
        h.door('side', 12, 0, z0, c.SOUTH, lit=True)
        cuboid('door step', 9, 15, -1.6, 0, 0, z0, CAST, KERB, omit='bk')
    elif kind == 'brace':
        # Wind bracing across a bay: two flat bars.
        for a, b in (((.6, z0+.4), (W-.6, 16.8)), ((W-.6, z0+.4), (.6, 16.8))):
            dx, dz = b[0]-a[0], b[1]-a[1]
            n = math.hypot(dx, dz)
            ox, oz = -dz/n*.22, dx/n*.22
            add('brace', MATTE, FRAME, [(a[0]-ox, -.12, a[1]-oz), (b[0]-ox, -.12, b[1]-oz), (b[0]+ox, -.12, b[1]+oz), (a[0]+ox, -.12, a[1]+oz)],
                [(0, 1, 2, 3)], detail=True)
    k.back_wall(W, 0, LEVEL, colour=k.DARK_BACK)


def light_eave(rng, kind):
    """The shed's eave: a gutter along the wall's top and the sheeting's flashing."""
    cuboid('gutter', 0, W, -.75, 0, -.9, .1, MATTE, FRAME, omit='klr')
    cuboid('flashing', 0, W, 0, 1.1, 0, .45, MATTE, FRAME, omit='blr')
    if kind == 'pipe':
        cuboid('downpipe head', 11.4, 12.6, -.85, -.75, -2.2, -.9, MATTE, FRAME, omit='k', detail=True)


def light_ridge_vent(rng):
    for x in (-7, 0, 7):
        round_prism('ridge vent neck', x, 0, 0, 1.6, 1.1, MATTE, FRAME, 8)
        round_prism('ridge vent', x, 0, 1.6, 3.0, 1.7, MATTE, (.62, .64, .65), 8)


def light_skylight(rng):
    cuboid('skylight kerb', -8, 8, -3, 3, 0, .7, MATTE, FRAME, omit='b')
    add('skylight', GLASS, (1, 1, 1), [(-7.6, -2.6, .72), (7.6, -2.6, .72), (7.6, 2.6, .72), (-7.6, 2.6, .72)], [(0, 1, 2, 3)], light='dim')


def light_fan(rng):
    cuboid('fan box', -3, 3, -3, 3, 0, 2.2, PAINT, (.40, .42, .43), omit='b')
    deck('fan grille', -2.5, 2.5, -2.5, 2.5, 2.22, h.GRILLE, (.62, .64, .66))


# -- Medium: insulated panels over a plinth ---------------------------------------------------------

def medium_bay(rng, kind, base):
    z0 = 2.6 if base else 0.0
    holes = [(2.5, 21.5, 9.6, 13.2)] if kind == 'windows' else []
    facade('wall panels', holes, z0, LEVEL, colour=PALE, du=6, dv=6, key=SHEET)
    if base:
        c.extrude('plinth', [(0, 0), (.9, 0), (.5, z0), (0, z0)], front, 0, W, CAST, KERB)
    else:
        add('wall band', SHEET, BAND, [(0, -.04, 13.9), (W, -.04, 13.9), (W, -.04, 16.3), (0, -.04, 16.3)], [(0, 1, 2, 3)])
    for x in (6, 12, 18):  # The panels' joints.
        add('panel joint', PAINT, DARK, [(x-.1, -.03, z0), (x+.1, -.03, z0), (x+.1, -.03, LEVEL), (x-.1, -.03, LEVEL)], [(0, 1, 2, 3)], detail=True)
    columns(z0, .35, .5, SHEET, FRAME)
    if kind == 'windows':
        strip_window('strip window', 2.5, 21.5, 9.6, 13.2, rng, 4)
    elif kind == 'vent':
        vent('wall louvre', 6.5, 17.5, 4.2 if base else 4.0, 9.2 if base else 9.0)
    elif kind == 'door':
        h.door('side', 12, 0, z0, c.SOUTH, lit=True)
        cuboid('door step', 9, 15, -2.2, 0, 0, z0, CAST, KERB, omit='bk')
        cuboid('door canopy', 8.6, 15.4, -2.2, 0, z0+8.6, z0+9.0, MATTE, FRAME, omit='k')
    elif kind == 'sign':
        add('bay marking', HAZARD, (1, 1, 1), [(3, -.05, z0+.6), (21, -.05, z0+.6), (21, -.05, z0+2.2), (3, -.05, z0+2.2)], [(0, 1, 2, 3)], detail=True)
        work_light(12, 13.2)
    k.back_wall(W, 0, LEVEL, colour=k.DARK_BACK)


def medium_fascia(rng, kind):
    """A steel fascia round the roof, a coping on it."""
    cuboid('fascia', 0, W, -.45, 1.3, -1.4, 2.4, SHEET, FRAME, omit='blr')
    cuboid('fascia coping', 0, W, -.6, 1.45, 2.4, 2.7, MATTE, (.62, .64, .65), omit='blr')
    if kind == 'lights':
        for x in (6, 18):
            work_light(x, -.6, -.5)


def medium_hvac(rng):
    c.plant_box('air handler', -8, 8, -4.5, 4.5, 0, 5, 2)


def medium_skylights(rng):
    for y in (-5, 5):
        cuboid('skylight kerb', -9, 9, y-2.2, y+2.2, 0, .8, MATTE, FRAME, omit='b')
        add('skylight', GLASS, (1, 1, 1), [(-8.6, y-1.8, .82), (8.6, y-1.8, .82), (8.6, y+1.8, .82), (-8.6, y+1.8, .82)], [(0, 1, 2, 3)], light='dim')


def medium_stack(rng):
    cuboid('exhaust plinth', -3, 3, -3, 3, 0, 1, CAST, KERB, omit='b')
    round_prism('exhaust stack', 0, 0, 1, 8, 1.2, MATTE, (.56, .58, .59), 10)
    round_prism('exhaust cowl', 0, 0, 8, 8.7, 1.7, MATTE, FRAME, 10, detail=True)


# -- Heavy: precast concrete between buttresses -------------------------------------------------------

def heavy_bay(rng, kind, base):
    tone = PRECAST
    facade('wall precast', [], 0, LEVEL, colour=tone, du=8, dv=9, key=PANELS)
    # Buttresses: half at each end of a bay, battered on the ground storey.
    for x0, x1, omit in ((0, 1.5, 'l'), (W-1.5, W, 'r')):
        if base:
            verts = [(x0, 0, 0), (x1, 0, 0), (x1, -2.6, 0), (x0, -2.6, 0), (x0, 0, LEVEL), (x1, 0, LEVEL), (x1, -1.5, LEVEL), (x0, -1.5, LEVEL)]
            faces = [(3, 2, 6, 7), (4, 7, 6, 5)]+([(1, 5, 6, 2)] if omit == 'l' else [(0, 3, 7, 4)])
            add('wall buttress', PANELS, (.84, .83, .79), verts, faces)
        else:
            cuboid('wall buttress', x0, x1, -1.5, 0, 0, LEVEL, PANELS, (.84, .83, .79), omit='bk'+omit)
    if base:
        c.extrude('plinth', [(0, 0), (1.3, 0), (0, 2.6)], front, 1.5, W-1.5, PANELS, (.80, .79, .75))
    c.cast_band('ring beam', front, 1.5, W-1.5, .7, 14.6, 16.6, (.86, .85, .81))
    if kind == 'slits':
        for x in (6.5, 12, 17.5):
            c.slot_windows('slit', front, x, 5.2, 12.4, width=1.8, height=2.8, gap=1.6)
    elif kind == 'louvre':
        c.louvre('wall louvre', front, 5.5, 18.5, 4.6 if base else 3.4, 11.6 if base else 11.2)
    elif kind == 'door':
        cuboid('porch', 7.6, 16.4, -2.4, 0, 0, 10.4, PANELS, (.84, .83, .79), omit='bk')
        h.door('side', 12, -2.4, 0, c.SOUTH, lit=True)
    elif kind == 'lamp':
        work_light(12, 12.6)
    k.back_wall(W, 0, LEVEL)


def heavy_parapet(rng, kind):
    height = 5.2 if kind == 'tall' else 3.6
    cuboid('parapet', 0, W, 0, 1.8, 0, height, PANELS, (.84, .83, .79), omit='bflr')
    c.face('parapet face', front, 0, W, -.4, height, 8, height+.4, PRECAST, top=height)
    cuboid('parapet coping', 0, W, -.3, 2.1, height, height+.35, CAST, c.COPING, omit='blr')
    for x0, x1, omit in ((0, 1.5, 'l'), (W-1.5, W, 'r')):
        cuboid('buttress cap', x0, x1, -1.5, 0, -.4, .5, PANELS, (.80, .79, .75), omit='k'+omit)


def heavy_plant(rng):
    c.plant_box('plant', -9, 9, -5, 5, 0, 6, 2, rows=2)


def heavy_vents(rng):
    for x in (-6, 6):
        cuboid('vent shaft', x-2.5, x+2.5, -2.5, 2.5, 0, 4.6, PANELS, (.80, .79, .75), omit='b')
        for wall, a0, a1 in (((x, -2.5, c.SOUTH), -2, 2), ((x, 2.5, c.NORTH), -2, 2)):
            c.quad('vent shaft louvre', wall, a0, a1, 1, 3.8, .05, SLATS, h.LOUVRE)


def heavy_tank(rng):
    for x in (-5, 5):
        cuboid('tank cradle', x-.5, x+.5, -3, 3, 0, 1.6, CAST, KERB, omit='b')
    v = [(x, 3.2*math.cos(a), 4.6+3.2*math.sin(a)) for x in (-8, 8) for a in (math.tau*i/10 for i in range(10))]
    f = [(i, (i+1) % 10, 10+(i+1) % 10, 10+i)[::-1] for i in range(10)]+[tuple(range(9, -1, -1)), tuple(range(10, 20))]
    add('tank', PAINT, (.60, .62, .60), v, f)


# -- Hardened: a bunker -------------------------------------------------------------------------------
BATTER = 3.2  # How far the ground storey's foot stands out.


def hard_bay(rng, kind, base):
    if base:
        # The battered wall: its face leans back from its foot to the storey's top.
        c.extrude('wall batter', [(0, 0), (BATTER, 0), (0, LEVEL)], front, 0, W, BUNKER, RAW)
        slope = lambda z, off=.06: -(BATTER*(1-z/LEVEL)+off)
        for z in (6, 12):  # Formwork lifts.
            add('lift line', PAINT, DARK, [(0, slope(z-.12), z-.12), (W, slope(z-.12), z-.12), (W, slope(z+.12), z+.12), (0, slope(z+.12), z+.12)],
                [(0, 1, 2, 3)], detail=True)
        if kind == 'rib':
            c.extrude('wall rib', [(0, 0), (BATTER+1.8, 0), (1.2, LEVEL), (0, LEVEL)], front, 10, 14, BUNKER, (.90, .88, .84))
        elif kind == 'door':
            cuboid('porch', 7.2, 16.8, -BATTER-1.2, 0, 0, 10.6, BUNKER, (.90, .88, .84), omit='bk')
            add('blast door', ARMOUR, (1, 1, 1), [(9.6, -BATTER-1.25, .2), (14.4, -BATTER-1.25, .2), (14.4, -BATTER-1.25, 8.6), (9.6, -BATTER-1.25, 8.6)], [(0, 1, 2, 3)])
            add('door stripe', HAZARD, (1, 1, 1), [(7.4, -BATTER-1.25, 8.9), (16.6, -BATTER-1.25, 8.9), (16.6, -BATTER-1.25, 10.2), (7.4, -BATTER-1.25, 10.2)],
                [(0, 1, 2, 3)], detail=True)
            work_light(12, 11.4, -BATTER-1.2)
        elif kind == 'hazard':
            add('foot stripe', HAZARD, (1, 1, 1), [(2, slope(.8, .08), .8), (22, slope(.8, .08), .8), (22, slope(2.6, .08), 2.6), (2, slope(2.6, .08), 2.6)],
                [(0, 1, 2, 3)], detail=True)
    else:
        facade('wall concrete', [(7, 17, 7.4, 10.2)] if kind == 'slit' else [], 0, LEVEL, colour=RAW, du=8, dv=6, key=BUNKER)
        for z in (6, 12):
            add('lift line', PAINT, DARK, [(0, -.03, z-.1), (W, -.03, z-.1), (W, -.03, z+.1), (0, -.03, z+.1)], [(0, 1, 2, 3)], detail=True)
        if kind == 'slit':
            recess('embrasure', 7, 17, 7.4, 10.2, 1.6, (.90, .88, .84), BUNKER)
            add('embrasure shutter', ARMOUR, (1, 1, 1), [(7, 1.5, 7.4), (17, 1.5, 7.4), (17, 1.5, 10.2), (7, 1.5, 10.2)], [(0, 1, 2, 3)])
            c.extrude('embrasure hood', [(0, 10.2), (1.3, 10.2), (0, 11.4)], front, 6.4, 17.6, BUNKER, (.90, .88, .84))
        elif kind == 'rib':
            for x in (6, 18):
                cuboid('wall rib', x-.8, x+.8, -.9, 0, 0, LEVEL, BUNKER, (.90, .88, .84), omit='bk')
        elif kind == 'vent':
            cuboid('vent cowl', 8.5, 15.5, -1.6, 0, 9.4, 13.6, ARMOUR, (1, 1, 1), omit='bk')
            add('vent cowl slats', SLATS, h.LOUVRE, [(9, -1.0, 9.38), (15, -1.0, 9.38), (15, -.2, 9.38), (9, -.2, 9.38)], [(3, 2, 1, 0)], detail=True)
    k.back_wall(W, 0, LEVEL, depth=4.0)


def hard_slab(rng, kind):
    """The burster slab's edge: it oversails the wall, chamfered under."""
    c.extrude('roof slab edge', [(0, -2.8), (1.8, -1.4), (1.8, .9), (0, .9)], front, 0, W, BUNKER, (.84, .82, .78))
    cuboid('roof slab upstand', 0, W, 0, 2.2, 0, .9, BUNKER, (.84, .82, .78), omit='bflr')
    if kind == 'lamps':
        for x in (6, 18):
            work_light(x, -2.0, -1.85)


def hard_cupola(rng):
    sides = 8
    low = [(4.6*math.cos(a), 4.6*math.sin(a), 0) for a in (math.tau*i/sides for i in range(sides))]
    high = [(3.2*math.cos(a), 3.2*math.sin(a), 3.4) for a in (math.tau*i/sides for i in range(sides))]
    add('cupola', ARMOUR, (1, 1, 1), low+high, [(i, (i+1) % sides, sides+(i+1) % sides, sides+i) for i in range(sides)]+[tuple(range(sides, 2*sides))])
    add('cupola slit', PAINT, (.05, .05, .05), [(-1.6, -3.95, 1.5), (1.6, -3.95, 1.5), (1.6, -3.65, 2.2), (-1.6, -3.65, 2.2)], [(0, 1, 2, 3)], detail=True)


def hard_vent(rng):
    cuboid('vent block', -4, 4, -3, 3, 0, 3.2, BUNKER, (.84, .82, .78), omit='b')
    cuboid('vent cap', -4.6, 4.6, -3.6, 3.6, 3.2, 3.9, BUNKER, (.90, .88, .84), omit='')
    for wall, a0, a1 in (((0, -3, c.SOUTH), -3.2, 3.2), ((0, 3, c.NORTH), -3.2, 3.2)):
        c.quad('vent block louvre', wall, a0, a1, .8, 2.6, .05, SLATS, h.LOUVRE)


def hard_hatch(rng):
    cuboid('hatch kerb', -3, 3, -3, 3, 0, 1.2, BUNKER, (.84, .82, .78), omit='b')
    deck('hatch lid', -2.6, 2.6, -2.6, 2.6, 1.22, ARMOUR, (1, 1, 1))


# -- The designers' halls ---------------------------------------------------------------------------------
ART = Path(__file__).resolve().parent/'art'
# A hall's finishes: its frames' width at each end of a bay and how high they stand on its roof, (material, pigment) of
# its walls and frames, its roof (material, repeat, pigment, shape, rise: half a level, 9, at the most, since a unit on
# the roof plays at its eaves' level) and its walls' repeat along them.
HALLS = {
    'light': {'rib': 1.5, 'crown': .4, 'wall': (CORRUGATED, SAGE), 'frame': (MATTE, FRAME), 'roof': (TIN_ROOF, 12.0, (.80, .82, .82), 'gable', 6.0),
              'repeat': 12.0},
    'medium': {'rib': 2.0, 'crown': .5, 'wall': (SHEET, PALE), 'frame': (SHEET, (.30, .34, .38)), 'roof': (TIN_ROOF, 12.0, (.52, .54, .55), 'bow', 8.0),
               'repeat': 12.0},
    'heavy': {'rib': 2.5, 'crown': .7, 'wall': (PANELS, PRECAST), 'frame': (PANELS, (.80, .79, .75)), 'roof': (TIN_ROOF, 12.0, (.40, .42, .44), 'bow', 9.0),
              'repeat': 18.0},
    'hard': {'rib': 2.5, 'crown': .9, 'wall': (BUNKER, RAW), 'frame': (BUNKER, (.88, .86, .82)), 'roof': (BUNKER, 18.0, (.90, .88, .84), 'arch', 9.0),
             'repeat': 18.0},
}


def proposal(weight, cache={}):
    """The designers' pieces for a hangar (art/hangar_<weight>_a-proposal.glb): each node's triangles in a piece's frame
    (x along the wall, the facade towards -y, z up), as (corners, normal). Their bays are alike within a storey."""
    if weight not in cache:
        data = (ART/f'hangar_{weight}_a-proposal.glb').read_bytes()
        size = struct.unpack_from('<I', data, 12)[0]
        gltf = json.loads(data[20:20+size])
        binary = data[28+size:]

        def read(index):
            a = gltf['accessors'][index]
            view = gltf['bufferViews'][a['bufferView']]
            fmt, width = {5126: ('f', 4), 5123: ('H', 2), 5125: ('I', 4)}[a['componentType']]
            n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
            at, stride = view.get('byteOffset', 0)+a.get('byteOffset', 0), view.get('byteStride', width*n)
            return [struct.unpack_from('<'+fmt*n, binary, at+i*stride) for i in range(a['count'])]

        frame = lambda v: (v[0], -v[2], v[1])  # glTF's y up to a piece's z up.
        nodes = {}
        for node in gltf['nodes']:
            if 'mesh' in node:
                triangles = []
                for primitive in gltf['meshes'][node['mesh']]['primitives']:
                    corners = [frame(v) for v in read(primitive['attributes']['POSITION'])]
                    normals = [frame(v) for v in read(primitive['attributes']['NORMAL'])]
                    indices = [i[0] for i in read(primitive['indices'])]
                    triangles += [([corners[i] for i in indices[t:t+3]], normals[indices[t]]) for t in range(0, len(indices), 3)]
                nodes[node['name']] = triangles
        cache[weight] = nodes
    return cache[weight]


def hall_body(weight, node):
    """A proposal wall piece in its hall's finishes: its frames (the ends of a bay) and its sheeting between them; without
    its underside and top, which lie on other pieces."""
    look = HALLS[weight]
    for corners, n in proposal(weight)[node]:
        xs = [corner[0] for corner in corners]
        if abs(n[2]) > .9:
            continue
        if n[1] > .9:
            part = ('back', PAINT, k.DARK_BACK)
        elif max(xs) <= look['rib']+1e-3 or min(xs) >= W-look['rib']-1e-3:
            part = ('frame', *look['frame'])
        else:
            part = ('wall sheeting', *look['wall'])
        add(*part, corners, [(0, 1, 2)])


def band_window(name, x0, x1, z0, z1, rng, panes, lit=.25):
    """A strip of dim glass in a frame standing on the wall: a wall without a recess for one."""
    cuboid(name+' frame', x0-.4, x1+.4, -.2, 0, z0-.4, z1+.4, PAINT, DARK, omit='bk')
    for i in range(panes):
        a, b = x0+(x1-x0)*i/panes, x0+(x1-x0)*(i+1)/panes
        glass(name, a+.12, b-.12, z0, z1, -.22, rng.random() < lit)


def hall_bay(rng, weight, kind, base):
    """A hall's wall bay: the proposal's, with what its weight adds between its frames."""
    hall_body(weight, ('base0' if base else 'floor0')+'-bay0-lod0')
    rib = HALLS[weight]['rib']
    a, b = rib, W-rib
    foot = 0.0
    if base and weight != 'hard':
        foot = 1.3
        cuboid('kerb', a, b, -.35, 0, 0, foot, CAST, KERB, omit='bklr')
    if weight == 'light':
        cuboid('girt', a, b, -.22, 0, 8.7, 9.3, MATTE, FRAME, omit='bklr', detail=True)
    elif weight == 'medium':
        if not base:
            add('wall band', SHEET, BAND, [(a, -.04, 13.9), (b, -.04, 13.9), (b, -.04, 16.3), (a, -.04, 16.3)], [(0, 1, 2, 3)])
        for x in (8.67, 15.33):
            add('panel joint', PAINT, DARK, [(x-.1, -.03, foot), (x+.1, -.03, foot), (x+.1, -.03, LEVEL), (x-.1, -.03, LEVEL)], [(0, 1, 2, 3)], detail=True)
    elif weight == 'heavy':
        add('panel joint', PAINT, (.42, .42, .40), [(a, -.03, 8.9), (b, -.03, 8.9), (b, -.03, 9.1), (a, -.03, 9.1)], [(0, 1, 2, 3)], detail=True)
    else:
        for z in (6, 12):  # Formwork lifts.
            add('lift line', PAINT, DARK, [(a+1.5, -.03, z-.1), (b-1.5, -.03, z-.1), (b-1.5, -.03, z+.1), (a+1.5, -.03, z+.1)], [(0, 1, 2, 3)], detail=True)
    if kind == 'vent':
        vent('wall louvre', 8, 16, 3.4 if base else 9.6, 7.6 if base else 13.8)
    elif kind == 'windows':
        band_window('strip window', 5.5, 18.5, 10.4, 13.4, rng, 3)
    elif kind == 'door':
        h.door('side', 12, 0, foot, c.SOUTH, lit=True)
        if foot:
            cuboid('door step', 9, 15, -1.6, 0, 0, foot, CAST, KERB, omit='bk')
    elif kind == 'slit':
        add('embrasure', PAINT, (.05, .05, .05), [(7.5, -.03, 8.0), (16.5, -.03, 8.0), (16.5, -.03, 9.8), (7.5, -.03, 9.8)], [(0, 1, 2, 3)])
        c.extrude('embrasure hood', [(0, 9.8), (1.1, 9.8), (0, 10.8)], front, 7, 17, *HALLS[weight]['frame'])
    elif kind == 'lamp':
        work_light(12, 13.0)
    elif kind == 'hazard':
        add('foot stripe', HAZARD, (1, 1, 1), [(a+2, -.04, .6), (b-2, -.04, .6), (b-2, -.04, 2.2), (a+2, -.04, 2.2)], [(0, 1, 2, 3)], detail=True)


def hall_eave(rng, weight):
    """A hall's eave: a gutter along the wall's top under the roof's edge, in its frames' finish; across a gable end, the
    tie under the gable."""
    key, colour = HALLS[weight]['frame']
    out = .6 if weight in ('light', 'medium') else 1.0
    cuboid('gutter', 0, W, -out, 0, -1.0, .2, key, colour, omit='klr')


def hall_pieces(weight, kinds):
    """Pieces hall-<kind> and hall-base-<kind>, and the hall's eave."""
    result = {'hall-eave': lambda rng: hall_eave(rng, weight)}
    for kind in kinds:
        result['hall-'+kind] = lambda rng, kind=kind: hall_bay(rng, weight, kind, False)
        result['hall-base-'+kind] = lambda rng, kind=kind: hall_bay(rng, weight, kind, True)
    return result


# -- Kits -----------------------------------------------------------------------------------------------

def bays(builder, kinds):
    """Pieces <kind> and base-<kind>, each built by builder(rng, kind, base)."""
    result = {}
    for kind in kinds:
        result[kind] = lambda rng, kind=kind: builder(rng, kind, False)
        result['base-'+kind] = lambda rng, kind=kind: builder(rng, kind, True)
    return result


def variant(name, weight, base, upper, roofs, roof, planar, fit, large_door, prefix='', inset=3.0, vault=None):
    """A variant: its ground bays (two modules' lists, a side door among each), its upper storeys', its roof's; its roof
    slab (material, repeat) and the vault over it, if any; its floors kept `inset` off the wall line, the wall's depth."""
    run = lambda names, door=None: [{'bays': [prefix+n for n in names], 'bay': W, 'planar': planar, **({'door': prefix+door} if door else {})}]
    return {
        'name': name, 'style': 'bays', 'pieces': f'hangar_{weight}_a-pieces.glb', 'lone': k.LONE, 'bandEnd': 1.75, 'varyBays': True,
        'roof': {'material': roof[0], 'repeat': roof[1], 'inset': 0.0, 'heights': [0.3], 'aol': True, **({'vault': vault} if vault else {})},
        'floors': {'material': CAST, 'repeat': 12.0, 'inset': inset, 'heights': [0.05]},
        'modules': {
            'base0': run(['base-'+n for n in base[0]], 'base-door'),
            'base1': run(['base-'+n for n in base[1]], 'base-door'),
            'floor0': run(upper[0]),
            'floor1': run(upper[1]),
            'roof0': [{'bays': roofs, 'bay': W, 'planar': planar}],
        },
        **({'fittings': fit} if fit else {}),
        'door': large_door,
    }


def hall(weight, base, upper, large_door):
    """The designers' hall, a kit's first variant, under the roof that spans it: its sheeting, shape and rise, its gable
    ends in the walls' finish (they take the building's tint with them), its frames running on over it as ribs."""
    look = HALLS[weight]
    material, repeat, pigment, shape, rise = look['roof']
    surface = lambda key, colour, units: {'material': key, 'repeat': units, 'tint': k.lin(colour)}
    vault = {'shape': shape, 'rise': rise, 'segments': [6, 3], 'gable': surface(look['wall'][0]+'#paint', look['wall'][1], look['repeat']),
             'trim': surface(*look['frame'], 12.0), 'verge': .9, 'ribPitch': W, 'ribWidth': look['rib'], 'ribHeight': look['crown'],
             'tint': k.lin(pigment)}
    return variant('default', weight, base, upper, ['hall-eave'], (material, repeat), {look['wall'][0]: look['repeat']}, None, large_door,
                   prefix='hall-', inset=1.3, vault=vault)


LIGHT = {**bays(light_bay, ('plain', 'vent', 'daylight', 'door', 'brace')),
         'eave-plain': lambda rng: light_eave(rng, 'plain'), 'eave-pipe': lambda rng: light_eave(rng, 'pipe'),
         'ridge-vent': light_ridge_vent, 'skylight': light_skylight, 'fan': light_fan}
MEDIUM = {**bays(medium_bay, ('plain', 'windows', 'vent', 'door', 'sign')),
          'fascia-plain': lambda rng: medium_fascia(rng, 'plain'), 'fascia-lights': lambda rng: medium_fascia(rng, 'lights'),
          'hvac': medium_hvac, 'skylights': medium_skylights, 'stack': medium_stack}
HEAVY = {**bays(heavy_bay, ('plain', 'slits', 'louvre', 'door', 'lamp')),
         'parapet-plain': lambda rng: heavy_parapet(rng, 'plain'), 'parapet-tall': lambda rng: heavy_parapet(rng, 'tall'),
         'plant': heavy_plant, 'vents': heavy_vents, 'tank': heavy_tank}
HARD = {**bays(hard_bay, ('plain', 'rib', 'slit', 'vent', 'door', 'hazard')),
        'slab-plain': lambda rng: hard_slab(rng, 'plain'), 'slab-lamps': lambda rng: hard_slab(rng, 'lamps'),
        'cupola': hard_cupola, 'vent-block': hard_vent, 'hatch': hard_hatch}
STRIPE = (HAZARD, (1, 1, 1), 4.0)
SILL = (CAST, KERB)

KITS = {
    'light': ({**hall_pieces('light', ('plain', 'vent', 'windows', 'door')), **LIGHT}, [
        hall('light', (['plain', 'vent', 'plain', 'plain'], ['plain', 'plain', 'vent']), (['windows', 'plain', 'windows'], ['plain', 'windows', 'vent', 'plain']),
             k.door((DOOR, (.80, .84, .82), 12.0, True), (MATTE, FRAME), jamb=1.5, header=2.0, out=.5, depth=3.2, recess=.5, lintel=.8,
                    panel=3.0, section=12.0, stripe=STRIPE, stripeHeight=1.4, windows=k.door_windows(3.2, 1.3, 7.3, 6.0), threshold=SILL, apron=3.0)),
        variant('alternative', 'light', (['plain', 'vent', 'plain', 'brace'], ['brace', 'plain', 'vent', 'plain']),
                (['daylight', 'plain', 'daylight', 'vent'], ['plain', 'daylight', 'brace', 'daylight']), ['eave-plain', 'eave-pipe', 'eave-plain'],
                (TIN_ROOF, 12.0), {CORRUGATED: 12.0},
                k.fittings('fan', 'ridge-vent', [{'ridge-vent': [[0, 0, 0]]}, {'skylight': [[0, -6, 0], [0, 6, 0]]}, {'fan': [[-8, 6, 0]], 'skylight': [[3, -5, 0]]},
                                                {'ridge-vent': [[0, 8, 0]], 'fan': [[7, -8, 0]]}, {}]),
                k.door((DOOR, (.80, .84, .82), 12.0, True), (SHEET, FRAME), jamb=1.5, header=2.0, out=.7, depth=3.2, recess=.5, lintel=1.2,
                       panel=3.0, section=12.0, stripe=STRIPE, stripeHeight=1.4, windows=k.door_windows(3.2, 1.3, 7.3, 6.0), threshold=SILL, apron=3.0)),
    ]),
    'medium': ({**hall_pieces('medium', ('plain', 'vent', 'windows', 'door')), **MEDIUM}, [
        hall('medium', (['plain', 'vent', 'plain', 'plain'], ['plain', 'plain', 'vent']), (['windows', 'plain', 'windows'], ['plain', 'windows', 'vent', 'windows']),
             k.door((DOOR, (.86, .87, .86), 12.0, True), (SHEET, (.30, .34, .38)), jamb=2.0, header=2.6, out=1.0, depth=3.2, recess=.7, lintel=.8,
                    panel=3.0, section=18.0, stripe=STRIPE, stripeHeight=1.6, windows=k.door_windows(4.0, 1.5, 7.2, 6.0), threshold=SILL, apron=3.5)),
        variant('alternative', 'medium', (['plain', 'vent', 'sign', 'plain'], ['sign', 'plain', 'plain', 'vent']),
                (['windows', 'plain', 'windows', 'vent'], ['plain', 'windows', 'windows', 'plain']), ['fascia-plain', 'fascia-lights', 'fascia-plain'],
                ('structures/buildings/light-roof', 18.0), {SHEET: 12.0},
                k.fittings('stack', 'hvac', [{'hvac': [[0, 0, 0]]}, {'skylights': [[0, 0, 0]]}, {'stack': [[-8, 7, 0]], 'skylights': [[3, -2, 90]]},
                                             {'hvac': [[-4, 5, 90]], 'stack': [[9, -8, 0]]}, {}]),
                k.door((DOOR, (.86, .87, .86), 12.0, True), (SHEET, (.24, .26, .28)), jamb=1.8, header=2.6, out=.6, depth=3.2, recess=.7, lintel=1.8,
                       panel=3.0, section=18.0, stripe=STRIPE, stripeHeight=1.6, windows=k.door_windows(4.0, 1.5, 7.2, 6.0), threshold=SILL, apron=3.5)),
    ]),
    'heavy': ({**hall_pieces('heavy', ('plain', 'vent', 'windows', 'door', 'lamp')), **HEAVY}, [
        hall('heavy', (['plain', 'vent', 'lamp', 'plain'], ['lamp', 'plain', 'vent']), (['windows', 'plain', 'plain'], ['plain', 'windows', 'vent', 'plain']),
             k.door((MATTE, (.50, .53, .55)), (PANELS, (.80, .79, .75)), jamb=2.5, header=3.4, out=1.5, depth=3.4, recess=1.0, lintel=.8,
                    panel=0.0, section=9.0, seam=(MATTE, (.26, .27, .28)), stripe=(HAZARD, (1, 1, 1), 5.0), stripeHeight=2.0, threshold=SILL, apron=4.0)),
        variant('alternative', 'heavy', (['plain', 'louvre', 'lamp', 'plain'], ['lamp', 'plain', 'plain', 'louvre']),
                (['slits', 'plain', 'slits', 'louvre'], ['plain', 'slits', 'plain', 'slits']), ['parapet-plain', 'parapet-plain', 'parapet-tall'],
                (DARK_ROOF, 24.0), {PANELS: 18.0},
                k.fittings('vents', 'plant', [{'plant': [[0, 0, 0]]}, {'vents': [[0, 0, 0]]}, {'tank': [[0, 5, 0]], 'vents': [[0, -8, 0]]},
                                              {'plant': [[-3, 4, 90]]}, {}]),
                k.door((MATTE, (.50, .53, .55)), (PANELS, (.80, .79, .75)), jamb=2.6, header=3.4, out=1.5, depth=3.4, recess=1.0, lintel=1.4,
                       panel=0.0, section=9.0, seam=(MATTE, (.26, .27, .28)), stripe=(HAZARD, (1, 1, 1), 5.0), stripeHeight=2.0, threshold=SILL, apron=4.0)),
    ]),
    'hard': ({**hall_pieces('hard', ('plain', 'slit', 'vent', 'door', 'hazard')), **HARD}, [
        hall('hard', (['plain', 'hazard', 'plain'], ['hazard', 'plain', 'plain']), (['slit', 'plain', 'vent'], ['plain', 'slit', 'plain']),
             k.door((ARMOUR, (1, 1, 1), 18.0), (BUNKER, (.88, .86, .82), 18.0), jamb=2.5, header=4.0, out=3.5, depth=4.0, recess=1.2, lintel=.8,
                    panel=6.0, section=10.0, seam=(YELLOW, (.75, .70, .55), 6.0), stripe=(HAZARD, (1, 1, 1), 6.0), stripeHeight=2.4,
                    threshold=SILL, apron=5.0)),
        variant('alternative', 'hard', (['plain', 'rib', 'hazard', 'plain'], ['hazard', 'plain', 'rib', 'plain']),
                (['slit', 'plain', 'rib', 'vent'], ['plain', 'slit', 'plain', 'rib']), ['slab-plain', 'slab-lamps', 'slab-plain'],
                (DARK_ROOF, 24.0), {BUNKER: 18.0},
                k.fittings('hatch', 'vent-block', [{'cupola': [[0, 0, 0]]}, {'vent-block': [[0, 0, 0]]}, {'hatch': [[-7, 6, 0]], 'vent-block': [[6, -6, 90]]},
                                                   {'cupola': [[-6, -5, 0]], 'hatch': [[8, 8, 0]]}, {}]),
                k.door((ARMOUR, (1, 1, 1), 18.0), (BUNKER, (.90, .88, .84), 18.0), jamb=3.4, header=4.2, out=BATTER+1.2, depth=4.2, recess=1.4, lintel=1.0,
                       panel=6.0, section=10.0, seam=(YELLOW, (.75, .70, .55), 6.0), stripe=(HAZARD, (1, 1, 1), 6.0), stripeHeight=2.4,
                       threshold=SILL, apron=BATTER+1.5)),
    ]),
}


def build(weight):
    pieces, variants = KITS[weight]
    name = f'hangar_{weight}_a'
    k.KITS[name] = (pieces, variants)
    # Walls take a building's tint; frames, concrete trims, roofs and equipment keep theirs.
    k.build(name, folder=f'hangar_{weight}', painted=lambda obj: obj.name.startswith('wall'))


if __name__ == '__main__' and '--' in sys.argv:
    for weight in sys.argv[sys.argv.index('--')+1:] or list(KITS):
        build(weight)
