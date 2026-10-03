"""Bake generated soil and granite into the existing sculpt material layout.

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
# A bank needs visible clods, not a two-metre photograph of almost subpixel grit.
# Its nine-centimetre height field remains shallow compared with the exposed cliff rock.
PROFILES = {'soil': (5.0, .09, 'mantle'), 'granite': (4.0, .04, 'wall')}
SIZE = 512


def bake(name, out):
    tile, relief, _ = PROFILES[name]
    with Image.open(SOURCES / (name + '.png')) as image:
        rgb = np.asarray(image.convert('RGB').resize((SIZE, SIZE), Image.Resampling.LANCZOS)) / 255.0
    rgb = np.clip(periodic(rgb), .015, .985)
    canvas = Canvas(SIZE, tile, 0)
    light = rgb @ np.array([.2126, .7152, .0722])
    # Keep soil clods coherent at board-view scale. Physical filtering excludes tiny pigment speckles from
    # the height field without blurring the albedo; POM, normals and cavities all follow that same field.
    height = (canvas.blur(light, .035) * .7 + canvas.blur(light, .11) * .3 if name == 'soil'
              else blur(light, 1.6) * .7 + blur(light, 6) * .3)
    low, high = np.percentile(height, [1, 99])
    height = np.clip((height - low) / max(high - low, .01), 0, 1) * relief
    albedo = flatten_tone(canvas, rgb, keep=.2)
    ao = (occlusion(canvas, height, (.06, .20), (14, 7)) if name == 'soil'
          else occlusion(canvas, height, (.02, .08), (40, 18)))
    save(name + '-contact', canvas, albedo, height, 1.0, ao, out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--only', nargs='+', choices=tuple(PROFILES), help='Bake or check just these contact materials')
    args = parser.parse_args()
    manifest_path = OUT / 'manifest.json'
    entries = {}
    for name in args.only or PROFILES:
        tile, relief, role = PROFILES[name]
        runtime_name = name + '-contact'
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
        else:
            bake(name, OUT)
        entries[runtime_name] = entry
        print(f'{runtime_name}: {SIZE}x{SIZE}, {tile} m repeat; ' + ('checked' if args.check else 'baked'))
    # Other material bakers share this manifest. Resolve it after the bake and replace only selected entries.
    manifest = json.loads(manifest_path.read_text())
    if args.check:
        for name, entry in entries.items():
            if manifest['materials'].get(name) != entry:
                raise SystemExit('Stale contact manifest: ' + name)
    else:
        manifest['materials'].update(entries)
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
