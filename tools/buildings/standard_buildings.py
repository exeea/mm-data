"""The standard buildings as connected building kits: their pieces GLBs and kit JSONs.

Run: blender -b --factory-startup --python standard_buildings.py -- [medium|heavy|hard ...]
Writes data/models/buildings/standard/building-<weight>-pieces.glb and building-<weight>.json, for the game's bays kit
(GeneratedKit, BayKit), as theme_kits writes the looks' (its piece frame, levels of detail and export).

A building is a habitat: people live and work in it, so every weight shows rooms' windows and doors (a fortress is the
fortress class's kit). Medium, heavy and hardened are the designers' buildings (art/building_<weight>-proposal.glb:
untextured wall bays, six or seven a storey), dressed here in the board's materials: each of their faces is sorted by
where it lies (a wall panel, a slab's edge, a window's glass, a door, a canopy, a step) and takes that part's finish,
and the script adds what a massing model leaves out (panes and mullions, door leaves, a hall's glass).
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import civic_blocks as c
import civic_habitat as h
import hangar_kits as hk
import theme_kits as k
from civic_citadel import GLAZING
from civic_habitat import CAST, PAINT, PANELS, STEEL, add, cuboid
from theme_kits import LEVEL, W

MATTE = hk.MATTE
BUNKER = hk.BUNKER
WHITE = 'structures/common/white-stone'
SIDEWALK = 'structures/buildings/light-sidewalk'
DARK = (.20, .21, .22)
KERB = (.70, .70, .67)
BACK = (.62, .62, .58)
LEAF = (.38, .43, .43)
LOBBY = (.72, .66, .50)  # A lit hall behind a doorway's glass.
SKY = (.70, .80, .95)  # A pane that shows the sky.


# -- The designers' buildings -----------------------------------------------------------------------------

def faces(weight, node, cache={}):
    """A proposal piece's triangles, its wall starting at x 0: (corners, normal, patch). A triangle that faces straight out
    of the wall is part of a flat patch, the triangles joined to it at its depth: (y, x0, x1, z0, z1, whole), its depth,
    its extent and whether it fills that rectangle."""
    if (weight, node) not in cache:
        triangles = hk.proposal(f'building_{weight}-proposal')[node]
        shift = round(min(corner[0] for corners, _ in triangles for corner in corners))
        triangles = [([(x-shift, y, z) for x, y, z in corners], n) for corners, n in triangles]
        parent = {}

        def find(key):
            while parent.setdefault(key, key) != key:
                parent[key] = parent[parent[key]]
                key = parent[key]
            return key

        keys = {}
        for index, (corners, n) in enumerate(triangles):
            if n[1] < -.99:
                keys[index] = [tuple(round(v, 2) for v in corner) for corner in corners]
                for key in keys[index][1:]:
                    parent[find(key)] = find(keys[index][0])
        points, areas = {}, {}
        for index, (a, b, c) in keys.items():
            root = find(a)
            points.setdefault(root, []).extend((a, b, c))
            areas[root] = areas.get(root, 0)+abs((b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2]))/2
        patches = {}
        for root, found in points.items():
            x0, x1, z0, z1 = min(p[0] for p in found), max(p[0] for p in found), min(p[2] for p in found), max(p[2] for p in found)
            patches[root] = (found[0][1], x0, x1, z0, z1, areas[root] > .98*(x1-x0)*(z1-z0))
        cache[weight, node] = [(corners, n, patches[find(keys[index][0])] if index in keys else None)
                               for index, (corners, n) in enumerate(triangles)]
    return cache[weight, node]


def hidden(corners, n, top, over):
    """Faces that lie on the pieces beside, under and over a storey's piece: its ends, its underside, and its top (`top`
    high) where the storey above, standing `over` out of the wall line, covers it. A cornice's top shows."""
    xs, ys, zs = [c[0] for c in corners], [c[1] for c in corners], [c[2] for c in corners]
    return ((abs(n[0]) > .99 and (max(xs) < .01 or min(xs) > W-.01)) or (n[2] < -.99 and max(zs) < .01)
            or (n[2] > .99 and min(zs) > top-.01 and min(ys) > -over-.01))


def ground(corners, n, patch, behind):
    """The plinth a ground storey stands on and a doorway's steps (their risers and treads lie `behind` this depth)."""
    ys, zs = [c[1] for c in corners], [c[2] for c in corners]
    return (max(zs) <= .31 or (n[2] > .99 and max(zs) < 3.5 and min(ys) > behind)
            or bool(patch and patch[4] < 3.5 and patch[4]-patch[3] < .7 and patch[0] > behind))


def medium_part(module, corners, n, patch):
    """Precast panels between slab edges: a panel's face stands 1 out of the wall line and its slab edges 2; grooves frame
    it. Sunk in it: slot windows and long windows at the wall line, loggias 3.5 behind; on the ground shop windows with
    cut corners, doors, doorways up steps, canopies."""
    ys = [c[1] for c in corners]
    if n[1] > .99:
        return 'back'
    if ground(corners, n, patch, -.1):
        return 'kerb'
    if min(ys) < -2.5:
        return 'canopy'
    if patch and patch[0] > -.5:
        y, x0, x1, z0, z1, whole = patch
        if (x1-x0)*(z1-z0) < 4 or module == 'roof':
            return 'groove'  # The triangles in a frame's corners; the parapet's sunk face.
        if y > 3:
            return 'doorway' if module == 'base' else 'glass'
        return 'door' if module == 'base' and z0 < 1 else 'glass'
    if max(ys) > -.95:
        return 'groove'  # Whatever turns in behind a panel's face.
    return 'slab' if min(ys) < -1.5 else 'wall'


def heavy_part(module, corners, n, patch):
    """Concrete piers (the bay's ends 1.7 out of the wall line, two between them 1.3) with walls half a unit out between
    them; up each wall a channel of tall windows over spandrels. On the ground a plinth course and a band, a porch of
    columns up steps, tall doors, a round canopy; a cornice 4 out under the storey above."""
    ys, zs = [c[1] for c in corners], [c[2] for c in corners]
    if n[1] > .99:
        return 'back'
    if ground(corners, n, patch, .1):
        return 'kerb'
    if min(ys) < -2.5:
        return 'canopy' if max(zs) < 14 and module != 'roof' else 'slab'
    if patch:
        y, x0, x1, z0, z1, whole = patch
        if y > .3:
            return 'doorway' if module == 'base' else 'glass'  # A porch's back and a tall door are a hall's glass.
        if y > -.1:
            return 'spandrel'
        if y > -.6:
            return 'wall'
        return 'band' if y > -1.2 else 'pier'
    if max(ys) > -.45:
        return 'reveal'
    return 'pier' if min(ys) < -1.0 else 'band' if module != 'roof' else 'wall'


def hard_part(module, corners, n, patch):
    """A bunker of a building: battered buttresses at each bay's ends, slab edges and their caps, walls a unit thick
    in front of deep window strips, and balconies behind solid parapets that lean out; on the ground a loading door, a
    doorway up steps and a blank annex."""
    xs, ys, zs = [c[0] for c in corners], [c[1] for c in corners], [c[2] for c in corners]
    if n[1] > .99:
        return 'back'
    if ground(corners, n, patch, 1):
        return 'kerb'
    if patch and patch[0] > 2:
        y, x0, x1, z0, z1, whole = patch
        if module == 'base' and z0 < 1:
            return 'doorway' if y > 5 else 'loading'
        return 'glass'
    if max(xs) < 3.95 or min(xs) > 20.05:
        return 'slab' if min(ys) < -3 or (module == 'roof' and max(zs) > 2.6) else 'buttress'
    if min(ys) < -1:
        return 'slab'  # Slab edges, parapets and the annex.
    if max(ys) > .2:
        return 'reveal'
    return 'wall'


def lobby(patch):
    """A hall's glass behind a doorway: lit panes between mullions, a transom over its doors."""
    y, x0, x1, z0, z1, whole = patch
    count = max(1, round((x1-x0)/3.2))
    for i in range(count):
        a, b = x0+(x1-x0)*i/count, x0+(x1-x0)*(i+1)/count
        add('lobby glass', h.PALE_GLASS, LOBBY, [(a, y, z0), (b, y, z0), (b, y, z1), (a, y, z1)], [(0, 1, 2, 3)], light='night')
        if i:
            cuboid('lobby mullion', a-.15, a+.15, y-.2, y, z0, z1, STEEL, DARK, omit='bk', detail=True)
    if z1-z0 > 9:
        cuboid('lobby transom', x0, x1, y-.2, y, z0+7.6, z0+8.0, STEEL, DARK, omit='klr', detail=True)


def glazing(rng, lit):
    """A pane's finish (material, tint, light): most dark, some pale with the sky, some lit at night."""
    pick = rng.random()
    return (h.PALE_GLASS, SKY, 'off') if lit < pick < lit+.22 else (h.DARK_GLASS, GLAZING, 'night' if pick < lit else 'off')


def panes(patch, rng, lit, pitch=4.4):
    """A window's panes between mullions."""
    y, x0, x1, z0, z1, whole = patch
    count = max(1, round((x1-x0)/pitch))
    for i in range(count):
        a, b = x0+(x1-x0)*i/count, x0+(x1-x0)*(i+1)/count
        key, colour, light = glazing(rng, lit)
        add('window', key, colour, [(a, y, z0), (b, y, z0), (b, y, z1), (a, y, z1)], [(0, 1, 2, 3)], light=light)
        if i:
            cuboid('window mullion', a-.12, a+.12, y-.15, y, z0, z1, STEEL, DARK, omit='bk', detail=True)


