"""Regression checks for the disposable GUI process and live local IPC."""
import json
import os
import sys
import unittest
from dataclasses import asdict
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalSocket
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from ui.settings_bridge import SettingsBridge


class SettingsBridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.config = CursorConfig()
        self.overlay = MagicMock()
        self.overlay.config = self.config
        self.tray = MagicMock()
        self.bridge = SettingsBridge(self.overlay, self.tray, self.app)

    def tearDown(self):
        self.bridge.stop()
        self.app.processEvents()
    def test_live_ipc_updates_without_disk_writes(self):
        client = QLocalSocket()
        client.connectToServer(self.bridge.name)
        self.assertTrue(client.waitForConnected(1000))
        QTest.qWait(100)
        self.assertEqual(len(self.bridge.clients), 1)
        settings = asdict(self.config)
        settings['cursor_size'] = 49
        settings['match_cursor_roles'] = False
        settings['enabled'] = False
        client.write((json.dumps({'type':'config', 'settings':settings})+'\n').encode())
        client.flush()
        QTest.qWait(100)
        self.assertEqual(self.config.cursor_size, 49)
        self.assertFalse(self.config.match_cursor_roles)
        self.assertFalse(self.config.enabled)
        self.overlay.clear_window.assert_called_once()
        self.overlay.cursor_mgr.restore_system_cursor.assert_called_once()
        self.overlay.invalidate_render.assert_called_once()
        self.tray.update_state.assert_called_with(False)
        client.disconnectFromServer()

    def test_settings_process_only_spawns_once(self):
        with patch('ui.settings_bridge.subprocess.Popen') as popen:
            popen.return_value.poll.return_value = None
            self.bridge.open_settings()
            self.bridge.open_settings()
            popen.assert_called_once()
            command = popen.call_args.args[0]
            self.assertIn('--settings-process', command)
            self.assertIn('--ipc', command)


if __name__ == '__main__':
    unittest.main()
