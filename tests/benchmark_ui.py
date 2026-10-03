"""Repeatable settings construction benchmark (does not change user preferences)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
start = time.perf_counter()
from PyQt6.QtWidgets import QApplication
from core.config import CursorConfig
from ui.settings_window import SettingsWindow
import_time = time.perf_counter() - start
app = QApplication.instance() or QApplication(sys.argv)
config = CursorConfig()
config.save = lambda *args, **kwargs: None
start = time.perf_counter()
window = SettingsWindow(config, lambda: None, None)
construction_ms = (time.perf_counter() - start) * 1000
print(f"UI_IMPORT_MS={import_time * 1000:.1f}")
print(f"UI_CONSTRUCTION_MS={construction_ms:.1f}")
print(f"WORKING_SET_MB={window.get_current_ram_mb():.1f}")
window.deleteLater()
app.processEvents()
