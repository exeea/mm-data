"""A bays kit's far level: a closed outer hull, each wall piece one face, textured from the kit's far atlas.

Run after the script that builds the kit (models/buildings/README.md, Kits), with the system Python (numpy, Pillow, SciPy):
    python far_levels.py building-hard [civic/civic ...]   (a kit of standard/, or <folder>/<kit>)
then export the far material: python ../materials/export.py structures/buildings/<kit>-far/<kit>-far.ptex

A kit's pieces GLB keeps its near level (lod0) and takes a far level (lod1) of the same pieces: every wall piece (a bay, an
entrance, an end, a joint, a corner's facet) becomes one face on its storey's outer face (planes: upright, or sloped where
the storey is battered), with no wall thickness, no reveals, frames, sills or mullions; a roof's edge a profile of at most
SEGMENTS faces round its section (sloped where an eave or a mansard slopes), the face towards the roof and a lid under
it; a turret or a spire standing out of a face a loft of octagonal frusta (lofts; on a rounded corner's piece shaped as
the kit stretches it, stretches); a roof fitting one box, or a loft where a box does not fit it; a face far out of its
wall line a second one on it behind (BACKED); a joint's fill its near mesh. Shapes follow solid surfaces, cutouts drawn
on them. Where a storey stands further out than the one on it, a ledge closes its top. A lit pane of a wall or roof edge
piece (a window, a sign) stands on its far surface as geometry in its own near material (panes), so it lights as the near
one does. A far face shows what the near piece shows through it: its atlas region is baked by rays along the iso
camera's view (BAKE_ELEVATION), head on, so a slab's top and a recessed window read where they do near, its albedo dimmed
by the sky the piece hides (daylight); it has no glow where a pane stands. The atlas (sources of
tools/materials/structures/buildings/<kit>-far) holds the albedo, its building paint (the near level's #paint surfaces,
which a building's tint colours) as a mask, the night glow of what lights without a pane, roughness and metallic, and
normals. The kit's JSON says `hull` (BayKit.Spec#hull). Far levels past it repeat it: the GLB has two levels.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import importlib.util  # noqa: E402

import kit_json  # noqa: E402
from glb_geometry import linear, read_glb, write_glb  # noqa: E402

# The .tres reader alone: its package needs Blender.
_tres = importlib.util.spec_from_file_location('tres', HERE.parent/'blender/mm_materials/tres.py')
read_material = importlib.util.module_from_spec(_tres)
_tres.loader.exec_module(read_material)
read_material = read_material.read_material

ROOT = HERE.parents[1]
DATA = ROOT/'data'
TEXTURES = DATA/'models/board/textures'
MATERIALS = ROOT/'tools/materials/structures/buildings'
LEVEL = 18.0  # A storey's height.
ROOF_INSET = .12  # How far inside its wall line the kit lays a roof's edge (KitOutline.ROOF_INSET).
BAKE_ELEVATION = math.radians(90-54.73561)  # The iso camera's elevation over the horizon (BoardCamera.ISOMETRIC_TILT).
# Daylight a far face no longer shades itself with: what the near piece seen through it hides of the sky (SKY, directions
# over the horizon) dims its albedo by DIRECT, the share of a lit surface's light the sun gives, as the near level's sun
# shadows dim it on average.
SKY = [np.array([math.cos(math.radians(e))*math.cos(math.radians(a)), math.cos(math.radians(e))*math.sin(math.radians(a)),
                 math.sin(math.radians(e))]) for e in (25, 50, 75) for a in range(0, 360, 45)]
DIRECT = .6
# A lit pane at most PANE_DEPTH inside its piece's far surface (a window in its reveal, behind a terrace's rail) stands
# PANE_LIFT outside it (panes), drawn in to what the iso camera sees of it past what stands before it near: from the
# PANE_VIEWS, the azimuths off a face's normal the camera sees a hex's walls at (15, 45 or 75 degrees; a Square
# footprint's 45), each weighted by the screen a face so seen takes. One it sees less than PANE_SHARE of stays in the atlas.
PANE_DEPTH = 8.0
PANE_LIFT = .05
PANE_VIEWS = tuple((math.radians(side*a), math.cos(math.radians(a))) for a in (15, 45, 75) for side in (-1, 1))
PANE_SHARE = .1
PANE_CLEAR = .25  # A pane seen head on less than this past what stands before it (a column; not a grille) has none.
RELIEF_DEPTH = 2.0  # A wall piece whose lit glass lies this far behind its far face (between fins, in deep reveals)...
RELIEF_TRIS = 120  # ...and that has no more triangles than this keeps its near mesh at the far level.
EDGE_TOP = 1.5  # How far under a roof edge's top its far profile's top reaches in (edge_chain).
FITTING_BOX = .6  # A fitting filling this much of its box, from above and the front, is a box; any other a loft of
FITTING_BANDS = 2  # at most this many frusta.
PLANE_SHARE = .05  # A piece's plane: the outermost depth at least this share of its front lies at or in front of.
LEDGE = .5  # A storey standing out less than this leaves no ledge: the storeys on it stand on its face.
BATTER = 1.0  # A storey whose face leans out this much over its height is battered: its far face slopes.
BACKED = 3.0  # A face standing further out of its wall line than this has the same face on the wall line behind it.
LID = .05  # How far under the storey's top a roof edge's lid lies.
SEGMENTS = 3  # A roof edge's far profile takes at most this many steps,
SLIVER = .5  # fewer where dropping one adds less than this area (square units of its section),
PLUMB = math.radians(6)  # and one within this of upright or level is made so.
PROTRUDE = 1.5  # Geometry this far out of a piece's far face...
TALL = 9.0  # ...and this tall (a turret, a spire), filling LOFT_FILL of its bounds, is drawn as a loft of its own
LOFT_FILL = .5  # rather than on the face.
LOFT_BANDS = 3  # A loft's frusta at most, one over another...
LOFT_FIT = .4  # ...split while the geometry stands this far out of a straight one.
# A loft's sides face these eight directions in plan.
LOFT_DIRECTIONS = np.array([[math.cos(a), math.sin(a)] for a in np.arange(8)*math.pi/4])
EXTEND = 10.0  # How far past a rounded corner's facet its piece goes on, for the mitres to trim (KitOutline.EXTEND).
SHARPEN = (1.5, .75)  # The atlas albedo's unsharp mask (atlas): its amount, and its radius in units.
# Each kit's atlas albedo gain (linear; atlas): the near level's mean luminance over the far level's where the switch
# changes pixels, by day, at a hex 88 pixels wide (the switch), the five buildings and views of work/far-kits' captures
# (calib.py) of the atlas baked without it.
TONE = {'civic': .972, 'utopia': .951, 'frontier': .910, 'imperial': .866, 'heritage': .890, 'hangar-light': .911,
        'hangar-medium': .923, 'hangar-heavy': .941, 'hangar-hard': .974, 'fortress-light': .916, 'building-light': .876,
        'building-medium': .960, 'building-heavy': .948, 'building-hard': .945, 'building-civilian': .978,
        'building-castle-brian': .875}
# Roof pieces a kit's far level keeps at their near meshes, where the far faces lose what the roof reads from (the
# user's choice, 2026-11-16, from work/far-kits' sheets): 'fittings' the roof fittings (units, tanks, masts), 'roof' also
# every roof edge piece (planting, railings, eaves, dormers).
NEAR_ROOF = {'civic': 'fittings', 'utopia': 'roof', 'frontier': 'roof', 'imperial': 'roof', 'heritage': 'roof'}
# A kit's lit panes (panes) grown this share of the way from their iso-seen size to their windows' full size (negative:
# shrunk further), so its far level lights what the near shows at the switch: lit window pixels far/near 0.97 and 1.00
# at a hex 88 pixels wide by night (work/far-kits litcount.py; 0.55 and 1.20 without).
PANE_GROW = {'building-light': .65, 'building-civilian': -.4}
# Kits whose lit glass is under a pixel wide at the switch (fortress-light's slits behind their bars): its lit pixels are
# sub-pixel noise, so the far level has no panes; the near's glass glows in the far atlas as the face's own texels
# (filtered by the atlas's mips: steady on a pan, no triangles), times this share (lit energy as the supersampled near's),
# in this colour (linear: the supersampled near's mean lit colour, measured; its glass's light saturates to pale yellow),
# falling with the view as the near's slits do: emission x clamp(scale (N.V - offset), 0, 1), N.V the far face's normal on
# the view (the far material's metadata/mmEmissionView). Share and pair fitted to the supersampled near's lit energy at a
# hex's six rotations (work/far-kits glowcheck4.py, 2026-11-19).
ATLAS_GLOW = {'fortress-light': (.62, (1, .965, .40), (1.65, .264))}
DENSITY = 2  # Atlas texels a unit: the far level shows at most 1.06 pixels a unit (a hex 88 pixels wide).
SAMPLES = 3  # Rays a texel, along each side.
PAD = 4  # Texels round each region, its edge texels repeated.
ATLAS = 512
ALIGN = 8  # Regions start and end on multiples of this, so the first mip levels stay within them.


# -- The near level --------------------------------------------------------------------------------------------------

def near_pieces(glb):
    """The near level's pieces: name -> triangles (N,3,3), their normals (N,3,3), colours (N,3,4), UVs (N,3,2), materials."""
    model = read_glb(glb, 0)
    # Level groups named after another stem (hangar_light_a-pieces-lod0): the game takes any name ending in its level.
    roots = [node for node in model['nodes'] if not node['parts'] and node['children'] and node['id'].rsplit('-lod', 1)[-1].isdigit()]
    if roots:
        model['nodes'] = next(node for node in roots if node['id'].endswith('-lod0'))['children']
    # The file's materials of this level alone: a far level written before has its own.
    used = {ref['materialid'] for node in model['nodes'] for ref in node['parts']}
    model['materials'] = [m for m in model['materials'] if m['id'] in used]
    mesh = model['meshes'][0]
    vertices = np.asarray(mesh['vertices'], dtype=np.float64).reshape(-1, 12)
    parts = {p['id']: np.asarray(p['indices'], dtype=np.int64).reshape(-1, 3) for p in mesh['parts']}
    result = {}
    for node in model['nodes']:
        indices, materials = [], []
        for ref in node['parts']:
            indices.append(parts[ref['meshpartid']])
            materials += [ref['materialid']]*len(parts[ref['meshpartid']])
        if indices:
            tri = vertices[np.concatenate(indices)]
            result[node['id'].rsplit('-lod', 1)[0]] = {'pos': tri[..., 0:3], 'nrm': tri[..., 3:6], 'col': tri[..., 6:10],
                                                       'uv': tri[..., 10:12], 'mat': np.array(materials)}
    return model, result


