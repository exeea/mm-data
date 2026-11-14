"""Far levels of authored buildings: a closed hull just outside the near level, its faces textured from a baked atlas.

Run after the building's own script, with the system Python (numpy, Pillow, SciPy):
    python authored_far.py [heritage-cathedral ...]
Without names it makes BUILDINGS' far levels, replacing those the script wrote.

A far level draws while the building's larger side, counting at most five hexes, is under 80 pixels (LOD1) or 24 (LOD2):
TreeLod.PROPS, each shown up to 10 % past that, so at the largest size a level shows a pixel is that side over
LEVEL_PIXELS. The hull is the near level closed over gaps narrower than 2*CLOSE pixels and over the hollow inside no camera
view sees, offset OFFSET pixels outward (it encloses the near level, as the shadow map needs: a far surface inside the near
one darkens), found on a grid of VOXEL pixels and simplified to within ERROR pixels; its underside stays open, as the near
level's. Its faces are grouped into nearly flat charts, laid flat in one atlas for both levels (512 texels at most), and
baked by rays from the hull in to the near level: albedo, dimmed by the sky the near level's own parts hide (as its shadows
do), the building paint's share of it (the alpha, mmPaintMask), its glow, roughness and metallic, and the near level's
normals. The atlas's images are the GLB's own. The near level's lit panes stand on each far hull as geometry in their own
materials (panes), so a lit window lights there as it does near; the atlas has no glow where they stand. The near level,
the volumes and the file's extras stay as they are.
"""
import heapq
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'blender/mm_materials'))
import building_lod  # noqa: E402
import far_levels as fl  # noqa: E402
import glb  # noqa: E402

AUTHORED = HERE.parents[1]/'data/models/buildings/authored'
# The buildings whose far levels this makes: those whose level switches it brings close to the near level by day and night.
BUILDINGS = ('heritage-administrative-offices', 'heritage-cathedral', 'heritage-church', 'heritage-commercial-center',
             'heritage-government-hall', 'heritage-medical-center', 'imperial-courtyard-habitat', 'imperial-government-hall',
             'imperial-industrial-works', 'imperial-transit-terminal', 'frontier-power-plant', 'frontier-trade-exchange')
LEVEL_PIXELS = {1: 88.0, 2: 26.4}  # The largest size each level shows: TreeLod.PROPS and its 10 % hysteresis.
PROPS_SIDE = 415.0  # The longest side that counts (TreeLod.PROPS_SIDE).
VOXEL = .4  # The grid, in pixels.
OFFSET = .25  # How far out the hull stands, in pixels.
CLOSE = 1.5  # Gaps narrower than twice this close, in pixels.
ERROR = .3  # How far the simplified hull may stray from the closed surface, in pixels (root mean square).
SAMPLE = .25  # Points on the near level's triangles, in voxels apart.
# Where the hull's outside may reach: what a camera sees from these (elevation, azimuth) in degrees.
VIEWS = [(e, a) for e in (20, 35.26, 55) for a in range(0, 360, 45)]+[(90, 0)]
CHART_ANGLE = 35  # A chart's faces turn at most this far from its first, in degrees.
MERGE_ANGLE = 75  # A chart smaller than SMALLEST joins a neighbour that turns at most this far from it, in degrees.
SMALLEST = 3  # In atlas texels across.
SMOOTH_ANGLE = 35  # A vertex's normal averages the faces round it within this angle of each face, in degrees.
TEXELS = 2.0  # Atlas texels a pixel at the largest size a level shows.
SUBSAMPLES = 2  # Rays a texel, along each side.
ATLASES = (128, 256, 512)  # The atlas takes the smallest that holds both levels.
PAD = 2  # Texels round each chart, its edge texels repeated.
FRONT = .75  # How far in front of the hull a near surface may lie and still be what a ray meets, in pixels.
BACK = 3.0  # How far behind it, in pixels.
THROUGH = 12.0  # How far behind blended glass, in pixels.
PANE_DEPTH = 1.0  # A lit pane at most this far inside the hull stands on it (panes), in pixels.


# -- The near level -------------------------------------------------------------------------------------------------

def surface_points(pos, spacing):
    """Points on every triangle (N,3,3), no two further apart than spacing along an edge."""
    a, b, c = pos[:, 0], pos[:, 1], pos[:, 2]
    longest = np.maximum.reduce([np.linalg.norm(b-a, axis=1), np.linalg.norm(c-b, axis=1), np.linalg.norm(a-c, axis=1)])
    steps = np.maximum(1, np.ceil(longest/spacing)).astype(int)
    points = [pos.reshape(-1, 3)]
    for n in np.unique(steps):
        chosen = steps == n
        i, j = np.meshgrid(np.arange(n+1), np.arange(n+1), indexing='ij')
        keep = i+j <= n
        s, t = (i[keep]/n)[None, :, None], (j[keep]/n)[None, :, None]
        points.append((a[chosen, None]+s*(b-a)[chosen, None]+t*(c-a)[chosen, None]).reshape(-1, 3))
    return np.concatenate(points)


# -- The hull ---------------------------------------------------------------------------------------------------------

def seen(pos, points, voxel):
    """Whether each point lies in front of the near level's triangles (N,3,3) along at least one of VIEWS."""
    result = np.zeros(len(points), dtype=bool)
    for elevation, azimuth in VIEWS:
        e, a = math.radians(elevation), math.radians(azimuth)
        forward = np.array([-math.sin(a)*math.cos(e), math.cos(a)*math.cos(e), -math.sin(e)])
        right = np.cross(forward, (0, 0, 1.0)) if elevation < 90 else np.array([1.0, 0, 0])
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)
        xy = np.stack([pos@right, pos@up], axis=-1)
        low = xy.reshape(-1, 2).min(axis=0)-voxel
        width, height = np.ceil((xy.reshape(-1, 2).max(axis=0)+voxel-low)/voxel).astype(int)+1
        _, depth, _ = fl.raster(xy, pos@forward, low, width, height, 1/voxel)
        column = np.floor((points@right-low[0])/voxel).astype(int)
        row = height-1-np.floor((points@up-low[1])/voxel).astype(int)
        inside = (column >= 0) & (column < width) & (row >= 0) & (row < height)
        nearest = np.full(len(points), np.inf)
        nearest[inside] = depth[row[inside], column[inside]]
        result |= points@forward < nearest-voxel
    return result


