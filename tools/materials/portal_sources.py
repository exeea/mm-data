"""The ground road tunnels' photo concrete (scenery/tunnel-portal): its sources from two photographic studies.

    python tools/materials/portal_sources.py layouts <folder>   the studies' layouts, front.png and sides.png
    python tools/materials/portal_sources.py                    sources/artwork.png, normal.png and regions.json

Needs numpy, scipy and Pillow. The layouts are drawn from the portal's numbers (tools/board-models/road-tunnel.md, in
model units; a hex is 83.125 units, 30 m), 1536 x 1024 each: front.png the portal's front at 32 px a unit (the face
light grey, the cap a lighter band, the opening black, the rest dark grey), sides.png at 25 px a unit a long wing's
outer face along its run, the cap's top and a wing's top. ImageGen photographed weathered board-formed concrete onto
each layout (sources/front-study.png and sides-study.png, their prompts beside them). The sources lay the studies out
in one 1024 picture: the front with its cap on top, then the wing's face, the cap's top, the wing's top and a plain
patch for the hidden faces; regions.json gives each region's pixel box (x0, y0, x1, y1; y down, as glTF's V), which
tools/board-models/road_tunnel.py maps the faces to. Outside the concrete every pixel repeats its nearest concrete
pixel two pixels in from the outline, so neither mip levels nor the normal map see the surround. The normal map is the
height of the photo's fine light (plank joints and tie holes are dark, so low), OpenGL convention.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt, gaussian_filter

SOURCES = Path(__file__).resolve().parent / 'scenery/tunnel-portal/sources'
SIZE = 1024
W, H = 1536, 1024
BACK, CONCRETE, CAP, OPENING = (60, 60, 60), (165, 165, 160), (200, 200, 195), (0, 0, 0)
# road-tunnel.md: the shell's and the cap's half widths, the cap's underside and top; the opening's half width, its
# piers' height and the arch's rise; a long wing's length, flare and end height.
HALF, CAP_HALF, CAP_LOW, TOP = 22.25, 22.55, 25.4, 26.0
OPEN, PIER, RISE = 17.5, 6.9, 10.925
LENGTH, FLARE, LOW = 21.7, .4, 4.0
CAP_DEPTH, WING_THICK = 2.1, 1.75


def layouts():
    """The front's and the sides' layouts, and each part's box on them."""
    s, ground = 32, H - 96
    front = Image.new('RGB', (W, H), BACK)
    draw = ImageDraw.Draw(front)
    px = lambda x, z: (W / 2 + x * s, ground - z * s)
    draw.rectangle([px(-HALF, CAP_LOW), px(HALF, 0)], fill=CONCRETE)
    draw.rectangle([px(-CAP_HALF, TOP), px(CAP_HALF, CAP_LOW)], fill=CAP)
    arch = [px(-OPEN, 0), px(-OPEN, PIER)]
    arch += [px(-OPEN * math.cos(math.pi * i / 64), PIER + RISE * math.sin(math.pi * i / 64)) for i in range(65)]
    draw.polygon(arch + [px(OPEN, 0)], fill=OPENING)
    boxes = {'front': (*px(-CAP_HALF, TOP), *px(CAP_HALF, 0))}
    s = 25
    sides = Image.new('RGB', (W, H), BACK)
    draw = ImageDraw.Draw(sides)
    run = LENGTH * math.hypot(1, FLARE)
    x0, base = 60, 60 + CAP_LOW * s
    draw.polygon([(x0, base), (x0 + run * s, base), (x0 + run * s, base - LOW * s), (x0, base - CAP_LOW * s)], fill=CONCRETE)
    cap = (60, base + 40, 60 + 2 * CAP_HALF * s, base + 40 + CAP_DEPTH * s)
    draw.rectangle(cap, fill=CAP)
    top = (60, cap[3] + 30, 60 + math.hypot(run, CAP_LOW - LOW) * s, cap[3] + 30 + WING_THICK * s)
    draw.rectangle(top, fill=CONCRETE)
    boxes.update(wing=(x0, base - CAP_LOW * s, x0 + run * s, base), cap=cap, top=top,
                 # A plain stretch low on the wing's face, between its tie holes.
                 plain=(150, 420, 450, 560))
    return front, sides, {k: tuple(round(v) for v in box) for k, box in boxes.items()}


def sources():
    front_layout, sides_layout, boxes = layouts()
    studies = {'front': Image.open(SOURCES / 'front-study.png').convert('RGB'),
               'sides': Image.open(SOURCES / 'sides-study.png').convert('RGB')}
    masks = {'front': front_layout.convert('L'), 'sides': sides_layout.convert('L')}
    atlas, layout, regions = Image.new('RGB', (SIZE, SIZE), CONCRETE), Image.new('L', (SIZE, SIZE), 0), {}

    def place(name, sheet, at, size):
        box = boxes[name]
        atlas.paste(studies[sheet].crop(box).resize(size, Image.LANCZOS), at)
        layout.paste(masks[sheet].crop(box).resize(size, Image.NEAREST), at)
        regions[name] = (at[0], at[1], at[0] + size[0], at[1] + size[1])

    f = boxes['front']
    height = round(SIZE * (f[3] - f[1]) / (f[2] - f[0]))
    place('front', 'front', (0, 0), (SIZE, height))
    w = boxes['wing']
    rest = SIZE - height - 2
    width = round(rest * (w[2] - w[0]) / (w[3] - w[1]))
    place('wing', 'sides', (0, height + 2), (width, rest))
    x = width + 2
    place('cap', 'sides', (x, height + 2), (SIZE - x, 40))
    place('top', 'sides', (x, height + 44), (SIZE - x, 30))
    place('plain', 'sides', (x, height + 76), (SIZE - x, SIZE - height - 76))
    valid = binary_erosion(np.asarray(layout) >= 150, iterations=2)
    _, (iy, ix) = distance_transform_edt(~valid, return_indices=True)
    pixels = np.asarray(atlas)[iy, ix]
    Image.fromarray(pixels.astype(np.uint8)).save(SOURCES / 'artwork.png')
    light = pixels.astype(float).mean(2) / 255
    height_map = .5 + light - gaussian_filter(light, 3)
    dx = (np.roll(height_map, -1, 1) - np.roll(height_map, 1, 1)) / 2
    dy = (np.roll(height_map, -1, 0) - np.roll(height_map, 1, 0)) / 2
    strength = 4.0
    normal = np.stack([-dx * strength, dy * strength, np.ones_like(dx)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    Image.fromarray(((normal + 1) / 2 * 255).round().astype(np.uint8)).save(SOURCES / 'normal.png')
    (SOURCES / 'regions.json').write_text(json.dumps({'size': SIZE, 'regions': regions}, indent=1) + '\n',
                                          encoding='utf-8')
    print(regions)


if __name__ == '__main__':
    if sys.argv[1:2] == ['layouts']:
        folder = Path(sys.argv[2])
        front, sides, _ = layouts()
        front.save(folder / 'front.png')
        sides.save(folder / 'sides.png')
    else:
        sources()
