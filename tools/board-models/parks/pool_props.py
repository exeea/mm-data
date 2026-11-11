"""The swimming pools, their deck slabs and the garden ponds. A pool is a white stone coping round tiled walls and
water, on a flagged deck where it has one, with its ladders and lane ropes (loungers and parasols stand on the wide deck slabs); a pond is a turf bank
round still water, with rocks, reeds and lilies. The pools keep the outlines they were first made to
(pool_outlines.json, from pool_outlines.py), which the layouts that place them rely on, and their colour slots.

Run: blender -b --factory-startup --python pool_props.py -- [name ...]   (none: all)
Writes data/models/board/scenery/pools/<name>.glb and scenery/parks/pond-<n>.glb, two levels of detail.
"""
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import park_props as pp
from park_props import PAINT, TAU, add, at, box, f, hk, kb, la, shared, u
from glb_geometry import write_glb

OUTLINES = json.loads((HERE/'pool_outlines.json').read_text(encoding='utf-8'))
STONE = u.STONE  # White stone: the coping.
PAVERS = hk.STONE  # Limestone flags: a deck.
MUD = 'terrain/surfaces/biome-mud'
COPING, TILE, FLOOR, DECK, WATER = (1, .985, .96), (.74, .88, .92), (.62, .84, .90), pp.FLAGS, (1, 1, 1)
POND_WATER, BANK = (.34, .46, .36), (.72, .84, .56)
TOP, LEVEL, DECK_TOP = 1.5, 1.1, .5  # A pool's coping, its water and its deck, above the ground.
# The colour slots an editor recolours a pool by: the parts by name, and each one's own colour.
SLOTS = (('Wall', TILE), ('Coping', COPING), ('Deck', DECK), ('Water', WATER))


def centroid(ring):
    return sum(p[0] for p in ring)/len(ring), sum(p[1] for p in ring)/len(ring)


def inward(ring, i):
    """The unit direction into a ring at its i-th corner."""
    (ax, ay), (bx, by), (cx, cy) = ring[i-1], ring[i], ring[(i+1) % len(ring)]
    nx, ny = -(cy-ay), cx-ax
    length = math.hypot(nx, ny) or 1
    return nx/length, ny/length


def basin(coping, wide=2.0):
    """A pool's stone and water inside its coping's outer line. Gives the water's edge."""
    edge = f.inset(coping, wide)
    f.wall_ring('pool coping', coping, 0, TOP, STONE, COPING)
    pp.ring_band('pool coping', edge, coping, TOP, STONE, COPING)
    for i in range(len(edge)):  # The tiled wall, down to the water.
        j = (i+1) % len(edge)
        la.facing('pool wall', STONE, TILE, [(*edge[j], LEVEL-.4), (*edge[i], LEVEL-.4), (*edge[i], TOP), (*edge[j], TOP)], (*f.outward(edge[j], edge[i]), 0))
    f.cap('pool wall', edge, LEVEL-.4, STONE, FLOOR)
    f.cap('pool water', edge, LEVEL, la.WATER, WATER)
    return edge


def deck(outline):
    f.cap('pool deck', outline, DECK_TOP, PAVERS, DECK)
    f.wall_ring('pool deck', outline, 0, DECK_TOP, PAVERS, DECK)


def ladder(edge, i):
    """A pool ladder at the water's edge: two steel rails over the coping."""
    (x, y), (nx, ny) = edge[i], inward(edge, i)
    tx, ty = -ny, nx
    for side in (-.55, .55):
        px, py = x+tx*side, y+ty*side
        u.tube('ladder', [(px+nx*.5, py+ny*.5, LEVEL-.3), (px+nx*.5, py+ny*.5, TOP+1.7), (px-nx*1.3, py-ny*1.3, TOP+1.7), (px-nx*1.3, py-ny*1.3, TOP)],
               .1, u.RAIL, u.RAIL_TINT, sides=4)['detail'] = True


def ropes(x0, x1, y0, y1, count):
    """Lane ropes along y: floats in red and white."""
    for lane in range(1, count):
        x = x0+(x1-x0)*lane/count
        steps = max(2, round((y1-y0)/3.2))
        for k in range(steps):
            a, b = y0+(y1-y0)*k/steps, y0+(y1-y0)*(k+1)/steps
            add('lane rope', PAINT, (.85, .20, .18) if k % 2 else (.95, .95, .93), [(x-.14, a, LEVEL+.05), (x+.14, a, LEVEL+.05), (x+.14, b, LEVEL+.05), (x-.14, b, LEVEL+.05)],
                [(0, 1, 2, 3)], detail=True)


