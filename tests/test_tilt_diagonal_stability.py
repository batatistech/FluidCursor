import unittest
from unittest.mock import patch
from core.physics import CursorPhysics


class TiltDiagonalStabilityTests(unittest.TestCase):
    def test_quantised_diagonal_does_not_axis_hunt(self):
        clock = [100.0]
        with patch('core.physics.time.perf_counter', side_effect=lambda: clock[0]):
            p = CursorPhysics(100, 100)
            x = y = 100
            tilts = []
            headings = []
            for i in range(90):
                clock[0] += .007
                if i % 2 == 0:
                    x += 2
                else:
                    y += 2
                p.update(x, y, False, False, False,
                         tilt_enabled=True, tilt_mode='physics_forward',
                         tilt_strength=1.0, tilt_deadzone=0.0)
                if i > 35:
                    tilts.append(p.tilt_angle)
                    headings.append(p.motion_heading)
            self.assertGreater(min(headings), 35.0)
            self.assertLess(max(headings), 55.0)
            max_step = max(abs(b-a) for a,b in zip(tilts, tilts[1:]))
            self.assertLess(max_step, 3.0)
