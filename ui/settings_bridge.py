"""Local, newline-delimited IPC between cursor/tray and disposable settings UI."""
import json
import os
import subprocess
import sys
from dataclasses import fields

from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication


class SettingsBridge(QObject):
    def __init__(self, overlay, tray, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.tray = tray
        self.process = None
        self.ui_ready = False
        self.clients = {}
        self.name = f'FluidCursorSettings_{os.getpid()}'
        self.server = QLocalServer(self)
        if not self.server.listen(self.name):
            raise RuntimeError('Unable to open local settings IPC: ' + self.server.errorString())
        self.server.newConnection.connect(self._accept)

    def open_settings(self):
        if self.process is not None and self.process.poll() is None:
            # The control panel is already running; request it to come forward.
            self.broadcast({'type': 'show'})
            return
        self.ui_ready = False
        project = os.path.dirname(os.path.dirname(__file__))
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        self.process = subprocess.Popen([sys.executable, os.path.join(project, 'main.py'),
                                         '--settings-process', '--ipc', self.name],
                                        cwd=project, creationflags=flags)
    def _accept(self):
        while self.server.hasPendingConnections():
            client = self.server.nextPendingConnection()
            self.clients[client] = bytearray()
            client.readyRead.connect(lambda c=client: self._read(c))
            client.disconnected.connect(lambda c=client: self._drop(c))
            self._send(client, {'type': 'state', 'enabled': self.overlay.config.enabled})

    def _send(self, client, message):
        if client.state() == QLocalSocket.LocalSocketState.ConnectedState:
            client.write((json.dumps(message) + '\n').encode('utf-8'))
            client.flush()

    def broadcast(self, message):
        for client in list(self.clients):
            self._send(client, message)

    def _drop(self, client):
        self.clients.pop(client, None)
        client.deleteLater()

    def _read(self, client):
        if client not in self.clients:
            return
        incoming = self.clients[client]
        incoming.extend(bytes(client.readAll()))
        while b'\n' in incoming:
            line, _, rest = incoming.partition(b'\n')
            incoming[:] = rest
            try:
                self._handle(json.loads(line))
            except (ValueError, TypeError, UnicodeDecodeError):
                continue
    def _handle(self, message):
        kind = message.get('type')
        if kind == 'ready':
            self.ui_ready = True
        elif kind == 'exit':
            QApplication.instance().quit()
        elif kind == 'config':
            settings = message.get('settings', {})
            if not isinstance(settings, dict):
                return
            config = self.overlay.config
            old_enabled = config.enabled
            for name in (field.name for field in fields(config)):
                if name in settings and isinstance(settings[name], type(getattr(config, name))):
                    setattr(config, name, settings[name])
            if old_enabled != config.enabled and not config.enabled:
                self.overlay.cursor_mgr.restore_system_cursor()
                self.overlay.clear_window()
            self.overlay.invalidate_render()
            self.tray.update_state(config.enabled)

    def stop(self):
        self.broadcast({'type': 'quit'})
        for client in list(self.clients):
            client.flush()
        self.server.close()
