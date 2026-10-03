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
from PyQt6.QtCore import Qt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FluidCursor")

from core.win32_cursor import Win32CursorManager
from core.config import CursorConfig
from core.i18n import tr
from ui.overlay import CursorOverlay
from ui.tray import CursorTrayIcon

# Win32 Single-Instance Mutex
MUTEX_NAME = "Local\\FluidCursor_SingleInstance_Mutex"


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="FluidCursor - Animated Windows Cursor")
    parser.add_argument("--settings", action="store_true", help="Open the settings window on launch")
    parser.add_argument("--tray", action="store_true", help="Start minimized directly to the system tray")
    parser.add_argument("--restore", action="store_true", help="Emergency restore default Windows cursor and exit")
    parser.add_argument("--settings-process", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ipc", default="", help=argparse.SUPPRESS)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.settings_process:
        from ui.settings_host import run_settings
        return run_settings(args.ipc)

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
        print("FluidCursor is already running in the background. Right-click its tray icon to open settings or use your configured shortcut.")
        return 0

    # Initialize Qt Application
    # High DPI attributes
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setApplicationName("FluidCursor")
    app.setOrganizationName("FluidCursor")
    # Only the separate Settings process needs the large application icon.
    # The resident cursor uses its own pre-rendered tray icon.
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

    # Never load the large Fluent UI library into the resident cursor process.
    tray_icon = CursorTrayIcon(overlay, None)
    tray_icon.menu.prewarm()  # Warm native popup before hiding Windows pointer.
    from ui.settings_bridge import SettingsBridge
    bridge = SettingsBridge(overlay, tray_icon, app)
    tray_icon.settings_launcher = bridge.open_settings
    tray_icon.show()
    app.aboutToQuit.connect(bridge.stop)

    # Synchronize toggle state between overlay hotkey, tray, and settings window
    def on_state_toggled(is_enabled: bool):
        tray_icon.update_state(is_enabled)
        config.save()
        bridge.broadcast({'type': 'state', 'enabled': is_enabled})

    overlay.on_state_toggled = on_state_toggled

    # Show overlay
    overlay.show()

    if not args.tray:
        bridge.open_settings()

    # Show initial balloon notification
    tray_icon.showMessage(
        tr("FluidCursor Active", config.language),
        (tr("Animated cursor is now active.", config.language) + "\n" +
         tr("Press {key} to toggle.", config.language).format(key=config.toggle_hotkey) + "\n" +
         tr("Right-click tray icon for settings.", config.language)),
        CursorTrayIcon.MessageIcon.Information,
        3000
    )

    logger.info("FluidCursor started successfully.")
    ret = app.exec()
    safe_shutdown()
    return ret


if __name__ == "__main__":
    sys.exit(main())
