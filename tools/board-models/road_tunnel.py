"""The road tunnel portals (scenery/road/road-tunnel, road-tunnel-long-wings and road-tunnel-bridge): the portal as
first made (commit FIRST), with a concrete headwall carried up past the shell's roof slab under an overhanging cap, so
the slab's back edge is hidden and the scree the height field piles behind it (the portal's join) meets a wall instead
of a bare edge. The long-winged ground portal's wing walls fall from the cap's underside at 45 degrees to a low end far
ahead of the face, so the height field's scree beside the approach lies along their tops; the game picks it where the
scree is and no road or rail leaves the road hex beside the tunnel's side (BoardTunnel), else the short wings as first
made. On the ground portals the cap's top and back carry a dust tint in the vertex colours, where
the scree meets the concrete; the bridge portal, set into clean cast walls, keeps a plain cap and has no wings.

The ground portals' headwall, cap and wing walls take the photo concrete (scenery/tunnel-portal): one picture of
weathered board-formed concrete (tools/materials/portal_sources.py) whose regions each face maps to (`photo`); the
lining keeps scenery/tunnel-concrete.

Run: python road_tunnel.py     (standard library only; the portals as first made come from the commit below)
Contract: road-tunnel.md (the headwall's numbers are HEADWALL there and in BoardTunnel).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from glb_geometry import read_glb, write_glb

REPO = TOOLS.parent
BOARD = REPO/'data/models/board'
MANIFEST = REPO/'tools/board-models/manifest.json'
FIRST = '434f9b8e00'  # The last commit that held the portals without a headwall.
# Each portal: the portal it is made from, whether its headwall carries the scree's dust, whether its wings are long,
# and whether it takes the photo concrete.
PORTALS = {'scenery/road/road-tunnel': ('scenery/road/road-tunnel', True, False, True),
           'scenery/road/road-tunnel-long-wings': ('scenery/road/road-tunnel', True, True, True),
           'scenery/road/road-tunnel-bridge': ('scenery/road/road-tunnel-bridge', False, False, False)}
# The photo concrete's picture and its regions (pixel boxes, y down as glTF's V), written by portal_sources.py.
PHOTO = '../../textures/scenery/tunnel-portal_albedo.png'
REGIONS = REPO/'tools/materials/scenery/tunnel-portal/sources/regions.json'
CLAMP = 33071
# The shell (road-tunnel.md): 44.5 units wide, its front face at Y -0.05, its roof slab's top at Z 22.08.
HALF, FRONT, ROOF = 22.25, -0.05, 22.08
# The headwall: 1.5 units thick up to the cap; the cap 0.6 high, standing 0.3 proud in front and at the ends.
THICK, CAP_LOW, TOP, OVER = 1.5, 25.4, 26.0, 0.3
CONCRETE = (0.94, 0.94, 0.92, 1.0)  # The portal's own vertex colour.
DUST = (0.86, 0.80, 0.71, 1.0)  # Scree dust on the cap's top and back, where the rubble lies against it.
REPEAT = 24.0  # The concrete repeats every 24 units (road-tunnel.md).
# The long wings (BoardTunnel's long wing numbers): 1.75 thick, their outer faces from X 21.44 at their roots (Y 0.3,
# inside the headwall) flaring 0.4 a unit to their ends LENGTH ahead of the face; their tops fall from the cap's
# underside at the root to LOW at the end.
WING_THICK, WING_OUTER, WING_BACK, WING_FLARE = 1.75, 21.44, 0.3, 0.4
WING_LENGTH, WING_LOW = 21.4, 4.0


def first(path):
    """A portal as the first commit held it."""
    data = subprocess.run(['git', '-C', str(REPO), 'show', f'{FIRST}:data/models/board/{path}.glb'],
                          capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory() as folder:
        file = Path(folder)/(path.split('/')[-1]+'.glb')
        file.write_bytes(data)
        model = read_glb(file)
    # As the committed files hold it: no zero translation on the node.
    for node in model['nodes']:
        if node.get('translation') == [0, 0, 0]:
            del node['translation']
    return model


def quad(vertices, indices, corners, normal, plane, colour):
    """One quad (corners counter-clockwise seen from outside) with its normal, the concrete's planar UVs (plane: point
    -> (u, v) in units) and its colour."""
    start = len(vertices) // 12
    for p in corners:
        u, v = plane(p)
        vertices.extend([*p, *normal, *colour, u / REPEAT, v / REPEAT])
    indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])


def box(vertices, indices, low, high, faces, colours):
    """The named faces of an axis-aligned box from low to high (x, y, z), each a quad with its own normal, the
    concrete's planar UVs and its colour (colours: face -> RGBA; CONCRETE otherwise)."""
    (x0, y0, z0), (x1, y1, z1) = low, high
    quads = {
        'front': ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], lambda p: (p[0], p[2])),
        'back': ((0, 1, 0), [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], lambda p: (-p[0], p[2])),
        'left': ((-1, 0, 0), [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], lambda p: (-p[1], p[2])),
        'right': ((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], lambda p: (p[1], p[2])),
        'top': ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], lambda p: (p[0], p[1])),
        'bottom': ((0, 0, -1), [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], lambda p: (p[0], -p[1])),
    }
    for name in faces:
        normal, corners, plane = quads[name]
        quad(vertices, indices, corners, normal, plane, colours.get(name, CONCRETE))


