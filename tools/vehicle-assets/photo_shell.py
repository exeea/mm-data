"""Photographic vehicles: a mesh fitted to an orthographic reference sheet (side, top, front and rear views of one
vehicle), every face textured with the view it faces. The sheet's views, packed into one square picture, are the
vehicle's own board material (a Material Maker project under tools/materials/structures/vehicles); wheels, tyre tread
and glass are the board's shared ones.

A vehicle's module gives its Sheet (where each view lies in the sheet and in the picture) and builds its levels with a
Shell. Model axes: y from the front (-y) to the rear, z up, +x the vehicle's left side. Sheet coordinates are pixels.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
BOARD = TOOLS.parent/'data/models/board'
TEXTURES = BOARD/'textures'
TAU = math.tau
WHITE = (1.0, 1.0, 1.0)
TREAD = 'structures/vehicles/tyre-tread'


class Sheet:
    """A reference sheet: `views` gives each view's `box` in the sheet (x0, y0, x1, y1) and its `rect` in the picture
    (the same, as shares of its width and height), and for a lofted body its `map` from model points to sheet pixels."""

    def __init__(self, name, views, size=512):
        self.name, self.views, self.size = name, views, size
        self.key = f'structures/vehicles/{name}'

    def uv(self, view, px, py):
        """The picture's point for a sheet pixel of a view."""
        x0, y0, x1, y1 = self.views[view]['box']
        u0, v0, u1, v1 = self.views[view]['rect']
        return u0+(px-x0)/(x1-x0)*(u1-u0), v0+(py-y0)/(y1-y0)*(v1-v0)

    def picture(self, sheet_file, out_file, background=14, paint=None):
        """Packs the views into the picture: the sheet's flat background becomes clear (alpha 0), under the colour of
        the nearest part of the vehicle, so that no edge shows a halo. With `paint` (the brightness the paint is
        brought to), alpha marks the body's pale paint instead, which a colour slot then tints (mmPaintMask)."""
        import numpy as np
        from PIL import Image
        from scipy import ndimage
        sheet = np.asarray(Image.open(sheet_file).convert('RGB')).astype(float)
        flat = np.median(sheet[:8, :8].reshape(-1, 3), axis=0)
        solid = np.abs(sheet-flat).max(axis=2) > background
        # Specks of background colour inside the vehicle stay solid; specks of noise outside it go.
        solid = ndimage.binary_opening(solid, iterations=1)
        holes, count = ndimage.label(~solid)
        sizes = ndimage.sum(~solid, holes, range(1, count+1))
        for index, area in enumerate(sizes, 1):
            if area < 40:
                solid[holes == index] = True
        if paint:  # A painted body has no openings: paint as grey as the background is still body.
            solid = ndimage.binary_fill_holes(ndimage.binary_closing(solid, iterations=3)) | solid
        nearest = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
        filled = sheet[nearest[0], nearest[1]]
        alpha = solid*255.0
        if paint:
            high, low = filled.max(axis=2), filled.min(axis=2)
            # Paint is pale and grey: not dark glass, seams and trim, nor coloured lamps. The mask reaches a pixel past
            # the paint, so the blended pixels along its edge are paint in shadow, not a line of bare silver.
            share = (high > 105)*np.clip(1-(high-low-45)/35, 0, 1)*solid
            share = ndimage.grey_dilation(share, size=(5, 5))*solid
            level = np.median(high[share > .9])
            # Lit headlamps are no paint: the bright patches of the front view and of the other views' front ends
            # (a glint along a crease is thinner, and stays paint).
            front = np.zeros_like(solid)
            for view, part in (('front', 1), ('side', .15), ('top', .12)):
                x0, y0, x1, y1 = self.views[view]['box']
                front[y0:y1, x0:int(x0+(x1-x0)*part)] = True
            lamps = ndimage.binary_opening((high > level+42) & front, iterations=3)
            share[ndimage.binary_dilation(lamps, iterations=4)] = 0
            alpha = share*255.0
            gain = paint*255/level
            share = (alpha/255)[:, :, None]
            filled = np.clip(filled*(1+(gain-1)*share), 0, 255)
        rgba = np.dstack([filled, alpha]).astype('uint8')
        picture = Image.new('RGBA', (self.size, self.size), tuple(int(v) for v in flat)+(0,))
        for view in self.views.values():
            x0, y0, x1, y1 = view['box']
            u0, v0, u1, v1 = view['rect']
            box = [round(u0*self.size), round(v0*self.size), round(u1*self.size), round(v1*self.size)]
            # Colour and alpha apart: scaled together, a clear pixel would lose the colour kept under it.
            size = (box[2]-box[0], box[3]-box[1])
            colour = Image.fromarray(rgba[:, :, :3]).crop((x0, y0, x1, y1)).resize(size, Image.LANCZOS)
            crop = Image.merge('RGBA', (*colour.split(), Image.fromarray(rgba[:, :, 3]).crop((x0, y0, x1, y1)).resize(size, Image.LANCZOS)))
            picture.paste(crop, box[:2])
        Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        picture.save(out_file)


