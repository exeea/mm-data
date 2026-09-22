"""Material-bake boundaries: wrap seams, physical normal direction and shipped map channels."""
import unittest

import numpy as np
from PIL import Image

from prepare_cliff_materials import OUTPUT, PROFILES, normal_map, periodic


class CliffMaterialsTest(unittest.TestCase):
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
