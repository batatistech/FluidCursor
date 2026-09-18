"""
FluidCursor - Smooth, Animated & Accurate Cursor Replacement for Windows.
Entry point for the application.
"""

import sys
import os
import signal
import atexit
import ctypes
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FluidCursor")

from core.win32_cursor import Win32CursorManager
from core.config import CursorConfig
from ui.overlay import CursorOverlay
from ui.settings_window import SettingsWindow
from ui.tray import CursorTrayIcon

# Win32 Single-Instance Mutex
MUTEX_NAME = "Local\\FluidCursor_SingleInstance_Mutex"


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="FluidCursor - Animated Windows Cursor")
    parser.add_argument("--settings", action="store_true", help="Open the settings window on launch")
    parser.add_argument("--tray", action="store_true", help="Start minimized directly to the system tray")
    parser.add_argument("--restore", action="store_true", help="Emergency restore default Windows cursor and exit")
    return parser.parse_args()


def main():
    args = parse_args()

    # Emergency command: restore cursor and exit immediately
    if args.restore:
        Win32CursorManager.force_restore()
        print("Standard Windows cursor has been restored.")
        return 0

    # Ensure single instance
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        logger.warning("FluidCursor is already running!")
        # If user ran with --settings, we could signal it, or just inform
        print("FluidCursor is already running in the background. Right-click its tray icon or press F9.")
        return 0

    # Initialize Qt Application
    # High DPI attributes
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setApplicationName("FluidCursor")
    app.setOrganizationName("FluidCursor")
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    # Keep running when windows are closed (system tray app)
    app.setQuitOnLastWindowClosed(False)

    # Initialize Cursor Manager & Config
    cursor_mgr = Win32CursorManager()
    config = CursorConfig.load()

    # Teardown safety: ensure system cursor is always restored
    def safe_shutdown(*_):
        logger.info("Restoring system cursor and cleaning up...")
        cursor_mgr.restore_system_cursor()
        Win32CursorManager.force_restore()

    atexit.register(safe_shutdown)
    app.aboutToQuit.connect(safe_shutdown)

    # Signal handlers for Ctrl+C
    def sig_handler(sig, frame):
        safe_shutdown()
        app.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # Create Overlay
    overlay = CursorOverlay(config, cursor_mgr)

    # Config change callback (144Hz render timer dynamically reads updated config in memory)
    def on_config_changed():
        pass

    # Create Settings Window with Fluent UI (lazy when started with --tray)
    start_in_tray = getattr(args, "tray", False)
    if start_in_tray and getattr(config, "ram_optimization_mode", True):
        settings_win = None
        # Trim working set immediately
        SettingsWindow._trim_process_memory()
    else:
        settings_win = SettingsWindow(config, on_config_changed, cursor_mgr, cloner=overlay.cloner)

    # Create System Tray Icon
    tray_icon = CursorTrayIcon(overlay, settings_win)
    tray_icon.show()

    # Synchronize toggle state between overlay hotkey, tray, and settings window
    def on_state_toggled(is_enabled: bool):
        tray_icon.update_state(is_enabled)

    overlay.on_state_toggled = on_state_toggled

    # Show overlay
    overlay.show()

    # Show Fluent GUI control center unless started with --tray
    if settings_win and not start_in_tray:
        settings_win.show()
        settings_win.raise_()
        settings_win.activateWindow()

    # Show initial balloon notification
    tray_icon.showMessage(
        "FluidCursor Active",
        "Animated cursor is now active.\nPress F9 to toggle anytime.\nRight-click tray icon for settings.",
        CursorTrayIcon.MessageIcon.Information,
        3000
    )

    logger.info("FluidCursor started successfully.")
    ret = app.exec()
    safe_shutdown()
    return ret


if __name__ == "__main__":
    sys.exit(main())
