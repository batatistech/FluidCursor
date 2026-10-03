"""Return-to-neutral must not unwind accumulated full turns."""
import math
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from core.physics import CursorPhysics


class TiltReturnShortestTests(unittest.TestCase):
    def settle(self, starting_angle, *, delay=False, never=False):
        clock = [1.0]
        with patch('core.physics.time.perf_counter', side_effect=lambda: clock[0]):
            engine = CursorPhysics(100, 100)
            engine.last_motion_time = 0.0
            engine.tilt_angle = starting_angle
            engine.target_tilt = starting_angle
            engine.held_tilt_target = starting_angle
            history = [starting_angle]
            for i in range(1, 251):
                clock[0] = 1.0 + i * .007
                engine.update(100, 100, False, False, False, tilt_enabled=True,
                              tilt_mode='physics_forward', tilt_strength=1.0,
                              tilt_disable_return=never, tilt_delay_enabled=delay,
                              tilt_decay_enabled=False)
                history.append(engine.tilt_angle)
            return engine, history
    def test_accumulated_turns_return_by_shortest_arc(self):
        for angle in (720.0, -730.0, 490.0, -490.0, 185.0, -185.0, 90.0):
            with self.subTest(start=angle):
                engine, samples = self.settle(angle)
                travelled = sum(abs((b - a + 180) % 360 - 180)
                                for a, b in zip(samples, samples[1:]))
                nearest = abs((angle + 180) % 360 - 180)
                self.assertLess(travelled, nearest + 8.0)
                self.assertLess(abs(engine.tilt_angle), .6)
                self.assertEqual(engine.held_tilt_target, 0.0)

    def test_never_return_still_holds_pose(self):
        engine, samples = self.settle(450.0, never=True)
        self.assertAlmostEqual(engine.tilt_angle, 450.0, delta=.01)


if __name__ == '__main__':
    unittest.main()
