"""
Full application lifecycle integration smoke test.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from core.win32_cursor import Win32CursorManager
from core.config import CursorConfig
from ui.overlay import CursorOverlay
from ui.settings_window import SettingsWindow
from ui.tray import CursorTrayIcon

def test_integration():
    app = QApplication.instance() or QApplication(sys.argv)

    config = CursorConfig()
    config.hide_system_cursor = False  # Keep visible during test for safety
    config.save = lambda *args, **kwargs: None  # Do not overwrite config.json on disk

    cursor_mgr = Win32CursorManager()

    overlay = CursorOverlay(config, cursor_mgr)
    settings_win = SettingsWindow(config, lambda: overlay.update(), cursor_mgr, cloner=overlay.cloner)
    tray = CursorTrayIcon(overlay, settings_win)

    overlay.show()
    settings_win.show()

    tick_count = 0
    def on_tick():
        nonlocal tick_count
        tick_count += 1
        overlay.tick()
        if tick_count == 10:
            # Simulate a click press
            overlay.physics.update(
                200, 200,
                left_down=True, right_down=False, middle_down=False,
                responsiveness=config.responsiveness,
                shrink_factor=config.shrink_factor,
                snap_on_click=True
            )
        elif tick_count == 20:
            # Release
            overlay.physics.update(
                200, 200,
                left_down=False, right_down=False, middle_down=False,
                responsiveness=config.responsiveness,
                shrink_factor=config.shrink_factor,
                snap_on_click=True
            )
        elif tick_count >= 30:
            print(f"Integration smoke test finished {tick_count} frames successfully!")
            settings_win.close()
            overlay.close()
            app.quit()

    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(on_tick)
    timer.start()

    app.exec()

if __name__ == "__main__":
    test_integration()