def layout(spec):
    """What the kit lays where: wall pieces by variant and role (name -> its length along the wall), the roofs' edge
    pieces with their deck heights and surfaces, the roofs' seams (laid along the joints between modules, not on an
    edge), the pieces laid at rounded corners, the joints' fills, the fittings, each piece's materials textured along the wall's line (its run's planar), and each variant's
    sidewalk material (None without one)."""
    shared = spec.get('shared', {})
    walls, fittings, planar, sidewalks, seams, corners, fills = {}, set(), {}, {}, set(), set(), set()

    def runs(entries, defaults, into):
        for entry in entries:
            run = {**defaults, **entry}
            bay = run.get('bay', shared.get('bay'))
            laid = {name: bay for name in run.get('bays', []) + ([run['entrance']] if run.get('entrance') else [])}
            for key in ('ends', 'under', 'round', 'shallow', 'seam'):
                if run.get(key):
                    laid[run[key]['piece']] = run[key]['length']
            if run.get('seam'):
                seams.add(run['seam']['piece'])
            corners.update(run[key]['piece'] for key in ('round', 'shallow') if run.get(key))
            if run.get('joints'):
                # A module's joint pieces are wall pieces of their length; their fills (BayKit#fill) stand inside the hull.
                for end in ('start', 'end'):
                    laid[run['joints'][end]] = run['joints']['length']
                    fills.add(run['joints'][end]+'-fill')
            into.update(laid)
            for name in laid:
                planar.setdefault(name, {}).update({**shared.get('planar', {}), **run.get('planar', {})})

    for variant in spec['variants']:
        name = variant.get('name', 'default')
        sidewalk = variant.get('sidewalk', shared.get('sidewalk'))
        sidewalks[name] = sidewalk['material'] if sidewalk else None
        for role in ('base', 'floor', 'top'):
            if role in variant:
                runs(variant[role], shared.get(role, {}), walls.setdefault((name, role), {}))
        layouts = variant.get('fittings', shared.get('fittings')) or []
        for options in (layouts.get('square', []) + layouts.get('angled', []) if isinstance(layouts, dict) else layouts):
            fittings.update(options)
    roofs = {}
    for name, roof in spec['roofs'].items():
        pieces = {}
        runs(roof.get('runs', []), {}, pieces)
        # A vaulted roof's sheeting takes its vault's tint (BayKit.Vault): its deck as the rays around an edge meet it.
        tint = roof.get('vault', {}).get('tint')
        roofs[name] = (pieces, roof['heights'][0], roof['material'], roof['repeat'],
                       tuple(int(tint[k:k+2], 16)/255 for k in (1, 3, 5)) if tint else None)
    return walls, roofs, seams, corners, fills, fittings, planar, sidewalks


def stretches(spec):
    """How much a rounded corner's pieces stretch along their wall where the kit lays them (BayKit#facade): over a facet
    of the corner's arc and EXTEND past each end. A run's round piece with a shallow one beside it goes on a Square
    footprint's corners, which turn a right angle; any other on a hex's, which turn 60 degrees."""
    shared, result = spec.get('shared', {}), {}

    def add(run, radius, segments):
        for key in ('round', 'shallow'):
            if run.get(key):
                turn = math.radians(90 if key == 'round' and run.get('shallow') else 60)
                facet = 2*radius*math.sin(turn/2/segments)
                result.setdefault(run[key]['piece'], (facet+2*EXTEND)/run[key]['length'])

    for variant in spec['variants']:
        radius = variant.get('cornerRadius', shared.get('cornerRadius', 0))
        segments = max(1, variant.get('cornerSegments', shared.get('cornerSegments', 1)))
        if radius <= 0:
            continue
        for role in ('base', 'floor', 'top'):
            for entry in variant.get(role, []):
                add({**shared.get(role, {}), **entry}, radius, segments)
        for run in spec['roofs'].get(variant.get('roof'), {}).get('runs', []):
            add(run, radius, segments)
    return result


def front(piece, length):
    """The piece's front seen straight on, 4 samples a unit over its length and its height: the depth (y) at each sample
    (inf where nothing is, row 0 at the top), and the height of the grid's bottom."""
    z0, z1 = float(piece['pos'][..., 2].min()), float(piece['pos'][..., 2].max())
    index, depth, _ = raster(piece['pos'][..., [0, 2]], piece['pos'][..., 1], (0, z0), int(length*4),
                             max(1, int(np.ceil((z1-z0)*4))), 4)
    return np.where(index >= 0, depth, np.inf), z0


def outermost(piece, length):
    """A piece's own plane: the outermost depth PLANE_SHARE of its front reaches."""
    depth, _ = front(piece, length)
    return float(np.quantile(depth[np.isfinite(depth)], PLANE_SHARE))


def rows(piece, length, share):
    """A piece's front by rows of 1/4 unit, bottom first: each row's bottom height, the depth the outermost share of its
    samples reach (nan in an empty row), and the share of its length it covers."""
    depth, z0 = front(piece, length)
    depth = depth[::-1]
    hit = np.isfinite(depth)
    out = np.array([np.quantile(row[seen], share) if seen.any() else np.nan for row, seen in zip(depth, hit)])
    return z0+np.arange(len(depth))/4, out, hit.mean(axis=1)


def dense(near, pieces, grid, share):
    """The pieces' outer depth (rows) on the rows of grid (their bottoms), the median of those pieces that cover at least
    half their length there, where at least half of them do (nan elsewhere)."""
    per = []
    for name, length in pieces.items():
        bottoms, out, covered_ = rows(near[name], length, share)
        index = np.round((grid-bottoms[0])*4).astype(int)
        valid = (index >= 0) & (index < len(out))
        values = np.full(len(grid), np.nan)
        values[valid] = np.where(covered_[index[valid]] >= .5, out[index[valid]], np.nan)
        per.append(values)
    per = np.array(per)
    counted = np.isfinite(per).sum(axis=0)
    result = np.full(len(grid), np.nan)
    for k in np.nonzero(2*counted >= len(pieces))[0]:
        result[k] = float(np.median(per[np.isfinite(per[:, k]), k]))
    return result


def storey_line(near, pieces):
    """A storey's face, its y at its bottom and at its top: on the median of its pieces' own outermost planes (a porch or
    a canopy in one bay leaves it where the other bays stand); sloped where the rows of its pieces lean out BATTER or more
    over the storey, as a battered plinth does, out to the PLANE_SHARE of them."""
    plane = float(np.median([outermost(near[name], length) for name, length in pieces.items()]))
    grid = np.arange(0, LEVEL, .25)
    depth = dense(near, pieces, grid, PLANE_SHARE)
    valid = np.isfinite(depth)
    if valid.sum() > len(grid)/2:
        z = grid[valid]+.125
        slope, at = np.polyfit(z, depth[valid], 1)
        residual = depth[valid]-(at+slope*z)
        if abs(slope)*LEVEL >= BATTER and np.quantile(np.abs(residual), .9) <= .5:
            shift = float(np.quantile(residual, PLANE_SHARE))
            return at+shift, at+slope*LEVEL+shift
    return plane, plane


def hull_chain(points):
    """The outer chain of the points' convex hull in (y, z): from its lowest point (the outermost of them) up its outer side
    and over its top to its highest (the innermost of them), each step facing out or up."""
    from scipy.spatial import ConvexHull
    points = np.unique(np.round(np.asarray(points, dtype=np.float64), 4), axis=0)
    hull = points[ConvexHull(points).vertices]  # counter-clockwise, y right and z up
    start = min(range(len(hull)), key=lambda i: (hull[i][1], hull[i][0]))
    end = max(range(len(hull)), key=lambda i: (hull[i][1], hull[i][0]))
    chain = [hull[start]]
    i = start
    while i != end:
        i = (i-1) % len(hull)  # clockwise: up the outer side first
        chain.append(hull[i])
    return [tuple(map(float, p)) for p in chain]


def simplified(chain, segments):
    """chain with at most segments steps, still enclosing it: the step whose neighbours, run on to meet, add the least
    area goes, while one may (its first and last steps stay), and while that adds under SLIVER; then a step within PLUMB of
    upright or level is made so, its inner end moved out to its outer one's line."""
    chain = [np.array(p) for p in chain]
    while True:
        best = None
        for i in range(1, len(chain)-2):
            a, b, c, d = chain[i-1], chain[i], chain[i+1], chain[i+2]
            u, v = b-a, d-c
            cross = u[0]*v[1]-u[1]*v[0]
            if abs(cross) < 1e-9:
                continue
            t = ((c[0]-a[0])*v[1]-(c[1]-a[1])*v[0])/cross
            s = ((c[0]-a[0])*u[1]-(c[1]-a[1])*u[0])/cross
            if t < 1 or s > 0:
                continue  # the steps beside it meet behind it: running them on would cut into the chain
            meet = a+t*u
            area = abs((meet[0]-b[0])*(c[1]-b[1])-(meet[1]-b[1])*(c[0]-b[0]))/2
            if best is None or area < best[0]:
                best = (area, i, meet)
        if best is None or len(chain)-1 <= segments and best[0] >= SLIVER:
            break
        _, i, meet = best
        chain[i:i+2] = [meet]
    for i in range(len(chain)-1):
        a, b = chain[i], chain[i+1]
        dy, dz = b-a
        if abs(dy) <= math.tan(PLUMB)*abs(dz):
            a[0] = b[0] = min(a[0], b[0])  # upright, at its outer side (the chain runs up its outer side)
        elif abs(dz) <= math.tan(PLUMB)*abs(dy):
            a[1] = b[1] = max(a[1], b[1])  # level, at its top
    return [tuple(map(float, p)) for p in chain]


def edge_chain(near, pieces, foot=None):
    """A roof's edge pieces' far profile in (y, z): the hull of their dense rows' middle depth (dense: a dormer standing
    out of a mansard, as a porch out of a wall, is drawn on it) and of the point their top reaches in to (the pieces'
    furthest point within EDGE_TOP of it: a deck strip lower down is not the edge), at most SEGMENTS steps; with foot,
    where it stands back from foot at the storey's top, a step at its bottom out to foot closes the storey under it."""
    lows = min(float(near[name]['pos'][..., 2].min()) for name in pieces)
    highs = max(float(near[name]['pos'][..., 2].max()) for name in pieces)
    grid = lows+np.arange(max(1, int(np.ceil((highs-lows)*4))))/4
    depth = dense(near, pieces, grid, .5)
    valid = np.isfinite(depth)
    if not valid.any():
        raise ValueError(f'no dense rows in the roof edge pieces {sorted(pieces)}')
    points = [(y, z) for y, z in zip(depth[valid], grid[valid])]+[(y, z+.25) for y, z in zip(depth[valid], grid[valid])]
    top = float(grid[valid].max()+.25)
    inner = []
    for name in pieces:
        pos = near[name]['pos'].reshape(-1, 3)
        upper = pos[pos[:, 2] >= top-EDGE_TOP]
        inner.append(float((upper if len(upper) else pos)[:, 1].max()))
    points.append((max(float(np.median(inner)), max(y for y, _ in points)), top))
    chain = simplified(hull_chain(points), SEGMENTS)
    if foot is not None:
        # Where it stands back from foot at the storey's top (or its own foot, higher up): a step out from there, what
        # it shows under that within the storey.
        z0 = max(0.0, chain[0][1])
        y0 = min((a[0]+(b[0]-a[0])*(z0-a[1])/(b[1]-a[1]) if b[1] != a[1] else min(a[0], b[0])
                  for a, b in zip(chain, chain[1:]) if min(a[1], b[1]) <= z0 <= max(a[1], b[1])), default=-np.inf)
        if y0 > foot+.05:
            chain = [(foot, z0), (y0, z0)]+[p for p in chain if p[1] > z0+1e-6]
    return chain