def normal(a, b, c):
    """The unit normal of the plane through a, b, c (counter-clockwise seen from outside)."""
    u = [b[i] - a[i] for i in range(3)]
    w = [c[i] - a[i] for i in range(3)]
    n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
    length = sum(x * x for x in n) ** .5
    return tuple(x / length for x in n)


def long_wings(model):
    """The portal with its wing walls (part tunnel-wings) made long: inner, outer, top and end faces per side."""
    mesh = model['meshes'][0]
    part = next(p for p in mesh['parts'] if p['id'] == 'tunnel-wings')
    vertices, indices = mesh['vertices'], []
    for side in (-1, 1):
        def at(outer, y, z):
            x = WING_OUTER + WING_FLARE * (WING_BACK - y) - (0 if outer else WING_THICK)
            return (side * x, y, z)
        ri, ro = at(False, WING_BACK, 0), at(True, WING_BACK, 0)
        ei, eo = at(False, -WING_LENGTH, 0), at(True, -WING_LENGTH, 0)
        rit, rot = at(False, WING_BACK, CAP_LOW), at(True, WING_BACK, CAP_LOW)
        eit, eot = at(False, -WING_LENGTH, WING_LOW), at(True, -WING_LENGTH, WING_LOW)
        faces = [[ri, ei, eit, rit], [eo, ro, rot, eot], [rit, eit, eot, rot], [ei, eo, eot, eit]]
        for corners in faces:
            if side < 0:
                corners = corners[::-1]
            n = normal(*corners[:3])
            # Planar UVs along the face's own run: the horizontal distance from the root, and the height.
            quad(vertices, indices, corners, n, lambda p: (((p[0] - ri[0]) ** 2 + (p[1] - ri[1]) ** 2) ** .5, p[2]),
                 CONCRETE)
    part['indices'] = indices
    return model


