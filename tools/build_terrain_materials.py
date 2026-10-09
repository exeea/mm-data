#!/usr/bin/env python3
# Copyright (C) 2026 The MegaMek Team. SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural, tileable materials for the sculpted 3D board.

Every map is synthesized from fixed seeds with NumPy and Pillow only: no photographs, no downloaded or generated
images, so the outputs are original works (CC0-1.0, as recorded in the manifest). Each material is authored from a
height field in metres, so its normals and occlusion agree with its relief, and its colour is delit (no baked sun).

Outputs, per material NAME in data/models/board/textures/sculpt/:
  NAME.png         sRGB albedo in RGB, normalized height in A (for height-based layer blending)
  NAME-normal.png  tangent-space normal in RGB (+U right, +V down the image), ambient occlusion in A
  manifest.json    tile size in metres, role and seed of every material; the renderer reads the sizes from here

Usage (from the mm-data root, or pass --out):
  python tools/build_terrain_materials.py [--size 512] [--only sand,grass] [--preview preview.png]
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/models/board/textures/sculpt'


# ---- Periodic fields -------------------------------------------------------------------------------------------

class Canvas:
    """One material's square, periodic sample grid: N pixels span `tile` metres."""

    def __init__(self, n, tile, seed):
        self.n = n
        self.tile = tile
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self._salt = 0
        self.v, self.u = np.mgrid[0:n, 0:n].astype(np.float32) / n  # u: columns (right), v: rows (down), in tiles

    def child(self):
        self._salt += 1
        return np.random.default_rng((self.seed, self._salt))

    def spectral(self, beta=2.0, lo=1.0, hi=None, stretch=(1.0, 1.0), angle=0.0):
        """Zero-mean, unit-deviation noise with power ~ f^-beta between lo and hi cycles per tile.

        stretch > 1 along an axis elongates features along that axis (u, v), after rotating by angle."""
        n = self.n
        white = self.child().standard_normal((n, n)).astype(np.float32)
        f = np.fft.fftfreq(n) * n
        fu, fv = np.meshgrid(f, f)
        c, s = math.cos(angle), math.sin(angle)
        a = (fu * c + fv * s) * stretch[0]
        b = (-fu * s + fv * c) * stretch[1]
        radius = np.sqrt(a * a + b * b)
        radius[0, 0] = 1
        amplitude = radius ** (-beta / 2)
        amplitude *= smoothstep(lo * .7, lo, radius)
        if hi is not None:
            amplitude *= 1 - smoothstep(hi, hi * 1.4, radius)
        amplitude[0, 0] = 0
        field = np.real(np.fft.ifft2(np.fft.fft2(white) * amplitude)).astype(np.float32)
        return (field - field.mean()) / (field.std() + 1e-9)

    def worley(self, cells_u, cells_v=None, jitter=.9, warp=0.0):
        """Periodic jittered-grid Voronoi. Distances are in cells. Returns F1, F2, cell id, and the offset (du, dv)
        from each pixel to its nearest feature point. A warp (in cells) bends the cell borders like natural cracks."""
        cells_v = cells_v or cells_u
        rng = self.child()
        points = (rng.random((cells_v, cells_u, 2)) - .5) * jitter + .5
        pu = self.u * cells_u
        pv = self.v * cells_v
        if warp:
            # Bends of about a cell's size, with a little finer wander.
            hi = 2.5 * max(cells_u, cells_v)
            pu = pu + (self.spectral(3, 1, hi) + .25 * self.spectral(2, hi, 3 * hi)) * warp
            pv = pv + (self.spectral(3, 1, hi) + .25 * self.spectral(2, hi, 3 * hi)) * warp
        cu = np.floor(pu).astype(np.int32)
        cv = np.floor(pv).astype(np.int32)
        f1 = np.full(pu.shape, np.inf, np.float32)
        f2 = np.full(pu.shape, np.inf, np.float32)
        ident = np.zeros(pu.shape, np.int32)
        ou = np.zeros(pu.shape, np.float32)
        ov = np.zeros(pu.shape, np.float32)
        for dv in (-1, 0, 1):
            for du in (-1, 0, 1):
                gu = (cu + du) % cells_u
                gv = (cv + dv) % cells_v
                fu = cu + du + points[gv, gu, 0] - pu
                fv = cv + dv + points[gv, gu, 1] - pv
                d = np.sqrt(fu * fu + fv * fv)
                closer = d < f1
                f2 = np.where(closer, f1, np.minimum(f2, d))
                f1 = np.where(closer, d, f1)
                ident = np.where(closer, gv * cells_u + gu, ident)
                ou = np.where(closer, fu, ou)
                ov = np.where(closer, fv, ov)
        return f1, f2, ident, ou, ov

    def per_cell(self, ident, count, low=0.0, high=1.0):
        return (low + (high - low) * self.child().random(count).astype(np.float32))[ident]

    def fractures(self, angle, spacing, wiggle):
        """One set of long, roughly parallel fractures at `angle` (radians from +U), `spacing` metres apart on
        average, bending by `wiggle` metres. Returns the distance to the nearest fracture in metres and the fraction
        of the way across the slab between two fractures. Periodic: the set's direction is snapped to whole
        cycles of the tile."""
        tile = self.tile
        ku = round(math.cos(angle) * tile / spacing)
        kv = round(math.sin(angle) * tile / spacing)
        if ku == 0 and kv == 0:
            ku = 1
        phase = ku * self.u + kv * self.v + self.spectral(2.2, 2, 12) * wiggle / spacing \
            + self.spectral(3, 1, 3) * .06
        fraction = phase - np.floor(phase)
        period = tile / math.hypot(ku, kv)
        return np.minimum(fraction, 1 - fraction) * period, fraction

    def joints(self, rows, columns, wiggle, bands=None):
        """Jointed blocks: roughly horizontal partings at random spacing, each course split by its own staggered,
        roughly vertical joints. rows/columns are (min, max) spacings in metres. Returns the distance to the nearest
        joint in metres, a block id, and the position inside the block (0..1 across, 0..1 down)."""
        rng = self.child()
        tile = self.tile
        cuts = [0.0]
        while cuts[-1] < tile:
            cuts.append(cuts[-1] + float(rng.uniform(*rows)))
        cuts = np.array(cuts, np.float32) * tile / cuts[-1]
        bend_v = self.spectral(2.5, 1, 12, stretch=(1, 4)) * wiggle
        bend_u = self.spectral(2.5, 1, 12, stretch=(4, 1)) * wiggle
        y = (self.v * tile + bend_v) % tile
        x = (self.u * tile + bend_u) % tile
        row = np.clip(np.searchsorted(cuts, y, side='right') - 1, 0, len(cuts) - 2)
        top, bottom = cuts[row], cuts[row + 1]
        distance = np.minimum(y - top, bottom - y)
        ident = np.zeros_like(row)
        across = np.zeros_like(x)
        for r in range(len(cuts) - 1):
            walls = [0.0]
            while walls[-1] < tile:
                walls.append(walls[-1] + float(rng.uniform(*columns)))
            walls = np.array(walls, np.float32) * tile / walls[-1] + rng.uniform(0, tile)
            walls = np.sort(walls % tile)
            here = row == r
            xs = x[here]
            index = np.searchsorted(walls, xs, side='right')
            left = np.where(index > 0, walls[np.maximum(index - 1, 0)], walls[-1] - tile)
            right = np.where(index < len(walls), walls[np.minimum(index, len(walls) - 1)], walls[0] + tile)
            distance[here] = np.minimum(distance[here], np.minimum(xs - left, right - xs))
            ident[here] = r * 64 + index % len(walls)
            across[here] = (xs - left) / (right - left)
        down = (y - top) / (bottom - top)
        return distance, ident, across, down

    def warp(self, field, du, dv):
        """Samples a periodic field at (u + du, v + dv), offsets in tiles, bilinearly."""
        n = self.n
        x = (self.u + du) * n
        y = (self.v + dv) * n
        x0 = np.floor(x).astype(np.int32)
        y0 = np.floor(y).astype(np.int32)
        fx = x - x0
        fy = y - y0
        x0 %= n
        y0 %= n
        x1 = (x0 + 1) % n
        y1 = (y0 + 1) % n
        return ((field[y0, x0] * (1 - fx) + field[y0, x1] * fx) * (1 - fy)
                + (field[y1, x0] * (1 - fx) + field[y1, x1] * fx) * fy)

    def blur(self, field, metres):
        """Periodic Gaussian blur with a standard deviation in metres."""
        sigma = metres / self.tile * self.n
        f = np.fft.fftfreq(self.n)
        fu, fv = np.meshgrid(f, f)
        kernel = np.exp(-2 * (math.pi * sigma) ** 2 * (fu * fu + fv * fv))
        return np.real(np.fft.ifft2(np.fft.fft2(field) * kernel)).astype(np.float32)

    def strokes(self, count, length, width, angle_of, colour_of, height_of, rgb, height):
        """Draws short periodic strokes (grass blades, straw) over rgb/height canvases in place."""
        n = self.n
        image = Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8))
        relief = Image.fromarray(np.clip(height * 255, 0, 255).astype(np.uint8))
        draw = ImageDraw.Draw(image)
        draw_h = ImageDraw.Draw(relief)
        rng = self.child()
        xs = rng.random(count) * n
        ys = rng.random(count) * n
        lengths = length[0] + (length[1] - length[0]) * rng.random(count)
        for i in range(count):
            x, y = xs[i], ys[i]
            a = angle_of(x / n, y / n, rng)
            ex = x + math.cos(a) * lengths[i]
            ey = y + math.sin(a) * lengths[i]
            colour = tuple(int(c * 255) for c in colour_of(x / n, y / n, rng))
            value = int(np.clip(height_of(rng) * 255, 0, 255))
            for ox in (-n, 0, n):
                if min(x, ex) + ox > n or max(x, ex) + ox < 0:
                    continue
                for oy in (-n, 0, n):
                    if min(y, ey) + oy > n or max(y, ey) + oy < 0:
                        continue
                    draw.line((x + ox, y + oy, ex + ox, ey + oy), fill=colour, width=width)
                    draw_h.line((x + ox, y + oy, ex + ox, ey + oy), fill=value, width=width)
        rgb[...] = np.asarray(image, np.float32) / 255
        height[...] = np.asarray(relief, np.float32) / 255


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 2:
        t = t[..., None]
    return np.asarray(a, np.float32) * (1 - t) + np.asarray(b, np.float32) * t