def planes(near, walls, roofs, seams, corners, spec):
    """Each wall piece's face (y at its storey's bottom and top: storey_line), storeys that share a piece on one face (the
    outermost of theirs at each end), a storey on the one under it where it stands back from it by less than LEDGE; how
    far in each wall piece's top closes a step to the storey on it (no further than its own face where none); and each
    roof edge piece's profile (edge_chain): a roof's, and those of roofs sharing a piece, one profile of their bays (a
    corner piece's turret is a loft of its own) out to the storeys under them, a seam its own."""
    lines = {key: storey_line(near, pieces) for key, pieces in walls.items()}
    uppers = {'base': ('floor', 'top'), 'floor': ('top',), 'top': ()}

    def united():
        changed = False
        for a in lines:
            for b in lines:
                if a < b and set(walls[a]) & set(walls[b]) and lines[a] != lines[b]:
                    lines[a] = lines[b] = (min(lines[a][0], lines[b][0]), min(lines[a][1], lines[b][1]))
                    changed = True
        return changed

    for _ in range(20):
        changed = united()
        for (variant, role), line in list(lines.items()):
            for upper in uppers[role]:
                above = lines.get((variant, upper))
                if above is not None and 0 < above[0]-line[1] < LEDGE:
                    step = above[0]-line[1]
                    lines[variant, upper] = (above[0]-step, above[1]-step)
                    changed = True
        if not changed:
            break
    wall, ledge = {}, {}
    for (variant, role), pieces in walls.items():
        line = lines[variant, role]
        inner = max([lines[variant, upper][0] for upper in uppers[role] if (variant, upper) in lines]+[line[1]])
        for name in pieces:
            wall[name] = line
            ledge[name] = max(ledge.get(name, line[1]), inner)
    shared = spec.get('shared', {})
    feet = {}
    for variant in spec['variants']:
        name = variant.get('name', 'default')
        # The storeys above the ground storey where it has them: its own top closes its step to them (ledge).
        under = min(lines[name, role][1] for role in (('floor', 'top') if (name, 'floor') in lines or (name, 'top') in lines
                                                        else ('base',)) if (name, role) in lines)
        vaulted = variant.get('vaulted', shared.get('vaulted'))
        for roof_name in [variant.get('roof', shared.get('roof'))]+([vaulted] if vaulted else []):
            feet[roof_name] = min(feet.get(roof_name, np.inf), under-ROOF_INSET)
    # Roofs sharing an edge piece: one profile, so their pieces meet where they are laid together.
    groups = []
    for roof_name, (pieces, *_) in roofs.items():
        edges = set(pieces)-seams
        joined_ = [g for g in groups if g[1] & edges]
        for g in joined_:
            groups.remove(g)
        groups.append(({roof_name, *(n for g in joined_ for n in g[0])}, edges.union(*(g[1] for g in joined_))))
    chain = {}
    for names, edges in groups:
        if not edges:
            continue
        pieces = {piece: length for n in names for piece, length in roofs[n][0].items() if piece in edges}
        bays = {piece: length for piece, length in pieces.items() if piece not in corners} or pieces
        foot = min(feet.get(n, np.inf) for n in names)
        profile = edge_chain(near, bays, foot if np.isfinite(foot) else None)
        for piece in pieces:
            chain[piece] = profile
    for roof_name, (pieces, *_) in roofs.items():
        for piece, length in pieces.items():
            if piece in seams:
                chain[piece] = edge_chain(near, {piece: length})
    return wall, ledge, chain


# -- Rays ------------------------------------------------------------------------------------------------------------

def raster(xy, depth, origin, width, height, scale):
    """Triangles projected to (N,3,2) on a grid of width x height texels, scale texels a unit from origin (row 0 at the
    top, the second axis up): at each texel centre the nearest triangle (least depth), its depth and barycentrics."""
    index = np.full((height, width), -1, dtype=np.int64)
    best = np.full((height, width), np.inf)
    bary = np.zeros((height, width, 3))
    px = (xy-np.asarray(origin))*scale
    for t in range(len(px)):
        (ax, ay), (bx, by), (cx, cy) = px[t]
        area = (bx-ax)*(cy-ay)-(cx-ax)*(by-ay)
        if abs(area) < 1e-12:
            continue
        x0, x1 = max(0, int(np.floor(min(ax, bx, cx)))), min(width-1, int(np.ceil(max(ax, bx, cx))))
        y0, y1 = max(0, int(np.floor(min(ay, by, cy)))), min(height-1, int(np.ceil(max(ay, by, cy))))
        if x0 > x1 or y0 > y1:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1+1)+.5, np.arange(y0, y1+1)+.5)
        w0 = ((bx-gx)*(cy-gy)-(cx-gx)*(by-gy))/area
        w1 = ((cx-gx)*(ay-gy)-(ax-gx)*(cy-gy))/area
        w2 = 1-w0-w1
        d = w0*depth[t, 0]+w1*depth[t, 1]+w2*depth[t, 2]
        rows = height-1-np.arange(y0, y1+1)
        columns = np.arange(x0, x1+1)
        take = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9) & (d < best[rows[:, None], columns[None, :]])
        if take.any():
            r, c = np.nonzero(take)
            best[rows[r], columns[c]] = d[r, c]
            index[rows[r], columns[c]] = t
            bary[rows[r], columns[c]] = np.stack([w0[r, c], w1[r, c], w2[r, c]], axis=-1)
    return index, best, bary


class View:
    """A face's region: the plane from origin along u (its width) and w (its height), seen along ray (into the piece);
    what the near piece shows through each texel there."""

    def __init__(self, origin, u, w, ray, width, height):
        self.origin, self.u, self.w, self.ray = (np.asarray(v, dtype=np.float64) for v in (origin, u, w, ray))
        self.width, self.height = width, height
        self.inverse = np.linalg.inv(np.stack([self.u, self.w, self.ray], axis=1))

    def project(self, pos):
        local = (pos-self.origin) @ self.inverse.T
        return local[..., 0:2], local[..., 2]


# -- Materials -------------------------------------------------------------------------------------------------------

