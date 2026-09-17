"""
Diagnostic & Verification test suite for FluidCursor.
"""

import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import CursorConfig
from core.physics import CursorPhysics, ClickRipple
from core.win32_cursor import Win32CursorManager
from core.theme import CursorRenderer

# Ensure QApplication exists for QPainter / QPixmap tests
app = QApplication.instance() or QApplication(sys.argv)

class TestFluidCursor(unittest.TestCase):

    def test_config_defaults_and_serialization(self):
        cfg = CursorConfig()
        self.assertTrue(cfg.enabled)
        self.assertTrue(cfg.snap_on_click)
        self.assertAlmostEqual(cfg.shrink_factor, 0.72)
        self.assertEqual(cfg.cursor_theme, "aero_modern")
        # All new advanced features MUST be disabled by default
        self.assertFalse(cfg.enable_advanced_physics)
        self.assertFalse(cfg.drag_boost)
        self.assertFalse(cfg.show_precision_dot)
        self.assertFalse(cfg.precision_dot_white_outline)

        # Test save and load to custom test path
        test_path = os.path.join(os.path.dirname(__file__), "test_config.json")
        try:
            cfg.responsiveness = 0.55
            cfg.save(test_path)
            loaded = CursorConfig.load(test_path)
            self.assertAlmostEqual(loaded.responsiveness, 0.55)
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)

    def test_physics_smoothing_and_snap_on_click(self):
        physics = CursorPhysics(x=100.0, y=100.0)

        # Move mouse hardware target to (200, 200) without click
        physics.update(
            hw_x=200, hw_y=200,
            left_down=False, right_down=False, middle_down=False,
            responsiveness=0.4,
            shrink_factor=0.7,
            snap_on_click=True
        )
        # Visual position should smoothly interpolate towards 200, but not jump to 200 in 1 frame
        self.assertGreater(physics.x, 100.0)
        self.assertLess(physics.x, 200.0)
        self.assertAlmostEqual(physics.scale, 1.0, delta=0.05)

        # Now simulate a click at (300, 300) with snap_on_click=True
        physics.update(
            hw_x=300, hw_y=300,
            left_down=True, right_down=False, middle_down=False,
            responsiveness=0.4,
            shrink_factor=0.7,
            snap_on_click=True,
            ripples_enabled=True
        )
        # MUST snap immediately to 300, 300 for 100% click accuracy
        self.assertEqual(physics.x, 300.0)
        self.assertEqual(physics.y, 300.0)
        # Scale target should be shrink_factor
        self.assertEqual(physics.target_scale, 0.7)
        # Ripple must be spawned at (300, 300)
        self.assertEqual(len(physics.ripples), 1)
        self.assertEqual(physics.ripples[0].x, 300.0)
        self.assertEqual(physics.ripples[0].y, 300.0)

    def test_cursor_renderer_all_themes(self):
        pixmap = QPixmap(128, 128)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        themes = ["aero_modern", "neon_glow", "macos_fluid", "cyber_arrow", "minimal_dot"]
        cursor_types = ["normal", "ibeam", "wait", "appstarting", "sizewe", "sizens", "sizenwse", "sizenesw", "sizeall", "hand", "cross", "no"]
        try:
            for theme in themes:
                for ctype in cursor_types:
                    # Render cursor with type
                    CursorRenderer.draw_cursor(
                        painter=painter,
                        x=32.0, y=32.0,
                        scale=0.75,
                        tilt_deg=12.0,
                        theme_name=theme,
                        size=28,
                        primary_color_hex="#FFFFFF",
                        border_color_hex="#00D2FF",
                        is_clicking=True,
                        cursor_type=ctype
                    )
            # Render ripple
            ripple = ClickRipple(x=32.0, y=32.0, radius=20.0, progress=0.5)
            CursorRenderer.draw_ripple(painter, ripple)

            # Render precision dot with white outline and legacy style
            CursorRenderer.draw_precision_dot(painter, 32.0, 32.0, with_white_outline=True)
            CursorRenderer.draw_precision_dot(painter, 40.0, 40.0, with_white_outline=False)

            # Render cloned cursor
            test_img = QPixmap(32, 32).toImage()
            CursorRenderer.draw_cloned_cursor(
                painter=painter,
                x=32.0, y=32.0,
                scale=0.75,
                tilt_deg=5.0,
                qimg=test_img,
                hotspot_x=0,
                hotspot_y=0,
                is_clicking=True
            )
        finally:
            painter.end()

    def test_all_smoothing_algorithms(self):
        modes = ["exponential", "spring", "smoothstep", "predictive", "drag"]
        for mode in modes:
            physics = CursorPhysics(x=50.0, y=50.0)
            # Simulate movement to (150, 150)
            for _ in range(5):
                physics.update(
                    hw_x=150, hw_y=150,
                    left_down=False, right_down=False, middle_down=False,
                    enable_advanced_physics=True,
                    smoothing_type=mode,
                    responsiveness=0.4,
                    spring_stiffness=280.0,
                    spring_damping=24.0,
                    prediction_factor=0.025,
                    drag_friction=18.0,
                    drag_boost=True
                )
            self.assertGreater(physics.x, 50.0)
            self.assertLessEqual(physics.x, 150.0 + 50.0) # Allow slight lead or overshoot within physical bounds

            # Test snap on click
            physics.update(
                hw_x=200, hw_y=200,
                left_down=True, right_down=False, middle_down=False,
                enable_advanced_physics=True,
                smoothing_type=mode,
                snap_on_click=True
            )
            self.assertEqual(physics.x, 200.0)
            self.assertEqual(physics.y, 200.0)

    def test_win32_system_cursor_safe_restore(self):
        mgr = Win32CursorManager()
        pos = mgr.get_cursor_pos()
        self.assertIsInstance(pos[0], int)
        self.assertIsInstance(pos[1], int)

        # Verify buttons query returns 3 bools
        btns = mgr.get_button_states()
        self.assertEqual(len(btns), 3)
        for b in btns:
            self.assertIsInstance(b, bool)

        # Force restore must not raise
        Win32CursorManager.force_restore()

if __name__ == "__main__":
    unittest.main()