class Shell:
    """One level of a vehicle: triangles gathered per material."""

    def __init__(self, sheet, paint=None):
        self.sheet = sheet
        self.parts = {}  # material -> (vertices, indices)
        self.paint = paint  # The colour the sheet's faces are painted in, in colour slot 1; None for none.

    def face(self, material, corners, uvs, colour=WHITE, both=False):
        """A flat polygon, anticlockwise seen from outside, with a picture point for each corner."""
        vertices, indices = self.parts.setdefault(material, ([], []))
        a, b, c = corners[0], corners[1], corners[2]
        n = [(b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]), (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])]
        length = math.sqrt(sum(v*v for v in n)) or 1
        n = [v/length for v in n]
        for sign in ((1, -1) if both else (1,)):
            base = len(vertices)//12
            for corner, uv in zip(corners, uvs):
                vertices.extend([*corner, *(sign*v for v in n), *colour, 1.0, *uv])
            order = range(1, len(corners)-1)
            for k in order:
                indices.extend((base, base+k, base+k+1) if sign > 0 else (base, base+k+1, base+k))

    def flat(self, material, corners, colour=WHITE, scale=18.0, both=False):
        """A polygon in a shared material, its picture laid on it at `scale` units a repeat."""
        a, b, c = corners[0], corners[1], corners[2]
        n = [(b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]), (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])]
        axis = max(range(3), key=lambda i: abs(n[i]))
        u, v = [i for i in range(3) if i != axis]
        self.face(material, corners, [(p[u]/scale, p[v]/scale) for p in corners], colour, both)

    # -- Faces textured from the sheet ---------------------------------------------------------------

    def panel(self, view, corners, rectangle, away, cut=False, both=False):
        """A flat polygon showing the sheet rectangle (px0, py0, px1, py1) of `view`, facing away from the point
        `away`. The rectangle's edges are the face's own: for the side view px0 is its front (lowest y) and py0 its
        top; for the top view px0 is its front and py0 its lowest x; for the front and rear views px0 is its lowest x
        and py0 its top. Name the edges the other way round where a sheet mirrors a view."""
        across, along = {'side': (1, 2), 'top': (1, 0), 'front': (0, 2), 'rear': (0, 2)}[view]
        px0, py0, px1, py1 = rectangle
        low = [min(c[i] for c in corners) for i in range(3)]
        span = [max(c[i] for c in corners)-low[i] or 1 for i in range(3)]
        pixels = []
        for corner in corners:
            u = (corner[across]-low[across])/span[across]
            v = (corner[along]-low[along])/span[along]
            pixels.append((px0+(px1-px0)*u, py0+(py1-py0)*v if view == 'top' else py1+(py0-py1)*v))
        a, b, c = corners[0], corners[1], corners[2]
        n = [(b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]), (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])]
        middle = [sum(corner[i] for corner in corners)/len(corners) for i in range(3)]
        if sum(n[i]*(middle[i]-away[i]) for i in range(3)) < 0:
            corners, pixels = corners[::-1], pixels[::-1]
        material = self.sheet.key+('#cut' if cut else '')
        self.face(material, corners, [self.sheet.uv(view, px, py) for px, py in pixels], self.paint or WHITE, both=both)

    def project(self, view, corners, away):
        """A polygon showing what a view of the sheet shows where it stands: each corner's place in the view comes from
        the view's own `map` of model points to sheet pixels. Without a `view`, the one the polygon faces most."""
        a, b, c = corners[0], corners[1], corners[2]
        n = [(b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]), (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])]
        middle = [sum(corner[i] for corner in corners)/len(corners) for i in range(3)]
        if sum(n[i]*(middle[i]-away[i]) for i in range(3)) < 0:
            corners, n = corners[::-1], [-v for v in n]
        if not view:
            axis = max(range(3), key=lambda i: abs(n[i]))
            view = ('side', 'front' if n[1] < 0 else 'rear', 'top')[axis]
        mapping = self.sheet.views[view]['map']
        self.face(self.sheet.key, corners, [self.sheet.uv(view, *mapping(*corner)) for corner in corners], self.paint or WHITE)

    def box(self, x0, x1, y0, y1, z0, z1, side=None, top=None, front=None, rear=None):
        """A box. Each of `side`, `top`, `front`, `rear` is the sheet rectangle its faces show (as panel takes it), or
        None to leave those faces out."""
        centre = ((x0+x1)/2, (y0+y1)/2, (z0+z1)/2)
        if side:
            for x in (x0, x1):
                self.panel('side', [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)], side, centre)
        if top:
            self.panel('top', [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], top, centre)
        if front:
            self.panel('front', [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], front, centre)
        if rear:
            self.panel('rear', [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], rear, centre)

    def prism(self, outline, x0, x1, to_model, rim=None):
        """A side-view outline (sheet pixels) drawn out across x: both ends show the side view inside the outline; a
        rim face shows the (view, rectangle) that `rim` gives its edge's index, or is left out."""
        points = [to_model(px, py) for px, py in outline]
        centre = ((x0+x1)/2, sum(p[0] for p in points)/len(points), sum(p[1] for p in points)/len(points))
        for x in (x0, x1):
            corners = [(x, y, z) for y, z in points]
            pixels = list(outline)
            if (x > centre[0]) != (self._turn(points) > 0):
                corners, pixels = corners[::-1], pixels[::-1]
            self.face(self.sheet.key, corners, [self.sheet.uv('side', px, py) for px, py in pixels], self.paint or WHITE)
        for index, (view, rectangle) in (rim or {}).items():
            (ya, za), (yb, zb) = points[index], points[(index+1) % len(points)]
            self.panel(view, [(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)], rectangle, centre)

    @staticmethod
    def _turn(points):
        """Positive when a (y, z) outline runs anticlockwise seen from +x."""
        return sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]+points[:1]))

    def card(self, x, y0, y1, z0, z1, rectangle):
        """An upright card along y at x, showing a side-view rectangle: clear where the sheet is background, seen from
        both sides."""
        self.panel('side', [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)], rectangle, (x-1, 0, 0), cut=True, both=True)

    # -- Shared parts --------------------------------------------------------------------------------

    def wheel(self, x, y, radius, wide, outward, material, sides, back=True, lowest=False):
        """A wheel on an axle along x: its picture on the outer face, tread round it, a dark inner face. With `lowest`,
        a corner stands at its foot, so that a coarse ring still reaches the ground and the wheel's full height."""
        start = -TAU/4 if lowest else 0

        def ring(px):
            return [(px, y+radius*math.cos(start+TAU*k/sides), radius+radius*math.sin(start+TAU*k/sides)) for k in range(sides)]
        outer, inner = ring(x+outward*wide/2), ring(x-outward*wide/2)
        uvs = [(.5+.5*outward*math.cos(start+TAU*k/sides), .5-.5*math.sin(start+TAU*k/sides)) for k in range(sides)]
        if outward > 0:
            self.face(material, outer, uvs)
        else:
            self.face(material, outer[::-1], uvs[::-1])
        if back:  # A tyre looks the same from behind.
            if outward > 0:
                self.face(material, inner[::-1], uvs[::-1])
            else:
                self.face(material, inner, uvs)
        turns = max(2, round(TAU*radius/(wide*1.6)))
        for k in range(sides):
            j = (k+1) % sides
            quad = [outer[k], inner[k], inner[j], outer[j]] if outward > 0 else [outer[j], inner[j], inner[k], outer[k]]
            t0, t1 = turns*k/sides, turns*(k+1)/sides
            self.face(TREAD, quad, [(0, t0), (1, t0), (1, t1), (0, t1)] if outward > 0 else [(0, t1), (1, t1), (1, t0), (0, t0)])

    def tube(self, material, p, q, radius, sides, colour=WHITE):
        """A round bar from p to q in a shared material."""
        axis = [q[i]-p[i] for i in range(3)]
        length = math.sqrt(sum(v*v for v in axis))
        axis = [v/length for v in axis]
        side = (0, 0, 1) if abs(axis[2]) < .9 else (1, 0, 0)
        e1 = [axis[1]*side[2]-axis[2]*side[1], axis[2]*side[0]-axis[0]*side[2], axis[0]*side[1]-axis[1]*side[0]]
        norm = math.sqrt(sum(v*v for v in e1))
        e1 = [v/norm for v in e1]
        e2 = [axis[1]*e1[2]-axis[2]*e1[1], axis[2]*e1[0]-axis[0]*e1[2], axis[0]*e1[1]-axis[1]*e1[0]]
        rings = [[tuple(c[i]+radius*(math.cos(TAU*k/sides)*e1[i]+math.sin(TAU*k/sides)*e2[i]) for i in range(3)) for k in range(sides)] for c in (p, q)]
        for k in range(sides):
            j = (k+1) % sides
            self.flat(material, [rings[0][k], rings[0][j], rings[1][j], rings[1][k]], colour)
        self.flat(material, rings[1], colour)

    def half_turn(self, dx=0.0, dy=0.0):
        """Turns the whole level half round its upright axis and moves it: for a vehicle whose place on the board has
        its front to +y."""
        for vertices, _ in self.parts.values():
            for at in range(0, len(vertices), 12):
                vertices[at], vertices[at+1] = dx-vertices[at], dy-vertices[at+1]
                vertices[at+3], vertices[at+4] = -vertices[at+3], -vertices[at+4]
        return self

    # -- Export ----------------------------------------------------------------------------------------

    def level(self, name, lod, depth):
        """This level as the GLB writer takes it: one node of the vehicle's name."""
        meshes, parts, materials = [], [], []
        for index, (material, (vertices, indices)) in enumerate(self.parts.items()):
            part = f'{name}-lod{lod}-{index}'
            meshes.append({'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': vertices,
                           'parts': [{'id': part, 'type': 'TRIANGLES', 'indices': indices}],
                           'slots': [1 if self.paint and material == self.sheet.key else 0]*(len(vertices)//12)})
            parts.append({'meshpartid': part, 'materialid': material})
            materials.append(board_material(material, depth))
        return {'id': name, 'meshes': meshes, 'nodes': [{'id': name, 'translation': [0, 0, 0], 'parts': parts, 'children': []}],
                'materials': materials}

    def triangles(self):
        return sum(len(indices)//3 for _, indices in self.parts.values())


def board_material(key, depth):
    """A GLB material that draws a board material: the maps its folder holds. `#cut` marks the cutout use of one."""
    name = key.split('#')[0]
    textures = []
    for kind, suffix in (('DIFFUSE', 'albedo'), ('NORMAL', 'normal'), ('AMBIENT', 'orm'), ('METALLIC_ROUGHNESS', 'orm')):
        if (TEXTURES/f'{name}_{suffix}.png').is_file():
            textures.append({'id': key, 'type': kind, 'filename': f'{depth}textures/{name}_{suffix}.png', 'wrapS': 10497, 'wrapT': 10497,
                             'minFilter': 9987, 'magFilter': 9729})
    assert textures and textures[0]['type'] == 'DIFFUSE', key
    material = {'id': key, 'diffuse': [1.0, 1.0, 1.0], 'roughness': 1.0, 'metallic': 1.0, 'textures': textures}
    if key.endswith('#cut'):
        material['alphaTest'] = .5
    return material


def carried(name, level, stride=12):
    """The container a port machine carries, where seaport/container-placements.json puts it: its meshes, its parts,
    its materials and the colour slot it keeps (None for a fixed colour)."""
    import sys
    sys.path.insert(0, str(TOOLS))
    from glb_geometry import read_glb
    meshes, parts, materials, slots = [], [], [], []
    places = json.loads((TOOLS/'board-models/seaport/container-placements.json').read_text(encoding='utf-8')).get(name, ())
    for index, place in enumerate(places):
        container = read_glb(BOARD/'scenery/seaport/yard/container.glb', level=level)
        own = container['extras']['mmColourSlots'][0]
        base_colour = [int(own['colour'][i:i+2], 16)/255 for i in (1, 3, 5)]
        c, s = math.cos(math.radians(place['rotation'])), math.sin(math.radians(place['rotation']))
        for source in container['meshes']:
            vertices = list(source['vertices'])
            for v in range(len(vertices)//stride):
                at = v*stride
                x, y, nx, ny = vertices[at], vertices[at+1], vertices[at+3], vertices[at+4]
                vertices[at], vertices[at+1], vertices[at+2] = x*c-y*s+place['center'][0], x*s+y*c+place['center'][1], vertices[at+2]+place['center'][2]
                vertices[at+3], vertices[at+4] = nx*c-ny*s, nx*s+ny*c
                if source['slots'][v]:
                    for k in range(3):
                        vertices[at+6+k] = min(1.0, vertices[at+6+k]*place['colour'][k]/base_colour[k])
            meshes.append({'attributes': source['attributes'], 'vertices': vertices,
                           'slots': [place['slot'] if own_slot else 0 for own_slot in source['slots']],
                           'parts': [{**part, 'id': f"{name}-{part['id']}-{index}"} for part in source['parts']]})
        for node in container['nodes']:
            parts += [{'meshpartid': f"{name}-{part['meshpartid']}-{index}", 'materialid': part['materialid']} for part in node['parts']]
        for material in container['materials']:
            if any(part['materialid'] == material['id'] for part in parts) and material['id'] not in [m['id'] for m in materials]:
                materials.append(material)
        if place['slot']:
            slots.append({'name': 'Container', 'colour': '#%02x%02x%02x' % tuple(round(255*v) for v in place['colour']), 'presets': own['presets']})
    return meshes, parts, materials, slots