class Finishes:
    """The near level's materials as the bake reads them: albedo (linear, filtered for the atlas's density), building
    paint (a #paint finish, or mmBuildingPaint on the GLB's material), night glow (linear: a finish's own colour, or the
    board material's emission map), roughness and metallic."""

    def __init__(self, materials):
        self.extras = {m['id']: m.get('extras', {}) for m in materials}
        self.cache = {}

    def material(self, key):
        if key not in self.cache:
            if key.endswith('#pane'):
                # A pane's triangle: it lights as geometry of its own (panes), the atlas behind it not.
                self.cache[key] = {**self.material(key[:-len('#pane')]), 'glow': np.zeros((1, 1, 3))}
                return self.cache[key]
            name = key.split('#')[0]
            spec = read_material(TEXTURES/(name+'.tres'), TEXTURES)
            # Linear, premultiplied by coverage and filtered down: a cutout (a plant's leaves) reads as its leaves' colour.
            image = np.asarray(Image.open(spec['albedo']).convert('RGBA').resize((256, 256), Image.NEAREST), dtype=np.float64)/255
            colour, alpha = srgb_linear(image[..., :3]), image[..., 3:]
            size = 64
            def box(array):
                h, w = array.shape[:2]
                return array.reshape(size, h//size, size, w//size, -1).mean(axis=(1, 3))
            premultiplied, coverage = box(colour*alpha), box(alpha)
            albedo = premultiplied/np.maximum(coverage, 1e-6)*srgb_linear(np.array(spec['tint'][:3]))
            orm = {}
            for role in ('roughness', 'metallic'):
                factor = spec[role]
                if spec[role+'_map'] is not None:
                    image = np.asarray(Image.open(spec[role+'_map']).convert('RGBA'), dtype=np.float64)/255
                    factor *= float(image[..., spec[role+'_channel']].mean())
                orm[role] = factor
            glow = fine = np.zeros((1, 1, 3))
            flags = key.split('#')[1:]
            for flag in flags:
                if flag.startswith('emission-') and flag != 'emission-off':
                    glow = np.array([[[linear(float(v)) for v in flag[len('emission-'):].split('-')]]])
            if 'blink' in flags or self.extras.get(key, {}).get('mmEmission') == 'blink':
                raise ValueError(f'A far atlas does not blink: {key}')
            off = 'emission-off' in flags or self.extras.get(key, {}).get('mmEmission') == 'off'
            if not glow.any() and spec['emission'] is not None and not off:
                # A board material's emission map, its tint as Godot's operator gives it (GpuMaterialMaps#emission).
                energy, colour = spec['emission_energy'], np.array([linear(c) for c in spec['emission_color'][:3]])
                tint = energy if spec['emission_operator'] == 0 else colour*energy
                emitted = np.asarray(Image.open(spec['emission']).convert('RGB').resize((256, 256), Image.NEAREST), dtype=np.float64)/255
                fine = srgb_linear(emitted)*tint+(colour*energy if spec['emission_operator'] == 0 else 0)
                glow = box(fine)
            paint = 'paint' in flags or bool(self.extras.get(key, {}).get('mmBuildingPaint'))
            # fine: the glow at 256 texels, where a window atlas's windows are told apart (windows).
            self.cache[key] = {'albedo': albedo, 'paint': paint, 'glow': glow, 'fine': fine, 'orm': orm, 'name': name}
        return self.cache[key]

    def sample(self, key, uv, image=None):
        image = self.material(key)['albedo'] if image is None else image
        size = image.shape[0]
        x = np.minimum(np.floor(np.mod(uv[:, 0], 1)*size).astype(int), size-1)
        y = np.minimum(np.floor(np.mod(uv[:, 1], 1)*size).astype(int), size-1)
        return image[y, x]


LUMINANCE = np.array([.2126, .7152, .0722])


def srgb_linear(value):
    return np.where(value <= .04045, value/12.92, ((value+.055)/1.055)**2.4)


def linear_srgb(value):
    value = np.clip(value, 0, 1)
    return np.where(value <= .0031308, value*12.92, 1.055*value**(1/2.4)-.055)


def planar_uv(pos, nrm, repeat):
    """A material textured along the wall's line (BayKit#planar): each face by its main axis."""
    n = np.abs(nrm)
    out = (n[:, 1] >= np.maximum(n[:, 0], n[:, 2]))
    up = ~out & (n[:, 2] >= n[:, 0])
    a = np.where(out | up, pos[:, 0], pos[:, 1])
    b = np.where(out, pos[:, 2], np.where(up, pos[:, 1], pos[:, 2]))
    return np.stack([a/repeat, -b/repeat], axis=-1)


def facing(triangles, ray):
    """The triangles that face against ray (seen along it), as the near level draws them, back faces culled."""
    pos = triangles['pos']
    normal = np.cross(pos[:, 1]-pos[:, 0], pos[:, 2]-pos[:, 0])
    # Wound to face where their vertex normals do.
    normal *= np.sign(np.einsum('nc,nc->n', normal, triangles['nrm'].sum(axis=1)))[:, None]
    keep = normal @ ray < 0
    return {key: value[keep] for key, value in triangles.items()}


def bake(view, triangles, finishes, planar):
    """A region's maps: albedo (linear) and the painted share of its light (the paint mask, as the game's mip levels read
    it: GpuColorTexture#paintLevels), glow (linear), roughness and metallic, and the normal in the face's frame (along u,
    up its image, out), SAMPLES x SAMPLES rays a texel; planar: the materials textured along the wall's line. Rays that
    meet nothing take the nearest texel's."""
    width, height = view.width, view.height
    occluders = triangles
    triangles = facing(triangles, view.ray)
    xy, depth = view.project(triangles['pos'])
    index, _, bary = raster(xy, depth, (0, 0), width*SAMPLES, height*SAMPLES, DENSITY*SAMPLES)
    hit = index >= 0
    albedo = np.zeros(index.shape+(3,))
    paint = np.zeros(index.shape)
    glow = np.zeros(index.shape+(3,))
    rough = np.zeros(index.shape)
    metal = np.zeros(index.shape)
    tangent = np.zeros(index.shape+(3,))
    tangent[..., 2] = 1
    if hit.any():
        t = index[hit]
        b = bary[hit]
        pos = np.einsum('nk,nkc->nc', b, triangles['pos'][t])
        nrm = triangles['nrm'][t].mean(axis=1)
        smooth = np.einsum('nk,nkc->nc', b, triangles['nrm'][t])
        smooth /= np.maximum(np.linalg.norm(smooth, axis=1, keepdims=True), 1e-9)
        out = np.cross(view.u, view.w)
        tangent[hit] = np.stack([smooth @ view.u, smooth @ view.w, smooth @ out], axis=-1)
        uv = np.einsum('nk,nkc->nc', b, triangles['uv'][t])
        colour = srgb_linear(np.clip(np.einsum('nk,nkc->nc', b, triangles['col'][t][..., :3]), 0, None))
        keys = triangles['mat'][t]
        rgb = np.zeros((len(t), 3))
        for key in np.unique(keys):
            mask = keys == key
            m = finishes.material(key)
            repeat = planar.get(m['name'])
            sample_uv = planar_uv(pos[mask], nrm[mask], repeat) if repeat else uv[mask]
            rgb[mask] = finishes.sample(key, sample_uv)*colour[mask]
            paint_value = 1.0 if m['paint'] else 0.0
            sub = np.argwhere(hit)[mask]
            paint[sub[:, 0], sub[:, 1]] = paint_value
            glow[sub[:, 0], sub[:, 1]] = finishes.sample(key, sample_uv, m['glow'])
            rough[sub[:, 0], sub[:, 1]] = m['orm']['roughness']
            metal[sub[:, 0], sub[:, 1]] = m['orm']['metallic']
        # As much darker as its own sky the near piece hides (its sun shadows, on average).
        albedo[hit] = rgb*(1-DIRECT*(1-daylight(pos+smooth*.05, smooth, occluders)))[:, None]
    if (~hit).any():
        filled = nearest(hit)
        for array in (albedo, paint, glow, rough, metal, tangent):
            array[~hit] = array[filled[0][~hit], filled[1][~hit]]

    def average(array):
        shape = (height, SAMPLES, width, SAMPLES) + array.shape[2:]
        return array.reshape(shape).mean(axis=(1, 3))
    normal = average(tangent)
    normal /= np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-9)
    light = albedo @ LUMINANCE
    whole = average(light)
    paint = np.where(whole > 1e-6, average(light*paint)/np.maximum(whole, 1e-6), average(paint))
    return {'albedo': average(albedo), 'paint': paint, 'glow': average(glow), 'rough': average(rough),
            'metal': average(metal), 'normal': normal}


def nearest(mask):
    """For every texel, the row and column of the nearest texel where mask holds."""
    from scipy import ndimage
    _, (rows, columns) = ndimage.distance_transform_edt(~mask, return_indices=True)
    return rows, columns


def shifted(triangles, dz, dx=0):
    return {**triangles, 'pos': triangles['pos']+np.array([dx, 0, dz])}


def stretched(triangles, s):
    """Triangles stretched s times along x, their normals with them."""
    normals = triangles['nrm']*np.array([1/s, 1, 1])
    normals /= np.maximum(np.linalg.norm(normals, axis=-1, keepdims=True), 1e-12)
    return {**triangles, 'pos': triangles['pos']*np.array([s, 1, 1]), 'nrm': normals}


def daylight(points, normals, occluders):
    """The share of the sky (SKY, each direction by its cosine on the normal) the occluders leave open over each point."""
    pos = occluders['pos']
    lit, total = np.zeros(len(points)), np.zeros(len(points))
    scale = 4
    for d in SKY:
        weight = np.clip(normals @ d, 0, None)
        if not weight.any():
            continue
        a = np.cross(d, (1, 0, 0) if abs(d[0]) < .9 else (0, 1, 0))
        a /= np.linalg.norm(a)
        b = np.cross(d, a)
        xy = np.stack([pos @ a, pos @ b], axis=-1)
        low = xy.reshape(-1, 2).min(axis=0)-1
        width, height = (np.ceil((xy.reshape(-1, 2).max(axis=0)+1-low)*scale)).astype(int)
        _, best, _ = raster(xy, -(pos @ d), low, width, height, scale)
        column = np.clip(((points @ a-low[0])*scale).astype(int), 0, width-1)
        row = np.clip(height-1-((points @ b-low[1])*scale).astype(int), 0, height-1)
        # Open where nothing stands nearer the sky along d than the point, a little bias for the map's texels.
        open_ = -(points @ d) <= best[row, column]+.35
        lit += weight*open_
        total += weight
    return np.where(total > 0, lit/np.maximum(total, 1e-9), 1)


def joined(*sets):
    return {key: np.concatenate([s[key] for s in sets]) for key in sets[0]}


def flat(length, y0, z, material, repeat=12, tint=None):
    """A level surface in front of and under a piece (the street before a ground storey, a roof's deck behind its edge),
    for the rays that pass by the piece; tint: its sRGB vertex colour (a vault's sheeting)."""
    x0, x1, y1 = -length, 2*length, 60
    pos = np.array([[[x0, y0, z], [x1, y0, z], [x1, y1, z]], [[x0, y0, z], [x1, y1, z], [x0, y1, z]]], dtype=np.float64)
    colour = np.ones((2, 3, 4)) if tint is None else np.tile([*tint, 1.0], (2, 3, 1))
    return {'pos': pos, 'nrm': np.tile([0, 0, 1.0], (2, 3, 1)), 'col': colour, 'uv': pos[..., :2]/repeat,
            'mat': np.array([material+'#board']*2)}


# -- Far pieces ------------------------------------------------------------------------------------------------------

class Region:
    """A face's place in the atlas and its baked maps."""

    def __init__(self, name, maps):
        self.name, self.maps = name, maps
        self.height, self.width = maps['paint'].shape
        self.x = self.y = None


