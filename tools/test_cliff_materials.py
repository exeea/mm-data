"""Material-bake boundaries: wrap seams, physical normal direction and shipped map channels."""
import hashlib
import json
import unittest

import numpy as np
from PIL import Image

from prepare_cliff_materials import OUTPUT, PROFILES, normal_map, periodic
from build_terrain_materials import Canvas, OUT, ROOT, normals


class CliffMaterialsTest(unittest.TestCase):
    def test_soil_bank_keeps_clods_at_board_scale_and_normals_match_height(self):
        entry = json.loads((OUT / 'manifest.json').read_text())['materials']['soil-contact']
        with Image.open(OUT / 'soil-contact.png') as image:
            height = np.asarray(image, dtype=np.float32)[..., 3] / 255 * entry['relief_metres']
        with Image.open(OUT / 'soil-contact-normal.png') as image:
            normal = np.asarray(image, dtype=np.float32)[..., :3] / 255 * 2 - 1
        expected = normals(Canvas(height.shape[0], entry['tile'], 0), height)
        self.assertTrue(np.allclose(normal, expected, atol=1 / 127),
            'The bank must light the same physical field that POM traces')
        for footprint in (.10, .20):
            with self.subTest(metres_per_pixel=footprint):
                size = round(entry['tile'] / footprint)
                filtered = np.asarray(Image.fromarray(height).resize((size, size), Image.Resampling.BOX))
                resolved = normals(Canvas(size, entry['tile'], 0), filtered)
                slope = resolved[..., :2] / resolved[..., 2:3]
                self.assertGreater(np.sqrt(np.mean(np.sum(slope * slope, axis=-1))), .025,
                    'Board-scale mips must retain clod slopes instead of a flat bank')
                self.assertGreater(filtered.std(), .005,
                    'Resolved soil relief must survive filtering, not consist only of fine pigment grain')

    def test_lunar_preserves_the_original_rock_maps_and_physical_scale(self):
        materials = json.loads((OUT / 'manifest.json').read_text())['materials']
        for name, tile in (('lunar', 8), ('lunar-cliff', 10), ('lunar-scree', 4)):
            with self.subTest(material=name):
                entry = materials[name]
                self.assertEqual(entry['tile'], tile)
                self.assertEqual(entry['source_revision'], '47748386b4224151fde1780b1401e6644f9a36b3')
                self.assertGreater(entry['relief_metres'], 0)
                for suffix, digest in (('', 'source_sha256'), ('-normal', 'normal_source_sha256')):
                    self.assertEqual(hashlib.sha256((OUT / f'{name}{suffix}.png').read_bytes()).hexdigest(), entry[digest])

    def test_generated_ground_keeps_fine_detail_without_overview_bands(self):
        materials = json.loads((OUT / 'manifest.json').read_text())['materials']
        luminance = lambda rgb: np.asarray(rgb, dtype=float) @ np.array([.2126, .7152, .0722]) / 255
        detail = lambda light: np.mean(np.diff(light, axis=0) ** 2) + np.mean(np.diff(light, axis=1) ** 2)
        for name in ('grass', 'dirt', 'sand'):
            with self.subTest(material=name), Image.open(OUT / f'{name}.png') as image:
                color = image.convert('RGB')
                with Image.open(ROOT / materials[name]['source']) as source:
                    source = source.convert('RGB').resize(color.size, Image.Resampling.LANCZOS)
                    # Measure retained detail against the artwork, not the old procedural palette's contrast.
                    self.assertGreater(detail(luminance(color)), detail(luminance(source)) * .85)
                for size in (32, 16, 8):
                    with self.subTest(mip=size):
                        light = luminance(color.resize((size, size), Image.Resampling.BOX))
                        power = abs(np.fft.fft2(light - light.mean())) ** 2
                        power[0, 0] = 0
                        for axis in (power[:, 0], power[0, :]):
                            # Ignore less than one colour-code RMS: at tiny mips quantization can dominate a
                            # nearly constant tile's relative spectrum without creating a visible band.
                            band_rms = np.sqrt(axis.sum()) / (size * size)
                            self.assertTrue(band_rms < 1 / 255 or axis.sum() / power.sum() < .15,
                                'Overview variation must not concentrate into visible repeated rows or columns')

    def test_authored_ground_and_cliff_normals_match_the_runtime_height_range(self):
        materials = json.loads((OUT / 'manifest.json').read_text())['materials']
        for name in ('grass', 'dirt', 'sand', 'granite'):
            with self.subTest(material=name):
                entry = materials[name]
                for key, digest in (('source', 'source_sha256'), ('height_source', 'height_sha256')):
                    self.assertEqual(hashlib.sha256((ROOT / entry[key]).read_bytes()).hexdigest(), entry[digest])
                with Image.open(OUT / f'{name}.png') as image:
                    height = np.asarray(image, dtype=float)[..., 3] / 255 * entry['relief_metres']
                with Image.open(OUT / f'{name}-normal.png') as image:
                    normal = np.asarray(image, dtype=float)[..., :3] / 255 * 2 - 1
                expected = normals(Canvas(height.shape[0], entry['tile'], entry['seed']), height)
                self.assertTrue(np.allclose(normal, expected, atol=1 / 127),
                    'POM and lighting must use the same quantized physical height field')

    def test_periodic_correction_removes_a_photo_edge_step_without_mirroring(self):
        x = np.arange(128) / 128
        field = np.tile(.3 * np.sin(x * 4 * np.pi) + x * .5, (128, 1))
        wrapped = periodic(field)
        seam = np.abs(wrapped[:, 0] - wrapped[:, -1]).mean()
        interior = np.abs(np.diff(wrapped, axis=1)).mean()
        self.assertLess(seam, interior * 2)
        self.assertAlmostEqual(wrapped.mean(), field.mean())
        self.assertGreater(np.std(wrapped), .1, 'Tiling must preserve broad geological structure')

    def test_normals_follow_positive_height_in_image_u_and_v(self):
        x = np.arange(128) / 128 * 2 * np.pi
        height = .5 + .2 * np.sin(x)[None, :] + .1 * np.sin(x)[:, None]
        normal = (normal_map(height, .04).astype(float) - 128) / 127
        self.assertLess(normal[0, 0, 0], 0, 'A rising U slope points the normal against U')
        self.assertLess(normal[0, 0, 1], 0, 'A rising V/down slope points against V/down')
        self.assertGreater(normal[64, 64, 0], 0)
        self.assertGreater(normal[64, 64, 1], 0)
        self.assertTrue(np.allclose(np.linalg.norm(normal, axis=-1), 1, atol=.007))
        self.assertTrue(np.array_equal(normal_map(np.full((16, 16), .5), .04)[0, 0], [128, 128, 255]))

    def test_every_runtime_family_has_aligned_finite_material_data(self):
        for family in PROFILES:
            with self.subTest(family=family):
                with Image.open(OUTPUT / f'{family}.png') as image:
                    color = np.array(image)
                with Image.open(OUTPUT / f'{family}-normal.png') as image:
                    normal = (np.array(image).astype(float) - 128) / 127
                with Image.open(OUTPUT / f'{family}-surface.png') as image:
                    surface = np.array(image)
                self.assertEqual(color.shape, (1024, 1024, 3))
                self.assertEqual(normal.shape, color.shape)
                self.assertEqual(surface.shape, (1024, 1024, 4))
                self.assertTrue(np.allclose(np.linalg.norm(normal, axis=-1), 1, atol=.007))
                self.assertGreater(surface[..., 0].std(), 10, 'Height is not a flat placeholder')
                self.assertGreater(surface[..., 1].min(), 70, 'Natural cliffs remain rough dielectrics')
                self.assertGreater(surface[..., 2].min(), 0, 'Cavities must retain ambient detail')
                self.assertEqual(np.unique(surface[..., 3]).size, 1, 'Relief range is material-wide')


if __name__ == '__main__':
    unittest.main()
