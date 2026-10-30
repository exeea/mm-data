"""Paint the Solaris elevator's level decals: data/models/board/decals/elevator/level-<n>.png, n from -10 to 10.

Run: python tools/decals/elevator_levels.py   (from the mm-data root; needs Pillow and numpy)

Each decal covers its hex (83.125 x 72 model px, no decals.json entry) at 8 image px per model px: an up-and-down arrow
and the level in Exo 2 Bold (data/fonts, OFL), white paint at 95 % with some wear, on the platform's diamond plate.
Straight RGBA: every texel is the white of the paint, so filtering never darkens its edges.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/models/board/decals/elevator'
FONT = ROOT / 'data/fonts/Exo 2/Exo2-Bold.ttf'
SCALE = 8  # image px per model px
SUPER = 2  # drawn larger, then reduced: smooth edges
WIDTH, HEIGHT = round(83.125 * SCALE), 72 * SCALE


def noise(shape, cell, seed):
    """Smooth value noise in [0, 1] with features about {@code cell} px apart."""
    rng = np.random.default_rng(seed)
    coarse = rng.random((shape[0] // cell + 2, shape[1] // cell + 2))
    y, x = np.mgrid[0:shape[0], 0:shape[1]] / cell
    iy, ix = y.astype(int), x.astype(int)
    fy, fx = y - iy, x - ix
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    top = coarse[iy, ix] * (1 - fx) + coarse[iy, ix + 1] * fx
    bottom = coarse[iy + 1, ix] * (1 - fx) + coarse[iy + 1, ix + 1] * fx
    return top * (1 - fy) + bottom * fy


def paint(level):
    s = SCALE * SUPER
    w, h = WIDTH * SUPER, HEIGHT * SUPER
    mask = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = w / 2, h / 2

    def px(x, y):
        """Model px from the hex centre, +y north (up), to image px."""
        return cx + x * s, cy - y * s

    # The arrow, up and down, left of the middle: a shaft and two heads.
    ax, reach, shaft, head, head_length = -17, 20, 2.6, 7.5, 8
    draw.rectangle([*px(ax - shaft, reach - head_length), *px(ax + shaft, -reach + head_length)], fill=255)
    for sign in (1, -1):
        tip, base = sign * reach, sign * (reach - head_length)
        draw.polygon([px(ax, tip), px(ax - head, base), px(ax + head, base)], fill=255)
    # The level, right of the arrow, fitted to its box.
    text = str(level)
    box_width, box_height = 40 * s, 26 * s
    size = int(box_height * 1.35)
    while True:
        font = ImageFont.truetype(str(FONT), size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        if right - left <= box_width and bottom - top <= box_height:
            break
        size -= 2
    nx, ny = px(12, 0)
    draw.text((nx - (left + right) / 2, ny - (top + bottom) / 2), text, font=font, fill=255)
    coverage = np.asarray(mask.resize((WIDTH, HEIGHT), Image.LANCZOS), dtype=np.float32) / 255
    # Worn where boots and tracks scuff it: blotches of thinner paint, a few bare.
    wear = noise(coverage.shape, 18, 17 + level) * .6 + noise(coverage.shape, 5, 117 + level) * .4
    alpha = np.clip(coverage, 0, 1) * .95 * np.clip(1.6 - 1.25 * wear, .35, 1)
    rgba = np.zeros((HEIGHT, WIDTH, 4), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = np.round(alpha * 255).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA')


def name(level):
    return f'level-minus-{-level}' if level < 0 else f'level-{level}'


OUT.mkdir(parents=True, exist_ok=True)
for level in range(-10, 11):
    paint(level).save(OUT / f'{name(level)}.png', optimize=True)
print('wrote', len(range(-10, 11)), 'decals to', OUT)