def pack(regions):
    """Shelves of regions, tallest first, each with PAD texels round it and aligned to ALIGN; their places set."""
    def size(value):
        return -(-(value+2*PAD)//ALIGN)*ALIGN
    x = y = shelf = 0
    for region in sorted(regions, key=lambda r: (-size(r.height), -size(r.width), r.name)):
        w, h = size(region.width), size(region.height)
        if x+w > ATLAS:
            x, y = 0, y+shelf
            shelf = 0
        if y+h > ATLAS:
            raise ValueError('the far atlas is full: lower DENSITY')
        region.x, region.y = x+PAD, y+PAD
        x += w
        shelf = max(shelf, h)


def atlas(regions, gain=1.0, glow=(1.0, None)):
    """The atlas maps: albedo RGBA (paint in A; its colour times gain), glow RGB (times glow's share; in its colour, the
    luminance kept, where it names one), ORM RGB (occlusion 1, roughness,
    metallic); every texel outside a region takes its nearest region texel's values, so mip levels keep the regions'
    colours."""
    covered = np.zeros((ATLAS, ATLAS), dtype=bool)
    out = {'albedo': np.zeros((ATLAS, ATLAS, 3)), 'paint': np.zeros((ATLAS, ATLAS)), 'glow': np.zeros((ATLAS, ATLAS, 3)),
           'rough': np.ones((ATLAS, ATLAS)), 'metal': np.zeros((ATLAS, ATLAS)), 'normal': np.dstack([np.zeros((ATLAS, ATLAS, 2)), np.ones((ATLAS, ATLAS))])}
    for region in regions:
        for key, array in out.items():
            array[region.y:region.y+region.height, region.x:region.x+region.width] = region.maps[key]
        covered[region.y:region.y+region.height, region.x:region.x+region.width] = True
    rows, columns = nearest(covered)
    for array in out.values():
        array[~covered] = array[rows[~covered], columns[~covered]]
    # Sharpened as displayed (SHARPEN): the game samples the atlas through its mip levels, softer than the near level's
    # own edges at the switch.
    from scipy import ndimage
    shown = linear_srgb(np.clip(out['albedo']*gain, 0, 1))
    amount, radius = SHARPEN
    shown = np.clip(shown+amount*(shown-ndimage.gaussian_filter(shown, sigma=(radius*DENSITY, radius*DENSITY, 0))), 0, 1)
    albedo = np.dstack([shown, out['paint']])
    orm = np.dstack([np.ones((ATLAS, ATLAS)), out['rough'], out['metal']])
    share, colour = glow
    lit = out['glow']*share
    if colour is not None:
        lit = (lit @ LUMINANCE)[..., None]*np.asarray(colour)/(np.asarray(colour) @ LUMINANCE)
    return {'albedo': albedo, 'glow': linear_srgb(np.clip(lit, 0, 1)), 'orm': orm, 'normal': out['normal']*.5+.5}


def uvs(region):
    """A region's UVs at a face's corners (counter-clockwise seen from where it faces: the region's bottom left, bottom
    right, top right, top left)."""
    u0, u1 = region.x/ATLAS, (region.x+region.width)/ATLAS
    v_top, v_bottom = region.y/ATLAS, (region.y+region.height)/ATLAS
    return [(u0, v_bottom), (u1, v_bottom), (u1, v_top), (u0, v_top)]


def far_kit(kit, folder='standard'):
    """The kit's far level: its near level's model, the far faces of each piece (corners, normal, atlas region) or its
    near triangles where a sparse fitting keeps them, the atlas regions, and the planes and ledges chosen."""
    directory = DATA/'models/buildings'/folder
    spec = json.loads((directory/f'{kit}.json').read_text(encoding='utf-8'))
    model, near = near_pieces(directory/spec['pieces'])
    grow = PANE_GROW.get(kit, 0.0)
    walls, roofs, seams, corners, fills, fittings, planar, sidewalks = layout(spec)
    finishes = Finishes(model['materials'])
    # The shapes come from a piece's solid surfaces: a cutout (leaves, a shrub on a planter) is drawn on them.
    cutouts = {m['id'] for m in model['materials'] if 'alphaTest' in m}
    solid = {name: {key: value[~np.isin(piece['mat'], list(cutouts))] for key, value in piece.items()}
             if np.isin(piece['mat'], list(cutouts)).any() and not np.isin(piece['mat'], list(cutouts)).all() else piece
             for name, piece in near.items()}
    wall, ledge, chain = planes(solid, walls, roofs, seams, corners, spec)
    stretch = stretches(spec)
    regions, faces = [], {}

    def baked(name, view, triangles):
        return bake(view, triangles, finishes, planar.get(name.split(' ')[0], {}))

    def region(name, view, triangles):
        made = Region(name, baked(name, view, triangles))
        regions.append(made)
        return made

    def hollow(top, face):
        """A ledge whose view met little of its piece (the strip under it is hollow in the near piece: its bake came out
        under a quarter of its face's brightness) takes its storey face's colour, column by column: the median down the
        face, its dominant surface rather than its windows; no glow, its normal straight out."""
        if (top.maps['albedo'] @ LUMINANCE).mean() >= .25*np.median(face.maps['albedo'] @ LUMINANCE):
            return
        columns = np.linspace(0, face.width-1, top.width).round().astype(int)
        for key in ('albedo', 'paint', 'rough', 'metal'):
            median = np.median(face.maps[key], axis=0)[columns]
            top.maps[key] = np.broadcast_to(median, top.maps[key].shape).copy()
        top.maps['glow'] = np.zeros_like(top.maps['glow'])
        top.maps['normal'] = np.broadcast_to(np.array([0, 0, 1.0]), top.maps['normal'].shape).copy()
        print('  hollow ledge filled from its face:', top.name)

    def seen(origin, u, w, width, height):
        """A face's view as the iso camera sees it from BAKE_ELEVATION, head on."""
        u, w = np.asarray(u, dtype=np.float64), np.asarray(w, dtype=np.float64)
        c, s = math.cos(BAKE_ELEVATION), math.sin(BAKE_ELEVATION)
        return View(origin, u, w, -c*np.cross(u, w)-s*np.array([0, 0, 1.0]), width, height)

    def down(origin, u, w, width, height):
        return View(origin, u, w, (0, 0, -1), width, height)

    def strip(name, length, a, b, triangles):
        """A face along the piece's whole length from (y, z) a to b, seen head on."""
        a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
        rise = np.linalg.norm(b-a)
        w = np.array([0, *(b-a)])/rise
        origin = (0, a[0], a[1])
        width, height = round(length*DENSITY), max(1, round(rise*DENSITY))
        made = region(name, seen(origin, (1, 0, 0), w, width, height), triangles)
        return ([(0, *a), (length, *a), (length, *b), (0, *b)], tuple(np.cross((1, 0, 0), w)), made, None)

    def lofted(name, piece, shapes):
        """Lofts' faces (frusta: a piece's turrets and spires, a fitting): each frustum's sides one region, side by side,
        each seen head on; a top seen from above."""
        made = []
        for n, (bands, top) in enumerate(shapes):
            for b, band in enumerate(bands):
                parts = []
                for corners, normal in band:
                    corners = np.asarray(corners, dtype=np.float64)
                    u = np.array([-normal[1], normal[0], 0])/np.linalg.norm(normal[:2])
                    rise = corners[3]-corners[0]
                    w = rise-(rise @ u)*u
                    w /= np.linalg.norm(w)
                    along = (corners-corners[0]) @ u
                    view = seen(corners[0]+along.min()*u, u, w, max(1, round(np.ptp(along)*DENSITY)),
                                max(1, round(((corners-corners[0]) @ w).max()*DENSITY)))
                    parts.append((corners, normal, view, baked(name, view, piece)))
                tallest = max(maps['paint'].shape[0] for *_, maps in parts)
                side_by_side = {key: np.concatenate([np.pad(maps[key], ((tallest-maps[key].shape[0], 0), (0, 0))
                                                            +((0, 0),)*(maps[key].ndim-2), mode='edge') for *_, maps in parts], axis=1)
                                for key in parts[0][3]}
                reg = Region(f'{name} loft {n} {b}', side_by_side)
                regions.append(reg)
                offset = 0
                for corners, normal, view, maps in parts:
                    local = [(offset+(p-view.origin) @ view.u*DENSITY, (p-view.origin) @ view.w*DENSITY) for p in corners]
                    made.append(([tuple(p) for p in corners], tuple(normal), reg, local))
                    offset += maps['paint'].shape[1]
            if top is not None:
                corners = np.asarray(top, dtype=np.float64)
                lo, size = corners.min(axis=0), np.ptp(corners, axis=0)
                view = down((lo[0], lo[1], corners[0][2]), (1, 0, 0), (0, 1, 0), max(1, round(size[0]*DENSITY)),
                            max(1, round(size[1]*DENSITY)))
                reg = region(f'{name} loft {n} top', view, piece)
                local = [((p-view.origin) @ view.u*DENSITY, (p-view.origin) @ view.w*DENSITY) for p in corners]
                made.append(([tuple(p) for p in corners], (0, 0, 1), reg, local))
        return made

    def loft(name, length, outside):
        """A piece's lofts (lofts), shaped and baked as the kit lays it: a rounded corner's piece stretched along its facet
        (stretches), then brought back to its own length."""
        s = stretch.get(name, 1.0)
        made = lofted(name, stretched(marks.get(name, near[name]), s), lofts(stretched(solid[name], s), length*s, outside))
        back = []
        for corners, normal, region_, local in made:
            normal = np.array([normal[0]*s, normal[1], normal[2]])
            back.append(([(x/s, y, z) for x, y, z in corners], tuple(normal/np.linalg.norm(normal)), region_, local))
        return back

    def mark(piece):
        """The piece as its far faces are baked: nothing of it glows in the atlas, its lit panes glow as geometry; an
        ATLAS_GLOW kit's glass glows in the atlas and it has no panes."""
        if kit in ATLAS_GLOW:
            return piece
        lit = np.isin(piece['mat'], [key for key in np.unique(piece['mat']).tolist() if finishes.material(key)['glow'].any()])
        return {**piece, 'mat': np.where(lit, np.char.add(piece['mat'].astype(str), '#pane'), piece['mat'])}

    glowing = [key for key in {m['id'] for m in model['materials']} if finishes.material(key)['glow'].any()]

    def relief(piece, length, face):
        """Whether the piece's lit glass lies RELIEF_DEPTH or more behind its far face, seen head on (the median of its
        glass's samples), and the piece has at most RELIEF_TRIS triangles."""
        least, most = RELIEF_DEPTH, RELIEF_TRIS
        if len(piece['pos']) > most or not np.isin(piece['mat'], glowing).any():
            return False
        z0 = float(piece['pos'][..., 2].min())
        index, depth, _ = raster(piece['pos'][..., [0, 2]], piece['pos'][..., 1], (0, z0), int(length*4),
                                 max(1, int(np.ceil(np.ptp(piece['pos'][..., 2])*4))), 4)
        glass = (index >= 0) & np.isin(piece['mat'][np.maximum(index, 0)], glowing)
        return bool(glass.any()) and float(np.median(depth[glass]))-face >= least

    marks, lit = {}, {}
    roles = {}
    for (variant, role), pieces in walls.items():
        for name, length in pieces.items():
            roles[name] = (role, length, variant)
    for name, (role, length, variant) in sorted(roles.items()):
        y0, y1 = wall[name]

        def surroundings(piece):
            """The same piece beside it and over it (under it, a storey's), as the rays that leave its own see them; under
            a ground storey its sidewalk."""
            row = joined(*(shifted(piece, 0, k*length) for k in (-2, -1, 0, 1, 2)))
            around = joined(row, shifted(row, LEVEL)) if role == 'base' else joined(shifted(row, -LEVEL), row, shifted(row, LEVEL))
            return joined(around, flat(length, y0-20, 0, sidewalks[variant])) if role == 'base' and sidewalks[variant] else around

        framed = relief(near[name], length, (y0+y1)/2)
        if framed:
            faces[name] = near[name]  # its fins or reveals frame its windows from every side the camera sees: as near
            marks[name] = mark(near[name])  # as a roof edge's storey under it
            continue
        lit[name] = None if kit in ATLAS_GLOW else panes(near[name], [(y0, 0), (y1, LEVEL)], finishes,
                                                         surroundings(solid[name])['pos'], grow)
        piece = marks[name] = mark(near[name])
        around = surroundings(piece)
        made = [strip(name, length, (y0, 0), (y1, LEVEL), around)]
        if min(y0, y1) < -BACKED:
            # Far out of its wall line its face no longer meets the next hex's at a corner they turn round: the same face
            # on the wall line behind it closes what shows between them.
            corners, normal, front_region, _ = made[0]
            made.append(([(0, 0, 0), (length, 0, 0), (length, 0, LEVEL), (0, 0, LEVEL)], (0, -1, 0), front_region, None))
        inner = ledge[name]
        if inner > y1+.01:
            top = region(name+' ledge', down((0, y1, LEVEL), (1, 0, 0), (0, 1, 0), round(length*DENSITY),
                                             max(1, round((inner-y1)*DENSITY))), piece)
            hollow(top, made[0][2])
            made.append(([(0, y1, LEVEL), (length, y1, LEVEL), (length, inner, LEVEL), (0, inner, LEVEL)], (0, 0, 1), top, None))
        made += loft(name, length, lambda p, y0=y0, y1=y1: y0+(y1-y0)*p[:, 2]/LEVEL-p[:, 1])
        faces[name] = made+([lit[name]] if lit[name] is not None else [])
    # Under a roof's edge, the storey it stands on (the first piece of its first variant's top storey): what a step out to
    # that storey's face shows.
    beneath = {}
    for variant in spec['variants']:
        storeys = [walls[key] for key in ((variant.get('name', 'default'), role) for role in ('top', 'floor', 'base')) if key in walls]
        if storeys:
            beneath.setdefault(variant.get('roof', spec.get('shared', {}).get('roof')), next(iter(storeys[0].items())))
    for roof_name, (pieces, deck, deck_material, repeat, deck_tint) in roofs.items():
        for name, length in pieces.items():
            if name in faces:
                continue  # laid by another roof too: one far piece
            if NEAR_ROOF.get(kit) == 'roof':
                faces[name] = near[name]  # what the roof's outline reads from: as near (NEAR_ROOF)
                marks[name] = mark(near[name])
                continue
            profile = chain[name]

            def surroundings(own, under):
                """The same piece beside it, its roof's deck behind it and the storey it stands on under it."""
                row = joined(*(shifted(own, 0, k*length) for k in (-2, -1, 0, 1, 2)))
                around = joined(row, flat(length, -ROOF_INSET, deck-.02, deck_material, repeat, deck_tint))
                if roof_name not in beneath:
                    return around
                bay, bay_length = beneath[roof_name]
                storey = {**under[bay], 'pos': under[bay]['pos']+np.array([0, -ROOF_INSET, -LEVEL])}
                return joined(around, *(shifted(storey, 0, k*bay_length) for k in range(-2, math.ceil(length/bay_length)+2)))

            lit[name] = None if kit in ATLAS_GLOW else panes(near[name], profile, finishes, surroundings(solid[name], solid)['pos'], grow)
            marks[name] = mark(near[name])
            piece = surroundings(marks[name], marks)
            made = [strip(f'{name} {k}', length, a, b, piece) for k, (a, b) in enumerate(zip(profile, profile[1:]))]
            # A strip whose view met nothing lies where the near piece has nothing (a hangar's step outside its gutter):
            # it would show as a row of dark, or filled light, pixels along the roof's outline. Left out.
            dropped = [m for m in made if not m[2].maps['albedo'].any()]
            # The section from its first strip kept on: the lid below stops where the piece starts.
            edge = profile[next((k for k, m in enumerate(made) if m not in dropped), 0):]
            made = [m for m in made if m[2].maps['albedo'].any()]
            for m in dropped:
                regions.remove(m[2])
                print('  empty strip left out:', m[2].name)
            inner, z1 = profile[-1]
            floor = deck-.05
            if z1 > floor+.1:
                back = region(name+' back', seen((length, inner, floor), (-1, 0, 0), (0, 0, 1), round(length*DENSITY),
                                                 max(1, round((z1-floor)*DENSITY))), piece)
                made.append(([(length, inner, floor), (0, inner, floor), (0, inner, z1), (length, inner, z1)], (0, 1, 0), back, None))
            # A lid just under the profile at the storey's top: where the kit cuts the piece (a sector's line, a joint)
            # its section stands open, and what shows through it is the lid, not the storey under it.
            z0 = max(0.0, edge[0][1])
            y0 = min((a[0]+(b[0]-a[0])*(z0-a[1])/(b[1]-a[1]) if b[1] != a[1] else min(a[0], b[0])
                      for a, b in zip(edge, edge[1:]) if min(a[1], b[1]) <= z0 <= max(a[1], b[1])), default=inner)
            if inner > y0+.1:
                z0 -= LID
                made.append(([(0, y0, z0), (length, y0, z0), (length, inner, z0), (0, inner, z0)], (0, 0, 1), made[-1][2], None))
            if name not in seams:
                made += loft(name, length, beyond(profile))
            faces[name] = made+([lit[name]] if lit[name] is not None else [])
    for name in sorted(fills & set(near)):
        faces[name] = near[name]  # inside the hull, but laid at every level (a piece needs a node there): a few triangles
    for name in sorted(fittings):
        piece = near[name]
        if name in near and kit in NEAR_ROOF:
            faces[name] = piece  # as near (NEAR_ROOF)
            continue
        lo, hi = piece['pos'].reshape(-1, 3).min(axis=0), piece['pos'].reshape(-1, 3).max(axis=0)
        size = hi-lo
        if covered(piece, lo, hi) < FITTING_BOX:
            # A fitting a box would not fit (a water tank, a mast on a hut, a tree): a loft, or its near mesh where that
            # is no more triangles.
            shape = frusta(piece, lambda p: np.ones(len(p)), -np.inf, np.inf, FITTING_BANDS)
            if len(piece['pos']) <= sum(2*len(band) for band in shape[0])+(6 if shape[1] is not None else 0):
                faces[name] = piece
            else:
                faces[name] = lofted(name, piece, [shape])
            continue
        top = region(name+' top', down((lo[0], lo[1], hi[2]), (1, 0, 0), (0, 1, 0), max(1, round(size[0]*DENSITY)),
                                       max(1, round(size[1]*DENSITY))), piece)
        side = region(name+' side', View((lo[0], lo[1], lo[2]), (1, 0, 0), (0, 0, 1), (0, 1, 0), max(1, round(size[0]*DENSITY)),
                                         max(1, round(size[2]*DENSITY))), piece)
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        faces[name] = [
            ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), top, None),
            ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0), side, None),
            ([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], (0, 1, 0), side, None),
            ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0), side, None),
            ([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], (-1, 0, 0), side, None)]
    pack(regions)
    unlaid = sorted(set(near) - set(faces))
    if unlaid:
        print('  no far level for pieces the kit does not lay:', ', '.join(unlaid))
    return model, faces, regions, wall, chain


