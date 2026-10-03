"""Regression tests for continuous tilt on pixel-quantised diagonal movement."""
import math
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.physics import CursorPhysics


class DiagonalTiltStabilityTests(unittest.TestCase):
    def simulate(self, coordinates):
        clock = [0.0]
        with patch('core.physics.time.perf_counter', side_effect=lambda: clock[0]):
            physics = CursorPhysics(100, 100)
            samples = []
            for index, (x, y) in enumerate(coordinates, 1):
                clock[0] = index * 0.007
                physics.update(x, y, False, False, False, tilt_enabled=True,
                               tilt_mode='physics_forward', tilt_strength=1.0,
                               tilt_deadzone=41.0, tilt_disable_return=True)
                samples.append((physics.tilt_angle, physics.target_tilt,
                                physics.x, physics.y))
            return samples
    def test_quantised_diagonal_does_not_hunt_across_180_degrees(self):
        points = [(100 + round(i * .4), 100 + i) for i in range(1, 121)]
        samples = self.simulate(points)
        stable = samples[35:]
        angles = [sample[0] for sample in stable]
        targets = [sample[1] for sample in stable]
        self.assertLess(max(angles) - min(angles), 2.0)
        self.assertLess(max(targets) - min(targets), 1.5)
        self.assertLess(max(abs(b-a) for a,b in zip(angles, angles[1:])), .4)
        self.assertTrue(all(math.isfinite(angle) for angle in angles))
        # Position smoothing may legitimately trail the hardware target slightly.
        self.assertLess(math.dist(samples[-1][2:], points[-1]), 6.0)

    def test_motion_heading_remains_stable_for_other_diagonal_slopes(self):
        for slope_x, slope_y in ((.5, 1.25), (1., .5), (1., 1.)):
            points = [(100+round(i*slope_x), 100+round(i*slope_y))
                      for i in range(1, 121)]
            angles = [sample[0] for sample in self.simulate(points)[35:]]
            self.assertLess(max(abs(b-a) for a,b in zip(angles,angles[1:])), .4,
                            (slope_x, slope_y))

    def test_intentional_turn_tracks_without_reversing_at_seam(self):
        points = [(100+4*i,100) for i in range(1,26)]
        points += [(200,100+4*i) for i in range(1,31)]
        samples = self.simulate(points)
        before = samples[24][0]
        after = samples[-1][0]
        # Right-to-down is a 90-degree turn, not a 270-degree reversal.
        self.assertGreater(before, 70)
        self.assertGreater(after, before+55)
        self.assertLess(after-before, 120)
        self.assertLess(max(abs(b[0]-a[0]) for a,b in zip(samples[25:-1],samples[26:])), 20)


if __name__ == '__main__':
    unittest.main()