LOOKS = {
    'medium': {
        'part': medium_part, 'lit': .3, 'depth': 1.25, 'over': 2.0, 'roof': ('structures/buildings/light-roof', 18.0), 'planar': {WHITE: 18.0, CAST: 12.0},
        'finish': {'wall': ('wall panel', WHITE, (.95, .94, .90)), 'groove': ('wall groove', WHITE, (.74, .74, .71)),
                   'slab': ('slab edge', CAST, (.86, .86, .83)), 'canopy': ('canopy', MATTE, DARK), 'kerb': ('kerb', CAST, KERB),
                   'back': ('back', CAST, BACK), 'door': ('door leaf', PAINT, LEAF)},
        'fittings': (hk.MEDIUM, [{'hvac': [[0, 0, 0]]}, {'skylights': [[0, 0, 0]]}, {'stack': [[-8, 7, 0]], 'skylights': [[3, -2, 90]]},
                                  {'hvac': [[-4, 5, 90]], 'stack': [[9, -8, 0]]}, {}]),
        'entrance': 'bay0',
        'base': (['bay1', 'bay5', 'bay4', 'bay2', 'bay1', 'bay3'], ['bay4', 'bay3', 'bay1', 'bay5', 'bay2', 'bay4']),
        'floor': ['bay0', 'bay1', 'bay2', 'bay3', 'bay4', 'bay5', 'bay6'],
    },
    'heavy': {
        'part': heavy_part, 'lit': .3, 'depth': 2.0, 'over': 1.7, 'roof': (hk.DARK_ROOF, 24.0), 'planar': {PANELS: 18.0, CAST: 12.0},
        'finish': {'wall': ('wall', PANELS, (.90, .89, .85)), 'pier': ('wall pier', PANELS, (.99, .97, .92)),
                   'band': ('band', CAST, (.86, .85, .81)), 'slab': ('cornice', CAST, (.90, .89, .85)),
                   'spandrel': ('spandrel', PAINT, (.26, .27, .27)), 'reveal': ('reveal', PANELS, (.72, .71, .68)),
                   'canopy': ('canopy', MATTE, DARK), 'kerb': ('kerb', CAST, KERB), 'back': ('back', CAST, BACK)},
        'fittings': (hk.HEAVY, [{'plant': [[0, 0, 0]]}, {'vents': [[0, 0, 0]]}, {'tank': [[0, 5, 0]], 'vents': [[0, -8, 0]]}, {'plant': [[-3, 4, 90]]}, {}]),
        'entrance': 'bay0',
        'base': (['bay1', 'bay5', 'bay2', 'bay4', 'bay3', 'bay2'], ['bay2', 'bay4', 'bay1', 'bay5', 'bay2', 'bay3']),
        'floor': ['bay0', 'bay1', 'bay2', 'bay3', 'bay4', 'bay5'],
    },
    'hard': {
        'part': hard_part, 'lit': .25, 'depth': 4.0, 'over': 3.26, 'roof': (hk.DARK_ROOF, 24.0), 'planar': {BUNKER: 18.0, CAST: 12.0},
        'finish': {'wall': ('wall', BUNKER, hk.RAW), 'buttress': ('wall buttress', BUNKER, (.90, .88, .84)),
                   'slab': ('slab edge', BUNKER, (.84, .82, .78)), 'reveal': ('reveal', BUNKER, (.70, .69, .66)),
                   'kerb': ('kerb', CAST, KERB), 'back': ('back', CAST, BACK)},
        'fittings': (hk.HARD, [{'vent-block': [[0, 0, 0]]}, {'hatch': [[-7, 6, 0]], 'vent-block': [[6, -6, 90]]}, {'hatch': [[8, 8, 0]]}, {}]),
        'entrance': 'bay3',
        'base': (['bay1', 'bay5', 'bay4', 'bay2', 'bay1', 'bay0'], ['bay4', 'bay0', 'bay1', 'bay5', 'bay2', 'bay4']),
        'floor': ['bay0', 'bay1', 'bay2', 'bay3', 'bay4', 'bay5'],
    },
}


def dressed(weight, node, rng):
    """A proposal piece in its weight's finishes, with what the script adds to its windows and doors."""
    look = LOOKS[weight]
    module = node.split('-')[0][:-1]
    done = {}
    for corners, n, patch in faces(weight, node):
        if hidden(corners, n, LEVEL if module != 'roof' else 1e9, look['over']):
            continue
        part = look['part'](module, corners, n, patch)
        if part not in ('glass', 'doorway', 'door', 'loading'):
            add(*look['finish'][part], corners, [(0, 1, 2)])
            continue
        y, x0, x1, z0, z1, whole = patch
        first = patch not in done
        if part == 'glass' and whole:
            if first:
                panes(patch, rng, look['lit'])
        elif part == 'glass':  # A slot or a window with cut corners: one pane, as modelled.
            if first:
                done[patch] = glazing(rng, look['lit'])
            key, colour, light = done[patch]
            add('window', key, colour, corners, [(0, 1, 2)], light=light)
        elif part == 'doorway':
            if first:
                lobby(patch)
        elif part == 'loading':
            add('loading door', k.SECTIONAL, (.62, .64, .64), corners, [(0, 1, 2)])
        else:
            add(*look['finish'][part], corners, [(0, 1, 2)])
            if first:
                cuboid('door frame', x0, x1, y-.12, y, z1-.4, z1, STEEL, DARK, omit='k', detail=True)
                middle = (x0+x1)/2
                add('door vision panel', h.PALE_GLASS, h.PALE, [(middle-.9, y-.05, z0+3.6), (middle+.9, y-.05, z0+3.6), (middle+.9, y-.05, z0+5.8),
                                                             (middle-.9, y-.05, z0+5.8)], [(0, 1, 2, 3)], light='night')
        done.setdefault(patch, True)


TWIN = '-b'  # A bay's twin: the same bay built from another seed.


def storeys(bays, count=4):
    """`count` runs of upper-storey bays and their twins, each in an order of its own: the game picks a run a storey, so
    the storeys of one wall differ, and its lit windows do not stand in columns."""
    order = random.Random(len(bays))
    pool = [*bays, *(bay+TWIN for bay in bays)]
    return [order.sample(pool, len(bays)+i % 2) for i in range(count)]


def pieces(weight):
    """A weight's pieces: base-bay<n>, floor-bay<n> and roof, the proposal's (its second base and floor modules repeat its
    first)."""
    result = {'roof': lambda rng: dressed(weight, 'roof0-bay0-lod0', rng)}
    fittings, layouts = LOOKS[weight]['fittings']
    result.update({name: fittings[name] for layout in layouts for name in layout})
    for node in sorted(hk.proposal(f'building_{weight}-proposal')):
        module, bay = node.split('-')[:2]
        if module in ('base0', 'floor0'):
            result[f'{module[:-1]}-{bay}'] = lambda rng, node=node: dressed(weight, node, rng)
        if module == 'floor0':
            result[f'floor-{bay}{TWIN}'] = lambda rng, node=node: dressed(weight, node, rng)
    return result


def designed(weight):
    """A designers' building as a kit: its pieces, its roof, its one variant."""
    look = LOOKS[weight]
    material, repeat = look['roof']
    roofs = {'flat': {'material': material, 'repeat': repeat, 'inset': 0.0, 'heights': [1.0], 'aviationLights': True,
                      'runs': [k.run(['roof'], look['planar'])]}}
    run = lambda module, bays: k.run([f'{module}-{bay}' for bay in bays], look['planar'], f"base-{look['entrance']}" if module == 'base' else None)
    variant = {
        'name': 'default', 'roof': 'flat', 'lone': k.LONE, 'bandEnd': 1.75, 'varyBays': True, 'fittings': look['fittings'][1],
        'floors': {'material': CAST, 'repeat': 12.0, 'inset': look['depth'], 'heights': [0.05]},
        'sidewalk': {'material': SIDEWALK, 'repeat': 12.0, 'width': 5.0, 'kerb': .25},
        'base': [run('base', bays) for bays in look['base']], 'floor': [run('floor', bays) for bays in storeys(look['floor'])],
    }
    return pieces(weight), roofs, [variant]


# -- Civilian: what people build for themselves, and what falls first -------------------------------------
CLAP = 'structures/common/clapboard'
PLANKS = 'structures/common/timber-planks'
SHINGLES = 'structures/common/timber-shingles'
FELT = 'structures/common/roofing-felt'
RENDER = 'structures/common/painted-render'
BRICK = 'structures/common/hollow-brick'
TIN = hk.TIN_ROOF
PAINTED = (.96, .95, .92)  # Clapboard and render are near white: a building's tint is their colour.
TRIM = (.97, .96, .93)
TIMBER = (.86, .82, .76)
OLD_TIMBER = (.56, .52, .48)
RAW = (.80, .79, .76)  # A concrete frame's columns and slab edges.
RUSTY = (.66, .64, .62)  # Tin sheet gone dull.
CLOTHES = ((.90, .90, .88), (.36, .48, .66), (.72, .26, .22), (.84, .70, .30), (.42, .58, .46))
STOREY = LEVEL/2  # A level is two storeys of rooms.
END = k.ROUND  # A wall-end piece's length: the kit stretches it to the room the bays leave.
MARGIN = 1.9  # How far the modelled kits' bays keep off a wall's ends: a Square hex's 20.8 of wall still takes a bay.


def quad(name, key, colour, a, b, c, d, both=False, **flags):
    """Four corners, counter-clockwise seen from where it faces; `both`: seen from behind too."""
    add(name, key, colour, [a, b, c, d], [(0, 1, 2, 3)]+([(3, 2, 1, 0)] if both else []), **flags)


def pane(x0, x1, z0, z1, y, rng, lit=.3, lean=0.0):
    """A pane at y, its head `lean` further in."""
    key, colour, light = glazing(rng, lit)
    quad('window', key, colour, (x0, y, z0), (x1, y, z0), (x1, y+lean, z1), (x0, y+lean, z1), light=light)


def clothesline(x0, x1, y, z, rng, count=4):
    """Washing on a line from x0 to x1."""
    cuboid('washing line', x0, x1, y-.03, y+.03, z-.03, z+.03, PAINT, DARK, omit='lr', detail=True)
    step = (x1-x0-1)/count
    for i in range(count):
        a = x0+.5+i*step+rng.uniform(0, .3)
        b, drop = a+rng.uniform(.5, .8)*step, rng.uniform(1.6, 2.8)
        quad('washing', PAINT, rng.choice(CLOTHES), (a, y, z-drop), (b, y, z-drop), (b, y, z), (a, y, z), both=True, detail=True)