def panes(piece, section, finishes, scene, grow=0.0):
    """A piece's lit panes on its far surface (section: that surface's (y, z) polyline, the piece running along x, the
    building on the polyline's right): each flat part of a material that glows (a lit window, a lit sign; on a facade lit
    by an emission map, each lit window of it: windows) that faces out of the surface within PANE_DEPTH of it, clear of
    the scene (the near triangles round the piece) along its normal, moved along it to PANE_LIFT outside the surface, in
    its own near material, and drawn in to what the iso camera sees of it past the scene (seen: as wide and as high as
    the share of its columns and rows seen, round the middle of what is seen); a rectangle as one quad. So a lit window
    lights at the far level as it does near: its colour, brightness, edge and lit pattern its own. Returns the panes'
    triangles, None for none."""
    import building_lod
    rows = []
    steps = [(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)) for a, b in zip(section, section[1:])]
    for key in np.unique(piece['mat']).tolist():
        glow = finishes.material(key)['glow']
        if not glow.any():
            continue
        chosen = np.flatnonzero(piece['mat'] == key)
        tri = piece['pos'][chosen]
        out = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
        out *= np.sign(np.einsum('nc,nc->n', out, piece['nrm'][chosen].sum(axis=1)))[:, None]
        unit = out/np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)
        # A pane: the triangles of one connected part that lie in one plane.
        part = building_lod.connected_pieces(tri.reshape(-1, 3), np.arange(3*len(chosen)).reshape(-1, 3))[::3]
        plane = np.column_stack([part, np.round(unit, 1), np.round(np.einsum('nc,nc->n', unit, tri[:, 0]), 1)])
        _, group = np.unique(plane, axis=0, return_inverse=True)
        group = group.ravel()
        for one in np.unique(group):
            mine = chosen[group == one]
            n = unit[group == one].mean(axis=0)
            n /= np.linalg.norm(n)
            up = np.array([0, 0, 1.0]) if abs(n[2]) < .9 else np.array([0, 1.0, 0])
            u = np.cross(up, n)
            u /= np.linalg.norm(u)
            w = np.cross(n, u)
            parts = [{k: piece[k][mine] for k in ('pos', 'nrm', 'col', 'uv')}]
            if glow.shape[:2] != (1, 1):
                lit = finishes.sample(key, piece['uv'][mine].reshape(-1, 2), glow) @ LUMINANCE
                if (lit < .5*(glow.reshape(-1, 3) @ LUMINANCE).max()).any():
                    parts = windows(parts[0], key, finishes, n, u, w)
            for own in parts:
                made = pane(own, n, u, w, steps, scene, grow)
                if made is not None:
                    rows.append((made, key))
    if not rows:
        return None
    triangles = np.concatenate([r for r, _ in rows])
    return {'pos': triangles[..., 0:3], 'nrm': triangles[..., 3:6], 'col': triangles[..., 6:10], 'uv': triangles[..., 10:12],
            'mat': np.concatenate([[key]*len(r) for r, key in rows])}


def windows(part, key, finishes, n, u, w):
    """A flat part lit by its emission map only in places (a facade's window atlas): each lit window (lit texels of the
    map at 256 texels, together, sampled every quarter unit over the part) a rectangle of its own, in the part's plane
    and texture."""
    from scipy import ndimage
    corners = part['pos'].reshape(-1, 3)
    a, b = corners @ u, corners @ w
    fit, *_ = np.linalg.lstsq(np.column_stack([a, b, np.ones(len(a))]), part['uv'].reshape(-1, 2), rcond=None)
    offset = float(np.mean(corners @ n))
    xs, ys = np.arange(a.min()+.125, a.max(), .25), np.arange(b.min()+.125, b.max(), .25)
    gx, gy = np.meshgrid(xs, ys)
    points = np.column_stack([gx.ravel(), gy.ravel()])
    inside = np.zeros(len(points), dtype=bool)
    for t in part['pos']:
        p = np.column_stack([t @ u, t @ w])
        d = (p[1, 1]-p[2, 1])*(p[0, 0]-p[2, 0])+(p[2, 0]-p[1, 0])*(p[0, 1]-p[2, 1])
        if abs(d) < 1e-12:
            continue
        l0 = ((p[1, 1]-p[2, 1])*(points[:, 0]-p[2, 0])+(p[2, 0]-p[1, 0])*(points[:, 1]-p[2, 1]))/d
        l1 = ((p[2, 1]-p[0, 1])*(points[:, 0]-p[2, 0])+(p[0, 0]-p[2, 0])*(points[:, 1]-p[2, 1]))/d
        inside |= (l0 >= 0) & (l1 >= 0) & (l0+l1 <= 1)
    fine = finishes.material(key)['fine']
    level = finishes.sample(key, np.column_stack([points, np.ones(len(points))]) @ fit, fine) @ LUMINANCE
    lit = (inside & (level >= .5*(fine.reshape(-1, 3) @ LUMINANCE).max())).reshape(gx.shape)
    if not lit.any():
        return []
    labels, _ = ndimage.label(lit)
    colour = part['col'].reshape(-1, 4).mean(axis=0)
    out = []
    for rows_, cols in ndimage.find_objects(labels):
        a0, a1 = xs[cols.start]-.125, xs[cols.stop-1]+.125
        b0, b1 = ys[rows_.start]-.125, ys[rows_.stop-1]+.125
        box = np.array([(a0, b0), (a1, b0), (a1, b1), (a0, b1)])
        quad = box[:, :1]*u+box[:, 1:]*w+offset*n
        uv = np.column_stack([box, np.ones(4)]) @ fit
        index = [0, 1, 2, 0, 2, 3]
        out.append({'pos': quad[index].reshape(2, 3, 3), 'nrm': np.tile(n, (2, 3, 1)), 'col': np.tile(colour, (2, 3, 1)),
                    'uv': uv[index].reshape(2, 3, 2)})
    return out


