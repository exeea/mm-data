"""Bake preserved plant sources: cutouts, estimated relief normals and packed leaf surface maps."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from prepare_cliff_materials import blur, normal_map, periodic

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'tools/foliage-sources'
OUT = ROOT / 'data/models/board/textures/foliage'


def bake(source):
    with Image.open(source) as image:
        pixels = np.array(image.convert('RGBA').resize((512, 512), Image.Resampling.LANCZOS))
    alpha = pixels[:, :, 3].copy()
    valid = alpha > 127
    assert .15 < valid.mean() < .85, f'{source.name}: expected a branch cutout'
    # Colour only expands into transparent pixels: alpha and the original silhouette stay intact.
    for _ in range(8):
        total = np.zeros(pixels[:, :, :3].shape, dtype=np.float32)
        count = np.zeros(valid.shape, dtype=np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            mask = np.roll(valid, (dy, dx), (0, 1))
            total += np.roll(pixels[:, :, :3], (dy, dx), (0, 1)) * mask[:, :, None]
            count += mask
        fill = ~valid & (count > 0)
        pixels[fill, :3] = np.rint(total[fill] / count[fill, None]).astype(np.uint8)
        valid |= fill
    pixels[:, :, 3] = alpha
    return pixels


def cactus_maps():
    with Image.open(SOURCES / 'cactus-skin.png') as image:
        color = np.asarray(image.convert('RGB').resize((512, 512), Image.Resampling.LANCZOS)) / 255.0
    color = np.clip(periodic(color), 0, 1)
    # Source-aligned estimated shallow rib/areole relief, never extra stem geometry.
    height = blur(color @ np.array([.2126, .7152, .0722]), 1.3)
    return {'cactus-skin': np.rint(color * 255).astype(np.uint8),
            'cactus-skin-normal': normal_map(height, .035)}


def leaf_maps(name, pixels):
    """Source-aligned shallow relief and AO/roughness/transmission; no displacement or baked sunlight.

    These are artistic estimates from the preserved source, not measured scan data.
    Broad source lighting is removed before estimating relief, and bark-colored veins
    transmit less than green leaf tissue. Alpha remains in the original color map.
    """
    color = pixels[:, :, :3] / 255.0
    alpha = pixels[:, :, 3] / 255.0
    light = color @ np.array([.2126, .7152, .0722])
    detail = blur(light, 1.2) - blur(light, 6)
    height = detail * .35 + blur(alpha, 1.4) * .12
    cavity = np.clip(np.exp(-np.maximum(blur(light, 4) - light, 0) * 1.8), .65, 1)
    green = np.clip((color[:, :, 1] - color[:, :, 0] * .6 - color[:, :, 2] * .4)
                    / np.maximum(color[:, :, 1], .05) * 3, 0, 1)
    snow = '-snow-' in name
    roughness = np.full_like(light, .85) if snow else np.clip(.62 - .15 * green + .1 * (1 - light), .4, .85)
    transmission = np.zeros_like(light) if snow else green * .65
    surface = np.stack((cavity, roughness, transmission), axis=-1)
    return {name + '-normal': normal_map(height, .012 if snow else .018),
            name + '-surface': np.rint(surface * 255).astype(np.uint8)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    maps = {source.stem: bake(source) for source in sorted(SOURCES.glob('*-cutout.png'))}
    for name, pixels in list(maps.items()):
        maps.update(leaf_maps(name, pixels))
    maps.update(cactus_maps())
    for name, pixels in maps.items():
        destination = OUT / (name + '.png')
        if args.check:
            with Image.open(destination) as expected:
                assert np.array_equal(pixels, np.array(expected)), f'Stale foliage texture: {destination}'
        else:
            Image.fromarray(pixels).save(destination)
        print(name, 'checked' if args.check else 'baked')