def headwall(model, dusty):
    """The portal with its headwall added to the shell's part, in the shell's material, dusted where scree lies."""
    mesh = model['meshes'][0]
    part = next(p for p in mesh['parts'] if p['id'] == 'tunnel-portal')
    vertices, indices = mesh['vertices'], part['indices']
    # The wall from the roof slab's top to the cap: its front flush with the shell's, its back facing the scree.
    box(vertices, indices, (-HALF, FRONT, ROOF), (HALF, FRONT + THICK, CAP_LOW),
        ('front', 'back', 'left', 'right'), {'back': DUST} if dusty else {})
    # The cap, proud of the wall in front and at the ends (a drip edge), its top and back dusty.
    box(vertices, indices, (-HALF - OVER, FRONT - OVER, CAP_LOW), (HALF + OVER, FRONT + THICK + OVER, TOP),
        ('front', 'back', 'left', 'right', 'top', 'bottom'), {'top': DUST, 'back': DUST} if dusty else {})
    return model


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def photo(model):
    """The portal's headwall, cap and wing walls (parts tunnel-portal and tunnel-wings) in the photo concrete: their
    vertices unshared, each face (a part's triangles in one plane) mapped into its region of the picture. The front,
    face and cap, is one projection across X and Z; the cap's top across X and Y; a wing's sides by their run from the
    root and their height, at the picture's own scale, so a short wing takes the near, low part of the long one's face,
    and the shell's sides and the headwall's and cap's ends by their depth back from the face, as a wing's root;
    a wing's top fills its strip along the wing; every other face (a wing's end, backs, undersides, the shell's roof in
    the hill) fills the plain patch."""
    layout = json.loads(REGIONS.read_text(encoding='utf-8'))
    size, regions = layout['size'], layout['regions']
    mesh = model['meshes'][0]
    source, added = mesh['vertices'], []

    def at(name, u, v):
        x0, y0, x1, y1 = regions[name]
        u, v = min(max(u, 0), 1), min(max(v, 0), 1)
        return [(x0 + .5 + u * (x1 - x0 - 1)) / size, (y0 + .5 + v * (y1 - y0 - 1)) / size]

    run = WING_LENGTH * (1 + WING_FLARE ** 2) ** .5
    width = 2 * (HALF + OVER)
    for part in mesh['parts']:
        if part['id'] not in ('tunnel-portal', 'tunnel-wings'):
            continue
        wing = part['id'] == 'tunnel-wings'
        faces = {}
        for i in range(0, len(part['indices']), 3):
            corners = [source[v * 12:v * 12 + 3] for v in part['indices'][i:i + 3]]
            n = normal(*corners)
            # Outward as the vertices' own normals say.
            if dot(n, source[part['indices'][i] * 12 + 3:part['indices'][i] * 12 + 6]) < 0:
                n = tuple(-c for c in n)
            key = (*(round(c, 3) for c in n), round(dot(n, corners[0]), 2))
            faces.setdefault(key, []).append(part['indices'][i:i + 3])
        indices = []
        for key, triangles in faces.items():
            n = key[:3]
            points = [source[v * 12:v * 12 + 3] for t in triangles for v in t]
            if not wing and n[1] < -.9:
                def uv(p): return at('front', (p[0] + HALF + OVER) / width, (TOP - p[2]) / TOP)
            elif not wing and n[2] > .9:
                def uv(p):
                    return at('cap', (p[0] + HALF + OVER) / width, (FRONT + THICK + OVER - p[1]) / (THICK + 2 * OVER))
            elif not wing and abs(n[0]) > .9:
                # The shell's sides and the headwall's and cap's ends: back from the face, as a wing's root.
                def uv(p): return at('wing', (p[1] - FRONT + OVER) / run, (CAP_LOW - p[2]) / CAP_LOW)
            elif wing and abs(n[0]) > .5:
                # Along the wall from its root (its end nearest the cliff), forward; its height from the ground.
                root = max(points, key=lambda p: p[1])
                along = (-n[1], n[0]) if n[0] < 0 else (n[1], -n[0])
                if along[1] > 0:
                    along = (-along[0], -along[1])

                def uv(p, root=root, along=along):
                    return at('wing', ((p[0] - root[0]) * along[0] + (p[1] - root[1]) * along[1]) / run,
                              (CAP_LOW - p[2]) / CAP_LOW)
            else:
                # The face's two in-plane axes, the face stretched over its region; a wing's top along its long axis.
                a = cross((0, 0, 1) if abs(n[2]) < .9 else (0, 1, 0), n)
                b = cross(n, a)
                us, vs = [dot(p, a) for p in points], [dot(p, b) for p in points]
                if max(vs) - min(vs) > max(us) - min(us):
                    a, b, us, vs = b, a, vs, us
                name = 'top' if wing and n[2] > .5 else 'plain'
                low, high = min(us), max(us)
                bottom, top = min(vs), max(vs)

                def uv(p, a=a, b=b, low=low, high=high, bottom=bottom, top=top, name=name):
                    return at(name, (dot(p, a) - low) / max(high - low, 1e-6),
                              (top - dot(p, b)) / max(top - bottom, 1e-6))
            for triangle in triangles:
                for v in triangle:
                    row = list(source[v * 12:v * 12 + 12])
                    row[10:12] = uv(row[:3])
                    indices.append((len(source) + len(added)) // 12)
                    added.extend(row)
        part['indices'] = indices
    vertices = source + added
    # The lining and floor keep the first vertices; the unshared ones follow. Keep only what a part uses.
    used = sorted({v for p in mesh['parts'] for v in p['indices']})
    renumber = {v: i for i, v in enumerate(used)}
    mesh['vertices'] = [x for v in used for x in vertices[v * 12:v * 12 + 12]]
    for p in mesh['parts']:
        p['indices'] = [renumber[v] for v in p['indices']]
    for material in model['materials']:
        if material['id'] in ('tunnel-portal', 'tunnel-wings'):
            for texture in material['textures']:
                texture.update(filename=PHOTO, wrapS=CLAMP, wrapT=CLAMP)
    return model


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for path, (source, dusty, long, photographed) in PORTALS.items():
        model = headwall(first(source), dusty)
        if long:
            model = long_wings(model)
        if photographed:
            model = photo(model)
        out = BOARD/(path+'.glb')
        write_glb(out, levels={0: model}, extras=model.get('extras') or None)
        triangles = sum(len(p['indices']) for p in model['meshes'][0]['parts']) // 3
        entry = manifest.setdefault(path, dict(manifest[source]))
        entry['triangles'], entry['vertices'] = triangles, len(model['meshes'][0]['vertices']) // 12
        print(f'{path}: {triangles} triangles')
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
