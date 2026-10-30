"""Seamless 512 px sources (albedo.png, orm.png, normal.png) for a material project, from a photographic study.

    python tools/materials/photo_sources.py paint|rust <study.png> tools/materials/<folder>/<name>/sources

Needs numpy, scipy and Pillow. `paint`: painted metal; grey low-saturation spots are chips of bare steel (recessed,
rougher, a little metallic), orange ones rust drips (rough); the study's top quarter, where streaks start, is left out.
`rust`: steel with rust; steel is metallic and fairly smooth, rust rough and raised. The broad light is flattened,
the tile made seamless (seamless.py) and normals derived from the estimated height, OpenGL convention. A project
cloned from structures/common/grille reads the three sources into its Material node.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seamless import seamless  # noqa: E402

KIND, STUDY, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
SIZE = 512

image = np.asarray(Image.open(STUDY).convert('RGB'), float) / 255
h, w = image.shape[:2]
if KIND == 'paint':
    # The study's top quarter is where its streaks start: repeated, it would band every repeat.
    side = min(w, int(h * .74))
    image = image[h - side:, (w - side) // 2:(w - side) // 2 + side]
else:
    side = min(h, w)
    image = image[:side, :side]
# Flatten the broad light: the material's own shading comes from the game's lighting.
luminance = image.mean(2)
broad = gaussian_filter(luminance, side / 6, mode='reflect')
image = np.clip(image * (luminance.mean() / broad)[..., None], 0, 1)
image = seamless(image, np.ones(3))
image = np.asarray(Image.fromarray((np.clip(image, 0, 1) * 255).round().astype(np.uint8)).resize((SIZE, SIZE),
                                                                                                    Image.LANCZOS), float) / 255
r, g, b = image[..., 0], image[..., 1], image[..., 2]
lum = image.mean(2)
saturation = image.max(2) - image.min(2)
orange = np.clip((r - b - .04) / .2, 0, 1)


def blur(a, sigma):
    return gaussian_filter(a, sigma, mode='wrap')


def smoothstep(a, b_, x):
    t = np.clip((x - a) / (b_ - a), 0, 1)
    return t * t * (3 - 2 * t)


grain = lum - blur(lum, 3)
if KIND == 'paint':
    # Chips: grey bare steel where the paint is gone; drips: rust stains below them.
    chip = smoothstep(.62, .45, lum) * smoothstep(.16, .06, saturation)
    drip = orange * smoothstep(.85, .6, lum)
    grime = np.clip((lum.mean() - lum) / .25, 0, 1) * (1 - chip)
    # Rust specks, pitted through the paint and gathered in clusters, and a light dirt film (the photo is too clean
    # beside the designer's tanks).
    rng = np.random.default_rng(2)
    clusters = blur(rng.standard_normal(lum.shape), 24)
    clusters = smoothstep(0, 1.5 * clusters.std(), clusters)
    pits = blur(rng.standard_normal(lum.shape), 1.2)
    speck = smoothstep(1.7, 2.5, pits / pits.std()) * (.2 + .8 * clusters)
    # Fewer, larger rust blotches where the paint has flaked through.
    flakes = blur(rng.standard_normal(lum.shape), 3.5)
    speck = np.maximum(speck, smoothstep(1.9, 2.5, flakes / flakes.std()) * (.5 + .5 * clusters))
    halo = np.clip(blur(speck, 2.5) * 2, 0, 1) * (1 - speck)
    # The dirt runs down in streaks.
    film = blur(rng.standard_normal(lum.shape), (40, 5))
    film = smoothstep(0, 1.5 * film.std(), film)
    image = image * (1 - .12 * film)[..., None]
    image = image * (1 - speck - .35 * halo)[..., None] + (speck[..., None] * [.40, .23, .14]
                                                         + .35 * halo[..., None] * [.55, .38, .27])
    lum = image.mean(2)
    grime = np.maximum(grime, .6 * film)
    height = .7 - .45 * blur(chip, .8) - .3 * speck + .12 * grain
    # Glossy enamel, as painted tanks are, its reflections broken by dried water stains (a wrapped noise drawn out
    # sideways) with a thin tide line round each; grime, chips and drips dull it further.
    stains = blur(np.random.default_rng(1).standard_normal(lum.shape), (7, 18))
    slope = np.hypot(np.roll(stains, 1, 0) - np.roll(stains, -1, 0), np.roll(stains, 1, 1) - np.roll(stains, -1, 1)) / 2
    tides = smoothstep(1.2, 0, np.abs(stains) / np.maximum(slope, 1e-9))
    roughness = np.clip(.13 + .2 * smoothstep(-.2 * stains.std(), stains.std(), stains) + .3 * tides + .3 * grime
                        + .45 * chip + .45 * drip + .5 * speck, 0, 1)
    metallic = .55 * chip
    strength = 6.0
else:
    rust = blur(smoothstep(.15, .6, orange) * smoothstep(.04, .12, saturation), .6)
    height = .45 + .35 * blur(rust, 1.5) + .2 * grain / (np.abs(grain).max() or 1)
    roughness = np.clip(.4 + .45 * rust + .4 * np.abs(grain), 0, 1)
    metallic = .8 * (1 - rust)
    strength = 5.0
dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / 2
dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) / 2
# OpenGL convention: +Y towards the image's top.
normal = np.stack([-dx * strength, dy * strength, np.ones_like(dx)], -1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
OUT.mkdir(parents=True, exist_ok=True)
Image.fromarray((image * 255).round().astype(np.uint8)).save(OUT / 'albedo.png')
orm = np.stack([np.ones_like(lum), roughness, metallic], -1)
Image.fromarray((orm * 255).round().astype(np.uint8)).save(OUT / 'orm.png')
Image.fromarray(((normal + 1) / 2 * 255).round().astype(np.uint8)).save(OUT / 'normal.png')
print(KIND, 'albedo mean', np.round(image.reshape(-1, 3).mean(0), 3), 'roughness', round(float(roughness.mean()), 2),
      'metallic', round(float(metallic.mean()), 2))