# Timber: a row of clapboard houses.

def sash(x, z0, z1, rng, width=2.8):
    """A sash window in the clapboard: casing boards, a sill, its meeting rail and glazing bar."""
    x0, x1 = x-width/2, x+width/2
    k.recess('sash', x0, x1, z0, z1, .3, TRIM, RENDER)
    pane(x0, x1, z0, z1, .26, rng)
    for a, b in ((x0-.4, x0), (x1, x1+.4)):
        cuboid('casing', a, b, -.14, 0, z0, z1+.45, RENDER, TRIM, omit='bk')
    cuboid('casing', x0-.5, x1+.5, -.2, 0, z1, z1+.45, RENDER, TRIM, omit='k')
    cuboid('window sill', x0-.55, x1+.55, -.4, 0, z0-.3, z0, RENDER, TRIM, omit='k')
    middle = (z0+z1)/2
    cuboid('sash rail', x0, x1, .12, .26, middle-.12, middle+.12, RENDER, TRIM, omit='klr', detail=True)
    cuboid('sash bar', x-.06, x+.06, .16, .26, z0, z1, RENDER, TRIM, omit='bkt', detail=True)


def plank_door(x, z0, rng, width=3.2, height=7.0):
    """A boarded door in a casing, a small lit pane in it."""
    x0, x1 = x-width/2, x+width/2
    k.recess('door', x0, x1, z0, z0+height, .3, TRIM, RENDER)
    quad('door leaf', PLANKS, OLD_TIMBER, (x0, .25, z0), (x1, .25, z0), (x1, .25, z0+height), (x0, .25, z0+height))
    quad('door pane', h.PALE_GLASS, LOBBY, (x-.7, .2, z0+4.4), (x+.7, .2, z0+4.4), (x+.7, .2, z0+5.8), (x-.7, .2, z0+5.8), light='night')
    for a, b in ((x0-.4, x0), (x1, x1+.4)):
        cuboid('casing', a, b, -.14, 0, z0, z0+height+.45, RENDER, TRIM, omit='bk')
    cuboid('casing', x0-.5, x1+.5, -.2, 0, z0+height, z0+height+.45, RENDER, TRIM, omit='k')


def timber_rail(x0, x1, y, z, height=2.8):
    """A porch's or a balcony's rail along x: posts, a top rail and balusters."""
    cuboid('rail top', x0, x1, y-.15, y+.15, z+height-.25, z+height, RENDER, TRIM, omit='b')
    cuboid('rail foot', x0, x1, y-.1, y+.1, z+.3, z+.5, RENDER, TRIM, omit='b', detail=True)
    count = max(2, round((x1-x0)/.9))
    for i in range(1, count):
        x = x0+(x1-x0)*i/count
        cuboid('baluster', x-.08, x+.08, y-.08, y+.08, z+.5, z+height-.25, RENDER, TRIM, omit='bt', detail=True)


def porch(z, rng):
    """A porch across the bay's middle: a boarded deck up three steps, posts, a rail and a shingled lean-to roof."""
    x0, x1, out, roof = 3.0, 21.0, 4.4, z+8.2
    cuboid('porch deck', x0, x1, -out, 0, z-.3, z, PLANKS, TIMBER, omit='bk')
    quad('porch skirt', PLANKS, OLD_TIMBER, (x0, -out+.1, 0), (9.6, -out+.1, 0), (9.6, -out+.1, z-.3), (x0, -out+.1, z-.3))
    quad('porch skirt', PLANKS, OLD_TIMBER, (14.4, -out+.1, 0), (x1, -out+.1, 0), (x1, -out+.1, z-.3), (14.4, -out+.1, z-.3))
    for i in range(3):  # Steps up through the deck's front.
        cuboid('porch step', 9.6, 14.4, -out-.2+i*.5, -out+.5+i*.5, 0, (i+1)*z/3-.3*(i == 2), PLANKS, TIMBER, omit='bk')
    for x in (x0+.3, x1-.3):
        cuboid('porch post', x-.25, x+.25, -out+.1, -out+.6, z, roof-.2, RENDER, TRIM, omit='bt')
    timber_rail(x0+.55, 9.4, -out+.35, z)
    timber_rail(14.6, x1-.55, -out+.35, z)
    cuboid('porch beam', x0, x1, -out+.05, -out+.65, roof-.7, roof-.2, RENDER, TRIM, omit='')
    # The lean-to: shingles from the wall down to its beam, a little past it, and its boards from below.
    a, b = (0, roof+1.6), (-out-.5, roof-.3)
    quad('porch roof', SHINGLES, (.95, .93, .90), (x0-.4, b[0], b[1]), (x1+.4, b[0], b[1]), (x1+.4, a[0], a[1]), (x0-.4, a[0], a[1]))
    quad('porch roof boards', PLANKS, OLD_TIMBER, (x0-.4, a[0], a[1]-.15), (x1+.4, a[0], a[1]-.15), (x1+.4, b[0], b[1]-.15), (x0-.4, b[0], b[1]-.15))
    quad('porch roof edge', PLANKS, OLD_TIMBER, (x0-.4, b[0], b[1]-.15), (x1+.4, b[0], b[1]-.15), (x1+.4, b[0], b[1]), (x0-.4, b[0], b[1]))


def balcony(x0, x1, z, rng, out=3.0):
    """A boarded balcony on brackets, a rail round it."""
    cuboid('balcony deck', x0, x1, -out, 0, z-.3, z, PLANKS, TIMBER, omit='k')
    for x in (x0+.3, x1-.3):
        add('balcony bracket', PLANKS, OLD_TIMBER, [(x-.15, 0, z-.3), (x+.15, 0, z-.3), (x+.15, -out+.4, z-.3), (x-.15, -out+.4, z-.3),
                                                   (x-.15, 0, z-2.6), (x+.15, 0, z-2.6)], [(0, 3, 4), (1, 5, 2), (3, 2, 5, 4)], detail=True)
        cuboid('balcony post', x-.2, x+.2, -out+.05, -out+.45, z, z+2.8, RENDER, TRIM, omit='bt')
    timber_rail(x0+.5, x1-.5, -out+.25, z)


def timber_bay(rng, kind, base):
    """A house's front, two storeys of it: clapboard between corner boards, sash windows, a band board at the upper floor;
    on the ground a boarded foundation, and by kind a porch (`porch`), a balcony (`balcony`) or more windows."""
    foot = 1.2 if base else 0.0
    low, high = (foot+2.2, foot+6.8) if base else (2.4, 7.4), (11.4, 16.4)
    rows = {'pair': ((7, 17), (7, 17)), 'triple': ((5, 12, 19), (5, 12, 19)), 'mixed': ((7, 17), (5, 12, 19)),
            'balcony': ((6, 18), (5.5,)), 'porch': ((5.4, 18.6), (7, 17)), 'yard': ((7,), (7, 17))}[kind]
    holes = [(x-1.4, x+1.4, *span) for xs, span in zip(rows, (low, high)) for x in xs]
    if kind == 'porch':
        holes.append((10.4, 13.6, foot, foot+7.0))
    elif kind == 'balcony':
        holes.append((13.4, 16.6, STOREY+.3, STOREY+7.3))
    k.facade('wall clapboard', holes, foot, LEVEL, colour=PAINTED, du=4, dv=6, key=CLAP, amount=.8, **({'foot': foot} if base else {}))
    for xs, span in zip(rows, (low, high)):
        for x in xs:
            sash(x, *span, rng)
    for x0, x1, omit in ((0, .3, 'bkl'), (W-.3, W, 'bkr')):  # Corner boards: with the next bay's, a house's edge.
        cuboid('corner board', x0, x1, -.15, 0, foot, LEVEL, RENDER, TRIM, omit=omit+'t')
    cuboid('band board', .3, W-.3, -.12, 0, STOREY-.3+foot/2, STOREY+.3+foot/2, RENDER, TRIM, omit='klr')
    if base:
        cuboid('foundation', 0, W, -.2, 0, 0, foot, PLANKS, OLD_TIMBER, omit='bklr')
    if kind == 'porch':
        plank_door(12, foot, rng)
        porch(foot, rng)
    elif kind == 'balcony':
        plank_door(15, STOREY+.3, rng, height=7.0)
        balcony(10.5, 21.5, STOREY+.3, rng)
    elif kind == 'yard':
        h.round_prism('water butt', 17.5, -1.6, 0, 3.6, 1.4, PLANKS, OLD_TIMBER, 10)
        cuboid('downpipe', 17.3, 17.7, -.4, 0, 3.6, LEVEL, MATTE, DARK, omit='bkt', detail=True)
        cuboid('crate', 12.4, 14.8, -2.4, -.2, 0, 2.2, PLANKS, TIMBER, omit='b')
    k.back_wall(W, 0, LEVEL, depth=1.0)


def timber_end(rng, base):
    """A wall's end: plain clapboard between corner boards."""
    foot = 1.2 if base else 0.0
    k.facade('wall clapboard', [], foot, LEVEL, length=END, colour=PAINTED, du=6, dv=6, key=CLAP)
    for x0, x1 in ((0, .6), (END-.6, END)):
        cuboid('corner board', x0, x1, -.15, 0, foot, LEVEL, RENDER, TRIM, omit='bkt')
    cuboid('band board', .6, END-.6, -.12, 0, STOREY-.3+foot/2, STOREY+.3+foot/2, RENDER, TRIM, omit='klr')
    if base:
        cuboid('foundation', 0, END, -.2, 0, 0, foot, PLANKS, OLD_TIMBER, omit='bklr')
    k.back_wall(END, 0, LEVEL, depth=1.0)