def colour(hex_or_tuple):
    if isinstance(hex_or_tuple, str):
        h = hex_or_tuple.lstrip('#')
        return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
    return np.array(hex_or_tuple, np.float32)


def fill(canvas, c):
    return np.broadcast_to(colour(c), (canvas.n, canvas.n, 3)).astype(np.float32).copy()


def shade(rgb, factor):
    return rgb * np.asarray(factor, np.float32)[..., None]


# ---- Outputs ---------------------------------------------------------------------------------------------------

def normals(canvas, height, strength=1.0):
    """Tangent-space normals from a height field in metres: x along +U (right), y along +V (down)."""
    pixel = canvas.tile / canvas.n
    gu = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / (2 * pixel) * strength
    gv = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) / (2 * pixel) * strength
    n = np.stack([-gu, -gv, np.ones_like(gu)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def occlusion(canvas, height, radii, strength):
    """Cavity occlusion: how far the surface lies below its neighbourhood, at a few scales, in metres."""
    ao = np.ones_like(height)
    for radius, weight in zip(radii, strength):
        depth = np.maximum(canvas.blur(height, radius) - height, 0)
        ao *= np.exp(-depth * weight)
    return np.clip(ao, 0, 1)


def flatten_tone(canvas, rgb, keep=.3):
    """Removes most of a ground map's variation broader than a third of its tile. Such variation repeats with the
    tile and reads as a regular pattern from the board's overview; the shader adds non-repeating broad variation."""
    blurred = np.stack([canvas.blur(rgb[..., i], canvas.tile / 3) for i in range(3)], -1)
    mean = rgb.reshape(-1, 3).mean(0)
    return rgb - blurred + mean + (blurred - mean) * keep


def save(name, canvas, rgb, height, normal_strength, ao, out):
    out.mkdir(parents=True, exist_ok=True)
    h = height - height.min()
    h = h / (h.max() + 1e-9)
    albedo = np.concatenate([np.clip(rgb, 0, 1), h[..., None]], -1)
    Image.fromarray(np.round(albedo * 255).astype(np.uint8), 'RGBA').save(out / f'{name}.png', optimize=True)
    n = normals(canvas, height, normal_strength)
    packed = np.concatenate([n * .5 + .5, ao[..., None]], -1)
    Image.fromarray(np.round(np.clip(packed, 0, 1) * 255).astype(np.uint8), 'RGBA').save(
        out / f'{name}-normal.png', optimize=True)
    return albedo, n, ao


# ---- Materials -------------------------------------------------------------------------------------------------
# Heights are metres. Colours are sRGB. Roles: ground (tops), debris (talus, rims, wear), wall (cliffs, rocks).

def sand(c):
    """Warm desert sand: broad swells and trains of wind ripples that fork, fade and bend; a few small pebbles."""
    swell = c.spectral(4, 1, 4) * .06
    bend = c.spectral(3, 1, 5) * .35 + c.spectral(2.5, 3, 10) * .08
    ripple = np.zeros_like(swell)
    choice = smoothstep(-.4, .4, c.spectral(3, 1, 4))
    for (ku, kv), weight in (((14, 5), 1 - choice), ((13, 7), choice)):
        phase = ku * c.u + kv * c.v + bend
        t = phase - np.floor(phase)
        # Gentle windward slope, steep lee face.
        ripple += weight * np.where(t < .75, smoothstep(0, .75, t), 1 - smoothstep(.75, 1, t))
    presence = smoothstep(-.8, .6, c.spectral(3, 1, 5))
    grains = c.spectral(.5, 150) * .0006
    f1, f2, ident, _, _ = c.worley(60, warp=.25)
    stone = c.per_cell(ident, 3600) < .05
    radius = c.per_cell(ident, 3600, .12, .3)
    pebble = np.where(stone, np.sqrt(np.clip(1 - (f1 / radius) ** 2, 0, 1)), 0)
    height = swell + ripple * presence * .012 + grains + pebble * .006
    tone = c.spectral(3, 1, 6)
    rgb = mix(fill(c, '#d69c66'), fill(c, '#c58352'), smoothstep(-1.8, 1.8, tone))
    rgb = mix(rgb, fill(c, '#e2b17f'), smoothstep(1.0, 2.4, c.spectral(3, 2, 10)) * .35)
    # Coarser, darker grains gather in the troughs.
    rgb = shade(rgb, 1 + (ripple - .5) * presence * .08)
    speck = c.child().random((c.n, c.n)).astype(np.float32)
    rgb = shade(rgb, np.where(speck < .02, .8, np.where(speck > .985, 1.06, 1)))
    rgb = mix(rgb, mix(fill(c, '#7d4a33'), fill(c, '#b08766'), c.per_cell(ident, 3600)), (pebble > 0) * .85)
    return rgb, height, 2.0


def pavement(c):
    """Desert pavement: varnished, closely packed stones and sandstone chips in a sandy matrix."""
    rgb = shade(fill(c, '#c9a57c'), 1 + .06 * c.spectral(2, 4, 60))
    height = c.spectral(2.5, 2, 30) * .004
    for cells, presence, size in ((16, .6, .03), (40, .55, .015)):
        f1, f2, ident, _, _ = c.worley(cells, warp=.08)
        count = cells * cells
        present = c.per_cell(ident, count) < presence
        edge = smoothstep(.03, .14, f2 - f1)
        dome = np.clip(1 - (f1 / .75) ** 2, 0, 1) ** .35
        mask = present * edge * dome
        top = c.per_cell(ident, count, .6, 1.0) * size
        height = np.maximum(height, mask * top)
        pick = c.per_cell(ident, count)
        stone = mix(fill(c, '#7a432a'), fill(c, '#b8744a'), smoothstep(.0, .45, pick))
        stone = mix(stone, fill(c, '#cf9a6c'), smoothstep(.5, .7, pick))
        stone = mix(stone, fill(c, '#5a4034'), smoothstep(.82, .9, pick))
        stone = mix(stone, fill(c, '#e0c49c'), smoothstep(.93, .99, pick))
        stone = shade(stone, .85 + .3 * dome)
        rgb = mix(rgb, stone, np.clip(mask * 3, 0, 1))
    rgb = shade(rgb, 1 + .08 * c.spectral(3, 1, 5))
    return rgb, height, 1.4

def sandstone(c):
    """Jointed sandstone: vertical master joints split thick beds into tall columns; minor joints reach part way down
    a bed, and only some bed partings are open. Each block is broken into flat, tilted spalls that step at their
    edges, and its arrises are eroded, so nothing reads as masonry. Desert varnish streaks run down from the
    partings. Rows run downward, so V is depth below the top of the tile."""
    rng = c.child()
    tile = c.tile
    thickness = []
    while sum(thickness) < tile:
        thickness.append(float(rng.uniform(1.4, 3.6)))
    bounds = np.cumsum([0] + thickness) / sum(thickness)
    beds = len(thickness)
    parted = rng.random(beds) < .7
    hardness = rng.uniform(-1, 1, beds).astype(np.float32)
    depth = (c.v + c.spectral(3, 1, 5, stretch=(1, 6)) * .008 + c.spectral(2.5, 4, 16, stretch=(1, 3)) * .002) % 1.0
    bed = np.clip(np.searchsorted(bounds, depth, side='right') - 1, 0, beds - 1)
    below_top = (depth - bounds[bed]) * tile
    above_bottom = (bounds[bed + 1] - depth) * tile
    parting = np.minimum(np.where(parted[bed], below_top, np.inf),
                         np.where(parted[(bed + 1) % beds], above_bottom, np.inf))
    within = below_top / (below_top + above_bottom)
    # Joints wander as they run down; a master joint jogs a little at each bed but runs on through most of them.
    x = (c.u + c.spectral(3, 1, 6, stretch=(3, 1)) * .02 + c.spectral(2.5, 4, 20, stretch=(2, 1)) * .003) % 1.0
    masters = np.cumsum(rng.uniform(1.6, 3.4, 12)) / tile
    masters = (masters[masters < 1.0] + rng.uniform(0, 1)) % 1.0
    master = np.full(x.shape, np.inf, np.float32)
    minor = np.full(x.shape, np.inf, np.float32)
    ident = np.zeros(x.shape, np.int32)
    for b in range(beds):
        here = bed == b
        xs = x[here]
        cuts = np.sort(np.array([(m + rng.normal(0, .08) / tile) % 1.0 for m in masters if rng.random() < .9]
                                or [rng.uniform(0, 1)], np.float32))
        index = np.searchsorted(cuts, xs, side='right')
        left = np.where(index > 0, cuts[np.maximum(index - 1, 0)], cuts[-1] - 1.0)
        right = np.where(index < len(cuts), cuts[np.minimum(index, len(cuts) - 1)], cuts[0] + 1.0)
        master[here] = np.minimum(xs - left, right - xs) * tile
        ident[here] = b * 64 + index % len(cuts)
        # Minor joints open from the bed's top parting and die out part way down.
        for _ in range(int(rng.integers(1, 4))):
            position, reach = rng.uniform(0, 1), rng.uniform(.3, 1.0)
            gap = np.abs((xs - position + .5) % 1.0 - .5) * tile
            minor[here] = np.minimum(minor[here], np.where(within[here] < reach, gap + within[here] / reach * .02, np.inf))
    count = beds * 64
    # Spalls: flat facets, each tilted its own way, stepping where they meet.
    f1, f2, facet, ou, ov = c.worley(22, 22, warp=.35)
    facets = 22 * 22
    tilt_u, tilt_v = c.per_cell(facet, facets, -1, 1), c.per_cell(facet, facets, -1, 1)
    spall = (tilt_u * ou + tilt_v * ov) * (tile / 22) * .06 + c.per_cell(facet, facets, 0, .012)
    scarp = 1 - smoothstep(.0, .03, f2 - f1)
    # Eroded arrises: each block falls away irregularly over its last 20 to 45 cm toward an open joint.
    width = .025 + .045 * smoothstep(-1, 1.6, c.spectral(2.5, 2, 20))
    edge = np.minimum(master, parting)
    worn = .2 + .25 * smoothstep(-1.2, 1.2, c.spectral(2.5, 3, 30))
    arris = smoothstep(0, 1, (edge - width) / worn)
    proud = c.per_cell(ident, count, 0, .07) + .02 * hardness[bed]
    height = (.05 + proud + spall + c.spectral(2.5, 3, 14) * .012) * (.35 + .65 * arris)
    crack = 1 - smoothstep(width * .5, width, edge)
    fine = (1 - smoothstep(.008, .022, minor)) * .8
    faint = (1 - smoothstep(.004, .012, np.minimum(below_top, above_bottom))) * .5
    height -= crack * .07 + fine * .02 + faint * .006 + scarp * .004
    lamina = np.sin((c.u * tile * np.sin(.3 + .25 * hardness[bed]) + depth * tile * math.cos(.3)) * 2 * math.pi / .07)
    height += lamina * .0008
    p1, p2, pid, _, _ = c.worley(40, 40, warp=.3)
    pit = (c.per_cell(pid, 40 * 40) < .07) * np.clip(1 - p1 / .45, 0, 1)
    height -= pit * .01
    height += c.spectral(2, 6, 220) * .003 + c.spectral(.5, 180) * .001
    # Colour: red-brown columns, each block and each spall its own tone; broad bleached and deeper zones cross the beds.
    rgb = mix(fill(c, '#9c5637'), fill(c, '#b56c41'), c.per_cell(ident, count))
    rgb = shade(rgb, (1 + .05 * hardness[bed]) * c.per_cell(facet, facets, .94, 1.06))
    zone = c.spectral(3, 1, 6, stretch=(1, 2))
    rgb = mix(rgb, fill(c, '#c68b61'), smoothstep(.7, 1.8, zone) * .55)
    rgb = mix(rgb, fill(c, '#7f3f29'), smoothstep(-.7, -1.8, zone) * .5)
    rgb = shade(rgb, 1 + .05 * c.spectral(2.5, 2, 24) + .04 * c.spectral(1.5, 30, 160))
    # Fresh, paler rock where the arris has just broken away; varnish runs down from the open partings.
    rgb = mix(rgb, fill(c, '#c9906a'), (1 - arris) * (1 - crack) * .25)
    streak = smoothstep(.4, 1.6, c.spectral(2.2, 2, 40, stretch=(1, 9))) * smoothstep(-.2, .9, c.spectral(3, 1, 4))
    streak *= 1 - smoothstep(.2, 1.6, below_top)
    rgb = mix(rgb, fill(c, '#4a2a1d'), streak * .45)
    rgb = shade(rgb, 1 - crack * .4 - fine * .3 - faint * .12 - pit * .3)
    return rgb, height, 1.6


def granite(c):
    """Fractured granite: two or three long joint sets cut the face into tilted slabs that step at each joint;
    broad weathering tones, lichen and water streaks. No courses: nothing reads as masonry."""
    height = np.zeros((c.n, c.n), np.float32)
    joint = np.zeros((c.n, c.n), np.float32)
    rng = c.child()
    for angle, spacing, step in ((math.pi / 2 + rng.normal(0, .12), 3.2, .14),
                                 (rng.uniform(.35, .7), 4.5, .1),
                                 (math.pi - rng.uniform(.3, .6), 6.0, .08)):
        distance, fraction = c.fractures(angle, spacing, .1)
        # Joints open only in stretches; between them the slab steps down across the set.
        open_part = smoothstep(.25, .9, c.spectral(2.5, 1, 8))
        width = .02 + .05 * smoothstep(-1, 1.5, c.spectral(2.5, 2, 16))
        crack = (1 - smoothstep(width * .5, width, distance)) * open_part
        height += fraction * step - (1 - smoothstep(width, width + .15, distance)) * .06 * open_part
        joint = np.maximum(joint, crack)
    g1, g2, gid, _, _ = c.worley(15, 12, warp=.35)
    fine = (1 - smoothstep(.0, .015, g2 - g1)) * smoothstep(.7, 1.3, c.spectral(2.5, 2, 20))
    height -= fine * .012
    height += c.spectral(2.5, 1, 12) * .08 + c.spectral(2, 5, 120) * .012 + c.spectral(.5, 150) * .0015
    tone = c.spectral(2.8, 1, 10)
    rgb = mix(fill(c, '#8c8a85'), fill(c, '#aeaaa2'), smoothstep(-1.4, 1.4, tone))
    rgb = mix(rgb, fill(c, '#9a8c82'), smoothstep(.8, 1.8, c.spectral(3, 1, 8)) * .5)
    speck = c.child().random((c.n, c.n)).astype(np.float32)
    rgb = shade(rgb, np.where(speck < .05, .7, np.where(speck > .92, 1.08, 1)))
    lichen = smoothstep(1.3, 1.9, c.spectral(2.2, 3, 40)) * (1 - joint) * smoothstep(-.3, .8, c.spectral(3, 1, 4))
    hue = c.spectral(2, 2, 10)
    rgb = mix(rgb, mix(fill(c, '#9c9c72'), fill(c, '#b08a5c'), smoothstep(-.3, .3, hue)), lichen * .6)
    # Broad weathering: darker, water-stained zones and paler fresh breaks.
    rgb = shade(rgb, 1 + .12 * c.spectral(3, 1, 5, stretch=(1, 2)))
    streak = smoothstep(.2, 1.5, c.spectral(2.2, 2, 40, stretch=(1, 9))) * smoothstep(-.2, 1, c.spectral(3, 1, 4))
    rgb = mix(rgb, fill(c, '#4f4d49'), streak * .4)
    rgb = shade(rgb, 1 - joint * .5 - fine * .2)
    return rgb, height, 1.3

def grass(c):
    """A meadow seen from above: tussocks of radiating blades over dark thatch, drier and lusher patches."""
    f1, f2, ident, ou, ov = c.worley(26)
    count = 26 * 26
    clump = np.clip(1 - f1 / .85, 0, 1) ** 1.2 * c.per_cell(ident, count, .6, 1)
    patch = smoothstep(-1.0, 1.2, c.spectral(3, 1, 6))
    dry = smoothstep(.4, 1.6, c.spectral(3, 1, 8))
    # Muted olive greens and straw, the tones of the printed map Grassland #3 rather than a lawn's green.
    rgb = mix(fill(c, '#2e2f1b'), fill(c, '#2e2b1d'), smoothstep(.8, 1.8, c.spectral(2, 3, 30)))
    height = clump * .45
    rgb = mix(rgb, fill(c, '#4b4e29'), clump * .8)
    lush = [colour('#6b6f3a'), colour('#8d914c'), colour('#54582d'), colour('#9fa25a')]
    dryc = [colour('#969061'), colour('#ada674'), colour('#827e55'), colour('#bcb586')]
    def angle(u, v, rng):
        # Blades lean outward from their tussock's centre, with scatter.
        x, y = int(u * c.n) % c.n, int(v * c.n) % c.n
        return math.atan2(-float(ov[y, x]), -float(ou[y, x])) + rng.normal(0, .6)

    def blade(u, v, rng):
        x, y = int(u * c.n) % c.n, int(v * c.n) % c.n
        source = dryc if rng.random() < dry[y, x] * .8 else lush
        base = source[rng.integers(0, 4)] * (.75 + .5 * rng.random())
        return np.clip(base * (.85 + .35 * patch[y, x]), 0, 1)

    c.strokes(int(80000 * (c.n / 1024) ** 2), (3 * c.n / 1024, 11 * c.n / 1024), max(1, c.n // 1024),
              angle, blade, lambda rng: .5 + .5 * rng.random(), rgb, height)
    flower = c.child().random((c.n, c.n)).astype(np.float32)
    rgb = np.where((flower < .0012)[..., None], mix(fill(c, '#f2efe0'), fill(c, '#e8cf4a'), flower > .0006), rgb)
    rgb = shade(rgb, .9 + .2 * patch)
    # A meadow in sun is brighter than its individual blades suggest: lift the whole palette.
    rgb = np.clip(rgb * 1.3, 0, 1)
    return rgb, height * .03 + clump * .02, 1.2


def scree(c):
    """Angular rock fragments of three sizes, heaped over dark grit: tilted faceted stones with open gaps."""
    rgb = shade(fill(c, '#4f4c47'), 1 + .18 * c.spectral(1, 60))
    height = c.spectral(2, 10, 200) * .005
    for cells, presence, size in ((8, .6, .16), (18, .65, .08), (40, .6, .035)):
        f1, f2, ident, ou, ov = c.worley(cells, warp=.08)
        count = cells * cells
        present = c.per_cell(ident, count) < presence
        su = c.per_cell(ident, count, -1.2, 1.2)
        sv = c.per_cell(ident, count, -1.2, 1.2)
        # A stone fills most of its cell; its tilted facet rounds off toward the gap.
        edge = smoothstep(.05, .2, f2 - f1)
        top = (c.per_cell(ident, count, .55, 1) * size + (su * ou + sv * ov) / cells * c.tile * .3) * edge ** .5
        stone = present & (edge > .02) & (top > height)
        height = np.where(stone, top, height)
        pick = c.per_cell(ident, count)
        face = mix(fill(c, '#85827b'), fill(c, '#a9a59b'), smoothstep(.2, .8, pick))
        face = mix(face, fill(c, '#71675d'), smoothstep(.82, .95, pick))
        face = shade(face, (.8 + .3 * c.per_cell(ident, count)) * (.75 + .25 * edge))
        rgb = np.where(stone[..., None], face, rgb)
    rgb = shade(rgb, 1 + .06 * c.spectral(3, 1, 6))
    return rgb, height, 1.0

def gravel(c):
    """Rounded mixed pebbles in a silty matrix."""
    rgb = shade(fill(c, '#5e4a38'), 1 + .1 * c.spectral(1, 60))
    height = c.spectral(2, 10, 200) * .003
    for cells, presence, size in ((22, .8, .03), (55, .65, .012)):
        f1, f2, ident, _, _ = c.worley(cells)
        count = cells * cells
        present = c.per_cell(ident, count) < presence
        radius = c.per_cell(ident, count, .45, .7)
        dome = np.sqrt(np.clip(1 - (f1 / radius) ** 2, 0, 1)) * smoothstep(.0, .06, f2 - f1)
        mask = present * (dome > 0)
        height = np.maximum(height, dome * present * c.per_cell(ident, count, .6, 1) * size)
        pick = c.per_cell(ident, count)
        stone = mix(fill(c, '#6e5c4a'), fill(c, '#8c765c'), smoothstep(.1, .6, pick))
        stone = mix(stone, fill(c, '#4f3f31'), smoothstep(.7, .9, pick))
        stone = mix(stone, fill(c, '#a49682'), smoothstep(.94, .99, pick))
        rgb = mix(rgb, shade(stone, .8 + .3 * dome), mask)
    return rgb, height, 1.3


def dirt(c):
    """Bare soil: clods, faint drying cracks that come and go, a few pebbles, humus patches and straw."""
    height = c.spectral(3, 1, 12) * .02
    f1, f2, ident, _, _ = c.worley(34, warp=.3)
    clod = np.clip(1 - f1 / .8, 0, 1) ** .7 * (c.per_cell(ident, 34 * 34) < .6)
    height += clod * .008
    k1, k2, _, _, _ = c.worley(7, warp=.35)
    open_crack = smoothstep(.1, .9, c.spectral(2.5, 2, 20))
    crack = (1 - smoothstep(0, .02 + .03 * open_crack, k2 - k1)) * open_crack
    height -= crack * .008
    p1, p2, pid, _, _ = c.worley(60, warp=.3)
    pebble = (c.per_cell(pid, 3600) < .04) * np.sqrt(np.clip(1 - (p1 / .4) ** 2, 0, 1))
    height += pebble * .01
    height += c.spectral(1, 60) * .0015
    rgb = mix(fill(c, '#6e5038'), fill(c, '#8a6a4c'), smoothstep(-1, 1.2, c.spectral(3, 1, 6)))
    rgb = mix(rgb, fill(c, '#503a26'), smoothstep(.2, 2.2, c.spectral(3, 1, 8)) * .5)
    rgb = shade(rgb, 1 + clod * .08 - crack * .18 + .08 * c.spectral(1, 40))
    rgb = mix(rgb, mix(fill(c, '#7d7264'), fill(c, '#9c8a72'), c.per_cell(pid, 3600)), (pebble > 0) * .8)
    straw_rgb = rgb.copy()
    straw_h = np.zeros((c.n, c.n), np.float32)
    c.strokes(int(1500 * (c.n / 1024) ** 2), (4 * c.n / 1024, 12 * c.n / 1024), 1,
              lambda u, v, rng: rng.random() * math.pi * 2,
              lambda u, v, rng: colour('#a8966a') * (.8 + .3 * rng.random()), lambda rng: 1.0, straw_rgb, straw_h)
    rgb = np.where((straw_h > .5)[..., None], straw_rgb, rgb)
    return rgb, height + straw_h * .002, 1.5


def rock(c):
    """Exposed bedrock: slabs of uneven size split by winding, soil-filled joints; weathered tops and lichen."""
    f1, f2, ident, ou, ov = c.worley(6, 6, .95, warp=.18)
    count = 36
    su = c.per_cell(ident, count, -.1, .1)
    sv = c.per_cell(ident, count, -.1, .1)
    width = .02 + .05 * smoothstep(-1, 1.5, c.spectral(2.5, 2, 16))
    gap = f2 - f1
    # Rounded slab edges falling into the joint.
    height = c.per_cell(ident, count, 0, .1) + (su * ou + sv * ov) / 6 * c.tile
    height -= (1 - smoothstep(width, width + .12, gap)) * .06
    joint = 1 - smoothstep(width * .4, width, gap)
    g1, g2, gid, _, _ = c.worley(18, warp=.25)
    crack = (1 - smoothstep(0, .02, g2 - g1)) * smoothstep(.2, .8, c.spectral(2.5, 2, 20))
    height -= crack * .012
    height += c.spectral(2, 4, 100) * .012 + c.spectral(.5, 150) * .001
    rgb = mix(fill(c, '#7d786f'), fill(c, '#9b958a'), c.per_cell(ident, count))
    rgb = shade(rgb, 1 + .09 * c.spectral(2.5, 2, 30))
    lichen = smoothstep(1.0, 1.5, c.spectral(2.2, 3, 60)) * (1 - joint)
    rgb = mix(rgb, mix(fill(c, '#9a9c68'), fill(c, '#b6b2a0'), smoothstep(-.2, .4, c.spectral(2, 2, 10))), lichen * .7)
    soil = mix(fill(c, '#3b3127'), fill(c, '#62574a'), c.child().random((c.n, c.n)).astype(np.float32))
    rgb = mix(rgb, soil, joint * .9)
    rgb = shade(rgb, 1 - crack * .3)
    return rgb, height, 1.2


def snow(c):
    """Settled granular snow: shallow irregular crust and fine grains, without repeated sastrugi waves."""
    height = c.spectral(3.2, 2, 10) * .009 + c.spectral(1.8, 10, 65) * .002
    height += c.spectral(.8, 65, 240) * .0006
    hollow = smoothstep(.003, -.012, height - c.blur(height, .18))
    rgb = mix(fill(c, '#f1f3f6'), fill(c, '#e4e9ef'), hollow * .45)
    rgb = shade(rgb, 1 + .008 * c.spectral(2, 3, 24))
    return rgb, height, 1.1


def aggregate(c, paste, clouds):
    """Cast concrete as it looks close up: a pale, neutral cement paste mottled by soft darker clouds, dense small
    specks of dark aggregate (more of them inside the clouds), paler grains, and small sharp pores. Returns rgb and
    height in metres."""
    cloud = smoothstep(.2, 1.9, c.spectral(2.4, 2, 48))
    rgb = mix(fill(c, paste), fill(c, clouds), cloud * .7)
    rgb = shade(rgb, 1 + .03 * c.spectral(2, 6, 160) + .025 * c.spectral(3, 1, 8))
    height = c.spectral(.8, 60, 400) * .0004 + c.spectral(3, 2, 20) * .0012
    # Aggregate at two sizes: irregular specks, each with its own darkness.
    for cells, share, radii, darkness in ((150, .32, (.12, .34), (.55, .8)), (55, .12, (.1, .26), (.5, .72))):
        f1, _, ident, _, _ = c.worley(cells, warp=.12)
        count = cells * cells
        present = c.per_cell(ident, count) < share * (.55 + .9 * cloud)
        speck = present & (f1 < c.per_cell(ident, count, *radii))
        rgb = shade(rgb, np.where(speck, c.per_cell(ident, count, *darkness), 1))
    grain = c.child().random((c.n, c.n)).astype(np.float32)
    rgb = shade(rgb, np.where(grain > .965, 1.09, 1))
    f1, _, ident, _, _ = c.worley(90)
    pore = (c.per_cell(ident, 8100) < .07) * np.clip(1 - f1 / c.per_cell(ident, 8100, .1, .24), 0, 1)
    height -= pore * .004
    rgb = shade(rgb, 1 - .5 * smoothstep(0, .3, pore))
    return rgb, height


def concrete(c):
    """Pavement: the slabs' concrete, weathered darker and warmer than a wall, with float marks and a faint broom
    finish; no joints or cracks to fight the hex grid."""
    rgb, height = aggregate(c, '#abaaa5', '#8f8d88')
    height += c.spectral(3, 1, 8) * .002 + c.spectral(1.5, 30, 200, stretch=(1, 8), angle=.3) * .0008
    rgb = mix(rgb, fill(c, '#7f7b74'), smoothstep(.8, 2.2, c.spectral(3, 2, 12)) * .3)
    return rgb, height, 3.0


def earth(c):
    """A cut soil bank, V running down from the ground surface: a dark, rooty topsoil over paler subsoil that grades
    through faint, wavy horizons; a few embedded stones; rills and slump scars washed down the face."""
    rng = c.child()
    wave = c.spectral(3, 1, 6, stretch=(1, 5)) * .025 + c.spectral(2.5, 4, 20, stretch=(1, 3)) * .006
    depth = (c.v + wave) % 1.0
    # Topsoil at the top of the tile; the subsoil below brightens with depth, with two faint horizons.
    top = .06 + .03 * c.spectral(3, 1, 6)
    subsoil = mix(fill(c, '#8a6644'), fill(c, '#a07a52'), smoothstep(top, .7, depth))
    rgb = mix(fill(c, '#4a3524'), subsoil, smoothstep(top - .015, top + .025, depth))
    for level, strength in ((rng.uniform(.3, .45), .1), (rng.uniform(.6, .8), .08)):
        band = 1 - smoothstep(0, .02, np.abs(depth - level - .01 * c.spectral(2.5, 2, 12)))
        rgb = shade(rgb, 1 - band * strength)
    rgb = shade(rgb, 1 + .08 * c.spectral(2, 3, 60) + .05 * c.spectral(3, 1, 6))
    # Rills: shallow grooves washed straight down the face, and a few paler slump scars.
    rill = c.spectral(2.4, 3, 60, stretch=(1, 10))
    height = rill * .012 + c.spectral(2, 8, 150) * .005 - (1 - smoothstep(top - .02, top + .03, depth)) * .01
    rgb = shade(rgb, 1 - .1 * smoothstep(.4, 1.6, -rill))
    scar = smoothstep(.9, 1.6, c.spectral(3, 1, 5, stretch=(1, 2)))
    rgb = mix(rgb, fill(c, '#b08a60'), scar * .35)
    f1, f2, ident, _, _ = c.worley(14, warp=.08)
    radius = c.per_cell(ident, 196, .18, .38)
    present = (c.per_cell(ident, 196) < .06) & (depth > top + .03)
    stone = present * np.sqrt(np.clip(1 - (f1 / radius) ** 2, 0, 1))
    height += stone * .05
    # Each stone sits in a shadowed socket of soil.
    socket = present * (1 - smoothstep(radius, radius * 1.5, f1)) * (stone <= 0)
    rgb = shade(rgb, 1 - socket * .3)
    rgb = mix(rgb, shade(mix(fill(c, '#6b5f52'), fill(c, '#8a7a66'), c.per_cell(ident, 196)), .75 + .35 * stone),
              (stone > 0) * .95)
    roots_rgb = rgb.copy()
    roots_h = np.zeros((c.n, c.n), np.float32)
    c.strokes(int(1400 * (c.n / 1024) ** 2), (5 * c.n / 1024, 24 * c.n / 1024), max(1, c.n // 1024),
              lambda u, v, rng: math.pi / 2 + rng.normal(0, .6),
              lambda u, v, rng: colour('#2c2016') * (.8 + .4 * rng.random()), lambda rng: 1.0, roots_rgb, roots_h)
    # Roots reach down from the topsoil into the upper subsoil only.
    keep = (roots_h > .5) & (depth < top + .12)
    rgb = np.where(keep[..., None], roots_rgb, rgb)
    return rgb, height, 1.3

def cast(c):
    """The face of a cast slab. Only the concrete itself: the shader lays out the slabs, their joints, tone and grime,
    and gives each slab its own window of this map, so nothing here may form a pattern."""
    rgb, height = aggregate(c, '#b9b8b4', '#9c9b96')
    return rgb, height, 2.0


MATERIALS = {
    # name: (generator, tile metres, role, seed)
    'sand': (sand, 6.0, 'ground', 101),
    'grass': (grass, 4.0, 'ground', 102),
    'dirt': (dirt, 5.0, 'ground', 103),
    'rock': (rock, 8.0, 'ground', 104),
    'lunar': (rock, 8.0, 'ground', 104),
    'lunar-scree': (scree, 4.0, 'debris', 202),
    'snow': (snow, 8.0, 'ground', 105),
    'concrete': (concrete, 6.0, 'ground', 106),
    'pavement': (pavement, 3.0, 'debris', 201),
    'scree': (scree, 4.0, 'debris', 202),
    'gravel': (gravel, 3.0, 'debris', 203),
    'sandstone': (sandstone, 12.0, 'wall', 301),
    'granite': (granite, 10.0, 'wall', 302),
    'earth': (earth, 20.0, 'wall', 303),
    'cast': (cast, 8.0, 'wall', 304),
}


def preview(results, path):
    """Lit contact sheet: each material once (left) and tiled 2x2 (right), sun from the upper left."""
    cells = []
    light = np.array([-.55, -.45, .7], np.float32)
    light /= np.linalg.norm(light)
    for name, (albedo, normal, ao) in results.items():
        linear = albedo[..., :3] ** 2.2
        lit = linear * (.35 * ao[..., None] + 1.1 * np.clip(normal @ light, 0, 1)[..., None])
        image = Image.fromarray(np.round(np.clip(lit, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8))
        single = image.resize((256, 256), Image.LANCZOS)
        tiled = Image.new('RGB', (image.width * 2, image.height * 2))
        for i in range(4):
            tiled.paste(image, ((i % 2) * image.width, (i // 2) * image.height))
        cell = Image.new('RGB', (512, 280), (40, 40, 40))
        cell.paste(single, (0, 24))
        cell.paste(tiled.resize((256, 256), Image.LANCZOS), (256, 24))
        ImageDraw.Draw(cell).text((6, 6), name, fill=(230, 230, 230))
        cells.append(cell)
    columns = 3
    sheet = Image.new('RGB', (512 * columns, 280 * ((len(cells) + columns - 1) // columns)), (20, 20, 20))
    for i, cell in enumerate(cells):
        sheet.paste(cell, ((i % columns) * 512, (i // columns) * 280))
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--size', type=int, default=512)
    parser.add_argument('--only', default='')
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args()
    names = [n for n in args.only.split(',') if n] or list(MATERIALS)
    results = {}
    for name in names:
        generator, tile, role, seed = MATERIALS[name]
        canvas = Canvas(args.size, tile, seed)
        rgb, height, strength = generator(canvas)
        if role != 'wall':
            rgb = flatten_tone(canvas, rgb)
        ao = occlusion(canvas, height, (tile / 200, tile / 40), (60 / tile * 8, 12 / tile * 8))
        results[name] = save(name, canvas, rgb, height, strength, ao, args.out)
        print(f'{name}: {tile} m, {role}')
    if not args.only:
        path = args.out / 'manifest.json'
        existing = json.loads(path.read_text())['materials'] if path.exists() else {}
        manifest = {'generator': 'tools/build_terrain_materials.py', 'license': 'CC0-1.0', 'size': args.size,
                    'materials': existing | {n: {'tile': t, 'role': r, 'seed': s} for n, (_, t, r, s) in MATERIALS.items()}}
        path.write_text(json.dumps(manifest, indent=2) + '\n')
    if args.preview:
        preview(results, args.preview)


if __name__ == '__main__':
    main()