def closed_field(pos, voxel, offset, close):
    """The hull's field on a grid: positive outside, zero offset beyond the near level closed over gaps narrower than
    2*close. Returns (field, origin of sample 0, the near level's points tree)."""
    points = surface_points(pos, voxel*SAMPLE)
    tree = cKDTree(points)
    pad = close+3*voxel
    low, high = points.min(axis=0)-pad, points.max(axis=0)+pad
    shape = np.ceil((high-low)/voxel).astype(int)+1
    grid = np.stack(np.meshgrid(*(low[k]+voxel*np.arange(shape[k]) for k in range(3)), indexing='ij'), axis=-1).reshape(-1, 3)
    distance, _ = tree.query(grid, distance_upper_bound=close+2*voxel, workers=-1)
    distance = distance.reshape(shape)
    # The outside eroded by close: the free space a ball of that radius reaches from the grid's edge, through what some
    # view sees. A building is hollow: through a portal the whole of it would be outside.
    free = (distance > close).ravel()
    free[free] = seen(pos, grid[free], voxel)
    labels, _ = ndimage.label(free.reshape(shape))
    edge = np.unique(np.concatenate([labels[0].ravel(), labels[-1].ravel(), labels[:, 0].ravel(), labels[:, -1].ravel(),
                                     labels[:, :, 0].ravel(), labels[:, :, -1].ravel()]))
    outside = np.isin(labels, edge[edge > 0])
    # The closed level: within close of that space is outside it. The distance to it on the grid can be short of the
    # truth by up to a cell's half diagonal, and where nothing closes the near level's own distance is exact: the nearer
    # of the two, the grid's lifted by its error.
    reach = ndimage.distance_transform_edt(~outside)*voxel
    closed = np.minimum(distance, close-reach+voxel*math.sqrt(3)/2)
    # Nothing under the ground: the near level stands on its lowest point.
    closed[:, :, low[2]+voxel*np.arange(shape[2]) < pos[..., 2].min()-offset] = offset+voxel
    return closed-offset, low, tree


def surface_nets(field, origin, voxel):
    """The zero surface of a grid field (positive outside) as triangles facing out: (vertices, faces)."""
    inside = field < 0
    nx, ny, nz = field.shape
    cells = np.full((nx-1, ny-1, nz-1), -1, dtype=np.int64)
    total = np.zeros((nx-1, ny-1, nz-1, 3))
    count = np.zeros((nx-1, ny-1, nz-1))
    edges = []
    for axis in range(3):
        a = [slice(None)]*3
        b = [slice(None)]*3
        a[axis], b[axis] = slice(0, -1), slice(1, None)
        fa, fb = field[tuple(a)], field[tuple(b)]
        crossing = inside[tuple(a)] != inside[tuple(b)]
        index = np.argwhere(crossing)
        t = fa[crossing]/(fa[crossing]-fb[crossing])
        point = index.astype(float)
        point[:, axis] += t
        edges.append((axis, index, inside[tuple(a)][crossing]))
        # The four cells round the edge each take its crossing point.
        others = [k for k in range(3) if k != axis]
        for d0 in (-1, 0):
            for d1 in (-1, 0):
                cell = index.copy()
                cell[:, others[0]] += d0
                cell[:, others[1]] += d1
                ok = np.all((cell >= 0) & (cell < np.array(cells.shape)), axis=1)
                np.add.at(total, tuple(cell[ok].T), point[ok])
                np.add.at(count, tuple(cell[ok].T), 1)
    used = count > 0
    cells[used] = np.arange(used.sum())
    vertices = origin+voxel*(total[used]/count[used, None])
    faces = []
    for axis, index, starts_inside in edges:
        others = [k for k in range(3) if k != axis]
        corners = []
        for d0, d1 in ((-1, -1), (0, -1), (0, 0), (-1, 0)):
            cell = index.copy()
            cell[:, others[0]] += d0
            cell[:, others[1]] += d1
            corners.append(cell)
        ok = np.all([np.all((c >= 0) & (c < np.array(cells.shape)), axis=1) for c in corners], axis=0)
        quad = np.stack([cells[tuple(c[ok].T)] for c in corners], axis=1)
        # The corners run counter-clockwise round the axis seen from its positive end, except round y: (x, z) turns the
        # other way. A face looks out of the inside.
        flip = starts_inside[ok] if axis == 1 else ~starts_inside[ok]
        quad[flip] = quad[flip][:, ::-1]
        # Along the shorter diagonal.
        p = vertices[quad]
        short = np.linalg.norm(p[:, 0]-p[:, 2], axis=1) <= np.linalg.norm(p[:, 1]-p[:, 3], axis=1)
        faces.append(np.where(short[:, None], quad[:, [0, 1, 2]], quad[:, [0, 1, 3]]))
        faces.append(np.where(short[:, None], quad[:, [0, 2, 3]], quad[:, [1, 2, 3]]))
    return vertices, np.concatenate(faces)