def timber_eave(rng, kind):
    """The roof's edge: a fascia board on brackets under an eave of felt."""
    cuboid('eave fascia', 0, W, -1.0, -.8, -.6, 1.0, RENDER, TRIM, omit='klr')
    quad('eave boards', PLANKS, OLD_TIMBER, (0, 0, -.6), (W, 0, -.6), (W, -.8, -.6), (0, -.8, -.6))
    quad('eave felt', FELT, (1, 1, 1), (0, -1.0, 1.0), (W, -1.0, 1.0), (W, .6, 1.0), (0, .6, 1.0))
    for x in (3, 9, 15, 21):
        cuboid('eave bracket', x-.2, x+.2, -.8, 0, -1.5, -.6, RENDER, TRIM, omit='kt', detail=True)
    if kind == 'pipe':
        cuboid('downpipe head', 11.6, 12.4, -1.3, -1.0, -1.4, .4, MATTE, DARK, omit='k', detail=True)


def stovepipe(rng):
    cuboid('flashing', -1.2, 1.2, -1.2, 1.2, 0, .2, MATTE, DARK, omit='b', detail=True)
    h.round_prism('stovepipe', 0, 0, 0, 5.4, .5, MATTE, (.30, .30, .30), 8)
    h.round_prism('stovepipe cowl', 0, 0, 5.4, 6.0, .9, MATTE, DARK, 8)


def roof_hatch(rng):
    cuboid('hatch kerb', -2.6, 2.6, -2.6, 2.6, 0, 1.0, PLANKS, OLD_TIMBER, omit='b')
    h.deck('hatch lid', -2.9, 2.9, -2.9, 2.9, 1.05, PLANKS, TIMBER)


def barrels(rng):
    for x, y in ((-2, 0), (1.6, 1.2)):
        h.round_prism('barrel', x, y, 0, 3.4, 1.5, PLANKS, OLD_TIMBER, 10)
    cuboid('crate', .2, 3.0, -3.4, -.8, 0, 2.4, PLANKS, TIMBER, omit='b')


def washing(rng):
    """Two posts and the washing between them."""
    for x in (-8, 8):
        cuboid('line post', x-.2, x+.2, -.2, .2, 0, 6.2, PLANKS, OLD_TIMBER, omit='b')
        cuboid('line arm', x-.15, x+.15, -1.6, 1.6, 5.8, 6.1, PLANKS, OLD_TIMBER, omit='', detail=True)
    for y in (-1.3, 1.3):
        clothesline(-8, 8, y, 5.9, rng, 5)


# Masonry: infill in a thin concrete frame, built storey by storey as money allows.

def masonry_window(x, z, width, height, rng, wall, extra=None):
    """A small steel window in a reveal of its wall's finish; extra: `bars`, an `awning` of tin, an `ac` box under it."""
    x0, x1, z1 = x-width/2, x+width/2, z+height
    k.recess('reveal', x0, x1, z, z1, .45, wall[1], wall[0])
    pane(x0, x1, z, z1, .4, rng, .35)
    for a, b, c, d in ((x0, x0+.14, z, z1), (x1-.14, x1, z, z1), (x0, x1, z, z+.14), (x0, x1, z1-.14, z1), (x-.07, x+.07, z, z1)):
        cuboid('window frame', a, b, .3, .4, c, d, MATTE, (.62, .63, .63), omit='k', detail=True)
    cuboid('window sill', x0-.2, x1+.2, -.25, 0, z-.25, z, CAST, RAW, omit='k', detail=True)
    if extra == 'bars':
        for i in range(1, round(width/.55)):
            a = x0+width*i/round(width/.55)
            cuboid('window bars', a-.04, a+.04, -.06, .02, z, z1, MATTE, DARK, omit='bt', detail=True)
        for c in (z+height/3, z+2*height/3):
            cuboid('window bars', x0, x1, -.07, .01, c-.04, c+.04, MATTE, DARK, omit='lr', detail=True)
    elif extra == 'awning':
        a, b = (0, z1+1.1), (-1.9, z1+.35)
        quad('awning', TIN, RUSTY, (x0-.5, b[0], b[1]), (x1+.5, b[0], b[1]), (x1+.5, a[0], a[1]), (x0-.5, a[0], a[1]), both=True)
    elif extra == 'ac':
        h.ac_unit(x, 0, z-2.9)


def steel_door(x, z, rng, width=3.2, height=6.6):
    x0, x1 = x-width/2, x+width/2
    k.recess('reveal', x0, x1, z, z+height, .4, RAW, CAST)
    quad('door leaf', PAINT, rng.choice(((.34, .40, .44), (.42, .30, .24), (.30, .38, .32))), (x0, .35, z), (x1, .35, z), (x1, .35, z+height), (x0, .35, z+height))
    quad('door grille', h.PALE_GLASS, LOBBY, (x-.8, .3, z+4.2), (x+.8, .3, z+4.2), (x+.8, .3, z+5.6), (x-.8, .3, z+5.6), light='night')


def masonry_bay(rng, kind, base):
    """Two storeys of a self-built block: columns and slab edges of raw concrete, infill of painted render or bare hollow
    brick, small windows as each household could afford them, pipes, air conditioners, dishes and washing."""
    render, brick = (RENDER, rng.choice((PAINTED, (.90, .89, .85), (.93, .90, .84))), 'wall render'), (BRICK, (1, 1, 1), 'brick infill')
    faded = (RENDER, rng.choice(((.86, .85, .81), PAINTED)), 'wall render')
    lower, upper, windows = {
        'render': (render, faded, [(0, 6.5, 2.8, 5.0, 3.2, 'bars'), (0, 17.5, 3.4, 2.6, 2.6, None), (1, 7, 2.6, 3.4, 3.4, 'awning'), (1, 17, 2.9, 3.4, 3.2, 'ac')]),
        'brick': (brick, brick, [(0, 7.5, 2.6, 3.4, 3.4, 'awning'), (0, 18, 4.2, 2.2, 2.2, None), (1, 6, 2.8, 2.6, 3.2, None), (1, 15.5, 2.8, 5.0, 3.2, 'bars')]),
        'mixed': (render, brick, [(0, 12, 2.6, 5.4, 3.4, 'bars'), (1, 6.5, 2.8, 3.4, 3.4, None), (1, 17.5, 2.9, 3.4, 3.2, 'ac')]),
        'patched': (faded, render, [(0, 6, 2.9, 3.4, 3.2, 'ac'), (0, 17, 2.6, 3.4, 3.4, 'bars'), (1, 7.5, 2.8, 5.0, 3.2, 'awning')]),
        'balcony': (render, render, [(0, 6.5, 2.6, 3.4, 3.4, None), (0, 17.5, 2.6, 3.4, 3.4, 'awning'), (1, 17, 2.8, 3.4, 3.4, None)]),
        'door': (render, faded, [(0, 17, 3.0, 3.4, 3.2, 'bars'), (1, 7, 2.6, 3.4, 3.4, None), (1, 17, 2.9, 3.4, 3.2, 'ac')]),
        'shop': (render, brick, [(1, 7, 2.8, 3.4, 3.4, 'awning'), (1, 17, 2.8, 2.6, 3.0, None)]),
        'plain': (brick, render, [(0, 8, 3.0, 3.4, 3.2, 'bars'), (1, 12, 2.6, 5.0, 3.4, 'bars')]),
    }[kind]
    foot = .2 if base else 0.0
    spans = ((foot, STOREY-.7), (STOREY+.1, LEVEL-.9))
    for half, wall in enumerate((lower, upper)):
        z0, z1 = spans[half]
        holes = [(x-w/2, x+w/2, z0+sill, z0+sill+height) for at, x, sill, w, height, extra in windows if at == half]
        if kind == 'door' and half == 0:
            holes.append((5.4, 8.6, foot, foot+6.6))
        elif kind == 'shop' and half == 0:
            holes.append((5, 19, foot, foot+6.4))
        elif kind == 'balcony' and half == 1:
            holes.append((6.4, 9.6, z0, z0+6.6))
        elif kind == 'patched' and half == 1:
            holes.append((14.5, 22.2, z0+1.2, z0+5.4))
        k.facade(wall[2], holes, z0, z1, colour=wall[1], du=4, dv=4, key=wall[0], amount=1.2 if wall[0] == RENDER else .5,
                 **({'foot': z0} if base and half == 0 else {}))
        for at, x, sill, w, height, extra in windows:
            if at == half:
                masonry_window(x, z0+sill, w, height, rng, wall, extra)
    for x0, x1, omit in ((0, .7, 'bkl'), (W-.7, W, 'bkr')):
        cuboid('frame column', x0, x1, -.15, 0, 0, LEVEL, CAST, RAW, omit=omit+'t')
    for z0, z1 in ((STOREY-.7, STOREY+.1), (LEVEL-.9, LEVEL)):
        cuboid('frame slab', 0, W, -.3, 0, z0, z1, CAST, (.74, .73, .70), omit='klr')
    cuboid('waste pipe', 1.2, 1.5, -.3, 0, foot, LEVEL, PAINT, (.74, .74, .70), omit='bkt', detail=True)
    if base:
        cuboid('threshold', 0, W, -.5, 0, 0, foot, CAST, KERB, omit='bklr')
    if kind == 'door':
        steel_door(7, foot, rng)
        h.lamp(7, 0, foot+7.3)
    elif kind == 'shop':
        k.recess('reveal', 5, 19, foot, foot+6.4, .4, RAW, CAST)
        quad('shop shutter', h.SLATS, (.66, .68, .66), (5, .35, foot), (19, .35, foot), (19, .35, foot+6.4), (5, .35, foot+6.4))
        sign = rng.choice(((.62, .26, .20), (.24, .40, .58), (.80, .66, .28)))
        cuboid('shop sign', 4.6, 19.4, -.25, 0, foot+6.6, foot+8.0, PAINT, sign, omit='k')
        a, b = (0, foot+6.6), (-2.6, foot+5.9)
        quad('awning', TIN, RUSTY, (4.6, b[0], b[1]), (19.4, b[0], b[1]), (19.4, a[0], a[1]), (4.6, a[0], a[1]), both=True)
    elif kind == 'balcony':
        z = STOREY+.1
        steel_door(8, z, rng)
        cuboid('balcony slab', 3, 21, -3.2, 0, z-.8, z, CAST, RAW, omit='k')
        h.rail('balcony rail', (3.15, -3.05, z), (20.85, -3.05, z), height=2.9, spacing=4.4)
        for x in (3.15, 20.85):
            cuboid('balcony rail side', x-.1, x+.1, -3.05, 0, z+2.68, z+2.9, STEEL, h.HANDRAIL, omit='b', detail=True)
        clothesline(4, 20, -2.4, z+5.6, rng, 5)
    elif kind == 'patched':  # Where the render has come away: the brick behind it, and a dish.
        z0 = spans[1][0]
        quad('brick infill', BRICK, (1, 1, 1), (14.5, .06, z0+1.2), (22.2, .06, z0+1.2), (22.2, .06, z0+5.4), (14.5, .06, z0+5.4))
        cuboid('dish arm', 18.4, 18.7, -1.1, 0, z0+6.2, z0+6.5, MATTE, DARK, omit='k', detail=True)
        h.disc('dish', 18.55, -1.15, z0+6.6, 1.3, '-y', PAINT, (.84, .84, .82), 10)
    k.back_wall(W, 0, LEVEL, depth=1.0)


