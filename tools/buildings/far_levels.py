"""The standard building kits' far level: a closed outer hull, each wall piece one face, textured from the kit's far atlas.

Run after standard_buildings.py, with the system Python (numpy, Pillow, SciPy):
    python far_levels.py building-hard [building-medium ...]
then export the far material: python ../materials/export.py structures/buildings/<kit>-far/<kit>-far.ptex

A kit's pieces GLB keeps its near level (lod0) and takes a far level (lod1) of the same pieces: every wall piece (a bay, an
entrance, an end) becomes one face on its storey's outer plane, with no wall thickness, no reveals, frames, sills or
mullions; a roof's edge its outer face, its top and the face towards the roof; a roof fitting one box (planes). Where a
ground storey stands further out than the storeys above, a ledge closes its top. A far face shows what the near piece shows
through it: its atlas region is baked by rays along the iso camera's view (BAKE_ELEVATION), head on, so a slab's top and a
recessed window read where they do near, its albedo dimmed by the sky the piece hides (daylight) and its windows' glow
brought to what the camera sees of them aside (GLOW_AZIMUTHS). The atlas (sources of
tools/materials/structures/buildings/<kit>-far) holds the albedo, its building paint (the near level's #paint surfaces,
which a building's tint colours) as a mask, the lit windows' night glow, roughness and metallic, and normals. The kit's
JSON says `hull` (BayKit.Spec#hull). Far levels past it repeat it: the GLB has two levels.
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
# The azimuths off a face's normal its lit windows' glow is measured at, each weighted by the share of the screen a face
# seen so takes: the iso camera sees a hex's walls 15, 45 or 75 degrees aside (a Square footprint's 45), never head on, and
# a recessed window shows less of its glass the further aside. A face's windows are baked head on, sharp, and glow as
# much in all as they do on average over these.
GLOW_AZIMUTHS = tuple(math.radians(side*a) for a in (15, 45, 75) for side in (-1, 1))
# The share of that glow a far window gives: spread by its texture's filtering over more pixels than a near window's few
# saturated ones, the same light shows brighter on screen (measured: 0.55 to 0.69 of the far windows' displayed light
# above mid grey matched the near's, by night, on the five kits).
GLOW_SCALE = .6
EDGE_TOP = 1.5  # How far under a roof edge's top its far box's top reaches in (edge_profile).
FITTING_COVER = .4  # A fitting filling less of its box than this, from above or the front, keeps its near mesh.
PLANE_SHARE = .05  # A piece's plane: the outermost depth at least this share of its front lies at or in front of.
LEDGE = .5  # A ground storey standing out less than this leaves no ledge: the storeys above stand on its plane.
DENSITY = 2  # Atlas texels a unit: the far level shows at most 1.06 pixels a unit (a hex 88 pixels wide).
SAMPLES = 3  # Rays a texel, along each side.
PAD = 4  # Texels round each region, its edge texels repeated.
ATLAS = 512
ALIGN = 8  # Regions start and end on multiples of this, so the first mip levels stay within them.


# -- The near level --------------------------------------------------------------------------------------------------

def near_pieces(glb):
    """The near level's pieces: name -> triangles (N,3,3), their normals (N,3,3), colours (N,3,4), UVs (N,3,2), materials."""
    model = read_glb(glb, 0)
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
    pieces with their deck heights and surfaces, the fittings, each piece's materials textured along the wall's line (its
    run's planar), and each variant's sidewalk material (None without one)."""
    shared = spec.get('shared', {})
    walls, fittings, planar, sidewalks = {}, set(), {}, {}

    def runs(entries, defaults, into):
        for entry in entries:
            run = {**defaults, **entry}
            bay = run.get('bay', shared.get('bay'))
            laid = {name: bay for name in run.get('bays', []) + ([run['entrance']] if run.get('entrance') else [])}
            for key in ('ends', 'under', 'round', 'shallow', 'seam'):
                if run.get(key):
                    laid[run[key]['piece']] = run[key]['length']
            if run.get('joints'):
                raise ValueError('far_levels lays plain runs: no joints')
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
        roofs[name] = (pieces, roof['heights'][0], roof['material'], roof['repeat'])
    return walls, roofs, fittings, planar, sidewalks


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


def planes(near, walls, roofs, spec):
    """Each wall piece's plane (its y): a variant's storey on the median of its pieces' own outermost planes (a porch or
    a canopy in one bay leaves the storey's plane where its other bays stand), its upper storeys on its ground storey's
    where that lies less than LEDGE further out, a roof's edges on one plane as far out as the outermost of their own and
    the storey under them; and per variant, where its ground storey stands further out than its upper storeys, the ledge
    (from, to) its ground storey's top closes."""
    storeys = {}
    for (variant, role), pieces in walls.items():
        storeys[variant, role] = float(np.median([outermost(near[name], length) for name, length in pieces.items()]))
    plane, ledges = {}, {}
    for variant in spec['variants']:
        name = variant.get('name', 'default')
        base, floor = storeys.get((name, 'base')), storeys.get((name, 'floor'))
        if base is not None and floor is not None and base < floor:
            if floor-base < LEDGE:
                storeys[name, 'floor'] = floor = base
            else:
                ledges[name] = (base, floor)
        under = floor if floor is not None else base
        for roof_name in [variant.get('roof', spec.get('shared', {}).get('roof'))] + ([variant['vaulted']] if 'vaulted' in variant else []):
            edges = roofs[roof_name][0]
            # One plane for a roof's edge pieces, as far out as the outermost of them and the storey under them.
            outer = min([outermost(near[piece], length) for piece, length in edges.items()]+[under-ROOF_INSET])
            for piece in edges:
                plane[piece] = min(plane.get(piece, np.inf), outer)
    for (variant, role), pieces in walls.items():
        for name in pieces:
            plane[name] = min(plane.get(name, np.inf), storeys[variant, role])
    return plane, ledges


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
            glow = np.zeros((1, 1, 3))
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
                glow = box(srgb_linear(emitted))*tint+(colour*energy if spec['emission_operator'] == 0 else 0)
            paint = 'paint' in flags or bool(self.extras.get(key, {}).get('mmBuildingPaint'))
            self.cache[key] = {'albedo': albedo, 'paint': paint, 'glow': glow, 'orm': orm, 'name': name}
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


def bake(view, triangles, finishes, planar, shade=True):
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
        albedo[hit] = rgb*(1-DIRECT*(1-daylight(pos+smooth*.05, smooth, occluders)))[:, None] if shade else rgb
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


def flat(length, y0, z, material, repeat=12):
    """A level surface in front of and under a piece (the street before a ground storey, a roof's deck behind its edge),
    for the rays that pass by the piece."""
    x0, x1, y1 = -length, 2*length, 60
    pos = np.array([[[x0, y0, z], [x1, y0, z], [x1, y1, z]], [[x0, y0, z], [x1, y1, z], [x0, y1, z]]], dtype=np.float64)
    return {'pos': pos, 'nrm': np.tile([0, 0, 1.0], (2, 3, 1)), 'col': np.ones((2, 3, 4)), 'uv': pos[..., :2]/repeat,
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


def atlas(regions):
    """The atlas maps: albedo RGBA (paint in A), glow RGB, ORM RGB (occlusion 1, roughness, metallic); every texel outside
    a region takes its nearest region texel's values, so mip levels keep the regions' colours."""
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
    albedo = np.dstack([linear_srgb(out['albedo']), out['paint']])
    orm = np.dstack([np.ones((ATLAS, ATLAS)), out['rough'], out['metal']])
    return {'albedo': albedo, 'glow': linear_srgb(out['glow']), 'orm': orm, 'normal': out['normal']*.5+.5}


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
    walls, roofs, fittings, planar, sidewalks = layout(spec)
    finishes = Finishes(model['materials'])
    plane, ledges = planes(near, walls, roofs, spec)
    regions, faces = [], {}

    def region(name, view, triangles, aside=()):
        """A face's region, its glow GLOW_SCALE of what the camera sees of it; a wall's of what it sees aside, on average."""
        maps = bake(view, triangles, finishes, planar.get(name.split(' ')[0], {}))
        if maps['glow'].any():
            seen_aside = maps['glow'].sum()
            if aside:
                weights = [-v.ray @ np.cross(v.u, v.w) for v in aside]
                seen_aside = np.average([bake(v, triangles, finishes, planar.get(name, {}), shade=False)['glow'].sum()
                                         for v in aside], weights=weights)
            maps['glow'] *= GLOW_SCALE*seen_aside/maps['glow'].sum()
        made = Region(name, maps)
        regions.append(made)
        return made

    def seen(origin, u, w, width, height, azimuth=0.0):
        """A face's view as the iso camera sees it from BAKE_ELEVATION, azimuth aside of head on."""
        u, w = np.asarray(u, dtype=np.float64), np.asarray(w, dtype=np.float64)
        c, s = math.cos(BAKE_ELEVATION), math.sin(BAKE_ELEVATION)
        ray = c*(-math.cos(azimuth)*np.cross(u, w)+math.sin(azimuth)*u)-s*np.array([0, 0, 1.0])
        return View(origin, u, w, ray, width, height)

    def aside(origin, u, w, width, height):
        return [seen(origin, u, w, width, height, a) for a in GLOW_AZIMUTHS]

    def down(origin, u, w, width, height):
        return View(origin, u, w, (0, 0, -1), width, height)

    roles = {}
    for (variant, role), pieces in walls.items():
        for name, length in pieces.items():
            roles[name] = (role, length, variant)
    for name, (role, length, variant) in sorted(roles.items()):
        piece, y = near[name], plane[name]
        width, height = round(length*DENSITY), round(LEVEL*DENSITY)
        # The same piece beside it and over it (under it, a storey's), as the rays that leave its own see them; under a
        # ground storey its sidewalk.
        row = joined(*(shifted(piece, 0, k*length) for k in (-2, -1, 0, 1, 2)))
        around = joined(row, shifted(row, LEVEL)) if role == 'base' else joined(shifted(row, -LEVEL), row, shifted(row, LEVEL))
        if role == 'base' and sidewalks[variant]:
            around = joined(around, flat(length, y-20, 0, sidewalks[variant]))
        front = region(name, seen((0, y, 0), (1, 0, 0), (0, 0, 1), width, height), around,
                       aside=aside((0, y, 0), (1, 0, 0), (0, 0, 1), width, height))
        quads = [([(0, y, 0), (length, y, 0), (length, y, LEVEL), (0, y, LEVEL)], (0, -1, 0), front)]
        if role == 'base' and variant in ledges:
            out, inner = ledges[variant]
            top = region(name+' ledge', down((0, out, LEVEL), (1, 0, 0), (0, 1, 0), width, max(1, round((inner-out)*DENSITY))), piece)
            quads.append(([(0, out, LEVEL), (length, out, LEVEL), (length, inner, LEVEL), (0, inner, LEVEL)], (0, 0, 1), top))
        faces[name] = quads
    for roof_name, (pieces, deck, deck_material, repeat) in roofs.items():
        for name, length in pieces.items():
            pos = near[name]['pos']
            row = joined(*(shifted(near[name], 0, k*length) for k in (-2, -1, 0, 1, 2)))
            piece, y = joined(row, flat(length, -ROOF_INSET, deck-.02, deck_material, repeat)), plane[name]
            z0, z1, inner = edge_profile(near[name], length)
            width = round(length*DENSITY)
            front = region(name, seen((0, y, z0), (1, 0, 0), (0, 0, 1), width, max(1, round((z1-z0)*DENSITY))), piece)
            top = region(name+' top', down((0, y, z1), (1, 0, 0), (0, 1, 0), width, max(1, round((inner-y)*DENSITY))), piece)
            quads = [([(0, y, z0), (length, y, z0), (length, y, z1), (0, y, z1)], (0, -1, 0), front),
                     ([(0, y, z1), (length, y, z1), (length, inner, z1), (0, inner, z1)], (0, 0, 1), top)]
            floor = deck-.05
            if z1 > floor+.1:
                back = region(name+' back', seen((length, inner, floor), (-1, 0, 0), (0, 0, 1), width, max(1, round((z1-floor)*DENSITY))),
                              piece)
                quads.append(([(length, inner, floor), (0, inner, floor), (0, inner, z1), (length, inner, z1)], (0, 1, 0), back))
            faces[name] = quads
    for name in sorted(fittings):
        piece = near[name]
        lo, hi = piece['pos'].reshape(-1, 3).min(axis=0), piece['pos'].reshape(-1, 3).max(axis=0)
        size = hi-lo
        if covered(piece, lo, hi) < FITTING_COVER:
            # A sparse fitting (a washing line, a mast, a pipe) would be a solid block as a box: it keeps its near mesh.
            faces[name] = piece
            continue
        top = region(name+' top', down((lo[0], lo[1], hi[2]), (1, 0, 0), (0, 1, 0), max(1, round(size[0]*DENSITY)),
                                       max(1, round(size[1]*DENSITY))), piece)
        side = region(name+' side', View((lo[0], lo[1], lo[2]), (1, 0, 0), (0, 0, 1), (0, 1, 0), max(1, round(size[0]*DENSITY)),
                                         max(1, round(size[2]*DENSITY))), piece)
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        faces[name] = [
            ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), top),
            ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0), side),
            ([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], (0, 1, 0), side),
            ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0), side),
            ([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], (-1, 0, 0), side)]
    pack(regions)
    unlaid = sorted(set(near) - set(faces))
    if unlaid:
        print('  no far level for pieces the kit does not lay:', ', '.join(unlaid))
    return model, faces, regions, plane, ledges


