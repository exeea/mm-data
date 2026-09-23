"""Bake photographic ground sets, at documented metre scales, using the cliff map format.

Height is estimated from source photographs, not a measured scan. The source, height,
normal, roughness and occlusion all share the same periodic field. No runtime baking.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from prepare_cliff_materials import blur, normal_map, periodic, pixels

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/models/board/textures/ground'
# Authored metres, height range, roughness. The renderer enlarges detail to a ten-metre visual hex.
PROFILES = {'grass': (4, .065, .94), 'dirt': (3, .08, .9), 'sand': (4, .12, .91),
            'rock': (6, .28, .8), 'concrete': (4, .022, .8), 'snow': (4, .12, .76),
            'water_bed': (3, .10, .72)}


def prepare(family):
    folder = 'cliff-sources' if family == 'concrete' else 'ground-sources'
    source = ROOT / 'tools' / folder / f'{family}.png'
    with Image.open(source) as image:
        rgb = np.asarray(image.convert('RGB').resize((1024, 1024), Image.Resampling.LANCZOS)) / 255.0
    rgb = np.clip(periodic(rgb), .012, .99)
    light = rgb @ np.array([.2126, .7152, .0722])
    field = blur(light, 1.4) * .45 + blur(light, 4) * .35 + blur(light, 12) * .20
    low, high = np.percentile(field, [1, 99])
    height = np.clip((field - low) / max(high - low, .01), 0, 1) * .9 + .05
    metres, amplitude, roughness = PROFILES[family]
    encoded = round(amplitude / metres / .1 * 255)
    depth = encoded / 255 * .1
    albedo = rgb * np.power(np.mean(light) / np.maximum(blur(light, 5), .03), .28)[..., None]
    cavity = np.maximum(blur(height, 9) - height, 0)
    packed = np.stack((height, np.clip(roughness + (.5 - height) * .09, .35, .98),
                       np.exp(-cavity * 2.2), np.full_like(height, encoded / 255)), axis=-1)
    maps = {f'{family}.png': pixels(albedo), f'{family}-normal.png': normal_map(height, depth),
            f'{family}-surface.png': pixels(packed)}
    return maps, {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'size': 1024,
                  'metres_per_repeat': metres, 'height_metres': amplitude, 'relief_uv': depth}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = {'generator': 'tools/prepare_ground_materials.py', 'families': {}}
    if not args.check:
        OUTPUT.mkdir(parents=True, exist_ok=True)
    for family in PROFILES:
        maps, entry = prepare(family)
        manifest['families'][family] = entry
        for name, data in maps.items():
            path = OUTPUT / name
            if args.check:
                with Image.open(path) as existing:
                    if not np.array_equal(np.array(existing), data):
                        raise SystemExit(f'Stale ground map: {path}')
            else:
                Image.fromarray(data).save(path, optimize=True)
        print(f'{family}: 1024 square, {entry["metres_per_repeat"]} metres per repeat')
    path = OUTPUT / 'manifest.json'
    if args.check:
        if json.loads(path.read_text()) != manifest:
            raise SystemExit('Stale ground manifest')
    else:
        path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
