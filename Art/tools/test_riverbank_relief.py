import unittest

import numpy as np

from bake_riverbank_relief import bank_delta


class BankBakeTest(unittest.TestCase):
    def test_protection_and_reach_stability_at_two_grid_sizes(self):
        for cell in (1., 1.8):
            with self.subTest(cell=cell):
                y, x = np.indices((181, 181)) * cell
                center = 80 + 6 * np.sin(y / 30)
                wet = abs(x - center) <= 6
                protected = abs(y - 65) < 4
                height = np.rint((20 + .35 * (abs(x - center) - 6)) / .005).astype("<u2")
                stations = np.arange(0., y.max() + 1., 2.)
                guide = np.column_stack([80 + 6 * np.sin(stations / 30), stations, stations * 0 + 20])
                args = (height, wet, protected, guide, [0, 0], cell, .005, 0, 711)
                full = bank_delta(*args)
                pilot = bank_delta(*args, reach=(40, 140))
                np.testing.assert_array_equal(pilot, bank_delta(*args, reach=(40, 140)))
                np.testing.assert_array_equal(pilot[wet | protected], 0)
                np.testing.assert_array_equal(pilot[(y < 28) | (y > 157)], 0)
                interior = (y > 60) & (y < 115)
                np.testing.assert_allclose(pilot[interior], full[interior], atol=1.e-6)
                for side in (x < center, x > center):
                    self.assertGreater(pilot[side].max(), .4)
                    self.assertLess(pilot[side].min(), -.12)


if __name__ == "__main__":
    unittest.main()