def pane(own, n, u, w, steps, scene, grow=0.0):
    """One lit flat part (pos, nrm, col, uv: (k,3,...)) of normal n as its pane (panes): its triangles (k,3,12), or None
    where it lies too deep or too far out, is hidden head on, or the iso camera sees too little of it."""
    corners = own['pos'].reshape(-1, 3)
    # How far along n each corner lies inside the surface (negative: outside it), where n meets it facing out.
    depth = np.full(len(corners), np.nan)
    for a, b in steps:
        edge = b-a
        outward = np.array([-edge[1], edge[0]])/np.linalg.norm(edge)
        if n[1:] @ outward < .5:
            continue
        t, along = np.linalg.solve(np.array([[n[1], -edge[0]], [n[2], -edge[1]]]), (a-corners[:, 1:]).T)
        met = (along >= -.02) & (along <= 1.02) & np.isnan(depth)
        depth[met] = t[met]
    if np.isnan(depth).any() or depth.max() > PANE_DEPTH or depth.min() < -PANE_DEPTH:
        return None
    a, b = corners @ u, corners @ w
    if seen(own['pos'], scene, [-n], [1.0], u, w)[0] < PANE_CLEAR:
        return None  # behind a column or a rail: brought out, it would light over it
    share, middle, scale = seen(own['pos'], scene, *iso(n), u, w)
    if share < PANE_SHARE:
        return None
    if grow:
        # The kit's pane size (PANE_GROW): grown towards the window's full size and centre, or shrunk.
        centre = np.array([(corners @ u).min()+(corners @ u).max(), (corners @ w).min()+(corners @ w).max()])/2
        middle, scale = middle+(centre-middle)*grow, scale+(1-scale)*grow
    row = np.concatenate([own['pos'], own['nrm'], own['col'], own['uv']], axis=-1).reshape(-1, 12)
    row[:, 3:6] = n
    area = np.linalg.norm(np.cross(own['pos'][:, 1]-own['pos'][:, 0], own['pos'][:, 2]-own['pos'][:, 0]), axis=1).sum()/2
    if len(own['pos']) > 1 and area >= .9*np.ptp(a)*np.ptp(b):
        # A rectangle: its box, the near UVs fitted to its plane.
        fit, *_ = np.linalg.lstsq(np.column_stack([a, b, np.ones(len(a))]), row[:, 10:12], rcond=None)
        half = np.array([np.ptp(a), np.ptp(b)])*scale/2
        box = middle+half*np.array([(-1, -1), (1, -1), (1, 1), (-1, 1)])
        quad = np.column_stack([box[:, :1]*u+box[:, 1:]*w+float(np.mean(corners @ n))*n, np.tile(n, (4, 1)),
                                np.tile(row[:, 6:10].mean(axis=0), (4, 1)), np.column_stack([box, np.ones(4)]) @ fit])
        row = quad[[0, 1, 2, 0, 2, 3]]
    else:
        centre = np.array([(a.min()+a.max())/2, (b.min()+b.max())/2])
        row[:, :3] += (np.outer(middle[0]+(a-centre[0])*scale[0]-a, u)+np.outer(middle[1]+(b-centre[1])*scale[1]-b, w))
    row[:, :3] += n*(depth.max()+PANE_LIFT)
    return row.reshape(-1, 3, 12)


def iso(normal):
    """The iso camera's looks at a face of this normal (PANE_VIEWS), and their weights."""
    flat = np.array([normal[0], normal[1], 0.0])
    flat = flat/np.linalg.norm(flat) if np.linalg.norm(flat) > .3 else np.array([0, -1.0, 0])
    side = np.cross([0, 0, 1.0], flat)
    rays = [-math.cos(BAKE_ELEVATION)*(math.cos(azimuth)*flat+math.sin(azimuth)*side)
            - math.sin(BAKE_ELEVATION)*np.array([0, 0, 1.0]) for azimuth, _ in PANE_VIEWS]
    return rays, [weight for _, weight in PANE_VIEWS]