def lounger(x, y, a, colour):
    """A sun lounger: a white frame, a cushion, its back raised."""
    box('lounger', x, y, a, -1.0, 1.0, -3.0, 1.4, DECK_TOP+.5, DECK_TOP+.72, PAINT, (.93, .93, .91), detail=True)
    box('lounger cushion', x, y, a, -.85, .85, -2.9, 1.3, DECK_TOP+.72, DECK_TOP+.9, PAINT, colour, omit='b', detail=True)
    v = [(*at(x, y, a, px, py), z) for px, py, z in ((-.85, 1.4, DECK_TOP+.72), (.85, 1.4, DECK_TOP+.72), (.85, 3.0, DECK_TOP+1.9), (-.85, 3.0, DECK_TOP+1.9))]
    add('lounger cushion', PAINT, colour, v, [(0, 1, 2, 3), (3, 2, 1, 0)], detail=True)


def parasol(x, y, colour):
    la.turned('parasol pole', [(.12, DECK_TOP), (.12, DECK_TOP+6.6)], 4, PAINT, (.90, .90, .88), x, y)
    la.turned('parasol', [(4.0, DECK_TOP+5.6), (0, DECK_TOP+7.0)], 8, PAINT, colour, x, y)
    f.cap('parasol', f.regular(x, y, 4.0, 8)[::-1], DECK_TOP+5.6, PAINT, tuple(v*.8 for v in colour))