def simplify(vertices, faces, error, keep_out=None):
    """Edge collapses by quadric error (Garland and Heckbert) while the surface stays within `error` (root mean square)
    of the planes it merged; keep_out(point) is negative where a moved vertex would come too near what the hull must
    enclose. Plain floats: numpy costs more than it saves on 4 x 4 matrices. Returns (vertices, faces) compacted."""
    a, b, c = (vertices[faces[:, k]] for k in range(3))
    cross = np.cross(b-a, c-a)
    area = np.linalg.norm(cross, axis=1)/2
    normal = cross/np.maximum(2*area, 1e-12)[:, None]
    d = -np.einsum('ij,ij->i', normal, a)
    nx, ny, nz = normal.T
    # The quadric's ten coefficients a2, ab, ac, ad, b2, bc, bd, c2, cd, d2, by area.
    terms = area[:, None]*np.column_stack((nx*nx, nx*ny, nx*nz, nx*d, ny*ny, ny*nz, ny*d, nz*nz, nz*d, d*d))
    quadric = np.zeros((len(vertices), 10))
    weight = np.zeros(len(vertices))
    for k in range(3):
        np.add.at(quadric, faces[:, k], terms)
        np.add.at(weight, faces[:, k], area)
    quadric, weight = quadric.tolist(), weight.tolist()
    points = vertices.tolist()
    faces = faces.tolist()
    alive = [True]*len(faces)
    around = [set() for _ in points]
    for f, face in enumerate(faces):
        for v in face:
            around[v].add(f)
    stamp = [0]*len(points)
    dead = [False]*len(points)

    def place(i, j):
        q = [x+y for x, y in zip(quadric[i], quadric[j])]
        a2, ab, ac, ad, b2, bc, bd, c2, cd, d2 = q
        total = max(weight[i]+weight[j], 1e-12)

        def cost(x, y, z):
            return max(0.0, a2*x*x+2*ab*x*y+2*ac*x*z+2*ad*x+b2*y*y+2*bc*y*z+2*bd*y+c2*z*z+2*cd*z+d2)/total
        pi, pj = points[i], points[j]
        options = [pi, pj, [(u+v)/2 for u, v in zip(pi, pj)]]
        det = a2*(b2*c2-bc*bc)-ab*(ab*c2-bc*ac)+ac*(ab*bc-b2*ac)
        if abs(det) > 1e-9*max(1.0, a2, b2, c2)**3:
            # Cramer's rule on the gradient's zero.
            r0, r1, r2 = -ad, -bd, -cd
            x = (r0*(b2*c2-bc*bc)-ab*(r1*c2-bc*r2)+ac*(r1*bc-b2*r2))/det
            y = (a2*(r1*c2-bc*r2)-r0*(ab*c2-bc*ac)+ac*(ab*r2-r1*ac))/det
            z = (a2*(b2*r2-r1*bc)-ab*(ab*r2-r1*ac)+r0*(ab*bc-b2*ac))/det
            options.insert(0, [x, y, z])
        best = None
        for x in options:
            value = cost(*x)
            if best is None or value < best[0]-1e-12:
                best = (value, x)
        return best

    def area2(p0, p1, p2):
        ux, uy, uz = p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]
        vx, vy, vz = p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]
        return uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx

    heap = []
    seen = set()
    for face in faces:
        for k in range(3):
            i, j = sorted((face[k], face[(k+1) % 3]))
            if (i, j) not in seen:
                seen.add((i, j))
                heap.append((place(i, j)[0], i, j, 0, 0))
    heapq.heapify(heap)
    limit = error*error
    while heap:
        cost, i, j, si, sj = heapq.heappop(heap)
        if cost > limit:
            break
        if dead[i] or dead[j]:
            continue
        shared = around[i] & around[j]
        if not shared:
            continue
        if (si, sj) != (stamp[i], stamp[j]):
            heapq.heappush(heap, (place(i, j)[0], i, j, stamp[i], stamp[j]))
            continue
        if len(shared) != 2:
            continue
        # The link condition: the edge's two ends share only the two faces' third corners as neighbours.
        ni = {v for f in around[i] for v in faces[f]}
        nj = {v for f in around[j] for v in faces[f]}
        thirds = {v for f in shared for v in faces[f]}
        if ni & nj != thirds:
            continue
        cost, x = place(i, j)
        # No face may turn over or close up.
        ok = True
        for f in (around[i] | around[j])-shared:
            face = faces[f]
            corners = [x if v == i or v == j else points[v] for v in face]
            new = area2(*corners)
            old = area2(*(points[v] for v in face))
            dot = new[0]*old[0]+new[1]*old[1]+new[2]*old[2]
            length = math.sqrt(new[0]**2+new[1]**2+new[2]**2)
            if length < 1e-9 or dot < .2*length*math.sqrt(old[0]**2+old[1]**2+old[2]**2):
                ok = False
                break
        if not ok or (keep_out is not None and keep_out(x) < 0):
            continue
        points[i] = x
        quadric[i] = [u+v for u, v in zip(quadric[i], quadric[j])]
        weight[i] += weight[j]
        dead[j] = True
        stamp[i] += 1
        for f in shared:
            alive[f] = False
            for v in faces[f]:
                around[v].discard(f)
        for f in around[j]:
            faces[f] = [i if v == j else v for v in faces[f]]
            around[i].add(f)
        around[j] = set()
        for k in {v for f in around[i] for v in faces[f]}-{i}:
            p, q = (i, k) if i < k else (k, i)
            heapq.heappush(heap, (place(p, q)[0], p, q, stamp[p], stamp[q]))
    kept = np.asarray([f for f, a in zip(faces, alive) if a], dtype=np.int64)
    used, inverse = np.unique(kept, return_inverse=True)
    return np.asarray(points)[used], inverse.reshape(-1, 3)


def charts(vertices, faces, smallest):
    """Faces grouped into charts, each grown from its largest face over edges to faces within CHART_ANGLE of it, then
    each chart smaller than `smallest` (an area) joined to the neighbour it turns least from, up to MERGE_ANGLE: a sliver
    would cost the atlas more padding than texels. Each face's chart, and the faces' normals and areas."""
    p = vertices[faces]
    cross = np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])
    double = np.linalg.norm(cross, axis=1)
    normal = cross/np.maximum(double, 1e-12)[:, None]
    by_edge = {}
    for f, (a, b, c) in enumerate(faces.tolist()):
        for i, j in ((a, b), (b, c), (c, a)):
            by_edge.setdefault((min(i, j), max(i, j)), []).append(f)
    neighbours = [[] for _ in faces]
    for shared in by_edge.values():
        for f in shared:
            neighbours[f].extend(g for g in shared if g != f)
    chart = np.full(len(faces), -1)
    limit = math.cos(math.radians(CHART_ANGLE))
    count = 0
    for seed in np.argsort(-double).tolist():
        if chart[seed] >= 0:
            continue
        chart[seed] = count
        stack = [seed]
        while stack:
            f = stack.pop()
            for g in neighbours[f]:
                if chart[g] < 0 and normal[g]@normal[seed] >= limit:
                    chart[g] = count
                    stack.append(g)
        count += 1
    area = double/2
    sums = np.zeros((count, 3))
    np.add.at(sums, chart, normal*area[:, None])
    sizes = np.bincount(chart, area, count)
    limit = math.cos(math.radians(MERGE_ANGLE))
    for small in np.argsort(sizes).tolist():
        if sizes[small] >= smallest:
            break
        mine = np.flatnonzero(chart == small)
        around = {chart[g] for f in mine.tolist() for g in neighbours[f]}-{small}
        own = sums[small]/max(np.linalg.norm(sums[small]), 1e-12)
        best = max(around, key=lambda k: own@sums[k]/max(np.linalg.norm(sums[k]), 1e-12), default=None)
        if best is not None and own@sums[best]/max(np.linalg.norm(sums[best]), 1e-12) >= limit:
            chart[mine] = best
            sums[best] += sums[small]
            sizes[best] += sizes[small]
            sizes[small] = 0
    _, chart = np.unique(chart, return_inverse=True)
    return chart.ravel(), normal, area