def masonry_end(rng, base):
    """A wall's end: render between two columns, the slab edges across it."""
    foot = .2 if base else 0.0
    for z0, z1 in ((foot, STOREY-.7), (STOREY+.1, LEVEL-.9)):
        k.facade('wall render', [], z0, z1, length=END, colour=(.90, .89, .85), du=3, dv=4, key=RENDER, amount=1.2)
    for x0, x1 in ((0, 1.4), (END-1.4, END)):
        cuboid('frame column', x0, x1, -.15, 0, 0, LEVEL, CAST, RAW, omit='bkt')
    for z0, z1 in ((STOREY-.7, STOREY+.1), (LEVEL-.9, LEVEL)):
        cuboid('frame slab', 0, END, -.3, 0, z0, z1, CAST, (.74, .73, .70), omit='klr')
    if base:
        cuboid('threshold', 0, END, -.5, 0, 0, foot, CAST, KERB, omit='bklr')
    k.back_wall(END, 0, LEVEL, depth=1.0)


def masonry_parapet(rng, kind):
    """The roof's edge, never finished: the frame's columns stand on as stubs with their bars out, and brick between them
    as high as it got."""
    for x0, x1, omit in ((0, .7, 'l'), (W-.7, W, 'r')):
        cuboid('frame column', x0, x1, -.15, .6, 0, 2.6, CAST, RAW, omit='b'+omit)
        for x in (x0+.2, x1-.2):
            for y in (0, .4):
                cuboid('starter bars', x-.05, x+.05, y-.05, y+.05, 2.6, 4.6+rng.uniform(-.6, .4), MATTE, (.36, .26, .22), omit='b', detail=True)
    steps = {'low': ((.7, W-.7, 1.2),), 'wall': ((.7, W-.7, 3.0),), 'part': ((.7, 9.4, 3.0), (9.4, 14.2, 1.9), (14.2, W-.7, .8))}[kind]
    for x0, x1, height in steps:
        cuboid('brick infill', x0, x1, 0, .5, 0, height, BRICK, (1, 1, 1), omit='b')


def water_tank(rng):
    cuboid('tank stand', -2.6, 2.6, -2.6, 2.6, 0, 2.2, BRICK, (1, 1, 1), omit='b')
    h.deck('tank stand top', -2.9, 2.9, -2.9, 2.9, 2.22, CAST, RAW)
    h.round_prism('water tank', 0, 0, 2.25, 6.2, 2.5, PAINT, (.16, .36, .66), 12)
    h.round_prism('water tank lid', 0, 0, 6.2, 6.7, 1.9, PAINT, (.14, .31, .58), 12)
    cuboid('tank pipe', -.12, .12, -4.4, -2.5, .1, .34, PAINT, (.74, .74, .70), omit='b', detail=True)


def roof_shack(rng):
    """A room begun on the roof: brick under a tin lean-to."""
    cuboid('brick infill', -6, 6, -4.5, 4.5, 0, 6.6, BRICK, (1, 1, 1), omit='bt')
    quad('shack door', PAINT, (.34, .40, .44), (-1.5, -4.56, 0), (1.5, -4.56, 0), (1.5, -4.56, 5.6), (-1.5, -4.56, 5.6))
    quad('tin roof', TIN, RUSTY, (-6.8, -5.4, 6.4), (6.8, -5.4, 6.4), (6.8, 5.2, 7.6), (-6.8, 5.2, 7.6), both=True)
    for x, y in ((-4, -2), (3, 3), (5, -3)):
        cuboid('roof weight', x-.6, x+.6, y-.4, y+.4, 6.9+.11*(y+5.4)-.4, 7.2+.11*(y+5.4)-.4, BRICK, (.9, .9, .9), omit='b', detail=True)


def brick_pile(rng):
    cuboid('brick pile', -2.4, 2.4, -1.4, 1.4, 0, 2.0, BRICK, (1, 1, 1), omit='b')
    cuboid('brick pile', -2.4, .8, -1.4, 1.4, 2.0, 3.0, BRICK, (.94, .94, .94), omit='b')
    h.round_prism('sand heap', 5, .5, 0, .9, 2.2, CAST, (.86, .80, .66), 8)
    h.round_prism('bucket', 3.2, -2.6, 0, 1.1, .5, PAINT, (.22, .24, .26), 8, detail=True)


def dish_mast(rng):
    cuboid('dish mast', -.12, .12, -.12, .12, 0, 4.4, MATTE, DARK, omit='b')
    h.disc('dish', 0, -.3, 4.2, 1.6, '-y', PAINT, (.84, .84, .82), 10)
    h.disc('dish', 0, -.29, 4.2, 1.6, '+y', PAINT, (.60, .60, .58), 10)


def civilian():
    timber_floors = ('pair', 'triple', 'mixed', 'balcony')
    masonry_floors = ('render', 'brick', 'mixed', 'patched', 'balcony')
    pieces = {
        **{f'timber-{kind}{twin}': (lambda rng, kind=kind: timber_bay(rng, kind, False)) for kind in timber_floors for twin in ('', TWIN)},
        **{f'timber-base-{kind}': (lambda rng, kind=kind: timber_bay(rng, kind, True)) for kind in ('porch', 'pair', 'yard')},
        **{f'eave-{kind}': (lambda rng, kind=kind: timber_eave(rng, kind)) for kind in ('plain', 'pipe')},
        'stovepipe': stovepipe, 'roof-hatch': roof_hatch, 'barrels': barrels, 'washing': washing,
        'timber-end': lambda rng: timber_end(rng, False), 'timber-base-end': lambda rng: timber_end(rng, True),
        'masonry-end': lambda rng: masonry_end(rng, False), 'masonry-base-end': lambda rng: masonry_end(rng, True),
        **{f'masonry-{kind}{twin}': (lambda rng, kind=kind: masonry_bay(rng, kind, False)) for kind in masonry_floors for twin in ('', TWIN)},
        **{f'masonry-base-{kind}': (lambda rng, kind=kind: masonry_bay(rng, kind, True)) for kind in ('door', 'shop', 'plain', 'render')},
        **{f'parapet-{kind}': (lambda rng, kind=kind: masonry_parapet(rng, kind)) for kind in ('low', 'wall', 'part')},
        'water-tank': water_tank, 'roof-shack': roof_shack, 'brick-pile': brick_pile, 'dish-mast': dish_mast,
    }
    timber_planar, masonry_planar = {CLAP: 18.0, RENDER: 18.0}, {RENDER: 18.0, BRICK: 12.0, CAST: 12.0}
    roofs = {
        'felt': {'material': FELT, 'repeat': 24.0, 'inset': 0.0, 'heights': [1.0], 'aviationLights': False,
                 'runs': [k.run(['eave-plain', 'eave-pipe', 'eave-plain'], timber_planar)]},
        'slab': {'material': CAST, 'repeat': 12.0, 'inset': 0.0, 'heights': [.3], 'aviationLights': False,
                 'runs': [k.run(['parapet-low', 'parapet-wall', 'parapet-part', 'parapet-low', 'parapet-part'], masonry_planar)]},
    }
    run = lambda prefix, bays, planar, entrance=None: k.run([prefix+bay for bay in bays], planar, entrance and prefix+entrance, prefix+'end', margin=MARGIN)
    common = {'lone': k.LONE, 'bandEnd': 1.75, 'varyBays': True}
    variants = [
        {'name': 'timber', 'roof': 'felt', **common,
         'floors': {'material': PLANKS, 'repeat': 18.0, 'inset': 1.0, 'heights': [0.05]},
         'fittings': [{'stovepipe': [[-6, 5, 0]]}, {'washing': [[0, -3, 0]], 'stovepipe': [[9, 10, 0]]}, {'barrels': [[-8, -7, 0]], 'roof-hatch': [[6, 6, 0]]},
                      {'stovepipe': [[5, -8, 0], [-9, 8, 0]]}, {'roof-hatch': [[0, 0, 0]], 'washing': [[0, 9, 0]]}, {}],
         'base': [run('timber-base-', ['pair', 'yard', 'pair', 'porch'], timber_planar, 'porch'),
                  run('timber-base-', ['yard', 'pair', 'porch', 'pair'], timber_planar, 'porch')],
         'floor': [run('timber-', bays, timber_planar) for bays in storeys(timber_floors)]},
        {'name': 'masonry', 'roof': 'slab', **common,
         'floors': {'material': CAST, 'repeat': 12.0, 'inset': 1.0, 'heights': [0.05]},
         'fittings': [{'water-tank': [[-7, 6, 0]]}, {'roof-shack': [[2, 3, 0]], 'dish-mast': [[-11, -9, 0]]}, {'washing': [[0, -5, 0]], 'water-tank': [[8, 9, 0]]},
                      {'brick-pile': [[-6, -6, 30]], 'water-tank': [[7, 5, 0]]}, {'roof-shack': [[-4, -2, 90]], 'water-tank': [[10, 10, 0]]},
                      {'dish-mast': [[6, -8, 0]], 'brick-pile': [[-5, 7, 0]]}],
         'base': [run('masonry-base-', ['plain', 'shop', 'render', 'door', 'plain'], masonry_planar, 'door'),
                  run('masonry-base-', ['render', 'plain', 'shop', 'plain'], masonry_planar, 'door')],
         'floor': [run('masonry-', bays, masonry_planar) for bays in storeys(masonry_floors)]},
    ]
    return pieces, roofs, variants


