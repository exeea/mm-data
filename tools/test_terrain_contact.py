"""Authored terrain depth stays independent of pigment and reaches the shipped map pair."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

import prepare_terrain_contact as contact
from prepare_cliff_materials import authored_height


class TerrainContactTest(unittest.TestCase):
    def test_authored_relief_is_independent_of_pigment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            x = np.arange(64) / 64 * 2 * np.pi
            height = np.tile(.5 + .3 * np.cos(x * 4), (64, 1))
            Image.fromarray(np.rint(height * 255).astype('uint8')).save(root / 'sandstone-cap-height.png')
            for name, value in [('bright', 220), ('dark', 40)]:
                Image.new('RGB', (64, 64), (value, value, value)).save(root / 'sandstone-cap.png')
                with patch.object(contact, 'SOURCES', root):
                    contact.bake('sandstone-cap', root / name)
            with Image.open(root / 'bright/sandstone-cap.png') as image:
                bright = np.array(image)
            with Image.open(root / 'dark/sandstone-cap.png') as image:
                dark = np.array(image)
            self.assertFalse(np.array_equal(bright[..., :3], dark[..., :3]))
            np.testing.assert_array_equal(bright[..., 3], dark[..., 3])
            with Image.open(root / 'bright/sandstone-cap-normal.png') as image:
                normal = np.array(image)
            with Image.open(root / 'dark/sandstone-cap-normal.png') as image:
                np.testing.assert_array_equal(normal, np.array(image))
            self.assertGreater(np.ptp(normal[..., 0]), 5, 'Authored elevation must produce real light-facing slopes')
            self.assertLess(normal[..., 3].min(), 255, 'Recesses must affect cavity shading')

    def test_linear_height_retains_eight_and_sixteen_bit_levels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for dtype, maximum in [('uint8', 255), ('uint16', 65535)]:
                source = root / (dtype + '.png')
                Image.fromarray(np.full((16, 16), round(maximum * .25), dtype=dtype)).save(source)
                field = authored_height(source, 32)
                self.assertTrue(np.allclose(field, .25, atol=1 / maximum))
            self.assertIsNone(authored_height(root / 'absent.png', 32))


if __name__ == '__main__':
    unittest.main()