def edge_profile(piece, length):
    """A roof edge's far box over its near piece's front: its bottom, its top (as high as the front covers half its length:
    a railing or a post over a parapet is not its top) and how far in its top reaches (the piece's furthest point within
    EDGE_TOP of that top: a deck strip lower down is not the edge)."""
    depth, z0 = front(piece, length)
    rows = np.isfinite(depth).mean(axis=1)[::-1]
    full = np.nonzero(rows >= .5)[0]
    z1 = min(z0+(full.max()+1)/4, float(piece['pos'][..., 2].max())) if len(full) else float(piece['pos'][..., 2].max())
    pos = piece['pos'].reshape(-1, 3)
    upper = pos[pos[:, 2] >= z1-EDGE_TOP]
    return z0, z1, float((upper if len(upper) else pos)[:, 1].max())


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
    maps = atlas(regions)
    Image.fromarray(np.round(maps['albedo'][..., :3]*255).astype(np.uint8), 'RGB').save(sources/'albedo.png')
    Image.fromarray(np.round(maps['albedo'][..., 3]*255).astype(np.uint8), 'L').save(sources/'paint-mask.png')
    Image.fromarray(np.round(maps['glow']*255).astype(np.uint8), 'RGB').save(sources/'window-emission.png')
    Image.fromarray(np.round(maps['orm']*255).astype(np.uint8), 'RGB').save(sources/'orm.png')
    Image.fromarray(np.round(maps['normal']*255).astype(np.uint8), 'RGB').save(sources/'normal.png')
    material = f'structures/buildings/{kit}-far'
    vertices, parts, nodes, kept = [], [], [], set()
    for name, made in faces.items():
        by_material = {}
        if isinstance(made, dict):
            # A sparse fitting's near triangles, in its near materials.
            for t in range(len(made['pos'])):
                first = len(vertices)//12
                for k in range(3):
                    vertices.extend([*made['pos'][t, k], *made['nrm'][t, k], *made['col'][t, k], *made['uv'][t, k]])
                by_material.setdefault(str(made['mat'][t]), []).extend((first, first+1, first+2))
            kept.update(by_material)
        else:
            for corners, normal, region in made:
                first = len(vertices)//12
                for corner, uv in zip(corners, uvs(region)):
                    vertices.extend([*corner, *normal, 1, 1, 1, 1, *uv])
                by_material.setdefault(material, []).extend((first, first+1, first+2, first, first+2, first+3))
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
    for kit in arguments:
        model, faces, regions, plane, ledges = far_kit(kit)
        triangles = write(kit, model, faces, regions, out=out)
        print('FAR', kit, 'pieces', len(faces), 'triangles', triangles, 'regions', len(regions), 'ledges', ledges)
        for name in sorted(faces):
            made = faces[name]
            count = len(made['pos']) if isinstance(made, dict) else 2*len(made)
            print(f'  {name:26s} plane {plane.get(name, float("nan")):6.2f} triangles {count}')