# -- Castle Brian: a habitat built to outlast a siege ------------------------------------------------------
FERRO = 'structures/common/ferrocrete'
GUNMETAL = (.44, .47, .52)  # The Castle Brian walls' steel (satin steel in their armour's tone).
GUN_DARK = (.31, .33, .37)
PALE = (.97, .96, .93)
SHADE = (.80, .79, .76)
OUT, LEDGE, IN, GLASS = 3.0, 1.5, .5, .9  # A hood's lip stands OUT; on it a LEDGE, then a wall leaning back to IN. A hall's glass lies GLASS in.
HOOD = 1.6  # A hood's fascia.
RIB = .8  # Half a steel rib, at each end of a bay.
A, B = RIB, W-RIB


def bolts(points, y, radius=.16):
    for x, z in points:
        h.disc('bolt', x, y, z, radius, '-y', STEEL, GUN_DARK, 6, detail=True)


def strip(z0, z1, rng, shutters=0.0, x0=A, x1=B, y=GLASS, lit=.35, lean=0.0):
    """A strip of armoured glass between steel mullions, some panes behind closed steel shutters; its head `lean` further in."""
    count = round((x1-x0)/3.75)
    for i in range(count):
        a, b = x0+(x1-x0)*i/count, x0+(x1-x0)*(i+1)/count
        if rng.random() < shutters:
            quad('shutter', h.SLATS, (.42, .45, .50), (a, y-.3, z0), (b, y-.3, z0), (b, y+lean-.3, z1), (a, y+lean-.3, z1))
        else:
            pane(a, b, z0, z1, y, rng, lit, lean)
        if i:
            front = [(a-.18, y-.45, z0), (a+.18, y-.45, z0), (a+.18, y+lean-.45, z1), (a-.18, y+lean-.45, z1)]
            back = [(x, v+.45, z) for x, v, z in front]
            add('mullion', STEEL, GUN_DARK, front+back, [(0, 1, 2, 3), (4, 0, 3, 7), (1, 5, 6, 2)], detail=True)


def ribs(base=False, top=LEVEL):
    """Half a gunmetal rib at each end of the bay: a web and its flange, on the ground a battered concrete buttress under it."""
    for x0, x1, omit, f0, f1 in ((0, RIB, 'l', 0, RIB+.5), (W-RIB, W, 'r', W-RIB-.5, W)):
        z0 = 0
        if base:
            h.profile_x('wall buttress', [(GLASS, 0), (-5, 0), (-5, .8), (-OUT-.7, STOREY-HOOD), (-OUT-.7, STOREY), (GLASS, STOREY)], x0, x1, FERRO, SHADE)
            z0 = STOREY
        cuboid('rib', x0, x1, -OUT-.5, GLASS, z0, top, STEEL, GUNMETAL, omit='bkt'+omit)
        cuboid('rib flange', f0, f1, -OUT-.7, -OUT-.5, z0, top, STEEL, GUN_DARK, omit='bt'+omit)


def terrace(z, rng, kind='strip', foot=None, gap=None):
    """One storey of the stepped front: a ledge on the hood below (a planter, where planted), a wall leaning back from it
    (an upstand of ferrocrete under a band of armoured glass), and over it this storey's hood: a ferrocrete fascia under
    a gunmetal edge beam. foot: on the ground, a glacis from that far out, open across `gap` (a porch's width)."""
    top = z+STOREY
    back = -(OUT-LEDGE)
    if foot:
        for a, b in ((A, gap[0]), (gap[1], B)) if gap else ((A, B),):
            quad('wall glacis', FERRO, PALE, (a, -foot, z), (b, -foot, z), (b, -foot, z+.8), (a, -foot, z+.8))
            quad('wall glacis', FERRO, PALE, (a, -foot, z+.8), (b, -foot, z+.8), (b, -OUT, top-HOOD), (a, -OUT, top-HOOD))
    else:
        head = top-HOOD-.6  # The wall's top, under the hood.
        at = lambda height: back+(back+IN)*-1*height/(head-z)  # The leaning wall's y that far up it.
        quad('ledge', CAST, (.80, .80, .77), (A, -OUT, z), (B, -OUT, z), (B, back, z), (A, back, z))
        for z0, z1 in ((0, 1.6), (head-z-.5, head-z)):
            quad('wall upstand', FERRO, PALE, (A, at(z0), z+z0), (B, at(z0), z+z0), (B, at(z1), z+z1), (A, at(z1), z+z1))
        strip(z+1.6, head-.5, rng, .45 if kind == 'shutter' else .08, y=at(1.6), lean=at(head-z-.5)-at(1.6))
        quad('hood soffit', CAST, (.55, .55, .53), (A, -IN, head), (B, -IN, head), (B, -OUT+.6, head), (A, -OUT+.6, head))
        quad('hood soffit', CAST, (.66, .66, .64), (A, -OUT+.6, head), (B, -OUT+.6, head), (B, -OUT, top-HOOD), (A, -OUT, top-HOOD))
        if kind == 'planted':
            # A trough on the ledge: plants root .3 under their soil, and a storey's piece keeps to its own 18 units.
            quad('planter lip', FERRO, SHADE, (A, -OUT+.3, z), (B, -OUT+.3, z), (B, -OUT+.3, z+.4), (A, -OUT+.3, z+.4))
            quad('planter soil', k.LAWN, k.LAWN_TINT, (A, -OUT+.3, z+.4), (B, -OUT+.3, z+.4), (B, back, z+.4), (A, back, z+.4))
            k.plants(A+1.2, B-1.2, -OUT+LEDGE/2+.15, z+.4, rng, size=(1.8, 2.6), spacing=2.4)
    quad('wall hood', FERRO, SHADE, (A, -OUT, top-HOOD), (B, -OUT, top-HOOD), (B, -OUT, top-.5), (A, -OUT, top-.5))
    cuboid('edge beam', A, B, -OUT-.15, -OUT+.2, top-.5, top, STEEL, GUNMETAL, omit='bklr')
    bolts([(x, top-.25) for x in (3, 7.5, 12, 16.5, 21)], -OUT-.17, .13)


def tower(rng, base):
    """A stair core in place of the terraces: a tower's sheer face between the ribs, a slit of glass up it."""
    y = -OUT-.3
    for x0, x1 in ((A, 10.2), (13.8, B)):
        quad('wall tower', FERRO, PALE, (x0, y, 0), (x1, y, 0), (x1, y, LEVEL), (x0, y, LEVEL))
    z0 = 8.4 if base else 0
    for x in (10.2, 13.8):
        quad('tower reveal', FERRO, SHADE, *((x, y, z0), (x, y+1.2, z0), (x, y+1.2, LEVEL), (x, y, LEVEL))[::1 if x < 12 else -1])
        cuboid('slit frame', x-.25, x+.25, y-.2, y, z0, LEVEL, STEEL, GUNMETAL, omit='bkt', detail=True)
    count = 2 if base else 3
    for i in range(count):
        a, b = z0+(LEVEL-z0)*i/count, z0+(LEVEL-z0)*(i+1)/count
        quad('stair glass', h.PALE_GLASS, LOBBY, (10.2, y+1.2, a), (13.8, y+1.2, a), (13.8, y+1.2, b), (10.2, y+1.2, b), light='night')
        if i:
            cuboid('slit transom', 10.2, 13.8, y+.9, y+1.2, a-.15, a+.15, STEEL, GUN_DARK, omit='klr', detail=True)
    if base:
        quad('wall tower', FERRO, PALE, (10.2, y, 7.6), (13.8, y, 7.6), (13.8, y, 8.4), (10.2, y, 8.4))
        quad('blast door', hk.ARMOUR, (1, 1, 1), (10.2, y+.5, 0), (13.8, y+.5, 0), (13.8, y+.5, 7.6), (10.2, y+.5, 7.6))
        quad('door hazard', hk.HAZARD, (1, 1, 1), (10.2, y-.02, 7.6), (13.8, y-.02, 7.6), (13.8, y-.02, 8.4), (10.2, y-.02, 8.4), detail=True)
        for x in (10.2, 13.8):
            quad('tower reveal', FERRO, SHADE, *((x, y, 0), (x, y+.5, 0), (x, y+.5, 7.6), (x, y, 7.6))[::1 if x < 12 else -1])
        hk.work_light(12, 9.4, y-.02)


def portal(rng):
    """The way in: a ferrocrete porch standing out of the glacis, a lit hall deep in its mouth under a gunmetal lintel."""
    x0, x1, y, top = 5.5, 18.5, -5.0, STOREY-HOOD
    a, b, head = 7.6, 16.4, 6.0
    for p, q, r, s in (((x0, 0), (a, 0), (a, top), (x0, top)), ((b, 0), (x1, 0), (x1, top), (b, top)), ((a, head), (b, head), (b, top), (a, top))):
        quad('wall porch', FERRO, PALE, *((x, y, z) for x, z in (p, q, r, s)))
    for x, flip in ((x0, False), (x1, True)):
        corners = [(x, y, 0), (x, -OUT+2.2, 0), (x, -OUT+.2, top), (x, y, top)]
        quad('wall porch', FERRO, SHADE, *(corners if flip else corners[::-1]))
    quad('porch top', CAST, (.80, .80, .77), (x0, y, top), (x1, y, top), (x1, -OUT, top), (x0, -OUT, top))
    for x, flip in ((a, True), (b, False)):
        corners = [(x, y, 0), (x, GLASS, 0), (x, GLASS, head), (x, y, head)]
        quad('porch reveal', FERRO, SHADE, *(corners if flip else corners[::-1]))
    quad('porch soffit', CAST, (.55, .55, .53), (a, GLASS, head), (b, GLASS, head), (b, y, head), (a, y, head))
    quad('porch floor', CAST, KERB, (a, y, .12), (b, y, .12), (b, GLASS, .12), (a, GLASS, .12))
    lobby((GLASS, a, b, .12, head, True))
    cuboid('lintel', a-.6, b+.6, y-.2, y, head, head+1.1, STEEL, GUNMETAL, omit='k')
    bolts([(x, head+.55) for x in (8, 10, 12, 14, 16)], y-.22)
    for x in (a-1.1, b+1.1):
        h.lamp(x, y, 4.8)


