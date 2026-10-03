"""
Tests for Basic page synchronization and Velocity vs Inertial Physics tilt dynamics (forward & opposing).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from core.config import CursorConfig
from core.physics import CursorPhysics
from ui.settings_window import SettingsWindow


class TestBasicAndTilt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_physics_tilt_modes(self):
        """Verify all three tilt modes: velocity, physics_forward, physics_opposing."""
        # 1. In 'physics_opposing' mode: Moving DOWN (vy > 0) rotates pointer upward towards -90° (positive tilt from -112.2°)
        p1 = CursorPhysics(100.0, 100.0)
        p1.update(
            hw_x=100, hw_y=200,
            left_down=False, right_down=False, middle_down=False,
            tilt_enabled=True,
            tilt_mode="physics_opposing",
            tilt_strength=1.0
        )
        self.assertGreater(p1.tilt_angle, 0.0, "Moving down in physics_opposing should rotate clockwise towards UP (-90°)")
        heading_p1 = ((-112.2 + p1.tilt_angle + 180.0) % 360.0) - 180.0
        self.assertGreater(heading_p1, -112.2, "Pointer heading should rotate towards vertical UP (-90°)")

        # 2. In 'physics_forward' mode: Moving DOWN (vy > 0) rotates pointer downward towards +90° (negative tilt from -112.2°)
        p2 = CursorPhysics(100.0, 100.0)
        p2.update(
            hw_x=100, hw_y=200,
            left_down=False, right_down=False, middle_down=False,
            tilt_enabled=True,
            tilt_mode="physics_forward",
            tilt_strength=1.0
        )
        self.assertLess(p2.tilt_angle, 0.0, "Moving down in physics_forward should rotate counter-clockwise towards DOWN (+90°)")
        heading_p2 = ((-112.2 + p2.tilt_angle + 180.0) % 360.0) - 180.0
        self.assertLess(heading_p2, -112.2, "Pointer heading should swing towards DOWN (+90°)")

        # 3. In 'velocity' mode: Moving RIGHT (vx > 0) tilts positive, moving LEFT (vx < 0) tilts negative
        p3_r = CursorPhysics(100.0, 100.0)
        p3_r.update(
            hw_x=200, hw_y=100,
            left_down=False, right_down=False, middle_down=False,
            tilt_enabled=True,
            tilt_mode="velocity",
            tilt_strength=1.0
        )
        self.assertGreater(p3_r.tilt_angle, 0.0, "Moving right in velocity tilt should lean positive")

        p3_l = CursorPhysics(100.0, 100.0)
        p3_l.update(
            hw_x=0, hw_y=100,
            left_down=False, right_down=False, middle_down=False,
            tilt_enabled=True,
            tilt_mode="velocity",
            tilt_strength=1.0
        )
        self.assertLess(p3_l.tilt_angle, 0.0, "Moving left in velocity tilt should lean negative")

    def test_tilt_strength_up_to_500(self):
        """Verify tilt strength scaling from 20% to 500% across modes."""
        # 1. In 'velocity' mode: 20% vs 100% vs 500%
        p_20 = CursorPhysics(100.0, 100.0)
        p_20.update(hw_x=200, hw_y=100, left_down=False, right_down=False, middle_down=False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=0.2)

        p_100 = CursorPhysics(100.0, 100.0)
        p_100.update(hw_x=200, hw_y=100, left_down=False, right_down=False, middle_down=False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0)

        p_500 = CursorPhysics(100.0, 100.0)
        p_500.update(hw_x=200, hw_y=100, left_down=False, right_down=False, middle_down=False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=5.0)

        self.assertLess(abs(p_20.tilt_angle), abs(p_100.tilt_angle))
        self.assertGreater(abs(p_500.tilt_angle), abs(p_100.tilt_angle) * 2.0)

        # 2. In 'physics_forward' mode: 20% vs 50% vs 100%
        pf_20 = CursorPhysics(100.0, 100.0)
        pf_20.update(hw_x=100, hw_y=200, left_down=False, right_down=False, middle_down=False, tilt_enabled=True, tilt_mode="physics_forward", tilt_strength=0.2)

        pf_100 = CursorPhysics(100.0, 100.0)
        pf_100.update(hw_x=100, hw_y=200, left_down=False, right_down=False, middle_down=False, tilt_enabled=True, tilt_mode="physics_forward", tilt_strength=1.0)

        self.assertLess(abs(pf_20.target_tilt), abs(pf_100.target_tilt))
        self.assertAlmostEqual(abs(pf_20.target_tilt), abs(pf_100.target_tilt) * 0.2, delta=1.0)

    def test_slow_rotation_decay(self):
        """Verify slow rotation return when stopping compared to instant snap."""
        import time

        # Fast snap back (tilt_decay_enabled = False, tilt_delay_enabled = False)
        p_fast = CursorPhysics(100.0, 100.0)
        for i in range(12):
            time.sleep(0.007)
            p_fast.update(100 + i * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_decay_enabled=False, tilt_delay_enabled=False)
        while p_fast.speed > 15.0:
            time.sleep(0.007)
            p_fast.update(100 + 11 * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_decay_enabled=False, tilt_delay_enabled=False)
        for _ in range(25):
            time.sleep(0.007)
            p_fast.update(100 + 11 * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_decay_enabled=False, tilt_delay_enabled=False)

        # Slow decay return (tilt_decay_enabled = True, speed = 0.5, tilt_delay_enabled = False)
        p_slow = CursorPhysics(100.0, 100.0)
        for i in range(12):
            time.sleep(0.007)
            p_slow.update(100 + i * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_decay_enabled=True, tilt_decay_speed=0.5, tilt_delay_enabled=False)
        while p_slow.speed > 15.0:
            time.sleep(0.007)
            p_slow.update(100 + 11 * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_decay_enabled=True, tilt_decay_speed=0.5, tilt_delay_enabled=False)
        for _ in range(25):
            time.sleep(0.007)
            p_slow.update(100 + 11 * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_decay_enabled=True, tilt_decay_speed=0.5, tilt_delay_enabled=False)

        # Slow decay must retain significantly more tilt after 25 stop frames (~175ms)
        self.assertGreater(abs(p_slow.tilt_angle), abs(p_fast.tilt_angle) * 3.0)

    def test_return_hold_delay(self):
        """Verify cursor holds its tilt angle after stopping before returning rather than correcting every ms."""
        import time

        p = CursorPhysics(100.0, 100.0)
        # Move for 10 frames
        for i in range(10):
            time.sleep(0.007)
            p.update(100 + i * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_delay_enabled=True, tilt_return_delay=0.45)

        # Catch up position
        while p.speed > 15.0:
            time.sleep(0.007)
            p.update(100 + 9 * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_delay_enabled=True, tilt_return_delay=0.45)

        tilt_at_stop = p.tilt_angle
        self.assertGreater(abs(tilt_at_stop), 20.0)

        # Simulate 15 frames of pause (~105ms, total ~270ms < 450ms hold delay)
        # Cursor must HOLD its tilt stably rather than correcting every ms!
        for _ in range(15):
            time.sleep(0.007)
            p.update(100 + 9 * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_delay_enabled=True, tilt_return_delay=0.45)

        self.assertAlmostEqual(p.tilt_angle, tilt_at_stop, delta=3.0, msg="Cursor must maintain tilt during hold delay")

        # Now wait for delay to expire (another 75 frames = ~525ms, total > 700ms > 450ms delay)
        for _ in range(75):
            time.sleep(0.007)
            p.update(100 + 9 * 15, 100, False, False, False, tilt_enabled=True, tilt_mode="velocity", tilt_strength=1.0, tilt_delay_enabled=True, tilt_return_delay=0.45)

        # After delay expires, it must have decayed towards 0
        self.assertLess(abs(p.tilt_angle), abs(tilt_at_stop) * 0.75, msg="Cursor must return towards neutral after delay expires")

    def test_tilt_deadzone_anti_jitter(self):
        """Verify slow movements below tilt_deadzone do not cause tilt or directional jitter."""
        import time

        # 1. Slow movement below deadzone (35 px/s threshold)
        p_slow = CursorPhysics(100.0, 100.0)
        # Move at ~10 px/s (0.1 pixel every 10ms)
        for i in range(10):
            time.sleep(0.007)
            p_slow.update(
                hw_x=100.0 + i * 0.1, hw_y=100.0,
                left_down=False, right_down=False, middle_down=False,
                tilt_enabled=True,
                tilt_mode="physics_forward",
                tilt_strength=1.0,
                tilt_deadzone=35.0
            )
        # Slow movement must produce 0 tilt, eliminating low-speed jitter!
        self.assertEqual(p_slow.tilt_angle, 0.0, "Movements below tilt_deadzone must produce 0 tilt deflection")

        # 2. Faster movement above deadzone (e.g. 15 px per frame = ~2000 px/s)
        p_fast = CursorPhysics(100.0, 100.0)
        p_fast.update(
            hw_x=100, hw_y=200,
            left_down=False, right_down=False, middle_down=False,
            tilt_enabled=True,
            tilt_mode="physics_forward",
            tilt_strength=1.0,
            tilt_deadzone=35.0
        )
        self.assertLess(p_fast.tilt_angle, 0.0, "Movements above tilt_deadzone must engage tilt smoothly")

    def test_basic_page_cleanliness_and_dedicated_tilt_page(self):
        """Verify Basic page is clean with only dynamic tilt switch, and Tilt page has nested controls."""
        config = CursorConfig()
        config.save = lambda *args, **kwargs: None
        win = SettingsWindow(config, lambda: None, None)
        win._load_page(win.tilt_interface)  # The Tilt page builds on first visit.

        # 1. Basic page cleanliness: only b_card_tilt exists, no verbose tilt sliders
        self.assertTrue(hasattr(win, "b_card_tilt"), "Basic page must have Dynamic cursor tilt switch")
        self.assertFalse(hasattr(win, "b_slider_tstr"), "Basic page should not have cluttered tilt multiplier slider")
        self.assertFalse(hasattr(win, "b_combo_tilt_mode"), "Basic page should not have tilt mode combo")
        self.assertFalse(hasattr(win, "b_card_tilt_delay"), "Basic page should not have tilt delay card")
        self.assertFalse(hasattr(win, "b_slider_delay_dur"), "Basic page should not have tilt return delay slider")
        self.assertFalse(hasattr(win, "b_card_tilt_decay"), "Basic page should not have tilt decay card")
        self.assertFalse(hasattr(win, "b_slider_decay_speed"), "Basic page should not have tilt decay speed slider")

        # 2. Dedicated Tilt page exists in sidebar
        self.assertTrue(hasattr(win, "tilt_interface"), "Dedicated Tilt interface must exist in SettingsWindow")
        self.assertTrue(hasattr(win, "t_card_tilt"), "Tilt page must have master Dynamic cursor tilt switch")
        self.assertTrue(hasattr(win, "group_tilt_options"), "Tilt page must have nested tilt options group")

        # 3. Tilt options exist on dedicated page
        self.assertTrue(hasattr(win, "t_combo_tilt_mode"))
        self.assertTrue(hasattr(win, "t_slider_tstr"))
        self.assertTrue(hasattr(win, "t_slider_deadzone"), "Tilt page must have slow movement deadzone slider")
        self.assertTrue(hasattr(win, "t_card_tilt_delay"))
        self.assertTrue(hasattr(win, "t_slider_delay_dur"))
        self.assertTrue(hasattr(win, "t_card_tilt_decay"))
        self.assertTrue(hasattr(win, "t_slider_decay_speed"))

        # 4. Tilt strength is normalized to 0-100%, including OFF at zero.
        self.assertEqual(win.t_slider_tstr.minimum(), 0)
        self.assertEqual(win.t_slider_tstr.maximum(), 100)
        win.t_slider_tstr.setValue(75)
        self.assertEqual(config.tilt_strength, .75)
        self.assertEqual(win.t_lbl_tstr.text(), "75%")

        # 5. Slow movement deadzone slider (0 to 120 px/s)
        self.assertEqual(win.t_slider_deadzone.maximum(), 120)
        win.t_slider_deadzone.setValue(50)
        self.assertEqual(config.tilt_deadzone, 50.0)
        self.assertEqual(win.t_lbl_deadzone.text(), "50 px/s")

        # 6. Nested disablement: when Dynamic cursor tilt is disabled, all nested options are disabled!
        win.t_card_tilt.setChecked(False)
        self.assertFalse(config.tilt_enabled)
        self.assertFalse(win.b_card_tilt.isChecked(), "Basic tilt card must sync with Tilt page card")
        self.assertFalse(win.group_tilt_options.isEnabled(), "All nested tilt options must be disabled when tilt is OFF")

        # Re-enable tilt: nested options become enabled
        win.b_card_tilt.setChecked(True)
        self.assertTrue(config.tilt_enabled)
        self.assertTrue(win.t_card_tilt.isChecked(), "Tilt page card must sync with Basic tilt card")
        self.assertTrue(win.group_tilt_options.isEnabled(), "Nested tilt options must re-enable when tilt is ON")

        # 7. Verify 'Hide Windows system cursor' switch exists on Basic and System pages and syncs
        self.assertTrue(hasattr(win, "b_card_hide"))
        self.assertTrue(hasattr(win, "s_card_hide"))
        win.b_card_hide.setChecked(False)
        self.assertFalse(config.hide_system_cursor)
        self.assertFalse(win.s_card_hide.isChecked())
        win.s_card_hide.setChecked(True)
        self.assertTrue(config.hide_system_cursor)
        self.assertTrue(win.b_card_hide.isChecked())

    def test_downward_motion_hold_delay(self):
        """Verify downward motion in physics_forward points down and strictly HOLDS its tilt angle during delay."""
        import time

        p = CursorPhysics(100.0, 100.0)
        # 1. Active downward stroke for 12 frames
        for i in range(12):
            time.sleep(0.007)
            p.update(
                hw_x=100.0, hw_y=100.0 + i * 25.0,
                left_down=False, right_down=False, middle_down=False,
                tilt_enabled=True,
                tilt_mode="physics_forward",
                tilt_strength=1.0,
                tilt_delay_enabled=True,
                tilt_return_delay=0.45
            )

        # Catch up position
        while p.speed > 30.0:
            time.sleep(0.007)
            p.update(
                hw_x=100.0, hw_y=100.0 + 11 * 25.0,
                left_down=False, right_down=False, middle_down=False,
                tilt_enabled=True,
                tilt_mode="physics_forward",
                tilt_strength=1.0,
                tilt_delay_enabled=True,
                tilt_return_delay=0.45
            )

        # The cursor must be tilted significantly towards pointing down (~ -157.8°)
        tilt_at_stop = p.tilt_angle
        self.assertLess(tilt_at_stop, -80.0, "Downward movement must produce substantial negative tilt pointing down")

        # 2. Pause for 15 frames (~105ms, total pause < 450ms hold delay)
        for _ in range(15):
            time.sleep(0.007)
            p.update(
                hw_x=100.0, hw_y=100.0 + 11 * 25.0,
                left_down=False, right_down=False, middle_down=False,
                tilt_enabled=True,
                tilt_mode="physics_forward",
                tilt_strength=1.0,
                tilt_delay_enabled=True,
                tilt_return_delay=0.45
            )

        # Cursor MUST hold downward tilt during return delay, NOT return ASAP!
        self.assertAlmostEqual(p.tilt_angle, tilt_at_stop, delta=4.0, msg="Downward motion must maintain tilt during return hold delay")

        # 3. After delay expires (> 450ms), cursor must smoothly return towards neutral
        for _ in range(75):
            time.sleep(0.007)
            p.update(
                hw_x=100.0, hw_y=100.0 + 11 * 25.0,
                left_down=False, right_down=False, middle_down=False,
                tilt_enabled=True,
                tilt_mode="physics_forward",
                tilt_strength=1.0,
                tilt_delay_enabled=True,
                tilt_return_delay=0.45
            )
        self.assertLess(abs(p.tilt_angle), abs(tilt_at_stop) * 0.75, msg="Cursor must return towards neutral after delay expires")

    def test_down_right_movement_anti_jitter(self):
        """Verify moving down-right across 67.8° branch cut produces smooth continuous deflection with zero jitter."""
        import time

        p = CursorPhysics(100.0, 100.0)
        # 1. Establish down-right motion
        for _ in range(15):
            time.sleep(0.007)
            p.update(140.0, 200.0, False, False, False, tilt_enabled=True, tilt_mode="physics_forward", tilt_strength=1.0)

        # 2. Sweep down-right wobbling across the +67.8° boundary
        targets = [
            (143.0, 300.0), (140.0, 400.0), (144.0, 500.0),
            (140.0, 600.0), (143.0, 700.0), (140.0, 800.0), (145.0, 900.0)
        ]
        prev_tilt = p.tilt_angle
        for hx, hy in targets:
            for _ in range(6):
                time.sleep(0.007)
                p.update(hx, hy, False, False, False, tilt_enabled=True, tilt_mode="physics_forward", tilt_strength=1.0)
            # Heading must remain stably pointing down / down-right (~65° to 95°) without 360° branch-cut flips
            heading = ((-112.2 + p.tilt_angle + 180.0) % 360.0) - 180.0
            self.assertGreater(heading, 55.0, "Visual heading must point towards down / down-right")
            self.assertLess(heading, 98.0, "Visual heading must point towards down / down-right")
            step = abs(((p.tilt_angle - prev_tilt + 180.0) % 360.0) - 180.0)
            self.assertLess(step, 15.0, f"Tilt changed by {step}° between wobble frames - must not jitter!")
            prev_tilt = p.tilt_angle

    def test_full_physics_stability_above_110_percent(self):
        """Verify full physics at 110%, 150%, 200%, 350%, 500% never wraps or throws cursor all over the place."""
        test_strengths = [1.1, 1.5, 2.0, 3.5, 5.0]

        for strength in test_strengths:
            for mode in ["physics_forward", "physics_opposing"]:
                # Downward motion (the critical case near -180°)
                p_down = CursorPhysics(100.0, 100.0)
                p_down.update(
                    hw_x=100.0, hw_y=200.0,
                    left_down=False, right_down=False, middle_down=False,
                    tilt_enabled=True,
                    tilt_mode=mode,
                    tilt_strength=strength
                )
                self.assertTrue(
                    -165.01 <= p_down.target_tilt <= 165.01,
                    f"Target tilt {p_down.target_tilt} at {strength*100}% in {mode} must stay strictly within [-165, 165]"
                )

                # Down-left diagonal motion (where bank/vx previously caused -180° wrap-around flip)
                p_diag = CursorPhysics(100.0, 100.0)
                p_diag.update(
                    hw_x=50.0, hw_y=200.0,
                    left_down=False, right_down=False, middle_down=False,
                    tilt_enabled=True,
                    tilt_mode=mode,
                    tilt_strength=strength
                )
                self.assertTrue(
                    -165.01 <= p_diag.target_tilt <= 165.01,
                    f"Diagonal target tilt {p_diag.target_tilt} at {strength*100}% in {mode} must stay strictly within [-165, 165]"
                )

    def test_tilt_disable_return(self):
        """Verify cursor retains its tilted orientation indefinitely after stopping when tilt_disable_return is True."""
        import time
        p = CursorPhysics(100.0, 100.0)

        # 1. Establish downward tilt
        for i in range(12):
            time.sleep(0.007)
            p.update(
                100.0, 100.0 + (i + 1) * 25.0, False, False, False,
                tilt_enabled=True,
                tilt_mode="physics_forward",
                tilt_strength=1.0,
                tilt_disable_return=True
            )

        # Catch up position
        while p.speed > 30.0:
            time.sleep(0.007)
            p.update(
                100.0, 100.0 + 12 * 25.0, False, False, False,
                tilt_enabled=True,
                tilt_mode="physics_forward",
                tilt_strength=1.0,
                tilt_disable_return=True
            )

        tilt_at_stop = p.tilt_angle
        self.assertLess(tilt_at_stop, -80.0, "Downward movement must produce substantial negative tilt")

        # 2. Wait 90 frames (~630ms, well beyond normal delay)
        for _ in range(90):
            time.sleep(0.007)
            p.update(
                100.0, 100.0 + 12 * 25.0, False, False, False,
                tilt_enabled=True,
                tilt_mode="physics_forward",
                tilt_strength=1.0,
                tilt_disable_return=True
            )

        # Cursor MUST maintain its tilted angle indefinitely and NEVER return to 0°!
        self.assertAlmostEqual(p.tilt_angle, tilt_at_stop, delta=3.0, msg="Cursor must never return to original position when tilt_disable_return is True")
        self.assertLess(p.tilt_angle, -80.0, "Cursor must remain tilted indefinitely")

    def test_greyed_out_controls_when_options_disabled(self):
        """Verify dependent controls are greyed out (disabled) when parent option is turned off."""
        config = CursorConfig()
        config.save = lambda *args, **kwargs: None
        win = SettingsWindow(config, lambda: None, None)
        for page in (win.tilt_interface, win.click_interface,
                     win.app_interface, win.motion_interface):
            win._load_page(page)

        # 1. Tilt page: Disable return to original position
        self.assertTrue(hasattr(win, "t_card_tilt_never_return"))
        win.t_card_tilt_never_return.setChecked(True)
        self.assertTrue(config.tilt_disable_return)
        # When disable_return is True, delay and decay controls are greyed out!
        self.assertFalse(win.t_card_tilt_delay.isEnabled(), "Hold delay switch must be greyed out when return is disabled")
        self.assertFalse(win.t_card_delay_dur.isEnabled(), "Hold delay duration must be greyed out when return is disabled")
        self.assertFalse(win.t_card_tilt_decay.isEnabled(), "Decay switch must be greyed out when return is disabled")
        self.assertFalse(win.t_card_decay_speed.isEnabled(), "Decay speed slider must be greyed out when return is disabled")

        # Re-enable return: delay and decay switches re-enable
        win.t_card_tilt_never_return.setChecked(False)
        self.assertFalse(config.tilt_disable_return)
        self.assertTrue(win.t_card_tilt_delay.isEnabled())
        self.assertTrue(win.t_card_tilt_decay.isEnabled())

        # 2. Click Dynamics: Click ripples disablement
        self.assertTrue(hasattr(win, "c_card_ripples"))
        self.assertTrue(hasattr(win, "c_card_rip_col"))
        win.c_card_ripples.setChecked(False)
        self.assertFalse(config.ripples_enabled)
        self.assertFalse(win.c_card_rip_col.isEnabled(), "Ripple color card must be greyed out when ripples are OFF")
        win.c_card_ripples.setChecked(True)
        self.assertTrue(win.c_card_rip_col.isEnabled(), "Ripple color card must be enabled when ripples are ON")

        # 3. Precision Dot: white outline greyed out when dot is OFF
        win.card_dot.setChecked(False)
        self.assertFalse(win.card_outl.isEnabled(), "Dot outline must be greyed out when precision dot is OFF")
        win.card_dot.setChecked(True)
        self.assertTrue(win.card_outl.isEnabled(), "Dot outline must be enabled when precision dot is ON")

        # 4. Advanced Physics: All cards greyed out when master switch is OFF
        win.card_adv_master.setChecked(False)
        self.assertFalse(win.card_algo.isEnabled())
        self.assertTrue(win.card_boost.isEnabled())  # Works with standard physics.
        self.assertFalse(win.card_stiff.isEnabled())
        self.assertFalse(win.card_damp.isEnabled())
        self.assertFalse(win.card_pred.isEnabled())
        self.assertFalse(win.card_drag.isEnabled())

        # When enabled with spring algorithm:
        win.card_adv_master.setChecked(True)
        win._update_algo(1)  # spring
        self.assertTrue(win.card_stiff.isEnabled())
        self.assertTrue(win.card_damp.isEnabled())
        self.assertFalse(win.card_pred.isEnabled())
        self.assertFalse(win.card_drag.isEnabled())

        # When switched to predictive:
        win._update_algo(3)  # predictive
        self.assertFalse(win.card_stiff.isEnabled())
        self.assertFalse(win.card_damp.isEnabled())
        self.assertTrue(win.card_pred.isEnabled())
        self.assertFalse(win.card_drag.isEnabled())

        # When switched to drag:
        win._update_algo(4)  # drag
        self.assertFalse(win.card_stiff.isEnabled())
        self.assertFalse(win.card_damp.isEnabled())
        self.assertFalse(win.card_pred.isEnabled())
        self.assertTrue(win.card_drag.isEnabled())

        # 5. Appearance: When Clone active Windows cursor is ON, vector theme and colors are greyed out!
        self.assertTrue(hasattr(win, "a_card_clone"))
        self.assertTrue(hasattr(win, "card_theme"))
        self.assertTrue(hasattr(win, "card_prim"))
        self.assertTrue(hasattr(win, "card_border"))
        win.a_card_clone.setChecked(True)
        self.assertTrue(config.use_system_cursor_clone)
        self.assertFalse(win.card_theme.isEnabled(), "Theme selection must be greyed out when clone cursor is ON")
        self.assertFalse(win.card_prim.isEnabled(), "Primary color must be greyed out when clone cursor is ON")
        self.assertFalse(win.card_border.isEnabled(), "Border color must be greyed out when clone cursor is ON")

        # Cloning OFF enables themes, but palette editing requires Custom Colors Arrow.
        win.a_card_clone.setChecked(False)
        self.assertFalse(config.use_system_cursor_clone)
        self.assertTrue(win.card_theme.isEnabled())
        self.assertFalse(win.card_prim.isEnabled())
        self.assertFalse(win.card_border.isEnabled())
        win.combo_theme.setCurrentIndex(5)
        self.assertEqual(config.cursor_theme, "custom_arrow")
        self.assertTrue(win.card_prim.isEnabled())
        self.assertTrue(win.card_border.isEnabled())
        win.a_card_clone.setChecked(True)
        self.assertFalse(win.card_prim.isEnabled())
        win.a_card_clone.setChecked(False)
        self.assertTrue(win.card_prim.isEnabled())

    def test_gui_performance_save_debouncing(self):
        """Verify SettingsWindow has debounce timer to eliminate slider scrubbing disk I/O lag."""
        config = CursorConfig()
        config.save = lambda *args, **kwargs: None  # Never overwrite live user settings in tests.
        win = SettingsWindow(config, lambda: None, None)
        self.assertTrue(hasattr(win, "_save_timer"), "SettingsWindow must have _save_timer for debouncing")
        self.assertTrue(win._save_timer.isSingleShot(), "Save timer must be single shot")


if __name__ == "__main__":
    unittest.main()