def corner_normals(vertices, faces, normal, area):
    """Each face corner's normal: the faces at its vertex within SMOOTH_ANGLE of the face's own, by area."""
    limit = math.cos(math.radians(SMOOTH_ANGLE))
    at = [[] for _ in vertices]
    for f, face in enumerate(faces.tolist()):
        for v in face:
            at[v].append(f)
    result = np.zeros((len(faces), 3, 3))
    for f, face in enumerate(faces.tolist()):
        for k, v in enumerate(face):
            near = [g for g in at[v] if normal[g]@normal[f] >= limit]
            total = (normal[near]*area[near, None]).sum(axis=0)
            result[f, k] = total/max(np.linalg.norm(total), 1e-12)
    return result


class Chart:
    """A chart's frame: its plane's axes (u along, w up its region, n out) and its faces' corners in them."""

    def __init__(self, faces, corners, normal, area):
        n = (normal[faces]*area[faces, None]).sum(axis=0)
        self.n = n/np.linalg.norm(n)
        up = np.array([0, 0, 1.0]) if abs(self.n[2]) < .9 else np.array([0, 1.0, 0])
        self.u = np.cross(up, self.n)
        self.u /= np.linalg.norm(self.u)
        self.w = np.cross(self.n, self.u)
        self.faces = faces
        self.flat = np.stack([corners@self.u, corners@self.w], axis=-1)
        self.low, self.high = self.flat.reshape(-1, 2).min(axis=0), self.flat.reshape(-1, 2).max(axis=0)
        self.x = self.y = None

    def size(self, density):
        return np.maximum(1, np.ceil((self.high-self.low)*density).astype(int))


def pack(sizes, atlas):
    """Shelves of (width, height) regions, tallest first, PAD texels round each: their corners, or None if they do not
    fit."""
    places = [None]*len(sizes)
    x = y = shelf = 0
    for k in sorted(range(len(sizes)), key=lambda k: (-sizes[k][1], -sizes[k][0])):
        w, h = sizes[k][0]+2*PAD, sizes[k][1]+2*PAD
        if x+w > atlas:
            x, y, shelf = 0, y+shelf, 0
        if w > atlas or y+h > atlas:
            return None
        places[k] = (x+PAD, y+PAD)
        x += w
        shelf = max(shelf, h)
    return places


def hull(pos, level, side):
    """The hull of the near level's triangles (N,3,3) for a level: (vertices, faces), and the size of a pixel then."""
    pixel = min(side, PROPS_SIDE)/LEVEL_PIXELS[level]
    voxel = VOXEL*pixel
    field, origin, tree = closed_field(pos, voxel, OFFSET*pixel, CLOSE*pixel)
    vertices, faces = surface_nets(field, origin, voxel)
    floor = OFFSET*pixel/2
    vertices, faces = simplify(vertices, faces, ERROR*pixel,
                               keep_out=lambda p: tree.query(p, distance_upper_bound=floor)[0]-floor)
    # Its underside stays open, as the near level's: nothing shows under a building.
    p = vertices[faces]
    under = (p[..., 2].max(axis=1) < pos[..., 2].min()+voxel) & (np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])[:, 2] < 0)
    used, faces = np.unique(faces[~under], return_inverse=True)
    return vertices[used], faces.reshape(-1, 3), pixel


# -- The atlas --------------------------------------------------------------------------------------------------------

class Far:
    """A far level: its hull, the hull's charts and corner normals, and the atlas texels a unit."""

    def __init__(self, level, vertices, faces, pixel):
        self.level, self.vertices, self.faces, self.pixel = level, vertices, faces, pixel
        chart_of, normal, area = charts(vertices, faces, (SMALLEST*pixel/TEXELS)**2)
        self.normals = corner_normals(vertices, faces, normal, area)
        self.charts = [Chart(np.flatnonzero(chart_of == k), vertices[faces[chart_of == k]], normal, area)
                       for k in range(chart_of.max()+1)]
        self.density = TEXELS/pixel


def windowed(xy, depth, origin, width, height, scale, front, back):
    """As far_levels.raster, but at each sample only a depth from front to back there (arrays of the grid's shape) counts."""
    index = np.full((height, width), -1, dtype=np.int64)
    best = back.copy()
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
        window = (rows[:, None], columns[None, :])
        take = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9) & (d < best[window]) & (d >= front[window])
        if take.any():
            r, c = np.nonzero(take)
            best[rows[r], columns[c]] = d[r, c]
            index[rows[r], columns[c]] = t
            bary[rows[r], columns[c]] = np.stack([w0[r, c], w1[r, c], w2[r, c]], axis=-1)
    return index, best, bary


def opacity(key):
    """A blended finish's share of the light it stops: its albedo's mean alpha."""
    from PIL import Image
    spec = fl.read_material(fl.TEXTURES/(key.split('#')[0]+'.tres'), fl.TEXTURES)
    return float(np.asarray(Image.open(spec['albedo']).convert('RGBA'), dtype=np.float64)[..., 3].mean()/255)


def surface(near, finishes, tri, bary):
    """What the near level shows where rays met it: position, normal, linear albedo, paint, glow, roughness, metallic."""
    pos = np.einsum('nk,nkc->nc', bary, near['pos'][tri])
    normal = np.einsum('nk,nkc->nc', bary, near['nrm'][tri])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-9)
    uv = np.einsum('nk,nkc->nc', bary, near['uv'][tri])
    colour = fl.srgb_linear(np.clip(np.einsum('nk,nkc->nc', bary, near['col'][tri][..., :3]), 0, None))
    keys = near['mat'][tri]
    albedo, glow = np.zeros((len(tri), 3)), np.zeros((len(tri), 3))
    paint, rough, metal, always = np.zeros(len(tri)), np.zeros(len(tri)), np.zeros(len(tri)), np.zeros(len(tri), dtype=bool)
    for key in np.unique(keys):
        mask = keys == key
        m = finishes.material(key)
        albedo[mask] = finishes.sample(key, uv[mask])*colour[mask]
        glow[mask] = finishes.sample(key, uv[mask], m['glow'])
        paint[mask] = m['paint']
        rough[mask], metal[mask] = m['orm']['roughness'], m['orm']['metallic']
        always[mask] = emission(finishes, key) == 'always'
    return {'pos': pos, 'normal': normal, 'albedo': albedo, 'paint': paint, 'glow': glow, 'rough': rough, 'metal': metal,
            'always': always}