def castle_bay(rng, kind, base):
    """Two storeys of the stepped front between two ribs. kind: `strip`, `shutter` (steel shutters across some of its
    glass), `planted` (its upper ledge a planter), `garden` (both ledges), `core` (a stair tower); on the ground `glacis` (the lower storey a
    blank battered foot), `louvre` (an armoured vent in it), `entrance` (the portal)."""
    ribs(base)
    if kind == 'core':
        tower(rng, base)
    else:
        if base:
            terrace(0, rng, foot=5.0, gap=(5.5, 18.5) if kind == 'entrance' else None)
            if kind == 'entrance':
                portal(rng)
            elif kind == 'louvre':
                cuboid('vent hood', 6, 18, -5.0, -3.0, 2.4, 6.4, FERRO, SHADE, omit='bk')
                quad('vent louvre', h.SLATS, (.42, .45, .50), (6.6, -5.03, 3.0), (17.4, -5.03, 3.0), (17.4, -5.03, 5.8), (6.6, -5.03, 5.8))
                cuboid('vent frame', 6.3, 17.7, -5.12, -5.0, 2.7, 6.1, STEEL, GUNMETAL, omit='k', detail=True)
        else:
            terrace(0, rng, {'shutter': 'shutter', 'garden': 'planted'}.get(kind, 'strip'))
        terrace(STOREY, rng, {'shutter': 'shutter', 'planted': 'planted', 'garden': 'planted'}.get(kind, 'strip'))
    k.back_wall(W, 0, LEVEL, depth=3.0)


def castle_end(rng, base, top=LEVEL):
    """A wall's end: a pier of ferrocrete as far out as the ribs, steel at its edges; on the ground it stands battered,
    on the roof (`top`) it stands on as a stub."""
    front = -OUT-.5
    if base:
        h.profile_x('wall pier', [(GLASS, 0), (-5, 0), (-5, .8), (front, STOREY-HOOD), (front, top), (GLASS, top)], 0, END, FERRO, PALE)
    else:
        cuboid('wall pier', 0, END, front, GLASS, 0, top, FERRO, PALE, omit='bk'+('t' if top == LEVEL else ''))
    for x0, x1 in ((0, 1.2), (END-1.2, END)):
        cuboid('pier edge', x0, x1, front-.2, front, STOREY if base else 0, top, STEEL, GUNMETAL, omit='bkt')
    if top != LEVEL:
        cuboid('pier cap', -.0, END, front-.2, GLASS+.2, top, top+.5, STEEL, GUN_DARK, omit='b')
    else:
        k.back_wall(END, 0, LEVEL, depth=3.0)


def exo_end(rng, base, top=LEVEL):
    """A wall's end: ferrocrete between two columns, the beams across it."""
    for x0, x1 in ((0, 2.0), (END-2.0, END)):
        cuboid('column', x0, x1, -1.6, 0, 0, top, STEEL, GUNMETAL, omit='bk'+('t' if top == LEVEL else ''))
        cuboid('column flange', x0, x1, -1.9, -1.6, 0, top, STEEL, GUN_DARK, omit='bk'+('t' if top == LEVEL else ''))
    if top == LEVEL:
        k.facade('wall ferrocrete', [], 0, LEVEL, length=END, colour=PALE, du=6, dv=4.5, key=FERRO)
        for z0, z1 in ((LEVEL-1.5, LEVEL), (STOREY-.6, STOREY+.3)):
            cuboid('beam', 2.0, END-2.0, -1.3, 0, z0, z1, STEEL, GUNMETAL, omit='klr')
        k.back_wall(END, 0, LEVEL, depth=3.0)
    else:
        cuboid('edge beam', 2.0, END-2.0, -1.3, .6, 0, 2.0, STEEL, GUNMETAL, omit='blr')
        cuboid('edge beam flange', 0, END, -1.9, .6, top-.4, top, STEEL, GUN_DARK, omit='b')


def castle_parapet(rng, kind):
    """The roof's edge: the last hood's ledge and a leaning parapet under a steel coping, the ribs standing through it."""
    back = -(OUT-LEDGE)
    quad('ledge', CAST, (.80, .80, .77), (A, -OUT, 0), (B, -OUT, 0), (B, back, 0), (A, back, 0))
    quad('wall upstand', FERRO, PALE, (A, back, 0), (B, back, 0), (B, back+.4, 3.0), (A, back+.4, 3.0))
    cuboid('coping', A, B, back+.2, .5, 3.0, 3.4, STEEL, GUNMETAL, omit='blr')
    quad('parapet back', FERRO, SHADE, (B, .3, .2), (A, .3, .2), (A, .3, 3.0), (B, .3, 3.0))
    ribs(top=4.0)
    for x0, x1 in ((0, RIB+.5), (W-RIB-.5, W)):
        quad('rib cap', STEEL, GUN_DARK, (x0, -OUT-.7, 4.0), (x1, -OUT-.7, 4.0), (x1, GLASS, 4.0), (x0, GLASS, 4.0))
    if kind == 'lamps':
        for x in (6, 18):
            hk.work_light(x, 1.6, back+.1)


# The exoskeleton: ferrocrete walls inside a frame of gunmetal columns, beams and braces.
COLUMN = 1.0  # Half a column, at each end of a bay.


def frame(base=False, top=LEVEL):
    for x0, x1, omit, f0, f1 in ((0, COLUMN, 'l', 0, COLUMN+.5), (W-COLUMN, W, 'r', W-COLUMN-.5, W)):
        cuboid('column', x0, x1, -1.6, 0, 0, top, STEEL, GUNMETAL, omit='bkt'+omit)
        cuboid('column flange', f0, f1, -1.9, -1.6, 0, top, STEEL, GUN_DARK, omit='bt'+omit)
        if base:
            c.extrude('column boot', [(1.9, 0), (3.0, 0), (1.9, 3.4)], k.front, f0, f1, STEEL, GUN_DARK)


def beam(z0, z1, out=1.3):
    cuboid('beam', COLUMN, W-COLUMN, -out, 0, z0, z1, STEEL, GUNMETAL, omit='klr')
    for z in (z0, z1-.25):
        cuboid('beam flange', COLUMN, W-COLUMN, -out-.25, -out, z, z+.25, STEEL, GUN_DARK, omit='klr')


def brace(rising, z0=.8, z1=LEVEL-2.3):
    """A diagonal across the bay, from one column's foot to the other's head, and the gussets that bolt it on."""
    x0, x1 = (COLUMN, W-COLUMN) if rising else (W-COLUMN, COLUMN)
    length = math.hypot(x1-x0, z1-z0)
    ux, uz = (x1-x0)/length, (z1-z0)/length
    nx, nz = -uz*.8, ux*.8
    low, high = [(x0+nx, z0+nz), (x0-nx, z0-nz)], [(x1+nx, z1+nz), (x1-nx, z1-nz)]
    y0, y1 = -1.55, -.9
    corners = [low[0], low[1], high[1], high[0]]
    quad('brace', STEEL, GUNMETAL, *((x, y0, z) for x, z in (corners if rising else corners[::-1])[::-1]))
    for p, q in ((low[0], high[0]), (high[1], low[1])):  # Its two sides.
        quad('brace', STEEL, GUN_DARK, (p[0], y0, p[1]), (q[0], y0, q[1]), (q[0], y1, q[1]), (p[0], y1, p[1]))
    for x, z, sx, sz in ((x0, z0, 1 if rising else -1, 1), (x1, z1, -1 if rising else 1, -1)):
        plate = [(x, z), (x+sx*5.2, z), (x+sx*5.2, z+sz*1.4), (x+sx*1.6, z+sz*4.6), (x, z+sz*4.6)]
        plate = plate if sx*sz > 0 else plate[::-1]
        add('gusset', STEEL, GUN_DARK, [(px, y0-.06, pz) for px, pz in plate], [(0, 1, 2, 3, 4)])
        bolts([(x+sx*a, z+sz*b) for a, b in ((.8, .7), (2.6, .7), (4.4, .7), (.8, 2.4), (.8, 4.0), (2.4, 2.2))], y0-.08)


def band(z0, z1, rng, shutters):
    """A band of glass deep in the ferrocrete, armoured louvres over some of it."""
    k.recess('band', 2.8, 21.2, z0, z1, 1.0, SHADE, FERRO)
    strip(z0, z1, rng, shutters, 2.8, 21.2, .95, .4)