def pool(name, lanes=0, ladders=2, rng=None):
    entry = OUTLINES[name]
    coping = entry['coping']
    if 'deck' in entry:
        deck(entry['deck'])
    edge = basin(coping)
    for k in range(ladders):
        ladder(edge, (len(edge)*k)//ladders+len(edge)//(4*ladders)*0)
    if lanes:
        xs, ys = [p[0] for p in edge], [p[1] for p in edge]
        ropes(min(xs), max(xs), min(ys)+.4, max(ys)-.4, lanes)


def slab(name, rng):
    """A pool deck on its own: flags to its edge, and its planters."""
    entry = OUTLINES[name]
    deck(entry['land@0.3'])
    if 'land@1.6' in entry:  # The round deck's two planters, where they always stood.
        for x, y in ((-1.2, 18.95), (16.35, 2.2)):
            la.ring_wall('planter', f.regular(x, y, 4.4, 12), DECK_TOP, DECK_TOP+1.5, STONE, COPING, thick=.7)
            f.cap('planter soil', f.regular(x, y, 3.7, 12), DECK_TOP+1.1, pp.MULCH, (1, 1, 1))
            pp.shrub(x, y, DECK_TOP+1.1, 4.6, rng)
        pp.flush_cards(False)
    else:  # The long deck: loungers down both sides of its pools, a parasol at each end of a row.
        colour = (.24, .46, .66)
        for side in (-1, 1):
            for y in (-3.4, 0, 3.4, 10.2, 13.6, 17.0):
                lounger(side*13.6, y, 90*side, colour)
            for y in (-7.4, 6.8, 21.0):
                parasol(side*13.9, y, colour)


def pond(source, rng, jetty=False):
    """A garden pond in the outline of a pool: a turf bank up to its lip, a muddy shore down to still water, rocks on
    the lip, reeds and lilies in the shallows."""
    lip = OUTLINES[source]['coping']
    foot, shore = f.inset(lip, -3.4), f.inset(lip, 2.0)
    f.frustum('pond bank', foot, 0, lip, .9, u.TURF, BANK)
    f.frustum('pond shore', lip, .9, shore, .42, MUD, (.86, .80, .70))
    f.cap('pond bed', shore, .42, MUD, (.62, .60, .50))
    f.cap('pond water', shore, .5, la.WATER, POND_WATER)
    cx, cy = centroid(shore)
    for i in range(0, len(lip), max(1, len(lip)//9)):
        x, y = lip[i]
        la.rock(x+rng.uniform(-.6, .6), y+rng.uniform(-.6, .6), rng.uniform(1.0, 2.1), rng)
    for i in rng.sample(range(len(shore)), 4):
        x, y = shore[i]
        nx, ny = inward(shore, i)
        for _ in range(4):
            d, s = rng.uniform(.6, 3.2), rng.uniform(-2.2, 2.2)
            u.upright(u.SPIKE, (.74, .84, .56), x+nx*d-ny*s, y+ny*d+nx*s, .4, 2.4, rng.uniform(3.6, 5.2), rng.uniform(0, TAU))
    for _ in range(10):
        i = rng.randrange(len(shore))
        t = rng.uniform(.25, .8)
        x, y = shore[i][0]+(cx-shore[i][0])*t, shore[i][1]+(cy-shore[i][1])*t
        spin = rng.uniform(0, TAU)
        add('lily pad', PAINT, (.26, .42, .22), [(x+1.0*math.cos(TAU*k/6+spin), y+1.0*math.sin(TAU*k/6+spin), .53) for k in range(5)]+[(x, y, .53)],
            [(k, k+1, 5) for k in range(4)], detail=True)
        if rng.random() < .5:
            u.tilted(u.FLOWER, (1, .96, .98), x+.4, y+.3, .5, 1.2, 1.2, spin, math.radians(80))
    pp.flush_cards(True)
    if jetty:  # A timber jetty from the bank out over the water.
        i = max(range(len(lip)), key=lambda k: lip[k][1])
        x, y = lip[i]
        a = math.degrees(math.atan2(cy-y, cx-x))-90
        box('jetty', x, y, a, -1.5, 1.5, -1.5, 9.0, 1.05, 1.25, PAINT, pp.TIMBER_PALE, omit='')
        for px, py in ((-1.3, 3.0), (1.3, 3.0), (-1.3, 8.6), (1.3, 8.6)):
            la.turned('jetty post', [(.22, .3), (.22, 1.9)], 5, PAINT, pp.TIMBER, *at(x, y, a, px, py))


PROPS = {'freeform': lambda rng: pool('freeform', rng=rng), 'rectangular-no-deck': lambda rng: pool('rectangular-no-deck', lanes=4, rng=rng),
         'rectangular': lambda rng: pool('rectangular', lanes=4, rng=rng), 'round-no-deck': lambda rng: pool('round-no-deck', rng=rng),
         'sport-1-main': lambda rng: pool('sport-1-main', lanes=3, rng=rng), 'sport-1-wading': lambda rng: pool('sport-1-wading', ladders=1, rng=rng),
         'sport-2': lambda rng: pool('sport-2', rng=rng), 'sport-3-main': lambda rng: pool('sport-3-main', rng=rng),
         'sport-3-wading': lambda rng: pool('sport-3-wading', ladders=1, rng=rng), 'sport-4': lambda rng: pool('sport-4', rng=rng),
         'sport-5': lambda rng: pool('sport-5', lanes=4, rng=rng), 'sport-1-deck': lambda rng: slab('sport-1-deck', rng),
         'sport-3-deck': lambda rng: slab('sport-3-deck', rng), 'pond-1': lambda rng: pond('freeform', rng),
         'pond-2': lambda rng: pond('sport-2', rng, jetty=True), 'pond-4': lambda rng: pond('sport-4', rng)}


def colour_slots(level):
    """Marks a pool's parts for recolouring: each vertex's slot by its material, the white stone's by its tint (the
    coping's own, or the tiles')."""
    sizes = {'POSITION': 3, 'NORMAL': 3, 'COLOR': 4, 'TEXCOORD0': 2}
    material = {part['meshpartid']: part['materialid'] for node in level['nodes'] for part in node.get('parts', ())}
    for mesh in level['meshes']:
        stride = sum(sizes[name] for name in mesh['attributes'])
        colour = sum(sizes[name] for name in mesh['attributes'][:mesh['attributes'].index('COLOR')])
        slots = [0]*(len(mesh['vertices'])//stride)
        for part in mesh['parts']:
            key = material.get(part['id'], '')
            for index in part['indices']:
                red, _, blue = mesh['vertices'][index*stride+colour:index*stride+colour+3]
                slots[index] = 4 if key == la.WATER else 3 if key == PAVERS else 0 if key != STONE else 1 if blue > red*1.05 else 2
        mesh['slots'] = slots


def build(name):
    """Writes one prop in its two levels."""
    kb.build_scene(name, lambda: PROPS[name](random.Random(sum(map(ord, 'pools'+name)))), lambda obj: None, lambda obj: False)
    levels = {i: shared.export_model(shared.objects, f'{name}-lod{i}', level=i, exact=True) for i in (0, 1)}
    for level in levels.values():
        for material in level['materials']:
            for texture in material.get('textures', ()):
                texture['filename'] = texture['filename'].replace('../../board/textures/', '../../textures/')
    triangles = [sum(len(part['indices'])//3 for mesh in level['meshes'] for part in mesh['parts']) for level in levels.values()]
    assert triangles[0] <= pp.LIMITS['hex'], (name, triangles)
    extras = None
    if not name.startswith('pond') and name not in ('sport-1-deck', 'sport-3-deck'):
        for level in levels.values():
            colour_slots(level)
        extras = {'mmColourSlots': [{'name': slot, 'colour': '#%02x%02x%02x' % tuple(round(255*v) for v in colour), 'presets': []}
                                    for slot, colour in SLOTS]}
    if '--debug' in sys.argv:
        print('DEBUG', name, sorted({part['materialid'] for node in levels[0]['nodes'] for part in node.get('parts', ())}),
              [sorted(set(mesh.get('slots', ()))) for mesh in levels[0]['meshes']])
    folder = Path(sys.argv[sys.argv.index('--out')+1]) if '--out' in sys.argv else la.SCENERY/('parks' if name.startswith('pond') else 'pools')
    folder.mkdir(parents=True, exist_ok=True)
    write_glb(folder/(name+'.glb'), levels=levels, **({'extras': extras} if extras else {}))
    print('RESULT', name, 'triangles', *triangles)


if __name__ == '__main__' and '--' in sys.argv:
    wanted = [arg for arg in sys.argv[sys.argv.index('--')+1:] if arg in PROPS]
    for name in PROPS:
        if not wanted or name in wanted:
            build(name)
