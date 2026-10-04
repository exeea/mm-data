"""Bake generated ground and cliff sources into the existing sculpt material layout.

Uses the shared periodic filtering and sculpt normal/AO baker. Estimated relief
is artistic, not measured. Run from any directory; --check verifies every pixel.
"""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from build_terrain_materials import Canvas, OUT, flatten_tone, occlusion, save
from prepare_cliff_materials import blur, periodic

SOURCES = Path(__file__).resolve().parent / 'terrain-contact-sources'
PROFILES = {'soil': (4.0, .095, 'mantle', 'soil-contact'),
            'granite-bedrock': (8.0, .08, 'wall', 'granite-contact'),
            'dirt': (5.0, .045, 'ground', 'dirt'),
            'sandstone': (12.0, .16, 'wall', 'sandstone'),
            'sand-ground': (6.0, .025, 'ground', 'sand'),
            'granite-scree': (4.0, .10, 'debris', 'scree'),
            'meadow-ground': (4.0, .025, 'ground', 'grass')}
SIZE = 512


def bake(name, out):
    tile, relief, _, runtime_name = PROFILES[name]
    with Image.open(SOURCES / (name + '.png')) as image:
        rgb = np.asarray(image.convert('RGB').resize((SIZE, SIZE), Image.Resampling.LANCZOS)) / 255.0
    rgb = np.clip(periodic(rgb), .015, .985)
    canvas = Canvas(SIZE, tile, 0)
    light = rgb @ np.array([.2126, .7152, .0722])
    # Gentle, source-aligned grain; pigment variation must not become deep relief.
    height = (blur(light, 1.6) * .7 + blur(light, 6) * .3 if runtime_name == 'granite-contact'
              else blur(light, 1.2) * .2 + blur(light, 4) * .55 + blur(light, 14) * .25)
    low, high = np.percentile(height, [1, 99])
    height = np.clip((height - low) / max(high - low, .01), 0, 1) * relief
    albedo = flatten_tone(canvas, rgb, keep=.2)
    ao = occlusion(canvas, height, (.02, .08), (40, 18))
    save(runtime_name, canvas, albedo, height, 1.0, ao, out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--only', nargs='+', choices=[*PROFILES, 'granite'], default=list(PROFILES))
    args = parser.parse_args()
    manifest_path = OUT / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for name in args.only:
        # Keep the original CLI name usable after replacing the source study.
        if name == 'granite':
            name = 'granite-bedrock'
        tile, relief, role, runtime_name = PROFILES[name]
        entry = {'tile': tile, 'role': role, 'size': SIZE,
                 'generator': 'tools/prepare_terrain_contact.py',
                 'source': f'tools/terrain-contact-sources/{name}.png',
                 'source_sha256': hashlib.sha256((SOURCES / (name + '.png')).read_bytes()).hexdigest(),
                 'height_source': 'estimated multiscale luminance', 'relief_metres': relief}
        if args.check:
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)
                bake(name, output)
                for suffix in ('.png', '-normal.png'):
                    with Image.open(output / (runtime_name + suffix)) as actual, Image.open(OUT / (runtime_name + suffix)) as expected:
                        if not np.array_equal(np.asarray(actual), np.asarray(expected)):
                            raise SystemExit('Stale contact material: ' + runtime_name + suffix)
            if manifest['materials'].get(runtime_name) != entry:
                raise SystemExit('Stale contact manifest: ' + runtime_name)
        else:
            bake(name, OUT)
            manifest['materials'][runtime_name] = entry
        print(f'{runtime_name}: {SIZE}x{SIZE}, {tile} m repeat; ' + ('checked' if args.check else 'baked'))
    if not args.check:
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