def vault_door(rng):
    """A round vault door in a ferrocrete portal, its steel collar bolted on."""
    cx, cz, r, y = 12, 4.6, 3.7, -1.3
    cuboid('wall portal', 5.6, 18.4, y, 0, 0, 9.6, FERRO, PALE, omit='bk')
    ring = [(math.cos(math.tau*i/16), math.sin(math.tau*i/16)) for i in range(16)]
    for i, (p, q) in enumerate(zip(ring, ring[1:]+ring[:1])):
        outer, inner = [(cx+(r+.8)*s, cz+(r+.8)*t) for s, t in (p, q)], [(cx+r*s, cz+r*t) for s, t in (p, q)]
        quad('door collar', STEEL, GUNMETAL, (outer[0][0], y-.25, outer[0][1]), (outer[1][0], y-.25, outer[1][1]),
             (inner[1][0], y-.25, inner[1][1]), (inner[0][0], y-.25, inner[0][1]))
        quad('door collar', STEEL, GUN_DARK, (inner[0][0], y-.25, inner[0][1]), (inner[1][0], y-.25, inner[1][1]),
             (inner[1][0], y+.3, inner[1][1]), (inner[0][0], y+.3, inner[0][1]))
    add('vault door', hk.ARMOUR, (1, 1, 1), [(cx+r*s, y+.3, cz+r*t) for s, t in ring], [tuple(range(16))])
    h.disc('door boss', cx, y+.22, cz, 1.2, '-y', STEEL, GUNMETAL, 10)
    cuboid('door bar', cx-r+.5, cx+r-.5, y+.1, y+.3, cz-.25, cz+.25, STEEL, GUN_DARK, omit='k', detail=True)
    bolts([(cx+(r+.4)*s, cz+(r+.4)*t) for s, t in ring[::2]], y-.27)
    for x in (cx-r-1.4, cx+r+1.4):
        h.lamp(x, y, 7.4)


def exo_bay(rng, kind, base):
    """Two storeys inside the frame: bands of glass in ferrocrete behind the columns and beams. kind: `frame`, `shutter`,
    `brace-up` and `brace-down`; on the ground `plinth` (a blank lower storey over a battered foot), `vault` (the door)."""
    frame(base)
    k.facade('wall ferrocrete', [(2.8, 21.2, 11.4, 15.4)]+([] if base else [(2.8, 21.2, 2.4, 6.4)]), 0, LEVEL, colour=PALE, du=4, dv=4.5, key=FERRO, amount=.7)
    band(11.4, 15.4, rng, .35 if kind == 'shutter' else .12)
    if not base:
        band(2.4, 6.4, rng, .35 if kind == 'shutter' else .12)
    beam(LEVEL-1.5, LEVEL)
    beam(STOREY-.6, STOREY+.3, 1.0)
    if kind in ('brace-up', 'brace-down'):
        brace(kind == 'brace-up')
    if base:
        if kind == 'vault':
            vault_door(rng)
        else:
            c.extrude('wall plinth', [(0, 0), (2.4, 0), (1.9, .8), (0, 3.4)], k.front, COLUMN+.5, W-COLUMN-.5, FERRO, SHADE)
    k.back_wall(W, 0, LEVEL, depth=3.0)


def exo_edge(rng, kind):
    """The roof's edge: the columns' heads under a gunmetal edge beam."""
    frame(top=2.4)
    cuboid('edge beam', COLUMN, W-COLUMN, -1.3, .6, 0, 2.0, STEEL, GUNMETAL, omit='blr')
    cuboid('edge beam flange', 0, W, -1.9, .6, 2.0, 2.4, STEEL, GUN_DARK, omit='blr')
    bolts([(x, 1.0) for x in (4, 8, 12, 16, 20)], -1.32)
    if kind == 'lamps':
        for x in (6, 18):
            hk.work_light(x, .9, -1.34)


def vent_cowl(rng):
    """An armoured vent: a ferrocrete block under a gunmetal hood."""
    cuboid('vent block', -4, 4, -3, 3, 0, 3.0, FERRO, SHADE, omit='b')
    add('vent cowl', STEEL, GUNMETAL, [(-4.6, -3.6, 3.0), (4.6, -3.6, 3.0), (4.6, 3.6, 3.0), (-4.6, 3.6, 3.0), (-3.2, -2.4, 4.4), (3.2, -2.4, 4.4),
                                      (3.2, 2.4, 4.4), (-3.2, 2.4, 4.4)], [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)])
    for wall, a0, a1 in (((0, -3, c.SOUTH), -3.2, 3.2), ((0, 3, c.NORTH), -3.2, 3.2)):
        c.quad('vent louvre', wall, a0, a1, .7, 2.5, .05, h.SLATS, (.42, .45, .50))


def roof_garden(rng):
    """A planter of ferrocrete: the terraces' planting, on the roof."""
    cuboid('wall planter', -8, 8, -3.5, 3.5, 0, 2.0, FERRO, SHADE, omit='b')
    quad('planter soil', k.LAWN, k.LAWN_TINT, (-7.3, -2.8, 1.8), (7.3, -2.8, 1.8), (7.3, 2.8, 1.8), (-7.3, 2.8, 1.8))
    for y in (-1.4, 1.4):
        k.plants(-6.5, 6.5, y, 1.8, rng, size=(2.6, 3.8), spacing=2.8)


def armoured_hatch(rng):
    cuboid('hatch kerb', -3, 3, -3, 3, 0, 1.2, FERRO, SHADE, omit='b')
    h.deck('hatch lid', -2.7, 2.7, -2.7, 2.7, 1.22, STEEL, GUNMETAL)


def castle_brian():
    terraces, frames = ('strip', 'shutter', 'planted', 'garden'), ('frame', 'shutter', 'brace-up', 'brace-down')
    pieces = {
        **{f'terrace-{kind}{twin}': (lambda rng, kind=kind: castle_bay(rng, kind, False)) for kind in terraces for twin in ('', TWIN)},
        'terrace-core': lambda rng: castle_bay(rng, 'core', False),
        **{f'terrace-base-{kind}': (lambda rng, kind=kind: castle_bay(rng, kind, True)) for kind in ('glacis', 'louvre', 'entrance', 'core')},
        **{f'parapet-{kind}': (lambda rng, kind=kind: castle_parapet(rng, kind)) for kind in ('plain', 'lamps')},
        **{f'frame-{kind}{twin}': (lambda rng, kind=kind: exo_bay(rng, kind, False)) for kind in frames for twin in ('', TWIN)},
        **{f'frame-base-{kind}': (lambda rng, kind=kind: exo_bay(rng, kind, True)) for kind in ('plinth', 'vault', 'brace-up', 'brace-down')},
        **{f'edge-{kind}': (lambda rng, kind=kind: exo_edge(rng, kind)) for kind in ('plain', 'lamps')},
        'terrace-end': lambda rng: castle_end(rng, False), 'terrace-base-end': lambda rng: castle_end(rng, True),
        'parapet-end': lambda rng: castle_end(rng, False, 4.0),
        'frame-end': lambda rng: exo_end(rng, False), 'frame-base-end': lambda rng: exo_end(rng, True), 'edge-end': lambda rng: exo_end(rng, False, 2.4),
        'vent-cowl': vent_cowl, 'roof-garden': roof_garden, 'hatch': armoured_hatch, 'plant': lambda rng: c.plant_box('plant', -9, 9, -5, 5, 0, 6, 2, rows=2),
    }
    planar = {FERRO: 18.0, CAST: 12.0}
    slab = {'material': hk.DARK_ROOF, 'repeat': 24.0, 'inset': 0.0, 'heights': [.3], 'aviationLights': True}
    roofs = {'parapet': {**slab, 'runs': [k.run(['parapet-plain', 'parapet-lamps', 'parapet-plain'], planar, None, 'parapet-end', margin=MARGIN)]},
             'edge': {**slab, 'runs': [k.run(['edge-plain', 'edge-lamps', 'edge-plain'], planar, None, 'edge-end', margin=MARGIN)]}}
    run = lambda prefix, bays, entrance=None: k.run([prefix+bay for bay in bays], planar, entrance and prefix+entrance, prefix+'end', margin=MARGIN)
    common = {'lone': k.LONE, 'bandEnd': 1.75, 'varyBays': True, 'floors': {'material': CAST, 'repeat': 12.0, 'inset': 3.0, 'heights': [0.05]},
              'sidewalk': {'material': SIDEWALK, 'repeat': 12.0, 'width': 5.0, 'kerb': .25}}
    variants = [
        {'name': 'terraces', 'roof': 'parapet', **common,
         'fittings': [{'roof-garden': [[0, -6, 0]], 'vent-cowl': [[-7, 8, 0]]}, {'plant': [[0, 2, 0]]}, {'roof-garden': [[-4, 5, 90]], 'hatch': [[9, -8, 0]]},
                      {'vent-cowl': [[6, 6, 90], [-8, -7, 0]]}, {'roof-garden': [[0, 0, 0]]}, {'hatch': [[0, 0, 0]]}],
         'base': [run('terrace-base-', ['glacis', 'louvre', 'glacis', 'core'], 'entrance'), run('terrace-base-', ['louvre', 'glacis', 'glacis'], 'entrance')],
         'floor': [run('terrace-', [*bays, 'core'] if i % 2 else bays) for i, bays in enumerate(storeys(terraces))]},
        {'name': 'exoskeleton', 'roof': 'edge', **common,
         'fittings': [{'vent-cowl': [[-7, 8, 0]], 'hatch': [[8, -7, 0]]}, {'plant': [[0, 2, 0]]}, {'vent-cowl': [[6, 6, 90], [-8, -7, 0]]}, {'hatch': [[0, 0, 0]]},
                      {'plant': [[-4, -5, 90]], 'vent-cowl': [[9, 9, 0]]}, {}],
         'base': [run('frame-base-', ['plinth', 'brace-up', 'plinth', 'brace-down'], 'vault'), run('frame-base-', ['brace-down', 'plinth', 'brace-up', 'plinth'], 'vault')],
         'floor': [run('frame-', bays) for bays in storeys(frames)]},
    ]
    return pieces, roofs, variants


KITS = {'civilian': civilian, 'castle-brian': castle_brian}


def build(weight):
    """Writes a weight's kit: a designers' building dressed, or one of the kits modelled here."""
    name = f'building-{weight}'
    k.KITS[name] = designed(weight) if weight in LOOKS else KITS[weight]()
    # Walls take a building's tint; frames, slab edges, trims, glass, doors and roofs keep theirs.
    k.build(name, folder='standard', painted=lambda obj: obj.name.startswith('wall'))


if __name__ == '__main__' and '--' in sys.argv:
    for weight in sys.argv[sys.argv.index('--')+1:] or [*LOOKS, *KITS]:
        build(weight)