def emission(finishes, key):
    """When a near material glows, as RigidGlb reads it: its GLB extras' mmEmission, else its .tres's, else always."""
    mode = finishes.extras.get(key, {}).get('mmEmission')
    if mode is None:
        text = (fl.TEXTURES/(key.split('#')[0]+'.tres')).read_text(encoding='utf-8-sig')
        mode = 'night' if 'metadata/mmEmission = "night"' in text else 'off' if 'metadata/mmEmission = "off"' in text else 'always'
    return mode


def rays(far, chart, near, blended):
    """A chart's samples: where its hull lies (covered), the hull's normal there, and the near triangle and barycentrics
    each ray from it against the chart's normal meets (index -1 for none), opaque and, in front of that, blended."""
    width, height = chart.size(far.density)
    scale = far.density*SUBSAMPLES
    shape = (height*SUBSAMPLES, width*SUBSAMPLES)
    # A point is o + a*u + b*w - t*n, o on the chart's plane: (a, b) on that plane, t along the ray.
    frame = np.linalg.inv(np.column_stack([chart.u, chart.w, -chart.n]))
    origin = chart.n*float(np.mean(far.vertices[far.faces[chart.faces]]@chart.n))
    corners = (far.vertices[far.faces[chart.faces]]-origin)@frame.T
    index, depth, bary = fl.raster(corners[..., :2], corners[..., 2], chart.low, shape[1], shape[0], scale)
    covered = index >= 0
    normal = np.einsum('hwk,hwkc->hwc', bary, far.normals[chart.faces][np.maximum(index, 0)])
    front = np.where(covered, depth-FRONT*far.pixel, np.inf)
    back = np.where(covered, depth+BACK*far.pixel, -np.inf)
    local = (near['pos']-origin)@frame.T
    xy, along = local[..., :2], local[..., 2]
    top = chart.low+np.array([width, height])/far.density
    facing = near['out']@chart.n > 0
    chosen = (facing & np.all(xy.max(axis=1) >= chart.low, axis=1) & np.all(xy.min(axis=1) <= top, axis=1)
              & (along.max(axis=1) >= front[covered].min(initial=np.inf))
              & (along.min(axis=1) <= back[covered].max(initial=-np.inf)+(THROUGH*far.pixel if blended.any() else 0)))
    result = {'covered': covered, 'normal': normal, 'shape': shape}
    # Through blended glass a ray goes on to what shows behind it, as far as THROUGH.
    for kind, mask in (('glass', chosen & blended), ('opaque', chosen & ~blended)):
        limit = back if kind == 'glass' else np.where(result['glass'][0] >= 0, result['glass'][1]+THROUGH*far.pixel, back)
        picked = np.flatnonzero(mask)
        if not len(picked):
            result[kind] = (np.full(shape, -1), limit.copy(), np.zeros(shape+(3,)))
            continue
        hit, hit_depth, hit_bary = windowed(xy[picked], along[picked], chart.low, shape[1], shape[0], scale, front, limit)
        result[kind] = (np.where(hit >= 0, picked[np.maximum(hit, 0)], -1), hit_depth, hit_bary)
    # Glass behind what the ray met first is not seen.
    index, depth, bary = result['glass']
    result['glass'] = (np.where((result['opaque'][0] >= 0) & (result['opaque'][1] < depth), -1, index), depth, bary)
    return result


def glass(near, materials):
    """Which near triangles are blended glass."""
    return np.isin(near['mat'], [m['id'] for m in materials if m.get('alphaMode') == 'BLEND'])


def opaque(near, materials):
    """The near triangles that hide the sky: all but blended glass."""
    return {key: value[~glass(near, materials)] for key, value in near.items()}