def seen(pane, scene, rays, weights, u, w):
    """What looks along rays (each a weight) see of a pane (triangles (k,3,3), its plane spanned by u and w) past the
    scene's triangles (m,3,3), on average: the share of its area, the middle of what they see (along u and w), and the
    shares of its extent along u and along w they see (its columns and its rows with any of it seen)."""
    corners = pane.reshape(-1, 3)
    extent = np.array([np.ptp(corners @ u), np.ptp(corners @ w)])
    low = np.array([(corners @ u).min(), (corners @ w).min()])
    shares, middles, spans, kept = [], [], [], []
    for along, weight in zip(rays, weights):
        a = np.cross(along, [0, 0, 1.0]) if abs(along[2]) < .99 else np.array([1.0, 0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(a, along)
        pxy, pd = np.stack([pane @ a, pane @ b], -1), pane @ along
        sxy, sd = np.stack([scene @ a, scene @ b], -1), scene @ along
        lo, hi = pxy.reshape(-1, 2).min(axis=0), pxy.reshape(-1, 2).max(axis=0)
        before = ((sxy[..., 0].max(axis=1) >= lo[0]) & (sxy[..., 0].min(axis=1) <= hi[0]) & (sxy[..., 1].max(axis=1) >= lo[1])
                  & (sxy[..., 1].min(axis=1) <= hi[1]) & (sd.min(axis=1) < pd.max()))
        size = np.maximum(1, np.ceil((hi-lo)*8)).astype(int)
        alone, _, _ = raster(pxy, pd, lo, size[0], size[1], 8)
        among, _, bary = raster(np.concatenate([pxy, sxy[before]]), np.concatenate([pd, sd[before]]), lo, size[0], size[1], 8)
        if not (alone >= 0).any():
            continue
        mine = (among >= 0) & (among < len(pane))
        kept.append(weight)
        shares.append(mine.sum()/(alone >= 0).sum())
        if not mine.any():
            middles.append(low+extent/2)
            spans.append(np.zeros(2))
            continue
        points = np.einsum('nk,nkc->nc', bary[mine], pane[among[mine]])
        plane = np.stack([points @ u, points @ w], -1)
        middles.append((plane.min(axis=0)+plane.max(axis=0))/2)
        cells = np.maximum(1, np.ceil(extent/.25))
        spans.append(np.array([len(np.unique(np.floor((plane[:, k]-low[k])/.25))) for k in (0, 1)])/cells)
    if not kept:
        return 0.0, low+extent/2, np.zeros(2)
    return (float(np.average(shares, weights=kept)), np.average(middles, axis=0, weights=kept),
            np.minimum(np.average(spans, axis=0, weights=kept), 1.0))


def beyond(profile):
    """How far points (N,3) stand out of a roof edge's profile (its steps' half-planes, but a step at its foot's; negative
    within)."""
    steps = [(np.array(a), np.array(b)) for a, b in zip(profile, profile[1:])]
    if len(steps) > 1 and steps[0][0][1] == steps[0][1][1] and steps[0][1][0] > steps[0][0][0]:
        steps = steps[1:]

    def outside(points):
        result = np.full(len(points), -np.inf)
        for a, b in steps:
            d = (b-a)/np.linalg.norm(b-a)
            # The profile runs with the building on its right: out is its left.
            result = np.maximum(result, (points[:, 1:3]-a) @ np.array([-d[1], d[0]]))
        return result
    return outside


def lofts(piece, length, outside):
    """The far shapes (frusta) of what stands PROTRUDE or more out of a piece's far face (outside: how far points stand
    out of it) seen from its front, each connected part of it TALL or more high that fills LOFT_FILL or more of its
    bounds there: a turret or a spire. A dormer, a porch or a canopy is drawn on the face."""
    from scipy import ndimage
    depth, z0 = front(piece, length)
    rows_, columns = np.nonzero(np.isfinite(depth))
    points = np.stack([(columns+.5)/4, depth[rows_, columns], z0+(depth.shape[0]-rows_-.5)/4], axis=1)
    standing = np.zeros(depth.shape, dtype=bool)
    standing[rows_, columns] = outside(points) > PROTRUDE
    labels, count = ndimage.label(standing, structure=np.ones((3, 3)))
    result = []
    for k in range(1, count+1):
        r, c = np.nonzero(labels == k)
        high, wide = np.ptp(r)+1, np.ptp(c)+1
        if high/4 >= TALL and len(r)/(high*wide) >= LOFT_FILL:
            result.append(frusta(piece, outside, c.min()/4, (c.max()+1)/4))
    return result


def frusta(piece, outside, x0, x1, most=LOFT_BANDS):
    """A turret's or a spire's far shape: frusta of octagons (LOFT_DIRECTIONS) one over another, enclosing the triangles
    standing out of the face between x0 and x1 along the wall, at most most of them, split where the geometry stands
    LOFT_FIT out of a straight frustum: each frustum's sides (corners counter-clockwise from outside, normal; all eight,
    as the face behind one may not reach past the piece), and the top's corners (None for a point)."""
    pos = piece['pos']
    standing = outside(pos.reshape(-1, 3)).reshape(-1, 3)
    keep = (standing > .05).any(axis=1) & (pos[..., 0].max(axis=1) >= x0-1) & (pos[..., 0].min(axis=1) <= x1+1)
    triangles = pos[keep]
    z0, z1 = float(triangles[..., 2].min()), float(triangles[..., 2].max())
    count = max(1, int(np.ceil((z1-z0)/.5)))
    bounds = np.linspace(z0, z1, count+1)
    # Each slab's support in the eight directions: its triangles clipped to it, their corners and where their edges cross
    # its bounds.
    points = [triangles.reshape(-1, 3)]
    for z in bounds:
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = triangles[:, i], triangles[:, j]
            span = b[:, 2]-a[:, 2]
            with np.errstate(divide='ignore', invalid='ignore'):
                t = (z-a[:, 2])/span
            crossing = (np.abs(span) > 1e-9) & (t >= 0) & (t <= 1)
            points.append(a[crossing]+t[crossing, None]*(b[crossing]-a[crossing]))
    points = np.concatenate(points)
    support = np.full((count, len(LOFT_DIRECTIONS)), -np.inf)
    for k in range(count):
        inside = (points[:, 2] >= bounds[k]-1e-6) & (points[:, 2] <= bounds[k+1]+1e-6)
        if inside.any():
            support[k] = (points[inside, :2] @ LOFT_DIRECTIONS.T).max(axis=0)
    filled = [k for k in range(count) if np.isfinite(support[k, 0])]
    for k in range(count):
        if not np.isfinite(support[k, 0]):
            support[k] = support[min(filled, key=lambda f: abs(f-k))]
    # At each bound, the support of the slabs on both sides of it.
    at = np.vstack([support[:1], np.maximum(support[:-1], support[1:]), support[-1:]])

    def misfit(i, j, both=False):
        """How far the slabs between bounds i and j stand out of the frustum straight between them (both: or it out of
        them, at their middle), and the inner bound nearest to where most."""
        worst, where = -np.inf, None
        for k in range(i, j):
            t0, t1 = (bounds[k]-bounds[i])/(bounds[j]-bounds[i]), (bounds[k+1]-bounds[i])/(bounds[j]-bounds[i])
            straight = np.minimum(at[i]+(at[j]-at[i])*t0, at[i]+(at[j]-at[i])*t1)
            gap = float((support[k]-straight).max())
            if both:
                gap = max(gap, float((at[i]+(at[j]-at[i])*(t0+t1)/2-support[k]).max()))
            if gap > worst:
                worst, where = gap, (k if k > i else k+1)
        return worst, where

    # Split where the geometry departs most from a straight frustum, in or out (a mast on a hut is a frustum of its own).
    breaks = [0, count]
    while len(breaks)-1 < most:
        fits = [misfit(i, j, both=True) for i, j in zip(breaks, breaks[1:]) if j-i > 1]
        if not fits:
            break
        worst, where = max(fits)
        if worst <= LOFT_FIT or where in breaks:
            break
        breaks = sorted(breaks+[where])
    # Each frustum's sides as close as enclose it: in each direction the straight line over its slabs' supports (at both
    # their bounds) that stands least far out at its middle height; a ring the outermost of the frusta's on it.
    reach = np.full((len(breaks), len(LOFT_DIRECTIONS)), -np.inf)
    for n, (i, j) in enumerate(zip(breaks, breaks[1:])):
        t = (np.concatenate([bounds[i:j], bounds[i+1:j+1]])-bounds[i])/(bounds[j]-bounds[i])
        for d in range(len(LOFT_DIRECTIONS)):
            low, high = tightest(t, np.tile(support[i:j, d], 2))
            reach[n, d], reach[n+1, d] = max(reach[n, d], low), max(reach[n+1, d], high)
    rings = []
    for n, b in enumerate(breaks):
        h = reach[n].copy()
        # A side the two beside it leave no room for (each line fitted on its own) goes in to where they meet, so the
        # ring's corners run round it in order and no side turns inside out.
        for _ in range(8):
            for d in range(8):
                h[d] = min(h[d], (h[d-1]+h[(d+1) % 8])/math.sqrt(2))
        corners = [np.linalg.solve(np.array([LOFT_DIRECTIONS[i], LOFT_DIRECTIONS[(i+1) % 8]]), [h[i], h[(i+1) % 8]])
                   for i in range(8)]
        rings.append([np.array([c[0], c[1], bounds[b]]) for c in corners])
    bands = []
    for low, high in zip(rings, rings[1:]):
        band = []
        for i in range(8):
            quad = [low[i-1], low[i], high[i], high[i-1]]
            if np.linalg.norm(quad[1]-quad[0]) < 1e-3 and np.linalg.norm(quad[2]-quad[3]) < 1e-3:
                continue
            along = quad[1]-quad[0] if np.linalg.norm(quad[1]-quad[0]) > 1e-3 else quad[2]-quad[3]
            normal = np.cross(along, quad[3]-quad[0])
            band.append(([tuple(map(float, p)) for p in quad], normal/np.linalg.norm(normal)))
        if band:
            bands.append(band)
    top = rings[-1]
    area = .5*abs(sum(top[i-1][0]*top[i][1]-top[i][0]*top[i-1][1] for i in range(8)))
    return bands, ([tuple(map(float, p)) for p in top] if area > .25 else None)


def tightest(t, s):
    """The straight line over points (t, s), t from 0 to 1, that stands least high at t = 1/2: its heights at 0 and 1."""
    k, l = np.meshgrid(np.nonzero(t <= .5)[0], np.nonzero(t >= .5)[0], indexing='ij')
    k, l = k.ravel(), l.ravel()
    k, l = k[t[l] > t[k]], l[t[l] > t[k]]
    slope = (s[l]-s[k])/(t[l]-t[k])
    start = s[k]-slope*t[k]
    over = (start[:, None]+slope[:, None]*t[None, :] >= s[None, :]-1e-9).all(axis=1)
    middle = np.where(over, start+slope/2, np.inf)
    if not over.any() or middle.min() >= s.max():
        return s.max(), s.max()
    m = int(np.argmin(middle))
    return start[m], start[m]+slope[m]


def covered(piece, lo, hi):
    """The share of a fitting's box its near mesh fills, seen from above and from the front."""
    shares = []
    for axes, depth in (((0, 1), 2), ((0, 2), 1)):
        extent = np.maximum(hi[list(axes)]-lo[list(axes)], .25)
        size = np.maximum(1, np.ceil(extent*4).astype(int))
        index, _, _ = raster(piece['pos'][..., list(axes)], piece['pos'][..., depth], lo[list(axes)], size[0], size[1], 4)
        shares.append((index >= 0).mean())
    return min(shares)


def write(kit, model, faces, regions, folder='standard', out=None):
    """The pieces GLB with its far level, and the far atlas's sources."""
    directory = (out or DATA/'models/buildings')/folder
    sources = (out or MATERIALS)/f'{kit}-far'/'sources'
    sources.mkdir(parents=True, exist_ok=True)
    maps = atlas(regions, TONE.get(kit, 1.0), ATLAS_GLOW.get(kit, (1.0, None))[:2])
    tres = DATA/'models/board/textures/structures/buildings'/f'{kit}-far.tres'
    if kit in ATLAS_GLOW and out is None and tres.exists():
        # The far material's view falloff, kept by its later exports (tools/materials/export.py keeps metadata).
        falloff = ATLAS_GLOW[kit][2]
        raw = tres.read_bytes()
        eol = b'\r\n' if b'\r\n' in raw else b'\n'
        lines = [l for l in raw.split(eol) if not l.startswith(b'metadata/mmEmissionView')]
        while lines and not lines[-1]:
            lines.pop()
        if falloff:
            lines.append(f'metadata/mmEmissionView = "{falloff[0]:.4g} {falloff[1]:.4g}"'.encode())
        tres.write_bytes(eol.join(lines)+eol)
    Image.fromarray(np.round(maps['albedo'][..., :3]*255).astype(np.uint8), 'RGB').save(sources/'albedo.png')
    Image.fromarray(np.round(maps['albedo'][..., 3]*255).astype(np.uint8), 'L').save(sources/'paint-mask.png')
    Image.fromarray(np.round(maps['glow']*255).astype(np.uint8), 'RGB').save(sources/'window-emission.png')
    Image.fromarray(np.round(maps['orm']*255).astype(np.uint8), 'RGB').save(sources/'orm.png')
    Image.fromarray(np.round(maps['normal']*255).astype(np.uint8), 'RGB').save(sources/'normal.png')
    material = f'structures/buildings/{kit}-far'
    vertices, parts, nodes, kept = [], [], [], set()
    for name, made in faces.items():
        by_material = {}
        for item in [made] if isinstance(made, dict) else made:
            if isinstance(item, dict):
                # Triangles in their near materials: a sparse fitting's, a joint's fill, lit panes.
                for t in range(len(item['pos'])):
                    first = len(vertices)//12
                    for k in range(3):
                        vertices.extend([*item['pos'][t, k], *item['nrm'][t, k], *item['col'][t, k], *item['uv'][t, k]])
                    by_material.setdefault(str(item['mat'][t]), []).extend((first, first+1, first+2))
                kept.update(item['mat'].tolist())
                continue
            corners, normal, region, local = item
            first = len(vertices)//12
            # A face's texels in its region (from its bottom left), or its region's corners for a quad filling it.
            coords = uvs(region) if local is None else [((region.x+s)/ATLAS, (region.y+region.height-t)/ATLAS)
                                                        for s, t in local]
            for corner, uv in zip(corners, coords):
                vertices.extend([*corner, *normal, 1, 1, 1, 1, *uv])
            for k in range(1, len(corners)-1):
                by_material.setdefault(material, []).extend((first, first+k, first+k+1))
        refs = []
        for k, (key, indices) in enumerate(by_material.items()):
            parts.append({'id': f'{name}-far-{k}', 'type': 'TRIANGLES', 'indices': indices})
            refs.append({'meshpartid': f'{name}-far-{k}', 'materialid': key})
        nodes.append({'id': name+'-lod1', 'parts': refs, 'children': []})
    far = {'meshes': [{'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': vertices, 'parts': parts}],
           'nodes': nodes,
           'materials': [{'id': material, 'diffuse': [1, 1, 1], 'roughness': 1, 'metallic': 0,
                          'textures': [{'type': 'DIFFUSE', 'filename': f'../../board/textures/{material}_albedo.png'}],
                          'extras': {'mmBuildingPaint': True}}]+[m for m in model['materials'] if m['id'] in kept]}
    directory.mkdir(parents=True, exist_ok=True)
    write_glb(directory/f'{kit}-pieces.glb', levels={0: model, 1: far}, extras=model.get('extras') or None)
    # The kit says its far level is a closed hull (BayKit.Spec#hull): the game lays no roof body there.
    # The hull is its far level: no run lays another, and a roof's deck stands where it does near.
    spec = json.loads((DATA/'models/buildings'/folder/f'{kit}.json').read_text(encoding='utf-8'))
    for owner in [*spec['roofs'].values(), *spec['variants'], spec.get('shared', {})]:
        for runs in [owner.get('runs', [])] + [owner.get(role, []) for role in ('base', 'floor', 'top')]:
            for run in runs if isinstance(runs, list) else [runs]:
                run.pop('far', None)
    for roof in spec['roofs'].values():
        roof['heights'] = roof['heights'][:1]
    shared = {**spec.get('shared', {}), 'hull': True}
    spec = {key: value for key, value in spec.items() if key != 'shared'}
    spec = {**{key: spec[key] for key in ('style', 'pieces')}, 'shared': shared,
            **{key: value for key, value in spec.items() if key not in ('style', 'pieces')}}
    (directory/f'{kit}.json').write_text(kit_json.dumps(spec)+'\n', encoding='utf-8', newline='\n')
    return sum(len(p['indices'])//3 for p in parts)


if __name__ == '__main__' and len(sys.argv) > 1:
    arguments = sys.argv[1:]
    out = None
    if arguments[0] == '--out':
        out, arguments = Path(arguments[1]), arguments[2:]
    for name in arguments:
        # A kit of another folder as <folder>/<kit>: civic/civic.
        folder, _, kit = name.rpartition('/')
        folder = folder or 'standard'
        model, faces, regions, wall, chain = far_kit(kit, folder)
        triangles = write(kit, model, faces, regions, folder, out=out)
        print('FAR', kit, 'pieces', len(faces), 'triangles', triangles, 'regions', len(regions))
        for name in sorted(faces):
            made = faces[name]
            count = sum(len(item['pos']) if isinstance(item, dict) else len(item[0])-2
                        for item in ([made] if isinstance(made, dict) else made))
            shape = (f'face {wall[name][0]:6.2f} {wall[name][1]:6.2f}' if name in wall else
                     'profile '+' '.join(f'({y:.2f} {z:.2f})' for y, z in chain[name]) if name in chain else 'fitting')
            print(f'  {name:26s} triangles {count:3d} {shape}')
