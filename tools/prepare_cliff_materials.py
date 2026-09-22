"""Bake repeating cliff materials offline (NumPy + Pillow); no runtime image processing.

Source colors live in tools/cliff-sources. Optional NAME-height.png is a linear
grayscale authored height; without it, multiscale source luminance estimates relief.
This is an artistic approximation, not measured geometry or a photogrammetry scan.
Runtime maps: RGB color, RGB tangent normal (U/right, V/down), and RGBA surface
(height, perceptual roughness, ambient occlusion, UV relief range divided by 0.1).
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'tools/cliff-sources'
OUTPUT = ROOT / 'data/models/board/textures/cliffs'
SIZE = 1024
# Physical relief / 96-world-unit texture repeat, and dry perceptual roughness.
PROFILES = {'rock': (.047, .78), 'sand': (.040, .87), 'dirt': (.025, .93),
            'concrete': (.004, .82), 'snow': (.018, .73)}


def periodic(image):
    """Remove the smooth boundary mismatch using a periodic Poisson solve.

    Unlike mirror tiling, this retains one unreflected geological pattern. The
    same periodic signal supplies color, height, normals and all mip levels.
    """
    height, width = image.shape[:2]
    boundary = np.zeros_like(image, dtype=np.float64)
    boundary[0] = image[-1] - image[0]
    boundary[-1] = -boundary[0]
    boundary[:, 0] += image[:, -1] - image[:, 0]
    boundary[:, -1] -= image[:, -1] - image[:, 0]
    denominator = (2 * np.cos(2 * np.pi * np.arange(height) / height)[:, None]
                   + 2 * np.cos(2 * np.pi * np.arange(width) / width)[None, :] - 4)
    denominator[0, 0] = 1
    if image.ndim == 3:
        denominator = denominator[..., None]
    frequency = np.fft.fft2(boundary, axes=(0, 1)) / denominator
    frequency[0, 0] = 0
    return image - np.fft.ifft2(frequency, axes=(0, 1)).real


def blur(field, radius):
    """Gaussian convolution with wrap boundaries, including sub-pixel radii."""
    fy = np.fft.fftfreq(field.shape[0])[:, None]
    fx = np.fft.fftfreq(field.shape[1])[None, :]
    kernel = np.exp(-2 * np.pi ** 2 * radius ** 2 * (fx * fx + fy * fy))
    return np.fft.ifft2(np.fft.fft2(field) * kernel).real


def normal_map(height, depth):
    """Differentiate the actual height field at its UV/world scale, not color edges."""
    du = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * height.shape[1] / 2
    dv = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * height.shape[0] / 2
    normal = np.stack((-du * depth, -dv * depth, np.ones_like(height)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return np.rint(normal * 127 + 128).clip(0, 255).astype(np.uint8)


def pixels(values):
    return np.rint(np.clip(values, 0, 1) * 255).astype(np.uint8)


def prepare(family):
    source = SOURCES / f'{family}.png'
    with Image.open(source) as image:
        rgb = np.array(image.convert('RGB').resize((SIZE, SIZE), Image.Resampling.LANCZOS)) / 255.0
    rgb = np.clip(periodic(rgb), .015, .985)
    light = rgb @ np.array([.2126, .7152, .0722])
    authored = SOURCES / f'{family}-height.png'
    if authored.exists():
        with Image.open(authored) as image:
            maximum = 65535 if image.mode.startswith('I') else 255
            height = np.array(image.convert('F').resize((SIZE, SIZE), Image.Resampling.BICUBIC)) / maximum
        height = np.clip(periodic(height), 0, 1)
    else:
        # Broad fracture planes and finer grain share one field; no unrelated procedural bump noise.
        # Fine pigment/grain must not become deep embossing. Let broad erosion planes carry the relief,
        # with only a small contribution from the fine source detail to the height derivative.
        height = blur(light, 1.6) * .035 + blur(light, 7) * .265 + blur(light, 22) * .70
        low, high = np.percentile(height, [1, 99])
        height = np.clip((height - low) / max(high - low, .01), 0, 1) * .88 + .06
    depth, roughness = PROFILES[family]
    # Quantize the amplitude once; normal slopes use exactly the range the shader will decode.
    encoded_depth = round(depth / .1 * 255)
    depth = encoded_depth / 255 * .1
    # Reduce broad baked light in the source while retaining its mineral color and fine grain.
    albedo = rgb * np.power(np.mean(light) / np.maximum(blur(light, 6), .03), .48)[..., None]
    cavities = np.maximum(blur(height, 10) - height, 0)
    grain = light - blur(light, 2)
    surface = np.stack((height, np.clip(roughness + .08 * (.5 - height) - .20 * grain, .3, .98),
                        np.exp(-cavities * 3.5), np.full_like(height, encoded_depth / 255)), axis=-1)
    maps = {f'{family}.png': pixels(albedo), f'{family}-normal.png': normal_map(height, depth),
            f'{family}-surface.png': pixels(surface)}
    entry = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
             'height_source': authored.name if authored.exists() else 'estimated multiscale luminance',
             'height_sha256': hashlib.sha256(authored.read_bytes()).hexdigest() if authored.exists() else None,
             'size': SIZE, 'relief_uv': depth, 'roughness': roughness}
    return maps, entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare all shipped maps with a fresh deterministic bake')
    args = parser.parse_args()
    manifest = {'generator': 'tools/prepare_cliff_materials.py', 'families': {}}
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
                        raise SystemExit(f'Stale cliff map: {path}')
            else:
                Image.fromarray(data).save(path, optimize=True)
        print(f'{family}: {SIZE}x{SIZE}, relief {entry["relief_uv"]:.4f} UV')
    path = OUTPUT / 'manifest.json'
    if args.check:
        if json.loads(path.read_text()) != manifest:
            raise SystemExit(f'Stale cliff manifest: {path}')
    else:
        path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