def bake(fars, near, materials, paned):
    """Every far level's charts baked into one atlas: its maps as 8-bit images, its size, how far its density had to
    shrink to fit, and how many charts no ray from met the near level. A level's charts bake no glow where the near
    triangles paned[level] stand as panes (panes)."""
    finishes = fl.Finishes(materials)
    blended = glass(near, materials)
    every = [(far, chart) for far in fars for chart in far.charts]
    # The smallest atlas that holds every chart at its level's density, else the largest at a lower density.
    shrink = 1.0
    while True:
        for far in fars:
            far.density = TEXELS/far.pixel*shrink
        sizes = [tuple(chart.size(far.density)) for far, chart in every]
        places = next((p for p in (pack(sizes, atlas) for atlas in ATLASES) if p), None)
        if places:
            atlas = next(atlas for atlas in ATLASES if pack(sizes, atlas))
            break
        shrink *= .9
    sampled = [rays(far, chart, near, blended) for far, chart in every]
    # What the rays met, all at once: the sky the near level hides needs every point together. Glass lets it through.
    hits = [s['opaque'][0] >= 0 for s in sampled]
    tri = np.concatenate([s['opaque'][0][h] for s, h in zip(sampled, hits)])
    bary = np.concatenate([s['opaque'][2][h] for s, h in zip(sampled, hits)])
    seen = surface(near, finishes, tri, bary)
    light = fl.daylight(seen['pos']+seen['normal']*.05, seen['normal'], opaque(near, materials))
    seen['albedo'] *= (1-fl.DIRECT*(1-light))[:, None]
    # The atlas glows at night alone: what glows all day too (lamps, skylights) is as bright by day in its albedo.
    seen['albedo'] = np.where(seen.pop('always')[:, None], np.minimum(1, seen['albedo']+seen['glow']), seen['albedo'])
    # The panes light themselves.
    level = np.concatenate([np.full(int(h.sum()), far.level) for (far, _), h in zip(every, hits)])
    for far in fars:
        seen['glow'][paned[far.level][tri] & (level == far.level)] = 0
    # Blended glass in front: its own colour over what lies behind it, by its opacity.
    ahead = np.concatenate([s['glass'][0][h] for s, h in zip(sampled, hits)])
    if (ahead >= 0).any():
        under = ahead >= 0
        bary = np.concatenate([s['glass'][2][h] for s, h in zip(sampled, hits)])[under]
        pane = surface(near, finishes, ahead[under], bary)
        alpha = np.array([opacity(key) for key in near['mat'][ahead[under]]])[:, None]
        for key in ('albedo', 'glow'):
            seen[key][under] = pane[key]*alpha+seen[key][under]*(1-alpha)
    maps = {'albedo': np.zeros((atlas, atlas, 3)), 'paint': np.zeros((atlas, atlas)), 'glow': np.zeros((atlas, atlas, 3)),
            'rough': np.ones((atlas, atlas)), 'metal': np.zeros((atlas, atlas)), 'normal': np.zeros((atlas, atlas, 3))}
    placed = np.zeros((atlas, atlas), dtype=bool)
    start, empty = 0, 0
    for (far, chart), s, h, (x, y) in zip(every, sampled, hits, places):
        count = int(h.sum())
        grid = {}
        for key, value in seen.items():
            grid[key] = np.zeros(s['shape']+value.shape[1:])
            grid[key][h] = value[start:start+count]
        start += count
        if count:
            # Samples whose ray met nothing, and those off the chart's faces, take the nearest hit's.
            rows, columns = fl.nearest(h)
            grid = {key: value[rows, columns] for key, value in grid.items()}
            normal = s['normal'][rows, columns]
        else:
            # A chart no ray from met the near level (a soffit over nothing): the building's average, in shade.
            empty += 1
            for key, value in seen.items():
                grid[key][:] = value.mean(axis=0)
            grid['albedo'] *= .5
            grid['glow'][:] = 0
            grid['normal'][:] = chart.n
            normal = np.broadcast_to(chart.n, s['shape']+(3,))
        normal = normal/np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-9)
        # The near normal in the hull's frame there: along the chart's u, up its region, out (as far_levels bakes).
        tangent = chart.u-normal*(normal@chart.u)[..., None]
        tangent /= np.maximum(np.linalg.norm(tangent, axis=-1, keepdims=True), 1e-9)
        bitangent = np.cross(normal, tangent)
        n = grid['normal']
        local = np.stack([np.einsum('...c,...c', n, tangent), np.einsum('...c,...c', n, bitangent),
                          np.einsum('...c,...c', n, normal)], axis=-1)

        def average(array):
            rows, columns = s['shape'][0]//SUBSAMPLES, s['shape'][1]//SUBSAMPLES
            return array.reshape((rows, SUBSAMPLES, columns, SUBSAMPLES)+array.shape[2:]).mean(axis=(1, 3))
        lum = grid['albedo']@fl.LUMINANCE
        whole = average(lum)
        texels = {'albedo': average(grid['albedo']), 'glow': average(grid['glow']),
                  'paint': np.where(whole > 1e-6, average(lum*grid['paint'])/np.maximum(whole, 1e-6), average(grid['paint'])),
                  'rough': average(grid['rough']), 'metal': average(grid['metal']), 'normal': average(local)}
        texels['normal'] /= np.maximum(np.linalg.norm(texels['normal'], axis=-1, keepdims=True), 1e-9)
        rows, columns = texels['paint'].shape
        for key, value in texels.items():
            maps[key][y:y+rows, x:x+columns] = value
        placed[y:y+rows, x:x+columns] = True
        chart.x, chart.y, chart.top = x, y, chart.low[1]+rows/far.density
    # Texels between charts take the nearest chart's, so that mip levels keep the charts' colours.
    rows, columns = fl.nearest(placed)
    maps = {key: value[rows, columns] for key, value in maps.items()}
    images = {'albedo': np.dstack([fl.linear_srgb(maps['albedo']), maps['paint']]), 'glow': fl.linear_srgb(maps['glow']),
              'orm': np.dstack([np.zeros((atlas, atlas)), maps['rough'], maps['metal']]), 'normal': maps['normal']*.5+.5}
    return {key: np.round(np.clip(value, 0, 1)*255).astype(np.uint8) for key, value in images.items()}, atlas, shrink, empty


def level_model(far, atlas):
    """A far level's vertices (Z up: position, normal, colour, UV, as glb_geometry stores them) and triangles, its corners
    laid in the atlas."""
    rows = []
    for chart in far.charts:
        corners = far.vertices[far.faces[chart.faces]]
        u = (chart.x+(chart.flat[..., 0]-chart.low[0])*far.density)/atlas
        v = (chart.y+(chart.top-chart.flat[..., 1])*far.density)/atlas
        rows.append(np.concatenate([corners, far.normals[chart.faces], np.ones(corners.shape[:2]+(4,)),
                                    np.stack([u, v], axis=-1)], axis=-1).reshape(-1, 12))
    data = np.concatenate(rows)
    unique, inverse = np.unique(np.round(data, 6), axis=0, return_inverse=True)
    return unique, inverse.reshape(-1, 3)


# -- Lit panes --------------------------------------------------------------------------------------------------------

def hits(origins, direction, triangles):
    """How far each ray from origins along direction (both (N,3)) runs before it meets one of the triangles (M,3,3), inf
    for none (Moller and Trumbore)."""
    a, e1, e2 = triangles[:, 0], triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]
    result = np.full(len(origins), np.inf)
    for start in range(0, len(origins), 64):
        o, d = origins[start:start+64, None], direction[start:start+64, None]
        p = np.cross(d, e2[None])
        det = np.einsum('rmc,mc->rm', p, e1)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1/np.where(ok, det, 1), 0)
        s = o-a[None]
        u = np.einsum('rmc,rmc->rm', s, p)*inv
        q = np.cross(s, e1[None])
        v = np.einsum('rmc,rmc->rm', d, q)*inv
        t = np.einsum('rmc,mc->rm', q, e2)*inv
        result[start:start+64] = np.where(ok & (u >= 0) & (v >= 0) & (u+v <= 1) & (t > 0), t, np.inf).min(axis=1)
    return result


def panes(near, finishes, far):
    """The near level's lit panes as geometry just outside a far level's hull, in their own near materials: every flat
    piece of a material that glows (a lit window, a skylight, a lit sign), out along its normal to a tenth of a pixel past
    the hull, when it lies at most PANE_DEPTH inside it. A texture at a texel a pixel blurs and dims a window a few pixels
    wide; the pane itself lights as the near one does, its edge as sharp. A rectangular piece is one quad. Returns ({material: (vertices, triangles)}, which near
    triangles they stand for); a piece that is not flat (a lamp's body) stays in the atlas."""
    glowing = [key for key in np.unique(near['mat']).tolist() if finishes.material(key)['glow'].any()]
    hull = far.vertices[far.faces]
    made, paned = {}, np.zeros(len(near['mat']), dtype=bool)
    for key in glowing:
        chosen = np.flatnonzero(near['mat'] == key)
        piece = building_lod.connected_pieces(near['pos'][chosen].reshape(-1, 3), np.arange(3*len(chosen)).reshape(-1, 3))[::3]
        for one in np.unique(piece):
            mine = chosen[piece == one]
            tri = near['pos'][mine]
            out = near['out'][mine]
            area = np.linalg.norm(out, axis=1)
            n = out.sum(axis=0)
            if np.linalg.norm(n) < .95*area.sum():
                continue
            n /= np.linalg.norm(n)
            up = np.array([0, 0, 1.0]) if abs(n[2]) < .9 else np.array([0, 1.0, 0])
            u = np.cross(up, n)
            u /= np.linalg.norm(u)
            w = np.cross(n, u)
            corners = tri.reshape(-1, 3)
            reach = hits(corners-n*.01, np.broadcast_to(n, corners.shape).copy(), hull)
            reach = reach[np.isfinite(reach)].max() if np.isfinite(reach).any() else 0
            if reach > PANE_DEPTH*far.pixel:
                # Deep in a recess the hull closes over (a window behind a colonnade): brought out, it would light
                # where the near level shows columns.
                continue
            lift = n*(reach+.1*far.pixel)
            a, b = corners@u, corners@w
            rows = np.concatenate([near['pos'][mine], near['nrm'][mine], near['col'][mine], near['uv'][mine]], axis=-1).reshape(-1, 12)
            rows[:, 3:6] = n
            if len(mine) > 2 and area.sum()/2 >= .9*np.ptp(a)*np.ptp(b):
                # A rectangle: its box, the near UVs fitted to the plane.
                box = np.array([(a.min(), b.min()), (a.max(), b.min()), (a.max(), b.max()), (a.min(), b.max())])
                fit, *_ = np.linalg.lstsq(np.column_stack([a, b, np.ones(len(a))]), rows[:, 10:12], rcond=None)
                depth = float(np.mean(corners@n))
                quad = np.column_stack([box[:, :1]*u+box[:, 1:]*w+depth*n, np.broadcast_to(n, (4, 3)),
                                        np.broadcast_to(rows[:, 6:10].mean(axis=0), (4, 4)), np.column_stack([box, np.ones(4)])@fit])
                rows, triangles = quad, np.array([[0, 1, 2], [0, 2, 3]])
            else:
                triangles = np.arange(len(rows)).reshape(-1, 3)
            rows[:, :3] += lift
            # Colours as stored: linear.
            rows[:, 6:9] = fl.srgb_linear(np.clip(rows[:, 6:9], 0, 1))
            vertices, faces = made.setdefault(key, ([], []))
            faces.append(triangles+sum(len(v) for v in vertices))
            vertices.append(rows)
            paned[mine] = True
    return {key: (np.concatenate(v), np.concatenate(f)) for key, (v, f) in made.items()}, paned


# -- The file ---------------------------------------------------------------------------------------------------------

def png(image):
    """An image's PNG bytes."""
    from PIL import Image
    out = io.BytesIO()
    Image.fromarray(image).save(out, 'PNG', optimize=True)
    return out.getvalue()


def rewrite(path, levels, images):
    """The file with its far levels replaced: {level: [(vertices, triangles, material)]}, material None for the one of
    the atlas images, else a near material's id. Everything the scene's other roots reach (the near level, the volumes) is
    copied unchanged, the rest goes."""
    doc, binary = glb.read_glb(path)
    stem = path.stem
    out = {key: value for key, value in doc.items() if key not in ('nodes', 'meshes', 'materials', 'textures', 'images',
                                                                    'samplers', 'accessors', 'bufferViews', 'buffers', 'scenes')}
    out.update(scenes=[{'nodes': []}], nodes=[], meshes=[], materials=[], textures=[], images=[], samplers=[], accessors=[],
               bufferViews=[])
    blob = bytearray()

    def view(payload, target=None):
        while len(blob) % 4:
            blob.append(0)
        out['bufferViews'].append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(payload),
                                   **({'target': target} if target else {})})
        blob.extend(payload)
        return len(out['bufferViews'])-1

    copied = {}

    def accessor(index):
        if index not in copied:
            source = doc['accessors'][index]
            buffer = doc['bufferViews'][source['bufferView']]
            size = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[source['type']]*{5126: 4, 5125: 4, 5123: 2, 5121: 1}[source['componentType']]
            start = buffer.get('byteOffset', 0)+source.get('byteOffset', 0)
            assert buffer.get('byteStride', size) == size
            out['accessors'].append({**{key: value for key, value in source.items() if key != 'byteOffset'},
                                     'bufferView': view(binary[start:start+size*source['count']], buffer.get('target'))})
            copied[index] = len(out['accessors'])-1
        return copied[index]

    def table(name, index, copy):
        """An entry of a top-level list copied once, by its index in the source."""
        memo = table.memo.setdefault(name, {})
        if index not in memo:
            out[name].append(copy(doc[name][index]))
            memo[index] = len(out[name])-1
        return memo[index]
    table.memo = {}

    def texture(source):
        result = dict(source)
        if 'sampler' in source:
            result['sampler'] = table('samplers', source['sampler'], dict)
        result['source'] = table('images', source['source'], image)
        return result

    def image(source):
        result = dict(source)
        if 'bufferView' in source:
            buffer = doc['bufferViews'][source['bufferView']]
            result['bufferView'] = view(binary[buffer.get('byteOffset', 0):buffer.get('byteOffset', 0)+buffer['byteLength']])
        return result

    def material(source):
        result = json.loads(json.dumps(source))
        for holder in (result, result.get('pbrMetallicRoughness', {})):
            for key, value in holder.items():
                if key.endswith('Texture'):
                    value['index'] = table('textures', value['index'], texture)
        return result

    def mesh(source):
        result = json.loads(json.dumps(source))
        for primitive in result['primitives']:
            primitive['attributes'] = {key: accessor(value) for key, value in primitive['attributes'].items()}
            primitive['indices'] = accessor(primitive['indices'])
            if 'material' in primitive:
                primitive['material'] = table('materials', primitive['material'], material)
        return result

    def node(index):
        source = doc['nodes'][index]
        result = {key: value for key, value in source.items() if key not in ('mesh', 'children')}
        if 'mesh' in source:
            result['mesh'] = table('meshes', source['mesh'], mesh)
        children = [node(child) for child in source.get('children', [])]
        if children:
            result['children'] = children
        out['nodes'].append(result)
        return len(out['nodes'])-1

    def far_material():
        sampler = {'magFilter': 9729, 'minFilter': 9987, 'wrapS': 33071, 'wrapT': 33071}
        out['samplers'].append(sampler)
        textures = {}
        for key in ('albedo', 'orm', 'normal', 'glow'):
            out['images'].append({'name': f'{stem}-far-{key}', 'mimeType': 'image/png', 'bufferView': view(png(images[key]))})
            out['textures'].append({'source': len(out['images'])-1, 'sampler': len(out['samplers'])-1})
            textures[key] = len(out['textures'])-1
        # The atlas's alpha is the building paint's share (mmPaintMask); its glow lights at night, as lit windows do.
        out['materials'].append({'name': f'{stem}-far', 'pbrMetallicRoughness': {
            'baseColorFactor': [1, 1, 1, 1], 'baseColorTexture': {'index': textures['albedo']}, 'metallicFactor': 1,
            'roughnessFactor': 1, 'metallicRoughnessTexture': {'index': textures['orm']}},
            'normalTexture': {'index': textures['normal']}, 'emissiveTexture': {'index': textures['glow']},
            'emissiveFactor': [1, 1, 1], 'extras': {'mmBuildingPaint': True, 'mmPaintMask': True, 'mmEmission': 'night'}})
        return len(out['materials'])-1

    def far_node(level, parts):
        """A far level's node: parts [(vertices, triangles, material: None for the atlas's, else a near material's id)]."""
        name = f'{stem}-lod{level}-shell'
        primitives = []
        for k, (vertices, triangles, key) in enumerate(parts):
            # glTF is Y up.
            position = np.column_stack((vertices[:, 0], vertices[:, 2], -vertices[:, 1])).astype('<f4')
            normal = np.column_stack((vertices[:, 3], vertices[:, 5], -vertices[:, 4])).astype('<f4')
            attributes = {}
            for role, array, kind in (('POSITION', position, 'VEC3'), ('NORMAL', normal, 'VEC3'),
                                      ('COLOR_0', vertices[:, 6:10].astype('<f4'), 'VEC4'), ('TEXCOORD_0', vertices[:, 10:12].astype('<f4'), 'VEC2')):
                out['accessors'].append({'bufferView': view(array.tobytes(), 34962), 'componentType': 5126, 'count': len(array), 'type': kind})
                if role == 'POSITION':
                    out['accessors'][-1].update(min=array.min(axis=0).tolist(), max=array.max(axis=0).tolist())
                attributes[role] = len(out['accessors'])-1
            component, dtype = (5123, '<u2') if len(vertices) <= 65535 else (5125, '<u4')
            out['accessors'].append({'bufferView': view(triangles.astype(dtype).tobytes(), 34963), 'componentType': component,
                                     'count': triangles.size, 'type': 'SCALAR'})
            primitives.append({'attributes': attributes, 'indices': len(out['accessors'])-1, 'mode': 4,
                               'material': atlas if key is None else table('materials', names[key], material),
                               'extras': {'mmPart': f'{name}-{k}'}})
        out['meshes'].append({'name': name, 'primitives': primitives})
        out['nodes'].append({'name': name, 'mesh': len(out['meshes'])-1})
        out['nodes'].append({'name': f'{stem}-lod{level}', 'children': [len(out['nodes'])-1]})
        return len(out['nodes'])-1

    names = {source['name']: index for index, source in enumerate(doc['materials'])}
    far = {f'{stem}-lod{level}' for level in (1, 2, 3)}
    roots = [index for index in doc['scenes'][doc.get('scene', 0)]['nodes'] if doc['nodes'][index].get('name') not in far]
    assert doc['nodes'][roots[0]]['name'] == f'{stem}-lod0'
    for index in roots:
        out['scenes'][0]['nodes'].append(node(index))
        if doc['nodes'][index]['name'] == f'{stem}-lod0':
            atlas = far_material()
            for level, parts in sorted(levels.items()):
                out['scenes'][0]['nodes'].append(far_node(level, parts))
    out['buffers'] = [{'byteLength': len(blob)}]
    out = {key: value for key, value in out.items() if value != []}
    glb.validate(out, path, AUTHORED.parents[1])
    glb.write_glb(path, out, bytes(blob))


def near_level(path):
    """The near level's triangles (far_levels.near_pieces, every node together), with each one's outward normal (as the
    near level draws it, its vertex normals choosing the side), and its materials."""
    model, pieces = fl.near_pieces(path)
    near = {key: np.concatenate([piece[key] for piece in pieces.values()]) for key in next(iter(pieces.values()))}
    pos = near['pos']
    cross = np.cross(pos[:, 1]-pos[:, 0], pos[:, 2]-pos[:, 0])
    near['out'] = cross*np.sign(np.einsum('nc,nc->n', cross, near['nrm'].sum(axis=1)))[:, None]
    return near, model['materials']


def build(stem, hulls=hull):
    """Writes the far levels of data/models/buildings/authored/<stem>.glb; returns what it made. hulls(pos, level, side)
    makes each level's hull."""
    path = AUTHORED/(stem+'.glb')
    near, materials = near_level(path)
    points = near['pos'].reshape(-1, 3)
    side = float(max(np.ptp(points[:, 0]), np.ptp(points[:, 1])))
    fars = [Far(level, *hulls(near['pos'], level, side)) for level in (1, 2)]
    finishes = fl.Finishes(materials)
    lit = {far.level: panes(near, finishes, far) for far in fars}
    images, atlas, shrink, empty = bake(fars, near, materials, {level: mask for level, (_, mask) in lit.items()})
    levels = {far.level: [(*level_model(far, atlas), None)]+[(vertices, triangles, key) for key, (vertices, triangles)
                                                             in sorted(lit[far.level][0].items())] for far in fars}
    rewrite(path, levels, images)
    return {'near': len(near['pos']), **{f'lod{level}': sum(len(t) for _, t, _ in parts) for level, parts in levels.items()},
            'panes': sum(len(t) for _, t in lit[1][0].values()), 'atlas': atlas, 'shrink': round(shrink, 3),
            'empty charts': empty, 'charts': [len(far.charts) for far in fars]}


if __name__ == '__main__':
    for stem in sys.argv[1:] or BUILDINGS:
        print('FAR', stem, build(stem), flush=True)
